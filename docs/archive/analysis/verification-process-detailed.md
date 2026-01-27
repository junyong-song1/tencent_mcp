# 검증 프로세스 상세 설명

## 문제점

**Tencent Cloud SDK의 한계:**
- StreamLive에서 "어떤 입력이 현재 활성인지"를 직접 알려주는 API가 **없음**
- Failover 기능이 있어도 활성 입력 ID를 직접 반환하지 않음
- 따라서 **간접적인 방법**으로 추론해야 함

## 검증 프로세스 (우선순위 순)

### 1순위: StreamLink 플로우 상태 확인 ⭐ (가장 신뢰)

**방법:**
```python
# StreamLink 플로우 목록 가져오기
flows = client.list_streamlink_inputs()

# StreamLive 채널과 연결된 플로우 찾기
linked_flows = LinkageMatcher.find_linked_flows(channel_info, flows)

# 실행 중인 플로우 확인
running_flows = [f for f in linked_flows if f.get('status') == 'running']

# 플로우 이름으로 main/backup 구분
for flow in running_flows:
    is_backup = '_b' in flow_name.lower() or 'backup' in flow_name.lower()
    signal_type = 'BACKUP' if is_backup else 'MAIN'
```

**확인 값:**
- 플로우 이름: `cj_onstyle_m2`, `cj_onstyle_b2`
- 플로우 상태: `running` (실행 중), `idle` (대기 중)
- 출력 URL: StreamLive 입력 엔드포인트와 매칭

**장점:**
- ✅ 실시간 상태 확인
- ✅ 명확한 main/backup 구분 (플로우 이름)
- ✅ 가장 신뢰할 수 있는 지표

**예시:**
```
플로우: cj_onstyle_m2
상태: running
신호 타입: MAIN
→ 이 신호가 활성화되어 있음
```

### 2순위: StreamLive 입력 통계 확인

**API:** `DescribeStreamLiveChannelInputStatistics`

**방법:**
```python
stats_req = mdl_models.DescribeStreamLiveChannelInputStatisticsRequest()
stats_req.ChannelId = channel_id
stats_resp = client.DescribeStreamLiveChannelInputStatistics(stats_req)

# NetworkValid=True이고 NetworkIn이 가장 큰 입력 찾기
for stat_info in stats_resp.Infos:
    if stat_info.NetworkValid and stat_info.NetworkIn > max_bandwidth:
        active_input_id = stat_info.InputId
```

**확인 값:**
- `NetworkValid`: 네트워크 유효 여부 (True/False)
- `NetworkIn`: 입력 대역폭 (bytes)

**장점:**
- ✅ 실제 트래픽 확인
- ✅ 각 입력의 데이터 흐름 확인

**제한사항:**
- ⚠️ 통계 수집 지연 가능
- ⚠️ 실시간 반영이 안 될 수 있음
- ⚠️ `NetworkValid=False, NetworkIn=0`일 수 있음 (데이터 없음)

**예시:**
```
Input ID: 69425CAF0000BBDE05D7
NetworkValid: True
NetworkIn: 1234567 bytes
→ 활성 입력으로 판단 가능
```

### 3순위: StreamPackage 입력 순서 확인 (보조)

**API:** `DescribeStreamPackageChannel`

**방법:**
```python
# StreamPackage 채널의 Points.Inputs 확인
inputs = points.Inputs
# 첫 번째 입력 = MAIN (primary)
# 두 번째 입력 = BACKUP (secondary)
active_input_type = "main" if idx == 0 else "backup"
```

**확인 값:**
- 입력 URL 목록: `Points.Inputs` 배열
- 입력 순서: 첫 번째 = MAIN, 두 번째 = BACKUP

**장점:**
- ✅ 입력 구성 확인 가능

**제한사항:**
- ⚠️ **입력 순서만 확인**, 실제 활성 입력 보장 안 됨
- ⚠️ 두 입력이 모두 설정되어 있어도 실제로 어떤 입력에서 데이터가 들어오는지는 확인 불가
- ⚠️ Failover 발생 시에도 순서는 변하지 않음

