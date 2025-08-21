#!/usr/bin/env python3
"""
Setup script for SlackToJournal credentials.

This script helps users set up the necessary credentials and configuration
for SlackToJournal to work properly.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

def create_env_file():
    """Create .env file with template values."""
    env_path = Path(".env")
    
    if env_path.exists():
        print("ℹ️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            return
    
    env_content = """# SlackToJournal Configuration

# Slack Configuration
SLACK_MCP_SERVER_URL=http://localhost:3000
SLACK_WORKSPACE_ID=your-slack-workspace-id

# Gemini AI Configuration  
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_MAX_TOKENS=8192
GEMINI_TEMPERATURE=0.1

# Google Drive Configuration
GOOGLE_CREDENTIALS_FILE=configs/credentials/google_credentials.json
GOOGLE_FOLDER_ID=your-google-drive-folder-id

# Scheduling Configuration
SCHEDULE_CRON=0 17 * * 5
SCHEDULE_TIMEZONE=Asia/Taipei

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Application Configuration
APP_NAME=SlackToJournal
APP_VERSION=0.1.0
DEBUG=false
"""
    
    env_path.write_text(env_content)
    print(f"✅ Created {env_path}")
    print("📝 Please edit the .env file with your actual credentials")


def setup_directories():
    """Create necessary directories."""
    dirs_to_create = [
        "logs",
        "configs/credentials", 
        "backups",
        "exports"
    ]
    
    for dir_name in dirs_to_create:
        dir_path = Path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {dir_path}")


def create_sample_google_credentials():
    """Create sample Google credentials file."""
    creds_path = Path("configs/credentials/google_credentials.json")
    
    if creds_path.exists():
        print(f"ℹ️  {creds_path} already exists")
        return
    
    sample_creds = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id", 
        "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR-PRIVATE-KEY\\n-----END PRIVATE KEY-----\\n",
        "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
    }
    
    with open(creds_path, 'w') as f:
        json.dump(sample_creds, f, indent=2)
    
    print(f"📄 Created sample credentials file: {creds_path}")
    print("⚠️  Please replace with your actual Google service account credentials")


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import click
        import google.generativeai
        import googleapiclient
        import slack_sdk
        import pydantic
        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run 'uv sync' to install dependencies")
        return False


def main():
    """Main setup function."""
    print("🚀 SlackToJournal Setup Script")
    print("=" * 40)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n⚠️  Please install dependencies before continuing")
        return
    
    # Create directories
    print("\n📁 Setting up directories...")
    setup_directories()
    
    # Create .env file
    print("\n🔧 Setting up environment file...")
    create_env_file()
    
    # Create sample credentials
    print("\n🔑 Setting up credentials...")
    create_sample_google_credentials()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. 📝 Edit .env file with your actual API keys")
    print("2. 🔑 Replace google_credentials.json with your real credentials")
    print("3. 🧪 Run 'uv run python -m src.main test --test-all'")
    print("4. 📖 Run 'uv run python -m src.main weekly' to generate your first journal")
    print("\n📚 For more information, check the README.md file")


if __name__ == "__main__":
    main()