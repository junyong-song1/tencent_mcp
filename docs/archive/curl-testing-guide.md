# curl로 입력 상태 확인 테스트 가이드

## 개요

StreamLive 채널의 main/backup 입력 상태를 curl로 테스트하는 방법입니다.

## 사전 준비

### 1. 서버 실행 확인

API 서버가 실행 중이어야 합니다:

```bash
# 서버 상태 확인
curl http://localhost:8000/api/v1/health

# 또는
curl http://localhost:8000/
```

### 2. 채널 ID 확인

**중요**: API는 채널 **ID**를 사용합니다. 채널 이름이 아닙니다!

테스트할 StreamLive 채널의 **ID**를 확인합니다:

```bash
# 모든 리소스 목록 조회 (ID와 Name 모두 표시)
curl http://localhost:8000/api/v1/resources | jq '.resources[] | select(.service=="StreamLive") | {id, name, status}'
```

**응답 예제:**
```json
{
  "id": "694A308C79D37854B930",        ← 이것이 ID (사용해야 함)
  "name": "Production Channel",        ← 이것은 이름 (사용 안 함)
  "status": "running"
}
```

**차이점:**
- **ID**: Tencent Cloud가 생성한 실제 채널 식별자 (예: `694A308C79D37854B930`, `1234567890`)
- **Name**: 사용자가 설정한 채널 이름 (예: "Production Channel", "Main Stream")

API 엔드포인트에는 **ID**를 사용해야 합니다!

## 테스트 방법

### 방법 1: 테스트 스크립트 사용 (권장)

```bash
# 스크립트에 실행 권한 부여
chmod +x scripts/test-input-status.sh

# 테스트 실행
./scripts/test-input-status.sh <CHANNEL_ID>

# 예제 (실제 채널 ID 사용)
./scripts/test-input-status.sh 694A308C79D37854B930
```

### 방법 2: 직접 curl 명령어 사용

#### 2.1 채널 상세 정보 조회

```bash
curl -X GET \
  "http://localhost:8000/api/v1/resources/{CHANNEL_ID}?service=StreamLive" \
  -H "Content-Type: application/json" | jq '.'
```

**예제:**
```bash
# 실제 채널 ID 사용 (예: 694A308C79D37854B930)
curl -X GET \
  "http://localhost:8000/api/v1/resources/694A308C79D37854B930?service=StreamLive" \
  -H "Content-Type: application/json" | jq '.'
```

**주의**: `channel-123456`은 예제일 뿐입니다. 실제로는 Tencent Cloud에서 생성한 채널 ID를 사용해야 합니다.

**응답 예제:**
```json
{
  "id": "channel-123456",
  "name": "My StreamLive Channel",
  "status": "running",
  "service": "StreamLive",
  "type": "channel",
  "input_attachments": [
    {
      "id": "input-001",
      "name": "Main Input"
    },
    {
      "id": "input-002",
      "name": "Backup Input"
    }
  ]
}
```

#### 2.2 입력 상태 확인

```bash
curl -X GET \
  "http://localhost:8000/api/v1/resources/{CHANNEL_ID}/input-status?service=StreamLive" \
  -H "Content-Type: application/json" | jq '.'
```

**예제:**
```bash
# 실제 채널 ID 사용 (예: 694A308C79D37854B930)
curl -X GET \
  "http://localhost:8000/api/v1/resources/694A308C79D37854B930/input-status?service=StreamLive" \
  -H "Content-Type: application/json" | jq '.'
```

**주의**: `channel-123456`은 예제일 뿐입니다. 실제로는 Tencent Cloud에서 생성한 채널 ID를 사용해야 합니다.

**응답 예제 (Main 입력 활성):**
```json
{
  "channel_id": "694A308C79D37854B930",
  "channel_name": "My StreamLive Channel",
  "active_input": "main",
  "active_input_id": "input-001",
  "active_input_name": "Main Input",
  "primary_input_id": "input-001",
  "secondary_input_id": "input-002",
  "input_details": [
    {
      "id": "input-001",
      "name": "Main Input",
      "is_primary": true
    },
    {
      "id": "input-002",
      "name": "Backup Input",
      "is_primary": false
    }
  ],
  "input_states": {
    "input-001": {
      "status": 1,
      "is_active": true
    },
    "input-002": {
      "status": 0,
      "is_active": false
    }
  },
  "message": "현재 활성 입력: MAIN (Main Input)"
}
```

**응답 예제 (Backup 입력 활성):**
```json
{
  "channel_id": "694A308C79D37854B930",
  "channel_name": "My StreamLive Channel",
  "active_input": "backup",
  "active_input_id": "input-002",
  "active_input_name": "Backup Input",
  "primary_input_id": "input-001",
  "secondary_input_id": "input-002",
  "input_details": [
    {
      "id": "input-001",
      "name": "Main Input",
      "is_primary": true
    },
    {
      "id": "input-002",
      "name": "Backup Input",
      "is_primary": false
    }
  ],
  "input_states": {
    "input-001": {
      "status": 0,
      "is_active": false
    },
    "input-002": {
      "status": 1,
      "is_active": true
    }
  },
  "message": "현재 활성 입력: BACKUP (Backup Input)"
}
```

