# 활성 소스 감지의 한계 및 개선 방안

## 문제점

### 현재 로직의 한계

**상황:**
- `QueryInputStreamState` API에서 두 소스가 모두 `Status == 1` (활성)인 경우
- 현재 로직은 첫 번째 활성 소스를 main으로 판단
- 하지만 실제로 StreamLive가 어떤 소스를 서비스 중인지는 정확히 알 수 없음

**사용자 지적:**
> "2소스가 다 활성이면 메인이 서비스 중인거고 끊겨야 백업전환이라고 생각하는거네 ~ 흠.. api 가 정말 없을까?"

## 현재 로직 분석

### QueryInputStreamState 응답 예시

```json
{
  "Info": {
    "InputID": "695E065C00004F07D2D4",
    "InputName": "sbs_no1_news",
    "Protocol": "RTMP_PUSH",
    "InputStreamInfoList": [
      {
        "InputAddress": "rtmp://...ap-seoul-1...",
        "AppName": "...",
        "StreamName": "...",
        "Status": 1  // 활성
      },
      {
        "InputAddress": "rtmp://...ap-seoul-2...",
        "AppName": "...",
        "StreamName": "...",
        "Status": 1  // 활성
      }
    ]
  }
}
```

**문제:**
- 두 소스가 모두 `Status == 1` (활성)
- 하지만 실제로 StreamLive가 어떤 소스를 서비스 중인지는 알 수 없음
- 현재 로직: 첫 번째 활성 소스를 main으로 판단

### 현재 코드 로직

```python
active_sources = []
for stream_info in stream_infos:
    status = getattr(stream_info, "Status", 0)
    if status == 1:  # 활성 소스
        active_sources.append({
            "address": input_address,
            "type": source_type,
            "status": status
        })

# 첫 번째 활성 소스를 사용
if active_sources:
    primary_source = active_sources[0]  # ← 첫 번째를 선택
    active_input_type = primary_source.get("type")
```

**한계:**
- 두 소스가 모두 활성인 경우, 첫 번째를 선택
- 실제로 StreamLive가 어떤 소스를 사용하는지는 알 수 없음

## API 조사 결과

### 1. DescribeStreamLiveChannel

**응답 구조:**
- `AttachedInputs`: 연결된 입력 목록
- `FailOverSettings`: Failover 설정
- **하지만 현재 활성 입력을 직접 알려주는 필드는 없음**

### 2. QueryInputStreamState

**응답 구조:**
- `InputStreamInfoList`: 각 소스 주소의 상태
- `Status`: 1=활성, 0=비활성
- **하지만 실제로 서비스 중인 소스를 직접 알려주는 필드는 없음**

### 3. DescribeStreamLiveChannelInputStatistics

**응답 구조:**
- 각 입력의 통계 정보
- `NetworkValid`, `NetworkIn` 등
- **하지만 실제로 서비스 중인 소스를 직접 알려주는 필드는 없음**

## 가능한 해결 방안

### 방안 1: 통계 데이터 활용

**방법:**
- `DescribeStreamLiveChannelInputStatistics`에서 각 소스의 데이터 흐름 확인
- `NetworkIn`이 더 큰 소스가 실제 서비스 중일 가능성

**장점:**
- 실제 데이터 흐름 확인 가능

**단점:**
- 통계 수집 지연 가능
- 두 소스 모두 데이터가 있을 수 있음

### 방안 2: StreamLink 플로우 상태 확인

**방법:**
- StreamLink 플로우의 출력 URL 확인
- 어떤 소스 주소로 연결되어 있는지 확인

**장점:**
- 실제 연결 상태 확인 가능

**단점:**
- StreamLink와 StreamLive가 직접 연결되어 있어야 함
- Input Source Redundancy에서는 한 입력에 여러 소스 주소가 있음

### 방안 3: 실시간 모니터링

**방법:**
- 일정 시간 동안 모니터링
- 소스 전환 이벤트 추적
- 상태 변화 감지

**장점:**
- 실시간 상태 확인 가능

**단점:**
- 지속적인 모니터링 필요
- 복잡한 구현

### 방안 4: Tencent Cloud 지원팀 문의

**방법:**
- Tencent Cloud 지원팀에 문의
- 실제로 서비스 중인 소스를 알려주는 API가 있는지 확인

**장점:**
- 공식 답변 확인 가능

**단점:**
- 시간 소요
- API가 없을 수 있음

## 개선된 로직 제안

### 현재 로직 개선

```python
# 1. QueryInputStreamState로 활성 소스 확인
active_sources = []
for stream_info in stream_infos:
    if stream_info.Status == 1:
        active_sources.append(stream_info)

# 2. 두 소스가 모두 활성인 경우
if len(active_sources) > 1:
    # 통계 데이터 확인
    stats = get_input_statistics(channel_id, input_id)
    
    # NetworkIn이 더 큰 소스 선택
    max_network_in = 0
    active_source = None
    for source in active_sources:
        network_in = get_network_in_for_source(source, stats)
        if network_in > max_network_in:
            max_network_in = network_in
            active_source = source
    
    # 또는 StreamLink 플로우 상태 확인
    # 또는 첫 번째 소스를 main으로 가정 (현재 로직)
```

### 주의사항

**현재 상황:**
- 두 소스가 모두 `Status == 1`인 경우
- 실제로 StreamLive가 어떤 소스를 사용하는지는 정확히 알 수 없음
- 첫 번째 소스를 main으로 가정하는 것이 합리적일 수 있음

**이유:**
- Input Source Redundancy에서 main 소스가 우선
- main 소스가 정상이면 main 소스를 사용
- main 소스가 실패하면 backup 소스로 전환
- 두 소스가 모두 활성인 경우, main 소스가 서비스 중일 가능성이 높음

## 결론

### 현재 상황

1. **API 한계:**
   - StreamLive API에서 실제로 서비스 중인 소스를 직접 알려주는 필드는 없음
   - `QueryInputStreamState`에서 두 소스가 모두 `Status == 1`인 경우, 실제 사용 중인 소스를 구분할 수 없음

2. **현재 로직:**
   - 첫 번째 활성 소스를 main으로 판단
   - 두 소스가 모두 활성인 경우, main 소스가 서비스 중일 가능성이 높음

3. **개선 방안:**
   - 통계 데이터 활용
   - StreamLink 플로우 상태 확인
   - 실시간 모니터링
   - Tencent Cloud 지원팀 문의

### 권장 사항

1. **현재 로직 유지:**
   - 두 소스가 모두 활성인 경우, 첫 번째 소스를 main으로 판단
   - 대부분의 경우 main 소스가 서비스 중일 가능성이 높음

2. **추가 검증:**
   - 통계 데이터로 보조 검증
   - StreamLink 플로우 상태로 보조 검증

3. **문서화:**
   - 현재 로직의 한계를 문서화
   - 사용자에게 알림

4. **Tencent Cloud 지원팀 문의:**
   - 실제로 서비스 중인 소스를 알려주는 API가 있는지 확인
   - 또는 향후 추가될 예정인지 확인
