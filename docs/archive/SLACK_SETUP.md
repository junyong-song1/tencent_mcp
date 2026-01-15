# Slack Bot 설정 가이드

## 빠른 설정 체크리스트

### 1. Slack App 생성 및 기본 설정

1. **Slack App 생성**
   - https://api.slack.com/apps 접속
   - "Create New App" → "From scratch"
   - App Name: `Tencent MCP` (원하는 이름)
   - Workspace 선택 후 생성

2. **Socket Mode 활성화** (필수)
   - 왼쪽 메뉴: **Socket Mode**
   - "Enable Socket Mode" 토글 ON
   - Token Name: `WebSocket` → Generate
   - **App-Level Token** 복사 (`xapp-1-...` 형식)
   - → `.env` 파일의 `SLACK_APP_TOKEN`에 저장

3. **OAuth & Permissions 설정**
   - 왼쪽 메뉴: **OAuth & Permissions**
   - "Bot Token Scopes"에 다음 권한 추가:
     ```
     app_mentions:read      # 멘션 이벤트 수신
     chat:write              # 메시지 전송
     commands                # Slash command 사용
     channels:history        # 채널 메시지 읽기
     im:history             # DM 메시지 읽기
     im:write               # DM 전송
     ```
   - 페이지 상단: **"Install to Workspace"** 클릭
   - 권한 승인 후 **Bot User OAuth Token** 복사 (`xoxb-...` 형식)
   - → `.env` 파일의 `SLACK_BOT_TOKEN`에 저장

4. **Event Subscriptions 설정**
   - 왼쪽 메뉴: **Event Subscriptions**
   - "Enable Events" 토글 ON
   - "Subscribe to bot events"에 다음 이벤트 추가:
     ```
     app_mention            # 봇 멘션
     message.channels       # 채널 메시지
     message.im            # DM 메시지
     ```
   - "Save Changes" 클릭

5. **Slash Commands 설정**
   - 왼쪽 메뉴: **Slash Commands**
   - "Create New Command" 클릭
   - 설정:
     - Command: `/tencent`
     - Short Description: `Tencent 채널 검색 및 제어`
     - Usage Hint: `[검색어] 또는 help`
   - "Save" 클릭

6. **Signing Secret 확인**
   - 왼쪽 메뉴: **Basic Information**
   - "App Credentials" 섹션
   - "Signing Secret"의 "Show" 클릭 후 복사
   - → `.env` 파일의 `SLACK_SIGNING_SECRET`에 저장

### 2. 환경 변수 설정

`.env` 파일을 열고 다음 값들을 설정:

```env
# Slack Configuration (위에서 복사한 값들)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Tencent Cloud Configuration
TENCENT_SECRET_ID=your-tencent-secret-id
TENCENT_SECRET_KEY=your-tencent-secret-key
TENCENT_REGION=ap-seoul

# OpenAI Configuration (ChatGPT 기능 사용 시)
OPENAI_API_KEY=your-openai-api-key

# Security (선택사항 - 특정 사용자만 허용)
ALLOWED_USERS=U04N8223X36
```

### 3. Bot 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# Bot 실행
python app_v2.py
```

성공 메시지:
```
INFO:slack_bolt.App:⚡️ Bolt app is running!
```

### 4. Slack에서 테스트

#### A. Bot을 채널에 초대
```
/invite @Tencent MCP
```

#### B. 테스트 명령어

1. **멘션으로 검색**
   ```
   @Tencent MCP blackpaper 채널 찾아줘
   @Tencent MCP watchparty 채널 찾아줘
   ```

2. **Slash Command**
   ```
   /tencent blackpaper
   /tencent watchparty
   /tencent help
   ```

3. **Direct Message (DM)**
   - Bot에게 직접 메시지 보내기
   ```
   blackpaper 채널 찾아줘
   ```

#### C. 버튼 클릭 테스트

1. 검색 결과에서 채널 정보 확인
2. 상태 확인 (IDLE, RUNNING, STOPPED 등)
3. **[▶️ 실행]** 또는 **[⏹️ 중지]** 버튼 클릭
4. 결과 메시지 확인

## 중요 사항

### ⚠️ 명령어로 제어 불가
- "시작해줘", "중지해줘" 같은 명령어는 작동하지 않습니다
- 반드시 검색 결과의 **버튼을 클릭**해야 합니다

### ✅ 검색만 가능
- "blackpaper 채널 찾아줘" → 검색 결과 표시
- "watchparty" → 검색 결과 표시

### 🔘 버튼으로만 제어
- 검색 결과의 버튼 클릭 → Tencent Cloud API 호출

## 문제 해결

### Bot이 응답하지 않을 때

1. **Event Subscriptions 확인**
   - Slack App 설정에서 Event Subscriptions가 활성화되었는지 확인
   - 필요한 이벤트가 모두 추가되었는지 확인

2. **Bot 초대 확인**
   ```
   /invite @Tencent MCP
   ```

3. **토큰 확인**
   - `.env` 파일의 토큰이 올바른지 확인
   - `SLACK_BOT_TOKEN`은 `xoxb-`로 시작해야 함
   - `SLACK_APP_TOKEN`은 `xapp-`로 시작해야 함

4. **로그 확인**
   - 터미널에서 실행 중인 Bot의 로그 확인
   - 오류 메시지가 있는지 확인

### Socket Mode 연결 실패

1. `SLACK_APP_TOKEN`이 `xapp-`로 시작하는지 확인
2. Slack App에서 Socket Mode가 활성화되었는지 확인
3. 토큰이 만료되지 않았는지 확인 (재생성 필요 시)

### 권한 에러

1. OAuth & Permissions에서 필요한 권한이 모두 추가되었는지 확인
2. Workspace에 재설치:
   - OAuth & Permissions → "Reinstall to Workspace"

## 터미널에서 테스트

실제 Slack 연결 없이 기능을 테스트하려면:

```bash
python test_slack_bot.py
```

이 스크립트는 다음을 테스트합니다:
- 명령어 파싱
- 검색 기능
- UI 생성
- 제어 명령어 안내
- 연결 관계 찾기
