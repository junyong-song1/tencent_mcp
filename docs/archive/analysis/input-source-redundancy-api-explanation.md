# Input Source Redundancy와 StreamLive API 관계 설명

## 질문

**"Input Source Redundancy"는 StreamLive API에서 제공하는 것인가?**

## 답변

### 1. Input Source Redundancy는 StreamLive의 기능입니다

**Input Source Redundancy**는 StreamLive의 기능으로, 하나의 입력에 여러 소스 주소를 설정할 수 있습니다.

**예시:**
```
하나의 입력 (3tier_3pro_tv)
  ├─ InputAddress01: rtmp://...ap-seoul-1... (main)
  └─ InputAddress02: rtmp://...ap-seoul-2... (backup)
```

### 2. QueryInputStreamState API는 StreamLive API입니다

**`QueryInputStreamState`**는 StreamLive API로, 입력의 스트림 상태를 조회합니다.

**API 정보:**
- **서비스**: StreamLive (MDL)
- **API 이름**: `QueryInputStreamState`
- **파라미터**: `Id` (입력 ID)
- **응답**: `Info.InputStreamInfoList` - 각 소스 주소의 상태 정보

### 3. "InputSourceRedundancy" 필드명은 우리가 사용하는 플래그입니다

**중요:** API에서 직접 "InputSourceRedundancy"라는 필드를 제공하는 것은 아닙니다.

**우리가 하는 일:**
1. `QueryInputStreamState` API를 호출
2. 응답의 `InputStreamInfoList`를 확인
3. 여러 소스 주소가 있고, 그 중 여러 개가 활성(`Status == 1`)인 경우를 감지
4. 이 경우 `is_input_source_redundancy = True`로 설정

## QueryInputStreamState API 응답 구조

### 일반적인 경우 (단일 소스)

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
        "Status": 1
      }
    ]
  }
}
```

**특징:**
- `InputStreamInfoList`에 하나의 소스 주소만 있음
- Input Source Redundancy가 아닌 경우

### Input Source Redundancy인 경우 (여러 소스)

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
        "Status": 1  // 활성
      },
      {
        "InputAddress": "rtmp://1353725051.ap-seoul-2.streamlive.myqcloud.com",
        "AppName": "dffab7d360af435b8a4f9e24095c149d",
        "StreamName": "ec2ad91d660148a9b59cf97b769dc33b",
        "Status": 1  // 활성 (또는 0=비활성)
      }
    ]
  }
}
```

**특징:**
- `InputStreamInfoList`에 여러 소스 주소가 있음
- 이것이 Input Source Redundancy 방식입니다
- 각 소스 주소의 `Status`로 활성/비활성 확인 가능

## 우리 코드에서의 감지 로직

### 1. QueryInputStreamState 호출

```python
query_req = mdl_models.QueryInputStreamStateRequest()
query_req.Id = inp_id  # 입력 ID

query_resp = client.QueryInputStreamState(query_req)
```

### 2. InputStreamInfoList 확인

```python
if hasattr(query_resp, "Info") and query_resp.Info:
    info_obj = query_resp.Info
    
    if hasattr(info_obj, "InputStreamInfoList") and info_obj.InputStreamInfoList:
        stream_infos = info_obj.InputStreamInfoList
        
        active_sources = []
        for stream_info in stream_infos:
            input_address = getattr(stream_info, "InputAddress", "")
            status = getattr(stream_info, "Status", 0)
            
            if status == 1:  # 활성 소스
                active_sources.append({
                    "address": input_address,
                    "type": "main" if "ap-seoul-1" in input_address.lower() else "backup",
                    "status": status
                })
```

### 3. Input Source Redundancy 감지

```python
# 여러 소스 주소가 있고, 그 중 여러 개가 활성인 경우
if len(active_sources) > 1:
    is_input_source_redundancy = True
    verification_sources.append("InputSourceRedundancy")
```

**의미:**
- `InputStreamInfoList`에 여러 소스 주소가 있음
- 그 중 여러 개가 활성(`Status == 1`)인 경우
- 이것이 Input Source Redundancy 방식입니다

## 정리

### StreamLive API에서 제공하는 것

1. **`QueryInputStreamState` API**
   - StreamLive API입니다
   - 입력의 스트림 상태를 조회합니다
   - `InputStreamInfoList`를 반환합니다

2. **`InputStreamInfoList`**
   - 각 소스 주소의 정보를 포함합니다
   - `InputAddress`, `Status` 등이 포함됩니다
   - 여러 소스 주소가 있으면 Input Source Redundancy 방식입니다

### 우리가 감지하는 것

1. **Input Source Redundancy 감지**
   - `InputStreamInfoList`에 여러 소스 주소가 있는지 확인
   - 여러 개가 활성인지 확인
   - 이 경우 `is_input_source_redundancy = True`로 설정

2. **활성 소스 판단**
   - `Status == 1`인 소스 찾기
   - `InputAddress`에서 `ap-seoul-1` vs `ap-seoul-2`로 main/backup 구분

## 결론

**질문: "Input Source Redundancy"는 StreamLive API에서 제공하는 것인가?**

**답변:**
- ✅ **Input Source Redundancy는 StreamLive의 기능**입니다
- ✅ **`QueryInputStreamState` API는 StreamLive API**입니다
- ✅ **`InputStreamInfoList`에 여러 소스 주소가 있으면 Input Source Redundancy 방식**입니다
- ❌ **하지만 "InputSourceRedundancy"라는 필드명은 API에서 직접 제공하는 것은 아닙니다**
- ✅ **우리가 `InputStreamInfoList`의 구조를 분석하여 Input Source Redundancy를 감지합니다**

**요약:**
- StreamLive API (`QueryInputStreamState`)에서 여러 소스 주소 정보를 받습니다
- 우리가 이 정보를 분석하여 Input Source Redundancy를 감지합니다
- "InputSourceRedundancy"는 검증 소스 이름으로 사용되며, API에서 직접 제공하는 필드는 아닙니다
