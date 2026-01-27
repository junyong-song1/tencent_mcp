# Tencent Cloud CSS Timeshift 파라미터 설정 가이드

## 개요

Tencent Cloud CSS(Cloud Streaming Service)의 Timeshift(타임시프트) 기능은 라이브 스트리밍을 녹화하고 시청자가 과거 방송을 다시 볼 수 있게 해주는 기능입니다.

이 문서는 Tencent Cloud SDK를 사용하여 Timeshift 템플릿과 규칙을 설정하는 방법을 설명합니다.

---

## 1. Timeshift 템플릿 생성

Timeshift 템플릿은 타임시프트 기능의 기본 설정을 정의합니다.

### API: `CreateLiveTimeShiftTemplate`

### 필수 파라미터

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `TemplateName` | string | 템플릿 이름 (고유해야 함) | `"timeshift_1hour"` |
| `Duration` | int | 타임시프트 저장 기간 (초 단위) | `3600` (1시간) |

### 선택 파라미터

| 파라미터 | 타입 | 설명 | 기본값 | 예시 |
|---------|------|------|--------|------|
| `ItemDuration` | int | 각 세그먼트 길이 (초 단위) | `60` | `60`, `120` |
| `Area` | string | 지역 설정 | `"Mainland"` | `"Mainland"` (중국 본토)<br>`"Overseas"` (해외) |
| `Description` | string | 템플릿 설명 | `null` | `"1시간 타임시프트 템플릿"` |
| `RemoveWatermark` | bool | 워터마크 제거 여부 | `false` | `true`, `false` |
| `TranscodeTemplateIds` | list[int] | 트랜스코딩 템플릿 ID 리스트 | `[]` | `[123, 456]` |

### 파라미터 상세 설명

#### `Duration` (저장 기간)
- **단위**: 초 (seconds)
- **범위**: 최소값과 최대값은 Tencent Cloud 정책에 따름
- **권장값**: 
  - 1시간: `3600`
  - 2시간: `7200`
  - 4시간: `14400`
  - 24시간: `86400`

#### `ItemDuration` (세그먼트 길이)
- **단위**: 초 (seconds)
- **설명**: 타임시프트 스트림을 저장할 때 각 파일의 길이
- **권장값**: `60` (1분), `120` (2분), `300` (5분)
- **주의**: 너무 짧으면 파일이 많아지고, 너무 길면 시청 시 로딩이 느려질 수 있음

#### `Area` (지역)
- **Mainland**: 중국 본토 지역
- **Overseas**: 해외 지역 (한국 포함)
- **선택 기준**: 스트리밍 대상 지역에 따라 선택

#### `RemoveWatermark` (워터마크 제거)
- **true**: 워터마크 제거 (추가 비용 발생 가능)
- **false**: 워터마크 유지

#### `TranscodeTemplateIds` (트랜스코딩 템플릿)
- 여러 해상도/비트레이트로 타임시프트 저장 시 사용
- 트랜스코딩 템플릿을 먼저 생성한 후 ID를 입력

### API 호출 URL 예시

Tencent Cloud API는 RESTful API로, POST 요청을 사용합니다.

#### HTTP 요청 예시

```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
Content-Type: application/json
X-TC-Action: CreateLiveTimeShiftTemplate
X-TC-Version: 2018-08-01
X-TC-Region: ap-seoul
Authorization: TC3-HMAC-SHA256 Credential=YOUR_SECRET_ID/20240101/live/tc3_request, ...
Host: live.tencentcloudapi.com

{
  "TemplateName": "timeshift_1hour",
  "Duration": 3600,
  "ItemDuration": 60,
  "Area": "Overseas",
  "Description": "1시간 타임시프트 템플릿",
  "RemoveWatermark": false
}
```

#### cURL 예시