**응답 예제 (확인 불가):**
```json
{
  "channel_id": "694A308C79D37854B930",
  "channel_name": "My StreamLive Channel",
  "active_input": null,
  "message": "활성 입력을 확인할 수 없습니다."
}
```

## 전체 테스트 플로우

### 1단계: 서버 상태 확인

```bash
curl http://localhost:8000/api/v1/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2단계: StreamLive 채널 목록 조회

```bash
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.resources[] | {id, name, status}'
```

### 3단계: 특정 채널 상세 정보 조회

```bash
# 실제 채널 ID 사용 (예: 694A308C79D37854B930)
CHANNEL_ID="694A308C79D37854B930"
curl "http://localhost:8000/api/v1/resources/${CHANNEL_ID}?service=StreamLive" | jq '.'
```

### 4단계: 입력 상태 확인

```bash
# 실제 채널 ID 사용 (예: 694A308C79D37854B930)
CHANNEL_ID="694A308C79D37854B930"
curl "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" | jq '.'
```

## 고급 사용법

### jq를 사용한 결과 파싱

```bash
# 활성 입력만 추출
curl -s "http://localhost:8000/api/v1/resources/channel-123456/input-status?service=StreamLive" | \
  jq -r '.active_input // "unknown"'

# 채널 이름과 활성 입력 함께 표시
curl -s "http://localhost:8000/api/v1/resources/channel-123456/input-status?service=StreamLive" | \
  jq -r '"\(.channel_name): \(.active_input // "unknown")"'

# 입력 상태가 backup인 경우만 필터링
curl -s "http://localhost:8000/api/v1/resources?service=StreamLive" | \
  jq '.resources[] | select(.status=="running") | .id' | \
  while read channel_id; do
    status=$(curl -s "http://localhost:8000/api/v1/resources/${channel_id}/input-status?service=StreamLive" | \
      jq -r '.active_input // "unknown"')
    if [ "$status" = "backup" ]; then
      echo "⚠️  ${channel_id}: Backup 입력 사용 중"
    fi
  done
```

### 여러 채널 일괄 확인

```bash
#!/bin/bash
# check-all-channels.sh

API_BASE="http://localhost:8000"

# 실행 중인 모든 StreamLive 채널 조회
CHANNELS=$(curl -s "${API_BASE}/api/v1/resources?service=StreamLive&status=running" | \
  jq -r '.resources[] | select(.status=="running") | .id')

echo "=== StreamLive 채널 입력 상태 확인 ==="
echo ""

for channel_id in $CHANNELS; do
  echo -n "채널 ${channel_id}: "
  
  status=$(curl -s "${API_BASE}/api/v1/resources/${channel_id}/input-status?service=StreamLive" | \
    jq -r '.active_input // "unknown"')
  
  case "$status" in
    "main")
      echo "✅ MAIN"
      ;;
    "backup")
      echo "⚠️  BACKUP"
      ;;
    *)
      echo "❓ ${status}"
      ;;
  esac
done
```

## 오류 처리

### 서버 연결 실패

```bash
# 오류 응답
curl: (7) Failed to connect to localhost port 8000: Connection refused

# 해결 방법
# 1. 서버가 실행 중인지 확인
ps aux | grep uvicorn

# 2. 서버 시작
python -m app.main
# 또는
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 채널을 찾을 수 없음

```json
{
  "error": "Resource not found"
}
```

**해결 방법:**
- 채널 ID가 올바른지 확인
- 채널이 존재하는지 목록에서 확인

### 입력 상태 확인 불가

```json
{
  "channel_id": "channel-123456",
  "active_input": null,
  "message": "활성 입력을 확인할 수 없습니다."
}
```

**가능한 원인:**
- 채널이 실행 중이 아님
- 입력이 연결되지 않음
- Tencent Cloud API 오류
- 네트워크 문제

## 환경 변수 설정

테스트 스크립트에서 사용할 수 있는 환경 변수:

```bash
# API 서버 주소 변경
export API_BASE_URL="http://api.example.com:8000"

# 테스트 실행
./scripts/test-input-status.sh channel-123456
```

## Tencent Cloud API 직접 호출 (참고)

Tencent Cloud API를 직접 호출하려면 복잡한 인증이 필요합니다. 
대신 이 봇의 API를 통해 간편하게 테스트할 수 있습니다.

하지만 Tencent Cloud API를 직접 호출하고 싶다면:

```bash
# 참고: 실제 사용 시 인증 정보가 필요합니다
curl -X POST \
  "https://mdl.tencentcloudapi.com/" \
  -H "Content-Type: application/json" \
  -H "X-TC-Action: QueryInputStreamState" \
  -H "X-TC-Version: 2020-03-26" \
  -H "X-TC-Region: ap-seoul" \
  -H "Authorization: TC3-HMAC-SHA256 ..." \
  -d '{
    "ChannelId": "channel-123456"
  }'
```

## 관련 문서

- [입력 상태 UI 가이드](./input-status-ui.md)
- [API 레퍼런스](./api-reference.md)
- [설정 가이드](./setup.md)
