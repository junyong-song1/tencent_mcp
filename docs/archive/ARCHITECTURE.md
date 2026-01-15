# Tencent MCP - 시스템 아키텍처

## 시스템 개요

```
┌─────────────┐
│   Slack     │
│  Workspace  │
└──────┬──────┘
       │ Socket Mode
       │ (WebSocket)
       │
┌──────▼──────────────────────────────────────┐
│         Slack Bot Application               │
│              (app.py)                       │
│  ┌────────────────────────────────────┐    │
│  │  Event Handlers                     │    │
│  │  - app_mention                      │    │
│  │  - message                          │    │
│  │  - slash_command                    │    │
│  │  - button_actions                   │    │
│  └────────┬────────────────────────────┘    │
│           │                                  │
│  ┌────────▼────────────┐  ┌──────────────┐ │
│  │   NLP Parser        │  │  Slack UI     │ │
│  │  (nlp_parser.py)    │  │ (slack_ui.py) │ │
│  │                     │  │               │ │
│  │  - Intent detection │  │  - Block Kit  │ │
│  │  - Keyword extract  │  │  - Buttons    │ │
│  │  - Channel matching │  │  - Status UI  │ │
│  └────────┬────────────┘  └──────────────┘ │
│           │                                  │
│  ┌────────▼────────────────────────────┐    │
│  │     Tencent API Client              │    │
│  │     (tencent_client.py)             │    │
│  │                                     │    │
│  │  - list_channels()                  │    │
│  │  - get_channel_status()             │    │
│  │  - start_channel()                  │    │
│  │  - stop_channel()                   │    │
│  └────────┬────────────────────────────┘    │
└───────────┼─────────────────────────────────┘
            │ HTTP/REST API
            │
┌───────────▼──────────────┐
│     Tencent API          │
│  (Custom/Internal API)   │
│                          │
│  - Channel Management    │
│  - Status Monitoring     │
│  - Control Operations    │
└──────────────────────────┘
```

## 주요 컴포넌트

### 1. app.py - Main Application

**역할**: Slack Bot의 진입점 및 이벤트 라우팅

**주요 기능**:
- Slack Bolt 앱 초기화
- Socket Mode Handler 설정
- 이벤트 핸들러 등록 (@app.event, @app.command, @app.action)
- 사용자 권한 검증
- 요청 라우팅

**Event Handlers**:
```python
@app.event("app_mention")        # @Tencent MCP 멘션
@app.message("채널")              # DM 또는 채널 메시지
@app.command("/tencent")          # Slash command
@app.action("start_*")            # 실행 버튼
@app.action("stop_*")             # 중지 버튼
@app.action("restart_*")          # 재시작 버튼
```

### 2. nlp_parser.py - Natural Language Parser

**역할**: 자연어 쿼리를 파싱하여 의도와 키워드 추출

**주요 기능**:
- **Intent Detection**: search, status, start, stop, unknown
- **Keyword Extraction**: 불용어 제거 및 키워드 추출
- **Channel Matching**: 키워드 기반 채널 필터링

**지원 패턴**:
```python
# Korean
"KBO 채널 찾아줘"
"라이브 스포츠 검색"
"news 관련 채널 보여줘"
"OOO 채널 상태"

# English
"find sports channel"
"search live channel"
"show news channel"
"status of OOO"

# Mixed
"KBO channel 검색"
```

### 3. tencent_client.py - Tencent API Client

**역할**: Tencent API와의 통신 담당

**주요 메서드**:

```python
list_channels() -> List[Dict]
    # 모든 채널 목록 조회
    # Returns: [{"id": "ch_001", "name": "...", "status": "...", ...}]

get_channel_status(channel_id: str) -> str
    # 특정 채널 상태 조회
    # Returns: "running" | "stopped" | "error" | "unknown"

start_channel(channel_id: str) -> Dict
    # 채널 시작
    # Returns: {"success": bool, "message": str, "status": str}

stop_channel(channel_id: str) -> Dict
    # 채널 중지
    # Returns: {"success": bool, "message": str, "status": str}
```

**Channel Status**:
- `running`: 정상 실행 중
- `stopped`: 중지됨
- `error`: 오류 발생
- `unknown`: 상태 불명

### 4. slack_ui.py - Slack UI Components

**역할**: Slack Block Kit UI 생성

**주요 메서드**:

```python
create_channel_blocks(channels, query)
    # 채널 목록을 Slack Block Kit으로 변환
    # 상태 아이콘, 버튼, 정보 표시

create_action_result_blocks(...)
    # 작업 결과 피드백 UI 생성
    # 성공/실패 메시지, 새로운 상태 표시

create_help_blocks()
    # 도움말 메시지 UI 생성

get_status_emoji(status)
    # 상태별 이모지 반환
    # 🟢 running, 🔴 stopped, 🟡 error, ⚪ unknown
```

### 5. config.py - Configuration Management

**역할**: 환경 변수 관리 및 검증

**설정 항목**:
- Slack 인증 정보 (Bot Token, Signing Secret, App Token)
- Tencent API 정보 (URL, API Key, Secret)
- 서버 설정 (Port, Debug)
- 보안 설정 (Allowed Users)

## 데이터 흐름

### 채널 검색 Flow

```
1. User: "@Tencent MCP KBO 채널 찾아줘"
   ↓
2. app.py: handle_app_mention()
   ↓
3. nlp_parser.parse("KBO 채널 찾아줘")
   → intent: "search", keywords: ["KBO"]
   ↓
4. tencent_client.list_channels()
   → API 호출: GET /channels
   ↓
5. nlp_parser.match_channel("KBO_LIVE_01", ["KBO"])
   → 필터링된 채널 목록
   ↓
6. slack_ui.create_channel_blocks(filtered_channels)
   → Slack Block Kit 생성
   ↓
7. say(blocks=blocks)
   → 사용자에게 응답
```

