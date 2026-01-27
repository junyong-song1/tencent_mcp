# 알림 수집 가이드

이 문서는 Tencent Cloud StreamLive에서 알림을 수집하는 방법과 제한사항을 설명합니다.

## 현재 알림 수집 방법

### 1. API 폴링 (주기적 확인)

**방법**: `DescribeStreamLiveChannelAlerts` API를 주기적으로 호출

**현재 설정**:
- 주기: 5분마다 (기본값)
- 확인 대상: 모든 running 상태의 채널
- 알림 타입: PipelineFailover, PipelineRecover, No Input Data 등

**장점**:
- 다양한 알림 타입 수집 가능
- API로 제공되는 모든 알림 확인 가능

**단점**:
- 실시간성이 떨어짐 (최대 5분 지연)
- API 호출 비용 발생

### 2. Webhook 콜백 (실시간)

**방법**: StreamLive에서 직접 콜백 호출

**제한사항**:
- **RTMP Push 이벤트만 지원**
  - 329: Stream push 시작
  - 330: Stream push 중단
- 다른 알림 타입은 Webhook 미지원

**장점**:
- 실시간 알림
- 서버 부하 감소

**단점**:
- 알림 타입이 매우 제한적 (2개만)

## Tencent Cloud에서 제공하는 알림 타입

### API로 확인 가능한 알림 (`DescribeStreamLiveChannelAlerts`)

1. **PipelineFailover** - 파이프라인 failover 발생
2. **PipelineRecover** - 파이프라인 복구
3. **No Input Data** - 입력 데이터 없음
4. **StreamStart** - 스트림 시작
5. **StreamStop** - 스트림 중단
6. 기타 채널 상태 관련 알림

### Webhook으로만 제공되는 이벤트

1. **Stream Push Start (329)** - RTMP push 시작
2. **Stream Push Stop (330)** - RTMP push 중단

## 더 많은 알림을 받는 방법

### 방법 1: 폴링 주기 단축

현재 5분 → 1-2분으로 단축:

```python
# app/main.py에서
_alert_monitor = init_alert_monitor(
    ...,
    check_interval_minutes=1,  # 1분마다 확인
)
```

**장점**: 더 빠른 알림 수신
**단점**: API 호출 증가, 비용 증가

### 방법 2: 채널 로그 모니터링

채널 로그를 주기적으로 확인하여 추가 이벤트 감지:

```python
# DescribeStreamLiveChannelLogs API 사용
# PipelineFailover, PipelineRecover 등 로그 이벤트 확인
```

**현재 구현**: `_get_active_pipeline_from_logs()` 메서드로 로그 확인 중

### 방법 3: 상태 변화 감지

채널 상태를 주기적으로 확인하여 변화 감지:

```python
# 이전 상태와 비교
# running → stopped: 알림
# idle → error: 알림
# main → backup: 알림
```

### 방법 4: 입력 상태 모니터링

입력 상태를 주기적으로 확인:

```python
# QueryInputStreamState API 사용
# main → backup 전환 감지
# 신호 끊김 감지
```

### 방법 5: StreamPackage/CSS 상태 모니터링

StreamPackage와 CSS 상태도 함께 모니터링:

```python
# StreamPackage 입력 상태 변화
# CSS 스트림 활성/비활성 변화
```

## 개선된 알림 시스템 구현

다음과 같은 개선을 추가할 수 있습니다:

### 1. 상태 변화 감지 모니터 추가

```python
class StateChangeMonitor:
    """Monitor state changes and send alerts."""
    
    def check_state_changes(self):
        """Check for state changes in channels."""
        # 이전 상태와 비교
        # 변화가 있으면 알림
```

### 2. 입력 상태 모니터 추가

```python
class InputStatusMonitor:
    """Monitor input status changes."""
    
    def check_input_changes(self):
        """Check for input status changes."""
        # main → backup 전환 감지
        # 신호 끊김 감지
```

### 3. 통합 모니터링

모든 모니터를 통합하여 종합적인 알림 제공:

```python
class ComprehensiveMonitor:
    """Comprehensive monitoring combining all methods."""
    
    def check_all(self):
        """Check alerts, state changes, input status, etc."""
        # 1. API 알림 확인
        # 2. 상태 변화 확인
        # 3. 입력 상태 확인
        # 4. StreamPackage/CSS 확인
```

## 권장 설정

### 실시간성이 중요한 경우

```python
# 1분마다 확인
check_interval_minutes=1

# 상태 변화도 감지
enable_state_change_detection=True

# 입력 상태도 모니터링
enable_input_status_monitoring=True
```

### 비용 최적화가 중요한 경우

```python
# 5분마다 확인 (기본값)
check_interval_minutes=5

# Webhook 활용 (가능한 경우)
enable_webhook=True
```

## 실제 사용 예시

### 현재 작동 방식

```
1. Alert Monitor가 5분마다 실행
2. 모든 running 채널의 DescribeStreamLiveChannelAlerts 호출
3. 새로운 알림 발견 시 Slack 알림 전송
4. Webhook 이벤트 수신 시 즉시 알림
```

### 개선된 작동 방식 (제안)

```
1. Alert Monitor가 1-2분마다 실행
2. API 알림 확인
3. 상태 변화 감지 (이전 상태와 비교)
4. 입력 상태 확인 (main/backup 전환)
5. StreamPackage/CSS 상태 확인
6. 모든 변화를 통합하여 상세 알림 전송
```

## Webhook 설정

Webhook을 사용하려면:

1. **StreamLive 콘솔에서 설정**:
   - 채널 설정 → 콜백 URL 설정
   - URL: `https://your-server.com/api/v1/webhooks/streamlive`

2. **서버에서 수신**:
   ```python
   # app/api/routes/webhooks.py
   @router.post("/webhooks/streamlive")
   async def streamlive_webhook(payload: dict):
       alert_monitor.process_webhook_event(payload)
   ```

3. **서명 검증** (선택):
   ```python
   # Webhook key 설정
   alert_monitor.set_webhook_key("your-webhook-key")
   ```

## 제한사항 및 해결책

### 제한사항

1. **Webhook 콜백이 제한적**: RTMP push 이벤트만 (2개)
2. **API 폴링 지연**: 최대 5분 지연 가능
3. **API 호출 비용**: 빈번한 호출 시 비용 증가

### 해결책

1. **폴링 주기 조정**: 필요에 따라 1-5분 사이 조정
2. **상태 변화 감지**: API 알림 외에 상태 변화도 감지
3. **로그 모니터링**: 채널 로그를 통한 추가 이벤트 감지
4. **통합 모니터링**: 여러 소스의 정보를 통합

## 다음 단계

1. **폴링 주기 조정**: `.env`에서 `ALERT_CHECK_INTERVAL_MINUTES` 설정
2. **상태 변화 감지 추가**: StateChangeMonitor 구현
3. **입력 상태 모니터링 추가**: InputStatusMonitor 구현
4. **Webhook 설정**: 가능한 경우 Webhook 활용
