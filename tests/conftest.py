"""
Pytest configuration and fixtures for SlackToJournal tests.
"""

from pathlib import Path
from typing import Generator
import tempfile
import pytest

from src.settings import AppSettings, load_settings


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings() -> AppSettings:
    """Create test settings with minimal configuration."""
    return AppSettings(
        name="TestSlackToJournal",
        version="0.1.0-test",
        debug=True
    )


@pytest.fixture
def sample_env_file(temp_dir: Path) -> Path:
    """Create a sample .env file for testing."""
    env_file = temp_dir / ".env"
    env_content = """
GEMINI_API_KEY=test_api_key
SLACK_WORKSPACE_ID=test_workspace
GOOGLE_FOLDER_ID=test_folder_id
LOG_LEVEL=DEBUG
"""
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def sample_yaml_config(temp_dir: Path) -> Path:
    """Create a sample YAML config file for testing."""
    yaml_file = temp_dir / "settings.yaml"
    yaml_content = """
app:
  name: "TestSlackToJournal"
  version: "0.1.0-test"
  debug: true

slack:
  mcp_server_url: "http://localhost:3000"
  workspace_id: "test_workspace"

gemini:
  model: "gemini-2.0-flash-exp"
  max_tokens: 4096
  temperature: 0.2

google_drive:
  credentials_file: "test_credentials.json"

schedule:
  cron: "0 9 * * 1"
  timezone: "UTC"

logging:
  level: "DEBUG"
  file: "test.log"
"""
    yaml_file.write_text(yaml_content.strip())
    return yaml_file