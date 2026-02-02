"""Control action handlers (start/stop/restart)."""
import json
import logging
import re
import threading
from typing import Dict, Optional

from slack_bolt import App

from app.config import get_settings
from app.slack.ui.dashboard import DashboardUI

logger = logging.getLogger(__name__)


def _check_streamlive_permission(user_id: str, service_type: str, client, channel_id: str) -> bool:
    """Check if user has permission to control StreamLive.

    Args:
        user_id: Slack user ID
        service_type: Service type (StreamLive, StreamLink, etc.)
        client: Slack client
        channel_id: Channel ID for sending error message

    Returns:
        True if user has permission, False otherwise
    """
    settings = get_settings()

    # StreamLink control is allowed for everyone
    if service_type not in ["StreamLive", "MediaLive"]:
        return True

    # Check if user is in streamlink_only list
    if settings.is_streamlink_only_user(user_id):
        if channel_id:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=":no_entry: StreamLive 채널 제어 권한이 없습니다.\n"
                     "StreamLink flow만 시작/중지할 수 있습니다.\n"
                     "(메인/백업 전환을 위해 StreamLink를 제어해 주세요)",
            )
        return False

    return True


def _format_input_status_brief(input_status: Optional[Dict]) -> str:
    """Format input status as brief one-line summary for '상태 확인' view.

    Only shows main/backup status when log-based detection is available (most reliable).
    """
    if not input_status:
        return ""

    # Only show input status if we have log-based detection (most reliable)
    log_detection = input_status.get("log_based_detection")
    if not log_detection or not log_detection.get("last_event_type"):
        # No reliable log-based data - don't show potentially incorrect info
        return ""

    active_input = input_status.get("active_input")
    if active_input:
        emoji = ":large_green_circle:" if active_input == "main" else ":warning:"
        last_event = log_detection.get("last_event_type", "")
        return f"\n   입력: {emoji} {active_input.upper()} (로그 기반: {last_event})"

    return ""


def _format_input_status_text(input_status: Optional[Dict]) -> str:
    """Format input status information for display.

    Only shows main/backup status when log-based detection is available (most reliable).
    Other info (failover config, logs) is shown regardless.

    Args:
        input_status: Result from get_channel_input_status()

    Returns:
        Formatted text string for Slack message
    """
    if not input_status:
        return ""

    text_parts = []
    active_input = input_status.get("active_input")
    secondary_input_id = input_status.get("secondary_input_id")
    is_input_source_redundancy = input_status.get("is_input_source_redundancy", False)
    failover_loss_threshold = input_status.get("failover_loss_threshold")
    failover_recover_behavior = input_status.get("failover_recover_behavior")
    log_detection = input_status.get("log_based_detection")

    # Check if we have reliable log-based detection
    has_log_detection = log_detection and log_detection.get("last_event_type")

    # Show input status ONLY if we have log-based detection (most reliable)
    if has_log_detection and active_input:
        # Main emoji based on active input
        if active_input == "main":
            active_emoji = ":large_green_circle:"
        else:  # backup
            active_emoji = ":warning:"

        text_parts.append(f"\n\n{active_emoji} *입력 상태*: {active_input.upper()}")

        if input_status.get("active_input_name"):
            text_parts.append(f" ({input_status.get('active_input_name')})")

        text_parts.append(" [로그 기반]")

        # Show log-based detection info
        last_event = log_detection.get("last_event_type")
        last_time = log_detection.get("last_event_time", "")
        failover_count = log_detection.get("failover_count", 0)

        if last_event:
            # Format time (remove seconds for brevity)
            if last_time and "T" in last_time:
                last_time = last_time.replace("T", " ").replace("Z", " UTC")[:19]

            event_emoji = ":arrows_counterclockwise:" if last_event == "PipelineFailover" else ":arrow_right:"
            text_parts.append(f"\n   {event_emoji} 마지막 이벤트: {last_event}")
            if last_time:
                text_parts.append(f" ({last_time})")

            if failover_count > 0:
                text_parts.append(f"\n   :chart_with_upwards_trend: 24h 내 Failover: {failover_count}회")

    # Always show failover configuration info (this is factual, not inferred)
    config_parts = []

    # Show failover mode summary
    if is_input_source_redundancy:
        config_parts.append("Input Source Redundancy")
    elif secondary_input_id:
        config_parts.append("Channel-level Failover")

    # Show failover policy details when available
    if failover_loss_threshold is not None:
        config_parts.append(f"LossThreshold {failover_loss_threshold}ms")
    if failover_recover_behavior:
        config_parts.append(f"Recover {failover_recover_behavior}")

    if config_parts:
        if not text_parts:
            text_parts.append("\n\n*Failover 구성*")
        else:
            text_parts.append("\n   구성: " + " / ".join(config_parts[:2]))
            if len(config_parts) > 2:
                text_parts.append(f"\n   정책: {' / '.join(config_parts[2:])}")

    return "".join(text_parts)


