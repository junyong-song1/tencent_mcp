# 입력 상태 확인 전략 - 다단계 검증

## 연결 구조

```
StreamLink (main/backup 플로우)
    ↓
StreamLive 입력 (main/backup)
    ↓
StreamLive 출력 → StreamPackage 입력
    ↓
StreamPackage 출력 → CSS origin
    ↓
CSS CDN → 사용자 재생
```

## 현재 확인 방법

### 1. StreamLink 플로우 상태 (현재 사용 중) ✅
- **장점**: 실시간 상태 확인 가능
- **확인 내용**: 
  - `sbs_no1_news_m` (main) - `running` 또는 `idle`
  - `sbs_no1_news_b` (backup) - `running` 또는 `idle`
- **판단**: 실행 중인 플로우의 이름(`_m`, `_b`)으로 main/backup 구분

### 2. StreamLive 입력 통계 ⚠️
- **문제**: 통계 수집 지연으로 실시간 확인 어려움
- **현재 결과**: `NetworkValid=False, NetworkIn=0` (데이터 없음)

### 3. StreamPackage 입력 상태 (추가 가능) ⭐
- **위치**: StreamLive 출력 → StreamPackage 입력
- **확인 가능**: StreamPackage가 실제로 어떤 입력을 사용 중인지
- **필요**: StreamPackage SDK 추가 필요

### 4. CSS 스트림 상태 (최종 확인) ⭐
- **위치**: 최종 사용자에게 전달되는 스트림
- **확인 가능**: 실제 재생 중인 스트림의 origin (main/backup)
- **필요**: CSS API 추가 필요

## 권장 검증 전략

### 단계별 검증 (우선순위 순)

#### 1단계: StreamLink 플로우 상태 (현재 구현) ✅
```python
# 가장 빠르고 확실한 방법
- StreamLink 플로우 상태 확인
- 플로우 이름으로 main/backup 구분
- URL 매칭으로 StreamLive 입력 연결 확인
```

#### 2단계: StreamPackage 입력 상태 (추가 권장) ⭐
```python
# StreamLive 출력이 StreamPackage로 잘 들어가는지 확인
- StreamPackage 채널 입력 상태 확인
- StreamPackage의 입력 중복(redundancy) 설정 확인
- 실제 활성화된 입력 확인
```

#### 3단계: CSS 스트림 상태 (최종 확인) ⭐
```python
# 최종 사용자에게 전달되는 스트림 확인
- CSS 스트림 상태 확인
- 실제 재생 중인 스트림의 origin 확인
- 최종적으로 어떤 경로가 활성화되어 있는지 확인
```

## StreamPackage 확인 방법

### StreamPackage SDK 필요
```bash
# StreamPackage SDK 설치 필요
pip install tencentcloud-sdk-python-msp
```

### 확인 가능한 정보
1. **StreamPackage 채널 입력 상태**
   - 입력 1 (main) 상태
   - 입력 2 (backup) 상태
   - 현재 활성화된 입력

2. **StreamPackage 입력 중복 설정**
   - Primary 입력
   - Secondary 입력
   - Failover 설정

3. **실제 트래픽 확인**
   - 입력별 대역폭
   - 입력별 상태

## CSS 확인 방법

### CSS API 필요
```python
from tencentcloud.live.v20180801 import live_client, models as live_models
```

### 확인 가능한 정보
1. **CSS 스트림 상태**
   - 스트림이 활성화되어 있는지
   - 재생 중인지

2. **CSS origin 확인**
   - StreamPackage origin 사용 여부
   - 실제 origin 서버

3. **최종 스트림 경로**
   - 사용자에게 전달되는 스트림
   - 어떤 입력 경로에서 나온 것인지

## 구현 제안

### 현재 구현 (1단계만)
```python
# StreamLink 플로우 상태로 판단
active_input = determine_from_streamlink_flows()
```

### 개선된 구현 (다단계 검증)
```python
# 1단계: StreamLink 플로우 상태
result_from_streamlink = check_streamlink_flows()

# 2단계: StreamPackage 입력 상태 (확인 가능한 경우)
if streampackage_id:
    result_from_streampackage = check_streampackage_inputs(streampackage_id)
    # StreamPackage 결과와 일치하는지 확인

# 3단계: CSS 스트림 상태 (확인 가능한 경우)
if css_stream_id:
    result_from_css = check_css_stream(css_stream_id)
    # CSS 결과와 일치하는지 확인

# 최종 판단: 여러 단계 결과를 종합
final_result = combine_results(
    result_from_streamlink,
    result_from_streampackage,
    result_from_css
)
```

## 결론

### 현재 방식의 한계
- StreamLink 플로우 상태만으로는 간접 확인
- StreamLive 입력 통계는 지연 문제로 실시간 확인 어려움

### 개선 방향
1. **StreamPackage 입력 상태 확인 추가** (가장 중요)
   - StreamLive 출력이 StreamPackage로 잘 들어가는지 확인
   - StreamPackage의 입력 중복 설정으로 main/backup 확인
   - 더 확실한 판단 가능

2. **CSS 스트림 상태 확인 추가** (최종 확인)
   - 실제 사용자에게 전달되는 스트림 확인
   - 최종 경로 검증

3. **다단계 검증 로직**
   - 여러 단계에서 일치하는 결과를 우선
   - 불일치 시 경고 표시

## 다음 단계

1. StreamPackage SDK 추가 및 입력 상태 확인 기능 구현
2. CSS API 추가 및 스트림 상태 확인 기능 구현
3. 다단계 검증 로직 구현
