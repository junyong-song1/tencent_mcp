#!/bin/bash

# Tencent MCP Slack Bot - Setup Script

echo "🚀 Tencent MCP Slack Bot Setup"
echo "================================"
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "✓ Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "✓ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "✓ Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your Slack and Tencent API credentials."
else
    echo ""
    echo "✓ .env file already exists."
fi

# Create logs directory
mkdir -p logs

echo ""
echo "================================"
echo "✅ Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   - SLACK_BOT_TOKEN"
echo "   - SLACK_SIGNING_SECRET"
echo "   - SLACK_APP_TOKEN"
echo "   - TENCENT_API_URL"
echo ""
echo "2. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Run the bot:"
echo "   python app.py"
echo ""
echo "📖 For detailed setup instructions, see SETUP_GUIDE.md"
echo ""
