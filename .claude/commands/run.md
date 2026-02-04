# Run Skill

Start the Tencent MCP application servers.

## Usage

```
/run [server-type]
```

## Arguments

- `$ARGUMENTS` - Server type: `slack`, `mcp`, or `both` (default: slack)

## Instructions

Based on the server type requested:

1. **`slack` or no argument**: Start the Slack Bot with FastAPI
   ```bash
   source venv/bin/activate 2>/dev/null || true
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **`mcp`**: Start the MCP Server for AI applications
   ```bash
   source venv/bin/activate 2>/dev/null || true
   python -m mcp_server
   ```

3. **`both`**: Start both servers (in separate terminals/processes)
   - First, start MCP server in background
   - Then start Slack bot

4. **`script`**: Use the start script
   ```bash
   ./scripts/start.sh
   ```

Before starting:
- Check if `.env` file exists and has required variables
- Verify virtual environment is set up
- Check if port 8000 is available (for Slack bot)

Required environment variables:
- SLACK_BOT_TOKEN
- SLACK_APP_TOKEN
- SLACK_SIGNING_SECRET
- TENCENT_SECRET_ID
- TENCENT_SECRET_KEY
