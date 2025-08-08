#!/usr/bin/env python3
"""
Tracker for managing processed files database
"""

import os
import json
import logging
import datetime
from typing import Dict, Optional, List

from config import CONFIG
from models import VideoFile

logger = logging.getLogger(__name__)

class ProcessedFilesTracker:
    """Manages tracking of processed files to avoid duplicates"""
    
    def __init__(self):
        self.db_file = CONFIG["PROCESSED_FILES_DB"]
        self.processed = self._load()
        logger.info(f"Loaded {len(self.processed)} processed files from database")
    
    def _load(self) -> Dict:
        """
        Load processed files database from JSON file
        
        Returns:
            Dictionary of processed files
        """
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse {self.db_file}, starting with empty database")
                return {}
            except Exception as e:
                logger.error(f"Error loading processed files database: {e}")
                return {}
        return {}
    
    def _save(self):
        """Save processed files database to JSON file"""
        try:
            # Create backup before saving
            if os.path.exists(self.db_file):
                backup_file = f"{self.db_file}.backup"
                with open(self.db_file, 'r') as original:
                    with open(backup_file, 'w') as backup:
                        backup.write(original.read())
            
            # Save the database
            with open(self.db_file, 'w') as f:
                json.dump(self.processed, f, indent=2, sort_keys=True)
                
        except Exception as e:
            logger.error(f"Error saving processed files database: {e}")
            raise
    
    def is_processed(self, file_id: str) -> bool:
        """
        Check if a file has been processed
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if file has been processed, False otherwise
        """
        return file_id in self.processed
    
    def mark_processed(self, video: VideoFile):
        """
        Mark a file as processed
        
        Args:
            video: VideoFile object with processing information
        """
        self.processed[video.id] = {
            "name": video.name,
            "size": video.size,
            "youtube_id": video.youtube_id,
            "youtube_url": video.youtube_url,
            "processed_date": video.processed_date or datetime.datetime.now().isoformat(),
            "status": video.upload_status,
            "error_message": video.error_message
        }
        self._save()
        logger.info(f"Marked as processed: {video.name} (ID: {video.id})")
    
    def get_processed_info(self, file_id: str) -> Optional[Dict]:
        """
        Get information about a processed file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary with processing information or None
        """
        return self.processed.get(file_id)
    
    def remove_processed(self, file_id: str) -> bool:
        """
        Remove a file from processed database
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if removed, False if not found
        """
        if file_id in self.processed:
            file_info = self.processed[file_id]
            del self.processed[file_id]
            self._save()
            logger.info(f"Removed from processed: {file_info.get('name', file_id)}")
            return True
        return False
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about processed files
        
        Returns:
            Dictionary with statistics
        """
        total = len(self.processed)
        successful = sum(1 for item in self.processed.values() if item.get('status') == 'success')
        failed = sum(1 for item in self.processed.values() if item.get('status') == 'failed')
        total_size = sum(item.get('size', 0) for item in self.processed.values())
        
        return {
            "total_processed": total,
            "successful": successful,
            "failed": failed,
            "pending": total - successful - failed,
            "total_size_bytes": total_size,
            "total_size_formatted": VideoFile.format_size(total_size)
        }
    
    def list_failed(self) -> List[Dict]:
        """
        Get list of failed uploads
        
        Returns:
            List of failed file information
        """
        failed = []
        for file_id, info in self.processed.items():
            if info.get('status') == 'failed':
                failed.append({
                    'id': file_id,
                    'name': info.get('name'),
                    'error': info.get('error_message'),
                    'date': info.get('processed_date')
                })
        return failed
    
    def clear_failed(self):
        """Remove all failed entries from the database"""
        failed_ids = [
            file_id for file_id, info in self.processed.items() 
            if info.get('status') == 'failed'
        ]
        
        for file_id in failed_ids:
            del self.processed[file_id]
        
        if failed_ids:
            self._save()
            logger.info(f"Cleared {len(failed_ids)} failed entries from database")
    
    def export_to_csv(self, output_file: str = "processed_files.csv"):
        """
        Export processed files database to CSV
        
        Args:
            output_file: Path to output CSV file
        """
        import csv
        
        if not self.processed:
            logger.warning("No processed files to export")
            return
        
        # Get all possible fields
        all_fields = set()
        for info in self.processed.values():
            all_fields.update(info.keys())
        
        # Write CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['file_id'] + sorted(list(all_fields))
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for file_id, info in self.processed.items():
                row = {'file_id': file_id}
                row.update(info)
                writer.writerow(row)
        
        logger.info(f"Exported {len(self.processed)} entries to {output_file}")