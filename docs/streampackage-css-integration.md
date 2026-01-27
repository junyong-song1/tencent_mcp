# StreamPackage & CSS 통합 가이드

이 문서는 StreamPackage와 CSS(Cloud Streaming Service) 상태 확인 기능을 MCP를 통해 사용하는 방법을 설명합니다.

## 개요

StreamLive 채널은 종종 StreamPackage와 CSS와 함께 사용됩니다:

```
StreamLive Channel
    ↓ (출력)
StreamPackage Channel
    ↓ (배포)
CSS (Cloud Streaming Service)
    ↓ (최종 스트리밍)
End Users
```

MCP를 통해 이 전체 파이프라인의 상태를 확인할 수 있습니다.

## StreamPackage

### StreamPackage란?

StreamPackage는 Tencent Cloud의 미디어 배포 플랫폼으로, StreamLive 채널의 출력을 받아서 배포합니다.

### 사용 가능한 기능

#### 1. 채널 목록 조회

**MCP Resource:**
- `tencent://streampackage/channels` - 모든 StreamPackage 채널 목록

**MCP Tool:**
```python
list_streampackage_channels()
```

**사용 예시:**
```
"StreamPackage 채널 목록을 보여줘"
```

#### 2. 채널 상세 상태 조회

**MCP Tool:**
```python
get_streampackage_status(channel_id="sp-channel-123")
```

**응답 정보:**
- 채널 ID, 이름, 상태
- 입력 정보 (main/backup)
- 활성 입력 타입 (main/backup)
- 입력 URL 목록

**사용 예시:**
```
"sp-channel-123의 입력 상태가 main인지 backup인지 확인해줘"
```

### StreamPackage와 StreamLive 연결

StreamLive 채널의 `get_input_status`를 호출하면 자동으로 연결된 StreamPackage 정보도 포함됩니다:

```json
{
  "streamlive": {
    "channel_id": "channel-123",
    "active_input": "main",
    ...
  },
  "streampackage_verification": {
    "streampackage_id": "sp-channel-123",
    "active_input": "main",
    "input_details": [...]
  }
}
```

## CSS (Cloud Streaming Service)

### CSS란?

CSS는 Tencent Cloud의 라이브 스트리밍 서비스로, StreamPackage를 통해 배포된 스트림을 최종 사용자에게 제공합니다.

### 사용 가능한 기능

#### 1. 도메인 목록 조회

**MCP Resource:**
- `tencent://css/domains` - 모든 CSS 도메인 목록

**MCP Tool:**
```python
list_css_domains()
```

**사용 예시:**
```
"CSS 도메인 목록을 보여줘"
```

#### 2. 활성 스트림 목록 조회

**MCP Resource:**
- `tencent://css/streams` - 모든 활성 CSS 스트림

**MCP Tool:**
```python
list_css_streams(domain="example.com")  # 선택적
```

**사용 예시:**
```
"CSS 활성 스트림 목록을 보여줘"
"example.com 도메인의 스트림 목록을 보여줘"
```

#### 3. 스트림 상태 조회

**MCP Tool:**
```python
get_css_stream_status(stream_name="app/stream-name", domain="example.com")
```

**응답 정보:**
- 스트림 이름, 앱 이름
- 스트림 상태 (active/inactive)
- 푸시 URL 정보
- 도메인 정보

**사용 예시:**
```
"app/stream-name 스트림이 활성화되어 있는지 확인해줘"
```

### CSS와 StreamLive 연결

StreamLive 채널의 `get_input_status`를 호출하면 CSS 검증 정보도 포함됩니다:

```json
{
  "streamlive": {
    "channel_id": "channel-123",
    ...
  },
  "css_verification": {
    "streampackage_connected": true,
    "stream_flowing": true
  }
}
```

## 통합 상태 조회

### get_full_status Tool

StreamLive, StreamPackage, CSS의 전체 상태를 한 번에 조회할 수 있습니다:

**MCP Tool:**
```python
get_full_status(channel_id="channel-123")
```

**응답 구조:**
```json
{
  "success": true,
  "streamlive": {
    "channel_id": "channel-123",
    "active_input": "main",
    "verification_sources": [...],
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
  "linked_streamlink_flows": [
    {
      "id": "flow-456",
      "name": "Linked Flow",
      "status": "running",
      ...
    }
  ]
}
```

**사용 예시:**
```
"channel-123의 전체 상태를 확인해줘 (StreamLive + StreamPackage + CSS)"
"channel-123이 정상적으로 작동하는지 모든 서비스를 포함해서 확인해줘"
```

## 실제 사용 시나리오

### 시나리오 1: 전체 파이프라인 상태 확인

```
사용자: "channel-123의 전체 상태를 확인해줘"

→ Claude가 get_full_status() 호출
→ StreamLive, StreamPackage, CSS 상태 모두 확인
→ 자연어로 종합 리포트 제공:
   "channel-123은 현재 정상 작동 중입니다:
    - StreamLive: MAIN 입력 사용 중
    - StreamPackage: sp-channel-123 연결됨, MAIN 입력 활성
    - CSS: 스트림이 정상적으로 흐르고 있음
    - 연결된 StreamLink 플로우: 2개 (모두 running)"
```

### 시나리오 2: StreamPackage 입력 상태 확인

```
사용자: "sp-channel-123이 backup 입력을 사용하고 있는지 확인해줘"

→ Claude가 get_streampackage_status() 호출
→ 입력 상태 확인
→ 자연어로 응답:
   "sp-channel-123은 현재 MAIN 입력을 사용하고 있습니다."
```

### 시나리오 3: CSS 스트림 활성화 확인

```
사용자: "app/kbo-stream 스트림이 라이브인지 확인해줘"

→ Claude가 get_css_stream_status() 호출
→ 스트림 상태 확인
→ 자연어로 응답:
   "app/kbo-stream 스트림은 현재 활성화되어 있습니다 (ACTIVE 상태)."
```

## 주의사항

### SDK 설치

StreamPackage와 CSS 기능을 사용하려면 해당 SDK가 설치되어 있어야 합니다:

```bash
# StreamPackage SDK (MDP)
pip install tencentcloud-sdk-python-mdp

# CSS SDK (Live) - 일반적으로 메인 SDK에 포함됨
# pip install tencentcloud-sdk-python-live
```

### SDK 가용성 확인

코드에서 자동으로 SDK 가용성을 확인합니다:
- SDK가 없으면 해당 기능은 사용할 수 없음
- 에러 대신 빈 결과 또는 None 반환

### 성능 고려사항

- `get_full_status`는 여러 API를 호출하므로 시간이 걸릴 수 있습니다
- CSS 스트림 목록 조회는 도메인별로 API 호출이 필요합니다
- 캐시를 활용하여 성능을 최적화합니다

## 문제 해결

### StreamPackage 정보가 없음

- StreamLive 채널이 StreamPackage에 연결되어 있는지 확인
- StreamPackage SDK가 설치되어 있는지 확인
- StreamPackage 채널 ID가 올바른지 확인

### CSS 정보가 없음

- CSS SDK가 사용 가능한지 확인
- 도메인 이름이 올바른지 확인
- 스트림 이름 형식이 올바른지 확인 (app/stream)

### 통합 상태 조회 실패

- 각 서비스의 개별 상태를 먼저 확인
- StreamLive 채널이 정상인지 확인
- 연결 관계가 올바른지 확인
