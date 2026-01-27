# 동작 원리 가이드

이 문서는 Tencent Cloud MCP 시스템이 어떻게 동작하는지 설명합니다.

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    사용자 인터페이스                            │
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │   Slack Bot     │              │   MCP Server     │        │
│  │                 │              │                  │        │
│  │ 사용자:         │              │ AI 앱:           │        │
│  │ /tencent        │              │ "채널 목록 보여줘"│        │
│  │ 버튼 클릭       │              │ 자연어 요청      │        │
│  └────────┬───────┘              └────────┬─────────┘        │
│           │                                │                   │
│           │ Socket Mode                     │ stdio (JSON-RPC) │
│           │ (WebSocket)                     │                   │
└───────────┼────────────────────────────────┼───────────────────┘
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    공통 서비스 레이어                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         TencentCloudClient                                │ │
│  │  • list_mdl_channels()                                   │ │
│  │  • list_streamlink_inputs()                              │ │
│  │  • list_streampackage_channels()                        │ │
│  │  • list_css_streams()                                   │ │
│  │  • control_resource()                                    │ │
│  │  • get_channel_input_status()                            │ │
│  │  • get_streampackage_channel_details()                   │ │
│  │  • get_css_stream_details()                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         ScheduleManager                                   │ │
│  │  • add_schedule()                                         │ │
│  │  • get_schedules_for_range()                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         LinkageService                                   │ │
│  │  • build_hierarchy()                                      │ │
│  │  • find_linked_flows()                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tencent Cloud APIs                          │
│                                                                 │
│  ┌──────────────┐              ┌──────────────┐               │
│  │ StreamLive   │              │ StreamLink   │               │
│  │   (MDL)      │              │   (MDC)     │               │
│  └──────────────┘              └──────────────┘               │
│  ┌──────────────┐              ┌──────────────┐               │
│  │StreamPackage │              │  CSS (Live)   │               │
│  │   (MDP)      │              │               │               │
│  └──────────────┘              └──────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## 동작 흐름 비교

### 시나리오 1: Slack Bot 사용

```
1. 사용자가 Slack에서:
   /tencent
   
2. Slack → FastAPI (app/main.py)
   └─> Socket Mode Handler가 이벤트 수신
   
3. app/slack/handlers/commands.py
   └─> handle_tencent_command() 실행
   
4. app/slack/ui/dashboard.py
   └─> create_dashboard_modal() 생성
   
5. app/services/tencent_client.py
   └─> list_all_resources() 호출
       ├─> list_mdl_channels() (병렬)
       └─> list_streamlink_inputs() (병렬)
   
6. Tencent Cloud SDK
   └─> API 호출
   
7. 응답 처리
   └─> Slack Modal 업데이트
       └─> 사용자가 대시보드에서 버튼 클릭 가능
```

### 시나리오 2: MCP Server 사용 (AI 앱)

```
1. 사용자가 Claude Desktop에서:
   "모든 StreamLive 채널 목록을 보여줘"
   
2. Claude Desktop → MCP Server (stdio)
   └─> JSON-RPC 요청: {"method": "tools/call", "params": {...}}
   
3. mcp_server/server.py
   └─> call_tool() 실행
   
4. mcp_server/tools.py
   └─> _execute_tool("list_channels", ...)
   
5. app/services/tencent_client.py
   └─> list_all_resources() 호출 (동일한 서비스!)
   
6. Tencent Cloud SDK
   └─> API 호출
   
7. 응답 처리
   └─> JSON-RPC 응답 반환
       └─> Claude Desktop이 자연어로 응답 생성
```

## 핵심 포인트

### 1. **공통 서비스 레이어**

Slack Bot과 MCP Server는 **같은 서비스**를 사용합니다:

```python
# Slack Bot에서
tencent_client = ServiceContainer().tencent_client
channels = tencent_client.list_mdl_channels()

# MCP Server에서
tencent_client = get_tencent_client()  # 같은 클래스!
channels = tencent_client.list_mdl_channels()
```

### 2. **인터페이스만 다름**

| 구분 | Slack Bot | MCP Server |
|------|-----------|------------|
| **입력** | Slack 명령어/버튼 | 자연어 (AI가 해석) |
| **통신** | WebSocket (Socket Mode) | stdio (JSON-RPC) |
| **출력** | Slack Modal/Message | JSON 응답 (AI가 자연어로 변환) |
| **서비스** | ✅ TencentCloudClient | ✅ TencentCloudClient (동일) |

### 3. **실행 방식**

#### Slack Bot (항상 실행)
```bash
# FastAPI 서버로 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 백그라운드에서 계속 실행
# - Slack 이벤트 대기
# - 스케줄러 실행
# - 알림 모니터링
```

