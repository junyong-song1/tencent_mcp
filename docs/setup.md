# Tencent MCP - Setup Guide

## Quick Start (5분 설치)

### 1. 환경 설정

```bash
# 프로젝트 디렉토리로 이동
cd tencent_mcp

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 파일 생성
cp .env.example .env
```

### 2. API 키 발급

#### Tencent Cloud
1. https://console.cloud.tencent.com/cam/capi 접속
2. "새 키 만들기" 클릭
3. SecretId, SecretKey 복사

#### Slack App 생성
1. https://api.slack.com/apps 접속
2. **"Create New App"** → **"From scratch"** 선택
3. App Name: `Tencent MCP`, Workspace 선택

#### Slack 설정

| 설정 항목 | 위치 | 작업 |
|----------|------|------|
| Socket Mode | Socket Mode | Enable, `xapp-...` 토큰 발급 |
| Bot Scopes | OAuth & Permissions | `app_mentions:read`, `chat:write`, `commands`, `channels:history`, `im:history`, `im:write` |
| Events | Event Subscriptions | Enable, `app_mention`, `message.channels`, `message.im` 추가 |
| Slash Command | Slash Commands | `/tencent` 생성 |

### 3. 환경 변수 설정

`.env` 파일 편집:

```env
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# Tencent Cloud
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key
TENCENT_REGION=ap-seoul
```

### 4. 실행

```bash
# 시작
./scripts/start.sh

# 또는 직접 실행
python app_v2.py
```

성공 메시지:
```
INFO:__main__:Starting Tencent MCP Slack Bot...
⚡️ Bolt app is running!
```

### 5. Slack에서 테스트

```
/invite @Tencent MCP
/tencent help
```

---

## Docker 배포

```bash
docker-compose up -d
docker-compose logs -f
```

---

## 문제 해결

| 증상 | 해결 방법 |
|------|----------|
| Bot이 응답 안함 | `/invite @Tencent MCP` 후 Event Subscriptions 확인 |
| Socket Mode 실패 | `SLACK_APP_TOKEN`이 `xapp-`로 시작하는지 확인 |
| Tencent API 오류 | SecretId/SecretKey 재확인, CAM 권한 확인 |
| 권한 에러 | OAuth & Permissions → Reinstall to Workspace |

---

## 프로덕션 체크리스트

- [ ] DEBUG=False 설정
- [ ] 로깅 레벨 INFO로 변경
- [ ] 환경 변수 보안 저장 (AWS SSM, Vault 등)
- [ ] 모니터링 설정 (Health check, 알림)
