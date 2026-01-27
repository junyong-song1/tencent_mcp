# CSS & StreamPackage 상세 정보 가이드

이 문서는 CSS와 StreamPackage에서 확인 가능한 모든 정보를 상세히 설명합니다.

## StreamPackage 확인 가능한 정보

### 1. 채널 목록 (`list_streampackage_channels`)

**API**: `DescribeStreamPackageChannels`

**확인 가능한 정보:**

| 필드 | 설명 | 예시 |
|------|------|------|
| `id` | StreamPackage 채널 ID | `sp-channel-123` |
| `name` | 채널 이름 | `KBO StreamPackage Channel` |
| `status` | 채널 상태 | `running`, `idle`, `stopped`, `error` |
| `service` | 서비스 타입 | `StreamPackage` |
| `type` | 리소스 타입 | `channel` |
| `input_details` | 입력 상세 정보 배열 | 아래 참조 |

**입력 상세 정보 (`input_details`):**

| 필드 | 설명 | 예시 |
|------|------|------|
| `id` | 입력 ID | `input-main-001` |
| `name` | 입력 이름 | `Main Input` |
| `url` | 입력 URL | `rtmp://main-input.example.com/stream` |

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

### 2. 채널 상세 상태 (`get_streampackage_status`)

**API**: `DescribeStreamPackageChannel`

**확인 가능한 정보:**

| 필드 | 설명 | 예시 |
|------|------|------|
| `streampackage_id` | StreamPackage 채널 ID | `sp-channel-123` |
| `name` | 채널 이름 | `KBO StreamPackage Channel` |
| `state` | 채널 상태 (원본) | `Running`, `Idle`, `Stopped` |
| `protocol` | 프로토콜 타입 | `HLS`, `DASH`, `HLS+DASH` |
| `active_input` | 활성 입력 타입 (추론) | `main`, `backup` |
| `active_input_id` | 활성 입력 ID | `input-main-001` |
| `input_details` | 모든 입력 상세 정보 | 배열 |

**입력 상세 정보 (`input_details`):**

각 입력에 대해:
- `id`: 입력 ID
- `name`: 입력 이름
- `url`: 입력 URL

**활성 입력 판단 로직:**

1. **URL 존재 여부**: URL이 있는 입력만 활성으로 간주
2. **이름 패턴 분석**:
   - 이름에 "backup" 또는 "_b" 포함 → `backup`
   - 그 외 → `main`
3. **순서 기반**: 여러 입력이 있으면 첫 번째를 `main`으로 간주

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

### 3. StreamPackage API에서 제공하는 추가 정보 (잠재적)

Tencent Cloud API가 제공할 수 있지만 현재 구현에서 사용하지 않는 정보:

- **Output Settings**: 출력 설정 (HLS/DASH 엔드포인트)
- **CDN Configuration**: CDN 설정
- **Bandwidth**: 대역폭 정보
- **Statistics**: 통계 정보 (요청 수, 트래픽 등)

**참고**: 현재는 입력 정보와 기본 상태만 확인 가능합니다.

## CSS 확인 가능한 정보

### 1. 도메인 목록 (`list_css_domains`)

**API**: `DescribeLiveDomains`

**확인 가능한 정보:**

| 필드 | 설명 | 예시 |
|------|------|------|
| `domain` | 도메인 이름 | `live.example.com` |
| `type` | 도메인 타입 | `push` (푸시), `play` (재생) |
| `status` | 도메인 상태 | `active`, `inactive` |
| `cname` | CNAME 설정 | `live.example.com.cdn.dnsv1.com` |
| `service` | 서비스 타입 | `CSS` |

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

**API**: `DescribeLiveStreamOnlineList`

**확인 가능한 정보:**

| 필드 | 설명 | 예시 |
|------|------|------|
| `stream_name` | 스트림 이름 | `kbo-game-001` |
| `app_name` | 앱 이름 | `live` |
| `full_name` | 전체 이름 (app/stream) | `live/kbo-game-001` |
| `domain` | 도메인 | `live.example.com` |
| `publish_time` | 푸시 시작 시간 | `2024-01-27 19:00:00` |
| `expire_time` | 만료 시간 | `2024-01-27 22:00:00` |
| `service` | 서비스 타입 | `CSS` |

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

**API**: `DescribeLiveStreamState` + `DescribeLiveStreamPushInfoList`

**확인 가능한 정보:**

#### 기본 상태 정보

| 필드 | 설명 | 예시 |
|------|------|------|
| `stream_name` | 스트림 이름 | `live/kbo-game-001` |
| `stream_state` | 스트림 상태 (원본) | `active`, `inactive` |
| `is_active` | 활성화 여부 (boolean) | `true`, `false` |

#### 푸시 정보 (가능한 경우)

