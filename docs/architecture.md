# Tencent MCP - Architecture

## System Overview

```
┌─────────────────┐
│   Slack         │
│   Workspace     │
└────────┬────────┘
         │ Socket Mode (WebSocket)
         │
┌────────▼────────────────────────────────────────────┐
│              Slack Bot Application                   │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Handlers     │  │  Slack UI    │  │  Command  │ │
│  │ (app_v2.py)  │  │ (slack_ui.py)│  │  Agent    │ │
│  │              │  │              │  │           │ │
│  │ - /tencent   │  │ - Block Kit  │  │ - NLP     │ │
│  │ - Mentions   │  │ - Modals     │  │ - Intent  │ │
│  │ - Actions    │  │ - Buttons    │  │           │ │
│  └──────┬───────┘  └──────────────┘  └───────────┘ │
│         │                                           │
│  ┌──────▼───────────────────────────────────────┐  │
│  │         Tencent Cloud Client                  │  │
│  │       (tencent_cloud_client.py)               │  │
│  │                                               │  │
│  │  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │ MDL Client  │  │  MDC Client         │    │  │
│  │  │ (StreamLive)│  │  (StreamLink)       │    │  │
│  │  └─────────────┘  └─────────────────────┘    │  │
│  │  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │ MDP Client  │  │  Live Client        │    │  │
│  │  │(StreamPackage)│ │  (CSS)             │    │  │
│  │  └─────────────┘  └─────────────────────┘    │  │
│  │                                               │  │
│  │  - list_mdl_channels()                        │  │
│  │  - list_streamlink_inputs()                   │  │
│  │  - list_streampackage_channels()              │  │
│  │  - list_css_streams()                        │  │
│  │  - start/stop operations                      │  │
│  │  - Cache management                           │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │
         │ HTTPS (SDK)
         │
┌────────▼────────────────────────────┐
│        Tencent Cloud APIs           │
│                                      │
│  ┌────────────┐  ┌────────────────┐ │
│  │ StreamLive │  │  StreamLink    │ │
│  │ (MDL)      │  │  (MDC)         │ │
│  └────────────┘  └────────────────┘ │
│  ┌────────────┐  ┌────────────────┐ │
│  │StreamPackage│  │  CSS (Live)     │ │
│  │ (MDP)       │  │                 │ │
│  └────────────┘  └────────────────┘ │
└──────────────────────────────────────┘
```

---

## Core Components

### 1. app_v2.py - Main Application

**Responsibility**: Entry point, event routing, Slack integration

| Handler Type | Examples |
|-------------|----------|
| Commands | `/tencent`, `/tencent help` |
| Events | `app_mention`, `message.im` |
| Actions | `start_*`, `stop_*`, `dashboard_*` |

### 2. tencent_cloud_client.py - API Client

**Responsibility**: Tencent Cloud SDK wrapper with caching

| Method | Description |
|--------|-------------|
| `list_all_resources()` | Parallel fetch MDL + StreamLink |
| `list_mdl_channels()` | StreamLive channels with inputs |
| `list_streamlink_inputs()` | StreamLink flows with outputs |
| `list_streampackage_channels()` | StreamPackage channels |
| `list_css_streams()` | CSS active streams |
| `get_channel_input_status()` | Input status (main/backup) with StreamPackage/CSS verification |
| `control_resource()` | Start/Stop/Restart unified |

**Thread Safety**: Creates per-request SDK clients

**Caching**: 120s TTL with prewarm on startup

### 3. slack_ui.py - UI Components

**Responsibility**: Slack Block Kit generation

| Component | Method |
|-----------|--------|
| Dashboard Modal | `create_dashboard_modal()` |
| Loading State | `create_loading_modal()` |
| Result Feedback | `create_action_result_blocks()` |

### 4. scheduler.py - Task Scheduler

**Responsibility**: Scheduled operations

| Feature | Description |
|---------|-------------|
| Schedule | Cron-like scheduling |
| Execute | Callback-based execution |
| Persist | In-memory storage |

---

## Data Flow

```
1. User: /tencent
   ↓
2. app_v2.py: handle_tencent_command()
   ↓
3. slack_ui.py: create_loading_modal() → Immediately respond
   ↓
4. [Async Thread]
   ├─ tencent_cloud_client.list_all_resources()
   │   ├─ list_mdl_channels() ──────────┐
   │   ├─ list_streamlink_inputs() ────┤ (Parallel)
   │   ├─ list_streampackage_channels()─┤
   │   └─ list_css_streams() ───────────┘
   ↓
5. slack_ui.py: create_dashboard_modal()
   ↓
6. Slack API: views.update()
```

---

## Resource Hierarchy

```
StreamLive Channel (Parent)
├── input_endpoints: ["rtmp://...", "srt://..."]
│
├── StreamLink Flow (Child) ← Linked via output_urls
│   └── output_urls: ["rtmp://...", "srt://..."]
│
├── StreamPackage Channel (Output) ← Connected via OutputGroups
│   └── Input URLs: [main, backup]
│
└── CSS Streams (Distribution) ← StreamPackage output
    └── Stream State: active/inactive
```

**Linkage Logic**: 
- `output_urls` of StreamLink matches `input_endpoints` of StreamLive
- StreamLive `OutputGroups` connects to StreamPackage channels
- StreamPackage distributes to CSS streams

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | ✅ | Bot User OAuth Token |
| `SLACK_APP_TOKEN` | ✅ | App-Level Token (Socket Mode) |
| `TENCENT_SECRET_ID` | ✅ | Tencent Cloud API ID |
| `TENCENT_SECRET_KEY` | ✅ | Tencent Cloud API Key |
| `TENCENT_REGION` | ✅ | API Region (e.g., `ap-seoul`) |
| `ALLOWED_USERS` | ❌ | Comma-separated user IDs |
| `DEBUG` | ❌ | Enable debug logging |

---

## Performance Optimizations

| Optimization | Impact |
|--------------|--------|
| Parallel MDL + StreamLink fetch | ~40% faster |
| Reduced API delay (50ms vs 200ms) | ~75% faster detail fetch |
| Thread pool (10 workers) | 2x parallelism |
| Cache prewarm on startup | Instant first load |
