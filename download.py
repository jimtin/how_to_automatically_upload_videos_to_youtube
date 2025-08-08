#!/usr/bin/env python3
"""
Google Drive to YouTube Uploader with Notion Tracking
Automatically uploads videos from Google Drive to YouTube and logs to Notion
Handles large files (4GB+) efficiently
"""

import os
import sys
import json
import time
import logging
import argparse
import datetime
import pickle
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# Google APIs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Notion API
import requests

# Progress bar for large file operations
from tqdm import tqdm

# =============================================================================
# CONFIGURATION - Update these values
# =============================================================================

CONFIG = {
    # Google Drive Settings
    "GDRIVE_FOLDER_ID": "YOUR_GOOGLE_DRIVE_FOLDER_ID",  # The folder to monitor
    "GDRIVE_SCOPES": ["https://www.googleapis.com/auth/drive.readonly"],
    
    # YouTube Settings
    "YOUTUBE_SCOPES": ["https://www.googleapis.com/auth/youtube.upload"],
    "YOUTUBE_CATEGORY_ID": "22",  # 22 = People & Blogs (change as needed)
    "YOUTUBE_PRIVACY": "private",  # private, unlisted, or public
    
    # Notion Settings
    "NOTION_TOKEN": "YOUR_NOTION_INTEGRATION_TOKEN",
    "NOTION_DATABASE_ID": "YOUR_NOTION_DATABASE_ID",
    "NOTION_VERSION": "2022-06-28",
    
    # Local Settings
    "TEMP_DOWNLOAD_PATH": "./temp_videos",  # Temporary storage for downloads
    "PROCESSED_FILES_DB": "./processed_files.json",  # Track processed files
    "LOG_FILE": "./upload_log.txt",
    
    # Processing Settings
    "MAX_RETRIES": 3,
    "CHUNK_SIZE": 50 * 1024 * 1024,  # 50MB chunks for large files
    "VIDEO_EXTENSIONS": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"],
}

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class VideoFile:
    """Represents a video file to be processed"""
    id: str
    name: str
    size: int
    mime_type: str
    gdrive_link: str
    local_path: Optional[str] = None
    youtube_id: Optional[str] = None
    youtube_url: Optional[str] = None
    upload_status: str = "pending"
    error_message: Optional[str] = None
    processed_date: Optional[str] = None

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging for the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"]),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# GOOGLE DRIVE FUNCTIONS
# =============================================================================

class GoogleDriveHandler:
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_file = 'gdrive_token.pickle'
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'gdrive_credentials.json', CONFIG["GDRIVE_SCOPES"])
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def list_videos(self, folder_id: str) -> List[VideoFile]:
        """List all video files in the specified folder"""
        videos = []
        
        try:
            # Build query for video files
            mime_types = [
                "video/mp4", "video/quicktime", "video/x-msvideo",
                "video/x-matroska", "video/webm", "video/x-flv",
                "video/x-ms-wmv"
            ]
            
            mime_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])
            query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"
            
            # Execute query
            response = self.service.files().list(
                q=query,
                fields="files(id, name, size, mimeType, webViewLink)",
                pageSize=100
            ).execute()
            
            files = response.get('files', [])
            
            for file in files:
                video = VideoFile(
                    id=file['id'],
                    name=file['name'],
                    size=int(file.get('size', 0)),
                    mime_type=file['mimeType'],
                    gdrive_link=file.get('webViewLink', '')
                )
                videos.append(video)
                logger.info(f"Found video: {video.name} ({self._format_size(video.size)})")
            
        except HttpError as error:
            logger.error(f"An error occurred listing files: {error}")
        
        return videos
    
    def download_file(self, file_id: str, file_name: str, file_size: int) -> str:
        """Download a file from Google Drive with progress bar"""
        Path(CONFIG["TEMP_DOWNLOAD_PATH"]).mkdir(parents=True, exist_ok=True)
        local_path = os.path.join(CONFIG["TEMP_DOWNLOAD_PATH"], file_name)
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=CONFIG["CHUNK_SIZE"])
                
                done = False
                pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Downloading {file_name}")
                
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        pbar.update(status.resumable_progress - pbar.n)
                
                pbar.close()
            
            logger.info(f"Downloaded: {file_name} to {local_path}")
            return local_path
            
        except HttpError as error:
            logger.error(f"An error occurred downloading file: {error}")
            raise
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