```bash
curl -X POST https://live.tencentcloudapi.com/ \
  -H "Content-Type: application/json" \
  -H "X-TC-Action: CreateLiveTimeShiftTemplate" \
  -H "X-TC-Version: 2018-08-01" \
  -H "X-TC-Region: ap-seoul" \
  -H "Authorization: TC3-HMAC-SHA256 ..." \
  -d '{
    "TemplateName": "timeshift_1hour",
    "Duration": 3600,
    "ItemDuration": 60,
    "Area": "Overseas",
    "Description": "1시간 타임시프트 템플릿",
    "RemoveWatermark": false
  }'
```

#### Python SDK 코드 예시

```python
from tencentcloud.common import credential
from tencentcloud.live.v20180801 import live_client, models as live_models

# 클라이언트 생성
cred = credential.Credential("YOUR_SECRET_ID", "YOUR_SECRET_KEY")
client = live_client.LiveClient(cred, "ap-seoul")

# 템플릿 생성 요청
request = live_models.CreateLiveTimeShiftTemplateRequest()
request.TemplateName = "timeshift_1hour"
request.Duration = 3600  # 1시간 저장
request.ItemDuration = 60  # 60초 세그먼트
request.Area = "Overseas"  # 해외 지역 (한국 포함)
request.Description = "1시간 타임시프트 템플릿"
request.RemoveWatermark = False
# request.TranscodeTemplateIds = [123, 456]  # 선택사항

# API 호출
try:
    response = client.CreateLiveTimeShiftTemplate(request)
    template_id = response.TemplateId
    print(f"템플릿 생성 성공: TemplateId = {template_id}")
except Exception as e:
    print(f"템플릿 생성 실패: {e}")
```

---

## 2. Timeshift 템플릿 수정

기존 템플릿의 설정을 변경합니다.

### API: `ModifyLiveTimeShiftTemplate`

### 필수 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `TemplateId` | int | 수정할 템플릿 ID |

### 수정 가능한 파라미터

`CreateLiveTimeShiftTemplate`과 동일하지만, `TemplateId`가 필수입니다.

### API 호출 URL 예시

#### HTTP 요청 예시

```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
Content-Type: application/json
X-TC-Action: ModifyLiveTimeShiftTemplate
X-TC-Version: 2018-08-01
X-TC-Region: ap-seoul
Authorization: TC3-HMAC-SHA256 Credential=YOUR_SECRET_ID/20240101/live/tc3_request, ...
Host: live.tencentcloudapi.com

{
  "TemplateId": 12345,
  "Duration": 7200,
  "ItemDuration": 120,
  "Description": "2시간 타임시프트 템플릿으로 업데이트"
}
```

#### cURL 예시

```bash
curl -X POST https://live.tencentcloudapi.com/ \
  -H "Content-Type: application/json" \
  -H "X-TC-Action: ModifyLiveTimeShiftTemplate" \
  -H "X-TC-Version: 2018-08-01" \
  -H "X-TC-Region: ap-seoul" \
  -H "Authorization: TC3-HMAC-SHA256 ..." \
  -d '{
    "TemplateId": 12345,
    "Duration": 7200,
    "ItemDuration": 120,
    "Description": "2시간 타임시프트 템플릿으로 업데이트"
  }'
```

#### Python SDK 코드 예시

```python
request = live_models.ModifyLiveTimeShiftTemplateRequest()
request.TemplateId = 12345  # 수정할 템플릿 ID
request.Duration = 7200  # 2시간으로 변경
request.ItemDuration = 120  # 2분 세그먼트로 변경
request.Description = "2시간 타임시프트 템플릿으로 업데이트"

try:
    response = client.ModifyLiveTimeShiftTemplate(request)
    print("템플릿 수정 성공")
except Exception as e:
    print(f"템플릿 수정 실패: {e}")
```

---

## 3. Timeshift 규칙 생성

특정 스트림에 타임시프트 템플릿을 적용합니다.

### API: `CreateLiveTimeShiftRule`

### 필수 파라미터

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `DomainName` | string | 라이브 스트리밍 도메인 이름 | `"example.com"` |
| `AppName` | string | 애플리케이션 이름 | `"live"` |
| `StreamName` | string | 스트림 이름 | `"stream123"` |
| `TemplateId` | int | 사용할 타임시프트 템플릿 ID | `12345` |

### 파라미터 상세 설명

