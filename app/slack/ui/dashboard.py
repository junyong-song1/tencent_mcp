"""Dashboard UI components."""
import json
from typing import Dict, List

from app.config import get_settings
from app.services.linkage import group_and_filter_resources
from .common import (
    get_status_emoji,
    get_service_emoji,
    create_divider_block,
    create_header_block,
    create_section_block,
    create_button,
    create_actions_block,
    create_context_block,
)


class DashboardUI:
    """Dashboard modal and blocks generator."""

    ITEMS_PER_PAGE = 25

    @classmethod
    def create_loading_modal(cls, channel_id: str = "") -> dict:
        """Create a loading modal view."""
        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",
            "private_metadata": json.dumps({"channel_id": channel_id, "page": 0}),
            "title": {"type": "plain_text", "text": "Tencent MCP"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": [
                create_section_block(":hourglass_flowing_sand: 텐센트 클라우드에서 리소스를 가져오고 있습니다..."),
            ],
        }

    @classmethod
    def create_dashboard_modal(
        cls,
        channels: List[Dict],
        service_filter: str = "all",
        status_filter: str = "all",
        keyword: str = "",
        channel_id: str = "",
        page: int = 0,
    ) -> dict:
        """Create the main dashboard modal view."""
        settings = get_settings()

        # Build hierarchy and filter
        hierarchy = group_and_filter_resources(
            channels, service_filter, status_filter, keyword
        )

        # Pagination
        total_groups = len(hierarchy)
        max_groups = min(settings.MAX_PARENT_GROUPS, total_groups)
        total_pages = max(1, (max_groups + cls.ITEMS_PER_PAGE - 1) // cls.ITEMS_PER_PAGE)
        page = max(0, min(page, total_pages - 1))

        start_idx = page * cls.ITEMS_PER_PAGE
        end_idx = min(start_idx + cls.ITEMS_PER_PAGE, max_groups)
        page_groups = hierarchy[start_idx:end_idx]

        blocks = []

        # Tab navigation
        blocks.append(cls._create_tab_buttons("channels"))

        # Filter controls
        blocks.append(cls._create_filter_block(service_filter, status_filter))
        blocks.append(cls._create_search_block(keyword))
        blocks.append(create_divider_block())

        # Summary
        running = sum(1 for c in channels if c.get("status") == "running")
        stopped = sum(1 for c in channels if c.get("status") in ["stopped", "idle"])
        blocks.append(
            create_context_block(
                f":bar_chart: 전체 {len(channels)}개 | "
                f":large_green_circle: 실행 {running} | "
                f":red_circle: 중지 {stopped} | "
                f":mag: 필터 결과 {total_groups}개"
            )
        )

        # Resource groups
        if not page_groups:
            blocks.append(
                create_section_block(":mag: 검색 결과가 없습니다. 필터를 변경해 주세요.")
            )
        else:
            for group in page_groups:
                parent = group["parent"]
                children = group["children"]
                blocks.extend(cls._create_resource_group_blocks(parent, children))
                if len(blocks) > 95:
                    break

        # Pagination
        if total_pages > 1:
            blocks.append(create_divider_block())
            blocks.append(cls._create_pagination_block(page, total_pages))

        # Refresh button
        blocks.append(create_divider_block())
        blocks.append(
            create_actions_block([
                create_button("새로고침", "dashboard_refresh", style="primary"),
            ])
        )

        metadata = json.dumps({
            "channel_id": channel_id,
            "page": page,
            "service_filter": service_filter,
            "status_filter": status_filter,
        })

        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": "Tencent MCP"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": blocks[:100],  # Slack limit
        }

    @classmethod
    def _create_tab_buttons(cls, active_tab: str = "channels") -> dict:
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
    def _create_filter_block(cls, service_filter: str, status_filter: str) -> dict:
        """Create filter dropdown block."""
        service_options = [
            {"text": {"type": "plain_text", "text": "전체 서비스"}, "value": "all"},
            {"text": {"type": "plain_text", "text": "StreamLive"}, "value": "StreamLive"},
            {"text": {"type": "plain_text", "text": "StreamLink"}, "value": "StreamLink"},
        ]

        status_options = [
            {"text": {"type": "plain_text", "text": "전체 상태"}, "value": "all"},
            {"text": {"type": "plain_text", "text": "실행 중"}, "value": "running"},
            {"text": {"type": "plain_text", "text": "중지됨"}, "value": "stopped"},
            {"text": {"type": "plain_text", "text": "오류"}, "value": "error"},
        ]

        service_initial = next(
            (o for o in service_options if o["value"] == service_filter),
            service_options[0],
        )
        status_initial = next(
            (o for o in status_options if o["value"] == status_filter),
            status_options[0],
        )

        return {
            "type": "actions",
            "block_id": "dashboard_filters",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "dashboard_filter_service",
                    "placeholder": {"type": "plain_text", "text": "서비스 선택"},
                    "options": service_options,
                    "initial_option": service_initial,
                },
                {
                    "type": "static_select",
                    "action_id": "dashboard_filter_status",
                    "placeholder": {"type": "plain_text", "text": "상태 선택"},
                    "options": status_options,
                    "initial_option": status_initial,
                },
            ],
        }

    @classmethod
    def _create_search_block(cls, keyword: str = "") -> dict:
        """Create search input block."""
        return {
            "type": "input",
            "block_id": "search_block",
            "dispatch_action": True,
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "dashboard_search_input",
                "placeholder": {"type": "plain_text", "text": "채널명 검색..."},
                "initial_value": keyword,
                "dispatch_action_config": {
                    "trigger_actions_on": ["on_enter_pressed"],
                },
            },
            "label": {"type": "plain_text", "text": "검색"},
        }

    @classmethod
    def _create_resource_group_blocks(
        cls, parent: Dict, children: List[Dict]
    ) -> List[dict]:
        """Create blocks for a resource group."""
        blocks = []

        status_emoji = get_status_emoji(parent.get("status", "unknown"))
        service_emoji = get_service_emoji(parent.get("service", ""))

        # Note: Input status is checked when user clicks info button, not in list view
        # to avoid performance issues with multiple API calls

        parent_text = (
            f"{status_emoji} {service_emoji} *{parent.get('name', 'Unknown')}*\n"
            f"ID: `{parent.get('id', '')}` | 상태: {parent.get('status', 'unknown')}"
        )

        # Parent info section
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": parent_text},
        })

        # Parent control buttons
        parent_buttons = cls._create_parent_control_buttons(parent, children)
        blocks.append({
            "type": "actions",
            "block_id": f"parent_actions_{parent.get('id', '')}",
            "elements": parent_buttons,
        })

        # Children (linked flows) with individual controls
        if children:
            for child in children[:5]:
                child_status_emoji = get_status_emoji(child.get("status", "unknown"))
                child_status_text = child.get("status", "unknown")
                child_id = child.get("id", "")
                child_service = child.get("service", "")
                child_name = child.get("name", "Unknown")
                child_service_emoji = get_service_emoji(child_service)

                # Create child control button
                child_btn = cls._create_child_control_button(child)

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"  └ {child_status_emoji} {child_service_emoji} *{child_name}* | 상태: {child_status_text}"
                    },
                    "accessory": child_btn,
                })

            if len(children) > 5:
                blocks.append(
                    create_context_block(f"  _... 외 {len(children) - 5}개_")
                )

        blocks.append(create_divider_block())
        return blocks

    @classmethod
    def _create_control_buttons(
        cls, resource: Dict, children: List[Dict] = None
    ) -> List[dict]:
        """Create control menu options for a resource.

        Args:
            resource: Parent resource dict
            children: List of linked child resources (for integrated control)
        """
        resource_id = resource.get("id", "")
        service = resource.get("service", "")
        status = resource.get("status", "unknown")
        has_children = bool(children)

        options = []

        if status in ["stopped", "idle"]:
            # Show integrated option first if there are linked resources
            if has_children:
                options.append({
                    "text": {"type": "plain_text", "text": "🔗 통합 시작"},
                    "value": f"start_all:{service}:{resource_id}",
                })
            options.append({
                "text": {"type": "plain_text", "text": "▶️ 개별 시작"},
                "value": f"start:{service}:{resource_id}",
            })
        elif status == "running":
            if has_children:
                options.append({
                    "text": {"type": "plain_text", "text": "🔗 통합 중지"},
                    "value": f"stop_all:{service}:{resource_id}",
                })
            options.append({
                "text": {"type": "plain_text", "text": "⏹️ 개별 중지"},
                "value": f"stop:{service}:{resource_id}",
            })
            options.append({
                "text": {"type": "plain_text", "text": "🔄 재시작"},
                "value": f"restart:{service}:{resource_id}",
            })

        options.append({
            "text": {"type": "plain_text", "text": "ℹ️ 상세 정보"},
            "value": f"info:{service}:{resource_id}",
        })

        return options

    @classmethod
    def _create_parent_control_buttons(
        cls, parent: Dict, children: List[Dict] = None
    ) -> List[dict]:
        """Create control buttons for parent resource."""
        resource_id = parent.get("id", "")
        service = parent.get("service", "")
        status = parent.get("status", "unknown")
        has_children = bool(children)

        buttons = []

        # Individual control button
        if status in ["stopped", "idle"]:
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ 시작", "emoji": True},
                "action_id": f"parent_start_{resource_id}",
                "value": f"{service}:{resource_id}",
                "style": "primary",
            })
        elif status == "running":
            buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "⏹️ 중지", "emoji": True},
                "action_id": f"parent_stop_{resource_id}",
                "value": f"{service}:{resource_id}",
                "style": "danger",
            })

        # Integrated control button (only if has children)
        if has_children:
            if status in ["stopped", "idle"]:
                buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗 통합 시작", "emoji": True},
                    "action_id": f"integrated_start_{resource_id}",
                    "value": f"{service}:{resource_id}",
                })
            elif status == "running":
                buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗 통합 중지", "emoji": True},
                    "action_id": f"integrated_stop_{resource_id}",
                    "value": f"{service}:{resource_id}",
                })

        # Info button
        buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "ℹ️", "emoji": True},
            "action_id": f"parent_info_{resource_id}",
            "value": f"{service}:{resource_id}",
        })

        return buttons

    @classmethod
    def _create_child_control_button(cls, resource: Dict) -> dict:
        """Create a simple control button for child resources."""
        resource_id = resource.get("id", "")
        service = resource.get("service", "")
        status = resource.get("status", "unknown")

        if status in ["stopped", "idle"]:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ 시작", "emoji": True},
                "action_id": f"child_start_{resource_id}",
                "value": f"{service}:{resource_id}",
                "style": "primary",
            }
        elif status == "running":
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "⏹️ 중지", "emoji": True},
                "action_id": f"child_stop_{resource_id}",
                "value": f"{service}:{resource_id}",
                "style": "danger",
            }
        else:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "ℹ️ 정보", "emoji": True},
                "action_id": f"child_info_{resource_id}",
                "value": f"{service}:{resource_id}",
            }

    @classmethod
    def _create_pagination_block(cls, page: int, total_pages: int) -> dict:
        """Create pagination controls."""
        elements = []

        if page > 0:
            elements.append(create_button("◀ 이전", "dashboard_page_prev"))

        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": f"{page + 1} / {total_pages}"},
            "action_id": "dashboard_page_info",
        })

        if page < total_pages - 1:
            elements.append(create_button("다음 ▶", "dashboard_page_next"))

        return create_actions_block(elements)
