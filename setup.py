#!/usr/bin/env python3
"""
Setup wizard and utility functions
"""

import os
import datetime

def create_env_template():
    """Create a .env.template file with all available options"""
    template = """# Google Drive to YouTube Uploader Configuration
# Copy this file to .env and fill in your values

# ==== REQUIRED SETTINGS ====

# Google Drive folder ID to monitor for videos
# You can use either just the folder ID or the full URL
GDRIVE_FOLDER_ID=

# ==== GOOGLE CREDENTIALS ====

# Path to Google Drive OAuth credentials JSON file
# Download from Google Cloud Console
GDRIVE_CREDENTIALS_FILE=gdrive_credentials.json

# Path to YouTube OAuth credentials JSON file
# Download from Google Cloud Console
YOUTUBE_CREDENTIALS_FILE=youtube_credentials.json

# ==== NOTION SETTINGS (Optional) ====

# Notion integration token
# Get from https://www.notion.so/my-integrations
NOTION_TOKEN=

# Notion database ID
# Find in database URL or share link
NOTION_DATABASE_ID=

# Skip Notion integration entirely (true/false)
SKIP_NOTION=false

# ==== YOUTUBE SETTINGS ====

# Privacy setting for uploaded videos: private, unlisted, or public
YOUTUBE_PRIVACY=private

# YouTube category ID (22 = People & Blogs)
# See: https://developers.google.com/youtube/v3/docs/videoCategories/list
YOUTUBE_CATEGORY_ID=22

# Default tags for videos (comma-separated)
YOUTUBE_DEFAULT_TAGS=

# ==== PROCESSING SETTINGS ====

# Temporary download directory
TEMP_DOWNLOAD_PATH=./temp_videos

# Database file to track processed videos
PROCESSED_FILES_DB=./processed_files.json

# Log file location
LOG_FILE=./upload_log.txt

# Maximum retry attempts for failed operations
MAX_RETRIES=3

# Chunk size for uploads/downloads in bytes (default: 50MB)
CHUNK_SIZE=52428800

# Delete local files after successful upload (true/false)
DELETE_AFTER_UPLOAD=true

# ==== ADVANCED SETTINGS ====

# Token storage files (pickle format)
GDRIVE_TOKEN_FILE=gdrive_token.pickle
YOUTUBE_TOKEN_FILE=youtube_token.pickle

# Notion API version
NOTION_VERSION=2022-06-28

# Video file extensions to process (comma-separated)
VIDEO_EXTENSIONS=.mp4,.mov,.avi,.mkv,.webm,.flv,.wmv

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Dry run mode - list videos without processing (true/false)
DRY_RUN=false
"""
    
    with open('.env.template', 'w') as f:
        f.write(template)
    
    print("✓ Created .env.template file")