#### `DomainName`
- Tencent Cloud CSS에 등록된 푸시/풀 도메인
- 예: `"live.example.com"`

#### `AppName`
- 라이브 스트리밍 애플리케이션 이름
- 일반적으로 `"live"` 또는 사용자 정의 앱 이름
- 도메인 내에서 여러 앱을 구분하는 용도

#### `StreamName`
- 스트림의 고유 이름 (StreamKey)
- 예: `"channel_001"`, `"event_20240101"`

#### `TemplateId`
- `CreateLiveTimeShiftTemplate`으로 생성한 템플릿의 ID

### API 호출 URL 예시

#### HTTP 요청 예시

```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
Content-Type: application/json
X-TC-Action: CreateLiveTimeShiftRule
X-TC-Version: 2018-08-01
X-TC-Region: ap-seoul
Authorization: TC3-HMAC-SHA256 Credential=YOUR_SECRET_ID/20240101/live/tc3_request, ...
Host: live.tencentcloudapi.com

{
  "DomainName": "live.example.com",
  "AppName": "live",
  "StreamName": "channel_001",
  "TemplateId": 12345
}
```

#### cURL 예시

```bash
curl -X POST https://live.tencentcloudapi.com/ \
  -H "Content-Type: application/json" \
  -H "X-TC-Action: CreateLiveTimeShiftRule" \
  -H "X-TC-Version: 2018-08-01" \
  -H "X-TC-Region: ap-seoul" \
  -H "Authorization: TC3-HMAC-SHA256 ..." \
  -d '{
    "DomainName": "live.example.com",
    "AppName": "live",
    "StreamName": "channel_001",
    "TemplateId": 12345
  }'
```

#### Python SDK 코드 예시

```python
# 템플릿 ID 조회 (또는 이전에 생성한 ID 사용)
template_id = 12345

# 규칙 생성 요청
request = live_models.CreateLiveTimeShiftRuleRequest()
request.DomainName = "live.example.com"
request.AppName = "live"
request.StreamName = "channel_001"
request.TemplateId = template_id

try:
    response = client.CreateLiveTimeShiftRule(request)
    print("타임시프트 규칙 생성 성공")
except Exception as e:
    print(f"규칙 생성 실패: {e}")
```

---

## 4. 전체 워크플로우 예시

### 단계별 설정 프로세스

```python
from tencentcloud.common import credential
from tencentcloud.live.v20180801 import live_client, models as live_models

# 1. 클라이언트 초기화
cred = credential.Credential("YOUR_SECRET_ID", "YOUR_SECRET_KEY")
client = live_client.LiveClient(cred, "ap-seoul")

# 2. 타임시프트 템플릿 생성
template_req = live_models.CreateLiveTimeShiftTemplateRequest()
template_req.TemplateName = "timeshift_1hour_template"
template_req.Duration = 3600  # 1시간
template_req.ItemDuration = 60  # 60초 세그먼트
template_req.Area = "Overseas"
template_req.Description = "1시간 타임시프트 템플릿"
template_req.RemoveWatermark = False

template_resp = client.CreateLiveTimeShiftTemplate(template_req)
template_id = template_resp.TemplateId
print(f"템플릿 생성 완료: TemplateId = {template_id}")

# 3. 타임시프트 규칙 생성 (특정 스트림에 적용)
rule_req = live_models.CreateLiveTimeShiftRuleRequest()
rule_req.DomainName = "live.example.com"
rule_req.AppName = "live"
rule_req.StreamName = "channel_001"
rule_req.TemplateId = template_id

rule_resp = client.CreateLiveTimeShiftRule(rule_req)
print("타임시프트 규칙 생성 완료")

# 4. 템플릿 목록 조회 (확인용)
list_req = live_models.DescribeLiveTimeShiftTemplatesRequest()
list_resp = client.DescribeLiveTimeShiftTemplates(list_req)
print(f"생성된 템플릿 수: {len(list_resp.Templates)}")

# 5. 규칙 목록 조회 (확인용)
rules_req = live_models.DescribeLiveTimeShiftRulesRequest()
rules_req.DomainName = "live.example.com"
rules_resp = client.DescribeLiveTimeShiftRules(rules_req)
print(f"생성된 규칙 수: {len(rules_resp.Rules)}")
```

