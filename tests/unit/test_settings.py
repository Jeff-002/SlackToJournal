"""
Unit tests for settings module.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from src.settings import (
    AppSettings,
    SlackSettings,
    GeminiSettings,
    GoogleDriveSettings,
    LoggingSettings,
    load_settings
)


class TestSlackSettings:
    """Test Slack configuration."""
    
    def test_default_values(self):
        """Test default Slack settings."""
        settings = SlackSettings(workspace_id="test_workspace")
        assert settings.mcp_server_url == "http://localhost:3000"
        assert settings.workspace_id == "test_workspace"
    
    def test_validation_missing_workspace(self):
        """Test validation fails without workspace ID."""
        with pytest.raises(ValidationError):
            SlackSettings()


class TestGeminiSettings:
    """Test Gemini AI configuration."""
    
    def test_default_values(self):
        """Test default Gemini settings."""
        settings = GeminiSettings(api_key="test_key")
        assert settings.model == "gemini-2.0-flash-exp"
        assert settings.max_tokens == 8192
        assert settings.temperature == 0.1
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        with pytest.raises(ValidationError):
            GeminiSettings(api_key="test", temperature=-0.1)
        
        with pytest.raises(ValidationError):
            GeminiSettings(api_key="test", temperature=2.1)
        
        # Valid temperatures
        settings = GeminiSettings(api_key="test", temperature=0.0)
        assert settings.temperature == 0.0
        
        settings = GeminiSettings(api_key="test", temperature=2.0)
        assert settings.temperature == 2.0


class TestLoggingSettings:
    """Test logging configuration."""
    
    def test_default_values(self):
        """Test default logging settings."""
        settings = LoggingSettings()
        assert settings.level == "INFO"
        assert settings.file == Path("logs/app.log")
    
    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = LoggingSettings(level=level)
            assert settings.level == level
        
        # Test case insensitive
        settings = LoggingSettings(level="debug")
        assert settings.level == "DEBUG"
        
        # Test invalid level
        with pytest.raises(ValidationError):
            LoggingSettings(level="INVALID")


class TestAppSettings:
    """Test main application settings."""
    
    def test_default_initialization(self):
        """Test default app settings initialization."""
        # Create minimal settings to avoid validation errors
        settings = AppSettings()
        assert settings.name == "SlackToJournal"
        assert settings.version == "0.1.0"
        assert settings.debug is False
    
    def test_nested_settings(self):
        """Test nested settings configuration."""
        settings = AppSettings()
        assert isinstance(settings.slack, SlackSettings)
        assert isinstance(settings.gemini, GeminiSettings)
        assert isinstance(settings.google_drive, GoogleDriveSettings)
        assert isinstance(settings.logging, LoggingSettings)


class TestLoadSettings:
    """Test settings loading functionality."""
    
    def test_load_from_yaml(self, sample_yaml_config):
        """Test loading settings from YAML file."""
        settings = AppSettings.from_yaml(sample_yaml_config)
        assert settings.name == "TestSlackToJournal"
        assert settings.slack.workspace_id == "test_workspace"
        assert settings.gemini.max_tokens == 4096
        assert settings.schedule.timezone == "UTC"
    
    def test_load_nonexistent_yaml(self, temp_dir):
        """Test loading from non-existent YAML file."""
        nonexistent_file = temp_dir / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            AppSettings.from_yaml(nonexistent_file)
    
    def test_load_settings_function(self, sample_yaml_config, sample_env_file):
        """Test load_settings function with multiple sources."""
        settings = load_settings(yaml_path=sample_yaml_config, env_file=sample_env_file)
        assert settings.name == "TestSlackToJournal"  # From YAML
        assert settings.debug is True  # From YAML