# CSS & StreamPackage 정보 확인 가이드

이 문서는 CSS(Cloud Streaming Service)와 StreamPackage에서 확인 가능한 정보를 설명합니다.

## StreamPackage 확인 가능한 정보

### 1. 채널 목록 (`list_streampackage_channels`)

**확인 가능한 정보:**
- 채널 ID
- 채널 이름
- 채널 상태 (running, idle, stopped, error)
- 입력 정보 (Input ID, Input Name, Input URL)
- 서비스 타입: "StreamPackage"

**응답 예시:**
```json
{
  "id": "sp-channel-123",
  "name": "KBO StreamPackage Channel",
  "status": "running",
  "service": "StreamPackage",
  "type": "channel",
  "input_details": [
    {
      "id": "input-main-001",
      "name": "Main Input",
      "url": "rtmp://..."
    },
    {
      "id": "input-backup-001",
      "name": "Backup Input",
      "url": "rtmp://..."
    }
  ]
}
```

### 2. 채널 상세 상태 (`get_streampackage_status`)

**확인 가능한 정보:**
- 채널 ID, 이름, 상태
- 프로토콜 (HLS, DASH 등)
- **활성 입력 타입** (main/backup)
- 활성 입력 ID
- 입력 상세 정보 (모든 입력의 ID, 이름, URL)

**응답 예시:**
```json
{
  "streampackage_id": "sp-channel-123",
  "name": "KBO StreamPackage Channel",
  "state": "Running",
  "protocol": "HLS",
  "active_input": "main",
  "active_input_id": "input-main-001",
  "input_details": [
    {
      "id": "input-main-001",
      "name": "Main Input",
      "url": "rtmp://main-input.example.com/stream"
    },
    {
      "id": "input-backup-001",
      "name": "Backup Input",
      "url": "rtmp://backup-input.example.com/stream"
    }
  ]
}
```

**활성 입력 판단 로직:**
- 입력 URL이 있는 입력만 활성으로 간주
- 입력 이름에 "backup" 또는 "_b"가 포함되면 backup으로 판단
- 그 외는 main으로 판단
- 여러 입력이 있으면 첫 번째를 main으로 간주

## CSS 확인 가능한 정보

### 1. 도메인 목록 (`list_css_domains`)

**확인 가능한 정보:**
- 도메인 이름
- 도메인 타입 (push, play 등)
- 도메인 상태
- CNAME 설정
- 서비스 타입: "CSS"

**응답 예시:**
```json
{
  "domain": "live.example.com",
  "type": "push",
  "status": "active",
  "cname": "live.example.com.cdn.dnsv1.com",
  "service": "CSS"
}
```

### 2. 활성 스트림 목록 (`list_css_streams`)

**확인 가능한 정보:**
- 스트림 이름
- 앱 이름
- 전체 이름 (app/stream 형식)
- 도메인
- 푸시 시작 시간
- 만료 시간
- 서비스 타입: "CSS"

**응답 예시:**
```json
{
  "stream_name": "kbo-game-001",
  "app_name": "live",
  "full_name": "live/kbo-game-001",
  "domain": "live.example.com",
  "publish_time": "2024-01-27 19:00:00",
  "expire_time": "2024-01-27 22:00:00",
  "service": "CSS"
}
```

### 3. 스트림 상세 상태 (`get_css_stream_status`)

**확인 가능한 정보:**
- 스트림 이름
- 스트림 상태 (active, inactive)
- 활성화 여부 (is_active: true/false)
- 푸시 URL (가능한 경우)
- 푸시 도메인 (가능한 경우)
- 푸시 앱/스트림 이름 (가능한 경우)

**응답 예시:**
```json
{
  "stream_name": "live/kbo-game-001",
  "stream_state": "active",
  "is_active": true,
  "push_url": "rtmp://live.example.com/live/kbo-game-001",
  "push_domain": "live.example.com",
  "push_app": "live",
  "push_stream": "kbo-game-001"
}
```

## 통합 상태 확인 (`get_full_status`)

StreamLive 채널의 전체 상태를 확인할 때 StreamPackage와 CSS 정보도 함께 포함됩니다:

**확인 가능한 정보:**
- StreamLive 채널 상태
- **StreamPackage 정보** (연결된 경우)
  - StreamPackage ID
  - 활성 입력 (main/backup)
  - 입력 상세 정보
