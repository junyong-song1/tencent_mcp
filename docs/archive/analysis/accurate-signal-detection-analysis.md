# 정확한 신호 감지 분석 문서

## 문제 상황

현재 cj_onstyle 채널의 서비스 신호를 확인했을 때:
- StreamPackage/CSS 검증: MAIN
- 하지만 실제로는 다른 신호일 가능성

## 핵심 문제점

### 1. StreamPackage 입력 순서 기반 판단의 한계

**현재 구현:**
```python
# 첫 번째 입력 = MAIN, 두 번째 입력 = BACKUP
active_input_type = "main" if idx == 0 else "backup"
```

**문제:**
- StreamPackage API는 **어떤 입력이 실제로 활성화되어 있는지**를 직접 알려주지 않음
- 입력 URL이 모두 설정되어 있어도 실제 데이터 흐름은 확인 불가
- 입력 순서만으로는 실제 활성 입력을 판단할 수 없음

### 2. StreamLive 출력 URL 매칭 부재

**필요한 정보:**
- StreamLive 채널의 OutputGroups에서 실제 출력 URL 추출
- StreamPackage 입력 URL과 매칭하여 어떤 입력이 사용 중인지 확인

**현재 상태:**
- StreamPackageSettings에는 ID만 있고 출력 URL 정보 없음
- StreamLive → StreamPackage 연결 정보만 확인 가능

## 정확한 감지 방법

### 방법 1: StreamLink 플로우 상태 확인 (가장 신뢰)

**장점:**
- 실시간 상태 확인 가능
- 플로우 이름으로 main/backup 명확히 구분
- 실행 중인 플로우 = 실제 활성 신호

**구현:**
```python
# 1. StreamLink 플로우 목록 가져오기
flows = client.list_streamlink_inputs()

# 2. StreamLive 채널과 연결된 플로우 찾기
linked_flows = LinkageMatcher.find_linked_flows(channel_info, flows)

# 3. 실행 중인 플로우 확인
running_flows = [f for f in linked_flows if f.get('status') == 'running']

# 4. 플로우 이름으로 main/backup 구분
for flow in running_flows:
    is_backup = '_b' in flow_name.lower() or 'backup' in flow_name.lower()
    signal_type = 'BACKUP' if is_backup else 'MAIN'
```

### 방법 2: StreamLive 입력 통계 확인

**API:** `DescribeStreamLiveChannelInputStatistics`

**장점:**
- 각 입력의 실제 트래픽 확인 가능
- `NetworkValid=True`이고 `NetworkIn > 0`인 입력 = 활성 입력

**제한사항:**
- 통계 수집 지연 가능
- 실시간 반영이 안 될 수 있음

**구현:**
```python
stats_req = mdl_models.DescribeStreamLiveChannelInputStatisticsRequest()
stats_req.ChannelId = channel_id
stats_resp = client.DescribeStreamLiveChannelInputStatistics(stats_req)

# NetworkValid=True이고 NetworkIn이 가장 큰 입력 찾기
for stat_info in stats_resp.Infos:
    if stat_info.NetworkValid and stat_info.NetworkIn > max_bandwidth:
        active_input_id = stat_info.InputId
```

### 방법 3: QueryInputStreamState API

**API:** `QueryInputStreamState`

**장점:**
- 각 입력의 실시간 상태 직접 확인
- `Status=1` = 활성, `Status=0` = 비활성

**제한사항:**
- 파라미터 구조 문제로 현재 사용 불가
- InputId별로 개별 호출 필요

### 방법 4: StreamPackage 입력 URL과 StreamLive 출력 URL 매칭

**필요한 정보:**
1. StreamLive 채널의 실제 출력 URL
2. StreamPackage 입력 URL 목록
3. URL 매칭 로직

**현재 문제:**
- StreamLive OutputGroups에서 출력 URL 추출 방법 불명확
- StreamPackageSettings에는 ID만 있고 URL 정보 없음

**개선 방안:**
- StreamPackage 채널의 Endpoints 확인 (CSS pull URL)
- StreamLive 출력이 StreamPackage로 들어가는 경로 추적
- URL 패턴 매칭

## 권장 검증 순서

### 1순위: StreamLink 플로우 상태 (가장 신뢰)
```python
# 실행 중인 플로우 = 실제 활성 신호
running_flows = [f for f in linked_flows if f.get('status') == 'running']
```

### 2순위: StreamLive 입력 통계
```python
# NetworkValid=True이고 NetworkIn이 가장 큰 입력
if network_valid and network_in > max_bandwidth:
    active_input_id = inp_id
```

### 3순위: StreamPackage 입력 순서 (보조 확인)
```python
# 첫 번째 입력 = MAIN (추정)
# 실제 활성 입력은 StreamLink나 통계로 확인 필요
```

## cj_onstyle 채널 분석

### 확인해야 할 사항

1. **StreamLink 플로우 상태**
   - 실행 중인 플로우 이름 확인
   - `_b` 또는 `backup` 포함 여부
   - `_m` 또는 `main` 포함 여부

2. **StreamLive 입력 통계**
   - 각 입력의 `NetworkValid` 상태
   - 각 입력의 `NetworkIn` 값
   - 가장 높은 대역폭을 가진 입력

3. **StreamPackage 입력 URL**
   - 실제로 데이터가 들어오는 입력 확인
   - URL 패턴 분석

## 결론

**가장 정확한 방법:**
1. StreamLink 플로우 상태 확인 (실시간, 명확)
2. StreamLive 입력 통계 확인 (실제 트래픽)
3. StreamPackage 입력 순서 (보조 확인)

**현재 구현의 문제:**
- StreamPackage 입력 순서만으로 판단하는 것은 부정확
- StreamLink 플로우 상태를 우선 확인해야 함
