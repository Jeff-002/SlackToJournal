"""
Schemas for journal processing and formatting.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class JournalFormat(str, Enum):
    """Journal output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    TEXT = "text"


class JournalType(str, Enum):
    """Types of journals."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    PROJECT = "project"
    CUSTOM = "custom"


class JournalMetadata(BaseModel):
    """Metadata for journal entries."""
    
    model_config = ConfigDict(extra="allow")
    
    # Basic information
    title: str = Field(description="Journal title")
    journal_type: JournalType = Field(description="Type of journal")
    period_start: datetime = Field(description="Period start date")
    period_end: datetime = Field(description="Period end date")
    
    # Author information
    author_name: str = Field(description="Author name")
    author_email: Optional[str] = Field(default=None, description="Author email")
    team: Optional[str] = Field(default=None, description="Team name")
    
    # Generation metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    generator_version: str = Field(default="1.0.0", description="Generator version")
    
    # Content statistics
    total_messages: int = Field(default=0, description="Total messages analyzed")
    work_items_count: int = Field(default=0, description="Number of work items")
    projects_count: int = Field(default=0, description="Number of projects")
    
    # Quality metrics
    confidence_score: float = Field(default=0.0, description="Overall confidence score")
    completeness_score: float = Field(default=0.0, description="Content completeness score")
    
    # Tags and categories
    tags: List[str] = Field(default_factory=list, description="Journal tags")
    categories: List[str] = Field(default_factory=list, description="Content categories")


class JournalEntry(BaseModel):
    """Complete journal entry with content and metadata."""
    
    model_config = ConfigDict(extra="allow")
    
    # Core content
    metadata: JournalMetadata = Field(description="Journal metadata")
    content: str = Field(description="Formatted journal content")
    raw_content: Optional[Dict[str, Any]] = Field(default=None, description="Raw structured content")
    
    # Formatting options
    format_type: JournalFormat = Field(default=JournalFormat.MARKDOWN, description="Content format")
    template_name: Optional[str] = Field(default=None, description="Template used")
    
    # File information
    file_name: Optional[str] = Field(default=None, description="Generated file name")
    file_path: Optional[str] = Field(default=None, description="File path if saved")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    
    # Export information
    exported_formats: List[JournalFormat] = Field(default_factory=list, description="Formats exported to")
    export_paths: Dict[str, str] = Field(default_factory=dict, description="Export paths by format")
    
    @property
    def word_count(self) -> int:
        """Calculate word count of content."""
        return len(self.content.split())
    
    @property
    def character_count(self) -> int:
        """Calculate character count of content."""
        return len(self.content)
    
    def add_export_path(self, format_type: JournalFormat, path: str) -> None:
        """Add export path for a specific format."""
        if format_type not in self.exported_formats:
            self.exported_formats.append(format_type)
        self.export_paths[format_type.value] = path


class TemplateConfig(BaseModel):
    """Configuration for journal templates."""
    
    model_config = ConfigDict(extra="allow")
    
    # Template identification
    name: str = Field(description="Template name")
    description: str = Field(description="Template description")
    format_type: JournalFormat = Field(description="Output format")
    
    # Content sections
    include_summary: bool = Field(default=True, description="Include executive summary")
    include_highlights: bool = Field(default=True, description="Include key highlights")
    include_projects: bool = Field(default=True, description="Include project breakdown")
    include_categories: bool = Field(default=True, description="Include category analysis")
    include_timeline: bool = Field(default=False, description="Include timeline view")
    include_metrics: bool = Field(default=True, description="Include metrics")
    include_action_items: bool = Field(default=True, description="Include action items")
    include_learnings: bool = Field(default=True, description="Include learnings")
    include_challenges: bool = Field(default=True, description="Include challenges")
    
    # Formatting options
    use_emoji: bool = Field(default=True, description="Use emoji in formatting")
    table_of_contents: bool = Field(default=True, description="Generate table of contents")
    collapsible_sections: bool = Field(default=False, description="Use collapsible sections")
    syntax_highlighting: bool = Field(default=True, description="Enable syntax highlighting")
    
    # Styling
    color_scheme: Optional[str] = Field(default=None, description="Color scheme for HTML/PDF")
    font_family: Optional[str] = Field(default=None, description="Font family")
    font_size: Optional[str] = Field(default=None, description="Font size")
    
    # Custom sections
    custom_sections: List[Dict[str, Any]] = Field(default_factory=list, description="Custom sections")


class ExportOptions(BaseModel):
    """Options for exporting journal entries."""
    
    model_config = ConfigDict(extra="allow")
    
    # Output formats
    formats: List[JournalFormat] = Field(default=[JournalFormat.MARKDOWN], description="Export formats")
    
    # File naming
    file_name_template: str = Field(
        default="journal_{type}_{date}",
        description="File name template"
    )
    include_timestamp: bool = Field(default=True, description="Include timestamp in filename")
    
    # Output location
    output_directory: Optional[str] = Field(default=None, description="Output directory")
    
    # Format-specific options
    markdown_options: Dict[str, Any] = Field(default_factory=dict, description="Markdown-specific options")
    html_options: Dict[str, Any] = Field(default_factory=dict, description="HTML-specific options")
    pdf_options: Dict[str, Any] = Field(default_factory=dict, description="PDF-specific options")
    
    # Upload options
    upload_to_drive: bool = Field(default=True, description="Upload to Google Drive")
    drive_folder_path: Optional[str] = Field(default=None, description="Drive folder path")
    make_public: bool = Field(default=False, description="Make files public")
    
    # Backup options
    create_backup: bool = Field(default=True, description="Create backup copy")
    backup_location: Optional[str] = Field(default=None, description="Backup location")


class ProcessingResult(BaseModel):
    """Result of journal processing operation."""
    
    success: bool = Field(description="Whether processing succeeded")
    journal_entry: Optional[JournalEntry] = Field(default=None, description="Generated journal entry")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Processing metrics
    processing_time: float = Field(description="Processing time in seconds")
    messages_processed: int = Field(description="Number of messages processed")
    
    # Quality metrics
    quality_score: float = Field(default=0.0, description="Quality score")
    validation_passed: bool = Field(default=True, description="Whether validation passed")
    validation_warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Export results
    export_results: Dict[str, Any] = Field(default_factory=dict, description="Export operation results")
    
    # Statistics
    stats: Dict[str, Any] = Field(default_factory=dict, description="Processing statistics")