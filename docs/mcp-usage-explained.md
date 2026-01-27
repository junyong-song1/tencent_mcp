# MCP 사용 방법 완전 정리

## 🤔 MCP가 뭔가요?

MCP (Model Context Protocol)는 AI가 외부 데이터와 도구를 사용할 수 있게 해주는 프로토콜입니다.

**간단히 말하면:**
- AI (Claude, ChatGPT 등)가 Tencent Cloud 정보를 직접 조회할 수 있게 해줍니다
- 텍스트 명령어로 "채널 목록 보여줘"라고 하면 AI가 실제로 Tencent Cloud API를 호출합니다

## 🎯 MCP를 사용하는 3가지 방법

### 방법 1: Cursor IDE (가장 추천 ⭐)

**Cursor는 이미 사용 중이시죠?**  
Cursor는 코드 에디터이면서 동시에 AI 채팅 기능이 있습니다.

#### 설정 방법

1. **프로젝트 열기**
   - Cursor에서 `tencent_mcp` 프로젝트를 엽니다
   - 프로젝트 루트에 `mcp.json` 파일이 이미 있습니다

2. **환경 변수 확인**
   - `.env` 파일에 Tencent Cloud 자격 증명이 있어야 합니다

3. **사용하기**
   - Cursor의 채팅 창(보통 오른쪽 사이드바)에서:
     ```
     모든 StreamLive 채널 목록을 보여줘
     ```
   - AI가 자동으로 MCP 도구를 사용해서 정보를 가져옵니다

**장점:**
- ✅ 별도 프로그램 설치 불필요
- ✅ 이미 사용 중인 Cursor에서 바로 사용
- ✅ 코드 작성하면서 동시에 사용 가능

---

### 방법 2: Claude Desktop (별도 프로그램)

**Claude Desktop은 뭔가요?**

Claude Desktop은 Anthropic에서 만든 **별도의 데스크톱 프로그램**입니다.
- 웹 브라우저에서 claude.ai를 사용하는 것과 비슷하지만, 데스크톱 앱입니다
- MCP를 지원해서 외부 도구를 연결할 수 있습니다

#### 설치 및 설정

1. **Claude Desktop 다운로드**
   - https://claude.ai/download 에서 다운로드
   - macOS 또는 Windows 버전 설치

2. **설정 파일 편집**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   
   설정 내용:
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

3. **Claude Desktop 재시작**

4. **사용하기**
   - Claude Desktop에서 채팅:
     ```
     모든 StreamLive 채널 목록을 보여줘
     ```

**장점:**
- ✅ Claude AI를 전용으로 사용 가능
- ✅ MCP 지원이 잘 됨

**단점:**
- ❌ 별도 프로그램 설치 필요
- ❌ Cursor와는 별개로 사용

---

### 방법 3: Slack Bot (이미 사용 중)

**Slack Bot은 MCP와 별개입니다!**

- Slack Bot: `/tencent` 명령어로 대시보드 사용
- MCP: AI 애플리케이션에서 자연어로 조회

**둘 다 사용 가능합니다:**
- Slack에서 제어 작업 (시작/중지 등)
- MCP에서 조회 작업 (상태 확인 등)

---

## 💡 추천: Cursor 사용하기

**이미 Cursor를 사용 중이시라면:**

1. **프로젝트 열기**
   ```bash
   cd /Users/songjun-yong/Workspace/tencent_mcp
   # Cursor에서 이 폴더 열기
   ```

2. **환경 변수 확인**
   - `.env` 파일에 Tencent Cloud 자격 증명이 있는지 확인

3. **Cursor 채팅에서 사용**
   - Cursor의 AI 채팅 창(보통 `Cmd+L` 또는 사이드바)에서:
     ```
     모든 StreamLive 채널 목록을 보여줘
     KBO 관련 채널을 검색해줘
     channel-123의 상태를 확인해줘
     ```

4. **자동으로 작동**
   - Cursor가 `mcp.json` 파일을 자동으로 인식
   - MCP 서버가 자동으로 연결됨
   - AI가 Tencent Cloud 정보를 조회할 수 있게 됨

---

## 🔍 MCP가 작동하는지 확인하는 방법

### Cursor에서 테스트

1. Cursor 채팅 창 열기
2. 다음 명령어 입력:
   ```
   Tencent Cloud StreamLive 채널 목록을 보여줘
   ```
3. AI가 응답하면:
   - ✅ MCP가 작동 중입니다
   - AI가 실제 채널 목록을 보여줍니다
4. AI가 "MCP 서버를 찾을 수 없습니다"라고 하면:
   - ❌ 설정을 확인해야 합니다

### 직접 테스트

터미널에서:
```bash
cd /Users/songjun-yong/Workspace/tencent_mcp
python -m mcp_server
```

오류가 없으면 정상입니다. `Ctrl+C`로 종료하세요.

---

## ❓ 자주 묻는 질문

### Q: Claude Desktop을 꼭 설치해야 하나요?

**A: 아니요!** Cursor만으로도 충분합니다.
- Cursor에서 MCP를 사용할 수 있습니다
- Claude Desktop은 선택사항입니다

### Q: Slack Bot과 MCP의 차이는?

**A:**
- **Slack Bot**: `/tencent` 명령어 → 대시보드 → 버튼 클릭으로 제어
- **MCP**: 자연어 명령어 → AI가 자동으로 조회

### Q: MCP로 채널을 시작/중지할 수 있나요?

**A: 아니요.** MCP는 조회(Read)만 가능합니다.
- ✅ 조회: 채널 목록, 상태 확인
- ❌ 제어: 시작/중지 (Slack 대시보드에서만 가능)

### Q: Cursor에서 MCP가 안 되면?

**A:**
1. Cursor 재시작
2. 프로젝트 다시 열기
3. `mcp.json` 파일이 프로젝트 루트에 있는지 확인
4. `.env` 파일에 자격 증명이 있는지 확인

---

## 📝 요약

1. **Cursor 사용 (추천)**
   - 이미 사용 중이면 별도 설정 불필요
   - `mcp.json` 파일만 있으면 자동 인식

2. **Claude Desktop 사용 (선택)**
   - 별도 프로그램 설치 필요
   - 설정 파일에 MCP 서버 정보 추가

3. **둘 다 사용 가능**
   - Slack Bot: 제어 작업
   - MCP: 조회 작업

**가장 간단한 방법: Cursor에서 바로 사용하세요!** 🚀
