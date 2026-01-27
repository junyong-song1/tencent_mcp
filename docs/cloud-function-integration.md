# Cloud Function 통합 가이드

이 문서는 Tencent Serverless Cloud Function에서 이미 콜백을 받고 있는 상황에서, 이 프로그램으로도 알림을 받는 방법을 설명합니다.

## 현재 상황

```
StreamLive 채널
    ↓ (콜백 URL - 변경 불가)
Tencent Serverless Cloud Function
    ↓ (Slack 알림)
ops_cloud-notification 채널
```

**제약사항:**
- StreamLive 콜백 URL을 변경할 수 없음
- Cloud Function에서 이미 알림 처리 중
- 이 프로그램으로도 알림을 받고 싶음

## 해결 방안: Cloud Function에서 이 프로그램으로도 전달

**권장 방법**: Cloud Function에서 이 프로그램의 webhook endpoint로도 알림을 전달

```
StreamLive 채널
    ↓ (콜백 URL)
Tencent Serverless Cloud Function
    ├─→ ops_cloud-notification 채널 (기존 - 유지)
    └─→ 이 프로그램의 webhook endpoint (추가)
         ↓
    이 프로그램의 상세 알림 시스템
         ↓
    설정된 Slack 채널
```

## 구현 방법

### 1. 이 프로그램의 Webhook Endpoint 확인

이 프로그램은 이미 Cloud Function용 webhook endpoint를 제공합니다:

```
POST https://your-server.com/api/v1/webhooks/cloud-function
```

### 2. Cloud Function 코드 수정

Cloud Function에서 이 프로그램의 webhook endpoint로도 알림을 전달하도록 수정:

#### Python 예시

```python
import requests
import json
from datetime import datetime

def main_handler(event, context):
    """
    StreamLive 콜백 처리
    """
    # 기존 로직: ops_cloud-notification 채널에 알림
    # ... (기존 코드 유지)
    
    # ===== 추가: 이 프로그램의 webhook으로도 전달 =====
    # 포트 3000 사용 시
    mcp_webhook_url = "https://your-server:3000/api/v1/webhooks/cloud-function"
    # 또는 Nginx 리버스 프록시 사용 시 (포트 80)
    # mcp_webhook_url = "https://your-server.com/api/v1/webhooks/cloud-function"
    
    try:
        # 원본 이벤트 데이터를 그대로 전달
        forward_payload = {
            "data": event.get("data", {}),
            "source": "cloud-function",
            "original_notification": {
                "channel": "ops_cloud-notification",
                "sent_at": datetime.now().isoformat(),
            }
        }
        
        response = requests.post(
            mcp_webhook_url,
            json=forward_payload,
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Alert forwarded to MCP system: {response.json()}")
        else:
            print(f"⚠️ Failed to forward alert: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error forwarding alert to MCP: {e}")
        # 실패해도 기존 알림은 정상 전송되므로 계속 진행
    
    # 기존 반환값 유지
    return {"statusCode": 200, "body": "OK"}
```

#### Node.js 예시

```javascript
const axios = require('axios');

exports.main_handler = async (event, context) => {
    // 기존 로직: ops_cloud-notification 채널에 알림
    // ... (기존 코드 유지)
    
    // ===== 추가: 이 프로그램의 webhook으로도 전달 =====
    const mcpWebhookUrl = 'https://your-server.com/api/v1/webhooks/cloud-function';
    
    try {
        const forwardPayload = {
            data: event.data || {},
            source: 'cloud-function',
            original_notification: {
                channel: 'ops_cloud-notification',
                sent_at: new Date().toISOString()
            }
        };
        
        const response = await axios.post(mcpWebhookUrl, forwardPayload, {
            timeout: 5000,
            headers: { 'Content-Type': 'application/json' }
        });
        
        console.log(`✅ Alert forwarded to MCP system:`, response.data);
    } catch (error) {
        console.error(`❌ Error forwarding alert to MCP:`, error.message);
        // 실패해도 기존 알림은 정상 전송되므로 계속 진행
    }
    
    // 기존 반환값 유지
    return { statusCode: 200, body: 'OK' };
};
```

### 3. 간단한 형식으로 전달 (선택)

Cloud Function에서 더 간단한 형식으로 전달할 수도 있습니다:

```python
# 간단한 형식
forward_payload = {
    "channel_id": event.get("data", {}).get("channel_id", ""),
    "event_type": event.get("data", {}).get("event_type", 0),
    "pipeline": event.get("data", {}).get("pipeline", 0),
    "timestamp": datetime.now().isoformat(),
    "alert_type": "StreamStart" if event.get("data", {}).get("event_type") == 329 else "StreamStop",
    "message": "Stream push event from Cloud Function"
}
```

## 지원하는 Payload 형식

이 프로그램의 webhook endpoint는 다음 형식들을 모두 지원합니다:

### 형식 1: 원본 StreamLive 형식 (권장)

```json
{
  "data": {
    "appid": 12345,
    "channel_id": "channel-123",
    "event_type": 329,
    "input_id": "input-456",
    "interface": "general_callback",
    "pipeline": 0,
    "sign": "...",
    "stream_id": "",
    "t": 1234567890
  },
  "source": "cloud-function"
}
```

### 형식 2: 간단한 형식

```json
{
  "channel_id": "channel-123",
  "event_type": 329,
  "alert_type": "StreamStart",
  "pipeline": 0,
  "timestamp": "2024-01-27T19:15:23Z",
  "message": "Optional message"
}
```

## 장점

1. **기존 시스템 유지**: ops_cloud-notification 채널 알림은 그대로 유지
2. **추가 기능 활용**: 이 프로그램의 상세 알림 시스템 활용
3. **중복 없음**: 같은 알림이 두 곳에서 처리되지만, 각각 다른 형식으로 표시
4. **실패 격리**: Cloud Function에서 전달 실패해도 기존 알림은 정상 전송

## 테스트

### 1. Webhook Endpoint 테스트

```bash
curl -X POST https://your-server.com/api/v1/webhooks/cloud-function \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "channel_id": "test-channel",
      "event_type": 329,
      "pipeline": 0
    },
    "source": "cloud-function"
  }'
```

### 2. Cloud Function에서 테스트

Cloud Function 코드에 로깅을 추가하여 전달 여부 확인:

```python
try:
    response = requests.post(mcp_webhook_url, json=forward_payload, timeout=5)
    print(f"MCP webhook response: {response.status_code} - {response.text}")
except Exception as e:
    print(f"MCP webhook error: {e}")
```

## 주의사항

1. **타임아웃 설정**: Cloud Function에서 webhook 호출 시 타임아웃 설정 (5초 권장)
2. **에러 처리**: 전달 실패해도 기존 알림은 정상 전송되도록 처리
3. **재시도**: 필요시 재시도 로직 추가 (선택사항)
4. **보안**: 필요시 API 키나 서명 검증 추가

## 환경 변수 설정

Cloud Function에서 webhook URL을 환경 변수로 관리:

```python
import os

MCP_WEBHOOK_URL = os.environ.get('MCP_WEBHOOK_URL', 'https://your-server.com/api/v1/webhooks/cloud-function')
```

## 완료 후 확인

1. Cloud Function에서 알림 수신 시 두 곳에 전달되는지 확인
2. 이 프로그램의 Slack 채널에 상세 알림이 오는지 확인
3. ops_cloud-notification 채널에도 기존 알림이 정상적으로 오는지 확인