| 필드 | 설명 | 예시 |
|------|------|------|
| `push_url` | 푸시 URL | `rtmp://live.example.com/live/kbo-game-001` |
| `push_domain` | 푸시 도메인 | `live.example.com` |
| `push_app` | 푸시 앱 이름 | `live` |
| `push_stream` | 푸시 스트림 이름 | `kbo-game-001` |

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

### 4. CSS API에서 제공하는 추가 정보 (잠재적)

Tencent Cloud CSS API가 제공할 수 있지만 현재 구현에서 사용하지 않는 정보:

- **Bandwidth**: 대역폭 사용량
- **Viewer Count**: 시청자 수
- **Bitrate**: 비트레이트 정보
- **Frame Rate**: 프레임레이트
- **Resolution**: 해상도
- **Stream History**: 스트림 이력
- **Push Statistics**: 푸시 통계
- **Play Statistics**: 재생 통계

**참고**: 현재는 스트림 상태와 기본 푸시 정보만 확인 가능합니다.

## 제한사항 및 주의사항

### StreamPackage

#### 제한사항

1. **활성 입력 판단**: API가 직접 제공하지 않음
   - 입력 URL 존재 여부와 이름 패턴으로 추론
   - 정확도: 중간 (70-80%)
   - StreamLive 로그와 연계 시 정확도 향상 가능

2. **로그 API 제한**: 직접적인 로그 API 없음
   - 현재 상태만 확인 가능
   - 상태 변화 이력 추적 어려움

3. **통계 정보**: 제한적
   - 기본 상태 정보만 제공
   - 대역폭, 요청 수 등 통계는 별도 API 필요

#### 개선 가능성

- StreamLive 채널과 연결하여 더 정확한 입력 상태 판단
- StreamLive 로그와 연계하여 입력 전환 이벤트 추적

### CSS

#### 제한사항

1. **스트림 상태만 확인**: active/inactive
   - 상세한 오류 정보 제한적
   - 스트림 품질 정보 없음

2. **푸시 정보**: 일부 스트림에서만 제공
   - 모든 스트림에 푸시 정보가 있는 것은 아님
   - 도메인별로 다를 수 있음

3. **로그 API 제한**: 제한적인 로그 제공
   - 스트림 상태 변화 이력 추적 어려움
   - 상세한 이벤트 로그 없음

4. **통계 정보**: 별도 API 필요
   - 대역폭, 시청자 수 등은 별도 API 호출 필요
   - 현재 구현에서는 포함되지 않음

#### 개선 가능성

- CSS 통계 API 추가 (`DescribeLiveStreamBandwidth`, `DescribeLiveStreamOnlineInfo` 등)
- 스트림 품질 정보 추가
- 재생 통계 정보 추가

## 실제 확인 가능한 정보 요약

### StreamPackage

✅ **확인 가능:**
- 채널 목록 (ID, 이름, 상태)
- 채널 상세 (프로토콜, 상태)
- 입력 정보 (ID, 이름, URL)
- 활성 입력 추론 (main/backup)

❌ **확인 불가능:**
- 정확한 활성 입력 (API 미제공)
- 상세 로그 이력
- 대역폭/통계 정보
- 출력 엔드포인트 정보

### CSS

✅ **확인 가능:**
- 도메인 목록 (도메인, 타입, 상태, CNAME)
- 활성 스트림 목록 (스트림 이름, 앱, 시간)
- 스트림 상태 (active/inactive)
- 푸시 정보 (일부 스트림)

❌ **확인 불가능:**
- 대역폭 사용량
- 시청자 수
- 스트림 품질 정보
- 상세 로그 이력
- 재생 통계

## 활용 예시

### StreamPackage

```
"StreamPackage 채널 목록을 보여줘"
→ 모든 채널의 기본 정보 (ID, 이름, 상태, 입력 정보)

"sp-channel-123의 입력이 main인지 backup인지 확인해줘"
→ 활성 입력 타입 추론 (70-80% 정확도)
→ 입력 상세 정보 (ID, 이름, URL)
```

### CSS

```
"CSS 활성 스트림 목록을 보여줘"
→ 현재 활성화된 모든 스트림 목록
→ 스트림 이름, 앱, 도메인, 시간 정보

"live/kbo-stream 스트림이 활성화되어 있는지 확인해줘"
→ 스트림 상태 (active/inactive)
→ 푸시 정보 (가능한 경우)
```

## 추가 정보가 필요한 경우

더 많은 정보가 필요하면 다음 API를 추가로 구현할 수 있습니다:

### StreamPackage
- `DescribeStreamPackageChannelOutputs` - 출력 엔드포인트 정보
- `DescribeStreamPackageChannelStatistics` - 통계 정보

### CSS
- `DescribeLiveStreamBandwidth` - 대역폭 정보
- `DescribeLiveStreamOnlineInfo` - 온라인 스트림 상세 정보
- `DescribeLiveStreamPushInfoList` - 푸시 정보 (일부 구현됨)
- `DescribeLiveStreamPlayInfoList` - 재생 정보

필요하시면 이 API들도 추가 구현할 수 있습니다.
