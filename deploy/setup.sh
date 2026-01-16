#!/bin/bash
set -e

# Tencent MCP Slack Bot - EC2 Setup Script
# Run this script on a fresh EC2 instance (Ubuntu 22.04 recommended)

echo "=========================================="
echo "Tencent MCP Slack Bot - EC2 Setup"
echo "=========================================="

# Update system
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
echo "[2/7] Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git

# Create app directory
echo "[3/7] Setting up application directory..."
APP_DIR="/home/ubuntu/tencent_mcp"
if [ ! -d "$APP_DIR" ]; then
    git clone https://github.com/junyong-song1/tencent_mcp.git $APP_DIR
fi
cd $APP_DIR

# Create virtual environment
echo "[4/7] Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
echo "[5/7] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
echo "[6/7] Creating logs directory..."
mkdir -p logs
mkdir -p data

# Setup systemd service
echo "[7/7] Setting up systemd service..."
sudo cp deploy/tencent-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tencent-mcp

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create .env file with your credentials:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start tencent-mcp"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status tencent-mcp"
echo ""
echo "4. View logs:"
echo "   tail -f logs/app.log"
echo ""
