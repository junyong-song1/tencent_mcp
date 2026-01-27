# Webhook URL 가이드

이 문서는 Cloud Function에서 사용할 webhook URL을 설정하는 방법을 설명합니다.

## Webhook Endpoint

이 프로그램은 다음 webhook endpoint를 제공합니다:

### Cloud Function용 Webhook

```
POST https://your-server:PORT/api/v1/webhooks/cloud-function
```

**포트 설정에 따른 URL 예시:**

| 포트 | URL |
|------|-----|
| 3000 | `https://your-server:3000/api/v1/webhooks/cloud-function` |
| 8000 | `https://your-server:8000/api/v1/webhooks/cloud-function` |
| 80 (Nginx) | `https://your-server/api/v1/webhooks/cloud-function` |

## 포트 3000 사용 시

### 설정

`.env` 파일:
```bash
PORT=3000
```

### Cloud Function Webhook URL

```
https://your-server:3000/api/v1/webhooks/cloud-function
```

### 모든 Endpoint

포트 3000에서 다음 endpoint들이 사용 가능합니다:

- **Health Check**: `GET https://your-server:3000/api/v1/health`
- **Resources**: `GET https://your-server:3000/api/v1/resources`
- **Schedules**: `GET/POST https://your-server:3000/api/v1/schedules`
- **Webhooks**:
  - `POST https://your-server:3000/api/v1/webhooks/streamlive`
  - `POST https://your-server:3000/api/v1/webhooks/streamlink`
  - `POST https://your-server:3000/api/v1/webhooks/cloud-function` ← Cloud Function용
- **API Docs**: `GET https://your-server:3000/docs`

## Cloud Function 코드 예시

```python
import requests

def main_handler(event, context):
    # 기존 로직: ops_cloud-notification 채널에 알림
    # ... (기존 코드)
    
    # 이 프로그램의 webhook으로도 전달
    mcp_webhook_url = "https://your-server:3000/api/v1/webhooks/cloud-function"
    
    try:
        response = requests.post(
            mcp_webhook_url,
            json={
                "data": event.get("data", {}),
                "source": "cloud-function"
            },
            timeout=5
        )
        print(f"✅ Forwarded to MCP: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return {"statusCode": 200, "body": "OK"}
```

## 방화벽 설정

포트 3000을 외부에서 접근할 수 있도록 방화벽을 열어야 합니다:

```bash
# UFW 사용 시
sudo ufw allow 3000/tcp

# 또는 iptables
sudo iptables -A INPUT -p tcp --dport 3000 -j ACCEPT
```

## HTTPS 사용 (선택사항)

HTTPS를 사용하려면:

1. **SSL 인증서 설정** (Let's Encrypt 등)
2. **Nginx 리버스 프록시 사용** (권장)
3. 또는 **애플리케이션에 직접 SSL 설정**

Nginx 사용 시:
- Nginx: 포트 443 (HTTPS)
- 애플리케이션: 포트 3000 (HTTP, 내부)

## 테스트

### Webhook Endpoint 테스트

```bash
curl -X POST https://your-server:3000/api/v1/webhooks/cloud-function \
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

### Health Check

```bash
curl https://your-server:3000/api/v1/health
```

## 주의사항

1. **포트 충돌**: 다른 서비스가 3000 포트를 사용하지 않는지 확인
2. **방화벽**: 포트 3000이 외부에서 접근 가능한지 확인
3. **보안**: 가능하면 HTTPS 사용 권장
4. **Cloud Function 타임아웃**: Cloud Function에서 webhook 호출 시 타임아웃 설정 (5초 권장)
