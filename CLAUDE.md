# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Slack Bot for managing Tencent Cloud StreamLive (MDL) and StreamLink (MDC) resources. Users interact via the `/tencent` slash command or by mentioning the bot. The bot provides an interactive modal dashboard for searching, filtering, and controlling media streaming channels.

## Commands

### Running the Application

```bash
# Setup virtual environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the bot (foreground - FastAPI + Slack)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run the bot (background via script)
./scripts/start.sh
./scripts/restart.sh
./scripts/shutdown.sh
```

### Testing

```bash
# Run all tests
pytest

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=app tests/
```

### Linting

```bash
black app/ tests/
flake8 app/ tests/
```

## Architecture

### Request Flow

```
HTTP/WebSocket → FastAPI (app/main.py)
                     ↓
                 Slack Bolt (Socket Mode) ← Slack Events
                     ↓
              app/slack/handlers/* → Services → Tencent Cloud APIs
                     ↓
              app/slack/ui/* (Block Kit) → Slack Modal/Message
```

### Core Modules

#### Main Application (`app/`)

- **app/main.py**: FastAPI entry point with lifespan management. Integrates Slack Bolt (Socket Mode) running in background thread, APScheduler for background tasks, and REST API endpoints.

- **app/config.py**: Pydantic BaseSettings for configuration management. Loads from environment variables with type validation.

#### Services (`app/services/`)

- **tencent_client.py**: Wrapper around Tencent Cloud SDK with async support via `asyncio.to_thread()`. Implements TTL caching and parallel fetching.

- **schedule_manager.py**: Broadcast schedule management with thread-safe operations. Supports CRUD operations and notification tracking.

- **scheduler.py**: APScheduler-based task scheduler for background jobs.

- **notification.py**: Notification service for schedule alerts.

- **linkage.py**: Resource linkage service matching StreamLink outputs to StreamLive inputs.

#### Slack Integration (`app/slack/`)

- **handlers/commands.py**: `/tencent` slash command handler
- **handlers/dashboard.py**: Dashboard modal interactions (filter, search, pagination)
- **handlers/schedule_tab.py**: Schedule tab CRUD operations
- **handlers/status_tab.py**: Status tab display
- **handlers/control.py**: Start/Stop/Restart operations (individual and integrated)

- **ui/common.py**: Shared Block Kit components
- **ui/dashboard.py**: Dashboard modal builder
- **ui/schedule.py**: Schedule modal builder
- **ui/status.py**: Status display builder

#### Models (`app/models/`)

- **enums.py**: ServiceType, ChannelStatus, ScheduleStatus
- **resource.py**: Resource, InputAttachment, ResourceHierarchy
- **schedule.py**: BroadcastSchedule
- **task.py**: ScheduledTask

#### Storage (`app/storage/`)

- **base.py**: Abstract storage interface
- **json_storage.py**: JSON file-based storage implementation

### Resource Hierarchy

StreamLink flows feed into StreamLive channels. Linkage is determined by matching StreamLink `output_urls` to StreamLive `input_endpoints`.

```
StreamLink Flow (output_urls: ["rtmp://..."])
    ↓ feeds into
StreamLive Channel (input_endpoints: ["rtmp://..."])
```

### Control Options

- **Individual Control**: Start/Stop parent (StreamLive) or child (StreamLink) separately
- **Integrated Control**: Start/Stop parent and all linked children together

### Threading Model

- FastAPI runs with uvicorn's async event loop
- Slack Bolt runs in Socket Mode in a daemon thread
- APScheduler uses BackgroundScheduler for periodic tasks
- TencentCloudClient uses ThreadPoolExecutor for parallel API calls
- Schedule operations protected by threading.Lock

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/resources` | GET | List all resources |
| `/api/v1/schedules` | GET | List schedules |
| `/api/v1/schedules` | POST | Create schedule |
| `/docs` | GET | Swagger UI |

## Environment Variables

Required in `.env`:
- `SLACK_BOT_TOKEN` (xoxb-...)
- `SLACK_APP_TOKEN` (xapp-...)
- `SLACK_SIGNING_SECRET`
- `TENCENT_SECRET_ID`
- `TENCENT_SECRET_KEY`
- `TENCENT_REGION` (default: ap-seoul)

Optional:
- `ALLOWED_USERS` - Comma-separated Slack user IDs for access control
- `DEBUG` - Enable debug logging
- `NOTIFICATION_CHANNEL` - Slack channel for schedule notifications

Performance Tuning (optional):
- `CACHE_TTL_SECONDS` - Cache TTL (default: 120)
- `THREAD_POOL_WORKERS` - Parallel workers (default: 10)
- `API_REQUEST_TIMEOUT` - SDK timeout in seconds (default: 20)
- `MAX_PARENT_GROUPS` - Max groups in modal (default: 30)
- `MAX_BULK_OPERATIONS` - Max bulk ops (default: 10)
- `SCHEDULER_CLEANUP_INTERVAL` - Cleanup interval in seconds (default: 3600)
- `SCHEDULER_TASK_MAX_AGE_HOURS` - Task retention hours (default: 24)

## Legacy Code

Old monolithic implementation is preserved in `legacy/` folder for reference. These files are deprecated and should not be modified. See `legacy/README.md` for migration mapping.
