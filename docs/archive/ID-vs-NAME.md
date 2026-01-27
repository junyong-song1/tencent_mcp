# 채널 ID vs 채널 Name

## 중요: API는 ID를 사용합니다!

Tencent Cloud StreamLive API를 사용할 때는 **채널 ID**를 사용해야 합니다. 채널 이름(Name)이 아닙니다.

## 차이점

### 채널 ID (Channel ID)
- **용도**: Tencent Cloud가 생성한 실제 채널 식별자
- **형식**: 긴 문자열 또는 숫자 (예: `694A308C79D37854B930`, `1234567890`)
- **특징**: 
  - 고유하고 변경 불가능
  - API 호출 시 필수
  - 채널 목록에서 `id` 필드로 확인 가능

### 채널 Name (Channel Name)
- **용도**: 사용자가 설정한 채널 표시 이름
- **형식**: 자유로운 텍스트 (예: "Production Channel", "Main Stream")
- **특징**:
  - 사용자가 변경 가능
  - 중복 가능
  - API 호출 시 사용 불가 (표시용)

## 예제

### 채널 목록 조회 결과

```bash
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.resources[] | {id, name}'
```

**응답:**
```json
{
  "id": "694A308C79D37854B930",        ← 이것이 ID (API에서 사용)
  "name": "Production Channel"         ← 이것은 이름 (표시용)
}
```

### 올바른 사용법

```bash
# ✅ 올바름: ID 사용
CHANNEL_ID="694A308C79D37854B930"
curl "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive"
```

### 잘못된 사용법

```bash
# ❌ 잘못됨: Name 사용 (동작하지 않음)
CHANNEL_NAME="Production Channel"
curl "http://localhost:8000/api/v1/resources/${CHANNEL_NAME}/input-status?service=StreamLive"
# → 오류: Resource not found
```

## 채널 ID 확인 방법

### 방법 1: API로 목록 조회

```bash
# 모든 StreamLive 채널 목록
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | \
  jq '.resources[] | {id, name, status}'
```

### 방법 2: 슬랙 대시보드에서 확인

1. `/tencent` 명령어로 대시보드 열기
2. StreamLive 채널의 정보 버튼(ℹ️) 클릭
3. 표시되는 "ID: `...`" 부분이 채널 ID

### 방법 3: Tencent Cloud Console에서 확인

1. Tencent Cloud Console 접속
2. StreamLive → 채널 관리
3. 채널 목록에서 채널 ID 확인

## 실제 사용 예제

### 예제 1: 채널 ID로 입력 상태 확인

```bash
# 1단계: 채널 목록에서 ID 확인
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | \
  jq '.resources[] | select(.name=="Production Channel") | .id'

# 출력: "694A308C79D37854B930"

# 2단계: 확인한 ID로 입력 상태 조회
CHANNEL_ID="694A308C79D37854B930"
curl "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" | \
  jq '.'
```

### 예제 2: 이름으로 ID 찾기

```bash
# 이름으로 ID 찾기
CHANNEL_NAME="Production Channel"
CHANNEL_ID=$(curl -s "http://localhost:8000/api/v1/resources?service=StreamLive" | \
  jq -r ".resources[] | select(.name==\"${CHANNEL_NAME}\") | .id")

echo "채널 ID: ${CHANNEL_ID}"

# 찾은 ID로 입력 상태 확인
curl "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" | \
  jq '.'
```

## 주의사항

1. **ID는 대소문자 구분**: `694A308C79D37854B930` ≠ `694a308c79d37854b930`
2. **ID는 변경 불가**: 채널을 삭제하고 다시 만들면 새로운 ID가 생성됨
3. **이름은 중복 가능**: 여러 채널이 같은 이름을 가질 수 있음
4. **API는 항상 ID 사용**: 모든 API 엔드포인트는 ID를 요구함

## FAQ

**Q: 채널 이름만 알고 있는데 어떻게 ID를 찾나요?**  
A: 채널 목록 API로 이름으로 검색하여 ID를 찾을 수 있습니다:
```bash
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | \
  jq '.resources[] | select(.name=="Your Channel Name") | .id'
```

**Q: ID 형식이 항상 같나요?**  
A: 아니요. Tencent Cloud가 생성하는 형식이므로 다양할 수 있습니다. 예: `694A308C79D37854B930`, `1234567890`, `abc-def-123` 등

**Q: 문서의 `channel-123456`은 무엇인가요?**  
A: 단순히 예제로 사용한 것입니다. 실제로는 Tencent Cloud가 생성한 실제 채널 ID를 사용해야 합니다.

## 관련 문서

- [curl 테스트 가이드](./curl-testing-guide.md)
- [curl 빠른 참조](./curl-quick-reference.md)
- [입력 상태 UI 가이드](./input-status-ui.md)
