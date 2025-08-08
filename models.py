#!/usr/bin/env python3
"""
Data models for Google Drive to YouTube Uploader
"""

from dataclasses import dataclass
from typing import Optional
import datetime

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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "mime_type": self.mime_type,
            "gdrive_link": self.gdrive_link,
            "local_path": self.local_path,
            "youtube_id": self.youtube_id,
            "youtube_url": self.youtube_url,
            "upload_status": self.upload_status,
            "error_message": self.error_message,
            "processed_date": self.processed_date or datetime.datetime.now().isoformat()
        }
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"