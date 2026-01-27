"""Status tab UI components."""
import json
from typing import Dict, List

from .common import (
    get_status_emoji,
    create_divider_block,
    create_header_block,
    create_section_block,
    create_button,
    create_actions_block,
    create_context_block,
)


class StatusUI:
    """Status tab UI generator."""

    @classmethod
    def create_status_tab_modal(
        cls,
        channels: List[Dict],
        schedules_today: List[Dict],
        schedules_upcoming: List[Dict],
        channel_id: str = "",
    ) -> dict:
        """Create the status tab modal view."""
        blocks = []

        # Tab navigation
        blocks.append(cls._create_tab_buttons("status"))

        blocks.append(create_divider_block())

        # Overall status summary
        running = sum(1 for c in channels if c.get("status") == "running")
        stopped = sum(1 for c in channels if c.get("status") in ["stopped", "idle"])
        error = sum(1 for c in channels if c.get("status") == "error")

        blocks.append(create_header_block("시스템 현황"))
        blocks.append(
            create_section_block(
                f":large_green_circle: 실행 중: *{running}*개\n"
                f":red_circle: 중지됨: *{stopped}*개\n"
                f":warning: 오류: *{error}*개\n"
                f":bar_chart: 전체: *{len(channels)}*개"
            )
        )

        blocks.append(create_divider_block())

        # Today's schedules
        blocks.append(create_header_block(f"오늘 스케줄 ({len(schedules_today)}개)"))
        if schedules_today:
            for schedule in schedules_today[:5]:
                blocks.append(
                    create_context_block(
                        f":calendar: *{schedule.get('title', '')}* | "
                        f"{schedule.get('start_time', '')} ~ {schedule.get('end_time', '')} | "
                        f"<@{schedule.get('assignee_id', '')}>"
                    )
                )
            if len(schedules_today) > 5:
                blocks.append(
                    create_context_block(f"_... 외 {len(schedules_today) - 5}개_")
                )
        else:
            blocks.append(create_context_block("오늘 예정된 스케줄이 없습니다."))

        blocks.append(create_divider_block())

        # Upcoming schedules (24h)
        blocks.append(create_header_block(f"예정된 스케줄 - 24시간 ({len(schedules_upcoming)}개)"))
        if schedules_upcoming:
            for schedule in schedules_upcoming[:5]:
                blocks.append(
                    create_context_block(
                        f":hourglass_flowing_sand: *{schedule.get('title', '')}* | "
                        f"{schedule.get('start_time', '')} | "
                        f"<@{schedule.get('assignee_id', '')}>"
                    )
                )
            if len(schedules_upcoming) > 5:
                blocks.append(
                    create_context_block(f"_... 외 {len(schedules_upcoming) - 5}개_")
                )
        else:
            blocks.append(create_context_block("24시간 내 예정된 스케줄이 없습니다."))

        # Refresh button
        blocks.append(create_divider_block())
        blocks.append(
            create_actions_block([
                create_button("새로고침", "status_refresh", style="primary"),
            ])
        )

        metadata = json.dumps({
            "channel_id": channel_id,
            "tab": "status",
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
    def _create_tab_buttons(cls, active_tab: str = "status") -> dict:
        """Create tab navigation buttons."""
        tabs = [
            ("tab_channels", "채널", active_tab == "channels"),
            ("tab_schedules", "스케줄", active_tab == "schedules"),
            ("tab_status", "상태", active_tab == "status"),
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
