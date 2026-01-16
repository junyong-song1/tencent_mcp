#!/bin/bash
set -e

# Tencent MCP Slack Bot - Update Script
# Run this script to pull latest changes and restart the service

APP_DIR="/home/ubuntu/tencent_mcp"
cd $APP_DIR

echo "=========================================="
echo "Updating Tencent MCP Slack Bot"
echo "=========================================="

# Pull latest changes
echo "[1/4] Pulling latest changes..."
git pull origin main

# Activate virtual environment
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

# Update dependencies
echo "[3/4] Updating dependencies..."
pip install -r requirements.txt

# Restart service
echo "[4/4] Restarting service..."
sudo systemctl restart tencent-mcp

echo ""
echo "Update complete!"
echo "Check status: sudo systemctl status tencent-mcp"
echo "View logs: tail -f logs/app.log"
