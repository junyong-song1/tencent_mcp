# Tencent MCP - API Reference

## Slash Commands

### `/tencent`

Opens the interactive dashboard modal.

```
/tencent              # Open dashboard
/tencent help         # Show help
/tencent [keyword]    # Open dashboard with search
```

---

## Dashboard Actions

### Search & Filter

| Action | Description |
|--------|-------------|
| Search Input | Filter by name or ID (Enter to submit) |
| Service Filter | All / StreamLive / StreamLink |
| Status Filter | All / Running / Stopped / Error |
| Refresh | Force reload from API |

### Resource Controls

| Button | Action |
|--------|--------|
| ▶️ Start | Start stopped resource |
| ⏹️ Stop | Stop running resource |
| 🔄 Restart | Restart errored resource |

---

## Natural Language Commands

When mentioning the bot (`@Tencent MCP`):

### Search

```
채널 목록 보여줘
KBO 관련 채널 찾아줘
MediaLive 채널만
실행 중인 거 보여줘
```

### Control

```
[채널명] 시작해줘
[채널명] 중지해줘
[채널명] 재시작해줘
```

### Analysis

```
채널 상태 분석해줘
오류 상태인 채널 있어?
```

---

## Python API (Internal)

### TencentCloudClient

```python
from tencent_cloud_client import TencentCloudClient

client = TencentCloudClient()

# List all resources
resources = client.list_all_resources()

# List specific services
mdl_channels = client.list_mdl_channels()
streamlink_flows = client.list_streamlink_inputs()

# Control resource
result = client.control_resource(
    resource_id="abcd1234",
    service="StreamLive",
    action="start"  # or "stop"
)
```

### SlackUI

```python
from slack_ui import SlackUI

# Dashboard modal
modal = SlackUI.create_dashboard_modal(
    channels=resources,
    service_filter="all",
    status_filter="all",
    keyword=""
)

# Loading modal (immediate response)
loading = SlackUI.create_loading_modal(channel_id="C123")

# Action result
blocks = SlackUI.create_action_result_blocks(
    channel_name="my_channel",
    action="start",
    success=True,
    message="Channel started",
    new_status="running"
)
```

---

## Resource Schema

### Channel/Flow Object

```python
{
    "id": "abc123def456",
    "name": "my_channel_name",
    "status": "running",        # running | stopped | idle | error | unknown
    "service": "StreamLive",    # StreamLive | StreamLink
    "inputs_count": 2,
    "input_endpoints": ["rtmp://..."],  # StreamLive only
    "output_urls": ["srt://..."]        # StreamLink only
}
```

### Control Result

```python
{
    "success": True,
    "message": "Channel started successfully",
    "new_status": "running"
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | ✅ | - | Bot OAuth token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | ✅ | - | App token (`xapp-...`) |
| `SLACK_SIGNING_SECRET` | ❌ | - | For request verification |
| `TENCENT_SECRET_ID` | ✅ | - | Tencent Cloud API ID |
| `TENCENT_SECRET_KEY` | ✅ | - | Tencent Cloud API Key |
| `TENCENT_REGION` | ✅ | `ap-seoul` | API Region |
| `ALLOWED_USERS` | ❌ | `*` | Comma-separated user IDs |
| `DEBUG` | ❌ | `False` | Enable debug mode |