- **CSS 정보** (연결된 경우)
  - StreamPackage 연결 여부
  - 스트림 활성화 여부

**응답 예시:**
```json
{
  "success": true,
  "streamlive": {
    "channel_id": "channel-123",
    "active_input": "main",
    ...
  },
  "streampackage": {
    "streampackage_id": "sp-channel-123",
    "active_input": "main",
    "input_details": [...]
  },
  "css": {
    "streampackage_connected": true,
    "stream_flowing": true
  },
  "linked_streamlink_flows": [...]
}
```

## 사용 방법

### Slack Bot

```
/tencent
→ 대시보드에서 StreamPackage/CSS 정보 확인
```

### MCP Server (AI)

```
"StreamPackage 채널 목록을 보여줘"
"sp-channel-123의 입력 상태가 main인지 backup인지 확인해줘"
"CSS 활성 스트림 목록을 보여줘"
"app/kbo-stream 스트림이 활성화되어 있는지 확인해줘"
"channel-123의 전체 상태를 확인해줘 (StreamLive + StreamPackage + CSS)"
```

### REST API

```bash
# StreamPackage 채널 목록
GET /api/v1/resources?service=StreamPackage

# CSS 스트림 목록
GET /api/v1/resources?service=CSS
```

## 정보 제한사항

### StreamPackage

**제한사항:**
- StreamPackage API는 직접적으로 "어떤 입력이 활성인지"를 알려주지 않음
- 입력 URL 존재 여부와 이름 패턴으로 추론
- 정확도: 중간 (입력 이름 패턴에 의존)

**개선 가능:**
- StreamLive 채널 로그와 연계하여 더 정확한 판단 가능
- StreamLive의 `get_input_status`와 함께 사용 권장

### CSS

**제한사항:**
- 스트림 상태만 확인 가능 (active/inactive)
- 푸시 정보는 일부 스트림에서만 제공
- 도메인별로 API 호출 필요 (도메인이 많으면 시간 소요)

**개선 가능:**
- StreamPackage와 연계하여 더 정확한 상태 확인
- StreamLive 채널과 연결 관계 파악

## 실제 활용 예시

### 예시 1: StreamPackage 입력 상태 확인

```
사용자: "sp-channel-123이 backup 입력을 사용하고 있는지 확인해줘"

→ get_streampackage_status() 호출
→ 입력 상세 정보 확인
→ 입력 이름 패턴 분석
→ 자연어 응답: "sp-channel-123은 현재 MAIN 입력을 사용하고 있습니다"
```

### 예시 2: CSS 스트림 활성화 확인

```
사용자: "live/kbo-game-001 스트림이 라이브인지 확인해줘"

→ get_css_stream_status() 호출
→ 스트림 상태 확인
→ 자연어 응답: "live/kbo-game-001 스트림은 현재 활성화되어 있습니다 (ACTIVE 상태)"
```

### 예시 3: 통합 상태 확인

```
사용자: "channel-123의 전체 상태를 확인해줘"

→ get_full_status() 호출
→ StreamLive + StreamPackage + CSS 모두 확인
→ 자연어 응답:
   "channel-123 상태 점검 결과:
   ✅ StreamLive: MAIN 입력 활성, 상태 정상
   ✅ StreamPackage: sp-channel-123 연결됨, MAIN 입력 사용 중
   ✅ CSS: 스트림 활성화됨
   
   전체 파이프라인 정상 작동 중!"
```

## 요약

### StreamPackage에서 확인 가능한 정보

| 정보 | 설명 | 정확도 |
|------|------|--------|
| 채널 목록 | 모든 StreamPackage 채널 | 높음 |
| 채널 상태 | running, idle, stopped 등 | 높음 |
| 입력 정보 | 입력 ID, 이름, URL | 높음 |
| 활성 입력 | main/backup 판단 | 중간 (패턴 기반) |

### CSS에서 확인 가능한 정보

| 정보 | 설명 | 정확도 |
|------|------|--------|
| 도메인 목록 | 모든 CSS 도메인 | 높음 |
| 활성 스트림 | 현재 활성화된 스트림 목록 | 높음 |
| 스트림 상태 | active/inactive | 높음 |
| 푸시 정보 | 푸시 URL, 도메인 등 | 중간 (일부만 제공) |

## 다음 단계

더 많은 정보가 필요하면:
1. Tencent Cloud API 문서 확인
2. 추가 API 호출 구현
3. 정보 통합 및 분석 로직 개선
