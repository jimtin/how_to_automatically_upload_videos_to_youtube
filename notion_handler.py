#!/usr/bin/env python3
"""
Notion handler for tracking uploads in a database
"""

import logging
import datetime
from typing import Optional, Dict, List
import requests

from config import CONFIG
from models import VideoFile

logger = logging.getLogger(__name__)

class NotionHandler:
    """Handles all Notion database operations"""
    
    def __init__(self):
        self.enabled = (
            not CONFIG["SKIP_NOTION"] 
            and CONFIG["NOTION_TOKEN"] 
            and CONFIG["NOTION_DATABASE_ID"]
        )
        
        if self.enabled:
            self.headers = {
                "Authorization": f"Bearer {CONFIG['NOTION_TOKEN']}",
                "Content-Type": "application/json",
                "Notion-Version": CONFIG["NOTION_VERSION"]
            }
            logger.info("Notion integration enabled")
        else:
            logger.info("Notion integration disabled")
    
    def create_entry(self, video: VideoFile) -> Optional[Dict]:
        """
        Create or update an entry in Notion database
        
        Args:
            video: VideoFile object with upload information
            
        Returns:
            Notion API response or None if disabled/failed
        """
        if not self.enabled:
            return None
        
        url = "https://api.notion.com/v1/pages"
        
        # Prepare the data according to your Notion database schema
        data = {
            "parent": {"database_id": CONFIG["NOTION_DATABASE_ID"]},
            "properties": self._build_properties(video)
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info(f"Created Notion entry for: {video.name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Notion entry: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return None
    
    def _build_properties(self, video: VideoFile) -> Dict:
        """
        Build Notion properties from VideoFile
        
        Args:
            video: VideoFile object
            
        Returns:
            Dictionary of Notion properties
        """
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": video.name[:2000]  # Notion text limit
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": video.upload_status
                }
            }
        }
        
        # Add optional properties if they have values
        if video.size:
            properties["File Size"] = {
                "number": round(video.size / (1024 * 1024), 2)  # Convert to MB
            }
        
        if video.gdrive_link:
            properties["Google Drive Link"] = {
                "url": video.gdrive_link
            }
        
        if video.youtube_url:
            properties["YouTube URL"] = {
                "url": video.youtube_url
            }
        
        if video.youtube_id:
            properties["YouTube ID"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": video.youtube_id
                        }
                    }
                ]
            }
        
        if video.processed_date or video.upload_status == "success":
            properties["Upload Date"] = {
                "date": {
                    "start": video.processed_date or datetime.datetime.now().isoformat()
                }
            }
        
        if video.error_message:
            properties["Error Message"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": video.error_message[:2000]  # Limit error message length
                        }
                    }
                ]
            }
        
        return properties
    
    def find_entry_by_gdrive_id(self, gdrive_id: str) -> Optional[str]:
        """
        Find an existing Notion entry by Google Drive file ID
        
        Args:
            gdrive_id: Google Drive file ID
            
        Returns:
            Notion page ID if found, None otherwise
        """
        if not self.enabled:
            return None
        
        url = f"https://api.notion.com/v1/databases/{CONFIG['NOTION_DATABASE_ID']}/query"
        
        # Query for entries with matching Google Drive ID
        query = {
            "filter": {
                "property": "Google Drive ID",
                "rich_text": {
                    "equals": gdrive_id
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=query)
            response.raise_for_status()
            results = response.json().get("results", [])
            
            if results:
                return results[0]["id"]
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Notion database: {e}")
            return None
    
    def update_entry(self, page_id: str, video: VideoFile) -> Optional[Dict]:
        """
        Update an existing Notion entry
        
        Args:
            page_id: Notion page ID
            video: VideoFile object with updated information
            
        Returns:
            Notion API response or None if failed
        """
        if not self.enabled:
            return None
        
        url = f"https://api.notion.com/v1/pages/{page_id}"
        
        data = {
            "properties": self._build_properties(video)
        }
        
        try:
            response = requests.patch(url, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info(f"Updated Notion entry for: {video.name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update Notion entry: {e}")
            return None
    
    def get_database_schema(self) -> Optional[Dict]:
        """
        Get the schema of the Notion database
        
        Returns:
            Dictionary with database schema or None if failed
        """
        if not self.enabled:
            return None
        
        url = f"https://api.notion.com/v1/databases/{CONFIG['NOTION_DATABASE_ID']}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get database schema: {e}")
            return None