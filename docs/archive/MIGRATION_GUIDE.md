# Migration Guide: v1 → v2 (ChatGPT + Tencent Cloud SDK)

## 주요 변경사항

### 아키텍처 변경

**v1 (기존)**:
```
Slack → NLP Parser → Custom Tencent API → Channels
```

**v2 (신규)**:
```
Slack → ChatGPT Agent → Tencent Cloud SDK → MediaLive/CSS/VOD
```

### 새로운 기능

1. **ChatGPT 통합**
   - 자연어 이해 및 처리
   - Function calling
   - 대화 컨텍스트 관리
   - AI 분석 및 진단

2. **Tencent Cloud SDK**
   - 공식 SDK 사용
   - MediaLive, CSS, VOD 통합 지원
   - 안정적인 API 호출

3. **대화형 인터페이스**
   - 연속적인 대화 지원
   - 컨텍스트 기반 응답
   - 사용자별 세션 관리

## 마이그레이션 단계

### Step 1: 백업

```bash
# 기존 코드 백업
cp app.py app_v1_backup.py
cp tencent_client.py tencent_client_v1_backup.py
```

### Step 2: 의존성 업데이트

```bash
# requirements.txt 업데이트 확인
pip install -r requirements.txt
```

**추가된 패키지**:
- `tencentcloud-sdk-python` - Tencent Cloud SDK
- `tencentcloud-sdk-python-mdl` - MediaLive
- `tencentcloud-sdk-python-live` - CSS
- `tencentcloud-sdk-python-vod` - VOD
- `openai` - ChatGPT
- `cachetools` - 대화 캐시

### Step 3: 환경 변수 업데이트

`.env` 파일에 추가:

```env
# 기존 (제거 또는 유지)
# TENCENT_API_URL=...
# TENCENT_API_KEY=...
# TENCENT_API_SECRET=...

# 신규 추가
TENCENT_SECRET_ID=your-secret-id
TENCENT_SECRET_KEY=your-secret-key
TENCENT_REGION=ap-seoul

OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=2000
```

### Step 4: Tencent Cloud 인증 설정

1. Tencent Cloud Console 접속
2. CAM (액세스 관리) → API 키 관리
3. 새 API 키 생성
4. SecretId, SecretKey 복사

**필요한 권한**:
- `QcloudMDLFullAccess` - MediaLive 전체 액세스
- `QcloudLIVEFullAccess` - CSS 전체 액세스
- `QcloudVODFullAccess` - VOD 전체 액세스

### Step 5: OpenAI API 키 발급

1. https://platform.openai.com/api-keys 접속
2. API 키 생성
3. 키 복사하여 `.env`에 저장

### Step 6: 애플리케이션 전환

```bash
# v1 실행 중이면 중지
# Ctrl+C

# v2 실행
python app_v2.py
```

## 코드 변경 사항

### Custom API → Tencent Cloud SDK

**v1 (기존)**:
```python
# tencent_client.py
def list_channels(self):
    response = self.session.get(f"{self.base_url}/channels")
    return response.json()
```

**v2 (신규)**:
```python
# tencent_cloud_client.py
def list_mdl_channels(self):
    req = mdl_models.DescribeStreamLiveChannelsRequest()
    resp = self.mdl_client.DescribeStreamLiveChannels(req)
    return [self._normalize_channel(ch) for ch in resp.Infos]
```

### NLP Parser → ChatGPT Agent

**v1 (기존)**:
```python
# nlp_parser.py
parsed = nlp_parser.parse("KBO 채널 찾아줘")
# → {"intent": "search", "keywords": ["KBO"]}
```

**v2 (신규)**:
```python
# chatgpt_agent.py
result = chatgpt_agent.process_message(
    "KBO 채널 찾아줘",
    conversation_history=history
)
# → ChatGPT가 search_channels 함수 호출
```

### 단순 응답 → 대화형 응답

**v1 (기존)**:
```python
@app.event("app_mention")
def handle_app_mention(event, say):
    text = event["text"]
    channels = tencent_client.list_channels()
    say(blocks=create_blocks(channels))
```

**v2 (신규)**:
```python
@app.event("app_mention")
def handle_app_mention(event, say):
    text = event["text"]
    # 대화 컨텍스트 관리
    conversation_manager.add_message(user_id, "user", text)
    # ChatGPT 처리
    process_with_chatgpt(user_id, text, say)
```