---

## 5. 타임시프트 재생 URL 예시

타임시프트 규칙이 적용된 스트림을 재생할 때 사용하는 URL 형식입니다.

### 일반 라이브 스트리밍 재생 URL

타임시프트 기능을 사용하지 않는 일반 라이브 스트리밍:

```
http://your-playback-domain/appname/streamname.m3u8
```

이 경우 `txTimeshift` 파라미터는 **필요 없습니다**. 현재 라이브 스트림을 실시간으로 재생합니다.

### 타임시프트 재생 URL

과거 방송을 다시 보려면 **반드시 `txTimeshift=on` 파라미터가 필요합니다**.

**⚠️ 중요: `txTimeshift=on`은 타임시프트 재생 시 필수 파라미터입니다.**

- 타임시프트 기능을 사용하려면 URL에 `txTimeshift=on`을 반드시 포함해야 합니다
- 이 파라미터가 없으면 타임시프트 기능이 작동하지 않고 일반 라이브 스트림으로 재생됩니다
- 타임시프트 규칙이 생성되어 있어도, 재생 URL에 `txTimeshift=on`이 없으면 타임시프트가 활성화되지 않습니다

### 타임시프트 재생 URL 예시

#### 1. 특정 시간 구간 재생 (tsStart ~ tsEnd)

```
http://your-playback-domain/appname/streamname.m3u8?txTimeshift=on&tsFormat=unix_s&tsStart=1705658400&tsEnd=1705662000&tsCodecname=hd
```

**파라미터 설명:**
- `txTimeshift=on`: **필수** - 타임시프트 기능 활성화 (없으면 타임시프트 작동 안 함)
- `tsFormat=unix_s`: 시간 형식 (unix timestamp, 초 단위) - `tsStart`/`tsEnd` 사용 시 필요
- `tsStart=1705658400`: 재생 시작 시간 (Unix timestamp) - `tsDelay`와 함께 사용 불가
  - 예시 값 `1705658400` = 2024년 1월 19일 19:00:00 (UTC) = 2024년 1월 20일 04:00:00 (KST)
- `tsEnd=1705662000`: 재생 종료 시간 (Unix timestamp) - 선택사항
  - 예시 값 `1705662000` = 2024년 1월 19일 20:00:00 (UTC) = 2024년 1월 20일 05:00:00 (KST)
  - `tsStart`와의 차이: 3600초 (1시간)
- `tsCodecname=hd`: 트랜스코딩 템플릿 이름 (원본 스트림이면 생략 가능)

**예시:**
```
http://live.example.com/live/channel_001.m3u8?txTimeshift=on&tsFormat=unix_s&tsStart=1705658400&tsEnd=1705662000
```

**Unix Timestamp 계산 방법:**
- Unix timestamp는 1970년 1월 1일 00:00:00 UTC부터 경과한 초(seconds) 수입니다
- Python 예시:
  ```python
  from datetime import datetime
  # 날짜/시간 → Unix timestamp
  dt = datetime(2024, 1, 19, 19, 0, 0)
  timestamp = int(dt.timestamp())  # 1705658400
  
  # Unix timestamp → 날짜/시간
  timestamp = 1705658400
  dt = datetime.fromtimestamp(timestamp)  # 2024-01-19 19:00:00
  ```
- 온라인 변환 도구: https://www.epochconverter.com/

#### 2. 일정 시간 지연 후 재생 (tsDelay)

```
http://your-playback-domain/appname/streamname.m3u8?txTimeshift=on&tsDelay=30&tsCodecname=hd
```

**파라미터 설명:**
- `txTimeshift=on`: **필수** - 타임시프트 기능 활성화 (없으면 타임시프트 작동 안 함)
- `tsDelay=30`: 현재 시점에서 30초 전부터 재생 - `tsStart`와 함께 사용 불가
- `tsCodecname=hd`: 트랜스코딩 템플릿 이름 (선택사항)

