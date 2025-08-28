"""
Google Drive service layer for business logic.

This module provides high-level business logic for Google Drive operations,
including journal file management, folder organization, and batch operations.
"""

import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from ..core.logging import get_logger
from ..core.exceptions import DriveIntegrationError, ValidationError
from ..settings import GoogleDriveSettings
from .client import GoogleDriveClient
from .schemas import (
    UploadRequest, UploadResult, DriveFile, DriveFolder,
    FolderCreateRequest, SearchQuery, DriveFileType
)


logger = get_logger(__name__)


class DriveService:
    """
    High-level service for Google Drive operations.
    
    Provides business logic for journal file management,
    folder organization, and automated workflows.
    """
    
    def __init__(self, settings: GoogleDriveSettings) -> None:
        """
        Initialize the Drive service.
        
        Args:
            settings: Google Drive integration settings
        """
        self.settings = settings
        self.client = GoogleDriveClient(settings)
        
        logger.info("Initialized Drive service")
    
    async def upload_weekly_journal(
        self,
        journal_content: str,
        week_start_date: datetime,
        format_type: str = "markdown"
    ) -> UploadResult:
        """
        Upload a weekly work journal to Google Drive.
        
        Args:
            journal_content: The journal content as string
            week_start_date: Start date of the week
            format_type: Format type ("markdown", "text", "json")
            
        Returns:
            UploadResult with upload status and file information
            
        Raises:
            DriveIntegrationError: If upload fails
        """
        await self.client.authenticate()
        
        # Generate file name based on week
        file_name = self._generate_journal_filename(week_start_date, format_type)
        
        # Determine MIME type
        mime_type_map = {
            "markdown": "text/markdown",
            "text": "text/plain",
            "json": "application/json"
        }
        mime_type = mime_type_map.get(format_type, "text/plain")
        
        # Create folder structure for the year/month
        folder_path = self._generate_folder_path(week_start_date)
        target_folder_id = self.client.ensure_folder_exists(folder_path, self.settings.folder_id)
        
        # Prepare upload request
        upload_request = UploadRequest(
            file_name=file_name,
            content=journal_content.encode('utf-8'),
            mime_type=mime_type,
            parent_folder_id=target_folder_id,
            description=f"Work journal for week of {week_start_date.strftime('%Y-%m-%d')}",
            convert_to_google_doc=(format_type in ["markdown", "text"])
        )
        
        # Upload the journal
        result = self.client.upload_file(upload_request)
        
        if result.success:
            logger.info(f"Successfully uploaded weekly journal: {file_name}")
        else:
            logger.error(f"Failed to upload weekly journal: {result.error_message}")
        
        return result
    
    async def upload_daily_summary(
        self,
        summary_data: Dict[str, Any],
        date: datetime
    ) -> UploadResult:
        """
        Upload a daily work summary to Google Drive.
        
        Args:
            summary_data: Dictionary containing daily summary data
            date: Date of the summary
            
        Returns:
            UploadResult with upload status and file information
        """
        await self.client.authenticate()
        
        # Generate filename
        file_name = f"daily_summary_{date.strftime('%Y-%m-%d')}.json"
        
        # Create folder structure
        folder_path = f"{date.year}/{date.strftime('%B')}/Daily"
        target_folder_id = self.client.ensure_folder_exists(folder_path, self.settings.folder_id)
        
        # Convert summary to JSON
        json_content = json.dumps(summary_data, indent=2, ensure_ascii=False)
        
        # Prepare upload request
        upload_request = UploadRequest(
            file_name=file_name,
            content=json_content.encode('utf-8'),
            mime_type="application/json",
            parent_folder_id=target_folder_id,
            description=f"Daily work summary for {date.strftime('%Y-%m-%d')}"
        )
        
        # Upload the summary
        result = self.client.upload_file(upload_request)
        
        if result.success:
            logger.info(f"Successfully uploaded daily summary: {file_name}")
        else:
            logger.error(f"Failed to upload daily summary: {result.error_message}")
        
        return result
    
    
    async def backup_journal_data(
        self,
        data: Dict[str, Any],
        backup_type: str = "weekly"
    ) -> UploadResult:
        """
        Create a backup of journal data.
        
        Args:
            data: Data to backup
            backup_type: Type of backup ("weekly", "monthly", "full")
            
        Returns:
            UploadResult with backup status
        """
        await self.client.authenticate()
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"journal_backup_{backup_type}_{timestamp}.json"
        
        # Create backup folder
        backup_folder_path = f"Backups/{datetime.now().year}"
        target_folder_id = self.client.ensure_folder_exists(backup_folder_path, self.settings.folder_id)
        
        # Add metadata to backup
        backup_data = {
            "backup_type": backup_type,
            "created_at": datetime.now().isoformat(),
            "data_count": len(data) if isinstance(data, (list, dict)) else 1,
            "data": data
        }
        
        # Convert to JSON
        json_content = json.dumps(backup_data, indent=2, ensure_ascii=False, default=str)
        
        # Prepare upload request
        upload_request = UploadRequest(
            file_name=file_name,
            content=json_content.encode('utf-8'),
            mime_type="application/json",
            parent_folder_id=target_folder_id,
            description=f"{backup_type.title()} backup of journal data"
        )
        
        # Upload backup
        result = self.client.upload_file(upload_request)
        
        if result.success:
            logger.info(f"Successfully created backup: {file_name}")
        else:
            logger.error(f"Failed to create backup: {result.error_message}")
        
        return result
    
    async def organize_journal_files(self) -> Dict[str, Any]:
        """
        Organize existing journal files into proper folder structure.
        
        Returns:
            Dictionary with organization results
        """
        await self.client.authenticate()
        
        # Search for all journal files
        search_query = SearchQuery(
            query="journal OR summary OR work",
            max_results=500,
            order_by="createdTime desc"
        )
        
        all_files = self.client.search_files(search_query)
        
        organized_count = 0
        errors = []
        
        for file in all_files:
            try:
                # Skip if already in organized structure
                if len(file.parents) > 0:
                    parent_files = self.client.search_files(
                        SearchQuery(file_name="*", parent_folder_id=file.parents[0], max_results=1)
                    )
                    # If parent looks like year/month structure, skip
                    continue
                
                # Determine target folder based on file creation date
                if file.created_time:
                    folder_path = self._generate_folder_path(file.created_time)
                    target_folder_id = self.client.ensure_folder_exists(folder_path, self.settings.folder_id)
                    
                    # Move file (this would require additional API calls)
                    # For now, we'll just log what we would do
                    logger.info(f"Would move {file.name} to {folder_path}")
                    organized_count += 1
                
            except Exception as e:
                error_msg = f"Failed to organize {file.name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        result = {
            "total_files_processed": len(all_files),
            "files_organized": organized_count,
            "errors": errors,
            "success": len(errors) == 0
        }
        
        logger.info(f"Organization complete: {organized_count} files processed")
        return result
    
    async def get_drive_usage_stats(self) -> Dict[str, Any]:
        """
        Get Google Drive usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        await self.client.authenticate()
        
        about_info = self.client.get_about()
        
        # Search for journal files to get statistics
        journal_search = SearchQuery(
            query="journal OR summary",
            max_results=1000
        )
        
        journal_files = self.client.search_files(journal_search)
        
        # Calculate journal file statistics
        total_journal_size = sum(
            int(file.size) for file in journal_files 
            if file.size and file.size.isdigit()
        )
        
        journal_by_type = {}
        for file in journal_files:
            file_type = file.mime_type.split('/')[-1] if file.mime_type else 'unknown'
            journal_by_type[file_type] = journal_by_type.get(file_type, 0) + 1
        
        stats = {
            "account": {
                "user_email": about_info.user.get('emailAddress'),
                "user_name": about_info.user.get('displayName')
            },
            "storage": {
                "total_limit": about_info.storage_quota.limit,
                "total_usage": about_info.storage_quota.usage,
                "available_space": about_info.storage_quota.available_space,
                "usage_percentage": about_info.storage_quota.usage_percentage
            },
            "journal_files": {
                "total_count": len(journal_files),
                "total_size": total_journal_size,
                "files_by_type": journal_by_type
            }
        }
        
        logger.info("Retrieved Drive usage statistics")
        return stats
    
    def _generate_journal_filename(self, week_start_date: datetime, format_type: str) -> str:
        """
        Generate standardized filename for journal.
        
        Args:
            week_start_date: Start date of the week
            format_type: File format type
            
        Returns:
            Generated filename
        """
        week_end_date = week_start_date + timedelta(days=6)
        
        # Format: work_journal_2024-01-15_to_2024-01-21.md
        filename = (
            f"work_journal_"
            f"{week_start_date.strftime('%Y-%m-%d')}_to_"
            f"{week_end_date.strftime('%Y-%m-%d')}"
        )
        
        extensions = {
            "markdown": ".md",
            "text": ".txt",
            "json": ".json"
        }
        
        extension = extensions.get(format_type, ".txt")
        return filename + extension
    
    def _generate_folder_path(self, date: datetime) -> str:
        """
        Generate folder path based on date.
        
        Args:
            date: Date to base folder structure on
            
        Returns:
            Folder path string (e.g., "2024/January")
        """
        year = str(date.year)
        month = date.strftime('%B')  # Full month name
        
        return f"{year}/{month}"