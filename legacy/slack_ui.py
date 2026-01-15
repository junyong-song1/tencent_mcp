"""Slack UI components using Block Kit."""
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from config import Config
from linkage_service import group_and_filter_resources

logger = logging.getLogger(__name__)

# Slack Block Kit has a limit of ~100 blocks per modal
MAX_BLOCKS_LIMIT = 95


class SlackUI:
    """Helper class to generate Slack Block Kit UI components."""

    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Get emoji for channel status."""
        status_emojis = {
            "running": ":large_green_circle:",
            "idle": ":large_yellow_circle:",
            "stopped": ":red_circle:",
            "error": ":red_circle:",
            "unknown": ":white_circle:",
        }
        return status_emojis.get(status.lower(), ":white_circle:")

    @staticmethod
    def get_task_status_emoji(status: str) -> str:
        """Get emoji for task status."""
        task_emojis = {
            "pending": ":hourglass_flowing_sand:",
            "running": ":arrows_counterclockwise:",
            "completed": ":white_check_mark:",
            "cancelled": ":no_entry_sign:",
            "failed": ":x:",
        }
        return task_emojis.get(status.lower(), ":grey_question:")

    @staticmethod
    def get_service_emoji(service: str) -> str:
        """Get emoji for service type."""
        service_emojis = {
            "StreamLive": "📡",
            "StreamLink": "🔗",
        }
        return service_emojis.get(service, "📺")

    @staticmethod
    def _group_channels(channels: List[Dict], service_filter: str = "all", status_filter: str = "all", keyword: str = "") -> List[Dict]:
        """
        Group channels into a hierarchy based on technical linkage (Endpoints/URLs).
        Delegates to linkage_service for the actual logic.
        """
        return group_and_filter_resources(channels, service_filter, status_filter, keyword)

    # Items per page (Slack has 100 block limit, each group ~2-3 blocks)
    ITEMS_PER_PAGE = 25

    @staticmethod
    def create_dashboard_modal(
        channels: List[Dict],
        service_filter: str = "all",
        status_filter: str = "all",
        keyword: str = "",
        channel_id: str = "",
        page: int = 0,
    ) -> Dict:
        """
        Create a modal view for the dashboard with pagination.

        Args:
            page: Current page number (0-indexed). Each page shows ITEMS_PER_PAGE groups.
        """
        total_count = len(channels)
        blocks = []

        # Store state in private_metadata as JSON
        metadata = json.dumps({
            "channel_id": channel_id,
            "service_filter": service_filter,
            "status_filter": status_filter,
            "keyword": keyword,
            "page": page,
            "active_tab": "channels",  # channels, schedules, status
        })
        
        # 0. Header
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                "text": "Tencent Media Dashboard",
                "emoji": False
                }
            })

        # Tab Navigation Buttons (Channels tab is active)
            blocks.append({
            "type": "actions",
            "block_id": "tab_navigation",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📺 채널", "emoji": True},
                    "style": "primary",  # Currently active
                    "value": "channels",
                    "action_id": "tab_channels"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📅 스케줄", "emoji": True},
                    "value": "schedules",
                    "action_id": "tab_schedules"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 현황", "emoji": True},
                    "value": "status",
                    "action_id": "tab_status"
                }
            ]
            })

        blocks.append({"type": "divider"})

        # 1. Statistics Cards (4 cards: Total, Running, Idle, Stream Links)
        running_count = sum(1 for c in channels if c.get("status", "").lower() == "running")
        idle_count = sum(1 for c in channels if c.get("status", "").lower() in ["idle", "stopped"])
        streamlink_count = sum(1 for c in channels if c.get("service", "") == "StreamLink")
        
            blocks.append({
                "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Streams*\n{total_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Running*\n:large_green_circle: {running_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Idle*\n:white_circle: {idle_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Stream Links*\n:link: {streamlink_count}"
                }
            ]
        })

        blocks.append({"type": "divider"})

        # 2. Search Bar
            blocks.append({
            "type": "input",
            "dispatch_action": True,
            "block_id": "search_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "dashboard_search_input",
                "placeholder": {
                        "type": "plain_text",
                    "text": "Search streams..."
                },
                "initial_value": keyword,
                "dispatch_action_config": {
                    "trigger_actions_on": ["on_enter_pressed"]
                }
            },
            "label": {
                "type": "plain_text",
                "text": " "
            }
        })

        # 3. Filter Tabs (All, Live, Link, Running, Idle)
        filter_tabs = []
        
        # Determine active tab based on filters
        active_tab = "all"
        if service_filter == "StreamLive":
            active_tab = "live"
        elif service_filter == "StreamLink":
            active_tab = "link"
        elif status_filter == "running":
            active_tab = "running"
        elif status_filter == "idle" or status_filter == "stopped":
            active_tab = "idle"
        
        tabs = [
            {"text": "All", "value": "all", "action_id": "filter_tab_all"},
            {"text": "Live", "value": "live", "action_id": "filter_tab_live"},
            {"text": "Link", "value": "link", "action_id": "filter_tab_link"},
            {"text": "Running", "value": "running", "action_id": "filter_tab_running"},
            {"text": "Idle", "value": "idle", "action_id": "filter_tab_idle"}
        ]
        
        for tab in tabs:
            is_active = active_tab == tab["value"]
            filter_tabs.append({
                "type": "button",
                "text": {"type": "plain_text", "text": tab["text"]},
                "value": tab["value"],
                "action_id": tab["action_id"],
                "style": "primary" if is_active else None
            })
        
        blocks.append({
            "type": "actions",
            "block_id": "filter_tabs",
            "elements": filter_tabs
        })

        blocks.append({"type": "divider"})

        # Hierarchical Rendering & Filtering
        hierarchy = SlackUI._group_channels(channels, service_filter, status_filter, keyword)
        
        if not hierarchy:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "No results found."}
            })
        else:
                # Pagination: calculate start and end indices
                items_per_page = SlackUI.ITEMS_PER_PAGE
                total_groups = len(hierarchy)
                total_pages = (total_groups + items_per_page - 1) // items_per_page  # ceil division

                # Ensure page is within bounds
                page = max(0, min(page, total_pages - 1)) if total_pages > 0 else 0

                start_idx = page * items_per_page
                end_idx = min(start_idx + items_per_page, total_groups)
                display_hierarchy = hierarchy[start_idx:end_idx]

            # Helper for consistent resource display (Card-style like image)
            def get_resource_blocks(res, is_child=False, child_count=0, is_expanded=False):
                # Get service type and icon
                service_text = res.get('service', 'Unknown')
                service_emoji = "🟣" if service_text == "StreamLive" else "🔵"
                
                # Get status
                status = res.get("status", "unknown").lower()
                status_emoji = ":large_green_circle:" if status == "running" else ":white_circle:"
                status_text = "Running" if status == "running" else "Idle"
                
                # Get ID (shortened)
                short_id = res['id']
                short_id_disp = (short_id[:8] + "...") if len(short_id) > 8 else short_id
                
                # Get inputs count
                input_attachments = res.get("input_attachments", [])
                if isinstance(input_attachments, list):
                    inputs_count = len(input_attachments)
                else:
                    inputs_count = int(input_attachments) if input_attachments else 0
                
                # Build text content (card-style)
                # Icon + Name + Type Tag + Status + ID + Inputs
                text_parts = []
                
                if not is_child:
                    # Parent stream - add expand/collapse indicator if has children
                    if child_count > 0:
                        expand_icon = "▼" if is_expanded else "▶"
                        text_parts.append(f"{expand_icon} ")
                    else:
                        text_parts.append(f"{service_emoji} ")
                else:
                    # Child stream - indented
                    text_parts.append("  ")
                
                text_parts.append(f"*{res['name']}*\n")
                text_parts.append(f"`{service_text}`  {status_emoji} {status_text}  `{short_id_disp}`  Inputs: {inputs_count}")
                
                if not is_child and child_count > 0:
                    text_parts.append(f"\nChild Streams: {child_count}")
                
                text = "".join(text_parts)
                
                # Build buttons
                action_value = f"{service_text}:{res['id']}"
            buttons = []

                # Main action button (Start/Stop)
                if status in ["stopped", "idle"]:
                buttons.append({
                    "type": "button",
                        "text": {"type": "plain_text", "text": "Start Stream" if not is_child else "Start"},
                    "style": "primary",
                    "value": action_value,
                        "action_id": f"start_{res['id']}"
                })
                elif status == "running":
                buttons.append({
                    "type": "button",
                        "text": {"type": "plain_text", "text": "Stop Stream" if not is_child else "Stop"},
                    "style": "danger",
                    "value": action_value,
                        "action_id": f"stop_{res['id']}"
                })

                # Bulk Action button for parent with children
                if not is_child and child_count > 0:
                buttons.append({
                    "type": "button",
                        "text": {"type": "plain_text", "text": "Bulk Action"},
                    "value": action_value,
                        "action_id": f"bulk_action_{res['id']}"
                    })
                
                # Expand/Collapse button for parent with children
                if not is_child and child_count > 0:
                    expand_action_id = f"collapse_{res['id']}" if is_expanded else f"expand_{res['id']}"
                    buttons.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": "접기" if is_expanded else "펼치기"},
                        "value": action_value,
                        "action_id": expand_action_id
                    })
                
                # Build result block
                result_blocks = []
                
                # Main section with text and buttons
                section_block = {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text}
                }
                
                # Add buttons as accessory if single button, or separate actions block if multiple
                if len(buttons) == 1:
                    section_block["accessory"] = buttons[0]
                    result_blocks.append(section_block)
                elif len(buttons) > 1:
                    result_blocks.append(section_block)
                    result_blocks.append({
                    "type": "actions",
                        "block_id": f"actions_{res['id']}",
                        "elements": buttons
                    })
                else:
                    result_blocks.append(section_block)
                
                return result_blocks

            # Render groups for current page
            # Track expanded state (for now, all expanded by default)
            expanded_resources = set()  # Can be enhanced to track per-resource expansion state
            
            for item in display_hierarchy:
                parent = item["parent"]
                children = item["children"]
                is_expanded = parent['id'] in expanded_resources or len(children) > 0  # Default to expanded

                # Add Parent (returns list of blocks)
                parent_blocks = get_resource_blocks(parent, is_child=False, child_count=len(children), is_expanded=is_expanded)
                blocks.extend(parent_blocks)

                # Add Children if expanded
                if is_expanded:
                    for child in children:
                        child_blocks = get_resource_blocks(child, is_child=True)
                        blocks.extend(child_blocks)

            # Pagination controls
            if total_pages > 1:
                pagination_elements = []

                # Previous page button
                if page > 0:
                    pagination_elements.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": "◀️ 이전", "emoji": True},
                        "value": str(page - 1),
                        "action_id": "dashboard_page_prev"
                    })

                # Page indicator (as a button that does nothing, just shows info)
                pagination_elements.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"📄 {page + 1} / {total_pages}", "emoji": True},
                    "value": "info",
                    "action_id": "dashboard_page_info"
                })

                # Next page button
                if page < total_pages - 1:
                    pagination_elements.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": "다음 ▶️", "emoji": True},
                        "value": str(page + 1),
                        "action_id": "dashboard_page_next"
                    })

            blocks.append({
                "type": "actions",
                    "block_id": "pagination_block",
                    "elements": pagination_elements
                })

                blocks.append({
                    "type": "context",
                "elements": [{
                        "type": "mrkdwn",
                        "text": f"📊 전체 {total_groups}개 그룹 중 {start_idx + 1}-{end_idx}번째 표시 중"
                    }]
                })
        
        # Bottom navigation: Showing X streams, Refresh, Close
        if hierarchy:
            total_streams_display = sum(1 + len(item["children"]) for item in hierarchy)
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Showing {total_streams_display} streams"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Refresh"},
                    "value": "refresh",
                    "action_id": "dashboard_refresh"
                }
            })

        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",
            "private_metadata": metadata,
            "title": {
                "type": "plain_text",
                "text": "Tencent Media Dashboard"
            },
            "close": {
                "type": "plain_text",
                "text": "닫기"
            },
            "blocks": blocks
        }

    @staticmethod
    def create_loading_modal(channel_id: str) -> Dict:
        """Create a skeleton loading modal to respond immediately to Slack."""
        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",
            "private_metadata": channel_id,
            "title": {
                "type": "plain_text",
                "text": "Tencent Media Dashboard"
            },
            "close": {
                "type": "plain_text",
                "text": "닫기"
            },
            "blocks": [
                {
                    "type": "image",
                    "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Tencent_Cloud_Logo.png",
                    "alt_text": "Tencent Cloud Logo"
                },
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⏳ 리소스를 불러오는 중입니다...",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "텐센트 클라우드에서 최신 정보를 가져오고 있습니다. 잠시만 기다려 주세요. (약 3~5초 소요)"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": ":arrows_counterclockwise: _상태 동기화 및 계층 구조 분석 중..._"
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def create_dashboard_blocks(
        channels: List[Dict],
        service_filter: str = "all",
        status_filter: str = "all",
        keyword: str = "",
    ) -> List[Dict]:
        """
        Create Slack blocks for the main dashboard.
        """
        blocks = []

        # 1. Header is optional if we want to save space, but keeping it for now
        # blocks.append(...) 

        # 2. Filters & Actions Row
        filter_elements = [
            {
                "type": "static_select",
                "placeholder": {"type": "plain_text", "text": "Service"},
                "options": [
                    {"text": {"type": "plain_text", "text": "All Services"}, "value": "all"},
                    {"text": {"type": "plain_text", "text": "📡 StreamLive"}, "value": "StreamLive"},
                    {"text": {"type": "plain_text", "text": "🔗 StreamLink"}, "value": "StreamLink"}
                ],
                "initial_option": next(
                    (opt for opt in [
                        {"text": {"type": "plain_text", "text": "All Services"}, "value": "all"},
                        {"text": {"type": "plain_text", "text": "📡 StreamLive"}, "value": "StreamLive"},
                        {"text": {"type": "plain_text", "text": "🔗 StreamLink"}, "value": "StreamLink"}
                    ] if opt["value"] == service_filter),
                    {"text": {"type": "plain_text", "text": "All Services"}, "value": "all"}
                ),
                "action_id": "dashboard_filter_service"
            },
            {
                "type": "static_select",
                "placeholder": {"type": "plain_text", "text": "Status"},
                "options": [
                    {"text": {"type": "plain_text", "text": "All Status"}, "value": "all"},
                    {"text": {"type": "plain_text", "text": "🟢 Running"}, "value": "running"},
                    {"text": {"type": "plain_text", "text": "🔴 Stopped"}, "value": "stopped"},
                    {"text": {"type": "plain_text", "text": "⚠️ Error"}, "value": "error"}
                ],
                "initial_option": next(
                    (opt for opt in [
                        {"text": {"type": "plain_text", "text": "All Status"}, "value": "all"},
                        {"text": {"type": "plain_text", "text": "🟢 Running"}, "value": "running"},
                        {"text": {"type": "plain_text", "text": "🔴 Stopped"}, "value": "stopped"},
                        {"text": {"type": "plain_text", "text": "⚠️ Error"}, "value": "error"}
                    ] if opt["value"] == status_filter),
                    {"text": {"type": "plain_text", "text": "All Status"}, "value": "all"}
                ),
                "action_id": "dashboard_filter_status"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔍 Search"},
                "value": "search",
                "action_id": "dashboard_search_open"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 Refresh"},
                "value": "refresh",
                "action_id": "dashboard_refresh"
            }
        ]
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🎛️ *Tencent Media Dashboard*" + (f" | 🔍 `{keyword}`" if keyword else "")
            }
        })

        blocks.append({
            "type": "actions",
            "elements": filter_elements
        })

        blocks.append({"type": "divider"})

        # 3. List Items (Compact)
        if not channels:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*검색 결과가 없습니다.* 필터를 변경해보세요."
                }
            })
        else:
            MAX_ITEMS = 10  # More compact usually means we can fit more, but Block Kit limits to ~50 blocks.
            # Each item needs 1 section + 1 divider = 2 blocks.
            display_channels = channels[:MAX_ITEMS]

            for channel in display_channels:
                status_emoji = SlackUI.get_status_emoji(channel["status"])
                service_emoji = SlackUI.get_service_emoji(channel.get("service", ""))
                
                # Action Button Logic
                accessory = None
                action_value = f"{channel.get('service', 'Unknown')}:{channel['id']}"

                if channel["status"] in ["stopped", "idle"]:
                    accessory = {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "▶️ 실행"},
                        "style": "primary",
                        "value": action_value,
                        "action_id": f"start_{channel['id']}"
                    }
                elif channel["status"] == "running":
                    accessory = {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⏹️ 중지"},
                        "style": "danger",
                        "value": action_value,
                        "action_id": f"stop_{channel['id']}"
                    }
                elif channel["status"] == "error":
                    accessory = {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔄 재시작"},
                        "value": action_value,
                        "action_id": f"restart_{channel['id']}"
                    }
                else:
                    accessory = {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "ℹ️ 정보"},
                        "value": channel['id'],
                        "action_id": f"channel_info_{channel['id']}"
                    }

                # Compact Text Layout
                # [Emoji] [Name]
                # [Status] | [ID] | [Domain/Inputs]
                
                # Make ID smaller or hidden? Let's show truncated ID.
                short_id = channel['id'][:8] + "..." if len(channel['id']) > 8 else channel['id']
                
                # Context info
                info_parts = [f"`{short_id}`"]
                input_attachments = channel.get("input_attachments", [])
                if input_attachments:
                    if isinstance(input_attachments, list):
                        inputs_count = len(input_attachments)
                        if inputs_count > 0:
                            # Input 이름 목록 생성 (최대 2개만 표시)
                            input_names = [inp.get("name", inp.get("id", "Unknown")) for inp in input_attachments[:2]]
                            input_display = f"In: {inputs_count}" + (f" ({', '.join(input_names)}" + (", ..." if inputs_count > 2 else "") + ")")
                        else:
                            input_display = f"In: 0"
                        info_parts.append(input_display)
                    else:
                        # 숫자로 저장된 경우 (하위 호환성)
                        info_parts.append(f"In: {input_attachments}")

                if channel.get("domain"):
                    # Shorten domain
                    domain = channel['domain'].replace("https://", "").replace("http://", "")[:20]
                    info_parts.append(f"Dom: {domain}")

                context_str = " | ".join(info_parts)
                
                text = (
                    f"{service_emoji} *{channel['name']}*\n"
                    f"{status_emoji} {channel['status'].upper()}  <non/existent| >  {context_str}" 
                    # Hack: <non/existent| > adds some spacing? or just use spaces. 
                    # Better: 
                    # f"{status_emoji} {channel['status'].upper()} · {context_str}"
                )
                
                section = {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text}
                }
                if accessory:
                    section["accessory"] = accessory
                
                blocks.append(section)
                # blocks.append({"type": "divider"}) # Remove divider for tighter look? Or keep. 
                # Without divider, it might look cluttered. Let's keep divider but maybe minimal?
                blocks.append({"type": "divider"})

            if len(channels) > MAX_ITEMS:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"⚠️ _...외 {len(channels) - MAX_ITEMS}개 항목이 더 있습니다. 검색을 사용하세요._"
                    }]
                })

        # 4. Footer Stats
        total_count = len(channels)
        running_count = sum(1 for c in channels if c["status"] == "running")
        error_count = sum(1 for c in channels if c["status"] == "error")

        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📊 Total: {total_count} | 🟢 Running: {running_count} | 🔴 Error: {error_count}"
            }]
        })

        return blocks

    @staticmethod
    def create_search_modal(channel_id: str, message_ts: str, current_keyword: str = "") -> Dict:
        """
        Create a modal for searching/filtering command.
        """
        return {
            "type": "modal",
            "callback_id": "dashboard_search_modal",
            "private_metadata": f"{channel_id}|{message_ts}",  # Pass context to update the message later
            "title": {
                "type": "plain_text",
                "text": "🔍 리소스 검색"
            },
            "submit": {
                "type": "plain_text",
                "text": "검색"
            },
            "close": {
                "type": "plain_text",
                "text": "취소"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "search_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "search_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "채널명, ID 키워드 입력"
                        },
                        "initial_value": current_keyword,
                        "multiline": False
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "검색어"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "입력한 키워드가 포함된 채널만 대시보드에 표시됩니다."
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def create_channel_blocks(channels: List[Dict], query: str = "") -> List[Dict]:
        """
        Legacy method kept for compatibility, now redirects to dashboard style 
        but without the interactive dashboard header (to avoid refresh confusion).
        """
        # Simply reuse the dashboard logic or keep simpler list
        return SlackUI.create_dashboard_blocks(channels)

    @staticmethod
    def create_action_result_blocks(
        channel_name: str,
        action: str,
        success: bool,
        message: str,
        new_status: str = None
    ) -> List[Dict]:
        """
        Create blocks for action result feedback.
        """
        emoji = "✅" if success else "❌"
        status_emoji = SlackUI.get_status_emoji(new_status) if new_status else ""

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {action.upper()} 결과",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*채널:* {channel_name}\n"
                        f"*작업:* {action}\n"
                        f"*결과:* {message}"
                    ),
                }
            }
        ]

        if new_status:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *새로운 상태:* {new_status.upper()}",
                }
            })

        return blocks

    @staticmethod
    def create_help_blocks() -> List[Dict]:
        """Create help message blocks."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤖 Tencent MediaBot",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*사용 가능한 명령어:*",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "• `/tencent list` - 통합 대시보드 열기 (추천)\n"
                        "• `StreamLink 목록` - 리소스 조회\n"
                        "• `[채널명] 시작/중지` - 리소스 제어\n"
                        "• `/tencent help` - 도움말\n"
                    ),
                }
            },
            {
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "Supports: 📡 StreamLive | 🔗 StreamLink"
                }]
            }
        ]

    # ... existing create_scheduled_task_blocks, create_schedule_result_blocks, create_cancel_result_blocks ...
    # (Leaving these unchanged or standardizing layout)
    # For brevity in this replacement, I'll include the methods but keep them simple or assume they exist.
    # To be safe, I'll copy them back.

    @staticmethod
    def create_scheduled_task_blocks(tasks: List[Dict]) -> List[Dict]:
        """Create Slack blocks for displaying scheduled tasks."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⏰ 예약된 작업 목록",
                }
            },
            {"type": "divider"},
        ]

        if not tasks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_예약된 작업이 없습니다._",
                }
            })
            return blocks

        for task in tasks:
            status_emoji = SlackUI.get_task_status_emoji(task["status"])
            service_emoji = SlackUI.get_service_emoji(task.get("service", ""))
            action_emoji = "▶️" if task["action"] == "start" else "⏹️"

            # ... (Logic identical to previous version) ...
            task_text = (
                f"*Task ID:* `{task['task_id']}`\n"
                f"{service_emoji} *채널:* {task['channel_name']}\n"
                f"{action_emoji} *작업:* {task['action'].upper()}\n"
                f"⏰ *예약 시간:* {task['scheduled_time']}\n"
                f"{status_emoji} *상태:* {task['status'].upper()}"
            )

            section = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": task_text},
            }
            if task["status"] == "pending":
                section["accessory"] = {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ 취소"},
                    "style": "danger",
                    "value": task["task_id"],
                    "action_id": f"cancel_task_{task['task_id']}",
                }
            blocks.append(section)
            blocks.append({"type": "divider"})

        return blocks

    @staticmethod
    def create_schedule_result_blocks(
        task_id: str,
        channel_name: str,
        action: str,
        scheduled_time: str,
        success: bool,
        message: str = ""
    ) -> List[Dict]:
        """Create blocks for schedule result feedback."""
        emoji = "✅" if success else "❌"
        action_emoji = "▶️" if action == "start" else "⏹️"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} 예약 {'완료' if success else '실패'}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*채널:* {channel_name}\n"
                        f"{action_emoji} *작업:* {action.upper()}\n"
                        f"⏰ *예약 시간:* {scheduled_time}\n"
                        f"*Task ID:* `{task_id}`"
                    ) if success else f"*오류:* {message}",
                }
            }
        ]
        return blocks

    @staticmethod
    def create_cancel_result_blocks(task_id: str, success: bool, message: str) -> List[Dict]:
        """Create blocks for cancel result feedback."""
        emoji = "✅" if success else "❌"
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} {message}",
                }
            }
        ]

    # ========== Schedule Tab UI Methods ==========

    @staticmethod
    def get_schedule_status_emoji(status: str) -> str:
        """Get emoji for schedule status."""
        status_emojis = {
            "scheduled": "🔵",
            "active": "🟢",
            "completed": "✅",
            "cancelled": "⚫",
        }
        return status_emojis.get(status.lower(), "⚪")

    @staticmethod
    def create_schedule_tab_modal(
        schedules: List[Dict],
        selected_date: str = "",
        channel_id: str = "",
        channels_for_dropdown: List[Dict] = None,
        month_view: bool = False,
    ) -> Dict:
        """
        Create a modal view for the schedule tab.

        Args:
            schedules: List of schedule dictionaries
            selected_date: Currently selected date (YYYY-MM-DD format)
            channel_id: Slack channel ID for context
            channels_for_dropdown: List of channels for the add schedule form
        """
        blocks = []

        # Use today's date if not specified
        if not selected_date:
            selected_date = datetime.now().strftime("%Y-%m-%d")

        metadata = json.dumps({
            "channel_id": channel_id,
            "active_tab": "schedules",
            "selected_date": selected_date,
        })

        # 0. Header & Logo
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔹 Tencent Media Dashboard",
                "emoji": True
            }
        })

        logo_url = "https://upload.wikimedia.org/wikipedia/commons/e/ea/Tencent_Cloud_Logo.png"
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": logo_url,
                    "alt_text": "Tencent Cloud Logo"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Official Management Console*"
                }
            ]
        })

        # Tab Navigation Buttons (Schedules tab is active)
        blocks.append({
            "type": "actions",
            "block_id": "tab_navigation",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📺 채널", "emoji": True},
                    "value": "channels",
                    "action_id": "tab_channels"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📅 스케줄", "emoji": True},
                    "style": "primary",  # Currently active
                    "value": "schedules",
                    "action_id": "tab_schedules"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 현황", "emoji": True},
                    "value": "status",
                    "action_id": "tab_status"
                }
            ]
        })

        blocks.append({"type": "divider"})

        # Schedule Header with Date Picker and Add Button
        blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                "text": "*📅 방송 스케줄 관리*"
            }
        })

        # Date picker and actions row
        blocks.append({
            "type": "actions",
            "block_id": "schedule_actions",
            "elements": [
                {
                    "type": "datepicker",
                    "action_id": "schedule_date_picker",
                    "initial_date": selected_date,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "날짜 선택"
                    }
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "➕ 스케줄 등록", "emoji": True},
                    "style": "primary",
                    "value": "add_schedule",
                    "action_id": "schedule_add_button"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔄 새로고침", "emoji": True},
                    "value": "refresh",
                    "action_id": "schedule_refresh"
                }
            ]
        })

        blocks.append({"type": "divider"})

        # Parse selected date for display
        try:
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
            if month_view:
                display_date = date_obj.strftime("%Y년 %m월")
            else:
                display_date = date_obj.strftime("%Y년 %m월 %d일")
        except:
            display_date = selected_date

        # Group schedules by date if month_view
        if month_view and schedules:
            # Group schedules by date
            schedules_by_date = {}
            for schedule in schedules:
                start_time_str = schedule.get("start_time", "")
                try:
                    if isinstance(start_time_str, str):
                        if " " in start_time_str:
                            schedule_date = datetime.strptime(start_time_str.split(" ")[0], "%Y-%m-%d").date()
                        else:
                            schedule_date = datetime.strptime(start_time_str, "%Y-%m-%d").date()
                    else:
                        schedule_date = start_time_str.date()
                except:
                    continue
                
                date_key = schedule_date.strftime("%Y-%m-%d")
                if date_key not in schedules_by_date:
                    schedules_by_date[date_key] = []
                schedules_by_date[date_key].append(schedule)
            
            # Sort dates
            sorted_dates = sorted(schedules_by_date.keys())
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{display_date} 스케줄* (총 {len(schedules)}건)"
                }
            })
            
            # Display schedules grouped by date
            for date_key in sorted_dates:
                date_schedules = schedules_by_date[date_key]
                try:
                    date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%m월 %d일 (%a)")
                except:
                    date_display = date_key
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📅 {date_display}* ({len(date_schedules)}건)"
                    }
                })
                
                for schedule in date_schedules:
                    status_emoji = SlackUI.get_schedule_status_emoji(schedule.get("status", "scheduled"))
                    service_emoji = SlackUI.get_service_emoji(schedule.get("service", ""))

                    # Time format
                    start_time = schedule.get("start_time", "")
                    end_time = schedule.get("end_time", "")

                    # Try to extract just time part if it's a datetime string
                    if " " in start_time:
                        start_time = start_time.split(" ")[1]
                    if " " in end_time:
                        end_time = end_time.split(" ")[1]

                    schedule_text = (
                        f"{status_emoji} *{schedule.get('title', 'Untitled')}*\n"
                        f"   ⏰ {start_time} ~ {end_time}\n"
                        f"   {service_emoji} {schedule.get('channel_name', 'Unknown')}\n"
                        f"   👤 <@{schedule.get('assignee_id', '')}>"
                    )

                    # Build section with optional button
                    section = {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": schedule_text}
                    }

                    # Add action button based on status
                    if schedule.get("status") == "scheduled":
                        section["accessory"] = {
                            "type": "overflow",
                            "action_id": f"schedule_menu_{schedule.get('schedule_id', '')}",
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "✏️ 수정"},
                                    "value": f"edit:{schedule.get('schedule_id', '')}"
                                },
                                {
                                    "text": {"type": "plain_text", "text": "🗑️ 삭제"},
                                    "value": f"delete:{schedule.get('schedule_id', '')}"
                                }
                            ]
                        }

                    blocks.append(section)
                
                blocks.append({"type": "divider"})
        else:
            # Single date view (original behavior)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{display_date} 스케줄* ({len(schedules)}건)"
                }
            })

            if not schedules:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_등록된 스케줄이 없습니다._"
                    }
                })
            else:
                for schedule in schedules:
                    status_emoji = SlackUI.get_schedule_status_emoji(schedule.get("status", "scheduled"))
                    service_emoji = SlackUI.get_service_emoji(schedule.get("service", ""))

                    # Time format
                    start_time = schedule.get("start_time", "")
                    end_time = schedule.get("end_time", "")

                    # Try to extract just time part if it's a datetime string
                    if " " in start_time:
                        start_time = start_time.split(" ")[1]
                    if " " in end_time:
                        end_time = end_time.split(" ")[1]

                    schedule_text = (
                        f"{status_emoji} *{schedule.get('title', 'Untitled')}*\n"
                        f"   ⏰ {start_time} ~ {end_time}\n"
                        f"   {service_emoji} {schedule.get('channel_name', 'Unknown')}\n"
                        f"   👤 <@{schedule.get('assignee_id', '')}>"
                    )

                    # Build section with optional button
                    section = {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": schedule_text}
                    }

                    # Add action button based on status
                    if schedule.get("status") == "scheduled":
                        section["accessory"] = {
                            "type": "overflow",
                            "action_id": f"schedule_menu_{schedule.get('schedule_id', '')}",
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "✏️ 수정"},
                                    "value": f"edit:{schedule.get('schedule_id', '')}"
                                },
                                {
                                    "text": {"type": "plain_text", "text": "🗑️ 삭제"},
                                    "value": f"delete:{schedule.get('schedule_id', '')}"
                                }
                            ]
                        }

                    blocks.append(section)
                    blocks.append({"type": "divider"})

        # Footer with summary
        scheduled_count = sum(1 for s in schedules if s.get("status") == "scheduled")
        active_count = sum(1 for s in schedules if s.get("status") == "active")
        completed_count = sum(1 for s in schedules if s.get("status") == "completed")

        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📊 예정: {scheduled_count} | 진행중: {active_count} | 완료: {completed_count}"
            }]
        })

        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",  # Use same callback_id as dashboard for tab navigation
            "private_metadata": metadata,
            "title": {
                "type": "plain_text",
                "text": "Tencent Media Dashboard"
            },
            "close": {
                "type": "plain_text",
                "text": "닫기"
            },
            "blocks": blocks
        }

    @staticmethod
    def create_schedule_add_modal(
        channels: List[Dict],
        parent_metadata: str = "",
        selected_date: str = "",
    ) -> Dict:
        """
        Create a modal for adding a new broadcast schedule.

        Args:
            channels: List of available channels for dropdown
            parent_metadata: Metadata from parent modal to preserve state
            selected_date: Pre-selected date (YYYY-MM-DD format)
        """
        if not selected_date:
            selected_date = datetime.now().strftime("%Y-%m-%d")

        # Default times
        default_start_time = "18:00"
        default_end_time = "21:00"

        # Build channel options for dropdown (StreamLive only)
        channel_options = []
        streamlive_channels = [ch for ch in channels if ch.get("service") == "StreamLive"]
        for ch in streamlive_channels[:100]:  # Slack limit
            channel_options.append({
                "text": {
                    "type": "plain_text",
                    "text": f"{ch.get('name', 'Unknown')[:70]}"
                },
                "value": f"StreamLive:{ch.get('id', '')}"
            })

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📅 방송 스케줄 등록",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "schedule_title_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "schedule_title_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "예: KBO 개막전 생중계"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "방송 제목"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_channel_block",
                "element": {
                    "type": "static_select",
                    "action_id": "schedule_channel_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "채널 선택"
                    },
                    "options": channel_options if channel_options else [
                        {"text": {"type": "plain_text", "text": "채널 없음"}, "value": "none"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "방송 채널"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_start_date_block",
                "element": {
                    "type": "datepicker",
                    "action_id": "schedule_start_date_input",
                    "initial_date": selected_date,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "시작 날짜 선택"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "시작 날짜"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_start_time_block",
                "element": {
                    "type": "timepicker",
                    "action_id": "schedule_start_time_input",
                    "initial_time": default_start_time,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "시작 시간"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "시작 시간"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_end_date_block",
                "element": {
                    "type": "datepicker",
                    "action_id": "schedule_end_date_input",
                    "initial_date": selected_date,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "종료 날짜 선택"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "종료 날짜"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_end_time_block",
                "element": {
                    "type": "timepicker",
                    "action_id": "schedule_end_time_input",
                    "initial_time": default_end_time,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "종료 시간"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "종료 시간"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_assignee_block",
                "element": {
                    "type": "users_select",
                    "action_id": "schedule_assignee_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "담당자 선택"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "담당자"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_options_block",
                "optional": True,
                "element": {
                    "type": "checkboxes",
                    "action_id": "schedule_options_input",
                    "initial_options": [
                        {"text": {"type": "plain_text", "text": "2시간 전 알림"}, "value": "notify_2h"},
                        {"text": {"type": "plain_text", "text": "30분 전 알림 (상태 체크)"}, "value": "notify_30m"},
                    ],
                    "options": [
                        {"text": {"type": "plain_text", "text": "2시간 전 알림"}, "value": "notify_2h"},
                        {"text": {"type": "plain_text", "text": "30분 전 알림 (상태 체크)"}, "value": "notify_30m"},
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "옵션"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_repeat_block",
                "optional": True,
                "element": {
                    "type": "static_select",
                    "action_id": "schedule_repeat_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "반복 없음"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "반복 없음"}, "value": "none"},
                        {"text": {"type": "plain_text", "text": "매일"}, "value": "daily"},
                        {"text": {"type": "plain_text", "text": "매주 (같은 요일)"}, "value": "weekly"},
                        {"text": {"type": "plain_text", "text": "매월 (같은 날짜)"}, "value": "monthly"},
                    ],
                    "initial_option": {"text": {"type": "plain_text", "text": "반복 없음"}, "value": "none"}
                },
                "label": {
                    "type": "plain_text",
                    "text": "반복 주기"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_repeat_count_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "schedule_repeat_count_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "예: 10 (10회 반복) 또는 2026-01-31 (종료 날짜)"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "반복 횟수/종료일"
                },
                "hint": {
                    "type": "plain_text",
                    "text": "숫자(반복 횟수) 또는 날짜(YYYY-MM-DD) 형식"
                }
            },
            {
                "type": "input",
                "block_id": "schedule_notes_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "schedule_notes_input",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "메모 (선택사항)"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "메모"
                }
            }
        ]

        return {
            "type": "modal",
            "callback_id": "schedule_add_modal_submit",
            "private_metadata": parent_metadata,
            "title": {
                "type": "plain_text",
                "text": "스케줄 등록"
            },
            "submit": {
                "type": "plain_text",
                "text": "등록"
            },
            "close": {
                "type": "plain_text",
                "text": "취소"
            },
            "blocks": blocks
        }

    @staticmethod
    def create_status_tab_modal(
        channels: List[Dict],
        schedules_today: List[Dict],
        schedules_upcoming: List[Dict],
        channel_id: str = "",
    ) -> Dict:
        """
        Create a modal view for the status/overview tab.

        Args:
            channels: List of all channels
            schedules_today: Today's schedules
            schedules_upcoming: Upcoming schedules (next 24h)
            channel_id: Slack channel ID
        """
        blocks = []

        metadata = json.dumps({
            "channel_id": channel_id,
            "active_tab": "status",
        })

        # 0. Header & Logo
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔹 Tencent Media Dashboard",
                "emoji": True
            }
        })

        logo_url = "https://upload.wikimedia.org/wikipedia/commons/e/ea/Tencent_Cloud_Logo.png"
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": logo_url,
                    "alt_text": "Tencent Cloud Logo"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Official Management Console*"
                }
            ]
        })

        # Tab Navigation Buttons (Status tab is active)
        blocks.append({
            "type": "actions",
            "block_id": "tab_navigation",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📺 채널", "emoji": True},
                    "value": "channels",
                    "action_id": "tab_channels"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📅 스케줄", "emoji": True},
                    "value": "schedules",
                    "action_id": "tab_schedules"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 현황", "emoji": True},
                    "style": "primary",  # Currently active
                    "value": "status",
                    "action_id": "tab_status"
                }
            ]
        })

        blocks.append({"type": "divider"})

        # Channel Statistics
        total_channels = len(channels)
        running_channels = sum(1 for c in channels if c.get("status") == "running")
        stopped_channels = sum(1 for c in channels if c.get("status") in ["stopped", "idle"])
        error_channels = sum(1 for c in channels if c.get("status") == "error")

        streamlive_count = sum(1 for c in channels if c.get("service") == "StreamLive")
        streamlink_count = sum(1 for c in channels if c.get("service") == "StreamLink")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 채널 현황*"
            }
        })

        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*전체 채널*\n{total_channels}개"},
                {"type": "mrkdwn", "text": f"*🟢 실행중*\n{running_channels}개"},
                {"type": "mrkdwn", "text": f"*🔴 중지됨*\n{stopped_channels}개"},
                {"type": "mrkdwn", "text": f"*⚠️ 에러*\n{error_channels}개"},
            ]
        })

        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*📡 StreamLive*\n{streamlive_count}개"},
                {"type": "mrkdwn", "text": f"*🔗 StreamLink*\n{streamlink_count}개"},
            ]
        })

        blocks.append({"type": "divider"})

        # Today's Schedule Summary
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📅 오늘의 스케줄* ({len(schedules_today)}건)"
            }
        })

        if not schedules_today:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "_오늘 예정된 스케줄이 없습니다._"}]
            })
        else:
            for schedule in schedules_today[:5]:
                status_emoji = SlackUI.get_schedule_status_emoji(schedule.get("status", "scheduled"))
                start_time = schedule.get("start_time", "")
                if " " in start_time:
                    start_time = start_time.split(" ")[1]
                blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                        "text": f"{status_emoji} *{start_time}* | {schedule.get('title', 'Untitled')} | <@{schedule.get('assignee_id', '')}>"
                    }]
                })

            if len(schedules_today) > 5:
                blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"_...외 {len(schedules_today) - 5}건_"}]
                })

        blocks.append({"type": "divider"})

        # Upcoming Schedule (Next 24h)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⏰ 다가오는 스케줄 (24시간 내)* ({len(schedules_upcoming)}건)"
            }
        })

        if not schedules_upcoming:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "_24시간 내 예정된 스케줄이 없습니다._"}]
            })
        else:
            for schedule in schedules_upcoming[:5]:
                status_emoji = SlackUI.get_schedule_status_emoji(schedule.get("status", "scheduled"))
                start_time = schedule.get("start_time", "")
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"{status_emoji} *{start_time}* | {schedule.get('title', 'Untitled')} | <@{schedule.get('assignee_id', '')}>"
                    }]
                })

            if len(schedules_upcoming) > 5:
                blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"_...외 {len(schedules_upcoming) - 5}건_"}]
                })

        # Refresh button
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔄 새로고침", "emoji": True},
                    "value": "refresh",
                    "action_id": "status_refresh"
                }
            ]
        })

        return {
            "type": "modal",
            "callback_id": "dashboard_modal_view",  # Use same callback_id as dashboard for tab navigation
            "private_metadata": metadata,
            "title": {
                "type": "plain_text",
                "text": "Tencent Media Dashboard"
            },
            "close": {
                "type": "plain_text",
                "text": "닫기"
            },
            "blocks": blocks
        }

    @staticmethod
    def create_schedule_notification_blocks(
        schedule: Dict,
        notification_type: str,
        channel_status: str = None,
    ) -> List[Dict]:
        """
        Create blocks for schedule notification message.

        Args:
            schedule: Schedule dictionary
            notification_type: "2h" or "30m"
            channel_status: Current channel status (for 30m notification)
        """
        service_emoji = SlackUI.get_service_emoji(schedule.get("service", ""))

        if notification_type == "2h":
            header_text = "⏰ 방송 2시간 전 알림"
            time_text = "2시간 후"
        else:
            header_text = "⚠️ 방송 30분 전 알림"
            time_text = "30분 후"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{schedule.get('title', 'Untitled')}* 방송이 {time_text} 시작됩니다!\n\n"
                        f"📅 *시간:* {schedule.get('start_time', '')} ~ {schedule.get('end_time', '')}\n"
                        f"{service_emoji} *채널:* {schedule.get('channel_name', 'Unknown')}\n"
                        f"👤 *담당자:* <@{schedule.get('assignee_id', '')}>"
                    )
                }
            }
        ]

        # Add channel status for 30m notification
        if notification_type == "30m" and channel_status:
            status_emoji = SlackUI.get_status_emoji(channel_status)
            status_text = f"현재 채널 상태: {status_emoji} {channel_status.upper()}"

            if channel_status not in ["running"]:
                status_text += "\n⚠️ *채널이 아직 실행되지 않았습니다!*"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": status_text
                }
            })

        return blocks
