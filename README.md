# 🎥 Google Drive to YouTube Uploader

> **Automatically upload videos from Google Drive to YouTube with Notion tracking**

An automated tool that monitors a Google Drive folder for new videos and automatically uploads them to YouTube with customizable metadata, while tracking everything in Notion for easy management.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Google Drive API](https://img.shields.io/badge/Google_Drive-API_v3-green.svg)](https://developers.google.com/drive)
[![YouTube API](https://img.shields.io/badge/YouTube-Data_API_v3-red.svg)](https://developers.google.com/youtube)

## ✨ Features

- 🔄 **Automatic Monitoring**: Continuously monitors a Google Drive folder for new videos
- 📤 **YouTube Upload**: Automatically uploads videos to YouTube with customizable settings
- 📊 **Notion Integration**: Optional tracking of upload progress and video metadata in Notion
- 🔒 **Privacy Controls**: Configure video privacy (private, unlisted, public)
- 🏷️ **Smart Tagging**: Automatic and custom video tags
- 📁 **Flexible Input**: Accept both Google Drive folder IDs and full URLs
- 🔄 **Resume Support**: Handles interruptions and resumes where it left off
- 📝 **Comprehensive Logging**: Detailed logs for monitoring and debugging

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account
- YouTube account
- Notion account (optional)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/jimtin/how_to_automatically_upload_videos_to_youtube.git
cd how_to_automatically_upload_videos_to_youtube

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Credentials

#### Google Drive & YouTube API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Drive API
   - YouTube Data API v3
4. Create credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Desktop application"
   - Download the JSON file and save as `gdrive_credentials.json` and `youtube_credentials.json`

#### Notion Setup (Optional)

1. Go to [Notion Developers](https://developers.notion.com/)
2. Create a new integration
3. Copy the integration token
4. Create a database in Notion and share it with your integration

### 3. Configuration

Run the setup wizard for easy configuration:

```bash
python main.py --setup
```

Or manually create a `.env` file using `.env.template` as a reference:

```bash
cp .env.template .env
# Edit .env with your settings
```

#### Google Drive Folder Configuration

You can provide either:

- **Folder ID**: `1ABC123xyz`
- **Full URL**: `https://drive.google.com/drive/folders/1ABC123xyz`

The tool automatically extracts the folder ID from URLs, making setup easier!

### 4. Run the Uploader

```bash
python main.py
```

## 📖 Detailed Usage

### Command Line Options

```bash
python main.py [options]

Options:
  --setup              Run the interactive setup wizard
  --config             Show current configuration
  --check              Check configuration and requirements
  --folder FOLDER_ID   Override the default Google Drive folder
  --dry-run           Test mode - don't actually upload videos
  --skip-processed    Skip videos that have been processed before
  --help              Show help message
```

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `GDRIVE_FOLDER_ID` | Google Drive folder to monitor | Required |
| `YOUTUBE_PRIVACY` | Video privacy setting | `private` |
| `YOUTUBE_CATEGORY_ID` | YouTube category ID | `22` (People & Blogs) |
| `YOUTUBE_DEFAULT_TAGS` | Comma-separated default tags | None |
| `NOTION_TOKEN` | Notion integration token | Optional |
| `DELETE_AFTER_UPLOAD` | Delete local files after upload | `true` |
| `MAX_RETRIES` | Maximum upload retry attempts | `3` |

### Supported Video Formats

- `.mp4` (recommended)
- `.mov`
- `.avi`
- `.mkv`
- `.webm`
- `.flv`
- `.wmv`

## 🔧 Advanced Features

### Notion Integration

When configured, the tool creates and updates records in your Notion database with:

- Video title and description
- Upload status and progress
- File size and duration
- Upload timestamps
- Error messages (if any)

### Automatic Retry Logic

The uploader includes robust error handling:

- Network timeouts and connection issues
- API rate limiting
- Partial upload recovery
- Configurable retry attempts

### Logging and Monitoring

Comprehensive logging includes:

- Processing start/completion times
- Upload progress and status
- Error details and stack traces
- Configuration validation results

## 🛠️ Troubleshooting

### Common Issues

#### "File not found" errors

- Ensure your Google Drive folder ID is correct
- Check that the folder is accessible with your credentials
- Verify API permissions are properly configured

#### Upload failures

- Check your YouTube API quota limits
- Ensure video files meet YouTube's requirements
- Verify your OAuth tokens haven't expired

#### Authentication issues

- Delete existing token files (`*.pickle`) and re-authenticate
- Ensure your OAuth client is configured for "Desktop application"
- Check that required APIs are enabled in Google Cloud Console

### Getting Help

1. Check the logs in `upload_log.txt`
2. Run with `--check` to validate your configuration
3. Use `--dry-run` to test without uploading
4. Check the [Issues](https://github.com/jimtin/how_to_automatically_upload_videos_to_youtube/issues) page

## 📚 Related Resources

### 📺 YouTube Tutorials

Coming Soon - Links will be added when videos are published

### 📝 Blog Posts

Coming Soon - Links will be added when articles are published

### 🔗 Additional Resources

- [Google Drive API Documentation](https://developers.google.com/drive)
- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [Notion API Documentation](https://developers.notion.com/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support

If this tool helps you automate your video uploads, please consider giving it a star! ⭐

---

Made with ❤️ for content creators who want to automate their workflow