**예시:**
```
Input 1 (MAIN): https://...streampackage.../v1/.../input1
Input 2 (BACKUP): https://...streampackage.../v1/.../input2
→ 첫 번째 입력이 MAIN으로 추정 (실제 활성 입력은 보장 안 됨)
```

### 4순위: FailOverSettings 확인

**API:** `DescribeStreamLiveChannel` → `AttachedInputs[].FailOverSettings`

**방법:**
```python
for att in attached_inputs:
    if hasattr(att, 'FailOverSettings'):
        failover = att.FailOverSettings
        secondary_id = getattr(failover, 'SecondaryInputId', '')
        # Primary/Secondary 입력 관계 확인
```

**확인 값:**
- `SecondaryInputId`: 백업 입력 ID
- `FailOverInputId`: Failover 입력 ID

**장점:**
- ✅ Primary/Secondary 입력 관계 확인

**제한사항:**
- ⚠️ 입력 관계만 확인, 현재 활성 입력은 알 수 없음
- ⚠️ Failover 발생 여부는 알 수 없음

**예시:**
```
Input 1:
  FailOverSettings:
    SecondaryInputId: 69425XXX...
→ Input 1이 Primary, Input 2가 Secondary로 설정됨
```

## StreamLive Failover 기능

### Failover 설정 확인

**위치:** `AttachedInputs[].FailOverSettings`

**설정 항목:**
- `SecondaryInputId`: 백업 입력 ID
- `FailOverInputId`: Failover 입력 ID

**동작 방식:**
1. Primary 입력이 실패하면 자동으로 Secondary 입력으로 전환
2. 하지만 **어떤 입력이 현재 활성인지**는 API로 직접 확인 불가

### Failover 상태 확인의 한계

**문제:**
- Failover가 발생했는지 알 수 없음
- 현재 Primary인지 Secondary인지 직접 확인 불가
- 따라서 StreamLink 플로우 상태나 입력 통계로 추론해야 함

## 검증 프로세스 흐름도

```
1. StreamLink 플로우 상태 확인
   ↓ (실행 중인 플로우 발견)
   → 플로우 이름으로 main/backup 구분
   → 최종 판단 ✅

2. StreamLive 입력 통계 확인
   ↓ (NetworkValid=True, NetworkIn > 0)
   → 가장 높은 대역폭 입력 찾기
   → 최종 판단 ✅

3. StreamPackage 입력 순서 확인
   ↓ (첫 번째 입력 = MAIN 추정)
   → 보조 확인용 ⚠️

4. FailOverSettings 확인
   ↓ (Primary/Secondary 관계 확인)
   → 입력 관계만 확인, 활성 입력은 알 수 없음
```

## 실제 검증 예시 (cj_onstyle_2)

### 1단계: StreamLink 플로우 상태
```
플로우: cj_onstyle_m2 (MAIN)
상태: running ✅
→ MAIN 신호 활성화

플로우: cj_onstyle_b2 (BACKUP)
상태: running ✅
→ BACKUP 신호도 실행 중 (대기 상태)
```

### 2단계: StreamLive 입력 통계
```
Input 69425CAF0000BBDE05D7:
  NetworkValid: True/False (확인 필요)
  NetworkIn: XXX bytes
```

### 3단계: StreamPackage 입력 순서
```
Input 1 (MAIN): https://.../input1
Input 2 (BACKUP): https://.../input2
→ 첫 번째 입력이 MAIN으로 추정
```

### 최종 판단
```
활성 입력: MAIN
검증 소스: StreamLink, CSS
신뢰도: 높음 (StreamLink 플로우 상태 기반)
```

## 결론

**Tencent Cloud SDK의 한계:**
- ❌ "어떤 입력이 활성인지" 직접 제공하는 API 없음
- ❌ Failover 발생 여부 직접 확인 불가

**해결 방법:**
- ✅ StreamLink 플로우 상태 확인 (가장 신뢰)
- ✅ StreamLive 입력 통계 확인 (실제 트래픽)
- ✅ StreamPackage 입력 순서 확인 (보조)
- ✅ 다단계 검증으로 정확도 향상

**권장 검증 순서:**
1. StreamLink 플로우 상태 (1순위)
2. StreamLive 입력 통계 (2순위)
3. StreamPackage 입력 순서 (3순위, 보조)
