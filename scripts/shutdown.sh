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
pkill -9 -f "app.py" 2>/dev/null

# Kill any uvicorn on port 8000
pkill -9 -f "uvicorn.*8000" 2>/dev/null

# Wait for processes to terminate
sleep 1

# Double check
echo "🔍 Checking for lingering processes..."
ps aux | grep -E "(uvicorn|app_v2.py|app.py)" | grep -v grep

echo "🧹 Cleaning pycache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

echo "✅ All processes stopped."
