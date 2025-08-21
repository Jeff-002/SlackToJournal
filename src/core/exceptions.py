"""
Custom exceptions for the SlackToJournal application.

This module defines application-specific exceptions that provide
clear error handling and debugging information.
"""

from typing import Optional, Dict, Any


class SlackToJournalError(Exception):
    """Base exception for all SlackToJournal application errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(SlackToJournalError):
    """Raised when there are configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class SlackIntegrationError(SlackToJournalError):
    """Raised when Slack API or MCP integration fails."""
    
    def __init__(
        self, 
        message: str, 
        slack_error: Optional[str] = None,
        response_code: Optional[int] = None
    ) -> None:
        super().__init__(message, "SLACK_ERROR")
        self.slack_error = slack_error
        self.response_code = response_code


class AIProcessingError(SlackToJournalError):
    """Raised when AI content processing fails."""
    
    def __init__(
        self, 
        message: str, 
        ai_error: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> None:
        super().__init__(message, "AI_ERROR")
        self.ai_error = ai_error
        self.model_name = model_name


class DriveIntegrationError(SlackToJournalError):
    """Raised when Google Drive operations fail."""
    
    def __init__(
        self, 
        message: str, 
        drive_error: Optional[str] = None,
        file_id: Optional[str] = None
    ) -> None:
        super().__init__(message, "DRIVE_ERROR")
        self.drive_error = drive_error
        self.file_id = file_id


class AuthenticationError(SlackToJournalError):
    """Raised when authentication fails."""
    
    def __init__(
        self, 
        message: str, 
        service: Optional[str] = None,
        auth_type: Optional[str] = None
    ) -> None:
        super().__init__(message, "AUTH_ERROR")
        self.service = service
        self.auth_type = auth_type


class ValidationError(SlackToJournalError):
    """Raised when data validation fails."""
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None
    ) -> None:
        super().__init__(message, "VALIDATION_ERROR")
        self.field_name = field_name
        self.invalid_value = invalid_value


class SchedulingError(SlackToJournalError):
    """Raised when task scheduling fails."""
    
    def __init__(
        self, 
        message: str, 
        task_name: Optional[str] = None,
        cron_expression: Optional[str] = None
    ) -> None:
        super().__init__(message, "SCHEDULING_ERROR")
        self.task_name = task_name
        self.cron_expression = cron_expression