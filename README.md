# Tencent MCP Slack Bot

Slack Bot for managing Tencent Cloud StreamLive (MDL) and StreamLink (MDC) resources.

## Features

- 🔍 **Search & Filter** - Find channels by name, status, or service type
- 📊 **Interactive Dashboard** - Modal-based UI with real-time status
- ▶️ **Control Resources** - Start/Stop channels directly from Slack
- 🔗 **Hierarchy View** - See StreamLive → StreamLink relationships
- 📅 **Schedule Management** - Plan and track broadcast schedules
- ⚡ **Fast Loading** - Parallel fetching with intelligent caching
- 🔄 **Integrated Control** - Start/Stop linked resources together

## Quick Start

```bash
# Clone & setup
cd tencent_mcp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Configure .env with your credentials
# (See docs/setup.md for detailed instructions)

# Run (FastAPI + Slack)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or use scripts
./scripts/start.sh
./scripts/restart.sh
./scripts/shutdown.sh
```

## Usage

```
/tencent           # Open dashboard
/tencent help      # Show help
/tencent [keyword] # Search resources
```

## Documentation

| Document | Description |
|----------|-------------|
| [📘 Setup Guide](docs/setup.md) | Installation and configuration |
| [🏗️ Architecture](docs/architecture.md) | System design and components |
| [📖 API Reference](docs/api-reference.md) | Commands and internal APIs |
| [🔧 Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |

## Project Structure

```
tencent_mcp/
├── app/                          # Main application (FastAPI + Slack Bolt)
│   ├── main.py                   # Entry point
│   ├── config.py                 # Pydantic settings
│   ├── api/                      # REST API
│   │   ├── dependencies.py       # Dependency injection
│   │   └── routes/               # API routes
│   │       ├── health.py         # Health check
│   │       ├── resources.py      # Resource endpoints
│   │       └── schedules.py      # Schedule endpoints
│   ├── slack/                    # Slack integration
│   │   ├── handlers/             # Event handlers
│   │   │   ├── commands.py       # /tencent command
│   │   │   ├── dashboard.py      # Dashboard interactions
│   │   │   ├── schedule_tab.py   # Schedule management
│   │   │   ├── status_tab.py     # Status tab
│   │   │   └── control.py        # Start/Stop/Restart
│   │   └── ui/                   # Block Kit UI
│   │       ├── common.py         # Shared components
│   │       ├── dashboard.py      # Dashboard modal
│   │       ├── schedule.py       # Schedule modal
│   │       └── status.py         # Status display
│   ├── services/                 # Business logic
│   │   ├── tencent_client.py     # Tencent Cloud API
│   │   ├── schedule_manager.py   # Schedule management
│   │   ├── scheduler.py          # APScheduler service
│   │   ├── notification.py       # Notifications
│   │   └── linkage.py            # Resource linking
│   ├── models/                   # Pydantic models
│   │   ├── enums.py              # Status enums
│   │   ├── resource.py           # Resource models
│   │   ├── schedule.py           # Schedule model
│   │   └── task.py               # Task model
│   └── storage/                  # Data persistence
│       ├── base.py               # Abstract interface
│       └── json_storage.py       # JSON file storage
├── tests/                        # Test files
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── data/                         # Data storage (JSON files)
│   ├── broadcast_schedules.json  # Schedule data
│   └── scheduled_tasks.json      # Task data
├── scripts/                      # Shell scripts
├── docs/                         # Documentation
├── legacy/                       # Old implementation (reference)
├── requirements.txt              # Python dependencies
└── .env                          # Environment variables
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/resources` | GET | List all resources |
| `/api/v1/schedules` | GET | List schedules |
| `/api/v1/schedules` | POST | Create schedule |
| `/docs` | GET | Swagger UI |

## Requirements

- Python 3.8+
- Slack Workspace with Bot permissions
- Tencent Cloud account with MDL/MDC access

## Testing

```bash
# Run all tests
pytest

# Run unit tests
pytest tests/unit/

# Run with coverage
pytest --cov=app tests/
```

## License

MIT