def register(app: App, services):
    """Register control action handlers."""

    def extract_modal_filter_state(view: dict) -> dict:
        """Extract filter state from modal view."""
        filters = view.get("state", {}).get("values", {}).get("dashboard_filters", {})
        search_block = view.get("state", {}).get("values", {}).get("search_block", {})

        private_metadata = view.get("private_metadata", "")
        channel_id = ""
        page = 0

        try:
            metadata = json.loads(private_metadata)
            channel_id = metadata.get("channel_id", "")
            page = metadata.get("page", 0)
        except (json.JSONDecodeError, TypeError):
            channel_id = private_metadata

        service_filter = "all"
        status_filter = "all"
        keyword = ""

        if "dashboard_filter_service" in filters:
            selected = filters["dashboard_filter_service"].get("selected_option")
            if selected:
                service_filter = selected.get("value", "all")

        if "dashboard_filter_status" in filters:
            selected = filters["dashboard_filter_status"].get("selected_option")
            if selected:
                status_filter = selected.get("value", "all")

        if "dashboard_search_input" in search_block:
            keyword = search_block["dashboard_search_input"].get("value") or ""

        return {
            "view_id": view.get("id"),
            "channel_id": channel_id,
            "service_filter": service_filter,
            "status_filter": status_filter,
            "keyword": keyword,
            "page": page,
        }

    def async_update_modal(client, state, clear_cache=False):
        """Update modal asynchronously."""
        def _update():
            try:
                if clear_cache:
                    services.tencent_client.clear_cache()

                channels = services.tencent_client.list_all_resources()
                modal_view = DashboardUI.create_dashboard_modal(
                    channels=channels,
                    service_filter=state["service_filter"],
                    status_filter=state["status_filter"],
                    keyword=state["keyword"],
                    channel_id=state["channel_id"],
                    page=state["page"],
                )
                client.views_update(view_id=state["view_id"], view=modal_view)
            except Exception as e:
                logger.error(f"Async modal update failed: {e}")

        threading.Thread(target=_update, daemon=True).start()

    @app.action(re.compile(r"resource_menu_.*"))
    def handle_resource_menu(ack, body, client, logger):
        """Handle resource overflow menu actions."""
        ack()

        action = body["actions"][0]
        
        # Handle both overflow menu and static select
        if "selected_option" in action:
            selected_value = action["selected_option"]["value"]
        elif "value" in action:
            # Fallback for other action types
            selected_value = action["value"]
        else:
            logger.warning(f"Unknown action format: {action}")
            return

        # Parse action:service:resource_id
        parts = selected_value.split(":")
        if len(parts) < 3:
            logger.error(f"Invalid menu value: {selected_value}")
            return

        action_type = parts[0]
        service_type = parts[1]
        resource_id = ":".join(parts[2:])

        view = body["view"]
        state = extract_modal_filter_state(view)
        channel_id = state["channel_id"]
        user_id = body["user"]["id"]

        if action_type == "info":
            details = services.tencent_client.get_resource_details(resource_id, service_type)
            if details:
                text = (
                    f"*{details.get('name', 'Unknown')}*\n"
                    f"ID: `{details.get('id', '')}`\n"
                    f"서비스: {details.get('service', '')}\n"
                    f"상태: {details.get('status', 'unknown')}"
                )

                # For StreamLive channels, also show input status
                if service_type in ["StreamLive", "MediaLive"]:
                    input_status = services.tencent_client.get_channel_input_status(resource_id)
                    text += _format_input_status_text(input_status)
            else:
                text = "리소스 정보를 가져올 수 없습니다."

            client.chat_postEphemeral(
                channel=channel_id or body.get("channel", {}).get("id", ""),
                user=user_id,
                text=text,
            )
            return

        # Handle integrated control (start_all, stop_all)
        is_integrated = action_type in ["start_all", "stop_all"]
        base_action = action_type.replace("_all", "")  # start_all -> start

        # Check permission for StreamLive control
        if action_type in ["start", "stop", "restart", "start_all", "stop_all"]:
            if not _check_streamlive_permission(user_id, service_type, client, channel_id):
                return

        # Get all resources and find the parent + children
        all_resources = services.tencent_client.list_all_resources()
        parent_resource = None
        linked_children = []

        for res in all_resources:
            if res.get("id") == resource_id:
                parent_resource = res
                break

        resource_name = parent_resource.get("name", resource_id) if parent_resource else resource_id

        # Find linked children if integrated action
        if is_integrated and parent_resource:
            from app.services.linkage import group_and_filter_resources
            hierarchy = group_and_filter_resources(all_resources, "all", "all", "")
            for group in hierarchy:
                if group["parent"].get("id") == resource_id:
                    linked_children = group["children"]
                    break

        # Send initial message
        if channel_id:
            if is_integrated and linked_children:
                child_names = ", ".join([c.get("name", c.get("id", ""))[:20] for c in linked_children[:3]])
                if len(linked_children) > 3:
                    child_names += f" 외 {len(linked_children) - 3}개"
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{user_id}> requested *통합 {base_action.upper()}* on `{resource_name}` + {len(linked_children)} linked resources ({child_names})...",
                )
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{user_id}> requested *{base_action.upper()}* on `{resource_name}` (`{resource_id}`)...",
                )

        # Execute control on parent
        result = services.tencent_client.control_resource(resource_id, service_type, base_action)
        success = result.get("success", False)
        message = result.get("message", "Unknown error")

        result_icon = ":white_check_mark:" if success else ":x:"
        results_summary = [f"{result_icon} `{resource_name}`: {message}"]

        # Execute on children if integrated
        if is_integrated and linked_children:
            for child in linked_children:
                child_id = child.get("id", "")
                child_service = child.get("service", "")
                child_name = child.get("name", child_id)

                child_result = services.tencent_client.control_resource(child_id, child_service, base_action)
                child_success = child_result.get("success", False)
                child_msg = child_result.get("message", "Unknown")
                child_icon = ":white_check_mark:" if child_success else ":x:"
                results_summary.append(f"{child_icon} `{child_name}`: {child_msg}")

        # Send result message
        if channel_id:
            if is_integrated and linked_children:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"*통합 {base_action.upper()}* 결과:\n" + "\n".join(results_summary),
                )
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"{result_icon} *{base_action.upper()}* `{resource_name}`: {message}",
                )

        async_update_modal(client, state, clear_cache=True)

    @app.action(re.compile(r"parent_(start|stop|info)_.*"))
    def handle_parent_control(ack, body, client, logger):
        """Handle parent resource individual control buttons."""
        ack()

        action_data = body["actions"][0]
        action_id = action_data["action_id"]
        value = action_data.get("value", "")

        view = body["view"]
        state = extract_modal_filter_state(view)
        channel_id = state["channel_id"]
        user_id = body["user"]["id"]

        # Parse action_id: parent_start_RESOURCEID
        parts = action_id.split("_")
        action_type = parts[1]  # start, stop, or info

        # Parse value: service:resource_id
        service_type = ""
        resource_id = ""
        if ":" in value:
            value_parts = value.split(":")
            service_type = value_parts[0]
            resource_id = ":".join(value_parts[1:])

        # Get resource name
        resource_name = resource_id
        try:
            details = services.tencent_client.get_resource_details(resource_id, service_type)
            if details and details.get("name"):
                resource_name = details["name"]
        except Exception:
            pass

        if action_type == "info":
            details = services.tencent_client.get_resource_details(resource_id, service_type)
            if details:
                text = (
                    f"*{details.get('name', 'Unknown')}*\n"
                    f"ID: `{details.get('id', '')}`\n"
                    f"서비스: {details.get('service', '')}\n"
                    f"상태: {details.get('status', 'unknown')}"
                )

                # For StreamLive channels, also show input status
                if service_type in ["StreamLive", "MediaLive"]:
                    input_status = services.tencent_client.get_channel_input_status(resource_id)
                    text += _format_input_status_text(input_status)
            else:
                text = "리소스 정보를 가져올 수 없습니다."

            client.chat_postEphemeral(
                channel=channel_id or body.get("channel", {}).get("id", ""),
                user=user_id,
                text=text,
            )
            return

        # Check permission for StreamLive control
        if not _check_streamlive_permission(user_id, service_type, client, channel_id):
            return

        # Start/Stop action
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> requested *{action_type.upper()}* on `{resource_name}`...",
            )

        result = services.tencent_client.control_resource(resource_id, service_type, action_type)
        success = result.get("success", False)
        message = result.get("message", "Unknown error")

        result_icon = ":white_check_mark:" if success else ":x:"
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"{result_icon} *{action_type.upper()}* `{resource_name}`: {message}",
            )

        async_update_modal(client, state, clear_cache=True)

    @app.action(re.compile(r"integrated_(start|stop)_.*"))
    def handle_integrated_control(ack, body, client, logger):
        """Handle integrated start/stop buttons."""
        ack()

        action_data = body["actions"][0]
        action_id = action_data["action_id"]
        value = action_data.get("value", "")

        view = body["view"]
        state = extract_modal_filter_state(view)
        channel_id = state["channel_id"]
        user_id = body["user"]["id"]

        # Parse action_id: integrated_start_RESOURCEID
        parts = action_id.split("_")
        action_type = parts[1]  # start or stop

        # Parse value: service:resource_id
        service_type = ""
        resource_id = ""
        if ":" in value:
            value_parts = value.split(":")
            service_type = value_parts[0]
            resource_id = ":".join(value_parts[1:])

        # Check permission for StreamLive control (integrated control always affects StreamLive parent)
        if not _check_streamlive_permission(user_id, service_type, client, channel_id):
            return

        # Get all resources and find the parent + children
        all_resources = services.tencent_client.list_all_resources()
        parent_resource = None
        linked_children = []

        for res in all_resources:
            if res.get("id") == resource_id:
                parent_resource = res
                break

        resource_name = parent_resource.get("name", resource_id) if parent_resource else resource_id

        # Find linked children
        from app.services.linkage import group_and_filter_resources
        hierarchy = group_and_filter_resources(all_resources, "all", "all", "")
        for group in hierarchy:
            if group["parent"].get("id") == resource_id:
                linked_children = group["children"]
                break

        # Send initial message
        if channel_id:
            child_names = ", ".join([c.get("name", c.get("id", ""))[:20] for c in linked_children[:3]])
            if len(linked_children) > 3:
                child_names += f" 외 {len(linked_children) - 3}개"
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> requested *통합 {action_type.upper()}* on `{resource_name}` + {len(linked_children)} linked resources ({child_names})...",
            )

        # Execute control on parent
        result = services.tencent_client.control_resource(resource_id, service_type, action_type)
        success = result.get("success", False)
        message = result.get("message", "Unknown error")

        result_icon = ":white_check_mark:" if success else ":x:"
        results_summary = [f"{result_icon} `{resource_name}`: {message}"]

        # Execute on children
        for child in linked_children:
            child_id = child.get("id", "")
            child_service = child.get("service", "")
            child_name = child.get("name", child_id)

            child_result = services.tencent_client.control_resource(child_id, child_service, action_type)
            child_success = child_result.get("success", False)
            child_msg = child_result.get("message", "Unknown")
            child_icon = ":white_check_mark:" if child_success else ":x:"
            results_summary.append(f"{child_icon} `{child_name}`: {child_msg}")

        # Send result message
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"*통합 {action_type.upper()}* 결과:\n" + "\n".join(results_summary),
            )

        async_update_modal(client, state, clear_cache=True)

    @app.action(re.compile(r"child_(start|stop|info)_.*"))
    def handle_child_control(ack, body, client, logger):
        """Handle child resource control buttons."""
        ack()

        action_data = body["actions"][0]
        action_id = action_data["action_id"]
        value = action_data.get("value", "")

        view = body["view"]
        state = extract_modal_filter_state(view)
        channel_id = state["channel_id"]
        user_id = body["user"]["id"]

        # Parse action_id: child_start_RESOURCEID or child_stop_RESOURCEID
        parts = action_id.split("_")
        action_type = parts[1]  # start, stop, or info

        # Parse value: service:resource_id
        service_type = ""
        resource_id = ""
        if ":" in value:
            value_parts = value.split(":")
            service_type = value_parts[0]
            resource_id = ":".join(value_parts[1:])

        # Get resource name
        resource_name = resource_id
        try:
            details = services.tencent_client.get_resource_details(resource_id, service_type)
            if details and details.get("name"):
                resource_name = details["name"]
        except Exception:
            pass

        if action_type == "info":
            details = services.tencent_client.get_resource_details(resource_id, service_type)
            if details:
                text = (
                    f"*{details.get('name', 'Unknown')}*\n"
                    f"ID: `{details.get('id', '')}`\n"
                    f"서비스: {details.get('service', '')}\n"
                    f"상태: {details.get('status', 'unknown')}"
                )

                # For StreamLive channels, also show input status
                if service_type in ["StreamLive", "MediaLive"]:
                    input_status = services.tencent_client.get_channel_input_status(resource_id)
                    text += _format_input_status_text(input_status)
            else:
                text = "리소스 정보를 가져올 수 없습니다."

            client.chat_postEphemeral(
                channel=channel_id or body.get("channel", {}).get("id", ""),
                user=user_id,
                text=text,
            )
            return

        # Start/Stop action
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> requested *{action_type.upper()}* on `{resource_name}`...",
            )

        result = services.tencent_client.control_resource(resource_id, service_type, action_type)
        success = result.get("success", False)
        message = result.get("message", "Unknown error")

        result_icon = ":white_check_mark:" if success else ":x:"
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"{result_icon} *{action_type.upper()}* `{resource_name}`: {message}",
            )

        async_update_modal(client, state, clear_cache=True)

    @app.action(re.compile(r"(start|stop|restart)_.*"))
    def handle_control_action(ack, body, client, logger):
        """Handle direct control buttons."""
        ack()

        action_data = body["actions"][0]
        action_id = action_data["action_id"]
        value = action_data.get("value", "")

        view = body["view"]
        state = extract_modal_filter_state(view)
        channel_id = state["channel_id"]
        user_id = body["user"]["id"]

        action_type = action_id.split("_")[0]
        target_id = "_".join(action_id.split("_")[1:])

        service_type = None
        if ":" in value:
            parts = value.split(":")
            if len(parts) >= 2:
                service_type = parts[0]
                target_id = ":".join(parts[1:])

        resource_name = target_id
        try:
            if service_type:
                details = services.tencent_client.get_resource_details(target_id, service_type)
                if details and details.get("name"):
                    resource_name = details["name"]
            else:
                all_resources = services.tencent_client.list_all_resources()
                for res in all_resources:
                    if res.get("id") == target_id:
                        resource_name = res.get("name", target_id)
                        service_type = res.get("service")
                        break
        except Exception:
            pass

        # Check permission for StreamLive control
        if service_type and not _check_streamlive_permission(user_id, service_type, client, channel_id):
            return

        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> requested *{action_type.upper()}* on `{resource_name}`...",
            )

        result = services.tencent_client.control_resource(target_id, service_type or "", action_type)
        success = result.get("success", False)
        message = result.get("message", "Unknown error")

        result_icon = ":white_check_mark:" if success else ":x:"
        if channel_id:
            client.chat_postMessage(
                channel=channel_id,
                text=f"{result_icon} *{action_type.upper()}* `{resource_name}`: {message}",
            )

        async_update_modal(client, state, clear_cache=True)

    # Alert notification button handlers
    @app.action("alert_status_check")
    def handle_alert_status_check(ack, body, client, logger):
        """Handle '상태 확인' button: concise status overview only."""
        ack()
        
        try:
            action = body["actions"][0]
            value = action.get("value", "")
            
            if ":" not in value:
                return
            parts = value.split(":")
            service_type = parts[0]
            channel_id = ":".join(parts[1:])
            user_id = body["user"]["id"]
            channel = body.get("channel", {}).get("id", "")
            
            details = services.tencent_client.get_resource_details(channel_id, service_type)
            if not details:
                client.chat_postEphemeral(channel=channel, user=user_id, text=f"채널 `{channel_id}` 정보를 가져올 수 없습니다.")
                return
            
            name = details.get("name", "Unknown")
            status = details.get("status", "unknown")
            status_emoji = ":large_green_circle:" if status == "running" else ":red_circle:" if status in ("stopped", "error") else ":large_yellow_circle:"
            
            # 상태 확인: 요약만 (이름, 서비스, 상태, 입력 한 줄)
            text = (
                f"*{name} 상태 요약*\n"
                f"   서비스: {details.get('service', '')} | 상태: {status_emoji} {status}"
            )
            if service_type in ["StreamLive", "MediaLive"]:
                input_status = services.tencent_client.get_channel_input_status(channel_id)
                text += _format_input_status_brief(input_status)
            text += f"\n   ID: `{details.get('id', '')}`"
            
            client.chat_postEphemeral(channel=channel, user=user_id, text=text)
        except Exception as e:
            logger.error(f"Error handling alert status check: {e}", exc_info=True)

    @app.action("alert_channel_detail")
    def handle_alert_channel_detail(ack, body, client, logger):
        """Handle '채널 상세' button: full details (input status, verification, failover, logs, SP/CSS)."""
        ack()
        
        try:
            action = body["actions"][0]
            value = action.get("value", "")
            
            if ":" not in value:
                return
            parts = value.split(":")
            service_type = parts[0]
            channel_id = ":".join(parts[1:])
            user_id = body["user"]["id"]
            channel = body.get("channel", {}).get("id", "")
            
            details = services.tencent_client.get_resource_details(channel_id, service_type)
            if not details:
                client.chat_postEphemeral(channel=channel, user=user_id, text=f"채널 `{channel_id}` 상세 정보를 가져올 수 없습니다.")
                return
            
            name = details.get("name", "Unknown")
            text = (
                f"*{name} 상세 정보*\n"
                f"ID: `{details.get('id', '')}`\n"
                f"서비스: {details.get('service', '')}\n"
                f"상태: {details.get('status', 'unknown')}"
            )
            
            # 채널 상세: 전체 입력/검증/구성/정책/이벤트/StreamPackage/CSS
            if service_type in ["StreamLive", "MediaLive"]:
                input_status = services.tencent_client.get_channel_input_status(channel_id)
                text += _format_input_status_text(input_status)
                if input_status:
                    verification_sources = input_status.get("verification_sources", [])
                    if verification_sources:
                        text += f"\n\n*검증 소스:* {', '.join(verification_sources)}"
                
                # 최근 채널 로그 (24h, 최근 N건)
                try:
                    logs = services.tencent_client.get_streamlive_channel_logs(channel_id, hours=24)
                    if logs:
                        text += "\n\n*최근 로그 (24h)*"
                        for entry in logs[:8]:  # 최근 8건
                            ev = entry.get("event_type", "")
                            tm = entry.get("time", "") or entry.get("timestamp", "")
                            pipe = entry.get("pipeline", "")
                            msg = (entry.get("message", "") or "")[:50]
                            if "T" in str(tm):
                                tm = str(tm).replace("T", " ").replace("Z", "")[:16]
                            text += f"\n   · {ev} | {tm} | {pipe}"
                            if msg:
                                text += f"\n     _{msg}_"
                    else:
                        text += "\n\n*최근 로그 (24h)*: 이벤트 없음"
                except Exception as log_err:
                    logger.debug(f"Could not fetch channel logs for detail: {log_err}")
                    text += "\n\n*최근 로그*: 조회 실패"
            
            client.chat_postEphemeral(channel=channel, user=user_id, text=text)
        except Exception as e:
            logger.error(f"Error handling alert channel detail: {e}", exc_info=True)

    # Fallback handler for unknown/auto-generated action IDs (like +Mv8B, qB3fB)
    # This catches actions that don't match any specific pattern
    # Note: This should be registered last, but Slack Bolt processes handlers in registration order
    # More specific patterns should be registered first
    @app.action(re.compile(r"^[+\-]?[A-Za-z0-9_]+$"))
    def handle_unknown_action(ack, body, client, logger):
        """Handle unknown/auto-generated action IDs as fallback."""
        ack()
        
        try:
            action = body["actions"][0]
            action_id = action.get("action_id", "")
            value = action.get("value", "")
            
            logger.info(f"Handling unknown action {action_id} with value: {value}")
            
            # Try to parse value format: service:resource_id
            # This works for buttons that have value set
            if ":" in value:
                parts = value.split(":")
                if len(parts) >= 2:
                    service_type = parts[0]
                    resource_id = ":".join(parts[1:])
                    
                    view = body.get("view", {})
                    state = extract_modal_filter_state(view)
                    channel_id = state.get("channel_id")
                    user_id = body["user"]["id"]
                    
                    # Check if this is an info action by checking button text or context
                    # For now, assume any unknown action with value is an info request
                    details = services.tencent_client.get_resource_details(resource_id, service_type)
                    if details:
                        text = (
                            f"*{details.get('name', 'Unknown')}*\n"
                            f"ID: `{details.get('id', '')}`\n"
                            f"서비스: {details.get('service', '')}\n"
                            f"상태: {details.get('status', 'unknown')}"
                        )
                        
                        # For StreamLive channels, also show input status
                        if service_type in ["StreamLive", "MediaLive"]:
                            input_status = services.tencent_client.get_channel_input_status(resource_id)
                            text += _format_input_status_text(input_status)
                    else:
                        text = "리소스 정보를 가져올 수 없습니다."
                    
                    client.chat_postEphemeral(
                        channel=channel_id or body.get("channel", {}).get("id", ""),
                        user=user_id,
                        text=text,
                    )
                    return
            
            # Handle overflow menu with selected_option
            if "selected_option" in action:
                selected_value = action["selected_option"].get("value", "")
                logger.info(f"Handling unknown action {action_id} with selected_option value: {selected_value}")
                
                # Try to parse as resource menu format: action:service:resource_id
                if ":" in selected_value:
                    parts = selected_value.split(":")
                    if len(parts) >= 3:
                        action_type = parts[0]
                        service_type = parts[1]
                        resource_id = ":".join(parts[2:])
                        
                        # Handle info action
                        if action_type == "info":
                            view = body.get("view", {})
                            state = extract_modal_filter_state(view)
                            channel_id = state.get("channel_id")
                            user_id = body["user"]["id"]
                            
                            details = services.tencent_client.get_resource_details(resource_id, service_type)
                            if details:
                                text = (
                                    f"*{details.get('name', 'Unknown')}*\n"
                                    f"ID: `{details.get('id', '')}`\n"
                                    f"서비스: {details.get('service', '')}\n"
                                    f"상태: {details.get('status', 'unknown')}"
                                )
                                
                                # For StreamLive channels, also show input status
                                if service_type in ["StreamLive", "MediaLive"]:
                                    input_status = services.tencent_client.get_channel_input_status(resource_id)
                                    text += _format_input_status_text(input_status)
                            else:
                                text = "리소스 정보를 가져올 수 없습니다."
                            
                            client.chat_postEphemeral(
                                channel=channel_id or body.get("channel", {}).get("id", ""),
                                user=user_id,
                                text=text,
                            )
                            return
        except Exception as e:
            logger.debug(f"Error handling unknown action {action_id}: {e}", exc_info=True)
