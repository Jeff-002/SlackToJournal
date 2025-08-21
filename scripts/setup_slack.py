#!/usr/bin/env python3
"""
Slack setup helper for SlackToJournal.

This script helps users set up Slack integration with step-by-step guidance.
"""

import os
import json
import requests
from pathlib import Path


def print_header():
    print("🚀 SlackToJournal Slack Setup Helper")
    print("=" * 50)


def check_bot_token(token):
    """Test if bot token is valid."""
    if not token or not token.startswith('xoxb-'):
        return False, "Token should start with 'xoxb-'"
    
    try:
        response = requests.post(
            'https://slack.com/api/auth.test',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        data = response.json()
        
        if data.get('ok'):
            return True, {
                'team_id': data.get('team_id'),
                'team_name': data.get('team'),
                'user_id': data.get('user_id'),
                'user_name': data.get('user')
            }
        else:
            return False, data.get('error', 'Unknown error')
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def setup_direct_api():
    """Set up direct Slack API integration."""
    print("\n🤖 Setting up Direct Slack API Integration")
    print("-" * 40)
    
    print("1. Create a Slack App:")
    print("   • Go to https://api.slack.com/apps")
    print("   • Click 'Create New App' → 'From scratch'")
    print("   • Name it 'WorkJournal Bot' and select your workspace")
    
    print("\n2. Add Bot Token Scopes:")
    print("   • Go to 'OAuth & Permissions' in your app settings")
    print("   • Add these Bot Token Scopes:")
    print("     - channels:history (read public channel messages)")
    print("     - channels:read (view public channel info)")
    print("     - users:read (read user information)")
    print("     - search:read (search messages - optional, requires paid plan)")
    
    print("\n3. Install App to Workspace:")
    print("   • Click 'Install to Workspace' in your app settings")
    print("   • Authorize the app")
    print("   • Copy the 'Bot User OAuth Token' (starts with xoxb-)")
    
    print("\n4. Invite Bot to Channels:")
    print("   • In each channel you want to analyze, type:")
    print("   • /invite @WorkJournal Bot")
    
    # Get bot token from user
    while True:
        bot_token = input("\n🔑 Enter your Bot User OAuth Token (xoxb-...): ").strip()
        
        if not bot_token:
            print("❌ Token cannot be empty")
            continue
        
        print("🧪 Testing token...")
        is_valid, result = check_bot_token(bot_token)
        
        if is_valid:
            print(f"✅ Token is valid!")
            print(f"   • Team: {result['team_name']} ({result['team_id']})")
            print(f"   • Bot User: {result['user_name']} ({result['user_id']})")
            
            # Update .env file
            update_env_file(bot_token, result['team_id'])
            return True
        else:
            print(f"❌ Token test failed: {result}")
            retry = input("Try again? (y/N): ").lower()
            if retry != 'y':
                return False


def update_env_file(bot_token, team_id):
    """Update .env file with Slack configuration."""
    env_path = Path('.env')
    
    # Read existing .env or create new one
    env_lines = []
    if env_path.exists():
        env_lines = env_path.read_text().splitlines()
    
    # Remove existing Slack configuration
    env_lines = [line for line in env_lines if not line.startswith(('SLACK_BOT_TOKEN=', 'SLACK_WORKSPACE_ID='))]
    
    # Add new configuration
    env_lines.extend([
        f"SLACK_BOT_TOKEN={bot_token}",
        f"SLACK_WORKSPACE_ID={team_id}"
    ])
    
    # Write back to file
    env_path.write_text('\n'.join(env_lines))
    print(f"✅ Updated {env_path} with Slack configuration")


def setup_mcp_server():
    """Set up MCP server integration."""
    print("\n🔧 Setting up MCP Server Integration (Advanced)")
    print("-" * 50)
    
    print("This method requires running a separate MCP server.")
    print("It's more complex but provides additional features.")
    
    proceed = input("Do you want to proceed with MCP setup? (y/N): ").lower()
    if proceed != 'y':
        return False
    
    print("\n📦 Installing MCP Server...")
    print("Choose your installation method:")
    print("1. Node.js (npm)")
    print("2. Python (pip)")
    print("3. Manual setup")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == '1':
        print("\nRun these commands:")
        print("npm install -g @slack/mcp-server")
        print("slack-mcp-server --bot-token YOUR_BOT_TOKEN --port 3000")
    elif choice == '2':
        print("\nRun these commands:")
        print("pip install slack-mcp-python")
        print("slack-mcp --bot-token YOUR_BOT_TOKEN --port 3000")
    else:
        print("\nPlease refer to MCP documentation for manual setup.")
    
    mcp_url = input("\nEnter MCP server URL (default: http://localhost:3000): ").strip()
    if not mcp_url:
        mcp_url = "http://localhost:3000"
    
    # Test MCP server
    try:
        response = requests.get(f"{mcp_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ MCP server is running")
        else:
            print("⚠️  MCP server responded but might not be ready")
    except requests.RequestException:
        print("❌ Cannot connect to MCP server")
        print("Make sure the server is running before using SlackToJournal")
    
    # Update environment
    env_path = Path('.env')
    env_lines = []
    if env_path.exists():
        env_lines = env_path.read_text().splitlines()
    
    # Remove existing MCP configuration
    env_lines = [line for line in env_lines if not line.startswith('SLACK_MCP_SERVER_URL=')]
    
    # Add new configuration
    env_lines.append(f"SLACK_MCP_SERVER_URL={mcp_url}")
    
    # Write back to file
    env_path.write_text('\n'.join(env_lines))
    print(f"✅ Updated {env_path} with MCP configuration")
    
    return True


def test_integration():
    """Test the Slack integration."""
    print("\n🧪 Testing Slack Integration...")
    print("-" * 30)
    
    try:
        # Try to import and test
        import sys
        sys.path.append('src')
        
        from src.slack_integration.adapter import SlackAdapter
        from src.settings import SlackSettings
        
        # Create settings
        settings = SlackSettings()
        adapter = SlackAdapter(settings)
        
        info = adapter.get_integration_info()
        print(f"✅ Integration Type: {info['type']}")
        print(f"✅ Ready: {info['ready']}")
        
        if info['type'] == 'direct':
            print(f"✅ Bot Token: {'✓' if info['bot_token_configured'] else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    print_header()
    
    print("\nSlack integration can be set up in two ways:")
    print("1. 🤖 Direct API (Recommended - simpler setup)")
    print("2. 🔧 MCP Server (Advanced - more features)")
    
    choice = input("\nChoose integration method (1 or 2): ").strip()
    
    if choice == '1':
        success = setup_direct_api()
    elif choice == '2':
        success = setup_mcp_server()
    else:
        print("❌ Invalid choice")
        return
    
    if success:
        print("\n🎉 Slack integration setup completed!")
        
        # Test integration
        test_integration()
        
        print("\n📋 Next steps:")
        print("1. Make sure your bot is invited to the channels you want to analyze")
        print("2. Configure your other API keys (Gemini, Google Drive)")
        print("3. Run: uv run python -m src.main test --test-slack")
        print("4. Generate your first journal: uv run python -m src.main weekly")
    else:
        print("\n❌ Setup incomplete. Please try again or refer to the documentation.")


if __name__ == "__main__":
    main()