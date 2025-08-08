#!/usr/bin/env python3
"""
Configuration management for Google Drive to YouTube Uploader
Handles environment variables and configuration validation
"""

import os
import sys
from typing import List, Tuple, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION FROM ENVIRONMENT
# =============================================================================

CONFIG = {
    # Google Drive Settings
    "GDRIVE_FOLDER_ID": os.getenv("GDRIVE_FOLDER_ID", ""),
    "GDRIVE_CREDENTIALS_FILE": os.getenv("GDRIVE_CREDENTIALS_FILE", "gdrive_credentials.json"),
    "GDRIVE_TOKEN_FILE": os.getenv("GDRIVE_TOKEN_FILE", "gdrive_token.pickle"),
    "GDRIVE_SCOPES": ["https://www.googleapis.com/auth/drive.readonly"],
    
    # YouTube Settings
    "YOUTUBE_CREDENTIALS_FILE": os.getenv("YOUTUBE_CREDENTIALS_FILE", "youtube_credentials.json"),
    "YOUTUBE_TOKEN_FILE": os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.pickle"),
    "YOUTUBE_SCOPES": [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly"
    ],
    "YOUTUBE_CATEGORY_ID": os.getenv("YOUTUBE_CATEGORY_ID", "22"),  # 22 = People & Blogs
    "YOUTUBE_PRIVACY": os.getenv("YOUTUBE_PRIVACY", "private"),  # private, unlisted, or public
    "YOUTUBE_DEFAULT_TAGS": os.getenv("YOUTUBE_DEFAULT_TAGS", "").split(",") if os.getenv("YOUTUBE_DEFAULT_TAGS") else [],
    
    # Notion Settings
    "NOTION_TOKEN": os.getenv("NOTION_TOKEN", ""),
    "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID", ""),
    "NOTION_VERSION": os.getenv("NOTION_VERSION", "2022-06-28"),
    
    # Local Settings
    "TEMP_DOWNLOAD_PATH": os.getenv("TEMP_DOWNLOAD_PATH", "./temp_videos"),
    "PROCESSED_FILES_DB": os.getenv("PROCESSED_FILES_DB", "./processed_files.json"),
    "LOG_FILE": os.getenv("LOG_FILE", "./upload_log.txt"),
    
    # Processing Settings
    "MAX_RETRIES": int(os.getenv("MAX_RETRIES", "3")),
    "CHUNK_SIZE": int(os.getenv("CHUNK_SIZE", str(50 * 1024 * 1024))),  # 50MB default
    "VIDEO_EXTENSIONS": os.getenv("VIDEO_EXTENSIONS", ".mp4,.mov,.avi,.mkv,.webm,.flv,.wmv").split(","),
    
    # Optional Settings
    "SKIP_NOTION": os.getenv("SKIP_NOTION", "false").lower() == "true",
    "DELETE_AFTER_UPLOAD": os.getenv("DELETE_AFTER_UPLOAD", "true").lower() == "true",
    "DRY_RUN": os.getenv("DRY_RUN", "false").lower() == "true",
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_environment() -> Tuple[List[str], List[str]]:
    """
    Validate that required environment variables are set
    
    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []
    
    # Required variables
    if not CONFIG["GDRIVE_FOLDER_ID"]:
        errors.append("GDRIVE_FOLDER_ID is not set")
    
    # Check for credential files
    if not os.path.exists(CONFIG["GDRIVE_CREDENTIALS_FILE"]):
        errors.append(f"Google Drive credentials file not found: {CONFIG['GDRIVE_CREDENTIALS_FILE']}")
    
    if not os.path.exists(CONFIG["YOUTUBE_CREDENTIALS_FILE"]):
        errors.append(f"YouTube credentials file not found: {CONFIG['YOUTUBE_CREDENTIALS_FILE']}")
    
    # Notion is optional but warn if partially configured
    if CONFIG["NOTION_TOKEN"] and not CONFIG["NOTION_DATABASE_ID"]:
        warnings.append("NOTION_TOKEN is set but NOTION_DATABASE_ID is missing")
    elif CONFIG["NOTION_DATABASE_ID"] and not CONFIG["NOTION_TOKEN"]:
        warnings.append("NOTION_DATABASE_ID is set but NOTION_TOKEN is missing")
    elif not CONFIG["NOTION_TOKEN"] and not CONFIG["SKIP_NOTION"]:
        warnings.append("Notion credentials not configured. Set SKIP_NOTION=true to disable Notion integration")
    
    return errors, warnings

def check_configuration() -> bool:
    """
    Check if configuration is valid and print any issues
    
    Returns:
        True if configuration is valid, False otherwise
    """
    errors, warnings = validate_environment()
    
    if errors:
        print("\n❌ Configuration errors detected:")
        for error in errors:
            print(f"  - {error}")
        print("\nRun 'python main.py --setup' to configure, or create a .env file manually")
        return False
    
    if warnings:
        print("\n⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return True

def print_configuration():
    """Print current configuration (hiding sensitive values)"""
    print("\n" + "=" * 60)
    print("CURRENT CONFIGURATION")
    print("=" * 60)
    
    sensitive_keys = ["NOTION_TOKEN", "GDRIVE_TOKEN", "YOUTUBE_TOKEN"]
    
    for key, value in CONFIG.items():
        if any(sensitive in key for sensitive in sensitive_keys):
            if value:
                display_value = "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
            else:
                display_value = "(not set)"
        elif isinstance(value, list):
            display_value = ", ".join(value) if value else "(empty)"
        elif isinstance(value, bool):
            display_value = "Yes" if value else "No"
        elif not value:
            display_value = "(not set)"
        else:
            display_value = value
        
        print(f"  {key}: {display_value}")
    
    print("=" * 60)