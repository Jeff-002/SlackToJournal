"""
Schemas for task scheduling.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of scheduled tasks."""
    WEEKLY_JOURNAL = "weekly_journal"
    DAILY_SUMMARY = "daily_summary"
    MONTHLY_REPORT = "monthly_report"
    BACKUP = "backup"
    CLEANUP = "cleanup"
    HEALTH_CHECK = "health_check"


class TaskConfig(BaseModel):
    """Configuration for scheduled tasks."""
    
    model_config = ConfigDict(extra="allow")
    
    # Task identification
    task_id: str = Field(description="Unique task identifier")
    task_type: TaskType = Field(description="Type of task")
    name: str = Field(description="Human-readable task name")
    description: Optional[str] = Field(default=None, description="Task description")
    
    # Scheduling
    cron_expression: str = Field(description="Cron expression for scheduling")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    enabled: bool = Field(default=True, description="Whether task is enabled")
    
    # Execution settings
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_delay: int = Field(default=300, description="Delay between retries in seconds")
    timeout: int = Field(default=1800, description="Task timeout in seconds")
    
    # Task-specific parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task-specific parameters")
    
    # Notifications
    notify_on_success: bool = Field(default=False, description="Send notification on success")
    notify_on_failure: bool = Field(default=True, description="Send notification on failure")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")


class TaskResult(BaseModel):
    """Result of task execution."""
    
    model_config = ConfigDict(extra="ignore")
    
    # Task identification
    task_id: str = Field(description="Task identifier")
    execution_id: str = Field(description="Unique execution identifier")
    
    # Status and timing
    status: TaskStatus = Field(description="Execution status")
    start_time: datetime = Field(description="Task start time")
    end_time: Optional[datetime] = Field(default=None, description="Task end time")
    duration: Optional[float] = Field(default=None, description="Execution duration in seconds")
    
    # Results
    success: bool = Field(description="Whether task completed successfully")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Task output data")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Retry information
    attempt: int = Field(default=1, description="Attempt number")
    max_attempts: int = Field(default=1, description="Maximum attempts")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed (successfully or failed)."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]


class SchedulerStatus(BaseModel):
    """Status of the task scheduler."""
    
    is_running: bool = Field(description="Whether scheduler is running")
    start_time: Optional[datetime] = Field(default=None, description="Scheduler start time")
    active_tasks: int = Field(default=0, description="Number of active tasks")
    total_tasks: int = Field(default=0, description="Total number of configured tasks")
    
    # Recent statistics
    tasks_executed_today: int = Field(default=0, description="Tasks executed today")
    successful_tasks_today: int = Field(default=0, description="Successful tasks today")
    failed_tasks_today: int = Field(default=0, description="Failed tasks today")
    
    # System information
    system_load: Optional[float] = Field(default=None, description="System load average")
    memory_usage: Optional[float] = Field(default=None, description="Memory usage percentage")
    
    # Next scheduled tasks
    next_tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Upcoming scheduled tasks")