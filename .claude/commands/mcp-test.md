# MCP Test Skill

Test MCP server resources and tools.

## Usage

```
/mcp-test [resource-or-tool]
```

## Arguments

- `$ARGUMENTS` - Optional: resource name, tool name, or `all`

## Instructions

This skill helps test the MCP server functionality.

1. **No arguments**: List available MCP resources and tools
   - Read `mcp_server/resources.py` to list resources
   - Read `mcp_server/tools.py` to list tools

2. **`resources`**: Show all MCP resources
   - Parse `mcp_server/resources.py`
   - List each resource with its URI pattern and description

3. **`tools`**: Show all MCP tools
   - Parse `mcp_server/tools.py`
   - List each tool with its name, parameters, and description

4. **`server`**: Test MCP server startup
   ```bash
   timeout 5 python -c "from mcp_server.server import main; print('MCP Server imports OK')" 2>&1
   ```

5. **Specific resource/tool name**: Show detailed info about that item
   - Find the definition in resources.py or tools.py
   - Show the full implementation
   - Explain what it does and how to use it

Available MCP Resources:
- `mdl://channels` - StreamLive channels
- `mdc://flows` - StreamLink flows
- `schedule://list` - Broadcast schedules
- `mdp://streampackage` - StreamPackage channels
- `css://streams` - CSS live streams
- `alerts://list` - Channel alerts

Available MCP Tools:
- `start_resource` - Start a channel/flow
- `stop_resource` - Stop a channel/flow
- `search_resources` - Search by name/status
- `create_schedule` - Create broadcast schedule
- `get_full_status` - Get comprehensive status
- `get_channel_alerts` - Get alerts for a channel