**예시:**
```
http://live.example.com/live/channel_001.m3u8?txTimeshift=on&tsDelay=60
```

#### 3. 특정 날짜/시간 재생 (tsStart만 지정)

```
http://your-playback-domain/appname/streamname.m3u8?txTimeshift=on&tsFormat=unix_s&tsStart=1705658400
```

**예시:**
```
http://live.example.com/live/channel_001.m3u8?txTimeshift=on&tsFormat=unix_s&tsStart=1705658400
```

**참고:** `1705658400` = 2024년 1월 19일 19:00:00 (UTC) = 2024년 1월 20일 04:00:00 (KST)

### URL 파라미터 정리

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `txTimeshift` | ✅ **필수** | 타임시프트 활성화 (없으면 타임시프트 작동 안 함) | `on` |
| `tsFormat` | 조건부 | 시간 형식 (`tsStart`/`tsEnd` 사용 시 필요) | `unix_s` (Unix timestamp, 초) |
| `tsStart` | 조건부 | 재생 시작 시간 (`tsDelay`와 함께 사용 불가) | `1705658400` (2024-01-19 19:00:00 UTC) |
| `tsEnd` | ❌ | 재생 종료 시간 | `1705662000` (2024-01-19 20:00:00 UTC) |
| `tsDelay` | 조건부 | 현재 시점에서 지연 시간 (초, `tsStart`와 함께 사용 불가) | `30`, `60` |
| `tsCodecname` | ❌ | 트랜스코딩 템플릿 이름 | `hd`, `sd`, `origin` |

**Unix Timestamp 참고:**
- `1705658400` = 2024년 1월 19일 19:00:00 (UTC) = 2024년 1월 20일 04:00:00 (KST)
- `1705662000` = 2024년 1월 19일 20:00:00 (UTC) = 2024년 1월 20일 05:00:00 (KST)
- 차이: 3600초 (1시간)
- **Unix Timestamp 계산 방법:**
  - Unix timestamp는 1970년 1월 1일 00:00:00 UTC부터 경과한 초(seconds) 수입니다
  - Python 예시:
    ```python
    from datetime import datetime
    # 날짜/시간 → Unix timestamp
    dt = datetime(2024, 1, 19, 19, 0, 0)
    timestamp = int(dt.timestamp())  # 1705658400
    
    # Unix timestamp → 날짜/시간
    timestamp = 1705658400
    dt = datetime.fromtimestamp(timestamp)  # 2024-01-19 19:00:00
    ```
  - 온라인 변환 도구: https://www.epochconverter.com/

### 파라미터 사용 규칙

**⚠️ 필수 사항:**
1. **`txTimeshift=on`은 타임시프트 재생 시 반드시 필요합니다**
   - 이 파라미터가 없으면 타임시프트 기능이 작동하지 않습니다
   - 타임시프트 규칙이 생성되어 있어도 URL에 `txTimeshift=on`이 없으면 일반 라이브 스트림으로 재생됩니다

2. **시간 지정 파라미터는 하나만 사용:**
   - `tsStart`와 `tsDelay` 중 하나만 사용해야 합니다 (동시 사용 불가)

3. **`tsFormat`은 `tsStart`/`tsEnd` 사용 시 필요:**
   - `tsStart` 또는 `tsEnd`를 사용할 때는 `tsFormat=unix_s`가 필요합니다
   - `tsDelay`만 사용할 때는 `tsFormat`이 필요 없습니다

### 사용 시나리오별 예시

#### 시나리오 1: 일반 라이브 스트리밍 (타임시프트 사용 안 함)
```
http://live.example.com/live/channel_001.m3u8
```
- `txTimeshift` 파라미터 없음
- 현재 라이브 스트림을 실시간으로 재생

#### 시나리오 2: 타임시프트 - 특정 시간 구간 재생
```
http://live.example.com/live/channel_001.m3u8?txTimeshift=on&tsFormat=unix_s&tsStart=1705658400&tsEnd=1705662000
```
- `txTimeshift=on` **필수**
- `tsStart=1705658400` (2024-01-19 19:00:00 UTC)와 `tsEnd=1705662000` (2024-01-19 20:00:00 UTC)로 재생 구간 지정
- 재생 구간: 1시간 (2024년 1월 19일 19:00 ~ 20:00 UTC)

