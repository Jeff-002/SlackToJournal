"""
Logging configuration and utilities for the SlackToJournal application.

This module provides centralized logging setup using Loguru with
structured logging and configurable output formats.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

from ..settings import LoggingSettings


# Store configured loggers to avoid reconfiguration
_configured_loggers: Dict[str, bool] = {}


def setup_logging(
    log_settings: LoggingSettings,
    logger_name: str = "slack_to_journal"
) -> None:
    """
    Set up application logging with Loguru.
    
    Args:
        log_settings: Logging configuration settings
        logger_name: Name of the logger instance
    """
    if logger_name in _configured_loggers:
        return  # Already configured
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colored output
    logger.add(
        sys.stdout,
        level=log_settings.level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler if specified
    if log_settings.file:
        # Ensure log directory exists
        log_settings.file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_settings.file,
            level=log_settings.level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            rotation="10 MB",
            retention="1 month",
            compression="gz",
            backtrace=True,
            diagnose=True
        )
    
    # Configure structured logging for specific modules
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "level": log_settings.level,
                "format": (
                    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                    "<level>{level: <8}</level> | "
                    "<cyan>{extra[module]}</cyan> | "
                    "<level>{message}</level>"
                ),
                "filter": lambda record: "module" in record["extra"]
            }
        ]
    )
    
    _configured_loggers[logger_name] = True
    logger.info(f"Logging configured for {logger_name} at level {log_settings.level}")


def get_logger(module_name: str) -> Any:
    """
    Get a logger instance for a specific module.
    
    Args:
        module_name: Name of the module requesting the logger
        
    Returns:
        Configured logger instance
    """
    return logger.bind(module=module_name)


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """Log function entry with parameters."""
    logger.debug(f"Calling {func_name} with params: {kwargs}")


def log_function_result(func_name: str, result: Any = None, success: bool = True) -> None:
    """Log function completion with result."""
    if success:
        logger.debug(f"Function {func_name} completed successfully")
        if result is not None:
            logger.debug(f"Function {func_name} result: {result}")
    else:
        logger.error(f"Function {func_name} failed")


def log_api_call(
    service: str, 
    method: str, 
    url: Optional[str] = None,
    status_code: Optional[int] = None,
    response_time: Optional[float] = None
) -> None:
    """Log external API calls."""
    log_data = {
        "service": service,
        "method": method,
        "url": url,
        "status_code": status_code,
        "response_time": response_time
    }
    
    if status_code and 200 <= status_code < 300:
        logger.info(f"API call to {service} successful", **log_data)
    else:
        logger.warning(f"API call to {service} failed or returned non-2xx status", **log_data)


def log_processing_stage(stage: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Log processing pipeline stages."""
    logger.info(f"Processing stage: {stage}", stage=stage, details=details or {})


def log_error_with_context(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    module: Optional[str] = None
) -> None:
    """Log errors with additional context information."""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
        "module": module
    }
    
    logger.error(f"Error in {module or 'unknown module'}: {error}", **error_data)