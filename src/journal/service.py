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
        team_name: str = "Development Team",
        export_options: Optional[ExportOptions] = None,
        user_email: Optional[str] = None,
        filter_user_name: Optional[str] = None
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
            
            # Calculate work week boundaries (Monday to Friday only)
            week_start = target_date - timedelta(days=target_date.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=4, hours=23, minutes=59, seconds=59)
            
            logger.info(f"Generating journal for week: {week_start.date()} to {week_end.date()}")
            
            # Step 1: Extract Slack messages
            messages = await self.slack_service.get_weekly_work_messages(
                target_date=target_date,
                user_email=user_email,
                user_name=filter_user_name
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
                user_name=filter_user_name or "Team Member",
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
                    'user_name': getattr(msg, 'user_name', None),
                    'user_real_name': getattr(msg, 'user_real_name', None),
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
                user_name=filter_user_name or "Team Member",
                team_name=team_name,
                messages_count=len(messages)
            )
            
            # Step 4: Export and upload
            export_results = {}
            if export_options is None:
                export_options = ExportOptions()
            
            # Try Google Drive upload, fallback to local file
            if export_options.upload_to_drive:
                try:
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
                    else:
                        logger.warning(f"Drive upload failed: {upload_result.error_message}")
                        # Fallback to local file
                        local_file = self._save_journal_locally(journal_entry, week_start)
                        export_results['local_file'] = local_file
                        
                except Exception as e:
                    logger.warning(f"Drive service unavailable: {e}")
                    # Fallback to local file
                    local_file = self._save_journal_locally(journal_entry, week_start)
                    export_results['local_file'] = local_file
            else:
                # Save locally by default
                local_file = self._save_journal_locally(journal_entry, week_start)
                export_results['local_file'] = local_file
            
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
        upload_to_drive: bool = True,
        user_email: Optional[str] = None,
        filter_user_name: Optional[str] = None
    ) -> ProcessingResult:
        """
        Generate a daily work summary.
        
        Args:
            target_date: Target date (defaults to today)
            user_name: Name of the user
            upload_to_drive: Whether to upload to Google Drive
            
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
            weekly_messages = await self.slack_service.get_weekly_work_messages(target_date, user_email=user_email, user_name=filter_user_name)
            
            # Filter messages for the specific day
            daily_messages = []
            for msg in weekly_messages:
                msg_date = getattr(msg, 'datetime', datetime.now()).date()
                if msg_date == target_date.date():
                    daily_messages.append({
                        'user': getattr(msg, 'user', 'Unknown'),
                        'user_name': getattr(msg, 'user_name', None),
                        'user_real_name': getattr(msg, 'user_real_name', None),
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
            
            # Determine if we should include user names in output
            # Include names if no specific user filter was provided
            include_user_names = not (user_email or filter_user_name)
            user_display_name = filter_user_name or "Team Member"
            
            # Process with AI
            ai_response = await self.ai_service.generate_daily_summary(
                messages=daily_messages,
                date=target_date,
                user_name=user_display_name,
                include_user_names=include_user_names
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
                author_name=filter_user_name or "Team Member",
                total_messages=len(daily_messages),
                confidence_score=ai_response.confidence_score
            )
            
            # Post-process AI response to enhance status labels
            processed_content = self._enhance_status_labels(ai_response.raw_response or "無法生成日誌內容")
            
            journal_entry = JournalEntry(
                metadata=metadata,
                content=processed_content,
                format_type=JournalFormat.MARKDOWN
            )
            
            processing_time = time.time() - start_time
            
            # Export results
            export_results = {}
            
            # Upload to Drive if requested
            if upload_to_drive and ai_response.raw_response:
                try:
                    summary_data = json.loads(ai_response.raw_response) if ai_response.raw_response.startswith('{') else {"summary": ai_response.raw_response}
                    upload_result = await self.drive_service.upload_daily_summary(summary_data, target_date)
                    export_results['drive_upload'] = {'success': True, 'result': upload_result}
                except Exception as e:
                    logger.warning(f"Failed to upload daily summary: {e}")
                    export_results['drive_upload'] = {'success': False, 'error': str(e)}
            
            # Always save locally (like weekly journal)
            if ai_response.raw_response:
                local_file = self._save_daily_summary_locally(journal_entry, target_date)
                export_results['local_file'] = local_file
            
            return ProcessingResult(
                success=True,
                journal_entry=journal_entry,
                processing_time=processing_time,
                messages_processed=len(daily_messages),
                quality_score=ai_response.confidence_score,
                export_results=export_results
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
        
        # Format content using simple format
        if ai_response.raw_response:
            try:
                # Post-process AI response to enhance status labels
                processed_content = self._enhance_status_labels(ai_response.raw_response)
                
                # Use simple text format directly
                formatted_content = f"""# 工作日誌_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}

