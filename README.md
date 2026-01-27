# Tencent Cloud MCP

Tencent Cloud StreamLive (MDL) and StreamLink (MDC) 리소스 관리를 위한 통합 솔루션.

**두 가지 인터페이스를 제공합니다:**
1. **Slack Bot** - 사용자가 Slack에서 직접 명령어로 제어
2. **MCP Server** - AI 애플리케이션(Claude Desktop, Cursor 등)에서 사용

## Features

- 🔍 **Search & Filter** - Find channels by name, status, or service type
- 📊 **Interactive Dashboard** - Modal-based UI with real-time status
- ▶️ **Control Resources** - Start/Stop channels directly from Slack
- 🔗 **Hierarchy View** - See StreamLive → StreamLink relationships
- 📅 **Schedule Management** - Plan and track broadcast schedules
- ⚡ **Fast Loading** - Parallel fetching with intelligent caching
- 🔄 **Integrated Control** - Start/Stop linked resources together
- 🤖 **MCP Protocol** - AI 애플리케이션과 통합 (개발자용, 선택사항)

> **💡 일반 사용자는 Slack만 사용하면 됩니다!**  
> MCP는 개발/자동화가 필요한 경우에만 설정하세요.  
> [사용자 역할별 가이드](docs/user-roles-guide.md) 참조

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
# Port is configured in .env file (default: 3000)
uvicorn app.main:app --host 0.0.0.0 --port 3000

# Or use scripts
./scripts/start.sh
./scripts/restart.sh
./scripts/shutdown.sh
```

## Usage

### Slack Bot

**대시보드 (제어 작업):**
```
/tencent           # Open dashboard
/tencent help      # Show help
/tencent [keyword] # Search resources
```

**자연어 조회 (채널에서 멘션):**
```
@tencent-bot KBO 채널 상태 확인해줘
@tencent-bot channel-123 상태 알려줘
@tencent-bot 모든 채널 목록 보여줘
@tencent-bot StreamLive 채널 목록 보여줘
```

### MCP Server (AI Applications)

Claude Desktop 또는 Cursor에서 자연어로 요청:

```
"모든 StreamLive 채널 목록을 보여줘"
"KBO 관련 채널을 검색해줘"
"channel-123의 입력 상태가 main인지 backup인지 확인해줘"
"channel-123과 연결된 모든 StreamLink 플로우를 함께 시작해줘"
"StreamPackage 채널 목록을 보여줘"
"sp-channel-123의 입력 상태 확인해줘"
"CSS 활성 스트림 목록을 보여줘"
"channel-123의 전체 상태를 확인해줘 (StreamLive + StreamPackage + CSS)"
```

**MCP 사용 방법:** [MCP 사용 방법 완전 정리](docs/mcp-usage-explained.md) ← **먼저 읽어보세요!**  
**MCP 빠른 시작:** [MCP Quick Start Guide](docs/mcp-quick-start.md)  
**상세 설정:** [MCP Setup Guide](docs/mcp-setup.md)

## Documentation

| Document | Description |
|----------|-------------|
| [📘 Setup Guide](docs/setup.md) | Installation and configuration |
| [🏗️ Architecture](docs/architecture.md) | System design and components |
| [📖 API Reference](docs/api-reference.md) | Commands and internal APIs |
| [🔧 Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [🚀 MCP Quick Start](docs/mcp-quick-start.md) | MCP 빠른 시작 가이드 (3단계) |
| [🤖 MCP Setup](docs/mcp-setup.md) | MCP Server 상세 설정 가이드 |
| [📊 StreamPackage & CSS](docs/streampackage-css-integration.md) | StreamPackage and CSS integration guide |
| [📋 CSS & StreamPackage 상세](docs/css-streampackage-details.md) | CSS & StreamPackage 확인 가능한 모든 정보 |
| [📈 통합 로그 분석](docs/integrated-log-analysis.md) | 통합 로그 조회 및 분석 |
| [🎬 OTT Operations](docs/ott-operations-guide.md) | OTT 미디어 운영 활용 가이드 |
| [🔔 Detailed Alerts](docs/detailed-alert-guide.md) | 상세 알림 시스템 가이드 |

## Project Structure

```
tencent_mcp/
├── mcp_server/                   # MCP Server (for AI applications)
│   ├── __init__.py
│   ├── __main__.py               # Module entry point
│   ├── server.py                 # MCP server main
│   ├── resources.py              # MCP Resources
│   └── tools.py                  # MCP Tools
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