#### 시나리오 3: 타임시프트 - 현재 시점에서 1분 전부터 재생
```
http://live.example.com/live/channel_001.m3u8?txTimeshift=on&tsDelay=60
```
- `txTimeshift=on` **필수**
- `tsDelay`로 지연 시간 지정

---

## 6. 관련 API 목록 및 URL 예시

### 템플릿 관리

#### CreateLiveTimeShiftTemplate (템플릿 생성)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: CreateLiveTimeShiftTemplate
X-TC-Version: 2018-08-01

{
  "TemplateName": "timeshift_1hour",
  "Duration": 3600,
  "ItemDuration": 60,
  "Area": "Overseas"
}
```

#### ModifyLiveTimeShiftTemplate (템플릿 수정)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: ModifyLiveTimeShiftTemplate
X-TC-Version: 2018-08-01

{
  "TemplateId": 12345,
  "Duration": 7200
}
```

#### DeleteLiveTimeShiftTemplate (템플릿 삭제)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DeleteLiveTimeShiftTemplate
X-TC-Version: 2018-08-01

{
  "TemplateId": 12345
}
```

#### DescribeLiveTimeShiftTemplates (템플릿 목록 조회)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DescribeLiveTimeShiftTemplates
X-TC-Version: 2018-08-01

{}
```

**응답 예시:**
```json
{
  "Templates": [
    {
      "TemplateId": 12345,
      "TemplateName": "timeshift_1hour",
      "Duration": 3600,
      "ItemDuration": 60,
      "Area": "Overseas",
      "Description": "1시간 타임시프트 템플릿"
    }
  ]
}
```

### 규칙 관리

#### CreateLiveTimeShiftRule (규칙 생성)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: CreateLiveTimeShiftRule
X-TC-Version: 2018-08-01

{
  "DomainName": "live.example.com",
  "AppName": "live",
  "StreamName": "channel_001",
  "TemplateId": 12345
}
```

#### DeleteLiveTimeShiftRule (규칙 삭제)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DeleteLiveTimeShiftRule
X-TC-Version: 2018-08-01

{
  "DomainName": "live.example.com",
  "AppName": "live",
  "StreamName": "channel_001"
}
```

#### DescribeLiveTimeShiftRules (규칙 목록 조회)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DescribeLiveTimeShiftRules
X-TC-Version: 2018-08-01

