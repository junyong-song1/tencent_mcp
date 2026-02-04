# Debug Skill

Help debug issues in the Tencent MCP application.

## Usage

```
/debug [component] [issue-description]
```

## Arguments

- `$ARGUMENTS` - Component to debug and optional issue description

## Instructions

Based on the component specified:

1. **`slack`**: Debug Slack integration issues
   - Check Slack token validity (format check only)
   - Review recent handler code in `app/slack/handlers/`
   - Look for common issues: missing ack(), wrong event types
   - Check Socket Mode connection setup in `app/main.py`

2. **`tencent` or `api`**: Debug Tencent Cloud API issues
   - Review `app/services/tencent_client.py`
   - Check credential configuration
   - Look for common SDK errors and their solutions
   - Verify region settings

3. **`mcp`**: Debug MCP server issues
   - Check `mcp_server/server.py` for startup errors
   - Verify resource and tool registrations
   - Check stdio transport configuration

4. **`schedule`**: Debug scheduling issues
   - Review `app/services/schedule_manager.py`
   - Check APScheduler configuration in `app/services/scheduler.py`
   - Verify notification setup

5. **`alert`**: Debug alert monitoring
   - Review `app/services/alert_monitor.py`
   - Check alert severity mapping
   - Verify notification channel settings

6. **`logs`**: Show recent logs
   ```bash
   # Check for any Python errors in recent output
   tail -100 logs/*.log 2>/dev/null || echo "No log files found"
   ```

For any debug request:
1. Identify the relevant source files
2. Look for common error patterns
3. Check configuration requirements
4. Suggest diagnostic steps
5. Provide potential fixes
