# 상세 알림 가이드

이 문서는 이미지에서 보여준 것과 같은 상세한 알림 형태를 만드는 방법을 설명합니다.

## 개요

상세 알림 시스템은 모니터링 시스템처럼 풍부한 정보를 포함한 알림을 제공합니다:

- **앱 이름 및 아이콘**: 알림을 보내는 애플리케이션 식별
- **알림 제목**: 이모지와 함께 주요 알림 내용
- **이벤트 시간**: 정확한 발생 시각
- **상세 메트릭 정보**: Key-Value 형태의 상세 정보
- **액션 버튼**: 로그 분석, 상태 확인 등의 빠른 액션
- **심각도 표시**: Critical, High, Medium, Low

## 기능

### 자동 상세 알림

Alert Monitor가 자동으로 감지한 알림은 상세 형식으로 표시됩니다:

```
PipelineFailover 발생
→ 자동으로 상세 알림 생성
→ 채널 정보, 입력 상태, StreamPackage, CSS 정보 모두 포함
→ 액션 버튼 제공
```

### 포함되는 정보

1. **기본 정보**
   - Alert Type
   - Severity
   - Channel ID/Name
   - Pipeline

2. **채널 상세 정보**
   - Channel Status
   - Service Type

3. **입력 상태 정보**
   - Active Input (main/backup)
   - Active Input ID
   - Verification Sources

4. **StreamPackage 정보**
   - StreamPackage ID
   - Active Input

5. **CSS 정보**
   - Stream Flowing Status
   - StreamPackage Connection Status

## 사용 예시

### 예시 1: PipelineFailover 알림

```
🚨🚨🚨 [firing] PipelineFailover

Event Time: start: 2024-01-27 19:15:23

Metric Info:
alert_type: PipelineFailover
severity: high
channel_id: channel-kbo-001
channel_name: KBO 경기 채널
pipeline: Pipeline A (Main)
set_time: 2024-01-27T19:15:23Z
channel_status: running
service: StreamLive
active_input: backup
active_input_id: input-backup-001
verification_sources: ChannelLogs, QueryInputStreamState
streampackage_id: sp-channel-001
streampackage_active_input: backup
css_stream_flowing: true
css_streampackage_connected: true

[상태 확인] [채널 상세]
```

### 예시 2: No Input Data 알림

```
🚨🚨🚨 [firing] No Input Data

Event Time: start: 2024-01-27 20:30:15

Metric Info:
alert_type: No Input Data
severity: critical
channel_id: channel-news-001
channel_name: 뉴스 채널
pipeline: Pipeline A (Main)
set_time: 2024-01-27T20:30:15Z
channel_status: running
service: StreamLive
active_input: unknown
verification_sources: QueryInputStreamState

[상태 확인] [채널 상세]
```

## 커스터마이징

### 액션 버튼 추가

`detailed_alert.py`의 `create_channel_alert_blocks()` 함수에서 액션 버튼을 수정할 수 있습니다:

```python
action_buttons = [
    {
        "label": "로그 분석",
        "url": "https://your-log-system.com/channel/{channel_id}",
        "style": "primary"
    },
    {
        "label": "상태 확인",
        "url": "https://your-dashboard.com/channel/{channel_id}",
        "style": "default"
    },
    {
        "label": "Datadog 링크",
        "url": "https://app.datadoghq.com/...",
        "style": "default"
    }
]
```

### 추가 정보 포함

`alert_monitor.py`의 `_send_alert_notification()` 메서드에서 추가 정보를 가져올 수 있습니다:

```python
# AWS 정보 추가
metric_info["aws_region"] = "ap-northeast-2"
metric_info["aws_ecs_task_family"] = "prod-ecs-task-gaia-api"

# 호스트 정보 추가
metric_info["host_name"] = "ip-10-11-22-72"
metric_info["os_type"] = "linux"
```

## 설정

### 상세 알림 활성화/비활성화

기본적으로 상세 알림이 활성화되어 있습니다. 비활성화하려면:

```python
# alert_monitor.py에서
self._send_alert_notification(
    channel_id=channel_id,
    channel_name=channel_name,
    alert=alert,
    use_detailed_format=False,  # 간단한 형식 사용
)
```

### 알림 채널 설정

`.env` 파일에서 알림 채널을 설정:

```bash
NOTIFICATION_CHANNEL=C1234567890  # Slack 채널 ID
```

## 실제 사용

### 자동 알림

Alert Monitor가 주기적으로 채널을 확인하고 알림을 보냅니다:

```python
# 5분마다 자동 확인 (기본값)
alert_monitor.register_jobs(check_interval_minutes=5)
```

### 수동 알림 테스트

```python
from app.services.alert_monitor import get_alert_monitor

alert_monitor = get_alert_monitor()
alert_monitor.check_now()  # 즉시 확인
```

## Slack에서 확인

알림이 오면 다음과 같이 표시됩니다:

1. **앱 이름**: "Tencent Cloud MCP" (아이콘 포함)
2. **알림 제목**: 이모지와 함께 "[firing] AlertType"
3. **이벤트 시간**: 정확한 발생 시각
4. **상세 정보**: Key-Value 형태로 모든 정보 표시
5. **액션 버튼**: 클릭 가능한 버튼들
6. **Footer**: 타임스탬프

## 다음 단계

1. **로그 시스템 연동**: 로그 분석 버튼에 실제 로그 시스템 URL 연결
2. **대시보드 연동**: 상태 확인 버튼에 대시보드 URL 연결
3. **추가 메트릭**: 필요한 추가 정보를 metric_info에 포함
4. **알림 그룹화**: 관련 알림들을 그룹화하여 표시
