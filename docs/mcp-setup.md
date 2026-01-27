# MCP Server Setup Guide

이 문서는 Tencent Cloud MCP 서버를 AI 애플리케이션(Claude Desktop, Cursor 등)에서 사용하는 방법을 설명합니다.

## 개요

MCP(Model Context Protocol)는 AI 애플리케이션이 외부 데이터와 도구에 접근할 수 있게 해주는 프로토콜입니다. 이 프로젝트는 Tencent Cloud StreamLive/StreamLink 리소스를 MCP를 통해 노출합니다.

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Applications                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Claude       │  │ Cursor       │  │ Other MCP    │      │
│  │ Desktop      │  │ IDE          │  │ Clients      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│                     MCP Protocol (stdio)                     │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                   Tencent Cloud MCP Server                   │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │     Resources       │  │      Tools          │          │
│  │                     │  │                     │          │
│  │ • StreamLive 채널   │  │ • list_channels     │          │
│  │ • StreamLink 플로우 │  │ • start_channel     │          │
│  │ • StreamPackage 채널│  │ • stop_channel      │          │
│  │ • CSS 도메인/스트림 │  │ • get_input_status  │          │
│  │ • 스케줄 목록      │  │ • get_streampackage_status│    │
│  │ • 리소스 계층구조  │  │ • get_css_stream_status│        │
│  └─────────────────────┘  │ • get_full_status   │          │
│                            │ • create_schedule   │          │
│                            │ • start_integrated  │          │
│                            └─────────────────────┘          │
│                                      │                       │
└──────────────────────────────────────┼───────────────────────┘
                                       │
                                Tencent Cloud SDK
                                       │
┌──────────────────────────────────────▼───────────────────────┐
│                    Tencent Cloud APIs                        │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   StreamLive    │  │   StreamLink    │                  │
│  │     (MDL)       │  │     (MDC)       │                  │
│  └─────────────────┘  └─────────────────┘                  │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ StreamPackage   │  │  CSS (Live)      │                  │
│  │     (MDP)       │  │                  │                  │
│  └─────────────────┘  └─────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

## 설치

### 1. 의존성 설치

```bash
cd tencent_mcp
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일에 Tencent Cloud 자격 증명을 설정합니다:

```bash
# Tencent Cloud credentials (MCP 서버용)
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
TENCENT_REGION=ap-seoul
```

## Claude Desktop 설정

### macOS

`~/Library/Application Support/Claude/claude_desktop_config.json` 파일을 편집합니다:

```json
{
  "mcpServers": {
    "tencent-cloud": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/Users/your-username/Workspace/tencent_mcp",
      "env": {
        "TENCENT_SECRET_ID": "your_secret_id",
        "TENCENT_SECRET_KEY": "your_secret_key",
        "TENCENT_REGION": "ap-seoul"
      }
    }
  }
}
```

### Windows

`%APPDATA%\Claude\claude_desktop_config.json` 파일을 편집합니다:

```json
{
  "mcpServers": {
    "tencent-cloud": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\path\\to\\tencent_mcp",
      "env": {
        "TENCENT_SECRET_ID": "your_secret_id",
        "TENCENT_SECRET_KEY": "your_secret_key",
        "TENCENT_REGION": "ap-seoul"
      }
    }
  }
}
```

## Cursor IDE 설정

프로젝트 루트의 `.cursor/mcp.json` 파일을 생성합니다:

```json
{
  "mcpServers": {
    "tencent-cloud": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "TENCENT_SECRET_ID": "${env:TENCENT_SECRET_ID}",
        "TENCENT_SECRET_KEY": "${env:TENCENT_SECRET_KEY}",
        "TENCENT_REGION": "${env:TENCENT_REGION}"
      }
    }
  }
}
```

## 사용 가능한 Resources

| Resource URI | 설명 |
|--------------|------|
| `tencent://streamlive/channels` | StreamLive 채널 목록 |
| `tencent://streamlink/flows` | StreamLink 플로우 목록 |
| `tencent://resources/all` | 모든 리소스 통합 목록 |
| `tencent://resources/hierarchy` | 리소스 계층 구조 (부모-자식 관계) |
| `tencent://schedules/upcoming` | 예정된 방송 스케줄 |
| `tencent://streampackage/channels` | StreamPackage 채널 목록 |
| `tencent://css/domains` | CSS 도메인 목록 |
| `tencent://css/streams` | CSS 활성 스트림 목록 |

