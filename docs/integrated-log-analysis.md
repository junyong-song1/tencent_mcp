# 통합 로그 분석 가이드

이 문서는 StreamLive, StreamLink, StreamPackage, CSS의 로그를 통합하여 보고 분석하는 방법을 설명합니다.

## 개요

통합 로그 분석 기능을 통해 다음을 수행할 수 있습니다:

1. **통합 로그 조회**: 모든 서비스의 로그를 한 번에 조회
2. **로그 분석**: 패턴 분석, 통계, 인사이트 제공
3. **이벤트 필터링**: 서비스별, 이벤트 타입별 필터링
4. **시간대별 분석**: 특정 시간대의 로그 분석

## 지원하는 로그

### StreamLive

**확인 가능한 로그:**
- PipelineFailover - 파이프라인 failover 발생
- PipelineRecover - 파이프라인 복구
- No Input Data - 입력 데이터 없음
- StreamStart - 스트림 시작
- StreamStop - 스트림 중단
- 기타 채널 상태 관련 이벤트

**API**: `DescribeStreamLiveChannelLogs`

### StreamLink

**확인 가능한 정보:**
- 현재 상태 (State)
- 상태 변화 이벤트

**제한사항**: StreamLink는 직접적인 로그 API가 제한적이므로 현재 상태만 확인 가능

### StreamPackage

**확인 가능한 정보:**
- 현재 상태 (State)
- 입력 상태 (main/backup)
- 입력 상태 변화 이벤트

**제한사항**: StreamPackage는 직접적인 로그 API가 제한적이므로 현재 상태만 확인 가능

### CSS

**확인 가능한 정보:**
- 스트림 상태 (active/inactive)
- 푸시 정보
- 스트림 상태 변화 이벤트

**제한사항**: CSS는 제한적인 로그 API만 제공

## 사용 방법

### MCP Server (AI)

#### 1. 통합 로그 조회

```
"channel-123의 최근 24시간 로그를 모두 보여줘"
"channel-123의 StreamLive와 StreamLink 로그를 보여줘"
"channel-123에서 PipelineFailover 이벤트만 필터링해서 보여줘"
```

#### 2. 로그 분석

```
"channel-123의 로그를 분석해서 문제점을 찾아줘"
"channel-123에서 failover 패턴을 분석해줘"
"channel-123의 최근 오류 이벤트를 분석해줘"
```

### REST API

```bash
# 통합 로그 조회
GET /api/v1/resources?uri=tencent://logs/integrated?channel_id=channel-123&hours=24
```

### MCP Tools

#### `get_channel_logs`

StreamLive 채널의 로그만 조회:

```json
{
  "name": "get_channel_logs",
  "arguments": {
    "channel_id": "channel-123",
    "hours": 24,
    "event_types": ["PipelineFailover", "PipelineRecover"]
  }
}
```

#### `get_integrated_logs`

모든 서비스의 로그를 통합 조회:

```json
{
  "name": "get_integrated_logs",
  "arguments": {
    "channel_id": "channel-123",
    "hours": 24,
    "services": ["StreamLive", "StreamLink", "StreamPackage", "CSS"],
    "event_types": ["PipelineFailover"]
  }
}
```

#### `analyze_logs`

로그를 분석하여 인사이트 제공:

```json
{
  "name": "analyze_logs",
  "arguments": {
    "channel_id": "channel-123",
    "hours": 24
  }
}
```

## 응답 형식

### 통합 로그 응답

```json
{
  "channel_id": "channel-123",
  "start_time": "2024-01-26T19:00:00Z",
  "end_time": "2024-01-27T19:00:00Z",
  "total_logs": 45,
  "service_counts": {
    "StreamLive": 30,
    "StreamLink": 5,
    "StreamPackage": 5,
    "CSS": 5
  },
  "event_counts": {
    "PipelineFailover": 2,
    "PipelineRecover": 1,
    "StreamStart": 3,
    "StateChange": 10
  },
  "logs": [
    {
      "service": "StreamLive",
      "resource_id": "channel-123",
      "pipeline": "Pipeline A (Main)",
      "event_type": "PipelineFailover",
      "time": "2024-01-27T19:15:23Z",
      "message": "Pipeline failover occurred",
      "timestamp": "2024-01-27T19:15:23Z"
    },
    ...
  ],
  "streamlive_logs": [...],
  "streamlink_logs": [...],
  "streampackage_logs": [...],
  "css_logs": [...]
}
```

### 로그 분석 응답

```json
{
  "success": true,
  "channel_id": "channel-123",
  "analysis_period_hours": 24,
  "total_events": 45,
  "service_distribution": {
    "StreamLive": 30,
    "StreamLink": 5,
    "StreamPackage": 5,
    "CSS": 5
  },
  "event_distribution": {
    "PipelineFailover": 2,
    "PipelineRecover": 1,
    "StreamStart": 3
  },
  "insights": [
    {
      "type": "failover_analysis",
      "failover_count": 2,
      "recover_count": 1,
      "last_failover": {...},
      "last_recover": {...}
    },
    {
      "type": "error_analysis",
      "error_count": 0,
      "recent_errors": []
    }
  ],
  "recommendations": [
    "⚠️ 높은 failover 발생률: 2회 발생. 입력 소스 상태를 확인하세요."
  ],
  "service_health": {
    "StreamLive": "active",
    "StreamLink": "active",
    "StreamPackage": "active",
    "CSS": "active"
  },
  "recent_events": [...]
}
```

