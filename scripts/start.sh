#!/bin/bash

# SlackToJournal Startup Script

set -e

echo "🚀 Starting SlackToJournal..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found"
    echo "💡 Run 'uv sync' to set up the environment"
    exit 1
fi

# Check if configuration exists
if [ ! -f ".env" ]; then
    echo "❌ Configuration file (.env) not found"
    echo "💡 Run 'python scripts/setup_credentials.py' to set up configuration"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    echo "📄 Loading environment variables..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for required environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY not set"
    echo "💡 Please configure your Gemini API key in .env file"
    exit 1
fi

if [ -z "$SLACK_WORKSPACE_ID" ]; then
    echo "⚠️  SLACK_WORKSPACE_ID not set"
    echo "💡 Please configure your Slack workspace ID in .env file"
fi

# Create log directory
mkdir -p logs

# Run the application
echo "✅ Environment ready"
echo "🎯 Generating weekly journal..."

# Execute the main command
uv run python -m src.main weekly --user "${USER_NAME:-Team Member}" --team "${TEAM_NAME:-Development Team}"

echo "✅ SlackToJournal completed successfully!"