#### MCP Server (요청 시 실행)
```bash
# Claude Desktop이 필요할 때만 실행
python -m mcp_server

# stdio로 통신 (표준 입력/출력)
# - 요청이 오면 처리
# - 응답 반환 후 종료 가능
```

## 실제 사용 예시

### 예시 1: 채널 목록 조회

**Slack Bot:**
```
사용자: /tencent
→ Slack Modal 열림
→ "StreamLive Channels" 탭 클릭
→ 채널 목록 표시
```

**MCP Server (Claude Desktop):**
```
사용자: "모든 채널 목록을 보여줘"
→ Claude가 MCP tool 호출: list_channels()
→ JSON 응답 받음
→ Claude가 자연어로 변환: "현재 5개의 StreamLive 채널이 있습니다..."
```

### 예시 2: 채널 시작

**Slack Bot:**
```
사용자: /tencent → 대시보드 → "channel-123" → "Start" 버튼 클릭
→ app/slack/handlers/control.py의 handle_start() 실행
→ tencent_client.control_resource("channel-123", "StreamLive", "start")
→ Slack 메시지: "✅ channel-123이 시작되었습니다"
```

**MCP Server (Claude Desktop):**
```
사용자: "channel-123을 시작해줘"
→ Claude가 MCP tool 호출: start_channel(channel_id="channel-123", service="StreamLive")
→ mcp_server/tools.py의 _execute_tool() 실행
→ tencent_client.control_resource("channel-123", "StreamLive", "start") (동일!)
→ JSON 응답: {"success": true, "message": "..."}
→ Claude가 자연어로 변환: "channel-123이 성공적으로 시작되었습니다"
```

### 예시 3: 입력 상태 확인 (main/backup)

**Slack Bot:**
```
사용자: /tencent → Status 탭 → "channel-123" 선택
→ app/slack/handlers/status_tab.py 실행
→ tencent_client.get_channel_input_status("channel-123")
→ Slack에 상태 표시: "현재 활성 입력: MAIN"
```

**MCP Server (Claude Desktop):**
```
사용자: "channel-123의 입력이 main인지 backup인지 확인해줘"
→ Claude가 MCP tool 호출: get_input_status(channel_id="channel-123")
→ mcp_server/tools.py 실행
→ tencent_client.get_channel_input_status("channel-123") (동일!)
→ JSON 응답: {"active_input": "main", "verification_sources": [...]}
→ Claude가 자연어로 변환: "channel-123은 현재 MAIN 입력을 사용하고 있습니다"
```

## 데이터 흐름

### 1. 리소스 조회

```
┌─────────────┐
│  사용자     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Slack Bot 또는 MCP Server          │
│  (인터페이스만 다름)                 │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  TencentCloudClient                 │
│  • 캐시 확인 (120초 TTL)            │
│  • 캐시 없으면 API 호출              │
│  • ThreadPoolExecutor로 병렬 처리   │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Tencent Cloud SDK                  │
│  • MDL Client (StreamLive)          │
│  • MDC Client (StreamLink)          │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Tencent Cloud APIs                │
│  • DescribeStreamLiveChannels       │
│  • DescribeStreamLinkFlows         │
└─────────────────────────────────────┘
```

### 2. 리소스 제어

```
┌─────────────┐
│  사용자     │
│  "시작해줘" │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Slack Bot 또는 MCP Server          │
│  • action="start" 파싱              │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  TencentCloudClient                │
│  control_resource(id, service, action)│
│  • 캐시 클리어 (최신 상태 필요)     │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Tencent Cloud SDK                  │
│  • StartStreamLiveChannel           │
│  • StopStreamLiveChannel            │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Tencent Cloud APIs                │
│  • 리소스 상태 변경                 │
└─────────────────────────────────────┘
```

## 동시 실행 가능

**중요:** Slack Bot과 MCP Server는 **동시에 실행 가능**합니다!

```
┌─────────────────────────────────────────┐
│  프로세스 1: Slack Bot                  │
│  uvicorn app.main:app --port 8000      │
│  └─> FastAPI + Slack Socket Mode       │
│      └─> 사용자들이 Slack에서 사용     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  프로세스 2: MCP Server                 │
│  python -m mcp_server                  │
│  └─> Claude Desktop이 필요할 때 실행   │
│      └─> AI 앱에서 사용                │
└─────────────────────────────────────────┘

        ┌──────────────┐
        │  공통 서비스  │
        │  (같은 코드)  │
        └──────────────┘
```

## 요약

1. **Slack Bot**: 사용자가 직접 명령어/버튼으로 제어
2. **MCP Server**: AI가 자연어를 해석해서 제어
3. **공통 서비스**: 둘 다 같은 `TencentCloudClient` 사용
4. **동시 실행**: 두 인터페이스를 동시에 사용 가능
5. **데이터 일관성**: 같은 캐시와 서비스를 공유하므로 데이터 일관성 유지
