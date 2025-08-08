#!/usr/bin/env python3
"""
YouTube handler for uploading videos
"""

import os
import pickle
import time
import logging
import datetime
from typing import Optional, List, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tqdm import tqdm

from config import CONFIG
from models import VideoFile

logger = logging.getLogger(__name__)

class YouTubeHandler:
    """Handles all YouTube operations"""
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API"""
        creds = None
        token_file = CONFIG["YOUTUBE_TOKEN_FILE"]
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CONFIG["YOUTUBE_CREDENTIALS_FILE"], 
                    CONFIG["YOUTUBE_SCOPES"]
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('youtube', 'v3', credentials=creds)
    
    def upload_video(self, 
                    video_file: VideoFile, 
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    thumbnail: Optional[str] = None) -> Tuple[str, str]:
        """
        Upload a video to YouTube with resumable upload for large files
        
        Args:
            video_file: VideoFile object with local_path set
            title: Video title (defaults to filename)
            description: Video description
            tags: List of tags for the video
            thumbnail: Path to thumbnail image (optional)
            
        Returns:
            Tuple of (video_id, video_url)
        """
        if not video_file.local_path or not os.path.exists(video_file.local_path):
            raise FileNotFoundError(f"Local file not found: {video_file.local_path}")
        
        # Prepare metadata
        if not title:
            title = os.path.splitext(video_file.name)[0]
        
        if not description:
            description = f"Uploaded from Google Drive on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Use default tags if none provided
        if not tags:
            tags = CONFIG["YOUTUBE_DEFAULT_TAGS"]
        
        body = {
            'snippet': {
                'title': title[:100],  # YouTube title limit is 100 chars
                'description': description[:5000],  # Description limit is 5000 chars
                'tags': tags[:500],  # Max 500 tags
                'categoryId': CONFIG["YOUTUBE_CATEGORY_ID"]
            },
            'status': {
                'privacyStatus': CONFIG["YOUTUBE_PRIVACY"],
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Create media upload object with resumable=True for large files
        media = MediaFileUpload(
            video_file.local_path,
            chunksize=CONFIG["CHUNK_SIZE"],
            resumable=True,
            mimetype=video_file.mime_type
        )
        
        try:
            # Execute upload
            logger.info(f"Starting YouTube upload for: {video_file.name}")
            logger.info(f"Title: {title}")
            logger.info(f"Privacy: {CONFIG['YOUTUBE_PRIVACY']}")
            
            request = self.service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Handle resumable upload with progress
            response = None
            error = None
            retry = 0
            pbar = tqdm(
                total=video_file.size, 
                unit='B', 
                unit_scale=True, 
                desc=f"Uploading to YouTube"
            )
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        pbar.update(status.resumable_progress - pbar.n)
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        error = f"HTTP {e.resp.status}: {e.content}"
                        retry += 1
                        if retry > CONFIG["MAX_RETRIES"]:
                            raise
                        wait_time = 2 ** retry
                        logger.warning(f"Upload failed, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise
            
            pbar.close()
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Upload successful! Video ID: {video_id}")
                
                # Upload thumbnail if provided
                if thumbnail and os.path.exists(thumbnail):
                    self.upload_thumbnail(video_id, thumbnail)
                
                return video_id, video_url
            else:
                raise Exception("Upload failed: No response received")
            
        except HttpError as error:
            logger.error(f"An error occurred uploading to YouTube: {error}")
            raise
        except Exception as error:
            logger.error(f"Unexpected error during upload: {error}")
            raise
    
    def upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """
        Upload a thumbnail for a video
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image
        """
        try:
            media = MediaFileUpload(thumbnail_path)
            request = self.service.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            response = request.execute()
            logger.info(f"Thumbnail uploaded for video {video_id}")
        except HttpError as error:
            logger.warning(f"Failed to upload thumbnail: {error}")
    
    def get_video_status(self, video_id: str) -> dict:
        """
        Get the processing status of a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video status information
        """
        try:
            request = self.service.videos().list(
                part="status,processingDetails",
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]
            return {}
        except HttpError as error:
            logger.error(f"Error getting video status: {error}")
            raise
    
    def update_video_metadata(self, 
                            video_id: str,
                            title: Optional[str] = None,
                            description: Optional[str] = None,
                            tags: Optional[List[str]] = None):
        """
        Update metadata for an existing video
        
        Args:
            video_id: YouTube video ID
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)
        """
        try:
            # First get the current video data
            request = self.service.videos().list(
                part="snippet",
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                raise ValueError(f"Video {video_id} not found")
            
            snippet = response['items'][0]['snippet']
            
            # Update only provided fields
            if title:
                snippet['title'] = title[:100]
            if description:
                snippet['description'] = description[:5000]
            if tags:
                snippet['tags'] = tags[:500]
            
            # Update the video
            update_request = self.service.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": snippet
                }
            )
            update_response = update_request.execute()
            logger.info(f"Updated metadata for video {video_id}")
            
        except HttpError as error:
            logger.error(f"Error updating video metadata: {error}")
            raise