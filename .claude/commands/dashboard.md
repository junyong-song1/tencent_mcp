# Dashboard Skill

Slack 대시보드 UI 수정 가이드를 제공합니다.

## Usage

```
/dashboard [component]
```

## Arguments

- `$ARGUMENTS` - 컴포넌트: `channel`, `flow`, `filter`, `modal` (선택사항)

## 대시보드 구조

```
app/slack/ui/dashboard.py          # 메인 UI 컴포넌트
app/slack/handlers/dashboard.py    # 액션 핸들러
app/slack/handlers/commands.py     # /tencent 명령어
app/services/linkage.py            # 리소스 계층 구조
```

## 주요 메서드

### DashboardUI 클래스 (dashboard.py)

| 메서드 | 용도 |
|--------|------|
| `create_dashboard_modal()` | 전체 대시보드 모달 생성 |
| `create_streamlink_only_modal()` | StreamLink 전용 대시보드 |
| `_create_streamlink_group_blocks()` | 채널+Flow 그룹 블록 |
| `_create_streamlink_child_block()` | StreamLink Flow 블록 |
| `_filter_streamlink_hierarchy()` | 필터링 로직 |

### 데이터 흐름

```
/tencent 명령어
    ↓
commands.py: handle_tencent_command()
    ↓
tencent_client.list_all_resources()
    ↓
linkage.py: group_and_filter_resources()
    ↓
dashboard.py: create_*_modal()
    ↓
Slack Modal 표시
```

## 수정 가이드

### 1. 채널 표시 수정
`_create_streamlink_group_blocks()` 메서드의 `parent_text` 부분

### 2. Flow 표시 수정
`_create_streamlink_child_block()` 메서드의 `flow_text` 부분

### 3. 필터 추가
`_filter_streamlink_hierarchy()` 메서드

### 4. 새로운 버튼 추가
1. UI에 버튼 추가 (dashboard.py)
2. 핸들러 등록 (dashboard.py handlers)
3. 액션 ID 패턴: `streamlink_only_{action}_{id}`

## Slack Block Kit 참고

- Section: 텍스트 + 버튼
- Context: 작은 텍스트 (메타 정보)
- Actions: 버튼 그룹
- Divider: 구분선
