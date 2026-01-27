# 방송 채널 선택 프로세스

## 개요

스케줄 등록 모달에서 방송 채널을 선택하는 프로세스와 데이터 흐름을 설명합니다.

**중요**: 현재 구현은 **로컬 스케줄 관리만** 수행하며, Tencent Cloud StreamLive 예약 스케줄 등록 API는 호출하지 않습니다.

## 프로세스 흐름

### 1. 스케줄 등록 모달 열기

**트리거**: 사용자가 "스케줄 등록" 버튼 클릭

**핸들러**: `handle_schedule_add_button()` (app_v2.py:661)

**동작**:
```python
# 1. Tencent Cloud에서 모든 리소스 가져오기
channels = tencent_client.list_all_resources()

# 2. 스케줄 등록 모달 생성
add_modal = slack_ui.create_schedule_add_modal(
    channels=channels,
    parent_metadata=parent_metadata,
    selected_date=selected_date
)

# 3. 모달 열기
client.views_push(trigger_id=body["trigger_id"], view=add_modal)
```

### 2. 채널 드롭다운 생성

**위치**: `slack_ui.py:create_schedule_add_modal()` (1184-1260)

**동작**:
```python
# 모든 리소스(StreamLive + StreamLink)를 드롭다운 옵션으로 변환
channel_options = []
for ch in channels[:100]:  # Slack limit
    service_emoji = SlackUI.get_service_emoji(ch.get("service", ""))
    channel_options.append({
        "text": {
            "type": "plain_text",
            "text": f"{service_emoji} {ch.get('name', 'Unknown')[:70]}"
        },
        "value": f"{ch.get('service', 'Unknown')}:{ch.get('id', '')}"
    })
```

**옵션 형식**:
- **표시 텍스트**: `📡 jtbc_news_archive` (서비스 이모지 + 채널 이름)
- **값**: `StreamLive:694A308C79D37854B930` (서비스:ID 형식)

### 3. 채널 선택

**트리거**: 사용자가 드롭다운에서 채널 선택

**핸들러**: `handle_schedule_channel_select()` (app_v2.py:941)

**현재 동작**:
```python
@app.action("schedule_channel_select")
def handle_schedule_channel_select(ack, body, client, logger):
    """Handle channel select in schedule form."""
    ack()  # 현재는 ack()만 하고 추가 동작 없음
```

**참고**: 현재는 채널 선택 시 추가 검증이나 동작이 없습니다. 필요시 여기에 추가 로직을 구현할 수 있습니다.

### 4. 스케줄 제출

**트리거**: 사용자가 "등록" 버튼 클릭

**핸들러**: `handle_schedule_add_submit()` (app_v2.py:765)

**프로세스**:

#### 4.1 채널 값 파싱
```python
channel_value = values["schedule_channel_block"]["schedule_channel_select"]["selected_option"]["value"]
# 예: "StreamLive:694A308C79D37854B930"

# 서비스와 ID 분리
if ":" in channel_value:
    service, channel_id = channel_value.split(":", 1)
else:
    service = "Unknown"
    channel_id = channel_value
```

#### 4.2 채널 이름 조회
```python
# 리소스 목록에서 채널 이름 찾기
channel_name = channel_id  # 기본값
try:
    all_resources = tencent_client.list_all_resources()
    for res in all_resources:
        if res.get("id") == channel_id:
            channel_name = res.get("name", channel_id)
            break
except Exception:
    pass
```

#### 4.3 스케줄 저장 (로컬만)
```python
# broadcast_schedule.py의 add_schedule() 호출
result = schedule_manager.add_schedule(
    channel_id=channel_id,        # Tencent Cloud 채널 ID
    channel_name=channel_name,     # 표시용 이름
    service=service,               # StreamLive 또는 StreamLink
    title=title,                   # 방송 제목
    start_time=start_datetime,    # 시작 시간
    end_time=end_datetime,        # 종료 시간
    assignee_id=assignee_id,       # 담당자 Slack ID
    assignee_name=assignee_name,   # 담당자 이름
    auto_start=auto_start,        # 자동 시작 여부
    auto_stop=auto_stop,          # 자동 종료 여부
    notify_2h=notify_2h,          # 2시간 전 알림
    notify_30m=notify_30m,        # 30분 전 알림
    created_by=created_by,        # 생성자
    notes=notes                   # 메모
)
```

**저장 위치**: `broadcast_schedules.json` (로컬 파일)

**중요**: 
- ❌ Tencent Cloud StreamLive 예약 스케줄 API는 **호출하지 않음**
- ✅ 로컬 JSON 파일에만 저장
- ✅ 알림 및 자동 시작/종료는 별도 스케줄러가 처리

## 데이터 구조

### 채널 선택 값 형식
```
"StreamLive:694A308C79D37854B930"
  └─ 서비스:ID
```

### 저장되는 스케줄 데이터
```json
{
  "schedule_id": "abc12345",
  "channel_id": "694A308C79D37854B930",
  "channel_name": "jtbc_news_archive",
  "service": "StreamLive",
  "title": "KBO 개막전 생중계",
  "start_time": "2026-01-15T18:00:00",
  "end_time": "2026-01-15T21:00:00",
  "assignee_id": "U04N8223X36",
  "assignee_name": "송준용",
  "auto_start": true,
  "auto_stop": false,
  "notify_2h": true,
  "notify_30m": true,
  "status": "scheduled"
}
```

## 향후 개선 가능 사항

### 채널 선택 시 추가 검증
```python
@app.action("schedule_channel_select")
def handle_schedule_channel_select(ack, body, client, logger):
    """Handle channel select in schedule form."""
    ack()
    
    # 선택된 채널 정보 가져오기
    selected_value = body["actions"][0]["selected_option"]["value"]
    service, channel_id = selected_value.split(":", 1)
    
    # 채널 상태 확인 (예: 이미 실행 중인지)
    # channel_status = tencent_client.get_resource_status(channel_id, service)
    
    # 필요시 모달 업데이트 (예: 상태 표시, 경고 메시지 등)
    # client.views_update(...)
```

### 채널별 필터링
- StreamLive만 표시
- 특정 상태의 채널만 표시
- 사용자 권한에 따른 채널 필터링

## 관련 파일

- `app_v2.py`: 스케줄 관련 핸들러
  - `handle_schedule_add_button()`: 모달 열기
  - `handle_schedule_channel_select()`: 채널 선택
  - `handle_schedule_add_submit()`: 스케줄 제출

- `slack_ui.py`: UI 생성
  - `create_schedule_add_modal()`: 스케줄 등록 모달 생성

- `broadcast_schedule.py`: 스케줄 관리
  - `BroadcastScheduleManager.add_schedule()`: 스케줄 저장

- `tencent_cloud_client.py`: 리소스 조회
  - `list_all_resources()`: 모든 리소스 목록 가져오기
