# Tencent MCP - 빠른 참조 가이드

## 설치 (3분)

```bash
# 1. 가상환경 설정
python3 -m venv venv && source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (Slack Token, Tencent API)

# 4. 실행
python app.py
```

## Slack App 설정 체크리스트

- [ ] Socket Mode 활성화 → App Token 복사
- [ ] OAuth Scopes 추가: `app_mentions:read`, `chat:write`, `commands`, `channels:history`, `im:history`, `im:write`
- [ ] Install to Workspace → Bot Token 복사
- [ ] Event Subscriptions 활성화 → 이벤트 추가: `app_mention`, `message.channels`, `message.im`
- [ ] Slash Command 생성: `/tencent`
- [ ] Signing Secret 복사

## 환경 변수 (필수)

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...
TENCENT_API_URL=https://...
```

## 사용 예시

### 검색

```
@Tencent MCP KBO 채널 찾아줘
@Tencent MCP 라이브 스포츠 검색
/tencent news 관련 채널
```

### 제어

검색 결과에서 버튼 클릭:
- ▶️ **실행** (Stopped → Running)
- ⏹️ **중지** (Running → Stopped)
- 🔄 **재시작** (Error → Running)

## 상태 아이콘

| 아이콘 | 상태 | 설명 |
|-------|------|------|
| 🟢 | Running | 정상 실행 중 |
| 🔴 | Stopped | 중지됨 |
| 🟡 | Error | 오류 발생 |
| ⚪ | Unknown | 상태 불명 |

## 프로젝트 구조

```
tencent_mcp/
├── app.py              # 메인 Slack Bot
├── config.py           # 환경 설정
├── nlp_parser.py       # 자연어 파서
├── tencent_client.py   # Tencent API 클라이언트
├── slack_ui.py         # Slack UI 컴포넌트
├── requirements.txt    # Python 패키지
└── .env               # 환경 변수 (직접 생성)
```

## Tencent API 연동

`tencent_client.py`에서 TODO 부분 구현:

```python
def list_channels(self):
    # TODO: Replace with actual API
    response = self.session.get(f"{self.base_url}/channels")
    # ...
```

필요한 API 엔드포인트:
- `GET /channels` - 채널 목록
- `GET /channels/{id}/status` - 상태 조회
- `POST /channels/{id}/start` - 시작
- `POST /channels/{id}/stop` - 중지

## 문제 해결

### Bot이 응답하지 않음
```bash
# 1. Bot 초대 확인
/invite @Tencent MCP

# 2. 로그 확인
# 터미널에서 에러 메시지 확인

# 3. Event Subscriptions 확인
# Slack App 설정에서 활성화 여부 확인
```

### Socket Mode 연결 실패
- App Token이 `xapp-`로 시작하는지 확인
- Socket Mode가 활성화되었는지 확인

## Docker 실행 (선택)

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

## 권한 제한

특정 사용자만 허용:

```env
ALLOWED_USERS=U123456,U789012
```

빈 값 = 모든 사용자 허용

## 유용한 명령어

```bash
# 테스트 실행
pytest

# 코드 포맷팅
black .

# Lint 검사
flake8 .

# 의존성 업데이트
pip list --outdated
```

## 다음 단계

1. **Tencent API 연동**: `tencent_client.py` 수정
2. **권한 설정**: `.env`에서 `ALLOWED_USERS` 설정
3. **프로덕션 배포**: Docker 또는 클라우드 플랫폼
4. **모니터링 추가**: 로깅, 메트릭, 알람

## 문서

- [README.md](README.md) - 전체 개요
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 상세 설정 가이드
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처

## 도움말

```
/tencent help
@Tencent MCP help
```