def setup_wizard():
    """Interactive setup wizard for first-time configuration"""
    print("\n" + "=" * 60)
    print("GOOGLE DRIVE TO YOUTUBE UPLOADER - SETUP WIZARD")
    print("=" * 60)
    
    print("\nThis wizard will help you set up the script for first use.")
    print("\nPrerequisites:")
    print("1. Google Cloud Console project with APIs enabled:")
    print("   - Google Drive API")
    print("   - YouTube Data API v3")
    print("2. OAuth 2.0 credentials downloaded as JSON files")
    print("3. (Optional) Notion integration token and database")
    
    input("\nPress Enter to continue...")
    
    # Create .env.template
    print("\n1. CREATING CONFIGURATION TEMPLATE")
    print("-" * 40)
    create_env_template()
    
    # Check for .env file
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        overwrite = input("  Overwrite existing .env? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("  Keeping existing .env file")
            return
    
    # Create .env file
    print("\n2. CREATING .ENV FILE")
    print("-" * 40)
    
    env_content = []
    
    # Google Drive Folder ID
    print("\nGoogle Drive Configuration:")
    print("  You can provide either:")
    print("    - Just the folder ID: 1ABC123xyz")
    print("    - Or the full URL: https://drive.google.com/drive/folders/1ABC123xyz")
    folder_id = input("  Enter folder ID or URL: ").strip()
    if folder_id:
        env_content.append(f"GDRIVE_FOLDER_ID={folder_id}")
    else:
        print("  ⚠️  Warning: No folder ID provided - you'll need to add this later")
    
    # Credentials files
    print("\nCredentials Files:")
    print("  Default locations:")
    print("    - gdrive_credentials.json")
    print("    - youtube_credentials.json")
    custom_paths = input("  Use custom paths? (y/N): ").strip().lower()
    if custom_paths == 'y':
        gdrive_creds = input("  Google Drive credentials path: ").strip()
        youtube_creds = input("  YouTube credentials path: ").strip()
        if gdrive_creds:
            env_content.append(f"GDRIVE_CREDENTIALS_FILE={gdrive_creds}")
        if youtube_creds:
            env_content.append(f"YOUTUBE_CREDENTIALS_FILE={youtube_creds}")
    else:
        env_content.append("GDRIVE_CREDENTIALS_FILE=gdrive_credentials.json")
        env_content.append("YOUTUBE_CREDENTIALS_FILE=youtube_credentials.json")
    
    # YouTube Settings
    print("\nYouTube Settings:")
    print("  Privacy options:")
    print("    1. private (only you can view)")
    print("    2. unlisted (anyone with link can view)")
    print("    3. public (searchable and public)")
    privacy_choice = input("  Choose (1-3) [default: 1]: ").strip() or "1"
    privacy_map = {"1": "private", "2": "unlisted", "3": "public"}
    privacy = privacy_map.get(privacy_choice, "private")
    env_content.append(f"YOUTUBE_PRIVACY={privacy}")
    
    # YouTube Category
    print("\n  Common YouTube categories:")
    print("    1. Film & Animation")
    print("    2. Autos & Vehicles")
    print("    10. Music")
    print("    22. People & Blogs (default)")
    print("    23. Comedy")
    print("    24. Entertainment")
    print("    25. News & Politics")
    print("    28. Science & Technology")
    category = input("  Enter category ID [default: 22]: ").strip() or "22"
    env_content.append(f"YOUTUBE_CATEGORY_ID={category}")
    
    # Default tags
    tags = input("  Default tags (comma-separated, optional): ").strip()
    if tags:
        env_content.append(f"YOUTUBE_DEFAULT_TAGS={tags}")
    
    # Notion Configuration
    print("\nNotion Integration:")
    use_notion = input("  Configure Notion integration? (y/N): ").strip().lower()
    if use_notion == 'y':
        print("\n  Steps to get Notion credentials:")
        print("  1. Go to https://www.notion.so/my-integrations")
        print("  2. Create new integration")
        print("  3. Copy the integration token")
        notion_token = input("  Enter Notion token: ").strip()
        if notion_token:
            env_content.append(f"NOTION_TOKEN={notion_token}")
            
            print("\n  4. Create a Notion database with these properties:")
            print("     - Title (Title)")
            print("     - File Size (Number)")
            print("     - Google Drive Link (URL)")
            print("     - YouTube URL (URL)")
            print("     - YouTube ID (Text)")
            print("     - Status (Select)")
            print("     - Upload Date (Date)")
            print("     - Error Message (Text)")
            print("  5. Share the database with your integration")
            print("  6. Copy the database ID from the URL")
            database_id = input("  Enter database ID: ").strip()
            if database_id:
                env_content.append(f"NOTION_DATABASE_ID={database_id}")
        env_content.append("SKIP_NOTION=false")
    else:
        env_content.append("SKIP_NOTION=true")
    
    # Processing Settings
    print("\nProcessing Settings:")
    delete_after = input("  Delete videos after upload? (Y/n): ").strip().lower()
    if delete_after == 'n':
        env_content.append("DELETE_AFTER_UPLOAD=false")
    else:
        env_content.append("DELETE_AFTER_UPLOAD=true")
    
    # Write .env file
    print("\n3. SAVING CONFIGURATION")
    print("-" * 40)
    
    with open('.env', 'w') as f:
        f.write("# Generated by setup wizard\n")
        f.write(f"# {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for line in env_content:
            f.write(line + "\n")
        
        # Add default values for other settings
        f.write("\n# Default settings (can be modified)\n")
        f.write("TEMP_DOWNLOAD_PATH=./temp_videos\n")
        f.write("PROCESSED_FILES_DB=./processed_files.json\n")
        f.write("LOG_FILE=./upload_log.txt\n")
        f.write("MAX_RETRIES=3\n")
        f.write("CHUNK_SIZE=52428800\n")
        f.write("LOG_LEVEL=INFO\n")
    
    print("✓ Created .env file")
    
    # Check for credential files
    print("\n4. CHECKING CREDENTIAL FILES")
    print("-" * 40)
    
    # Extract credential paths from env_content
    gdrive_creds = "gdrive_credentials.json"
    youtube_creds = "youtube_credentials.json"
    
    for line in env_content:
        if line.startswith("GDRIVE_CREDENTIALS_FILE="):
            gdrive_creds = line.split("=", 1)[1]
        elif line.startswith("YOUTUBE_CREDENTIALS_FILE="):
            youtube_creds = line.split("=", 1)[1]
    
    missing_files = []
    
    if os.path.exists(gdrive_creds):
        print(f"✓ {gdrive_creds} found")
    else:
        print(f"✗ {gdrive_creds} not found")
        missing_files.append(gdrive_creds)
    
    if os.path.exists(youtube_creds):
        print(f"✓ {youtube_creds} found")
    else:
        print(f"✗ {youtube_creds} not found")
        missing_files.append(youtube_creds)
    
    # Instructions for missing files
    if missing_files:
        print("\n5. NEXT STEPS")
        print("-" * 40)
        print("To get the missing credential files:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Select or create a project")
        print("3. Enable APIs:")
        print("   - Google Drive API")
        print("   - YouTube Data API v3")
        print("4. Create credentials:")
        print("   - Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
        print("   - Choose 'Desktop app'")
        print("   - Download the JSON file")
        print(f"5. Save the files as:")
        for file in missing_files:
            print(f"   - {file}")
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("\nTo start processing videos, run:")
    print("  python main.py")
    print("\nFor help and options:")
    print("  python main.py --help")
    print("=" * 60)

def check_requirements():
    """Check if all required packages are installed"""
    # Map package names to their import names
    required_packages = {
        'python-dotenv': 'dotenv',
        'google-api-python-client': 'googleapiclient',
        'google-auth-httplib2': 'google_auth_httplib2',
        'google-auth-oauthlib': 'google_auth_oauthlib',
        'requests': 'requests',
        'tqdm': 'tqdm'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("\n⚠️  Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall them with:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False
    
    return True