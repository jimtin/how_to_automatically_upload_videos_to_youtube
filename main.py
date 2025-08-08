#!/usr/bin/env python3
"""
Google Drive to YouTube Uploader with Notion Tracking
Main entry point for the application
"""

import os
import sys
import logging
import argparse
from typing import List

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG, validate_environment, check_configuration, print_configuration
from processor import VideoProcessor
from tracker import ProcessedFilesTracker
from setup import setup_wizard, check_requirements
from models import VideoFile

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging for the application"""
    log_level = getattr(logging, CONFIG["LOG_LEVEL"], logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(CONFIG["LOG_FILE"])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG["LOG_FILE"]),
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers to WARNING to reduce noise
    logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_list(args):
    """Handle list command"""
    processor = VideoProcessor()
    videos = processor.list_videos(args.folder)
    
    if not videos:
        print("No videos found in the specified folder")
        return
    
    print(f"\nFound {len(videos)} video(s):")
    print("-" * 60)
    
    for video in videos:
        status_icon = {
            "success": "✓",
            "failed": "✗",
            "pending": "○"
        }.get(video.upload_status, "?")
        
        print(f"{status_icon} {video.name}")
        print(f"  Size: {VideoFile.format_size(video.size)}")
        
        if video.upload_status == "success" and video.youtube_url:
            print(f"  YouTube: {video.youtube_url}")
        elif video.upload_status == "failed":
            print(f"  Status: Failed")
        elif video.upload_status == "pending":
            print(f"  Status: Not processed")

def handle_stats(args):
    """Handle stats command"""
    tracker = ProcessedFilesTracker()
    stats = tracker.get_statistics()
    
    print("\n" + "=" * 60)
    print("PROCESSING STATISTICS")
    print("=" * 60)
    print(f"Total processed: {stats['total_processed']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Pending: {stats['pending']}")
    print(f"Total size: {stats['total_size_formatted']}")
    
    if args.failed:
        failed = tracker.list_failed()
        if failed:
            print("\nFailed uploads:")
            print("-" * 40)
            for item in failed:
                print(f"• {item['name']}")
                if item['error']:
                    print(f"  Error: {item['error'][:100]}...")
                print(f"  Date: {item['date']}")

def handle_retry(args):
    """Handle retry command"""
    processor = VideoProcessor()
    processor.retry_failed()

def handle_clear(args):
    """Handle clear command"""
    tracker = ProcessedFilesTracker()
    
    if args.failed:
        tracker.clear_failed()
        print("Cleared failed entries from database")
    elif args.all:
        confirm = input("Are you sure you want to clear ALL processed files? (yes/no): ")
        if confirm.lower() == 'yes':
            # Clear the entire database
            with open(CONFIG["PROCESSED_FILES_DB"], 'w') as f:
                f.write("{}")
            print("Cleared all entries from database")
        else:
            print("Operation cancelled")
    else:
        print("Please specify --failed or --all")

def handle_export(args):
    """Handle export command"""
    tracker = ProcessedFilesTracker()
    output_file = args.output or "processed_files.csv"
    tracker.export_to_csv(output_file)
    print(f"Exported to {output_file}")

def handle_validate(args):
    """Handle validate command"""
    errors, warnings = validate_environment()
    
    print("\n" + "=" * 60)
    print("ENVIRONMENT VALIDATION")
    print("=" * 60)
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("\n✅ All environment variables are properly configured!")
    
    if args.verbose:
        print_configuration()
    
    print("=" * 60)
    
    return len(errors) == 0

def handle_process(args):
    """Handle process command (default)"""
    # Check configuration
    if not check_configuration():
        sys.exit(1)
    
    # Override dry run from command line
    if args.dry_run:
        CONFIG["DRY_RUN"] = True
    
    # Create processor and run
    processor = VideoProcessor()
    processor.process_videos(
        folder_id=args.folder,
        skip_processed=not args.reprocess,
        video_filter=args.filter
    )

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    # Check for required packages first
    if not check_requirements():
        sys.exit(1)
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Upload videos from Google Drive to YouTube with Notion tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Process videos from configured folder
  %(prog)s --dry-run          # Show what would be processed without uploading
  %(prog)s --folder FOLDER_ID # Process specific folder
  %(prog)s --filter "vacation" # Process only videos containing "vacation"
  %(prog)s list               # List all videos in folder
  %(prog)s stats              # Show processing statistics
  %(prog)s retry              # Retry failed uploads
  %(prog)s --setup            # Run setup wizard
        """
    )
    
    # Global options
    parser.add_argument('--setup', action='store_true',
                       help='Run interactive setup wizard')
    parser.add_argument('--validate', action='store_true',
                       help='Validate environment configuration')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    
    # Add arguments for default process command
    parser.add_argument('--folder', type=str,
                       help='Google Drive folder ID to process')
    parser.add_argument('--reprocess', action='store_true',
                       help='Reprocess already uploaded videos')
    parser.add_argument('--dry-run', action='store_true',
                       help='List videos without processing')
    parser.add_argument('--filter', type=str,
                       help='Filter videos by name (substring match)')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List videos in folder')
    list_parser.add_argument('--folder', type=str,
                            help='Google Drive folder ID')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show processing statistics')
    stats_parser.add_argument('--failed', action='store_true',
                             help='Show details of failed uploads')
    
    # Retry command
    retry_parser = subparsers.add_parser('retry', help='Retry failed uploads')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear processed files database')
    clear_group = clear_parser.add_mutually_exclusive_group(required=True)
    clear_group.add_argument('--failed', action='store_true',
                            help='Clear only failed entries')
    clear_group.add_argument('--all', action='store_true',
                            help='Clear all entries')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export database to CSV')
    export_parser.add_argument('--output', type=str,
                              help='Output CSV file (default: processed_files.csv)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle setup wizard
    if args.setup:
        setup_wizard()
        return
    
    # Handle validation
    if args.validate:
        success = handle_validate(args)
        sys.exit(0 if success else 1)
    
    # Setup logging
    logger = setup_logging()
    
    # Log startup
    logger.info("=" * 60)
    logger.info("Google Drive to YouTube Uploader")
    logger.info("=" * 60)
    
    try:
        # Handle commands
        if args.command == 'list':
            handle_list(args)
        elif args.command == 'stats':
            handle_stats(args)
        elif args.command == 'retry':
            handle_retry(args)
        elif args.command == 'clear':
            handle_clear(args)
        elif args.command == 'export':
            handle_export(args)
        else:
            # Default to process command
            handle_process(args)
            
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        sys.exit(1)

if __name__ == "__main__":
    main()