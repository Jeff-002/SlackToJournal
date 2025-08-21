#!/bin/bash

# SlackToJournal Deployment Script

set -e

echo "🚀 SlackToJournal Deployment Script"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

# Update system packages (optional)
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y || echo "⚠️  System update skipped"

# Install Python and uv if not present
if ! command -v uv &> /dev/null; then
    echo "📥 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

echo "✅ uv version: $(uv --version)"

# Set up Python environment
echo "🐍 Setting up Python environment..."
uv sync

# Run setup script
echo "🔧 Running setup script..."
uv run python scripts/setup_credentials.py

# Run tests
echo "🧪 Running tests..."
uv run python -m src.main test --test-all || echo "⚠️  Some tests failed, please check configuration"

# Set up systemd service (optional)
read -p "📋 Do you want to set up systemd service for scheduled execution? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Setting up systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/slack-to-journal.service > /dev/null <<EOF
[Unit]
Description=SlackToJournal Weekly Journal Generator
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin:$PATH
ExecStart=$(pwd)/scripts/start.sh

[Install]
WantedBy=multi-user.target
EOF

    # Create timer file
    sudo tee /etc/systemd/system/slack-to-journal.timer > /dev/null <<EOF
[Unit]
Description=Run SlackToJournal Weekly
Requires=slack-to-journal.service

[Timer]
OnCalendar=Fri 17:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable and start timer
    sudo systemctl daemon-reload
    sudo systemctl enable slack-to-journal.timer
    sudo systemctl start slack-to-journal.timer
    
    echo "✅ Systemd service and timer configured"
    echo "📅 Journal will be generated every Friday at 5 PM"
    echo "🔍 Check status with: sudo systemctl status slack-to-journal.timer"
fi

# Set up log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/slack-to-journal > /dev/null <<EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    copytruncate
    notifempty
    create 0644 $USER $USER
}
EOF

echo "✅ Log rotation configured"

# Final checks
echo "🔍 Final verification..."

# Check configuration
if [ -f ".env" ]; then
    echo "✅ Environment file exists"
else
    echo "❌ Environment file missing"
fi

# Check credentials
if [ -f "configs/credentials/google_credentials.json" ]; then
    echo "✅ Google credentials file exists"
else
    echo "❌ Google credentials file missing"
fi

# Test run
echo "🧪 Testing journal generation..."
uv run python -m src.main status

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your API keys in .env file"
echo "2. Add your Google service account credentials"
echo "3. Test with: uv run python -m src.main weekly"
echo "4. Check logs in logs/ directory"
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
echo "📅 Systemd timer is active - journals will be generated automatically"
echo "🔧 Manage with: sudo systemctl [start|stop|status] slack-to-journal.timer"
fi
echo ""