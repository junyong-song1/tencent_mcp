#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🛑 Stopping all Tencent MCP processes..."

# Kill FastAPI uvicorn processes
pkill -9 -f "uvicorn app.main:app" 2>/dev/null

# Kill old app_v2.py processes
pkill -9 -f "app_v2.py" 2>/dev/null

# Kill any uvicorn on port 8000
pkill -9 -f "uvicorn.*8000" 2>/dev/null

# Wait for processes to terminate
sleep 2

# Double check
echo "🔍 Checking for lingering processes..."
if pgrep -f "uvicorn app.main" > /dev/null || pgrep -f "app_v2.py" > /dev/null; then
    echo "⚠️ Some processes still running, force killing..."
    pkill -9 -f "uvicorn" 2>/dev/null
    pkill -9 -f "app_v2.py" 2>/dev/null
    sleep 1
fi

echo "🧹 Cleaning pycache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🚀 Starting Tencent MCP Server (FastAPI)..."

# Start FastAPI with uvicorn (logging handled by app)
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &

sleep 2

# Verify startup
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "✅ Server restarted successfully on http://localhost:8000"
    echo "📄 Check app.log for details"
else
    echo "❌ Server failed to start. Check app.log for errors."
    tail -20 app.log
fi
