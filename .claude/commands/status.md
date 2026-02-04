# Status Skill

Check the current status of the Tencent MCP system and services.

## Usage

```
/status [component]
```

## Arguments

- `$ARGUMENTS` - Optional: `env`, `git`, `deps`, `ports`, or `all`

## Instructions

Based on the component requested:

1. **No arguments or `all`**: Show comprehensive status

2. **`env`**: Check environment configuration
   - Verify `.env` file exists
   - Check required variables are set (mask sensitive values)
   - Report any missing required variables

3. **`git`**: Show git status
   ```bash
   git status
   git log --oneline -5
   ```

4. **`deps`**: Check dependencies
   ```bash
   pip list --outdated
   pip check
   ```

5. **`ports`**: Check if required ports are in use
   ```bash
   lsof -i :8000 2>/dev/null || echo "Port 8000 is available"
   ```

6. **`process`**: Check running processes
   ```bash
   ps aux | grep -E "(uvicorn|mcp_server)" | grep -v grep
   ```

For `all`, run all checks and provide a summary table:
| Component | Status |
|-----------|--------|
| Environment | OK/Warning |
| Dependencies | OK/Outdated |
| Git | Clean/Modified |
| Server | Running/Stopped |