## 기능 매핑

### 검색

| v1 | v2 |
|----|-----|
| 키워드 기반 매칭 | ChatGPT 자연어 이해 |
| 단일 서비스 | 다중 서비스 (MediaLive, CSS, VOD) |
| 정확한 키워드 필요 | 의도 파악 |

### 제어

| v1 | v2 |
|----|-----|
| 버튼 클릭만 가능 | 자연어 + 버튼 |
| 단순 start/stop | start/stop/restart + 진단 |
| 결과 메시지 | AI 분석 결과 |

### 상태 관리

| v1 | v2 |
|----|-----|
| 상태 표시만 | 상태 + AI 분석 |
| 오류 메시지 표시 | 오류 진단 + 해결책 제시 |
| - | 대화 컨텍스트 유지 |

## 호환성 문제

### Breaking Changes

1. **API 엔드포인트**
   - Custom API → Tencent Cloud SDK
   - 기존 API 엔드포인트 사용 불가

2. **환경 변수**
   - `TENCENT_API_URL` 제거
   - `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY` 필수

3. **채널 ID 형식**
   - v1: 임의 형식
   - v2: Tencent Cloud 표준 형식

### 하위 호환성

**유지되는 기능**:
- Slack 통합 방식
- 사용자 권한 관리
- 기본 UI/UX

**변경된 기능**:
- NLP 처리 방식
- API 호출 방식
- 응답 형식

## 롤백 방법

v2에 문제가 있을 경우 v1로 롤백:

```bash
# v2 중지
# Ctrl+C

# v1 복원
cp app_v1_backup.py app.py

# v1 실행
python app.py
```

## 테스트 시나리오

### 1. 기본 검색

```
사용자: @Tencent MCP KBO 채널 찾아줘
예상: ChatGPT가 search_channels 호출, 결과 표시
```

### 2. 채널 제어

```
사용자: KBO_LIVE_01 시작해줘
예상: ChatGPT가 control_channel 호출, 성공 메시지
```

### 3. 대화 컨텍스트

```
사용자: 스포츠 채널 보여줘
봇: [채널 리스트]
사용자: 그 중 실행 중인 것만
봇: [필터링된 리스트]
```

### 4. AI 분석

```
사용자: 채널 상태 분석해줘
예상: ChatGPT가 분석 결과 제공
```

## 비용 고려사항

### Tencent Cloud SDK

- API 호출 과금
- 채널 실행 시간당 과금

### OpenAI API

- GPT-4 Turbo: 입력 $10/1M tokens, 출력 $30/1M tokens
- GPT-3.5 Turbo: 입력 $0.50/1M tokens, 출력 $1.50/1M tokens

**절감 팁**:
- `gpt-3.5-turbo` 사용
- `MAX_TOKENS` 제한
- 대화 캐시 TTL 단축

## FAQ

### Q: v1과 v2를 동시에 실행할 수 있나요?
A: 아니요. 동일한 Slack Bot Token을 사용하므로 하나만 실행 가능합니다.

### Q: Custom API를 계속 사용하고 싶어요
A: v1을 계속 사용하거나, v2에서 custom API를 추가로 연동할 수 있습니다.

### Q: OpenAI API 비용이 부담됩니다
A: `gpt-3.5-turbo` 모델로 변경하거나, v1의 NLP Parser를 개선하여 사용하세요.

### Q: 기존 채널 데이터를 마이그레이션해야 하나요?
A: Tencent Cloud SDK는 실시간으로 채널을 조회하므로 별도 마이그레이션 불필요합니다.

### Q: ChatGPT 없이 Tencent Cloud SDK만 사용할 수 있나요?
A: 네, `chatgpt_agent.py` 대신 `nlp_parser.py`를 사용하도록 수정 가능합니다.

## 지원

문제 발생 시:
1. 로그 확인 (`DEBUG=True`)
2. GitHub Issues 생성
3. 커뮤니티 포럼 질문

## 다음 단계

v2 적용 후:
1. 실제 환경 테스트
2. 사용자 피드백 수집
3. AI 프롬프트 최적화
4. 비용 모니터링