**期間**: {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}  
**生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

## 工作內容

{processed_content}

---
*共處理 {messages_count} 條訊息*
"""
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}")
                # Post-process fallback content as well
                processed_fallback = self._enhance_status_labels(ai_response.raw_response)
                formatted_content = f"""# 工作日誌_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}

**期間**: {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}  
**生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

{processed_fallback}

---
*共處理 {messages_count} 條訊息*
"""
        else:
            # Fallback content
            formatted_content = f"""# 工作日誌_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}

**期間**: {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}  
**生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

本期間沒有檢測到工作相關討論。

---
*共處理 {messages_count} 條訊息*
"""
        
        # Create journal entry
        journal_entry = JournalEntry(
            metadata=metadata,
            content=formatted_content,
            raw_content=ai_response.journal_structure.model_dump() if ai_response.journal_structure else None,
            format_type=JournalFormat.MARKDOWN,
            template_name="default_weekly"
        )
        
        return journal_entry
    
    def _save_journal_locally(
        self, 
        journal_entry: JournalEntry, 
        week_start: datetime
    ) -> Dict[str, Any]:
        """
        Save journal entry to local file.
        
        Args:
            journal_entry: Journal entry to save
            week_start: Week start date for filename
            
        Returns:
            Dictionary with local file information
        """
        from pathlib import Path
        
        try:
            # Create output directory
            output_dir = Path("journals")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename with work week dates (Monday to Friday)
            week_end_filename = week_start + timedelta(days=4)  # Friday
            filename = f"工作日誌_{week_start.strftime('%Y%m%d')}_{week_end_filename.strftime('%Y%m%d')}.md"
            file_path = output_dir / filename
            
            # Write journal content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(journal_entry.content)
            
            # Update journal entry with file info
            journal_entry.file_name = filename
            journal_entry.file_path = str(file_path.absolute())
            journal_entry.file_size = file_path.stat().st_size
            
            logger.info(f"Journal saved locally: {file_path}")
            
            return {
                'success': True,
                'file_path': str(file_path.absolute()),
                'file_name': filename,
                'file_size': file_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to save journal locally: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_daily_summary_locally(
        self, 
        journal_entry: JournalEntry, 
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        Save daily summary to local file.
        
        Args:
            journal_entry: Journal entry to save
            target_date: Target date for filename
            
        Returns:
            Dictionary with local file information
        """
        from pathlib import Path
        
        try:
            # Create output directory
            output_dir = Path("journals")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename for daily summary
            filename = f"工作日誌_{target_date.strftime('%Y%m%d')}.md"
            file_path = output_dir / filename
            
            # Create formatted content for daily summary
            formatted_content = f"""# 工作日誌_{target_date.strftime('%Y%m%d')}

**日期**: {target_date.strftime('%Y-%m-%d')}  
**生成**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

## 工作內容

{journal_entry.content}

---
*每日摘要由 SlackToJournal 自動生成*
"""
            
            # Write journal content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            # Update journal entry with file info
            journal_entry.file_name = filename
            journal_entry.file_path = str(file_path.absolute())
            journal_entry.file_size = file_path.stat().st_size
            
            logger.info(f"Daily summary saved locally: {file_path}")
            
            return {
                'success': True,
                'file_path': str(file_path.absolute()),
                'file_name': filename,
                'file_size': file_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to save daily summary locally: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
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
                'settings': self.slack_service.get_integration_info()
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
    
    def _enhance_status_labels(self, content: str) -> str:
        """
        Enhanced status labels in journal content with highlighting and better formatting.
        
        Args:
            content: Raw AI generated content
            
        Returns:
            Enhanced content with improved status labels
        """
        if not content:
            return content
        
        # Enhanced label patterns and replacements
        import re
        
        # Pattern to match existing AI-generated status labels
        # Matches: MM/DD `status` description, MM/DD **status** description or MM/DD [status] description
        # Also matches lines that don't have any status labels yet
        label_pattern = r'^(\d{1,2}/\d{1,2})\s+(?:`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\])?(.+)$'
        
        lines = content.split('\n')
        enhanced_lines = []
        
        for line in lines:
            # Skip empty lines, headers, and non-work items
            if not line.strip() or line.startswith('#') or line.startswith('```') or line.startswith('本'):
                enhanced_lines.append(line)
                continue
                
            # Check if line matches work item pattern
            match = re.match(label_pattern, line, re.MULTILINE)
            
            if match:
                date = match.group(1)
                status1 = match.group(2)  # From `status` format
                status2 = match.group(3)  # From **status** format
                status3 = match.group(4)  # From [status] format
                description = match.group(5).strip()
                
                # Use whichever status was captured, or empty string if none
                existing_status = (status1 or status2 or status3 or "").strip()
                
                # Use existing status if it exists, otherwise determine from description
                if existing_status:
                    # Keep the existing status that was correctly determined
                    enhanced_status = f"`{existing_status}` "
                else:
                    # Determine status from description content  
                    enhanced_status = self._determine_enhanced_status("", description)
                
                # Remove existing </br> if present and add new one
                description_clean = description.replace('</br>', '').strip()
                
                # Format enhanced line with </br> at the end
                enhanced_line = f"{date} {enhanced_status}{description_clean}</br>"
                enhanced_lines.append(enhanced_line)
            else:
                # Check if it's a work item without proper format
                # Pattern for simple date-based lines: MM/DD description
                simple_pattern = r'^(\d{1,2}/\d{1,2})\s+(.+)$'
                simple_match = re.match(simple_pattern, line)
                
                if simple_match:
                    date = simple_match.group(1)
                    description = simple_match.group(2).strip()
                    
                    # Remove existing </br> if present
                    description_clean = description.replace('</br>', '').strip()
                    
                    # Determine status from description content
                    enhanced_status = self._determine_enhanced_status("", description_clean)
                    enhanced_line = f"{date} {enhanced_status}{description_clean}</br>"
                    enhanced_lines.append(enhanced_line)
                else:
                    # Keep original line
                    enhanced_lines.append(line)
        
        return '\n'.join(enhanced_lines)
    
    def _determine_enhanced_status(self, existing_status: str, description: str) -> str:
        """
        Determine enhanced status label based on existing status and description content.
        
        Args:
            existing_status: Existing status from AI
            description: Work item description
            
        Returns:
            Enhanced status label with formatting
        """
        # Combine status and description for analysis
        combined_text = f"{existing_status} {description}".lower()
        
        # Production/deployment keywords (更精確的關鍵字匹配)
        production_keywords = ['develop', 'dev', 'master', 'deploy', 'deployment', '部署', '上線', 'production', 'prod', 'release', '發布', 'live']
        # Testing keywords  
        testing_keywords = ['test', 'testing', 'training', '測試', '測試機', 'qa', 'quality', 'verify', '驗證', 'staging']
        
        # 詳細日誌記錄來調試
        logger.debug(f"Status analysis - Combined text: {combined_text}")
        
        # Check for production/deployment (優先級最高)
        for keyword in production_keywords:
            if keyword in combined_text:
                logger.debug(f"Found production keyword: {keyword}")
                return "`上線` "
        
        # Check for testing
        for keyword in testing_keywords:
            if keyword in combined_text:
                logger.debug(f"Found testing keyword: {keyword}")
                return "`交測` "
        
        # Default to merge
        logger.debug("No specific keywords found, defaulting to merge")
        return "`分支合併` "