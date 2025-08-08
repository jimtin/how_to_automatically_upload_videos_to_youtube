#!/usr/bin/env python3
"""
Google Drive handler for downloading videos
"""

import os
import pickle
import logging
from pathlib import Path
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm

from config import CONFIG
from models import VideoFile

logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    """Handles all Google Drive operations"""
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_file = CONFIG["GDRIVE_TOKEN_FILE"]
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CONFIG["GDRIVE_CREDENTIALS_FILE"], 
                    CONFIG["GDRIVE_SCOPES"]
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def list_videos(self, folder_id: str) -> List[VideoFile]:
        """
        List all video files in the specified folder
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of VideoFile objects
        """
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
            
            # Execute query with pagination support
            page_token = None
            while True:
                response = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, size, mimeType, webViewLink)",
                    pageSize=100,
                    pageToken=page_token
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
                    logger.info(f"Found video: {video.name} ({VideoFile.format_size(video.size)})")
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
        except HttpError as error:
            logger.error(f"An error occurred listing files: {error}")
            raise
        
        return videos
    
    def download_file(self, file_id: str, file_name: str, file_size: int) -> str:
        """
        Download a file from Google Drive with progress bar
        
        Args:
            file_id: Google Drive file ID
            file_name: Name for the downloaded file
            file_size: Size of the file in bytes
            
        Returns:
            Path to the downloaded file
        """
        # Create temp directory if it doesn't exist
        Path(CONFIG["TEMP_DOWNLOAD_PATH"]).mkdir(parents=True, exist_ok=True)
        local_path = os.path.join(CONFIG["TEMP_DOWNLOAD_PATH"], file_name)
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(
                    fh, 
                    request, 
                    chunksize=CONFIG["CHUNK_SIZE"]
                )
                
                done = False
                pbar = tqdm(
                    total=file_size, 
                    unit='B', 
                    unit_scale=True, 
                    desc=f"Downloading {file_name}"
                )
                
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        pbar.update(status.resumable_progress - pbar.n)
                
                pbar.close()
            
            logger.info(f"Downloaded: {file_name} to {local_path}")
            return local_path
            
        except HttpError as error:
            logger.error(f"An error occurred downloading file: {error}")
            if os.path.exists(local_path):
                os.remove(local_path)
            raise
        except Exception as error:
            logger.error(f"Unexpected error downloading file: {error}")
            if os.path.exists(local_path):
                os.remove(local_path)
            raise
    
    def get_file_metadata(self, file_id: str) -> dict:
        """
        Get detailed metadata for a file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary with file metadata
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, mimeType, createdTime, modifiedTime, parents, webViewLink"
            ).execute()
            return file
        except HttpError as error:
            logger.error(f"An error occurred getting file metadata: {error}")
            raise