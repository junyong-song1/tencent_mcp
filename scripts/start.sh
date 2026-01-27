#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 Starting Tencent MCP Server (FastAPI)..."

# Check if already running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "⚠️ Server is already running. Use ./restart.sh to restart."
    exit 1
fi

# Also check for old app_v2.py
if pgrep -f "app_v2.py" > /dev/null; then
    echo "⚠️ Old app_v2.py is running. Killing it first..."
    pkill -9 -f "app_v2.py"
    sleep 1
fi

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Get port from .env or use default
PORT=${PORT:-8000}
if [ -f .env ]; then
    source .env
    PORT=${PORT:-8000}
fi

# Start FastAPI with uvicorn
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT > app.log 2>&1 &

echo "✅ Server started on http://localhost:$PORT"
echo "📄 Check app.log for details"
