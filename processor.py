#!/usr/bin/env python3
"""
Main video processing logic
"""

import os
import logging
import datetime
from typing import Optional, List

from config import CONFIG
from models import VideoFile
from gdrive_handler import GoogleDriveHandler
from youtube_handler import YouTubeHandler
from notion_handler import NotionHandler
from tracker import ProcessedFilesTracker

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Main processor that coordinates all operations"""
    
    def __init__(self):
        """Initialize all handlers"""
        logger.info("Initializing video processor...")
        self.gdrive = GoogleDriveHandler()
        self.youtube = YouTubeHandler()
        self.notion = NotionHandler()
        self.tracker = ProcessedFilesTracker()
        logger.info("Video processor initialized successfully")
    
    def process_videos(self, 
                      folder_id: Optional[str] = None, 
                      skip_processed: bool = True,
                      video_filter: Optional[str] = None):
        """
        Main processing logic
        
        Args:
            folder_id: Google Drive folder ID (uses config default if None)
            skip_processed: Skip already processed videos
            video_filter: Optional filter for video names (substring match)
        """
        folder_id = folder_id or CONFIG["GDRIVE_FOLDER_ID"]
        
        logger.info("=" * 60)
        logger.info("Starting video processing...")
        logger.info(f"Monitoring folder: {folder_id}")
        logger.info(f"Skip processed: {skip_processed}")
        if video_filter:
            logger.info(f"Filter: '{video_filter}'")
        if CONFIG["DRY_RUN"]:
            logger.info("DRY RUN MODE - No actual uploads will be performed")
        logger.info("=" * 60)
        
        # Get statistics
        stats = self.tracker.get_statistics()
        logger.info(f"Database statistics: {stats['successful']} successful, "
                   f"{stats['failed']} failed, {stats['total_processed']} total")
        
        # Get list of videos
        videos = self.gdrive.list_videos(folder_id)
        logger.info(f"Found {len(videos)} video(s) in folder")
        
        # Apply filter if provided
        if video_filter:
            videos = [v for v in videos if video_filter.lower() in v.name.lower()]
            logger.info(f"After filtering: {len(videos)} video(s) match criteria")
        
        # Track processing results
        processed_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # Process each video
        for i, video in enumerate(videos, 1):
            try:
                logger.info(f"\n--- Video {i}/{len(videos)} ---")
                
                # Skip if already processed
                if skip_processed and self.tracker.is_processed(video.id):
                    processed_info = self.tracker.get_processed_info(video.id)
                    logger.info(f"Skipping already processed: {video.name}")
                    logger.info(f"  Status: {processed_info.get('status')}")
                    if processed_info.get('youtube_url'):
                        logger.info(f"  YouTube: {processed_info.get('youtube_url')}")
                    skipped_count += 1
                    continue
                
                logger.info(f"Processing: {video.name}")
                logger.info(f"Size: {VideoFile.format_size(video.size)}")
                
                if CONFIG["DRY_RUN"]:
                    logger.info("DRY RUN: Would process this video")
                    continue
                
                # Process the video
                self._process_single_video(video)
                
                if video.upload_status == "success":
                    success_count += 1
                else:
                    failed_count += 1
                
                processed_count += 1
                
            except KeyboardInterrupt:
                logger.info("\nProcess interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing {video.name}: {e}")
                failed_count += 1
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Videos found: {len(videos)}")
        logger.info(f"Processed: {processed_count}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Skipped: {skipped_count}")
        logger.info("=" * 60)
    
    def _process_single_video(self, video: VideoFile):
        """
        Process a single video file
        
        Args:
            video: VideoFile object to process
        """
        try:
            # Step 1: Download from Google Drive
            logger.info("Step 1/3: Downloading from Google Drive...")
            video.local_path = self.gdrive.download_file(
                video.id, video.name, video.size
            )
            
            # Step 2: Upload to YouTube
            logger.info("Step 2/3: Uploading to YouTube...")
            video.youtube_id, video.youtube_url = self.youtube.upload_video(video)
            video.upload_status = "success"
            video.processed_date = datetime.datetime.now().isoformat()
            
            # Step 3: Update Notion
            if not CONFIG["SKIP_NOTION"]:
                logger.info("Step 3/3: Updating Notion database...")
                self.notion.create_entry(video)
            
            # Mark as processed
            self.tracker.mark_processed(video)
            
            # Clean up temp file
            if CONFIG["DELETE_AFTER_UPLOAD"] and video.local_path and os.path.exists(video.local_path):
                os.remove(video.local_path)
                logger.info(f"Cleaned up temp file: {video.local_path}")
            
            logger.info(f"✓ Successfully processed: {video.name}")
            logger.info(f"  YouTube URL: {video.youtube_url}")
            
        except Exception as e:
            logger.error(f"✗ Failed to process {video.name}: {str(e)}")
            video.upload_status = "failed"
            video.error_message = str(e)
            video.processed_date = datetime.datetime.now().isoformat()
            
            # Still update Notion with failure status
            if not CONFIG["SKIP_NOTION"]:
                try:
                    self.notion.create_entry(video)
                except:
                    pass
            
            # Mark as processed (with failed status)
            self.tracker.mark_processed(video)
            
            # Clean up temp file if exists
            if video.local_path and os.path.exists(video.local_path):
                try:
                    os.remove(video.local_path)
                except:
                    pass
            
            # Re-raise the exception
            raise
    
    def list_videos(self, folder_id: Optional[str] = None) -> List[VideoFile]:
        """
        List videos without processing
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of VideoFile objects
        """
        folder_id = folder_id or CONFIG["GDRIVE_FOLDER_ID"]
        videos = self.gdrive.list_videos(folder_id)
        
        # Add processing status to each video
        for video in videos:
            if self.tracker.is_processed(video.id):
                info = self.tracker.get_processed_info(video.id)
                video.upload_status = info.get('status', 'unknown')
                video.youtube_url = info.get('youtube_url')
                video.processed_date = info.get('processed_date')
        
        return videos
    
    def retry_failed(self):
        """Retry all failed uploads"""
        failed = self.tracker.list_failed()
        
        if not failed:
            logger.info("No failed uploads to retry")
            return
        
        logger.info(f"Found {len(failed)} failed uploads to retry")
        
        for item in failed:
            logger.info(f"Retrying: {item['name']} (ID: {item['id']})")
            # Remove from processed database so it can be retried
            self.tracker.remove_processed(item['id'])
        
        # Now process with skip_processed=True (they've been removed from DB)
        self.process_videos(skip_processed=True)