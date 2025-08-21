# SlackToJournal

AI-powered automation tool that reads Slack workspace content and generates structured work journals using Model Context Protocol (MCP) and Gemini 2.5 AI.

## Features

- 🚀 **Slack Integration**: Connect to Slack workspaces via MCP
- 🤖 **AI-Powered Content Analysis**: Intelligent work content extraction using Gemini 2.5
- 📁 **Google Drive Integration**: Automated journal upload to Google Drive
- ⏰ **Scheduled Execution**: Weekly automatic journal generation
- 🔧 **Modular Architecture**: Clean, maintainable Python codebase

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set up configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Run the application**:
   ```bash
   uv run python src/main.py
   ```

## Architecture

- `src/slack_integration/` - Slack MCP client and data extraction
- `src/ai_processing/` - Gemini 2.5 AI content analysis
- `src/drive_integration/` - Google Drive file operations
- `src/scheduler/` - Task scheduling and automation
- `src/journal/` - Journal formatting and templates
- `src/core/` - Shared utilities and configuration

## Development

```bash
# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Code formatting
uv run black src tests
uv run isort src tests

# Type checking
uv run mypy src
```

## Configuration

See `configs/settings.yaml` for detailed configuration options.
