# Slack Skill

Work with Slack Bot handlers and UI components.

## Usage

```
/slack [action] [component]
```

## Arguments

- `$ARGUMENTS` - Action (handlers, ui, events, command) and optional component name

## Instructions

1. **`handlers`**: List all Slack handlers
   - Read `app/slack/handlers/` directory
   - Show each handler file with its main functions
   - Key handlers:
     - `commands.py` - `/tencent` slash command
     - `dashboard.py` - Dashboard modal interactions
     - `schedule_tab.py` - Schedule CRUD
     - `status_tab.py` - Status display
     - `control.py` - Start/Stop/Restart operations
     - `natural_language.py` - NLP queries

2. **`ui`**: List UI components
   - Read `app/slack/ui/` directory
   - Show Block Kit component builders:
     - `common.py` - Shared components
     - `dashboard.py` - Dashboard modal
     - `schedule.py` - Schedule modal
     - `status.py` - Status display

3. **`events`**: Show handled Slack events
   - Parse handler decorators for event types
   - Common events:
     - `command` - Slash commands
     - `action` - Button/select interactions
     - `view_submission` - Modal submissions
     - `shortcut` - Global shortcuts

4. **`command [name]`**: Show specific command handler
   - Find the handler function
   - Show its implementation
   - Explain the flow

5. **`add [handler-type]`**: Help add new handler
   - Provide template for new handler
   - Show where to register it
   - Example patterns from existing handlers

Key patterns:
- All handlers use `@app.command()`, `@app.action()`, or `@app.view()` decorators
- Handlers must call `ack()` immediately
- UI built with Block Kit JSON structures
- Modal updates use `client.views_update()`
