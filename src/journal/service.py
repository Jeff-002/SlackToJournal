"""
Journal service for coordinating content generation and formatting.

This module provides the main service that coordinates between
Slack data extraction, AI processing, and journal generation.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import time

from ..core.logging import get_logger
from ..core.exceptions import SlackToJournalError
from ..settings import AppSettings
from ..slack_integration.adapter import SlackAdapter
from ..ai_processing.service import AIProcessingService
from ..drive_integration.service import DriveService
from .schemas import (
    JournalEntry, JournalMetadata, JournalType, JournalFormat,
    TemplateConfig, ExportOptions, ProcessingResult
)
from .templates import JournalTemplates, MarkdownFormatter, HTMLFormatter


logger = get_logger(__name__)


class JournalService:
    """
    Main service orchestrating journal generation workflow.
    
    Coordinates Slack data extraction, AI processing, content formatting,
    and Drive upload to produce complete work journals.
    """
    
    def __init__(self, settings: AppSettings) -> None:
        """
        Initialize journal service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        
        # Initialize component services
        self.slack_service = SlackAdapter(settings.slack)
        self.ai_service = AIProcessingService(settings.gemini)
        self.drive_service = DriveService(settings.google_drive)
        
        logger.info("Initialized journal service with all components")
    
    async def generate_weekly_journal(
        self,
        target_date: Optional[datetime] = None,
        user_name: str = "Team Member",
        team_name: str = "Development Team",
        export_options: Optional[ExportOptions] = None
    ) -> ProcessingResult:
        """
        Generate a complete weekly work journal.
        
        Args:
            target_date: Target week date (defaults to current week)
            user_name: Name of the user
            team_name: Name of the team
            export_options: Export configuration
            
        Returns:
            ProcessingResult with journal entry and status
        """
        start_time = time.time()
        
        try:
            logger.info("Starting weekly journal generation")
            
            # Set default target date
            if target_date is None:
                target_date = datetime.now()
            
            # Calculate week boundaries
            week_start = target_date - timedelta(days=target_date.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            logger.info(f"Generating journal for week: {week_start.date()} to {week_end.date()}")
            
            # Step 1: Extract Slack messages
            messages = await self.slack_service.get_weekly_work_messages(
                target_date=target_date
            )
            
            if not messages:
                logger.warning("No work messages found for the specified week")
                return ProcessingResult(
                    success=False,
                    error_message="No work messages found for the specified week",
                    processing_time=time.time() - start_time,
                    messages_processed=0
                )
            
            logger.info(f"Retrieved {len(messages)} work messages from Slack")
            
            # Step 2: Process with AI
            from ..ai_processing.schemas import PromptContext
            
            context = PromptContext(
                user_name=user_name,
                role="Team Member",
                team=team_name,
                period_start=week_start,
                period_end=week_end,
                period_type="week"
            )
            
            # Convert messages to format expected by AI service
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    'user': getattr(msg, 'user', 'Unknown'),
                    'text': getattr(msg, 'text', ''),
                    'channel': getattr(msg, 'channel', 'general'),
                    'timestamp': getattr(msg, 'datetime', datetime.now()).isoformat() if hasattr(msg, 'datetime') else 'Unknown'
                })
            
            ai_response = await self.ai_service.generate_weekly_journal(
                messages=formatted_messages,
                context=context,
                include_trends=False
            )
            
            if not ai_response.success:
                logger.error(f"AI processing failed: {ai_response.error_message}")
                return ProcessingResult(
                    success=False,
                    error_message=f"AI processing failed: {ai_response.error_message}",
                    processing_time=time.time() - start_time,
                    messages_processed=len(messages)
                )
            
            logger.info("AI processing completed successfully")
            
            # Step 3: Format journal
            journal_entry = await self._create_journal_entry(
                ai_response=ai_response,
                week_start=week_start,
                week_end=week_end,
                user_name=user_name,
                team_name=team_name,
                messages_count=len(messages)
            )
            
            # Step 4: Export and upload
            export_results = {}
            if export_options is None:
                export_options = ExportOptions()
            
            if export_options.upload_to_drive:
                upload_result = await self.drive_service.upload_weekly_journal(
                    journal_content=journal_entry.content,
                    week_start_date=week_start,
                    format_type="markdown"
                )
                export_results['drive_upload'] = {
                    'success': upload_result.success,
                    'file_id': upload_result.file.id if upload_result.file else None,
                    'error': upload_result.error_message
                }
                
                if upload_result.success:
                    logger.info(f"Journal uploaded to Drive: {upload_result.file.web_view_link}")
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                success=True,
                journal_entry=journal_entry,
                processing_time=processing_time,
                messages_processed=len(messages),
                quality_score=ai_response.confidence_score,
                validation_passed=True,
                export_results=export_results,
                stats={
                    'ai_processing_time': ai_response.processing_time,
                    'tokens_used': ai_response.tokens_used,
                    'work_items_extracted': ai_response.work_items_extracted,
                    'projects_identified': ai_response.projects_identified
                }
            )
            
            logger.info(f"Weekly journal generation completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Journal generation failed: {str(e)}"
            logger.error(error_message)
            
            return ProcessingResult(
                success=False,
                error_message=error_message,
                processing_time=processing_time,
                messages_processed=0
            )
    
    async def generate_daily_summary(
        self,
        target_date: Optional[datetime] = None,
        user_name: str = "Team Member"
    ) -> ProcessingResult:
        """
        Generate a daily work summary.
        
        Args:
            target_date: Target date (defaults to today)
            user_name: Name of the user
            
        Returns:
            ProcessingResult with daily summary
        """
        start_time = time.time()
        
        try:
            if target_date is None:
                target_date = datetime.now()
            
            logger.info(f"Generating daily summary for {target_date.date()}")
            
            # Get daily messages (simplified - would need channel filtering)
            day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # For now, get weekly messages and filter (in production, implement daily filtering)
            weekly_messages = await self.slack_service.get_weekly_work_messages(target_date)
            
            # Filter messages for the specific day
            daily_messages = []
            for msg in weekly_messages:
                msg_date = getattr(msg, 'datetime', datetime.now()).date()
                if msg_date == target_date.date():
                    daily_messages.append({
                        'user': getattr(msg, 'user', 'Unknown'),
                        'text': getattr(msg, 'text', ''),
                        'channel': getattr(msg, 'channel', 'general'),
                        'timestamp': getattr(msg, 'datetime', datetime.now()).isoformat()
                    })
            
            if not daily_messages:
                return ProcessingResult(
                    success=False,
                    error_message="No messages found for the specified date",
                    processing_time=time.time() - start_time,
                    messages_processed=0
                )
            
            # Process with AI
            ai_response = await self.ai_service.generate_daily_summary(
                messages=daily_messages,
                date=target_date,
                user_name=user_name
            )
            
            if not ai_response.success:
                return ProcessingResult(
                    success=False,
                    error_message=f"AI processing failed: {ai_response.error_message}",
                    processing_time=time.time() - start_time,
                    messages_processed=len(daily_messages)
                )
            
            # Create simple daily summary entry
            metadata = JournalMetadata(
                title=f"每日工作總結 - {target_date.strftime('%Y-%m-%d')}",
                journal_type=JournalType.DAILY,
                period_start=day_start,
                period_end=day_end,
                author_name=user_name,
                total_messages=len(daily_messages),
                confidence_score=ai_response.confidence_score
            )
            
            journal_entry = JournalEntry(
                metadata=metadata,
                content=ai_response.raw_response or "無法生成日誌內容",
                format_type=JournalFormat.MARKDOWN
            )
            
            processing_time = time.time() - start_time
            
            # Upload daily summary
            if ai_response.raw_response:
                try:
                    summary_data = json.loads(ai_response.raw_response) if ai_response.raw_response.startswith('{') else {"summary": ai_response.raw_response}
                    await self.drive_service.upload_daily_summary(summary_data, target_date)
                except Exception as e:
                    logger.warning(f"Failed to upload daily summary: {e}")
            
            return ProcessingResult(
                success=True,
                journal_entry=journal_entry,
                processing_time=processing_time,
                messages_processed=len(daily_messages),
                quality_score=ai_response.confidence_score
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Daily summary generation failed: {str(e)}"
            logger.error(error_message)
            
            return ProcessingResult(
                success=False,
                error_message=error_message,
                processing_time=processing_time,
                messages_processed=0
            )
    
    async def _create_journal_entry(
        self,
        ai_response,
        week_start: datetime,
        week_end: datetime,
        user_name: str,
        team_name: str,
        messages_count: int
    ) -> JournalEntry:
        """
        Create formatted journal entry from AI response.
        
        Args:
            ai_response: AI processing response
            week_start: Week start date
            week_end: Week end date
            user_name: User name
            team_name: Team name
            messages_count: Number of processed messages
            
        Returns:
            Formatted journal entry
        """
        # Create metadata
        metadata = JournalMetadata(
            title=f"工作日誌 - {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}",
            journal_type=JournalType.WEEKLY,
            period_start=week_start,
            period_end=week_end,
            author_name=user_name,
            team=team_name,
            total_messages=messages_count,
            confidence_score=ai_response.confidence_score,
            completeness_score=ai_response.completeness_score,
            work_items_count=ai_response.work_items_extracted,
            projects_count=ai_response.projects_identified
        )
        
        # Format content
        if ai_response.journal_structure:
            # Use structured data to create formatted content
            journal_data = {
                'executive_summary': getattr(ai_response.journal_structure, 'executive_summary', '本週工作概況'),
                'key_highlights': getattr(ai_response.journal_structure, 'key_highlights', []),
                'projects': getattr(ai_response.journal_structure, 'projects', []),
                'work_by_category': getattr(ai_response.journal_structure, 'work_by_category', {}),
                'action_items': getattr(ai_response.journal_structure, 'action_items', []),
                'metrics': getattr(ai_response.journal_structure, 'metrics', {}),
                'learnings': getattr(ai_response.journal_structure, 'learnings', []),
                'challenges': getattr(ai_response.journal_structure, 'challenges', [])
            }
            
            # Get default template config
            template_config = JournalTemplates.get_default_config()
            
            # Render journal using template
            formatted_content = JournalTemplates.render_weekly_journal(
                journal_data=journal_data,
                metadata=metadata,
                config=template_config
            )
        else:
            # Fallback to raw response
            formatted_content = ai_response.raw_response or "無法生成結構化日誌內容"
        
        # Create journal entry
        journal_entry = JournalEntry(
            metadata=metadata,
            content=formatted_content,
            raw_content=ai_response.journal_structure.model_dump() if ai_response.journal_structure else None,
            format_type=JournalFormat.MARKDOWN,
            template_name="default_weekly"
        )
        
        return journal_entry
    
    async def get_recent_journals(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get recently generated journals from Drive.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of recent journal information
        """
        try:
            recent_files = await self.drive_service.get_recent_journals(days_back)
            
            journals = []
            for file in recent_files:
                journals.append({
                    'id': file.id,
                    'name': file.name,
                    'created_time': file.created_time,
                    'modified_time': file.modified_time,
                    'web_view_link': file.web_view_link,
                    'size': file.size
                })
            
            return journals
            
        except Exception as e:
            logger.error(f"Failed to get recent journals: {e}")
            return []
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all component services.
        
        Returns:
            Service status information
        """
        return {
            'slack_service': {
                'initialized': True,
                'settings': {
                    'server_url': self.settings.slack.mcp_server_url,
                    'workspace_id': self.settings.slack.workspace_id
                }
            },
            'ai_service': self.ai_service.get_processing_stats(),
            'drive_service': {
                'initialized': True,
                'settings': {
                    'folder_id': self.settings.google_drive.folder_id,
                    'credentials_file': str(self.settings.google_drive.credentials_file)
                }
            },
            'settings': {
                'app_name': self.settings.name,
                'version': self.settings.version,
                'debug': self.settings.debug
            }
        }