"""
Main application entry point for SlackToJournal.

This module provides the main application interface and CLI commands
for generating work journals from Slack messages.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import click

from .core.logging import setup_logging, get_logger
from .core.exceptions import SlackToJournalError
from .settings import get_settings
from .journal.service import JournalService


# Setup logging
settings = get_settings()
setup_logging(settings.logging, "slack_to_journal")
logger = get_logger(__name__)


@click.group()
@click.version_option(version=settings.version)
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
def cli(config: Optional[str], debug: bool):
    """SlackToJournal - AI-powered work journal generator from Slack messages."""
    if debug:
        settings.debug = True
        logger.info("Debug mode enabled")
    
    if config:
        logger.info(f"Using configuration file: {config}")


@cli.command()
@click.option('--date', '-d', type=click.DateTime(formats=['%Y-%m-%d']), 
              help='Target week date (default: current week)')
@click.option('--user', '-u', default='Team Member', help='User name')
@click.option('--team', '-t', default='Development Team', help='Team name')
@click.option('--upload/--no-upload', default=True, help='Upload to Google Drive')
def weekly(date: Optional[datetime], user: str, team: str, upload: bool):
    """Generate weekly work journal."""
    asyncio.run(generate_weekly_journal(date, user, team, upload))


@cli.command()
@click.option('--date', '-d', type=click.DateTime(formats=['%Y-%m-%d']), 
              help='Target date (default: today)')
@click.option('--user', '-u', default='Team Member', help='User name')
def daily(date: Optional[datetime], user: str):
    """Generate daily work summary."""
    asyncio.run(generate_daily_summary(date, user))


@cli.command()
def status():
    """Show system status and service health."""
    asyncio.run(show_status())


@cli.command()
@click.option('--days', '-d', default=30, help='Number of days to look back')
def recent(days: int):
    """Show recent journal entries."""
    asyncio.run(show_recent_journals(days))


@cli.command()
def setup():
    """Run initial setup and configuration."""
    asyncio.run(run_setup())


@cli.command()
@click.option('--test-slack', is_flag=True, help='Test Slack connection')
@click.option('--test-ai', is_flag=True, help='Test AI processing')
@click.option('--test-drive', is_flag=True, help='Test Google Drive connection')
@click.option('--test-all', is_flag=True, help='Test all connections')
def test(test_slack: bool, test_ai: bool, test_drive: bool, test_all: bool):
    """Test system components."""
    asyncio.run(run_tests(test_slack, test_ai, test_drive, test_all))


async def generate_weekly_journal(
    target_date: Optional[datetime],
    user_name: str,
    team_name: str,
    upload_to_drive: bool
):
    """Generate weekly work journal."""
    try:
        click.echo("🚀 Starting weekly journal generation...")
        
        # Initialize journal service
        journal_service = JournalService(settings)
        
        # Set up export options
        from .journal.schemas import ExportOptions
        export_options = ExportOptions(upload_to_drive=upload_to_drive)
        
        # If no Google credentials, disable Drive upload
        if upload_to_drive and not settings.google_drive.credentials_file.exists():
            click.echo("⚠️  Google credentials not found, saving locally instead...")
            export_options.upload_to_drive = False
        
        # Generate journal
        result = await journal_service.generate_weekly_journal(
            target_date=target_date,
            user_name=user_name,
            team_name=team_name,
            export_options=export_options
        )
        
        if result.success:
            click.echo("✅ Weekly journal generated successfully!")
            
            # Show summary
            journal = result.journal_entry
            click.echo(f"\n📊 Summary:")
            click.echo(f"  • Period: {journal.metadata.period_start.date()} to {journal.metadata.period_end.date()}")
            click.echo(f"  • Messages processed: {result.messages_processed}")
            click.echo(f"  • Work items extracted: {journal.metadata.work_items_count}")
            click.echo(f"  • Projects identified: {journal.metadata.projects_count}")
            click.echo(f"  • Quality score: {journal.metadata.confidence_score:.1%}")
            click.echo(f"  • Processing time: {result.processing_time:.2f}s")
            
            # Show export results
            if result.export_results.get('drive_upload'):
                drive_result = result.export_results['drive_upload']
                if drive_result['success']:
                    click.echo(f"  • ☁️  Uploaded to Google Drive: {drive_result['file_id']}")
                else:
                    click.echo(f"  • ❌ Drive upload failed: {drive_result['error']}")
            
            # Show local file results
            if result.export_results.get('local_file'):
                local_result = result.export_results['local_file']
                if local_result['success']:
                    click.echo(f"  • 📁 Saved locally: {local_result['file_name']}")
                    click.echo(f"  • 📍 File path: {local_result['file_path']}")
                    click.echo(f"  • 📊 File size: {local_result['file_size']} bytes")
                else:
                    click.echo(f"  • ❌ Local save failed: {local_result['error']}")
            
            # Show content preview
            click.echo(f"\n📝 Content preview:")
            preview = journal.content[:500] + "..." if len(journal.content) > 500 else journal.content
            click.echo(preview)
            
        else:
            click.echo(f"❌ Journal generation failed: {result.error_message}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Weekly journal generation failed: {e}")
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)


async def generate_daily_summary(target_date: Optional[datetime], user_name: str):
    """Generate daily work summary."""
    try:
        click.echo("📅 Starting daily summary generation...")
        
        if target_date is None:
            target_date = datetime.now()
        
        # Initialize journal service
        journal_service = JournalService(settings)
        
        # Generate summary
        result = await journal_service.generate_daily_summary(
            target_date=target_date,
            user_name=user_name
        )
        
        if result.success:
            click.echo("✅ Daily summary generated successfully!")
            
            journal = result.journal_entry
            click.echo(f"\n📊 Summary for {target_date.date()}:")
            click.echo(f"  • Messages processed: {result.messages_processed}")
            click.echo(f"  • Quality score: {journal.metadata.confidence_score:.1%}")
            click.echo(f"  • Processing time: {result.processing_time:.2f}s")
            
            # Show content
            click.echo(f"\n📝 Daily Summary:")
            click.echo(journal.content)
            
        else:
            click.echo(f"❌ Daily summary generation failed: {result.error_message}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Daily summary generation failed: {e}")
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)


async def show_status():
    """Show system status."""
    try:
        click.echo("🔍 Checking system status...")
        
        # Initialize journal service
        journal_service = JournalService(settings)
        
        # Get service status
        status = journal_service.get_service_status()
        
        click.echo("\n📊 System Status:")
        click.echo(f"  • Application: {status['settings']['app_name']} v{status['settings']['version']}")
        click.echo(f"  • Debug mode: {'Enabled' if status['settings']['debug'] else 'Disabled'}")
        
        click.echo("\n🔧 Service Status:")
        
        # Slack service
        slack_status = status['slack_service']
        click.echo(f"  • Slack Integration: {'✅ Ready' if slack_status['initialized'] else '❌ Not Ready'}")
        if slack_status['settings']['workspace_id']:
            click.echo(f"    - Workspace: {slack_status['settings']['workspace_id']}")
        
        # AI service
        ai_status = status['ai_service']
        model_info = ai_status.get('model_info', {})
        click.echo(f"  • AI Processing: {'✅ Ready' if model_info.get('api_key_configured') else '❌ Not Ready'}")
        click.echo(f"    - Model: {model_info.get('model_name', 'Unknown')}")
        click.echo(f"    - Temperature: {model_info.get('temperature', 'Unknown')}")
        
        # Drive service
        drive_status = status['drive_service']
        click.echo(f"  • Google Drive: {'✅ Ready' if drive_status['initialized'] else '❌ Not Ready'}")
        if drive_status['settings']['folder_id']:
            click.echo(f"    - Folder ID: {drive_status['settings']['folder_id']}")
        
        click.echo("\n✅ Status check completed")
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)


async def show_recent_journals(days_back: int):
    """Show recent journal entries."""
    try:
        click.echo(f"📚 Fetching recent journals (last {days_back} days)...")
        
        # Initialize journal service
        journal_service = JournalService(settings)
        
        # Get recent journals
        journals = await journal_service.get_recent_journals(days_back)
        
        if not journals:
            click.echo("📭 No recent journals found")
            return
        
        click.echo(f"\n📋 Recent Journals ({len(journals)} found):")
        
        for journal in journals:
            created_date = journal['created_time'].strftime('%Y-%m-%d %H:%M') if journal['created_time'] else 'Unknown'
            size_mb = int(journal['size']) / (1024*1024) if journal['size'] and journal['size'].isdigit() else 0
            
            click.echo(f"\n  📄 {journal['name']}")
            click.echo(f"     Created: {created_date}")
            click.echo(f"     Size: {size_mb:.1f} MB")
            if journal['web_view_link']:
                click.echo(f"     Link: {journal['web_view_link']}")
        
    except Exception as e:
        logger.error(f"Failed to fetch recent journals: {e}")
        click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)


async def run_setup():
    """Run initial setup."""
    click.echo("🔧 Starting SlackToJournal setup...")
    
    # Check configuration
    click.echo("\n1️⃣  Checking configuration...")
    click.echo(f"   • Config file: {Path('configs/settings.yaml').absolute()}")
    click.echo(f"   • Environment file: {Path('.env').absolute()}")
    
    # Check credentials
    click.echo("\n2️⃣  Checking credentials...")
    
    if not settings.gemini.api_key:
        click.echo("   ⚠️  Gemini API key not configured")
        click.echo("   Please set GEMINI_API_KEY environment variable")
    else:
        click.echo("   ✅ Gemini API key configured")
    
    if not settings.google_drive.credentials_file.exists():
        click.echo("   ⚠️  Google credentials file not found")
        click.echo(f"   Please place credentials at: {settings.google_drive.credentials_file}")
    else:
        click.echo("   ✅ Google credentials file found")
    
    if not settings.slack.workspace_id:
        click.echo("   ⚠️  Slack workspace ID not configured")
        click.echo("   Please set SLACK_WORKSPACE_ID environment variable")
    else:
        click.echo("   ✅ Slack workspace ID configured")
    
    # Setup directories
    click.echo("\n3️⃣  Setting up directories...")
    
    dirs_to_create = [
        Path("logs"),
        Path("configs/credentials"),
        Path("backups")
    ]
    
    for dir_path in dirs_to_create:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            click.echo(f"   ✅ Created directory: {dir_path}")
        else:
            click.echo(f"   ✓ Directory exists: {dir_path}")
    
    click.echo("\n✅ Setup completed!")
    click.echo("\nNext steps:")
    click.echo("1. Configure your API keys in .env file")
    click.echo("2. Place Google credentials in configs/credentials/")
    click.echo("3. Run 'slack-to-journal test --test-all' to verify setup")
    click.echo("4. Run 'slack-to-journal weekly' to generate your first journal")


async def run_tests(test_slack: bool, test_ai: bool, test_drive: bool, test_all: bool):
    """Run system tests."""
    click.echo("🧪 Running system tests...")
    
    if test_all:
        test_slack = test_ai = test_drive = True
    
    if not any([test_slack, test_ai, test_drive]):
        click.echo("Please specify which tests to run (--test-all, --test-slack, --test-ai, --test-drive)")
        return
    
    # Test AI processing
    if test_ai:
        click.echo("\n🤖 Testing AI processing...")
        try:
            from .ai_processing.service import AIProcessingService
            ai_service = AIProcessingService(settings.gemini)
            
            # Simple test with dummy data
            test_messages = [
                {
                    'user': 'test_user',
                    'text': 'Completed the user authentication feature',
                    'channel': 'dev-team',
                    'timestamp': datetime.now().isoformat()
                }
            ]
            
            from .ai_processing.schemas import PromptContext
            context = PromptContext(
                user_name="Test User",
                period_start=datetime.now() - timedelta(days=7),
                period_end=datetime.now()
            )
            
            response = await ai_service.generate_daily_summary(test_messages, datetime.now(), "Test User")
            
            if response.success:
                click.echo("   ✅ AI processing test passed")
            else:
                click.echo(f"   ❌ AI processing test failed: {response.error_message}")
                
        except Exception as e:
            click.echo(f"   ❌ AI test error: {str(e)}")
    
    # Test Google Drive (simplified)
    if test_drive:
        click.echo("\n☁️  Testing Google Drive...")
        try:
            from .drive_integration.auth import DriveAuthenticator
            auth = DriveAuthenticator(settings.google_drive)
            
            # Test authentication
            test_result = auth.test_authentication()
            
            if test_result['success']:
                click.echo("   ✅ Google Drive authentication test passed")
                click.echo(f"   📧 User: {test_result.get('user_email', 'Unknown')}")
            else:
                click.echo("   ❌ Google Drive authentication test failed")
                
        except Exception as e:
            click.echo(f"   ❌ Drive test error: {str(e)}")
    
    # Test Slack (basic connectivity test)
    if test_slack:
        click.echo("\n💬 Testing Slack connectivity...")
        try:
            from .slack_integration.client import SlackMCPClient
            slack_client = SlackMCPClient(settings.slack)
            
            # Simple connectivity test
            click.echo(f"   🔗 MCP Server URL: {settings.slack.mcp_server_url}")
            click.echo(f"   🏢 Workspace ID: {settings.slack.workspace_id}")
            click.echo("   ✅ Slack configuration loaded")
            
        except Exception as e:
            click.echo(f"   ❌ Slack test error: {str(e)}")
    
    click.echo("\n✅ Tests completed!")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        click.echo(f"❌ Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()