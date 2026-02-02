# MCP 사용 가이드 - AI와 함께하는 Tencent Cloud 관리

이 가이드는 Claude Code, Claude Desktop 등 AI 애플리케이션에서 MCP 서버를 사용하여 Tencent Cloud StreamLive/StreamLink 리소스를 자연어로 관리하는 방법을 설명합니다.

## 핵심 사용 시나리오

### 1. 시스템 상태 확인

```
현재 시스템 상태 어때?
전체 시스템 건강 상태를 확인해줘
```

AI가 `get_health_summary` 도구를 사용하여 전체 시스템 상태를 요약합니다:
- 실행 중인 채널 수
- 알람 현황 (critical/warning/info)
- 즉시 확인이 필요한 이슈

### 2. 채널 상태 확인

```
KBS 1TV 채널 상태 어때?
running 상태인 채널 목록 보여줘
channel-xxx 상태 확인해줘
```

### 3. 알람 확인

```
현재 알람 있어?
심각한 알람만 보여줘
KBS 채널에 알람 있어?
```

AI가 `get_alerts` 도구를 사용하여 현재 활성 알람을 조회합니다.

### 4. 장애 분석 (핵심 기능)

```
KBS 1TV 채널 알람 원인 분석해줘
channel-xxx에 No Input Data 알람이 왜 발생했는지 확인해봐
```

AI가 `analyze_alert` 도구를 사용하여:
- 알람 컨텍스트 분석
- 연관된 리소스 상태 확인 (StreamLink flow 등)
- 가능한 원인 제시
- 권장 조치 안내

## 설정 방법

### Claude Code (CLI)

프로젝트 디렉토리에서 Claude Code를 실행하면 자동으로 MCP 서버가 연결됩니다.

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/tencent_mcp

# Claude Code 실행
claude
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 또는
`%APPDATA%\Claude\claude_desktop_config.json` (Windows) 파일을 편집합니다:

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

설정 후 Claude Desktop을 재시작하세요.

### Cursor IDE

프로젝트 루트에 `mcp.json` 파일이 이미 설정되어 있습니다. Cursor가 자동으로 MCP 서버를 연결합니다.

## 자주 사용하는 질문 예시

### 상태 확인

| 질문 | 사용되는 도구 |
|------|--------------|
| "전체 시스템 상태 어때?" | `get_health_summary` |
| "현재 알람 있어?" | `get_alerts` |
| "KBS 채널 상태 확인해줘" | `search_resources` + `get_channel_status` |
| "running 상태 채널 목록" | `list_channels` (status filter) |
| "channel-xxx 입력이 main이야 backup이야?" | `get_input_status` |

### 검색

| 질문 | 사용되는 도구 |
|------|--------------|
| "KBO 관련 채널 검색해줘" | `search_resources` |
| "SBS 채널 찾아줘" | `search_resources` |

### 장애 분석

| 질문 | 사용되는 도구 |
|------|--------------|
| "channel-xxx 알람 원인 분석해줘" | `analyze_alert` |
| "No Input Data 알람 왜 발생했어?" | `analyze_alert` |
| "왜 채널이 끊겼는지 확인해봐" | `analyze_alert` + `get_linked_resources` |
| "channel-xxx 로그 확인해줘" | `get_channel_logs` |

### 통합 상태

| 질문 | 사용되는 도구 |
|------|--------------|
| "channel-xxx 전체 파이프라인 상태" | `get_full_status` |
| "StreamPackage 상태 확인" | `get_streampackage_status` |
| "CSS 스트림 상태 확인" | `get_css_stream_status` |

### 제어 (Slack Bot 권장)

| 질문 | 사용되는 도구 |
|------|--------------|
| "channel-xxx 시작해줘" | `start_channel` |
| "channel-xxx 중지해줘" | `stop_channel` |
| "통합 시작 (flow 포함)" | `start_integrated` |

> **참고**: 제어 명령은 MCP에서도 가능하지만, 운영 환경에서는 Slack Bot 대시보드 사용을 권장합니다. Slack Bot은 버튼 UI와 확인 과정을 제공합니다.

## 장애 분석 시나리오

### 시나리오 1: "채널에서 No Input Data 알람 발생"

```
User: channel-xxx에 No Input Data 알람이 왔어. 원인 분석해줘

AI: analyze_alert 도구를 사용하여 분석합니다...

[분석 결과]
- 알람: No Input Data (Pipeline A)
- 발생 시간: 2026-01-28T10:00:00+09:00
- 연결된 StreamLink flow: flow-yyy (status: stopped)

[가능한 원인]
1. StreamLink flow 'flow-yyy'가 중지되어 있음
2. 소스 장비의 송출 중단
3. 네트워크 연결 문제

[권장 조치]
1. StreamLink flow 상태 확인: flow-yyy가 stopped 상태입니다
2. flow를 시작하려면: start_channel 도구 사용
3. 소스 장비 확인 필요
```

