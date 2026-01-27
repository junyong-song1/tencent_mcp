# StreamLive API: 활성 소스 직접 확인 방법

## 발견: QueryInputStreamState API

### API 정보

**API 이름:** `QueryInputStreamState`  
**목적:** 입력의 스트림 상태 조회  
**파라미터:** `Id` (입력 ID) - **필수**  
**응답:** `InputStreamInfoList` - 각 소스 주소의 상태 정보

### 파라미터

**필수 파라미터:**
- `Id`: 입력 ID (Input ID)

**주의:**
- `ChannelId`와 `InputId`를 함께 사용하면 `MissingParameter` 오류 발생
- `Id`만 사용해야 함 (입력 ID)

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

### 핵심 필드

**InputStreamInfoList:**
- `InputAddress`: 소스 주소 (예: `rtmp://...ap-seoul-1...` 또는 `rtmp://...ap-seoul-2...`)
- `AppName`: 애플리케이션 이름
- `StreamName`: 스트림 이름
- `Status`: 상태 (1=활성, 0=비활성)

**활성 소스 판단:**
- `Status == 1`인 소스가 실제로 StreamLive가 사용 중인 소스
- `InputAddress`에서 `ap-seoul-1` vs `ap-seoul-2`로 main/backup 구분 가능

## 사용 방법

### Python SDK 예제

```python
from tencentcloud.mdl.v20200326 import mdl_client, models as mdl_models

# 입력 ID로 QueryInputStreamState 호출
query_req = mdl_models.QueryInputStreamStateRequest()
query_req.Id = input_id  # 입력 ID만 설정

query_resp = mdl_cli.QueryInputStreamState(query_req)

# 응답에서 활성 소스 확인
if hasattr(query_resp, 'Info') and hasattr(query_resp.Info, 'InputStreamInfoList'):
    stream_infos = query_resp.Info.InputStreamInfoList
    
    for stream_info in stream_infos:
        status = getattr(stream_info, 'Status', 0)
        input_address = getattr(stream_info, 'InputAddress', '')
        
        if status == 1:  # 활성 소스
            # ap-seoul-1 vs ap-seoul-2로 main/backup 판단
            if 'ap-seoul-1' in input_address.lower():
                active_source_type = 'main'
            elif 'ap-seoul-2' in input_address.lower():
                active_source_type = 'backup'
            
            print(f"활성 소스: {active_source_type} ({input_address})")
```

## 다른 StreamLive API 목록

### Input 관련 API (12개)

1. `CreateStreamLiveInput` - 입력 생성
2. `DeleteStreamLiveInput` - 입력 삭제
3. `DescribeStreamLiveInput` - 입력 상세 조회
4. `DescribeStreamLiveInputs` - 입력 목록 조회
5. `ModifyStreamLiveInput` - 입력 수정
6. `QueryInputStreamState` - **입력 스트림 상태 조회** ⭐
7. `CreateStreamLiveInputSecurityGroup` - 입력 보안 그룹 생성
8. `DeleteStreamLiveInputSecurityGroup` - 입력 보안 그룹 삭제
9. `DescribeStreamLiveInputSecurityGroup` - 입력 보안 그룹 조회
10. `DescribeStreamLiveInputSecurityGroups` - 입력 보안 그룹 목록 조회
11. `ModifyStreamLiveInputSecurityGroup` - 입력 보안 그룹 수정

### Statistics 관련 API (3개)

1. `DescribeStreamLiveChannelInputStatistics` - 채널 입력 통계
2. `DescribeStreamLiveChannelOutputStatistics` - 채널 출력 통계
3. `QueryInputStreamState` - **입력 스트림 상태 조회** ⭐

### Query 관련 API (1개)

1. `QueryInputStreamState` - **입력 스트림 상태 조회** ⭐

## QueryInputStreamState의 장점

### 1. 직접적인 활성 소스 확인

**기존 방법 (간접):**
- StreamLink 플로우 상태 확인
- URL 매칭으로 추론
- 통계 데이터로 추론

**QueryInputStreamState (직접):**
- StreamLive가 직접 제공하는 상태 정보
- `Status == 1`이면 실제로 활성
- `InputAddress`로 정확한 소스 주소 확인

### 2. Input Source Redundancy 지원

**하나의 입력에 여러 소스 주소가 있는 경우:**
- `InputStreamInfoList`에 모든 소스 주소 포함
- 각 소스 주소의 `Status` 확인 가능
- `Status == 1`인 소스가 실제 활성 소스

### 3. 실시간 상태 확인

**통계 API와의 차이:**
- `DescribeStreamLiveChannelInputStatistics`: 통계 수집 지연
- `QueryInputStreamState`: 실시간 상태 확인

## 활용 방안

### 현재 코드 개선

**기존 로직:**
1. StreamLink 플로우 상태 확인
2. URL 매칭으로 추론
3. 통계 데이터 확인 (지연)

**개선된 로직:**
1. **QueryInputStreamState로 직접 확인** (최우선)
   - 각 입력에 대해 `QueryInputStreamState` 호출
   - `Status == 1`인 소스 주소 확인
   - `ap-seoul-1` vs `ap-seoul-2`로 main/backup 판단
2. StreamLink 플로우 상태 확인 (보조)
3. 통계 데이터 확인 (보조)

### 우선순위

**Priority 1: QueryInputStreamState** (가장 신뢰)
- StreamLive가 직접 제공하는 상태 정보
- 실시간 확인 가능
- 정확한 활성 소스 주소 확인

**Priority 2: StreamLink 플로우 상태**
- StreamLink 플로우가 실행 중인지 확인
- 보조 검증용

**Priority 3: 통계 데이터**
- 데이터 수집 지연으로 실시간 확인 어려움
- 보조 검증용

## 결론

**QueryInputStreamState API 발견:**
- ✅ 실제로 작동하는 API
- ✅ 파라미터: `Id` (입력 ID)만 필요
- ✅ 응답: `InputStreamInfoList`에서 각 소스 주소의 `Status` 확인
- ✅ `Status == 1`인 소스가 실제 활성 소스

**활용:**
- 현재 코드의 최우선 검증 방법으로 사용 가능
- StreamLive가 직접 제공하는 상태 정보로 정확한 활성 소스 확인
- Input Source Redundancy 방식에서도 정확한 활성 소스 주소 확인 가능
