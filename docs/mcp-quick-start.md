# MCP 빠른 시작 가이드

Tencent Cloud MCP 서버를 AI 애플리케이션(Cursor, Claude Desktop 등)에서 사용하는 방법입니다.

## 🚀 빠른 설정 (3단계)

### 1단계: 환경 변수 설정

`.env` 파일에 Tencent Cloud 자격 증명이 설정되어 있어야 합니다:

```bash
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
TENCENT_REGION=ap-seoul
```

### 2단계: MCP 서버 설정

#### Cursor IDE 사용 시

프로젝트 루트에 이미 `mcp.json` 파일이 있습니다. Cursor가 자동으로 인식합니다.

**설정 확인:**
- Cursor에서 프로젝트를 열면 자동으로 MCP 서버가 연결됩니다
- Cursor 설정에서 MCP 서버 상태를 확인할 수 있습니다

#### Claude Desktop 사용 시

**macOS:**
```bash
# 설정 파일 편집
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
# 설정 파일 편집
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**설정 내용:**
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

**중요:** 
- `cwd`는 프로젝트의 **절대 경로**여야 합니다
- 환경 변수는 `.env` 파일에서 읽거나 직접 설정할 수 있습니다

### 3단계: AI 애플리케이션 재시작

- **Cursor**: 프로젝트를 다시 열거나 Cursor를 재시작
- **Claude Desktop**: 완전히 종료 후 다시 시작

## ✅ 연결 확인

### Cursor에서 확인

1. Cursor 채팅 창에서:
   ```
   Tencent Cloud 채널 목록을 보여줘
   ```

2. MCP 서버가 연결되어 있으면:
   - AI가 `list_channels` 도구를 사용합니다
   - 채널 목록이 표시됩니다

### Claude Desktop에서 확인

1. Claude 채팅에서:
   ```
   StreamLive 채널 목록을 조회해줘
   ```

2. MCP 서버가 연결되어 있으면:
   - Claude가 MCP 도구를 사용합니다
   - 결과가 표시됩니다

## 📝 사용 예시

### 채널 목록 조회
```
모든 StreamLive 채널 목록을 보여줘
```

### 채널 검색
```
KBO 관련 채널을 검색해줘
```

### 채널 상태 확인
```
channel-123의 상태를 확인해줘
channel-123의 입력이 main인지 backup인지 확인해줘
```

### StreamPackage 확인
```
StreamPackage 채널 목록을 보여줘
sp-channel-123의 입력 상태를 확인해줘
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

### 대역폭/품질 확인
```
app/stream-name의 대역폭 사용량을 확인해줘
app/stream-name의 스트림 품질을 확인해줘 (비트레이트, 프레임레이트, 해상도)
app/stream-name의 시청자 수를 확인해줘
```

### 스트림 이벤트 확인
```
app/stream-name의 최근 이벤트 로그를 보여줘
```

## ⚠️ 주의사항

### 제어 명령어는 지원하지 않음

**❌ 작동하지 않음:**
```
channel-123을 시작해줘
채널을 생성해줘
채널을 삭제해줘
```

**✅ 대시보드 버튼 사용:**
- Slack에서 `/tencent` 명령어로 대시보드 열기
- 대시보드의 버튼으로 제어 작업 수행

### MCP는 조회 전용

MCP 서버는 **조회(Read)** 기능만 제공합니다:
- ✅ 채널 목록 조회
- ✅ 상태 확인
- ✅ 검색
- ❌ 채널 시작/중지 (Slack 대시보드에서만 가능)
- ❌ 채널 생성/삭제 (Slack 대시보드에서만 가능)

## 🔧 문제 해결

### MCP 서버가 연결되지 않음

1. **환경 변수 확인:**
   ```bash
   echo $TENCENT_SECRET_ID
   echo $TENCENT_SECRET_KEY
   echo $TENCENT_REGION
   ```

2. **Python 경로 확인:**
   ```bash
   which python
   python --version
   ```

3. **MCP 서버 직접 테스트:**
   ```bash
   cd /path/to/tencent_mcp
   python -m mcp_server
   ```
   - 오류가 없으면 정상입니다
   - 오류가 있으면 로그를 확인하세요

### Cursor에서 MCP가 작동하지 않음

1. Cursor 재시작
2. 프로젝트 다시 열기
3. `.cursor/mcp.json` 파일 확인 (프로젝트 루트에 있어야 함)

### Claude Desktop에서 연결 안됨

1. **설정 파일 경로 확인:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **JSON 문법 확인:**
   - JSON 유효성 검사: https://jsonlint.com/

3. **절대 경로 사용:**
   - `cwd`는 반드시 절대 경로여야 합니다
   - 예: `/Users/username/Workspace/tencent_mcp` (macOS)
   - 예: `C:\Users\username\Workspace\tencent_mcp` (Windows)

4. **Claude Desktop 완전 재시작:**
   - 완전히 종료 후 다시 시작

## 📚 더 자세한 정보

- [MCP 설정 가이드](./mcp-setup.md) - 상세 설정 방법
- [사용 가능한 Resources](./mcp-setup.md#사용-가능한-resources) - 모든 리소스 목록
- [사용 가능한 Tools](./mcp-setup.md#사용-가능한-tools) - 모든 도구 목록

## 💡 팁

1. **환경 변수는 `.env` 파일에서 자동으로 읽힙니다**
   - Cursor: `${env:TENCENT_SECRET_ID}` 형식 사용
   - Claude Desktop: 직접 값 입력 또는 환경 변수 참조

2. **MCP 서버는 별도로 실행할 필요가 없습니다**
   - AI 애플리케이션이 자동으로 시작합니다

3. **여러 프로젝트에서 사용하려면:**
   - 각 프로젝트에 `mcp.json` 파일을 복사
   - 또는 전역 설정 파일에 추가
