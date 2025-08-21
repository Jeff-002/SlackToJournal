#!/usr/bin/env python3
"""
Local test script for SlackToJournal without Google Drive.

This script tests the journal generation functionality
using only Slack and AI processing, saving results locally.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from src.settings import get_settings
from src.core.logging import setup_logging, get_logger
from src.journal.service import JournalService
from src.journal.schemas import ExportOptions


async def test_local_generation():
    """Test journal generation with local file output."""
    
    # Setup logging
    settings = get_settings()
    setup_logging(settings.logging, "test")
    logger = get_logger(__name__)
    
    print("🧪 Testing SlackToJournal Local Generation")
    print("=" * 50)
    
    # Check configuration
    print("📋 Checking configuration...")
    
    # Check Slack configuration
    slack_bot_token = None
    try:
        import os
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        if slack_bot_token:
            print(f"✅ Slack Bot Token configured")
        else:
            print("❌ SLACK_BOT_TOKEN not found in environment")
            return False
    except Exception as e:
        print(f"❌ Slack config error: {e}")
        return False
    
    # Check Gemini API key
    if settings.gemini.api_key:
        print(f"✅ Gemini API key configured")
    else:
        print("❌ GEMINI_API_KEY not configured")
        return False
    
    # Google Drive status (optional)
    if settings.google_drive.credentials_file.exists():
        print("ℹ️  Google Drive credentials found (will try Drive upload)")
    else:
        print("ℹ️  Google Drive credentials not found (will save locally)")
    
    print("\n🚀 Starting journal generation...")
    
    try:
        # Initialize journal service
        journal_service = JournalService(settings)
        
        # Set up export options for local save
        export_options = ExportOptions(
            upload_to_drive=False,  # Force local save for testing
            output_directory="journals"
        )
        
        # Generate weekly journal
        result = await journal_service.generate_weekly_journal(
            target_date=datetime.now(),
            user_name="Test User",
            team_name="Test Team",
            export_options=export_options
        )
        
        # Show results
        if result.success:
            print("✅ Journal generation successful!")
            
            journal = result.journal_entry
            print(f"\n📊 Results:")
            print(f"  • Period: {journal.metadata.period_start.date()} to {journal.metadata.period_end.date()}")
            print(f"  • Messages processed: {result.messages_processed}")
            print(f"  • Work items: {journal.metadata.work_items_count}")
            print(f"  • Projects: {journal.metadata.projects_count}")
            print(f"  • Processing time: {result.processing_time:.2f}s")
            print(f"  • Quality score: {journal.metadata.confidence_score:.1%}")
            
            # File information
            if result.export_results.get('local_file'):
                local_result = result.export_results['local_file']
                if local_result['success']:
                    print(f"\n📁 File saved:")
                    print(f"  • Filename: {local_result['file_name']}")
                    print(f"  • Path: {local_result['file_path']}")
                    print(f"  • Size: {local_result['file_size']} bytes")
                    
                    # Show content preview
                    try:
                        file_path = Path(local_result['file_path'])
                        if file_path.exists():
                            content = file_path.read_text(encoding='utf-8')
                            print(f"\n📝 Content preview (first 300 characters):")
                            print(content[:300] + "..." if len(content) > 300 else content)
                    except Exception as e:
                        print(f"⚠️  Could not preview file: {e}")
                else:
                    print(f"❌ File save failed: {local_result.get('error')}")
            
            return True
            
        else:
            print(f"❌ Journal generation failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False


def main():
    """Main test function."""
    try:
        success = asyncio.run(test_local_generation())
        
        if success:
            print("\n🎉 Test completed successfully!")
            print("\nNext steps:")
            print("1. Check the generated file in the 'journals' directory")
            print("2. Run 'uv run python -m src.main weekly' for normal usage")
            print("3. Set up Google Drive credentials for cloud storage")
        else:
            print("\n❌ Test failed. Please check your configuration.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()