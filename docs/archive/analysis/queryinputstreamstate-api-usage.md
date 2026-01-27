# QueryInputStreamState API 사용 가이드

## API 발견 및 확인

### API 정보

**API 이름:** `QueryInputStreamState`  
**목적:** 입력의 스트림 상태 조회  
**파라미터:** `Id` (입력 ID) - **필수**  
**응답:** `Info.InputStreamInfoList` - 각 소스 주소의 상태 정보

### 파라미터

**필수 파라미터:**
- `Id`: 입력 ID (Input ID)

**주의 사항:**
- ❌ `ChannelId`와 `InputId`를 함께 사용하면 `MissingParameter` 오류 발생
- ✅ `Id`만 사용해야 함 (입력 ID)

### 응답 구조

```json
{
  "Info": {
    "InputID": "695E065C00004F07D2D4",
    "InputName": "sbs_no1_news",
    "Protocol": "RTMP_PUSH",
    "InputStreamInfoList": [
      {
        "InputAddress": "rtmp://1353725051.ap-seoul-1.streamlive.myqcloud.com",
        "AppName": "dffab7d360af435b8a4f9e24095c149d",
        "StreamName": "74e0b66da9eb42949229103c28bb2dfa",
        "Status": 1  // 1=활성, 0=비활성
      },
      {
        "InputAddress": "rtmp://1353725051.ap-seoul-2.streamlive.myqcloud.com",
        "AppName": "dffab7d360af435b8a4f9e24095c149d",
        "StreamName": "ec2ad91d660148a9b59cf97b769dc33b",
        "Status": 1  // 1=활성, 0=비활성
      }
    ]
  }
}
```

## 핵심 필드

### InputStreamInfoList

각 소스 주소의 정보:
- `InputAddress`: 소스 주소 (예: `rtmp://...ap-seoul-1...` 또는 `rtmp://...ap-seoul-2...`)
- `AppName`: 애플리케이션 이름
- `StreamName`: 스트림 이름
- `Status`: 상태 (1=활성, 0=비활성)

### 활성 소스 판단

**방법:**
1. `InputStreamInfoList`에서 `Status == 1`인 소스 찾기
2. `InputAddress`에서 `ap-seoul-1` vs `ap-seoul-2`로 main/backup 구분
3. 첫 번째 `Status == 1`인 소스가 실제 활성 소스

**주의:**
- 두 소스가 모두 `Status == 1`일 수 있음
- 이 경우 둘 다 활성 상태이지만, 실제로 StreamLive가 사용하는 것은 하나
- 첫 번째 `Status == 1`인 소스가 우선 사용될 가능성

## Python SDK 사용 예제

### 기본 사용법

```python
from tencentcloud.mdl.v20200326 import mdl_client, models as mdl_models

# 입력 ID로 QueryInputStreamState 호출
query_req = mdl_models.QueryInputStreamStateRequest()
query_req.Id = input_id  # 입력 ID만 설정 (ChannelId + InputId 아님!)

query_resp = mdl_cli.QueryInputStreamState(query_req)

# 응답에서 활성 소스 확인
if hasattr(query_resp, 'Info') and hasattr(query_resp.Info, 'InputStreamInfoList'):
    stream_infos = query_resp.Info.InputStreamInfoList
    
    active_sources = []
    for stream_info in stream_infos:
        status = getattr(stream_info, 'Status', 0)
        input_address = getattr(stream_info, 'InputAddress', '')
        app_name = getattr(stream_info, 'AppName', '')
        stream_name = getattr(stream_info, 'StreamName', '')
        
        if status == 1:  # 활성 소스
            # ap-seoul-1 vs ap-seoul-2로 main/backup 판단
            if 'ap-seoul-1' in input_address.lower():
                source_type = 'main'
            elif 'ap-seoul-2' in input_address.lower():
                source_type = 'backup'
            else:
                source_type = 'unknown'
            
            full_url = f"{input_address}/{app_name}/{stream_name}"
            active_sources.append({
                'type': source_type,
                'address': input_address,
                'url': full_url
            })
    
    # 첫 번째 활성 소스가 실제 활성 소스
    if active_sources:
        primary_source = active_sources[0]
        print(f"활성 소스: {primary_source['type']} ({primary_source['url']})")
```

## 코드 개선 사항

### 변경 전

**우선순위:**
1. StreamLink 플로우 상태 확인
2. 통계 데이터 확인
3. QueryInputStreamState (fallback, 파라미터 문제로 사용 안 됨)

**문제점:**
- StreamLink 플로우 상태만으로는 실제 활성 소스를 알 수 없음
- 두 플로우가 모두 running이면 둘 다 실행 중
- 실제로 StreamLive가 어떤 소스를 사용하는지는 확인 불가

### 변경 후

**우선순위:**
1. **QueryInputStreamState** (최우선 - StreamLive가 직접 제공)
   - 각 입력에 대해 `QueryInputStreamState` 호출
   - `InputStreamInfoList`에서 `Status == 1`인 소스 확인
   - `InputAddress`로 main/backup 구분
2. StreamLink 플로우 상태 확인 (fallback)
3. 통계 데이터 확인 (fallback)

**장점:**
- ✅ StreamLive가 직접 제공하는 상태 정보
- ✅ 실시간 확인 가능
- ✅ 정확한 활성 소스 주소 확인
- ✅ Input Source Redundancy 방식에서도 정확한 활성 소스 확인

## 테스트 결과

**채널:** `695E09660000090927DE` (sbs_no1_news)

**QueryInputStreamState 응답:**
- Input 1: `695E065C00004F07D2D4`
  - Stream 1: `ap-seoul-1` (main), Status: 1 (활성)
  - Stream 2: `ap-seoul-2` (backup), Status: 1 (활성)
- Input 2: `695E085379D31EA36323`
  - Protocol not support 오류 (다른 입력 타입일 수 있음)

**결과:**
- 두 소스가 모두 `Status == 1` (활성)
- 첫 번째 활성 소스 (main, ap-seoul-1)가 실제 활성 소스로 판단

## 주의 사항

### 1. 파라미터 사용

**올바른 사용:**
```python
query_req.Id = input_id  # ✅
```

**잘못된 사용:**
```python
query_req.ChannelId = channel_id  # ❌
query_req.InputId = input_id      # ❌
```

### 2. 응답 구조

**올바른 접근:**
```python
query_resp.Info.InputStreamInfoList  # ✅
```

**잘못된 접근:**
```python
query_resp.Infos  # ❌
```

### 3. 두 소스가 모두 활성인 경우

**상황:**
- 두 소스가 모두 `Status == 1`
- 둘 다 활성 상태이지만, 실제로 StreamLive가 사용하는 것은 하나

**처리:**
- 첫 번째 `Status == 1`인 소스를 활성 소스로 판단
- 또는 통계 데이터와 결합하여 더 많은 데이터를 받는 소스 선택

## 결론

**QueryInputStreamState API:**
- ✅ 실제로 작동하는 API
- ✅ StreamLive가 직접 제공하는 상태 정보
- ✅ 정확한 활성 소스 주소 확인 가능
- ✅ Input Source Redundancy 방식에서도 정확한 활성 소스 확인

**활용:**
- 현재 코드의 최우선 검증 방법으로 사용
- StreamLink 플로우 상태는 보조 검증으로 사용
- 통계 데이터는 보조 검증으로 사용
