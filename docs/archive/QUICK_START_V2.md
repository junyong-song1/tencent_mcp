# Quick Start Guide - Tencent MCP v2 (ChatGPT + Tencent Cloud SDK)

## 5분 설치 가이드

### 1. 기본 설정 (2분)

```bash
# 가상환경 설정
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 파일 생성
cp .env.example .env
```

### 2. API 키 발급 (3분)

#### Tencent Cloud (1분)

1. https://console.cloud.tencent.com/cam/capi 접속
2. "새 키 만들기" 클릭
3. SecretId, SecretKey 복사

#### OpenAI (1분)

1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. API 키 복사

#### Slack (1분)

기존 SETUP_GUIDE.md 참조 또는:
- Bot Token: `xoxb-...`
- App Token: `xapp-...`
- Signing Secret: 앱 설정에서 확인

### 3. 환경 변수 설정

`.env` 파일 편집:

```env
# Slack
SLACK_BOT_TOKEN=xoxb-여기에-복사
SLACK_APP_TOKEN=xapp-여기에-복사
SLACK_SIGNING_SECRET=여기에-복사

# Tencent Cloud
TENCENT_SECRET_ID=여기에-복사
TENCENT_SECRET_KEY=여기에-복사
TENCENT_REGION=ap-seoul

# OpenAI
OPENAI_API_KEY=sk-여기에-복사
OPENAI_MODEL=gpt-4-turbo-preview
```

### 4. 실행

```bash
python app_v2.py
```

성공 메시지:
```
INFO:__main__:Starting Tencent MCP Slack Bot with ChatGPT...
⚡️ Bolt app is running!
```

## 첫 번째 명령 실행

### Slack에서 테스트

```
@Tencent MCP help
```

### 자연어 검색

```
@Tencent MCP MediaLive 채널 보여줘
```

### AI 분석

```
@Tencent MCP 채널 상태 분석해줘
```

## 주요 명령어

### 검색

```
KBO 채널 찾아줘
라이브 중인 스포츠 채널
오류 상태인 채널 있어?
MediaLive 채널만 보여줘
```

### 제어

```
[채널명] 시작해줘
[채널명] 중지해줘
[채널명] 재시작해줘
```

### 분석

```
채널 상태 분석해줘
왜 [채널명]이 에러야?
```

### 유틸리티

```
/tencent clear      # 대화 초기화
/tencent stats      # 통계
/tencent help       # 도움말
```

## 문제 해결

### Bot이 응답하지 않음

```bash
# 1. 로그 확인
# 터미널에서 에러 확인

# 2. Bot 초대
/invite @Tencent MCP

# 3. Token 확인
cat .env | grep SLACK
```

### Tencent Cloud 연결 실패

```python
# tencent_cloud_client.py에서 확인
TencentCloudSDKException: [AuthFailure]
```

**해결**:
- SecretId, SecretKey 재확인
- CAM 권한 설정 확인

### OpenAI API 오류

```
openai.error.AuthenticationError
```

**해결**:
- API 키 재확인
- https://platform.openai.com/account/billing 에서 크레딧 확인

## 비용 예상

### OpenAI (ChatGPT)

**GPT-4 Turbo**:
- 사용자 10명, 하루 100개 쿼리
- 평균 1000 tokens/쿼리
- 월 비용: ~$50

**GPT-3.5 Turbo** (권장):
- 동일 사용량
- 월 비용: ~$3

### Tencent Cloud

- API 호출: 무료 또는 매우 저렴
- 채널 실행 비용: 사용량에 따름

## 최적화 팁

### 1. 비용 절감

```env
# .env 파일에서
OPENAI_MODEL=gpt-3.5-turbo  # GPT-4 대신
OPENAI_MAX_TOKENS=1000      # 토큰 제한
```

### 2. 속도 향상

```env
OPENAI_MODEL=gpt-3.5-turbo  # 빠른 응답
```

### 3. 대화 관리

```bash
# 대화 기록이 길어지면
/tencent clear
```

## 다음 단계

### 1. 권한 설정

특정 사용자만 허용:

```env
ALLOWED_USERS=U123456,U789012
```

### 2. 프로덕션 배포

```bash
# Docker 사용
docker-compose up -d
```

### 3. 모니터링

```bash
# 로그 레벨 조정
DEBUG=False
```

## 지원

- **문서**: README_V2.md, MIGRATION_GUIDE.md
- **기존 v1 문서**: README.md, SETUP_GUIDE.md
- **GitHub**: Issues 생성

## 체크리스트

- [ ] Python 3.8+ 설치
- [ ] 가상환경 생성 및 활성화
- [ ] requirements.txt 설치
- [ ] Tencent Cloud API 키 발급
- [ ] OpenAI API 키 발급
- [ ] Slack Bot Token 설정
- [ ] .env 파일 설정
- [ ] app_v2.py 실행
- [ ] Slack에서 테스트
- [ ] 첫 번째 채널 검색 성공!

## 예제 대화

```
사용자: @Tencent MCP 안녕
봇: 안녕하세요! Tencent Cloud 채널 관리를 도와드리겠습니다.
    어떤 작업을 도와드릴까요?

사용자: 채널 목록 보여줘
봇: [MediaLive, CSS, VOD 채널 목록 표시]

사용자: 이 중에 실행 중인 것만
봇: [Running 상태 채널만 필터링]

사용자: 상태 분석해줘
봇: 🤖 AI 분석
    전체 15개 채널 중...
    [상세 분석 결과]

사용자: 고마워!
봇: 천만에요! 추가로 도움이 필요하시면 언제든 말씀해주세요. 😊
```

즐거운 채널 관리 되세요! 🚀
