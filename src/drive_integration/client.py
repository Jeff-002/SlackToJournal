"""
Google Drive API client.

This module provides a comprehensive client for Google Drive API
operations including file upload, download, search, and management.
"""

import io
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime
import mimetypes
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

from ..core.logging import get_logger
from ..core.exceptions import DriveIntegrationError, ValidationError
from ..settings import GoogleDriveSettings
from .auth import DriveAuthenticator
from .schemas import (
    DriveFile, DriveFolder, UploadRequest, UploadResult,
    FolderCreateRequest, SearchQuery, DriveAbout, DriveQuota,
    BatchOperation, BatchResult, DriveFileType
)


logger = get_logger(__name__)


class GoogleDriveClient:
    """
    Google Drive API client for file operations.
    
    Provides methods for uploading, downloading, searching, and managing
    files and folders in Google Drive.
    """
    
    def __init__(self, settings: GoogleDriveSettings) -> None:
        """
        Initialize the Google Drive client.
        
        Args:
            settings: Google Drive integration settings
        """
        self.settings = settings
        self.authenticator = DriveAuthenticator(settings)
        self.service = None
        self._authenticated = False
        
        logger.info("Initialized Google Drive client")
    
    async def authenticate(self) -> None:
        """
        Authenticate with Google Drive API.
        
        Raises:
            DriveIntegrationError: If authentication fails
        """
        try:
            credentials = self.authenticator.authenticate()
            self.service = build('drive', 'v3', credentials=credentials)
            self._authenticated = True
            
            logger.info("Successfully authenticated with Google Drive")
            
        except Exception as e:
            logger.error(f"Google Drive authentication failed: {e}")
            raise DriveIntegrationError(
                f"Authentication failed: {str(e)}",
                drive_error=str(e)
            )
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated before API calls."""
        if not self._authenticated or not self.service:
            raise DriveIntegrationError("Client not authenticated. Call authenticate() first.")
    
    def upload_file(self, upload_request: UploadRequest) -> UploadResult:
        """
        Upload a file to Google Drive.
        
        Args:
            upload_request: Upload request with file details
            
        Returns:
            UploadResult with upload status and file information
            
        Raises:
            DriveIntegrationError: If upload fails
        """
        self._ensure_authenticated()
        
        start_time = datetime.now()
        
        try:
            # Prepare file metadata
            file_metadata = {
                'name': upload_request.file_name,
                'parents': [upload_request.parent_folder_id] if upload_request.parent_folder_id else []
            }
            
            if upload_request.description:
                file_metadata['description'] = upload_request.description
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(upload_request.content),
                mimetype=upload_request.mime_type,
                resumable=True
            )
            
            # Upload file
            if upload_request.convert_to_google_doc and upload_request.mime_type in ['text/plain', 'text/markdown']:
                # Convert to Google Doc
                file_metadata['mimeType'] = DriveFileType.DOCUMENT
            
            result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,createdTime,parents,webViewLink'
            ).execute()
            
            # Apply sharing settings if specified
            if upload_request.share_with or upload_request.public:
                self._apply_sharing_settings(result['id'], upload_request)
            
            # Create DriveFile object
            drive_file = DriveFile(
                id=result['id'],
                name=result['name'],
                mime_type=result['mimeType'],
                size=result.get('size'),
                created_time=datetime.fromisoformat(result['createdTime'].replace('Z', '+00:00')) if result.get('createdTime') else None,
                parents=result.get('parents', []),
                web_view_link=result.get('webViewLink')
            )
            
            upload_duration = (datetime.now() - start_time).total_seconds()
            
            upload_result = UploadResult(
                success=True,
                file=drive_file,
                bytes_uploaded=len(upload_request.content),
                upload_duration=upload_duration
            )
            
            logger.info(f"Successfully uploaded file: {upload_request.file_name} (ID: {result['id']})")
            return upload_result
            
        except HttpError as e:
            error_message = f"Google Drive API error: {e}"
            logger.error(error_message)
            return UploadResult(
                success=False,
                error_message=error_message,
                upload_duration=(datetime.now() - start_time).total_seconds()
            )
        except Exception as e:
            error_message = f"Upload failed: {str(e)}"
            logger.error(error_message)
            return UploadResult(
                success=False,
                error_message=error_message,
                upload_duration=(datetime.now() - start_time).total_seconds()
            )
    
    def create_folder(self, request: FolderCreateRequest) -> DriveFolder:
        """
        Create a folder in Google Drive.
        
        Args:
            request: Folder creation request
            
        Returns:
            Created DriveFolder object
            
        Raises:
            DriveIntegrationError: If folder creation fails
        """
        self._ensure_authenticated()
        
        try:
            file_metadata = {
                'name': request.folder_name,
                'mimeType': DriveFileType.FOLDER,
                'parents': [request.parent_folder_id] if request.parent_folder_id else []
            }
            
            if request.description:
                file_metadata['description'] = request.description
            
            result = self.service.files().create(
                body=file_metadata,
                fields='id,name,mimeType,createdTime,parents,webViewLink'
            ).execute()
            
            folder = DriveFolder(
                id=result['id'],
                name=result['name'],
                mime_type=result['mimeType'],
                created_time=datetime.fromisoformat(result['createdTime'].replace('Z', '+00:00')) if result.get('createdTime') else None,
                parents=result.get('parents', []),
                web_view_link=result.get('webViewLink')
            )
            
            logger.info(f"Created folder: {request.folder_name} (ID: {result['id']})")
            return folder
            
        except HttpError as e:
            logger.error(f"Failed to create folder: {e}")
            raise DriveIntegrationError(
                f"Folder creation failed: {e}",
                drive_error=str(e)
            )
    
    def search_files(self, search_query: SearchQuery) -> List[DriveFile]:
        """
        Search for files in Google Drive.
        
        Args:
            search_query: Search criteria
            
        Returns:
            List of matching DriveFile objects
            
        Raises:
            DriveIntegrationError: If search fails
        """
        self._ensure_authenticated()
        
        try:
            # Build query string
            query_parts = []
            
            if search_query.file_name:
                query_parts.append(f"name='{search_query.file_name}'")
            
            if search_query.mime_type:
                query_parts.append(f"mimeType='{search_query.mime_type}'")
            
            if search_query.parent_folder_id:
                query_parts.append(f"'{search_query.parent_folder_id}' in parents")
            
            if search_query.starred is not None:
                query_parts.append(f"starred={str(search_query.starred).lower()}")
            
            if not search_query.trashed:
                query_parts.append("trashed=false")
            
            if search_query.shared is not None:
                query_parts.append(f"sharedWithMe={str(search_query.shared).lower()}")
            
            # Date filters
            if search_query.created_after:
                query_parts.append(f"createdTime>'{search_query.created_after.isoformat()}'")
            
            if search_query.created_before:
                query_parts.append(f"createdTime<'{search_query.created_before.isoformat()}'")
            
            if search_query.modified_after:
                query_parts.append(f"modifiedTime>'{search_query.modified_after.isoformat()}'")
            
            if search_query.modified_before:
                query_parts.append(f"modifiedTime<'{search_query.modified_before.isoformat()}'")
            
            # Full-text search
            if search_query.query:
                query_parts.append(f"fullText contains '{search_query.query}'")
            
            query_string = " and ".join(query_parts) if query_parts else ""
            
            # Execute search
            results = self.service.files().list(
                q=query_string,
                pageSize=min(search_query.max_results, 1000),
                orderBy=search_query.order_by,
                fields="files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,shared,starred,trashed)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                drive_file = DriveFile(
                    id=item['id'],
                    name=item['name'],
                    mime_type=item['mimeType'],
                    size=item.get('size'),
                    created_time=datetime.fromisoformat(item['createdTime'].replace('Z', '+00:00')) if item.get('createdTime') else None,
                    modified_time=datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00')) if item.get('modifiedTime') else None,
                    parents=item.get('parents', []),
                    web_view_link=item.get('webViewLink'),
                    shared=item.get('shared', False),
                    starred=item.get('starred', False),
                    trashed=item.get('trashed', False)
                )
                files.append(drive_file)
            
            logger.info(f"Found {len(files)} files matching search criteria")
            return files
            
        except HttpError as e:
            logger.error(f"Search failed: {e}")
            raise DriveIntegrationError(
                f"File search failed: {e}",
                drive_error=str(e)
            )
    
    def get_file_content(self, file_id: str) -> bytes:
        """
        Download file content from Google Drive.
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            File content as bytes
            
        Raises:
            DriveIntegrationError: If download fails
        """
        self._ensure_authenticated()
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            content = file_io.getvalue()
            logger.info(f"Downloaded file {file_id} ({len(content)} bytes)")
            return content
            
        except HttpError as e:
            logger.error(f"Download failed for file {file_id}: {e}")
            raise DriveIntegrationError(
                f"File download failed: {e}",
                drive_error=str(e),
                file_id=file_id
            )
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            DriveIntegrationError: If deletion fails
        """
        self._ensure_authenticated()
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            raise DriveIntegrationError(
                f"File deletion failed: {e}",
                drive_error=str(e),
                file_id=file_id
            )
    
    def get_about(self) -> DriveAbout:
        """
        Get Google Drive account information.
        
        Returns:
            DriveAbout object with account details
            
        Raises:
            DriveIntegrationError: If request fails
        """
        self._ensure_authenticated()
        
        try:
            result = self.service.about().get(
                fields="user,storageQuota,importFormats,exportFormats,maxImportSizes,maxUploadSizes"
            ).execute()
            
            quota_data = result.get('storageQuota', {})
            quota = DriveQuota(
                limit=int(quota_data.get('limit', 0)) if quota_data.get('limit') else None,
                usage=int(quota_data.get('usage', 0)) if quota_data.get('usage') else None,
                usage_in_drive=int(quota_data.get('usageInDrive', 0)) if quota_data.get('usageInDrive') else None,
                usage_in_drive_trash=int(quota_data.get('usageInDriveTrash', 0)) if quota_data.get('usageInDriveTrash') else None
            )
            
            about = DriveAbout(
                user=result.get('user', {}),
                storage_quota=quota,
                import_formats=result.get('importFormats', {}),
                export_formats=result.get('exportFormats', {}),
                max_import_size=result.get('maxImportSizes', {}),
                max_upload_size=int(result.get('maxUploadSizes', {}).get('*', 0)) if result.get('maxUploadSizes', {}).get('*') else None
            )
            
            logger.info("Retrieved Drive account information")
            return about
            
        except HttpError as e:
            logger.error(f"Failed to get Drive account info: {e}")
            raise DriveIntegrationError(
                f"Account info request failed: {e}",
                drive_error=str(e)
            )
    
    def _apply_sharing_settings(self, file_id: str, upload_request: UploadRequest) -> None:
        """Apply sharing settings to uploaded file."""
        try:
            if upload_request.public:
                permission = {
                    'role': 'reader',
                    'type': 'anyone'
                }
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                logger.debug(f"Made file {file_id} public")
            
            for permission in upload_request.share_with:
                permission_body = {
                    'role': permission.role,
                    'type': permission.type
                }
                
                if permission.email_address:
                    permission_body['emailAddress'] = permission.email_address
                
                if permission.domain:
                    permission_body['domain'] = permission.domain
                
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission_body
                ).execute()
                logger.debug(f"Applied permission to file {file_id}: {permission.role} for {permission.type}")
                
        except HttpError as e:
            logger.warning(f"Failed to apply sharing settings to {file_id}: {e}")
    
    def ensure_folder_exists(self, folder_path: str, parent_id: Optional[str] = None) -> str:
        """
        Ensure a folder path exists, creating folders as needed.
        
        Args:
            folder_path: Folder path (e.g., "2024/January/Week1")
            parent_id: Parent folder ID (defaults to Drive root)
            
        Returns:
            ID of the final folder in the path
            
        Raises:
            DriveIntegrationError: If folder creation fails
        """
        self._ensure_authenticated()
        
        current_parent = parent_id or self.settings.folder_id
        folders = folder_path.strip('/').split('/')
        
        for folder_name in folders:
            if not folder_name:
                continue
            
            # Check if folder already exists
            search_query = SearchQuery(
                file_name=folder_name,
                mime_type=DriveFileType.FOLDER,
                parent_folder_id=current_parent,
                max_results=1
            )
            
            existing_folders = self.search_files(search_query)
            
            if existing_folders:
                current_parent = existing_folders[0].id
                logger.debug(f"Found existing folder: {folder_name} (ID: {current_parent})")
            else:
                # Create folder
                create_request = FolderCreateRequest(
                    folder_name=folder_name,
                    parent_folder_id=current_parent
                )
                
                new_folder = self.create_folder(create_request)
                current_parent = new_folder.id
                logger.info(f"Created folder: {folder_name} (ID: {current_parent})")
        
        return current_parent