# =============================================================================
# YOUTUBE FUNCTIONS
# =============================================================================

class YouTubeHandler:
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API"""
        creds = None
        token_file = 'youtube_token.pickle'
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'youtube_credentials.json', CONFIG["YOUTUBE_SCOPES"])
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('youtube', 'v3', credentials=creds)
    
    def upload_video(self, video_file: VideoFile, 
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Tuple[str, str]:
        """Upload a video to YouTube with resumable upload for large files"""
        
        if not video_file.local_path or not os.path.exists(video_file.local_path):
            raise FileNotFoundError(f"Local file not found: {video_file.local_path}")
        
        # Prepare metadata
        if not title:
            title = os.path.splitext(video_file.name)[0]
        
        if not description:
            description = f"Uploaded from Google Drive on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': CONFIG["YOUTUBE_CATEGORY_ID"]
            },
            'status': {
                'privacyStatus': CONFIG["YOUTUBE_PRIVACY"]
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
            request = self.service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Handle resumable upload with progress
            response = None
            error = None
            retry = 0
            pbar = tqdm(total=video_file.size, unit='B', unit_scale=True, 
                       desc=f"Uploading to YouTube")
            
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
                        time.sleep(2 ** retry)
                    else:
                        raise
            
            pbar.close()
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"Upload successful! Video ID: {video_id}")
                return video_id, video_url
            
        except HttpError as error:
            logger.error(f"An error occurred uploading to YouTube: {error}")
            raise

# =============================================================================
# NOTION FUNCTIONS
# =============================================================================

class NotionHandler:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {CONFIG['NOTION_TOKEN']}",
            "Content-Type": "application/json",
            "Notion-Version": CONFIG["NOTION_VERSION"]
        }
    
    def create_entry(self, video: VideoFile):
        """Create or update an entry in Notion database"""
        url = "https://api.notion.com/v1/pages"
        
        # Prepare the data according to your Notion database schema
        # Adjust property names to match your database
        data = {
            "parent": {"database_id": CONFIG["NOTION_DATABASE_ID"]},
            "properties": {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": video.name
                            }
                        }
                    ]
                },
                "File Size": {
                    "number": video.size / (1024 * 1024)  # Convert to MB
                },
                "Google Drive Link": {
                    "url": video.gdrive_link
                },
                "YouTube URL": {
                    "url": video.youtube_url if video.youtube_url else None
                },
                "YouTube ID": {
                    "rich_text": [
                        {
                            "text": {
                                "content": video.youtube_id or ""
                            }
                        }
                    ]
                },
                "Status": {
                    "select": {
                        "name": video.upload_status
                    }
                },
                "Upload Date": {
                    "date": {
                        "start": datetime.datetime.now().isoformat()
                    }
                },
                "Error Message": {
                    "rich_text": [
                        {
                            "text": {
                                "content": video.error_message or ""
                            }
                        }
                    ]
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info(f"Created Notion entry for: {video.name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Notion entry: {e}")
            # Don't fail the whole process if Notion update fails
            pass

# =============================================================================
# PROCESSED FILES TRACKING
# =============================================================================

class ProcessedFilesTracker:
    def __init__(self):
        self.db_file = CONFIG["PROCESSED_FILES_DB"]
        self.processed = self._load()
    
    def _load(self) -> Dict:
        """Load processed files database"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save(self):
        """Save processed files database"""
        with open(self.db_file, 'w') as f:
            json.dump(self.processed, f, indent=2)
    
    def is_processed(self, file_id: str) -> bool:
        """Check if a file has been processed"""
        return file_id in self.processed
    
    def mark_processed(self, video: VideoFile):
        """Mark a file as processed"""
        self.processed[video.id] = {
            "name": video.name,
            "youtube_id": video.youtube_id,
            "youtube_url": video.youtube_url,
            "processed_date": datetime.datetime.now().isoformat(),
            "status": video.upload_status
        }
        self._save()

