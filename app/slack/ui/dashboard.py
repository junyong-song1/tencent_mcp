"""Dashboard UI components."""
import json
from typing import Dict, List, Optional

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
        flow_stats: Optional[Dict[str, Dict]] = None,
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
                blocks.extend(cls._create_resource_group_blocks(parent, children, flow_stats))
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
        cls, parent: Dict, children: List[Dict], flow_stats: Optional[Dict[str, Dict]] = None
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

                # Build child text with metrics if available
                child_text = f"  └ {child_status_emoji} {child_service_emoji} *{child_name}*"

                # Add metrics for running flows
                if child_status_text == "running" and flow_stats and child_id in flow_stats:
                    stats = flow_stats[child_id]
                    if stats:
                        metrics_parts = []
                        bitrate = stats.get("bitrate_mbps", "0")
                        fps = stats.get("fps", 0)

                        if float(bitrate) > 0:
                            metrics_parts.append(f"{bitrate}Mbps")
                        if fps > 0:
                            metrics_parts.append(f"{fps}fps")

                        if metrics_parts:
                            child_text += f"\n      :bar_chart: {' / '.join(metrics_parts)}"

                child_text += f" | 상태: {child_status_text}"

                # Create child control button
                child_btn = cls._create_child_control_button(child)

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": child_text,
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

    # ========== StreamLink Only Dashboard ==========

    STREAMLINK_ITEMS_PER_PAGE = 20

    @classmethod
    def create_streamlink_only_loading_modal(cls, channel_id: str = "") -> dict:
        """Create a loading modal for StreamLink-only dashboard."""
        return {
            "type": "modal",
            "callback_id": "streamlink_only_modal_view",
            "private_metadata": json.dumps({"channel_id": channel_id, "page": 0}),
            "title": {"type": "plain_text", "text": "StreamLink"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": [
                create_section_block(":hourglass_flowing_sand: StreamLink Flow 정보를 가져오고 있습니다..."),
            ],
        }

    @classmethod
    def create_streamlink_only_modal(
        cls,
        hierarchy: List[Dict],
        status_filter: str = "all",
        keyword: str = "",
        channel_id: str = "",
        page: int = 0,
        failover_map: Optional[Dict[str, Dict]] = None,
        loading_message: Optional[str] = None,
    ) -> dict:
        """Create StreamLink-only dashboard modal for external partners.

        Shows StreamLive channels as parents with their linked StreamLink flows as children.
        Same hierarchy structure as the full dashboard.

        Args:
            hierarchy: List of {parent: StreamLive, children: [StreamLink flows]}
            status_filter: Filter by status (all, running, stopped)
            keyword: Search keyword
            channel_id: Slack channel ID
            page: Current page number
            failover_map: Optional map of channel_id to failover info
                         {channel_id: {"active_input": str, "failover_info": dict}}
            loading_message: Optional loading message to show as banner
        """
        if failover_map is None:
            failover_map = {}
        blocks = []

        # Header
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": "📡 StreamLink 대시보드", "emoji": True}
        })

        # Loading banner (if provided)
        if loading_message:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⏳ *{loading_message}*"}
            })
            blocks.append(create_divider_block())

        # Filter controls
        blocks.append(cls._create_streamlink_filter_block(status_filter))
        blocks.append(cls._create_streamlink_search_block(keyword))
        blocks.append(create_divider_block())

        # Filter hierarchy - only show groups with StreamLink children
        filtered_hierarchy = cls._filter_streamlink_hierarchy(hierarchy, status_filter, keyword)

        # Count channels and flows with status
        streamlive_groups = [g for g in hierarchy if g["parent"].get("service") == "StreamLive" and g["children"]]
        total_channels = len(streamlive_groups)
        channels_running = sum(1 for g in streamlive_groups if g["parent"].get("status") == "running")
        channels_stopped = total_channels - channels_running

        total_flows = sum(len(g["children"]) for g in streamlive_groups)
        flows_running = sum(
            1 for g in streamlive_groups
            for c in g["children"] if c.get("status") == "running"
        )
        flows_stopped = total_flows - flows_running

        filtered_count = sum(len(g["children"]) for g in filtered_hierarchy)

        blocks.append(
            create_context_block(
                f"📺 채널 {total_channels} (🟢{channels_running} 🔴{channels_stopped}) | "
                f"📡 Flow {total_flows} (🟢{flows_running} 🔴{flows_stopped}) | "
                f"🔍 필터 {filtered_count}"
            )
        )
        blocks.append(create_divider_block())

        # Pagination (by groups)
        total_pages = max(1, (len(filtered_hierarchy) + cls.STREAMLINK_ITEMS_PER_PAGE - 1) // cls.STREAMLINK_ITEMS_PER_PAGE)
        page = max(0, min(page, total_pages - 1))
        start_idx = page * cls.STREAMLINK_ITEMS_PER_PAGE
        end_idx = min(start_idx + cls.STREAMLINK_ITEMS_PER_PAGE, len(filtered_hierarchy))
        page_groups = filtered_hierarchy[start_idx:end_idx]

        # Resource groups
        if not page_groups:
            blocks.append(
                create_section_block(":mag: 검색 결과가 없습니다.")
            )
        else:
            for group in page_groups:
                group_blocks = cls._create_streamlink_group_blocks(group, failover_map)
                blocks.extend(group_blocks)
                if len(blocks) > 90:
                    break

        # Pagination controls
        if total_pages > 1:
            blocks.append(create_divider_block())
            blocks.append(cls._create_streamlink_pagination_block(page, total_pages))

        # Refresh button
        blocks.append(create_divider_block())
        blocks.append(
            create_actions_block([
                create_button("🔄 새로고침", "streamlink_only_refresh", style="primary"),
            ])
        )

        metadata = json.dumps({
            "channel_id": channel_id,
            "page": page,
            "status_filter": status_filter,
            "keyword": keyword,
        })

        return {
            "type": "modal",
            "callback_id": "streamlink_only_modal_view",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": "StreamLink"},
            "close": {"type": "plain_text", "text": "닫기"},
            "blocks": blocks[:100],
        }

    @classmethod
    def _filter_streamlink_hierarchy(
        cls, hierarchy: List[Dict], status_filter: str, keyword: str
    ) -> List[Dict]:
        """Filter hierarchy to only show groups with StreamLink children that match filters."""
        filtered = []

        for group in hierarchy:
            parent = group["parent"]
            children = group["children"]

            # Skip if parent is StreamLink (unlinked flow)
            if parent.get("service") != "StreamLive":
                continue

            # Skip if no children
            if not children:
                continue

            # Filter children by status
            filtered_children = children
            if status_filter == "running":
                filtered_children = [c for c in filtered_children if c.get("status") == "running"]
            elif status_filter == "stopped":
                filtered_children = [c for c in filtered_children if c.get("status") in ["stopped", "idle"]]

            # Filter by keyword (match parent or children)
            if keyword:
                keyword_lower = keyword.lower()
                parent_match = (
                    keyword_lower in parent.get("name", "").lower()
                    or keyword_lower in parent.get("id", "").lower()
                )
                if parent_match:
                    # Parent matches, include all filtered children
                    pass
                else:
                    # Filter children by keyword
                    filtered_children = [
                        c for c in filtered_children
                        if keyword_lower in c.get("name", "").lower()
                        or keyword_lower in c.get("id", "").lower()
                    ]

            if filtered_children:
                filtered.append({"parent": parent, "children": filtered_children})

        return filtered

    @classmethod
    def _create_streamlink_group_blocks(cls, group: Dict, failover_map: Dict[str, Dict] = None) -> List[dict]:
        """Create blocks for a StreamLive parent with StreamLink children."""
        blocks = []
        parent = group["parent"]
        children = group["children"]
        if failover_map is None:
            failover_map = {}

        # Parent (StreamLive channel) header
        parent_status = parent.get("status", "unknown")
        parent_emoji = get_status_emoji(parent_status)
        parent_name = parent.get("name", "Unknown")
        parent_id = parent.get("id", "")

        # Build parent text with failover status if available
        failover_info = failover_map.get(parent_id, {})
        active_input = failover_info.get("active_input")
        log_info = failover_info.get("failover_info", {})

        parent_text = f"{parent_emoji} 📺 *{parent_name}*"

        # Add failover status
        if active_input:
            if active_input == "main":
                parent_text += " | 🟢 Main"
            elif active_input == "backup":
                last_event = log_info.get("last_event_type", "")
                if last_event == "PipelineFailover":
                    parent_text += " | 🟡 Backup (Failover)"
                else:
                    parent_text += " | 🟡 Backup"
            elif active_input == "no_signal":
                parent_text += " | ⚫ 신호 없음"
            else:
                parent_text += f" | ⚪ {active_input}"

        parent_text += f"\nID: `{parent_id[:20]}...` | 상태: {parent_status}"

        # Add failover time if available
        if active_input == "backup" and log_info.get("last_event_type") == "PipelineFailover":
            last_time = log_info.get("last_event_time")
            if last_time:
                parent_text += f" | 전환: {last_time}"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": parent_text},
        })

        # Children (StreamLink flows)
        for child in children[:5]:  # Limit to 5 children
            child_block = cls._create_streamlink_child_block(child)
            blocks.append(child_block)

        if len(children) > 5:
            blocks.append(
                create_context_block(f"  _... 외 {len(children) - 5}개_")
            )

        blocks.append(create_divider_block())
        return blocks

    @classmethod
    def _create_streamlink_child_block(cls, flow: Dict) -> dict:
        """Create a block for a StreamLink flow (child)."""
        flow_id = flow.get("id", "")
        flow_name = flow.get("name", "Unknown")
        flow_status = flow.get("status", "unknown")
        status_emoji = get_status_emoji(flow_status)

        flow_text = f"  └ {status_emoji} 📡 *{flow_name}* | 상태: {flow_status}"

        # Control button
        if flow_status in ["stopped", "idle"]:
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ 시작", "emoji": True},
                "action_id": f"streamlink_only_start_{flow_id}",
                "value": f"StreamLink:{flow_id}",
                "style": "primary",
            }
        elif flow_status == "running":
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "⏹️ 중지", "emoji": True},
                "action_id": f"streamlink_only_stop_{flow_id}",
                "value": f"StreamLink:{flow_id}",
                "style": "danger",
            }
        else:
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "ℹ️ 정보", "emoji": True},
                "action_id": f"streamlink_only_info_{flow_id}",
                "value": f"StreamLink:{flow_id}",
            }

        return {
            "type": "section",
            "text": {"type": "mrkdwn", "text": flow_text},
            "accessory": control_btn,
        }

    @classmethod
    def _create_streamlink_filter_block(cls, status_filter: str) -> dict:
        """Create filter dropdown for StreamLink dashboard."""
        status_options = [
            {"text": {"type": "plain_text", "text": "전체 상태"}, "value": "all"},
            {"text": {"type": "plain_text", "text": "실행 중"}, "value": "running"},
            {"text": {"type": "plain_text", "text": "중지됨"}, "value": "stopped"},
        ]

        status_initial = next(
            (o for o in status_options if o["value"] == status_filter),
            status_options[0],
        )

        return {
            "type": "actions",
            "block_id": "streamlink_only_filters",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "streamlink_only_filter_status",
                    "placeholder": {"type": "plain_text", "text": "상태 선택"},
                    "options": status_options,
                    "initial_option": status_initial,
                },
            ],
        }

    @classmethod
    def _create_streamlink_search_block(cls, keyword: str = "") -> dict:
        """Create search input for StreamLink dashboard."""
        return {
            "type": "input",
            "block_id": "streamlink_only_search_block",
            "dispatch_action": True,
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "streamlink_only_search_input",
                "placeholder": {"type": "plain_text", "text": "Flow 이름 검색..."},
                "initial_value": keyword,
                "dispatch_action_config": {
                    "trigger_actions_on": ["on_enter_pressed"],
                },
            },
            "label": {"type": "plain_text", "text": "검색"},
        }

    @classmethod
    def _create_streamlink_flow_card(
        cls, flow: Dict, flow_to_channel_map: Dict[str, Dict]
    ) -> List[dict]:
        """Create a card block for a StreamLink flow."""
        blocks = []

        flow_id = flow.get("id", "")
        flow_name = flow.get("name", "Unknown")
        flow_status = flow.get("status", "unknown")
        status_emoji = get_status_emoji(flow_status)

        # Flow info
        flow_text = f"{status_emoji} *{flow_name}*\n"
        flow_text += f"ID: `{flow_id[:20]}...` | 상태: {flow_status}"

        # Linked StreamLive channel info
        channel_info = flow_to_channel_map.get(flow_id)
        if channel_info:
            ch_name = channel_info.get("channel_name", "")
            active_input = channel_info.get("active_input")  # None if not fetched
            failover_info = channel_info.get("failover_info", {})

            if active_input:
                # Failover status was fetched - show full info
                if active_input == "main":
                    input_display = "🟢 Main"
                elif active_input == "backup":
                    last_event = failover_info.get("last_event_type", "")
                    if last_event == "PipelineFailover":
                        input_display = "🟡 Backup (Failover)"
                    else:
                        input_display = "🟡 Backup"
                else:
                    input_display = f"⚪ {active_input}"

                flow_text += f"\n📺 연결: *{ch_name}* ({input_display})"

                # Show failover time if recent
                last_event_time = failover_info.get("last_event_time")
                if last_event_time and failover_info.get("last_event_type") == "PipelineFailover":
                    flow_text += f"\n└ 전환: {last_event_time}"
            else:
                # Failover status not fetched - show channel name only
                flow_text += f"\n📺 연결: *{ch_name}*"

        # Control button
        if flow_status in ["stopped", "idle"]:
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "▶️ 시작", "emoji": True},
                "action_id": f"streamlink_only_start_{flow_id}",
                "value": f"StreamLink:{flow_id}",
                "style": "primary",
            }
        elif flow_status == "running":
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "⏹️ 중지", "emoji": True},
                "action_id": f"streamlink_only_stop_{flow_id}",
                "value": f"StreamLink:{flow_id}",
                "style": "danger",
            }
        else:
            control_btn = {
                "type": "button",
                "text": {"type": "plain_text", "text": "ℹ️ 정보", "emoji": True},
                "action_id": f"streamlink_only_info_{flow_id}",
                "value": f"StreamLink:{flow_id}",
            }

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": flow_text},
            "accessory": control_btn,
        })
        blocks.append(create_divider_block())

        return blocks

    @classmethod
    def _create_streamlink_pagination_block(cls, page: int, total_pages: int) -> dict:
        """Create pagination controls for StreamLink dashboard."""
        elements = []

        if page > 0:
            elements.append(create_button("◀ 이전", "streamlink_only_page_prev"))

        elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": f"{page + 1} / {total_pages}"},
            "action_id": "streamlink_only_page_info",
        })

        if page < total_pages - 1:
            elements.append(create_button("다음 ▶", "streamlink_only_page_next"))

        return create_actions_block(elements)
