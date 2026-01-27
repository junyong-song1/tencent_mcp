# StreamLive 통계 API 분석

## 문제 상황

`sbs_no1_news` 채널에서 실제로 방송이 잘 들어오고 있는데, `DescribeStreamLiveChannelInputStatistics` API 호출 시:
- `NetworkValid: False`
- `NetworkIn: 0 bps`

이런 결과가 나오는 이유를 분석합니다.

## API 특성 분석

### DescribeStreamLiveChannelInputStatistics API

**특성:**
1. **시간 범위 기반 통계 API**: 실시간 API가 아닌 과거 시간 범위의 통계를 조회
2. **통계 수집 지연**: 통계 데이터 수집 및 집계에 시간이 소요될 수 있음
3. **시간 범위 필수/선택**: 
   - 시간 범위를 지정하면 해당 기간의 통계 조회
   - 시간 범위 없이 호출하면 기본값 사용 (최근 일정 시간)

**시간 형식:**
- UTC ISO 8601 형식: `YYYY-MM-DDThh:mm:ssZ`
- 예: `2026-01-19T04:24:05Z`

### 실제 테스트 결과

**채널: `sbs_no1_news` (ID: `695E09660000090927DE`)**

#### 1. 시간 범위 없이 호출
```
요청: ChannelId만 지정
응답:
  입력 1: NetworkIn=0, NetworkValid=False
  입력 2: NetworkIn=0, NetworkValid=False
```

#### 2. UTC 시간 범위 지정 (최근 5분)
```
요청: 
  ChannelId: 695E09660000090927DE
  StartTime: 2026-01-19T04:24:05Z
  EndTime: 2026-01-19T04:29:05Z
응답:
  입력 1: NetworkIn=0, NetworkValid=False
  입력 2: NetworkIn=0, NetworkValid=False
```

## 왜 이런 결과가 나올까?

### 가능한 원인

1. **통계 수집 지연**
   - StreamLive는 통계 데이터를 수집하고 집계하는데 시간이 걸림
   - 실시간이 아닌 일정 간격(예: 1분, 5분)으로 집계될 수 있음
   - 방금 시작한 스트림은 아직 통계가 수집되지 않았을 수 있음

2. **API의 목적**
   - 이 API는 **모니터링 및 분석**용
   - 실시간 상태 확인용이 아님
   - 과거 시간 범위의 평균/최대/최소 통계를 제공

3. **통계 데이터 부재**
   - 해당 시간 범위에 통계 데이터가 없을 수 있음
   - `NetworkValid=False`는 "통계 데이터 없음"을 의미할 수도 있음

4. **채널 상태와 통계의 차이**
   - 채널이 `RUNNING` 상태여도 통계는 별도로 수집됨
   - 채널이 실행 중이지만 통계 수집이 아직 안 되었을 수 있음

## 대안: 실시간 상태 확인 방법

### 1. QueryInputStreamState API
- **목적**: 각 입력의 실시간 활성 상태 확인
- **응답**: `Status` (1=활성, 0=비활성)
- **문제**: 파라미터 구조 문제로 현재 사용 불가

### 2. StreamLink 플로우 상태 (현재 사용 중)
- **장점**: 
  - 실시간 상태 확인 가능
  - 플로우 이름으로 main/backup 구분 가능
  - URL 매칭으로 입력 연결 관계 확인 가능
- **현재 구현**: 이 방법을 사용하여 활성 입력 판단

### 3. 채널 상태 확인
- `DescribeStreamLiveChannel`로 채널이 `RUNNING`인지 확인
- 하지만 어떤 입력이 활성인지는 알 수 없음

## 현재 구현 방식

현재 코드는 다음 순서로 활성 입력을 판단합니다:

1. **1순위**: `DescribeStreamLiveChannelInputStatistics` - 통계 기반
   - `NetworkValid=True`이고 `NetworkIn > 0`인 입력 찾기
   - **문제**: 통계 수집 지연으로 실시간 확인 어려움

2. **2순위**: StreamLink 플로우 상태 (실제 사용 중)
   - 실행 중인 StreamLink 플로우 확인
   - 플로우 이름(`_b`, `_m`)으로 main/backup 구분
   - 출력 URL과 StreamLive 입력 엔드포인트 매칭

3. **3순위**: 입력 이름 패턴 분석
   - 입력 이름에서 `backup`, `main` 등 키워드 확인

## 결론

**`DescribeStreamLiveChannelInputStatistics` API는:**
- ✅ 모니터링 및 분석용으로 유용
- ❌ 실시간 상태 확인에는 부적합
- ❌ 통계 수집 지연으로 즉시 반영되지 않음

**실시간 상태 확인에는:**
- ✅ StreamLink 플로우 상태 확인 (현재 사용 중)
- ✅ QueryInputStreamState (파라미터 문제 해결 시 사용 가능)

따라서 현재 구현이 StreamLink 플로우 상태를 우선 사용하는 것이 올바른 접근입니다.

## 개선 제안

1. **QueryInputStreamState API 파라미터 문제 해결**
   - SDK 문서 확인 또는 Tencent Cloud 지원팀 문의
   - 올바른 파라미터 형식 확인

2. **통계 API는 보조적으로만 사용**
   - 실시간 확인이 아닌 과거 통계 분석용으로 사용
   - 시간 범위를 넓게 지정 (예: 최근 1시간)

3. **현재 방식 유지**
   - StreamLink 플로우 상태를 주 방법으로 사용
   - 통계 API는 보조 확인용으로만 활용
