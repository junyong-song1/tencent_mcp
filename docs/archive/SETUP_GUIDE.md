# Tencent MCP Slack Bot - 설치 가이드

## 빠른 시작 (Quick Start)

### 1단계: 프로젝트 클론 및 환경 설정

```bash
# 프로젝트 디렉토리로 이동
cd /Users/songjun-yong/Workspace/tencent_mcp

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 파일 생성
cp .env.example .env
```

### 2단계: Slack App 생성 및 설정

#### A. Slack App 생성

1. 브라우저에서 https://api.slack.com/apps 접속
2. **"Create New App"** 클릭
3. **"From scratch"** 선택
4. App Name: `Tencent MCP` 입력
5. Workspace 선택 후 **"Create App"** 클릭

#### B. Socket Mode 활성화

1. 왼쪽 메뉴에서 **"Socket Mode"** 클릭
2. **"Enable Socket Mode"** 토글을 ON으로 변경
3. Token Name: `WebSocket` 입력
4. **"Generate"** 클릭
5. **App-Level Token** 복사 (형식: `xapp-1-...`)
   - 이 토큰을 `.env` 파일의 `SLACK_APP_TOKEN`에 저장

#### C. OAuth & Permissions 설정

1. 왼쪽 메뉴에서 **"OAuth & Permissions"** 클릭
2. **"Scopes"** 섹션으로 스크롤
3. **"Bot Token Scopes"**에 다음 권한 추가:
   - `app_mentions:read`
   - `chat:write`
   - `commands`
   - `channels:history`
   - `im:history`
   - `im:write`

4. 페이지 상단으로 스크롤하여 **"Install to Workspace"** 클릭
5. 권한 승인
6. **"Bot User OAuth Token"** 복사 (형식: `xoxb-...`)
   - 이 토큰을 `.env` 파일의 `SLACK_BOT_TOKEN`에 저장

#### D. Event Subscriptions 설정

1. 왼쪽 메뉴에서 **"Event Subscriptions"** 클릭
2. **"Enable Events"** 토글을 ON으로 변경
3. **"Subscribe to bot events"** 섹션에 다음 이벤트 추가:
   - `app_mention`
   - `message.channels`
   - `message.im`
4. **"Save Changes"** 클릭

#### E. Slash Commands 설정

1. 왼쪽 메뉴에서 **"Slash Commands"** 클릭
2. **"Create New Command"** 클릭
3. 다음 정보 입력:
   - Command: `/tencent`
   - Short Description: `Tencent 채널 검색 및 제어`
   - Usage Hint: `[검색어] 또는 help`
4. **"Save"** 클릭

#### F. App Credentials 확인

1. 왼쪽 메뉴에서 **"Basic Information"** 클릭
2. **"App Credentials"** 섹션 찾기
3. **"Signing Secret"**의 **"Show"** 클릭 후 복사
   - 이 값을 `.env` 파일의 `SLACK_SIGNING_SECRET`에 저장

### 3단계: 환경 변수 설정

`.env` 파일을 편집기로 열고 다음 값을 설정:

```env
# Slack Configuration (2단계에서 얻은 값들)
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
SLACK_SIGNING_SECRET=your-actual-signing-secret
SLACK_APP_TOKEN=xapp-your-actual-app-token

# Tencent API Configuration
TENCENT_API_URL=https://your-tencent-api-endpoint.com
TENCENT_API_KEY=your-api-key
TENCENT_API_SECRET=your-api-secret

# Server Configuration
PORT=3000
DEBUG=True
```

### 4단계: Bot 실행

```bash
# 가상환경이 활성화된 상태에서
python app.py
```

성공 메시지:
```
INFO:slack_bolt.App:⚡️ Bolt app is running!
```

### 5단계: Slack에서 테스트

#### A. Bot을 채널에 초대

Slack 채널에서:
```
/invite @Tencent MCP
```

#### B. 테스트 명령어

1. **멘션 테스트**
   ```
   @Tencent MCP help
   @Tencent MCP KBO 채널 찾아줘
   ```

2. **Slash Command 테스트**
   ```
   /tencent help
   /tencent 라이브 채널 검색
   ```

3. **DM 테스트**
   - Bot에게 직접 메시지: `채널 검색`

## Tencent API 연동

현재는 Mock 데이터를 사용합니다. 실제 Tencent API를 연동하려면:

### tencent_client.py 수정

```python
def list_channels(self) -> List[Dict]:
    """List all channels from Tencent."""
    try:
        # 실제 API 엔드포인트로 교체
        response = self.session.get(f"{self.base_url}/api/v1/channels")
        response.raise_for_status()

        channels = response.json()
        return [self._normalize_channel(ch) for ch in channels]
    except requests.RequestException as e:
        logger.error(f"Failed to list channels: {e}")
        return []
```

### API 엔드포인트 예시

실제 Tencent API는 다음과 같은 구조여야 합니다:

**GET /api/v1/channels**
```json
[
  {
    "id": "ch_001",
    "name": "KBO_LIVE_01",
    "status": "running",
    "event_group": "sports_live"
  }
]
```

**POST /api/v1/channels/{id}/start**
```json
{
  "success": true,
  "message": "Channel started",
  "status": "running"
}
```

**POST /api/v1/channels/{id}/stop**
```json
{
  "success": true,
  "message": "Channel stopped",
  "status": "stopped"
}
```

## Docker로 실행 (선택사항)

```bash
# Docker 이미지 빌드
docker-compose build

# 컨테이너 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

## 문제 해결

### Bot이 응답하지 않을 때

1. **Event Subscriptions 확인**
   - Slack App 설정에서 Event Subscriptions가 활성화되었는지 확인

2. **Bot 초대 확인**
   ```
   /invite @Tencent MCP
   ```

3. **로그 확인**
   ```bash
   # 터미널에서 앱 실행 중인 로그 확인
   ```

### Socket Mode 연결 실패

1. `SLACK_APP_TOKEN`이 `xapp-`로 시작하는지 확인
2. Socket Mode가 Slack App에서 활성화되었는지 확인

### 권한 에러

Slack App의 OAuth Scopes를 다시 확인하고, 필요한 경우 Workspace에 재설치:
```
OAuth & Permissions → Reinstall to Workspace
```

## 프로덕션 배포

### 환경 변수 관리

- `.env` 파일 대신 시스템 환경 변수 사용
- AWS Systems Manager Parameter Store, HashiCorp Vault 등 사용 권장

### 로깅

```python
# config.py에서 로깅 설정
logging.basicConfig(
    level=logging.INFO,  # DEBUG 대신 INFO
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
```

### 모니터링

- Health check 엔드포인트 추가
- 메트릭 수집 (Prometheus, CloudWatch 등)
- 에러 알림 (Sentry, Rollbar 등)

## 추가 도움말

- Slack API 문서: https://api.slack.com/
- Slack Bolt Python 문서: https://slack.dev/bolt-python/
- 프로젝트 README: [README.md](README.md)