# =============================================================================
# MAIN PROCESSING LOGIC
# =============================================================================

class VideoProcessor:
    def __init__(self):
        self.gdrive = GoogleDriveHandler()
        self.youtube = YouTubeHandler()
        self.notion = NotionHandler()
        self.tracker = ProcessedFilesTracker()
    
    def process_videos(self, folder_id: str = None, skip_processed: bool = True):
        """Main processing logic"""
        folder_id = folder_id or CONFIG["GDRIVE_FOLDER_ID"]
        
        logger.info("=" * 60)
        logger.info("Starting video processing...")
        logger.info(f"Monitoring folder: {folder_id}")
        logger.info("=" * 60)
        
        # Get list of videos
        videos = self.gdrive.list_videos(folder_id)
        logger.info(f"Found {len(videos)} video(s) in folder")
        
        # Process each video
        for video in videos:
            try:
                # Skip if already processed
                if skip_processed and self.tracker.is_processed(video.id):
                    logger.info(f"Skipping already processed: {video.name}")
                    continue
                
                logger.info(f"\nProcessing: {video.name}")
                logger.info(f"Size: {self.gdrive._format_size(video.size)}")
                
                # Step 1: Download from Google Drive
                logger.info("Step 1/3: Downloading from Google Drive...")
                video.local_path = self.gdrive.download_file(
                    video.id, video.name, video.size
                )
                
                # Step 2: Upload to YouTube
                logger.info("Step 2/3: Uploading to YouTube...")
                video.youtube_id, video.youtube_url = self.youtube.upload_video(video)
                video.upload_status = "success"
                
                # Step 3: Update Notion
                logger.info("Step 3/3: Updating Notion database...")
                self.notion.create_entry(video)
                
                # Mark as processed
                self.tracker.mark_processed(video)
                
                # Clean up temp file
                if video.local_path and os.path.exists(video.local_path):
                    os.remove(video.local_path)
                    logger.info(f"Cleaned up temp file: {video.local_path}")
                
                logger.info(f"✓ Successfully processed: {video.name}")
                logger.info(f"  YouTube URL: {video.youtube_url}")
                
            except Exception as e:
                logger.error(f"✗ Failed to process {video.name}: {str(e)}")
                video.upload_status = "failed"
                video.error_message = str(e)
                
                # Still update Notion with failure status
                try:
                    self.notion.create_entry(video)
                except:
                    pass
                
                # Clean up temp file if exists
                if video.local_path and os.path.exists(video.local_path):
                    try:
                        os.remove(video.local_path)
                    except:
                        pass
        
        logger.info("\n" + "=" * 60)
        logger.info("Processing complete!")
        logger.info("=" * 60)

# =============================================================================
# SETUP WIZARD
# =============================================================================

