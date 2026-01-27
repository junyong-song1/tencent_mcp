# curl 빠른 참조 가이드

## 기본 명령어

### 1. 서버 상태 확인
```bash
curl http://localhost:8000/api/v1/health
```

### 2. StreamLive 채널 목록
```bash
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.'
```

### 3. 특정 채널 정보
```bash
# {CHANNEL_ID}는 실제 Tencent Cloud 채널 ID를 사용 (예: 694A308C79D37854B930)
curl "http://localhost:8000/api/v1/resources/{CHANNEL_ID}?service=StreamLive" | jq '.'
```

### 4. 입력 상태 확인 ⭐
```bash
# {CHANNEL_ID}는 실제 Tencent Cloud 채널 ID를 사용 (예: 694A308C79D37854B930)
curl "http://localhost:8000/api/v1/resources/{CHANNEL_ID}/input-status?service=StreamLive" | jq '.'
```

**중요**: `{CHANNEL_ID}`는 채널 이름이 아닌 **Tencent Cloud가 생성한 실제 채널 ID**입니다!

## 실제 사용 예제

### 예제 1: 채널 ID로 입력 상태 확인
```bash
# 실제 채널 ID 설정 (예: 694A308C79D37854B930)
# 채널 목록에서 ID 확인: curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.resources[] | {id, name}'
CHANNEL_ID="694A308C79D37854B930"

# 입력 상태 확인
curl -s "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" | \
  jq '{channel: .channel_name, active_input: .active_input, message: .message}'
```

**출력 예제:**
```json
{
  "channel": "My StreamLive Channel",
  "active_input": "main",
  "message": "현재 활성 입력: MAIN (Main Input)"
}
```

### 예제 2: 모든 실행 중인 채널의 입력 상태 확인
```bash
# 실행 중인 채널 목록 가져오기
curl -s "http://localhost:8000/api/v1/resources?service=StreamLive&status=running" | \
  jq -r '.resources[].id' | \
  while read channel_id; do
    echo "=== 채널: ${channel_id} ==="
    curl -s "http://localhost:8000/api/v1/resources/${channel_id}/input-status?service=StreamLive" | \
      jq '{name: .channel_name, active: .active_input, message: .message}'
    echo ""
  done
```

### 예제 3: Backup 입력 사용 중인 채널 찾기
```bash
curl -s "http://localhost:8000/api/v1/resources?service=StreamLive&status=running" | \
  jq -r '.resources[].id' | \
  while read channel_id; do
    status=$(curl -s "http://localhost:8000/api/v1/resources/${channel_id}/input-status?service=StreamLive" | \
      jq -r '.active_input')
    if [ "$status" = "backup" ]; then
      name=$(curl -s "http://localhost:8000/api/v1/resources/${channel_id}/input-status?service=StreamLive" | \
        jq -r '.channel_name')
      echo "⚠️  ${name} (${channel_id}): Backup 입력 사용 중"
    fi
  done
```

### 예제 4: 한 줄로 입력 상태 확인
```bash
# Main 입력이면 ✅, Backup이면 ⚠️ 표시
# 실제 채널 ID 사용 (예: 694A308C79D37854B930)
CHANNEL_ID="694A308C79D37854B930"
curl -s "http://localhost:8000/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" | \
  jq -r 'if .active_input == "main" then "✅ MAIN" elif .active_input == "backup" then "⚠️  BACKUP" else "❓ UNKNOWN" end'
```

## 테스트 스크립트 사용

### 기본 사용법
```bash
./scripts/test-input-status.sh <CHANNEL_ID>
```

### 예제
```bash
# 실제 채널 ID로 테스트 (예: 694A308C79D37854B930)
./scripts/test-input-status.sh 694A308C79D37854B930

# 다른 서버 주소 사용
API_BASE_URL=http://api.example.com:8000 ./scripts/test-input-status.sh 694A308C79D37854B930

# 채널 ID를 모르는 경우, 먼저 목록 확인
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.resources[] | {id, name}'
```

## jq 없이 사용하기

jq가 설치되어 있지 않은 경우:

```bash
# 입력 상태 확인 (JSON 그대로 출력)
curl "http://localhost:8000/api/v1/resources/{CHANNEL_ID}/input-status?service=StreamLive"
```

## 환경 변수 설정

```bash
# API 서버 주소 설정
export API_BASE_URL="http://localhost:8000"

# 테스트 스크립트 사용
./scripts/test-input-status.sh channel-123456
```

## 문제 해결

### 연결 오류
```bash
# 서버가 실행 중인지 확인
curl http://localhost:8000/api/v1/health

# 포트 확인
netstat -an | grep 8000
```

### 채널을 찾을 수 없음
```bash
# 모든 채널 목록 확인 (ID와 Name 모두 표시)
curl "http://localhost:8000/api/v1/resources?service=StreamLive" | jq '.resources[] | {id, name}'

# 출력 예제:
# {
#   "id": "694A308C79D37854B930",    ← 이것이 ID (API에서 사용)
#   "name": "Production Channel"      ← 이것은 이름 (표시용)
# }
```
