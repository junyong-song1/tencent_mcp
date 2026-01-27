# 활성 소스 감지 분석: 어느 시스템에서 확인하는가?

## 현재 상황

**사용자 질문:**
- 최종 활성 소스가 backup으로 판단되는데, 어느 시스템에서 확인하는가?

**현재 결과:**
- 활성 소스: `backup` (ap-seoul-2)
- 플로우: `sbs_no1_news_b` (BACKUP)
- 엔드포인트: `rtmp://...ap-seoul-2.../ec2ad91d660148a9b59cf97b769dc33b`

## 현재 코드의 검증 방식

### 【검증 1단계】 StreamLink 플로우 상태 확인

**확인 시스템:** StreamLink (Tencent Cloud StreamLink)

**확인 내용:**
- 플로우 이름: `sbs_no1_news_m` (MAIN), `sbs_no1_news_b` (BACKUP)
- 플로우 상태: 둘 다 `running`
- 플로우 타입 판단:
  - `_m` 포함 → MAIN
  - `_b` 포함 → BACKUP

**문제점:**
- 두 플로우가 모두 `running` = 둘 다 실행 중
- 하지만 실제로 StreamLive가 어떤 소스를 사용하는지는 알 수 없음
- StreamLink는 플로우 상태만 제공, 실제 활성 소스는 알 수 없음

### 【검증 2단계】 Input Source Redundancy 확인

**확인 시스템:** StreamLink 출력 URL + StreamLive 입력 엔드포인트 매칭

**확인 내용:**
- 플로우 출력 URL과 입력 엔드포인트 매칭
- `ap-seoul-1` → main 소스 주소
- `ap-seoul-2` → backup 소스 주소

**문제점:**
- URL 매칭만으로는 실제 활성 소스를 알 수 없음
- 두 소스 주소가 모두 매칭되면 둘 다 연결되어 있다는 의미일 뿐

### 【검증 3단계】 CSS 검증

**확인 시스템:** StreamPackage + CSS (Cloud Streaming Service)

**확인 내용:**
- StreamPackage 연결 확인
- 스트림 흐름 확인

**문제점:**
- 스트림이 흐르고 있다는 것만 확인
- 어떤 소스가 활성인지는 알 수 없음

## 현재 코드의 문제점

### 문제 1: 플로우 순회 순서에 따른 결과 차이

**코드 로직:**
```python
for flow in linked_flows:
    if flow.get("status") == "running":
        # 매칭 로직
        if matched_source:
            flow_type_by_input[inp_id] = matched_source  # 덮어씀
```

**문제:**
- main 플로우와 backup 플로우가 모두 running
- 둘 다 같은 입력에 매칭됨
- 나중에 처리된 플로우의 값으로 덮어씀
- 따라서 순서에 따라 결과가 달라질 수 있음

**현재 결과:**
- backup 플로우가 나중에 처리되어 backup으로 판단됨
- 하지만 실제로는 StreamLive가 어떤 소스를 사용하는지 알 수 없음

### 문제 2: 실제 활성 소스를 확인할 수 없음

**현재 확인 방법:**
- StreamLink 플로우 상태만 확인
- 두 플로우가 모두 running = 둘 다 실행 중
- 하지만 실제로 StreamLive가 어떤 소스를 사용하는지는 알 수 없음

**실제 확인이 필요한 것:**
- StreamLive가 실제로 어떤 소스 주소에서 데이터를 받고 있는지
- 각 소스 주소의 실제 데이터 수신량
- StreamLive의 내부 상태 (어떤 소스가 활성인지)

## 실제 활성 소스를 확인하는 방법

### 방법 1: StreamLive 입력 통계 API

**API:** `DescribeStreamLiveChannelInputStatistics`

**확인 내용:**
- 각 입력의 `NetworkIn` 값 (실제 데이터 수신량)
- 더 많은 데이터를 받는 소스가 활성

**현재 상태:**
- `NetworkValid=False`, `NetworkIn=0`
- 통계 데이터로 활성 소스 확인 불가

**이유:**
- 통계 수집 지연
- 실시간 상태 확인에는 부적합

### 방법 2: StreamLink 플로우 통계

**확인 내용:**
- 각 플로우의 실제 데이터 전송량
- 더 많은 데이터를 전송하는 플로우가 활성

**현재 상태:**
- StreamLink API에서 플로우 통계 제공 여부 확인 필요

### 방법 3: StreamLive API에서 현재 활성 소스 확인

**API:** `QueryInputStreamState` (현재 파라미터 문제로 사용 불가)

**확인 내용:**
- StreamLive가 현재 사용 중인 소스 주소
- 직접적인 활성 소스 확인

**현재 상태:**
- API 파라미터 문제로 사용 불가

## 결론

### 현재 검증 방식

**확인 시스템:**
1. **StreamLink** (플로우 상태 확인)
2. **StreamLink 출력 URL + StreamLive 입력 엔드포인트 매칭** (소스 주소 확인)
3. **CSS** (스트림 흐름 확인)

**문제점:**
- StreamLink 플로우 상태만으로는 실제 활성 소스를 알 수 없음
- 두 플로우가 모두 running이면 둘 다 실행 중
- 실제로 StreamLive가 어떤 소스를 사용하는지는 확인 불가

### 실제 활성 소스를 확인하려면

**필요한 것:**
1. StreamLive 입력 통계 API로 실제 데이터 수신량 확인
2. StreamLink 플로우 통계로 실제 데이터 전송량 확인
3. StreamLive API에서 현재 활성 소스 주소 확인

**현재 한계:**
- 통계 API는 데이터 지연으로 실시간 확인 불가
- QueryInputStreamState는 파라미터 문제로 사용 불가
- 따라서 StreamLink 플로우 상태를 기반으로 추론하는 방식 사용

### 현재 결과의 의미

**"활성 소스: backup"의 의미:**
- StreamLink backup 플로우가 실행 중
- backup 소스 주소(ap-seoul-2)와 매칭됨
- 하지만 실제로 StreamLive가 이 소스를 사용하는지는 확인 불가
- **추론 기반 결과** (실제 확인 아님)

**개선 필요:**
- StreamLive 입력 통계를 활용한 실제 활성 소스 확인 로직 추가
- 또는 StreamLive API에서 직접 활성 소스 확인 가능한 방법 찾기