### 채널 제어 Flow

```
1. User: [실행] 버튼 클릭
   ↓
2. app.py: handle_start_action()
   ↓
3. 권한 검증: is_user_allowed(user_id)
   ↓
4. tencent_client.start_channel(channel_id)
   → API 호출: POST /channels/{id}/start
   ↓
5. result: {"success": True, "status": "running"}
   ↓
6. slack_ui.create_action_result_blocks(...)
   → 결과 UI 생성
   ↓
7. say(blocks=blocks)
   → 사용자에게 피드백
```

## API 인터페이스

### Slack Bot API (입력)

**Event Subscriptions**:
- `app_mention`: Bot 멘션 이벤트
- `message.channels`: 채널 메시지
- `message.im`: DM 메시지

**Slash Commands**:
- `/tencent [query]`: 채널 검색 및 제어

**Interactive Components**:
- `start_{channel_id}`: 채널 시작 버튼
- `stop_{channel_id}`: 채널 중지 버튼
- `restart_{channel_id}`: 채널 재시작 버튼
- `channel_info_{channel_id}`: 상세 정보 버튼

### Tencent API (출력)

**필수 엔드포인트**:

```
GET  /channels
     → 채널 목록 조회

GET  /channels/{id}/status
     → 채널 상태 조회

POST /channels/{id}/start
     → 채널 시작

POST /channels/{id}/stop
     → 채널 중지
```

**예상 응답 형식**:

```json
// GET /channels
[
  {
    "id": "ch_001",
    "name": "KBO_LIVE_01",
    "status": "running",
    "event_group": "sports_live"
  }
]

// POST /channels/{id}/start
{
  "success": true,
  "message": "Channel started successfully",
  "status": "running"
}
```

## 보안 고려사항

### 1. 인증 및 권한

- **Slack 인증**: Bot Token, Signing Secret 검증
- **사용자 권한**: `ALLOWED_USERS` 환경 변수로 제한
- **API 인증**: Authorization Header로 Tencent API 인증

### 2. 입력 검증

- Slack Signing Secret 검증으로 요청 위조 방지
- 사용자 ID 기반 권한 확인
- API 응답 검증 및 에러 핸들링

### 3. 민감 정보 관리

- `.env` 파일로 환경 변수 관리
- `.gitignore`로 민감 정보 버전 관리 제외
- Production에서는 Secret Manager 사용 권장

## 확장성 고려사항

### 1. NLP 고도화

현재: 정규표현식 기반 키워드 매칭

향후:
- OpenAI GPT API 연동
- 문맥 이해 기반 의도 파악
- 다국어 지원 강화

### 2. 캐싱

현재: 매 요청마다 API 호출

향후:
- Redis를 통한 채널 목록 캐싱
- 상태 변경 시 캐시 무효화
- 응답 속도 개선

### 3. 비동기 처리

현재: 동기식 API 호출

향후:
- 대규모 채널 목록 조회 시 비동기 처리
- 백그라운드 작업 큐 (Celery 등)
- 실시간 상태 업데이트

### 4. 모니터링

추가 권장 사항:
- 로그 집계 (ELK Stack, CloudWatch)
- 메트릭 수집 (Prometheus)
- 에러 트래킹 (Sentry)
- 성능 모니터링 (APM)

## 배포 옵션

### Option 1: Local Development

```bash
python app.py
```

- Socket Mode로 로컬 실행
- ngrok 불필요 (WebSocket 사용)
- 개발 및 테스트에 적합

### Option 2: Docker

```bash
docker-compose up -d
```

- 컨테이너화된 배포
- 환경 일관성 보장
- 쉬운 스케일링

### Option 3: Cloud Platform

**AWS**:
- ECS/Fargate로 컨테이너 실행
- Systems Manager Parameter Store로 환경 변수 관리

**GCP**:
- Cloud Run으로 서버리스 배포
- Secret Manager로 인증 정보 관리

**Heroku**:
- Git push 기반 배포
- Config Vars로 환경 변수 설정

## 문제 해결 가이드

### 일반적인 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| Bot 응답 없음 | Event Subscriptions 미설정 | Slack App 설정 확인 |
| 권한 에러 | OAuth Scopes 부족 | Scopes 추가 후 재설치 |
| Socket Mode 연결 실패 | App Token 오류 | xapp- 토큰 확인 |
| API 호출 실패 | Tencent API 인증 실패 | API Key/Secret 확인 |

### 디버깅

```python
# config.py에서 DEBUG 모드 활성화
DEBUG=True

# 상세 로그 출력
logging.basicConfig(level=logging.DEBUG)
```

## 성능 특성

### 예상 처리량

- 채널 검색: ~100ms (API 응답 시간 포함)
- 채널 제어: ~500ms (Tencent API 의존)
- 동시 사용자: 100+ (Socket Mode 기준)

### 리소스 요구사항

- CPU: 0.5 cores (일반 부하)
- Memory: 256MB - 512MB
- Network: 10Mbps (Socket Mode WebSocket)

## 참고 자료

- [Slack API Documentation](https://api.slack.com/)
- [Slack Bolt Python](https://slack.dev/bolt-python/)
- [Slack Block Kit](https://api.slack.com/block-kit)
- [Socket Mode](https://api.slack.com/apis/connections/socket)
