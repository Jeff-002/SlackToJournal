"""
Pydantic schemas for AI processing.

This module defines data models for AI requests, responses,
and structured journal content.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AIModelType(str, Enum):
    """Available AI model types."""
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_0_FLASH = "gemini-2.0-flash-exp"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"


class ContentCategory(str, Enum):
    """Content categories for work items."""
    DEVELOPMENT = "development"
    PROJECT_MANAGEMENT = "project_management"
    MEETING = "meeting"
    DECISION = "decision"
    DOCUMENTATION = "documentation"
    SUPPORT = "support"
    COLLABORATION = "collaboration"
    PLANNING = "planning"
    REVIEW = "review"
    GENERAL = "general"


class Priority(str, Enum):
    """Priority levels for work items."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WorkItemStatus(str, Enum):
    """Status of work items."""
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class WorkItem(BaseModel):
    """Individual work item extracted from messages."""
    
    model_config = ConfigDict(extra="ignore")
    
    title: str = Field(description="Concise title of the work item")
    description: str = Field(description="Detailed description")
    category: ContentCategory = Field(description="Work category")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    status: WorkItemStatus = Field(description="Current status")
    
    # Context information
    participants: List[str] = Field(default_factory=list, description="People involved")
    channels: List[str] = Field(default_factory=list, description="Related channels")
    mentioned_tools: List[str] = Field(default_factory=list, description="Tools/systems mentioned")
    
    # Time information
    deadline: Optional[datetime] = Field(default=None, description="Deadline if mentioned")
    estimated_effort: Optional[str] = Field(default=None, description="Estimated effort")
    
    # Source information
    source_messages: List[str] = Field(default_factory=list, description="Source message IDs")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence score")
    
    # Additional metadata
    tags: List[str] = Field(default_factory=list, description="Related tags")
    references: List[str] = Field(default_factory=list, description="External references (URLs, docs)")


class ProjectSummary(BaseModel):
    """Summary of work for a specific project."""
    
    project_name: str = Field(description="Project name")
    work_items: List[WorkItem] = Field(description="Work items for this project")
    key_achievements: List[str] = Field(default_factory=list, description="Key achievements")
    challenges: List[str] = Field(default_factory=list, description="Challenges faced")
    next_steps: List[str] = Field(default_factory=list, description="Planned next steps")
    
    # Metrics
    total_items: int = Field(description="Total number of work items")
    completed_items: int = Field(description="Number of completed items")
    in_progress_items: int = Field(description="Number of in-progress items")


class JournalStructure(BaseModel):
    """Structured journal content."""
    
    model_config = ConfigDict(extra="allow")
    
    # Header information
    period: str = Field(description="Time period covered (e.g., 'Week of 2024-01-15')")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    
    # Executive summary
    executive_summary: str = Field(description="High-level summary of the week")
    key_highlights: List[str] = Field(description="Key highlights and achievements")
    
    # Project-based organization
    projects: List[ProjectSummary] = Field(description="Work organized by project")
    
    # Category-based analysis
    work_by_category: Dict[ContentCategory, List[WorkItem]] = Field(
        default_factory=dict,
        description="Work items organized by category"
    )
    
    # Time-based insights
    daily_breakdown: Dict[str, List[WorkItem]] = Field(
        default_factory=dict,
        description="Work items by day"
    )
    
    # Metrics and analytics
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Quantitative metrics"
    )
    
    # Action items and follow-ups
    action_items: List[WorkItem] = Field(
        default_factory=list,
        description="Items requiring follow-up"
    )
    
    # Learnings and insights
    learnings: List[str] = Field(
        default_factory=list,
        description="Key learnings from the period"
    )
    
    # Challenges and blockers
    challenges: List[str] = Field(
        default_factory=list,
        description="Challenges encountered"
    )