### 시나리오 2: "갑자기 채널이 끊겼어"

```
User: KBS 1TV 채널이 갑자기 끊겼어. 뭐가 문제야?

AI: 먼저 채널을 검색하고 상태를 확인합니다...

[search_resources로 채널 찾기]
-> KBS_1TV_channel (id: channel-xxx)

[get_alerts로 알람 확인]
-> PipelineFailover 알람 발생 (Pipeline A -> Pipeline B로 전환됨)

[analyze_alert로 상세 분석]
-> 메인 입력 소스 손실로 자동 failover 발생
-> 현재 백업 입력으로 송출 중

[권장 조치]
1. 메인 입력(StreamLink flow) 상태 확인
2. 소스 장비 점검
3. failover가 발생했지만 백업으로 정상 송출 중
```

### 시나리오 3: "전체 시스템 점검"

```
User: 지금 전체 시스템 상태 점검해줘

AI: get_health_summary 도구를 사용합니다...

[시스템 상태 요약]
- 전체 상태: healthy
- StreamLive: 10개 채널 (8 running, 2 idle)
- StreamLink: 15개 플로우 (12 running, 3 idle)
- 알람: 없음

모든 시스템이 정상 작동 중입니다.
```

## 사용 가능한 MCP 도구

### 알람 및 상태 분석 (신규)

| 도구 | 설명 |
|------|------|
| `get_alerts` | 현재 활성 알람 조회 (severity 필터 지원) |
| `analyze_alert` | 알람 원인 분석 및 권장 조치 제공 |
| `get_health_summary` | 전체 시스템 건강 상태 요약 |

### 리소스 조회

| 도구 | 설명 |
|------|------|
| `list_channels` | 채널/플로우 목록 조회 |
| `search_resources` | 키워드로 리소스 검색 |
| `get_channel_status` | 채널 상세 상태 조회 |
| `get_input_status` | 입력 상태 (main/backup) 조회 |
| `get_linked_resources` | 연결된 리소스 조회 |
| `get_full_status` | 통합 상태 (StreamLive + StreamPackage + CSS) |

### 로그 분석

| 도구 | 설명 |
|------|------|
| `get_channel_logs` | 채널 로그 조회 |
| `get_integrated_logs` | 통합 로그 조회 (모든 서비스) |
| `analyze_logs` | 로그 패턴 분석 |

### 리소스 제어

| 도구 | 설명 |
|------|------|
| `start_channel` | 채널/플로우 시작 |
| `stop_channel` | 채널/플로우 중지 |
| `restart_channel` | 채널/플로우 재시작 |
| `start_integrated` | 통합 시작 (부모+자식) |
| `stop_integrated` | 통합 중지 (부모+자식) |

### 스케줄 관리

| 도구 | 설명 |
|------|------|
| `list_schedules` | 스케줄 목록 조회 |
| `create_schedule` | 스케줄 생성 |
| `delete_schedule` | 스케줄 삭제 |

## MCP Resources

MCP Resources는 데이터 소스를 직접 조회할 수 있습니다:

| Resource URI | 설명 |
|--------------|------|
| `tencent://alerts` | 현재 활성 알람 목록 |
| `tencent://system_status` | 전체 시스템 건강 상태 |
| `tencent://streamlive/channels` | StreamLive 채널 목록 |
| `tencent://streamlink/flows` | StreamLink 플로우 목록 |
| `tencent://resources/hierarchy` | 리소스 계층 구조 |
| `tencent://schedules/upcoming` | 예정된 스케줄 |

## 문제 해결

### MCP 서버가 연결되지 않음

1. 환경 변수 확인:
   ```bash
   echo $TENCENT_SECRET_ID
   echo $TENCENT_REGION
   ```

2. MCP 서버 직접 테스트:
   ```bash
   cd /path/to/tencent_mcp
   python -m mcp_server
   ```

3. Claude Desktop/Cursor 재시작

### 도구 실행 오류

로그 확인:
```bash
python -m mcp_server 2>&1 | tee mcp.log
```

### 알람이 조회되지 않음

- 알람은 **running** 상태의 StreamLive 채널에서만 조회됩니다
- 중지된 채널은 알람이 없습니다

## 참고 문서

- [MCP 설정 상세](./mcp-setup.md)
- [빠른 시작 가이드](./mcp-quick-start.md)
- [API 레퍼런스](./api-reference.md)