def setup_wizard():
    """Interactive setup wizard for first-time configuration"""
    print("\n" + "=" * 60)
    print("GOOGLE DRIVE TO YOUTUBE UPLOADER - SETUP WIZARD")
    print("=" * 60)
    
    print("\nThis wizard will help you set up the script for first use.")
    print("You'll need:")
    print("1. Google Cloud Console project with Drive and YouTube APIs enabled")
    print("2. OAuth 2.0 credentials (client_secrets.json files)")
    print("3. Notion integration token and database ID")
    print("4. Google Drive folder ID to monitor")
    
    input("\nPress Enter to continue...")
    
    # Check for credential files
    print("\n1. GOOGLE CREDENTIALS")
    print("-" * 40)
    
    if not os.path.exists('gdrive_credentials.json'):
        print("✗ gdrive_credentials.json not found!")
        print("  Download from Google Cloud Console and place in script directory")
    else:
        print("✓ gdrive_credentials.json found")
    
    if not os.path.exists('youtube_credentials.json'):
        print("✗ youtube_credentials.json not found!")
        print("  Download from Google Cloud Console and place in script directory")
    else:
        print("✓ youtube_credentials.json found")
    
    # Get configuration values
    print("\n2. CONFIGURATION VALUES")
    print("-" * 40)
    
    config_updates = {}
    
    # Google Drive Folder ID
    print("\nGoogle Drive Folder ID:")
    print("  Find this in the URL when viewing the folder")
    print("  Example: https://drive.google.com/drive/folders/[FOLDER_ID]")
    folder_id = input("  Enter folder ID: ").strip()
    if folder_id:
        config_updates["GDRIVE_FOLDER_ID"] = folder_id
    
    # Notion Configuration
    print("\nNotion Integration Token:")
    print("  Get this from https://www.notion.so/my-integrations")
    notion_token = input("  Enter token (or press Enter to skip Notion): ").strip()
    if notion_token:
        config_updates["NOTION_TOKEN"] = notion_token
        
        print("\nNotion Database ID:")
        print("  Find this in the database URL or share link")
        database_id = input("  Enter database ID: ").strip()
        if database_id:
            config_updates["NOTION_DATABASE_ID"] = database_id
    
    # YouTube Privacy Setting
    print("\nYouTube Privacy Setting:")
    print("  1. private (default)")
    print("  2. unlisted")
    print("  3. public")
    privacy_choice = input("  Choose (1-3): ").strip()
    privacy_map = {"1": "private", "2": "unlisted", "3": "public"}
    if privacy_choice in privacy_map:
        config_updates["YOUTUBE_PRIVACY"] = privacy_map[privacy_choice]
    
    # Update configuration
    if config_updates:
        print("\n3. SAVING CONFIGURATION")
        print("-" * 40)
        
        # Create config file
        with open('config.json', 'w') as f:
            json.dump(config_updates, f, indent=2)
        
        print("✓ Configuration saved to config.json")
        print("\nYou can edit config.json manually or update the CONFIG")
        print("dictionary in the script to change settings.")
    
    print("\n" + "=" * 60)
    print("Setup complete! Run the script again to start processing.")
    print("=" * 60)

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Upload videos from Google Drive to YouTube with Notion tracking'
    )
    parser.add_argument('--setup', action='store_true', 
                       help='Run setup wizard')
    parser.add_argument('--folder', type=str, 
                       help='Google Drive folder ID to process')
    parser.add_argument('--reprocess', action='store_true',
                       help='Reprocess already uploaded videos')
    parser.add_argument('--dry-run', action='store_true',
                       help='List videos without processing')
    
    args = parser.parse_args()
    
    # Load external config if exists
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            CONFIG.update(json.load(f))
    
    # Run setup wizard if requested
    if args.setup:
        setup_wizard()
        return
    
    # Check for required configuration
    if CONFIG["GDRIVE_FOLDER_ID"] == "YOUR_GOOGLE_DRIVE_FOLDER_ID":
        print("Error: Script not configured. Run with --setup flag first.")
        return
    
    # Dry run - just list videos
    if args.dry_run:
        gdrive = GoogleDriveHandler()
        videos = gdrive.list_videos(args.folder or CONFIG["GDRIVE_FOLDER_ID"])
        print(f"\nFound {len(videos)} video(s):")
        for v in videos:
            print(f"  - {v.name} ({gdrive._format_size(v.size)})")
        return
    
    # Process videos
    try:
        processor = VideoProcessor()
        processor.process_videos(
            folder_id=args.folder,
            skip_processed=not args.reprocess
        )
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()