## 사용 가능한 Tools

### 리소스 조회

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `list_channels` | 채널/플로우 목록 조회 | - |
| `search_resources` | 키워드로 리소스 검색 | `keyword` |
| `get_channel_status` | 채널 상세 상태 조회 | `channel_id`, `service` |
| `get_input_status` | 입력 상태 (main/backup) 조회 | `channel_id` |
| `get_linked_resources` | 연결된 리소스 조회 | `channel_id`, `service` |

### 리소스 제어

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `start_channel` | 채널 시작 | `channel_id`, `service` |
| `stop_channel` | 채널 중지 | `channel_id`, `service` |
| `restart_channel` | 채널 재시작 | `channel_id`, `service` |
| `start_integrated` | 통합 시작 (부모+자식) | `channel_id` |
| `stop_integrated` | 통합 중지 (부모+자식) | `channel_id` |

### StreamPackage 조회

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `list_streampackage_channels` | StreamPackage 채널 목록 조회 | - |
| `get_streampackage_status` | StreamPackage 채널 상세 상태 (입력 main/backup 포함) | `channel_id` |

### CSS 조회

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `list_css_domains` | CSS 도메인 목록 조회 | - |
| `list_css_streams` | CSS 활성 스트림 목록 조회 | - |
| `get_css_stream_status` | CSS 스트림 상세 상태 조회 | `stream_name` |

### 통합 상태 조회

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `get_full_status` | StreamLive + StreamPackage + CSS 통합 상태 조회 | `channel_id` |

### 스케줄 관리

| Tool | 설명 | 필수 파라미터 |
|------|------|---------------|
| `list_schedules` | 스케줄 목록 조회 | - |
| `create_schedule` | 스케줄 생성 | `channel_id`, `title`, `start_time`, `end_time`, ... |
| `delete_schedule` | 스케줄 삭제 | `schedule_id` |

## 사용 예시

Claude Desktop 또는 Cursor에서 다음과 같이 요청할 수 있습니다:

### 채널 목록 조회
```
모든 StreamLive 채널 목록을 보여줘
```

### 특정 채널 검색
```
KBO 관련 채널을 검색해줘
```

### 채널 상태 확인
```
channel-123의 입력 상태가 main인지 backup인지 확인해줘
```

### 채널 제어
```
channel-123 StreamLive 채널을 시작해줘
```

### 통합 제어
```
channel-123과 연결된 모든 StreamLink 플로우를 함께 시작해줘
```

### 스케줄 생성
```
오늘 저녁 7시부터 10시까지 KBO 경기 방송 스케줄을 만들어줘
```

### StreamPackage 상태 확인
```
StreamPackage 채널 목록을 보여줘
sp-channel-123의 입력 상태가 main인지 backup인지 확인해줘
```

### CSS 스트림 확인
```
CSS 활성 스트림 목록을 보여줘
app/stream-name 스트림이 활성화되어 있는지 확인해줘
```

### 통합 상태 확인
```
channel-123의 전체 상태를 확인해줘 (StreamLive + StreamPackage + CSS)
```

## 테스트

MCP 서버를 직접 테스트하려면:

```bash
# 서버 실행 (stdio 모드)
python -m mcp_server

# 또는 직접 실행
python mcp_server/server.py
```

## 문제 해결

### 서버가 시작되지 않음

1. 환경 변수 확인:
   ```bash
   echo $TENCENT_SECRET_ID
   echo $TENCENT_SECRET_KEY
   echo $TENCENT_REGION
   ```

2. Python 경로 확인:
   ```bash
   which python
   python --version
   ```

### 도구 실행 실패

로그 확인:
```bash
# stderr로 로그 출력됨
python -m mcp_server 2>&1 | tee mcp.log
```

### Claude Desktop에서 연결 안됨

1. Claude Desktop 재시작
2. 설정 파일 문법 확인 (JSON 유효성)
3. 경로가 절대 경로인지 확인
