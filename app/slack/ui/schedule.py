"""Schedule UI components."""
import json
from datetime import datetime
from typing import Dict, List

from .common import (
    get_schedule_status_emoji,
    create_divider_block,
    create_header_block,
    create_section_block,
    create_button,
    create_actions_block,
    create_context_block,
)


class ScheduleUI:
    """Schedule tab UI generator."""

    @classmethod
    def create_schedule_tab_modal(
        cls,
        schedules: List[Dict],
        selected_date: str = None,
        channel_id: str = "",
    ) -> dict:
        """Create the schedule tab modal view.

        Args:
            schedules: List of schedule dicts
            selected_date: Date string (YYYY-MM-DD) or None for "all upcoming"
            channel_id: Slack channel ID
        """
        blocks = []
        today = datetime.now().strftime("%Y-%m-%d")
        show_all_upcoming = selected_date is None

        # Tab navigation
        blocks.append(cls._create_tab_buttons("schedules"))

        # Date picker and add button
        date_picker_elements = [
            {
                "type": "datepicker",
                "action_id": "schedule_date_picker",
                "initial_date": selected_date or today,
                "placeholder": {"type": "plain_text", "text": "날짜 선택"},
            },
            create_button("+ 스케줄 추가", "schedule_add_button", style="primary"),
            create_button("새로고침", "schedule_refresh"),
        ]

        blocks.append({
            "type": "actions",
            "elements": date_picker_elements,
        })

        blocks.append(create_divider_block())

        # Schedule list
        if not schedules:
            if show_all_upcoming:
                blocks.append(
                    create_section_block(":calendar: 등록된 예정 스케줄이 없습니다.")
                )
            else:
                blocks.append(
                    create_section_block(
                        f":calendar: {selected_date}에 등록된 스케줄이 없습니다."
                    )
                )
        else:
            if show_all_upcoming:
                blocks.append(
                    create_header_block(f"다가오는 스케줄 ({len(schedules)}개)")
                )
            else:
                blocks.append(
                    create_header_block(f"{selected_date} 스케줄 ({len(schedules)}개)")
                )

            for schedule in schedules:
                blocks.extend(cls._create_schedule_item_blocks(schedule, show_date=show_all_upcoming))

        metadata = json.dumps({
            "channel_id": channel_id,
            "selected_date": selected_date,
            "tab": "schedules",
        })

        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": "Tencent MCP"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": blocks[:100],
        }

    @classmethod
    def create_schedule_add_modal(
        cls,
        channels: List[Dict],
        parent_metadata: str,
        selected_date: str,
    ) -> dict:
        """Create the add schedule modal."""
        channel_options = [
            {
                "text": {"type": "plain_text", "text": ch.get("name", ch.get("id", ""))[:75]},
                "value": f"{ch.get('service', '')}:{ch.get('id', '')}",
            }
            for ch in channels[:100]
        ]

        if not channel_options:
            channel_options = [
                {"text": {"type": "plain_text", "text": "채널 없음"}, "value": "none:none"}
            ]

        return {
            "type": "modal",
            "callback_id": "schedule_add_modal_submit",
            "private_metadata": parent_metadata,
            "title": {"type": "plain_text", "text": "스케줄 추가"},
            "submit": {"type": "plain_text", "text": "저장"},
            "close": {"type": "plain_text", "text": "취소"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "schedule_title_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "schedule_title_input",
                        "placeholder": {"type": "plain_text", "text": "방송 제목 입력"},
                    },
                    "label": {"type": "plain_text", "text": "방송 제목"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_channel_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "schedule_channel_select",
                        "placeholder": {"type": "plain_text", "text": "채널 선택"},
                        "options": channel_options,
                    },
                    "label": {"type": "plain_text", "text": "채널"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_start_date_block",
                    "element": {
                        "type": "datepicker",
                        "action_id": "schedule_start_date_input",
                        "initial_date": selected_date,
                    },
                    "label": {"type": "plain_text", "text": "시작 날짜"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_start_time_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "schedule_start_time_input",
                        "initial_time": "09:00",
                    },
                    "label": {"type": "plain_text", "text": "시작 시간"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_end_date_block",
                    "element": {
                        "type": "datepicker",
                        "action_id": "schedule_end_date_input",
                        "initial_date": selected_date,
                    },
                    "label": {"type": "plain_text", "text": "종료 날짜"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_end_time_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "schedule_end_time_input",
                        "initial_time": "18:00",
                    },
                    "label": {"type": "plain_text", "text": "종료 시간"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_assignee_block",
                    "element": {
                        "type": "users_select",
                        "action_id": "schedule_assignee_select",
                        "placeholder": {"type": "plain_text", "text": "담당자 선택"},
                    },
                    "label": {"type": "plain_text", "text": "담당자"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_options_block",
                    "optional": True,
                    "element": {
                        "type": "checkboxes",
                        "action_id": "schedule_options_input",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "2시간 전 알림"},
                                "value": "notify_2h",
                            },
                            {
                                "text": {"type": "plain_text", "text": "30분 전 알림"},
                                "value": "notify_30m",
                            },
                        ],
                        "initial_options": [
                            {
                                "text": {"type": "plain_text", "text": "2시간 전 알림"},
                                "value": "notify_2h",
                            },
                            {
                                "text": {"type": "plain_text", "text": "30분 전 알림"},
                                "value": "notify_30m",
                            },
                        ],
                    },
                    "label": {"type": "plain_text", "text": "알림 설정"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_repeat_block",
                    "optional": True,
                    "element": {
                        "type": "static_select",
                        "action_id": "schedule_repeat_select",
                        "placeholder": {"type": "plain_text", "text": "반복 주기"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "반복 없음"}, "value": "none"},
                            {"text": {"type": "plain_text", "text": "매일"}, "value": "daily"},
                            {"text": {"type": "plain_text", "text": "매주"}, "value": "weekly"},
                            {"text": {"type": "plain_text", "text": "매월"}, "value": "monthly"},
                        ],
                        "initial_option": {"text": {"type": "plain_text", "text": "반복 없음"}, "value": "none"},
                    },
                    "label": {"type": "plain_text", "text": "반복 설정"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_repeat_count_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "schedule_repeat_count_input",
                        "placeholder": {"type": "plain_text", "text": "횟수 또는 종료일 (YYYY-MM-DD)"},
                    },
                    "label": {"type": "plain_text", "text": "반복 횟수/종료일"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_notes_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "schedule_notes_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "메모 입력 (선택사항)"},
                    },
                    "label": {"type": "plain_text", "text": "메모"},
                },
            ],
        }

    @classmethod
    def create_schedule_edit_modal(
        cls,
        schedule: Dict,
        channels: List[Dict],
        parent_metadata: str,
    ) -> dict:
        """Create the edit schedule modal."""
        channel_options = [
            {
                "text": {"type": "plain_text", "text": ch.get("name", ch.get("id", ""))[:75]},
                "value": f"{ch.get('service', '')}:{ch.get('id', '')}",
            }
            for ch in channels[:100]
        ]

        if not channel_options:
            channel_options = [
                {"text": {"type": "plain_text", "text": "채널 없음"}, "value": "none:none"}
            ]

        # Find initial channel option
        current_channel_value = f"{schedule.get('service', '')}:{schedule.get('channel_id', '')}"
        initial_channel = None
        for opt in channel_options:
            if opt["value"] == current_channel_value:
                initial_channel = opt
                break
        if not initial_channel:
            initial_channel = channel_options[0]

        # Parse datetime
        try:
            start_dt = datetime.fromisoformat(schedule.get("start_time_iso", ""))
            end_dt = datetime.fromisoformat(schedule.get("end_time_iso", ""))
            start_date = start_dt.strftime("%Y-%m-%d")
            start_time = start_dt.strftime("%H:%M")
            end_date = end_dt.strftime("%Y-%m-%d")
            end_time = end_dt.strftime("%H:%M")
        except Exception:
            start_date = datetime.now().strftime("%Y-%m-%d")
            start_time = "09:00"
            end_date = start_date
            end_time = "18:00"

        # Build initial options for checkboxes
        initial_options = []
        if schedule.get("notify_2h", False):
            initial_options.append({
                "text": {"type": "plain_text", "text": "2시간 전 알림"},
                "value": "notify_2h",
            })
        if schedule.get("notify_30m", False):
            initial_options.append({
                "text": {"type": "plain_text", "text": "30분 전 알림"},
                "value": "notify_30m",
            })

        # Include schedule_id in metadata
        import json
        try:
            meta = json.loads(parent_metadata)
        except (json.JSONDecodeError, TypeError):
            meta = {}
        meta["schedule_id"] = schedule.get("schedule_id", "")
        edit_metadata = json.dumps(meta)

        checkbox_element = {
            "type": "checkboxes",
            "action_id": "schedule_options_input",
            "options": [
                {
                    "text": {"type": "plain_text", "text": "2시간 전 알림"},
                    "value": "notify_2h",
                },
                {
                    "text": {"type": "plain_text", "text": "30분 전 알림"},
                    "value": "notify_30m",
                },
            ],
        }
        if initial_options:
            checkbox_element["initial_options"] = initial_options

        return {
            "type": "modal",
            "callback_id": "schedule_edit_modal_submit",
            "private_metadata": edit_metadata,
            "title": {"type": "plain_text", "text": "스케줄 수정"},
            "submit": {"type": "plain_text", "text": "저장"},
            "close": {"type": "plain_text", "text": "취소"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "schedule_title_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "schedule_title_input",
                        "initial_value": schedule.get("title", ""),
                        "placeholder": {"type": "plain_text", "text": "방송 제목 입력"},
                    },
                    "label": {"type": "plain_text", "text": "방송 제목"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_channel_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "schedule_channel_select",
                        "placeholder": {"type": "plain_text", "text": "채널 선택"},
                        "options": channel_options,
                        "initial_option": initial_channel,
                    },
                    "label": {"type": "plain_text", "text": "채널"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_start_date_block",
                    "element": {
                        "type": "datepicker",
                        "action_id": "schedule_start_date_input",
                        "initial_date": start_date,
                    },
                    "label": {"type": "plain_text", "text": "시작 날짜"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_start_time_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "schedule_start_time_input",
                        "initial_time": start_time,
                    },
                    "label": {"type": "plain_text", "text": "시작 시간"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_end_date_block",
                    "element": {
                        "type": "datepicker",
                        "action_id": "schedule_end_date_input",
                        "initial_date": end_date,
                    },
                    "label": {"type": "plain_text", "text": "종료 날짜"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_end_time_block",
                    "element": {
                        "type": "timepicker",
                        "action_id": "schedule_end_time_input",
                        "initial_time": end_time,
                    },
                    "label": {"type": "plain_text", "text": "종료 시간"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_assignee_block",
                    "element": {
                        "type": "users_select",
                        "action_id": "schedule_assignee_select",
                        "initial_user": schedule.get("assignee_id", ""),
                        "placeholder": {"type": "plain_text", "text": "담당자 선택"},
                    },
                    "label": {"type": "plain_text", "text": "담당자"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_options_block",
                    "optional": True,
                    "element": checkbox_element,
                    "label": {"type": "plain_text", "text": "알림 설정"},
                },
                {
                    "type": "input",
                    "block_id": "schedule_notes_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "schedule_notes_input",
                        "multiline": True,
                        "initial_value": schedule.get("notes", ""),
                        "placeholder": {"type": "plain_text", "text": "메모 입력 (선택사항)"},
                    },
                    "label": {"type": "plain_text", "text": "메모"},
                },
            ],
        }

    @classmethod
    def _create_tab_buttons(cls, active_tab: str = "schedules") -> dict:
        """Create tab navigation buttons."""
        tabs = [
            ("tab_channels", "채널", active_tab == "channels"),
            ("tab_schedules", "스케줄", active_tab == "schedules"),
        ]

        elements = []
        for action_id, label, is_active in tabs:
            btn = create_button(
                f"{'*' if is_active else ''}{label}{'*' if is_active else ''}",
                action_id,
                style="primary" if is_active else None,
            )
            elements.append(btn)

        return create_actions_block(elements, "tab_buttons")

    @classmethod
    def _create_schedule_item_blocks(cls, schedule: Dict, show_date: bool = False) -> List[dict]:
        """Create blocks for a single schedule item.

        Args:
            schedule: Schedule dict
            show_date: Whether to show the date (for all upcoming view)
        """
        status_emoji = get_schedule_status_emoji(schedule.get("status", "scheduled"))
        start_time_iso = schedule.get("start_time_iso", "")
        end_time_iso = schedule.get("end_time_iso", "")

        # Parse datetime for display
        try:
            start_dt = datetime.fromisoformat(start_time_iso)
            end_dt = datetime.fromisoformat(end_time_iso)
            if show_date:
                time_str = f"{start_dt.strftime('%Y-%m-%d')} {start_dt.strftime('%H:%M')} ~ {end_dt.strftime('%H:%M')}"
            else:
                time_str = f"{start_dt.strftime('%H:%M')} ~ {end_dt.strftime('%H:%M')}"
        except Exception:
            time_str = f"{start_time_iso} ~ {end_time_iso}"

        text = (
            f"{status_emoji} *{schedule.get('title', 'Untitled')}*\n"
            f":clock1: {time_str}\n"
            f":tv: {schedule.get('channel_name', '')} | "
            f":bust_in_silhouette: <@{schedule.get('assignee_id', '')}>"
        )

        # Add notes if present
        notes = schedule.get("notes", "")
        if notes:
            text += f"\n:memo: {notes[:50]}{'...' if len(notes) > 50 else ''}"

        schedule_id = schedule.get("schedule_id", "")

        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
                "accessory": {
                    "type": "overflow",
                    "action_id": f"schedule_menu_{schedule_id}",
                    "options": [
                        {"text": {"type": "plain_text", "text": "수정"}, "value": f"edit:{schedule_id}"},
                        {"text": {"type": "plain_text", "text": "삭제"}, "value": f"delete:{schedule_id}"},
                    ],
                },
            },
            create_divider_block(),
        ]