class AIRequest(BaseModel):
    """Request for AI processing."""
    
    model_config = ConfigDict(extra="allow")
    
    # Input data
    messages: List[Dict[str, Any]] = Field(description="Input messages to process")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    # Processing parameters
    model_type: AIModelType = Field(default=AIModelType.GEMINI_2_5_FLASH, description="AI model to use")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Response creativity")
    max_tokens: int = Field(default=8192, description="Maximum response length")
    
    # Task configuration
    task_type: str = Field(description="Type of processing task")
    output_format: str = Field(default="json", description="Desired output format")
    language: str = Field(default="en", description="Response language")
    
    # Filtering options
    include_low_confidence: bool = Field(default=False, description="Include low-confidence results")
    min_confidence_score: float = Field(default=0.3, description="Minimum confidence threshold")
    
    # Processing options
    group_by_project: bool = Field(default=True, description="Group results by project")
    extract_action_items: bool = Field(default=True, description="Extract action items")
    analyze_sentiment: bool = Field(default=False, description="Include sentiment analysis")


class AIResponse(BaseModel):
    """Response from AI processing."""
    
    model_config = ConfigDict(extra="ignore")
    
    # Status
    success: bool = Field(description="Whether processing was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Processing metadata
    model_used: str = Field(description="AI model that was used")
    processing_time: float = Field(description="Processing time in seconds")
    tokens_used: int = Field(description="Number of tokens consumed")
    
    # Results
    journal_structure: Optional[JournalStructure] = Field(default=None, description="Structured journal content")
    raw_response: Optional[str] = Field(default=None, description="Raw AI response")
    
    # Quality metrics
    confidence_score: float = Field(default=0.0, description="Overall confidence score")
    completeness_score: float = Field(default=0.0, description="Content completeness score")
    
    # Processing statistics
    messages_processed: int = Field(description="Number of input messages processed")
    work_items_extracted: int = Field(description="Number of work items extracted")
    projects_identified: int = Field(description="Number of projects identified")


class PromptContext(BaseModel):
    """Context information for prompt generation."""
    
    model_config = ConfigDict(extra="allow")
    
    # User information
    user_name: Optional[str] = Field(default=None, description="User's name")
    role: Optional[str] = Field(default=None, description="User's role/title")
    team: Optional[str] = Field(default=None, description="Team name")
    
    # Time context
    period_start: datetime = Field(description="Period start date")
    period_end: datetime = Field(description="Period end date")
    period_type: str = Field(default="week", description="Period type (day, week, month)")
    
    # Project context
    active_projects: List[str] = Field(default_factory=list, description="Currently active projects")
    focus_areas: List[str] = Field(default_factory=list, description="Key focus areas")
    
    # Organization context
    company_name: Optional[str] = Field(default=None, description="Company name")
    department: Optional[str] = Field(default=None, description="Department name")
    
    # Previous context
    previous_journal: Optional[str] = Field(default=None, description="Previous journal for reference")
    recurring_themes: List[str] = Field(default_factory=list, description="Recurring themes to track")


class ValidationResult(BaseModel):
    """Result of AI output validation."""
    
    is_valid: bool = Field(description="Whether the output is valid")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")
    quality_score: float = Field(default=0.0, description="Quality score (0-1)")
    
    # Specific validation metrics
    structure_valid: bool = Field(description="Whether structure is valid")
    content_complete: bool = Field(description="Whether content is complete")
    format_correct: bool = Field(description="Whether format is correct")
    
    # Suggestions
    improvement_suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")


class ProcessingStats(BaseModel):
    """Statistics from AI processing session."""
    
    total_requests: int = Field(description="Total number of requests processed")
    successful_requests: int = Field(description="Number of successful requests")
    failed_requests: int = Field(description="Number of failed requests")
    
    total_tokens_used: int = Field(description="Total tokens consumed")
    total_processing_time: float = Field(description="Total processing time in seconds")
    average_processing_time: float = Field(description="Average processing time per request")
    
    work_items_extracted: int = Field(description="Total work items extracted")
    projects_identified: int = Field(description="Total projects identified")
    
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Quality metrics")
    error_breakdown: Dict[str, int] = Field(default_factory=dict, description="Error types and counts")