{
  "DomainName": "live.example.com"
}
```

**응답 예시:**
```json
{
  "Rules": [
    {
      "DomainName": "live.example.com",
      "AppName": "live",
      "StreamName": "channel_001",
      "TemplateId": 12345,
      "CreateTime": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 조회 및 모니터링

#### DescribeTimeShiftStreamList (타임시프트 스트림 목록 조회)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DescribeTimeShiftStreamList
X-TC-Version: 2018-08-01

{
  "StartTime": "2024-01-01T00:00:00Z",
  "EndTime": "2024-01-01T23:59:59Z",
  "StreamName": "channel_001"
}
```

#### DescribeTimeShiftRecordDetail (타임시프트 녹화 상세 정보 조회)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DescribeTimeShiftRecordDetail
X-TC-Version: 2018-08-01

{
  "DomainName": "live.example.com",
  "AppName": "live",
  "StreamName": "channel_001",
  "StartTime": "2024-01-01T00:00:00Z",
  "EndTime": "2024-01-01T23:59:59Z"
}
```

#### DescribeLiveTimeShiftBillInfoList (타임시프트 과금 정보 조회)

**HTTP 요청:**
```http
POST https://live.tencentcloudapi.com/ HTTP/1.1
X-TC-Action: DescribeLiveTimeShiftBillInfoList
X-TC-Version: 2018-08-01

{
  "StartTime": "2024-01-01T00:00:00Z",
  "EndTime": "2024-01-01T23:59:59Z"
}
```

---

## 7. 주의사항 및 베스트 프랙티스

### 주의사항

1. **템플릿 이름 중복**
   - 템플릿 이름은 고유해야 합니다
   - 중복 시 생성 실패

2. **저장 기간 설정**
   - `Duration`은 실제 사용 가능한 저장 용량에 따라 제한될 수 있습니다
   - 과도한 저장 기간은 비용 증가를 유발할 수 있습니다

3. **지역 설정**
   - 한국에서 사용 시 `Area = "Overseas"`로 설정
   - 중국 본토에서 사용 시 `Area = "Mainland"`로 설정

4. **템플릿 삭제**
   - 규칙에 사용 중인 템플릿은 삭제할 수 없습니다
   - 먼저 규칙을 삭제한 후 템플릿을 삭제해야 합니다

### 베스트 프랙티스

1. **템플릿 명명 규칙**
   ```
   timeshift_{duration}_{area}
   예: timeshift_1h_overseas, timeshift_2h_mainland
   ```

2. **저장 기간 권장값**
   - 일반 방송: 1-2시간 (`3600-7200` 초)
   - 이벤트 방송: 4-24시간 (`14400-86400` 초)

3. **세그먼트 길이 권장값**
   - 일반: 60초 (1분)
   - 긴 방송: 120-300초 (2-5분)

4. **에러 처리**
   ```python
   try:
       response = client.CreateLiveTimeShiftTemplate(request)
   except TencentCloudSDKException as e:
       if "TemplateName already exists" in str(e):
           print("템플릿 이름이 이미 존재합니다")
       else:
           print(f"API 오류: {e}")
   except Exception as e:
       print(f"예상치 못한 오류: {e}")
   ```

---

## 8. 참고 자료

- [Tencent Cloud CSS 공식 문서](https://intl.cloud.tencent.com/document/product/267)
- [Tencent Cloud SDK Python 문서](https://github.com/TencentCloud/tencentcloud-sdk-python)
- [Live API 레퍼런스](https://intl.cloud.tencent.com/document/product/267/30760)

---

## 9. FAQ

### Q: `txTimeshift=on` 파라미터가 필수인가요?
A: **네, 필수입니다.** 타임시프트 기능을 사용하려면 재생 URL에 반드시 `txTimeshift=on` 파라미터가 포함되어야 합니다. 이 파라미터가 없으면 타임시프트 규칙이 생성되어 있어도 일반 라이브 스트림으로 재생됩니다.

### Q: 일반 라이브 스트리밍과 타임시프트 재생의 차이는?
A: 
- **일반 라이브 스트리밍**: `txTimeshift` 파라미터 없이 재생 → 현재 실시간 스트림 재생
- **타임시프트 재생**: `txTimeshift=on` 파라미터 포함 → 과거 방송 재생 가능

### Q: 템플릿을 수정하면 기존 규칙에 영향을 주나요?
A: 네, 템플릿을 수정하면 해당 템플릿을 사용하는 모든 규칙에 즉시 반영됩니다.

### Q: 여러 스트림에 동일한 템플릿을 적용할 수 있나요?
A: 네, 하나의 템플릿을 여러 규칙에서 사용할 수 있습니다.

### Q: 타임시프트 저장 용량은 어떻게 계산되나요?
A: 스트림 비트레이트 × 저장 기간(Duration)으로 계산됩니다. Tencent Cloud 콘솔에서 상세 과금 정보를 확인할 수 있습니다.

### Q: 타임시프트 스트림을 시청하는 방법은?
A: Tencent Cloud에서 제공하는 타임시프트 재생 URL을 사용합니다. `DescribeTimeShiftStreamList` API로 재생 URL을 조회할 수 있습니다. 재생 URL에는 반드시 `txTimeshift=on` 파라미터가 포함되어야 합니다.

### Q: `tsStart`와 `tsDelay`를 동시에 사용할 수 있나요?
A: 아니요, `tsStart`와 `tsDelay`는 동시에 사용할 수 없습니다. 둘 중 하나만 선택해서 사용해야 합니다.
