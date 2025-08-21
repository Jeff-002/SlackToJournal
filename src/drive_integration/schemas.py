"""
Pydantic schemas for Google Drive integration.

This module defines data models for Google Drive API responses
and internal data structures for file operations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict


class DriveFileType(str, Enum):
    """Google Drive file types."""
    DOCUMENT = "application/vnd.google-apps.document"
    SPREADSHEET = "application/vnd.google-apps.spreadsheet"
    PRESENTATION = "application/vnd.google-apps.presentation"
    FOLDER = "application/vnd.google-apps.folder"
    PDF = "application/pdf"
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    JSON = "application/json"


class DrivePermissionRole(str, Enum):
    """Google Drive permission roles."""
    OWNER = "owner"
    ORGANIZER = "organizer"
    FILE_ORGANIZER = "fileOrganizer"
    WRITER = "writer"
    COMMENTER = "commenter"
    READER = "reader"


class DrivePermissionType(str, Enum):
    """Google Drive permission types."""
    USER = "user"
    GROUP = "group"
    DOMAIN = "domain"
    ANYONE = "anyone"


class DrivePermission(BaseModel):
    """Google Drive file permission."""
    
    model_config = ConfigDict(extra="ignore")
    
    id: Optional[str] = Field(default=None, description="Permission ID")
    type: DrivePermissionType = Field(description="Permission type")
    role: DrivePermissionRole = Field(description="Permission role")
    email_address: Optional[str] = Field(default=None, description="User email")
    domain: Optional[str] = Field(default=None, description="Domain name")
    display_name: Optional[str] = Field(default=None, description="Display name")


class DriveFile(BaseModel):
    """Google Drive file information."""
    
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(description="File ID")
    name: str = Field(description="File name")
    mime_type: str = Field(description="MIME type")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    
    # Timestamps
    created_time: Optional[datetime] = Field(default=None, description="Creation time")
    modified_time: Optional[datetime] = Field(default=None, description="Last modification time")
    
    # Parent information
    parents: List[str] = Field(default_factory=list, description="Parent folder IDs")
    
    # Sharing and permissions
    shared: bool = Field(default=False, description="Whether file is shared")
    permissions: List[DrivePermission] = Field(default_factory=list, description="File permissions")
    web_view_link: Optional[str] = Field(default=None, description="Web view link")
    web_content_link: Optional[str] = Field(default=None, description="Download link")
    
    # Additional metadata
    description: Optional[str] = Field(default=None, description="File description")
    starred: bool = Field(default=False, description="Whether file is starred")
    trashed: bool = Field(default=False, description="Whether file is trashed")
    
    # Owner information
    owners: List[Dict[str, Any]] = Field(default_factory=list, description="File owners")
    
    @property
    def is_folder(self) -> bool:
        """Check if this is a folder."""
        return self.mime_type == DriveFileType.FOLDER
    
    @property
    def is_google_doc(self) -> bool:
        """Check if this is a Google document."""
        google_types = {
            DriveFileType.DOCUMENT,
            DriveFileType.SPREADSHEET,
            DriveFileType.PRESENTATION
        }
        return self.mime_type in google_types


class DriveFolder(DriveFile):
    """Google Drive folder (specialized DriveFile)."""
    
    mime_type: str = Field(default=DriveFileType.FOLDER, description="Always folder MIME type")
    children: List[DriveFile] = Field(default_factory=list, description="Child files and folders")
    
    def add_child(self, child: DriveFile) -> None:
        """Add a child file or folder."""
        if child not in self.children:
            self.children.append(child)


class UploadRequest(BaseModel):
    """Request for uploading a file to Google Drive."""
    
    model_config = ConfigDict(extra="allow")
    
    file_name: str = Field(description="Name of the file to upload")
    content: bytes = Field(description="File content as bytes")
    mime_type: str = Field(description="MIME type of the file")
    parent_folder_id: Optional[str] = Field(default=None, description="Parent folder ID")
    
    # Optional metadata
    description: Optional[str] = Field(default=None, description="File description")
    convert_to_google_doc: bool = Field(default=False, description="Convert to Google Doc format")
    
    # Sharing settings
    share_with: List[DrivePermission] = Field(default_factory=list, description="Initial permissions")
    public: bool = Field(default=False, description="Make file public")


class UploadResult(BaseModel):
    """Result of a file upload operation."""
    
    model_config = ConfigDict(extra="ignore")
    
    success: bool = Field(description="Whether upload was successful")
    file: Optional[DriveFile] = Field(default=None, description="Uploaded file information")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    upload_time: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    
    # Upload statistics
    bytes_uploaded: Optional[int] = Field(default=None, description="Number of bytes uploaded")
    upload_duration: Optional[float] = Field(default=None, description="Upload duration in seconds")


class FolderCreateRequest(BaseModel):
    """Request for creating a folder in Google Drive."""
    
    folder_name: str = Field(description="Name of the folder to create")
    parent_folder_id: Optional[str] = Field(default=None, description="Parent folder ID")
    description: Optional[str] = Field(default=None, description="Folder description")


class SearchQuery(BaseModel):
    """Query parameters for searching Drive files."""
    
    model_config = ConfigDict(extra="allow")
    
    query: Optional[str] = Field(default=None, description="Search query string")
    file_name: Optional[str] = Field(default=None, description="Exact file name match")
    mime_type: Optional[str] = Field(default=None, description="MIME type filter")
    parent_folder_id: Optional[str] = Field(default=None, description="Parent folder ID")
    
    # Date filters
    created_after: Optional[datetime] = Field(default=None, description="Created after date")
    created_before: Optional[datetime] = Field(default=None, description="Created before date")
    modified_after: Optional[datetime] = Field(default=None, description="Modified after date")
    modified_before: Optional[datetime] = Field(default=None, description="Modified before date")
    
    # Other filters
    starred: Optional[bool] = Field(default=None, description="Starred files only")
    trashed: bool = Field(default=False, description="Include trashed files")
    shared: Optional[bool] = Field(default=None, description="Shared files filter")
    
    # Result options
    max_results: int = Field(default=100, description="Maximum number of results")
    order_by: str = Field(default="modifiedTime desc", description="Sort order")


class DriveQuota(BaseModel):
    """Google Drive quota information."""
    
    model_config = ConfigDict(extra="ignore")
    
    limit: Optional[int] = Field(default=None, description="Total quota limit in bytes")
    usage: Optional[int] = Field(default=None, description="Used quota in bytes")
    usage_in_drive: Optional[int] = Field(default=None, description="Usage in Drive")
    usage_in_drive_trash: Optional[int] = Field(default=None, description="Usage in trash")
    
    @property
    def available_space(self) -> Optional[int]:
        """Calculate available space in bytes."""
        if self.limit is not None and self.usage is not None:
            return self.limit - self.usage
        return None
    
    @property
    def usage_percentage(self) -> Optional[float]:
        """Calculate usage percentage."""
        if self.limit is not None and self.usage is not None and self.limit > 0:
            return (self.usage / self.limit) * 100
        return None


class DriveAbout(BaseModel):
    """Google Drive account information."""
    
    model_config = ConfigDict(extra="ignore")
    
    user: Dict[str, Any] = Field(description="User information")
    storage_quota: DriveQuota = Field(description="Storage quota information")
    import_formats: Dict[str, List[str]] = Field(default_factory=dict, description="Import formats")
    export_formats: Dict[str, List[str]] = Field(default_factory=dict, description="Export formats")
    max_import_size: Dict[str, int] = Field(default_factory=dict, description="Max import sizes")
    max_upload_size: Optional[int] = Field(default=None, description="Max upload size")


class BatchOperation(BaseModel):
    """Batch operation for multiple Drive operations."""
    
    operation_type: str = Field(description="Type of operation (upload, delete, etc.)")
    files: List[Dict[str, Any]] = Field(description="List of files to operate on")
    options: Dict[str, Any] = Field(default_factory=dict, description="Operation options")


class BatchResult(BaseModel):
    """Result of a batch operation."""
    
    total_operations: int = Field(description="Total number of operations")
    successful_operations: int = Field(description="Number of successful operations")
    failed_operations: int = Field(description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(description="Individual operation results")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    execution_time: float = Field(description="Total execution time in seconds")