## 실제 사용 예시

### 예시 1: 통합 로그 조회

```
사용자: "channel-123의 최근 24시간 동안 모든 서비스 로그를 보여줘"

→ get_integrated_logs() 호출
→ StreamLive, StreamLink, StreamPackage, CSS 로그 모두 수집
→ 시간순으로 정렬
→ 자연어 리포트:
   "channel-123의 통합 로그 (최근 24시간):
   
   총 45개 이벤트:
   - StreamLive: 30개
   - StreamLink: 5개
   - StreamPackage: 5개
   - CSS: 5개
   
   주요 이벤트:
   - PipelineFailover: 2회
   - PipelineRecover: 1회
   - StreamStart: 3회
   
   최근 이벤트:
   19:15:23 - StreamLive: PipelineFailover (Pipeline A)
   19:10:00 - StreamLink: StateChange (running)
   ..."
```

### 예시 2: 로그 분석

```
사용자: "channel-123의 로그를 분석해서 문제점을 찾아줘"

→ analyze_logs() 호출
→ 로그 패턴 분석
→ 자연어 리포트:
   "channel-123 로그 분석 결과 (최근 24시간):
   
   📊 통계:
   - 총 이벤트: 45개
   - Failover 발생: 2회
   - 복구 완료: 1회
   
   ⚠️ 주의사항:
   - 높은 failover 발생률 (2회)
   - 마지막 failover: 2024-01-27 19:15:23
   - 입력 소스 상태를 확인하세요
   
   ✅ 정상:
   - 모든 서비스 활성화됨
   - 최근 오류 없음
   
   💡 권장사항:
   1. 입력 소스 장비 상태 확인
   2. 네트워크 연결 상태 확인
   3. StreamLink 플로우 상태 모니터링"
```

### 예시 3: 특정 이벤트 필터링

```
사용자: "channel-123에서 PipelineFailover 이벤트만 보여줘"

→ get_integrated_logs(event_types=["PipelineFailover"]) 호출
→ PipelineFailover 이벤트만 필터링
→ 자연어 리포트:
   "channel-123의 PipelineFailover 이벤트 (최근 24시간):
   
   총 2건:
   1. 2024-01-27 19:15:23 - Pipeline A (Main)
      메시지: Pipeline failover occurred
   
   2. 2024-01-27 18:30:00 - Pipeline A (Main)
      메시지: Pipeline failover occurred"
```

## 필터링 옵션

### 서비스별 필터링

```python
# StreamLive와 StreamLink만
services=["StreamLive", "StreamLink"]

# StreamPackage와 CSS만
services=["StreamPackage", "CSS"]
```

### 이벤트 타입별 필터링

```python
# Failover 관련만
event_types=["PipelineFailover", "PipelineRecover"]

# 오류 관련만
event_types=["No Input Data", "Error"]
```

### 시간 범위 지정

```python
# 최근 12시간
hours=12

# 최근 7일
hours=168

# 특정 시간대
start_time="2024-01-27T00:00:00Z"
end_time="2024-01-27T23:59:59Z"
```

## 분석 기능

### 1. Failover 패턴 분석

- Failover 발생 횟수
- 복구 시간 분석
- Failover 간격 분석
- 패턴 감지

### 2. 오류 분석

- 오류 이벤트 수집
- 오류 유형 분류
- 오류 발생 시간대 분석
- 추세 분석

### 3. 서비스 건강도

- 각 서비스의 이벤트 수
- 서비스 간 상관관계
- 문제 서비스 식별

### 4. 시간대별 분석

- 특정 시간대의 이벤트 집중도
- 피크 시간대 식별
- 패턴 발견

## 제한사항

### API 제한

1. **StreamLink**: 직접적인 로그 API가 제한적
   - 현재 상태만 확인 가능
   - 상태 변화 이벤트만 기록

2. **StreamPackage**: 직접적인 로그 API가 제한적
   - 현재 상태만 확인 가능
   - 입력 상태 변화만 기록

3. **CSS**: 제한적인 로그 API
   - 스트림 상태만 확인 가능
   - 푸시 정보는 일부만 제공

4. **StreamLive**: 가장 상세한 로그 제공
   - 파이프라인별 로그
   - 다양한 이벤트 타입
   - 시간대별 필터링 가능

### 성능 고려사항

- 통합 로그 조회는 여러 API를 호출하므로 시간이 걸릴 수 있음
- CSS 스트림이 많으면 조회 시간 증가
- 시간 범위가 넓으면 로그 수가 많아질 수 있음

## 권장 사용법

### 일상 모니터링

```
"channel-123의 최근 1시간 로그 확인"
→ 빠른 상태 확인
```

### 문제 분석

```
"channel-123의 최근 24시간 로그 분석"
→ 상세 분석 및 문제점 파악
```

### 장기 트렌드 분석

```
"channel-123의 최근 7일 로그 분석"
→ 장기 패턴 및 트렌드 파악
```

## 다음 단계

1. **로그 저장**: 로그를 데이터베이스에 저장하여 장기 분석
2. **알림 연동**: 특정 패턴 감지 시 자동 알림
3. **대시보드**: 로그를 시각화하여 대시보드 제공
4. **예측 분석**: 머신러닝을 통한 문제 예측
