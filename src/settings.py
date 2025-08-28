"""
Global application settings and configuration management.

This module provides centralized configuration management using Pydantic Settings
with support for environment variables, YAML configuration files, and validation.
"""

from pathlib import Path
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from dotenv import load_dotenv


class SlackSettings(BaseSettings):
    """Slack integration configuration."""
    
    target_channels: Optional[List[str]] = Field(
        default=None,
        description="Specific channel names to monitor (comma-separated)"
    )
    exclude_keywords: Optional[List[str]] = Field(
        default=["sync"],
        description="Keywords to exclude from messages (case-insensitive, comma-separated)"
    )
    
    @field_validator('target_channels', mode='before')
    @classmethod
    def parse_target_channels(cls, v):
        """Parse comma-separated channel names from environment variable."""
        if isinstance(v, str) and v.strip():
            return [ch.strip() for ch in v.split(',') if ch.strip()]
        return v
    
    @field_validator('exclude_keywords', mode='before')
    @classmethod
    def parse_exclude_keywords(cls, v):
        """Parse comma-separated exclude keywords from environment variable."""
        if isinstance(v, str) and v.strip():
            return [kw.strip().lower() for kw in v.split(',') if kw.strip()]
        elif isinstance(v, list):
            return [kw.lower() if isinstance(kw, str) else str(kw).lower() for kw in v]
        return v or ["sync"]
    
    model_config = SettingsConfigDict(env_prefix="SLACK_")


class GeminiSettings(BaseSettings):
    """Gemini AI configuration."""
    
    api_key: str = Field(default="", description="Gemini API key")
    model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name"
    )
    max_tokens: int = Field(
        default=8192,
        description="Maximum tokens per request"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for AI responses"
    )
    
    model_config = SettingsConfigDict(env_prefix="GEMINI_")


class GoogleDriveSettings(BaseSettings):
    """Google Drive integration configuration."""
    
    credentials_file: Path = Field(
        default=Path("configs/credentials/google_credentials.json"),
        description="Path to Google credentials JSON file"
    )
    folder_id: str = Field(
        default="",
        description="Google Drive folder ID for journal uploads"
    )
    
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")
    
    @field_validator("credentials_file")
    def validate_credentials_file(cls, v: Path) -> Path:
        """Validate credentials file path."""
        if isinstance(v, str):
            v = Path(v)
        return v.resolve()


class ScheduleSettings(BaseSettings):
    """Task scheduling configuration."""
    
    cron: str = Field(
        default="0 17 * * 5",
        description="Cron expression for scheduling (default: Friday 5PM)"
    )
    timezone: str = Field(
        default="Asia/Taipei",
        description="Timezone for scheduling"
    )
    
    model_config = SettingsConfigDict(env_prefix="SCHEDULE_")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    file: Optional[Path] = Field(
        default=Path("logs/app.log"),
        description="Log file path"
    )
    
    model_config = SettingsConfigDict(env_prefix="LOG_")
    
    @field_validator("level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v
    
    @field_validator("file")
    def validate_log_file(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate and create log file directory."""
        if v is None:
            return None
        if isinstance(v, str):
            v = Path(v)
        v = v.resolve()
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class AppSettings(BaseSettings):
    """Main application settings."""
    
    name: str = Field(default="SlackToJournal", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Sub-configurations
    slack: SlackSettings = Field(default_factory=SlackSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    google_drive: GoogleDriveSettings = Field(default_factory=GoogleDriveSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AppSettings":
        """Load settings from YAML file."""
        if not yaml_path.exists():
            raise FileNotFoundError(f"Settings file not found: {yaml_path}")
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Convert nested dict to settings objects
        settings_data = {}
        for key, value in data.items():
            if key == "slack" and isinstance(value, dict):
                settings_data["slack"] = SlackSettings(**value)
            elif key == "gemini" and isinstance(value, dict):
                settings_data["gemini"] = GeminiSettings(**value)
            elif key == "google_drive" and isinstance(value, dict):
                settings_data["google_drive"] = GoogleDriveSettings(**value)
            elif key == "schedule" and isinstance(value, dict):
                settings_data["schedule"] = ScheduleSettings(**value)
            elif key == "logging" and isinstance(value, dict):
                settings_data["logging"] = LoggingSettings(**value)
            else:
                settings_data[key] = value
        
        return cls(**settings_data)


def load_settings(
    yaml_path: Optional[Path] = None,
    env_file: Optional[Path] = None
) -> AppSettings:
    """
    Load application settings from multiple sources.
    
    Priority order:
    1. Environment variables
    2. YAML configuration file
    3. Default values
    
    Args:
        yaml_path: Path to YAML configuration file
        env_file: Path to environment file (.env)
        
    Returns:
        Configured AppSettings instance
    """
    # Load .env file explicitly
    if env_file and env_file.exists():
        load_dotenv(env_file)
    else:
        # Try to load from default .env location
        load_dotenv()
    
    # Start with defaults and environment variables
    settings = AppSettings()
    
    # Override with YAML configuration if provided
    if yaml_path and yaml_path.exists():
        yaml_settings = AppSettings.from_yaml(yaml_path)
        # Merge settings (environment variables take precedence)
        settings = AppSettings(
            **{
                **yaml_settings.model_dump(),
                **{k: v for k, v in settings.model_dump().items() if v != settings.__fields__[k].default}
            }
        )
    
    return settings


# Global settings instance
_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Get global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        # Try to load from default locations
        yaml_path = Path("configs/settings.yaml")
        env_path = Path(".env")
        _settings = load_settings(
            yaml_path=yaml_path if yaml_path.exists() else None,
            env_file=env_path if env_path.exists() else None
        )
    return _settings


def reload_settings(
    yaml_path: Optional[Path] = None,
    env_file: Optional[Path] = None
) -> AppSettings:
    """Reload settings from files (useful for testing or runtime config changes)."""
    global _settings
    _settings = load_settings(yaml_path=yaml_path, env_file=env_file)
    return _settings