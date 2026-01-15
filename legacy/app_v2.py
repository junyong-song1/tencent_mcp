"""Main Slack Bot application for Tencent MCP with Command Agent."""
import atexit
import logging
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from datetime import datetime, timedelta

from config import Config
from tencent_cloud_client import TencentCloudClient
from command_parser import (
    parse_command, Intent, format_search_result,
    get_help_message, get_control_help_message
)
from slack_ui import SlackUI
from scheduler import TaskScheduler
from broadcast_schedule import get_schedule_manager
from notification_service import init_notification_service, stop_notification_service


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize components
Config.validate()
app = App(token=Config.SLACK_BOT_TOKEN)
tencent_client = TencentCloudClient()

# Phase 10: Background cache pre-warming (non-blocking)
def _safe_prewarm():
    try:
        tencent_client.prewarm_cache()
    except Exception as e:
        logger.warning(f"Cache prewarm failed (non-critical): {e}")

import threading
threading.Thread(target=_safe_prewarm, daemon=True).start()

slack_ui = SlackUI()


def scheduler_execute_callback(channel_id: str, service: str, action: str) -> dict:
    """Callback for scheduler to execute channel actions."""
    logger.info(f"Scheduler executing: {action} {service}:{channel_id}")
    return tencent_client.control_resource(channel_id, service, action)


task_scheduler = TaskScheduler(execute_callback=scheduler_execute_callback)

# Broadcast Schedule Manager (JSON file persistence)
schedule_manager = get_schedule_manager()

# Register cleanup on exit
atexit.register(task_scheduler.shutdown)
atexit.register(stop_notification_service)


def is_user_allowed(user_id: str) -> bool:
    """Check if user is allowed to use the bot."""
    if not Config.ALLOWED_USERS:
        return True  # No restrictions
    return user_id in Config.ALLOWED_USERS


def extract_modal_filter_state(view: dict) -> dict:
    """
    Extract filter state from modal view.

    Returns:
        dict with keys: view_id, channel_id, service_filter, status_filter, keyword, page
    """
    import json

    filters = view.get("state", {}).get("values", {}).get("dashboard_filters", {})
    search_block = view.get("state", {}).get("values", {}).get("search_block", {})

    # Parse private_metadata (JSON or legacy string)
    private_metadata = view.get("private_metadata", "")
    channel_id = ""
    page = 0

    try:
        metadata = json.loads(private_metadata)
        channel_id = metadata.get("channel_id", "")
        page = metadata.get("page", 0)
        
        # Handle nested JSON string in channel_id (fix for double-encoded JSON)
        # Sometimes channel_id itself is a JSON string like '{"channel_id": "C123", ...}'
        if isinstance(channel_id, str) and channel_id.strip().startswith("{"):
            try:
                nested = json.loads(channel_id)
                # Extract the actual channel_id from nested JSON
                channel_id = nested.get("channel_id", channel_id)
            except (json.JSONDecodeError, TypeError):
                # Not a nested JSON, use as-is
                pass
    except (json.JSONDecodeError, TypeError):
        # Legacy format: just channel_id string
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


def async_update_modal(client, view_id: str, channel_id: str, service_filter: str, status_filter: str, keyword: str, clear_cache: bool = False, page: int = 0):
    """
    Async wrapper for updating dashboard modal with error handling.

    Args:
        client: Slack client
        view_id: Modal view ID
        channel_id: Slack channel ID
        service_filter: Service filter value
        status_filter: Status filter value
        keyword: Search keyword
        clear_cache: Whether to clear cache before update
        page: Current page number (0-indexed)
    """
    import threading

    def _update():
        try:
            if clear_cache:
                tencent_client.clear_cache()
            update_dashboard_modal(client, view_id, channel_id, service_filter, status_filter, keyword, page)
        except Exception as e:
            logger.error(f"Async modal update failed: {e}", exc_info=True)
            try:
                client.views_update(view_id=view_id, view={
                    "type": "modal",
                    "callback_id": "dashboard_modal_view",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "오류 발생"},
                    "close": {"type": "plain_text", "text": "닫기"},
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ 업데이트 중 오류가 발생했습니다: {str(e)}"}}]
                })
            except Exception:
                pass

    threading.Thread(target=_update, daemon=True).start()


# ===== Dashboard Helper =====


def update_dashboard(say, body, service_filter="all", status_filter="all", keyword=""):
    """
    Update the dashboard message (or send new if say provided).
    
    If called from action handler, use body to ack/respond.
    If called from command, use say.
    """
    try:
        # 1. Fetch Resources
        all_resources = tencent_client.list_all_resources()

        # 2. Apply Filters
        filtered = []
        for r in all_resources:
            # Service Filter
            if service_filter != "all" and r.get("service") != service_filter:
                continue
            
            # Status Filter
            if status_filter != "all" and r.get("status", "").lower() != status_filter.lower():
                continue
                
            # Keyword Filter (if any) - simple case-insensitive check
            if keyword and keyword.lower() not in r.get("name", "").lower():
                continue
            
            filtered.append(r)

        # 3. Create Blocks
        blocks = slack_ui.create_dashboard_blocks(
            channels=filtered,
            service_filter=service_filter,
            status_filter=status_filter,
            keyword=keyword
        )

        # 4. Respond
        if body:
            # Updating existing message
            if "response_url" in body:
                # Slash command or similar where response_url exists
                from slack_sdk import WebClient
                client = WebClient(token=Config.SLACK_BOT_TOKEN)
                # For block actions, we usually use client.chat_update if we have channel/ts
                # or requests.post to response_url.
                pass
            
            # Using Bolt's ack() and respond() is handled in the handler wrapper generally.
            # But here we need to know HOW to update.
            # If triggered by block_actions (body['type'] == 'block_actions'):
            container = body.get("container", {})
            channel_id = container.get("channel_id")
            message_ts = container.get("message_ts")
            
            if channel_id and message_ts:
                app.client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    blocks=blocks,
                    text="Dashboard updated"
                )
        else:
            # Sending new message (Command)
            say(blocks=blocks, text="Tencent Media Dashboard")

    except Exception as e:
        logger.error(f"Error updating dashboard: {e}", exc_info=True)
        error_msg = f"❌ 대시보드 로드 중 오류 발생: {str(e)}"
        if body:
            # Try to notify user via channel message
            container = body.get("container", {})
            channel_id = container.get("channel_id")
            if channel_id:
                try:
                    app.client.chat_postEphemeral(
                        channel=channel_id,
                        user=body.get("user", {}).get("id", ""),
                        text=error_msg
                    )
                except Exception:
                    logger.error("Failed to send error notification to user")
        elif say:
            say(error_msg)


# ===== Event Handlers =====


@app.event("app_mention")
def handle_app_mention(event, say, logger):
    """Handle app mentions in channels."""
    user_id = event["user"]

    if not is_user_allowed(user_id):
        say("⚠️ You don't have permission to use this bot.")
        return

    text = event["text"]
    # Remove bot mention from text
    text = text.split(">", 1)[-1].strip() if ">" in text else text

    logger.info(f"App mention from {user_id}: {text}")

    # Handle special commands
    if text.lower() in ["help", "도움말", "사용법"]:
        say(blocks=slack_ui.create_help_blocks())
        return

    # Process with Command Agent
    process_command(user_id, text, say)


@app.event("message")
def handle_dm_message(event, say, logger):
    """Handle direct messages to the bot."""
    # Only handle DM messages (channel_type: im)
    if event.get("channel_type") != "im":
        return

    # Ignore bot messages to prevent loops
    if event.get("bot_id"):
        return

    user_id = event.get("user")
    if not user_id or not is_user_allowed(user_id):
        return

    text = event.get("text", "")
    if not text:
        return

    logger.info(f"DM from {user_id}: {text}")
    process_command(user_id, text, say)


# Helper for Dashboard Update (Modal)
def update_dashboard_modal(
    client,
    view_id: str,
    channel_id: str,
    service_filter: str = "all",
    status_filter: str = "all",
    keyword: str = "",
    page: int = 0
):
    """
    Fetch resources, apply filters, and update the modal view.

    Args:
        page: Current page number (0-indexed) for pagination.
    """
    try:
        # 1. Fetch Resources
        all_resources = tencent_client.list_all_resources()

        # 2. Update View (Filtering handled inside SlackUI._group_channels)
        modal_view = slack_ui.create_dashboard_modal(
            channels=all_resources,
            service_filter=service_filter,
            status_filter=status_filter,
            keyword=keyword,
            channel_id=channel_id,
            page=page
        )

        # 3. Update View
        client.views_update(
            view_id=view_id,
            view=modal_view
        )

    except Exception as e:
        logger.error(f"Failed to update dashboard modal: {e}")


# ==============================================================================
# 5. Action Handlers (Dashboard & Interactive)
# ==============================================================================

@app.action("dashboard_search_input")
def handle_dashboard_search_input(ack, body, client, logger):
    """Handle search input dispatch (Enter key in modal)."""
    ack()

    view = body["view"]
    view_id = view["id"]
    channel_id = view["private_metadata"]
    
    # 1. Get Params
    keyword = view["state"]["values"]["search_block"]["dashboard_search_input"]["value"] or ""
    
    # Get filters from existing state
    filters = view["state"]["values"].get("dashboard_filters", {})
    service_filter = "all"
    status_filter = "all"
    
    if "dashboard_filter_service" in filters:
        service_filter = filters["dashboard_filter_service"]["selected_option"]["value"]
    if "dashboard_filter_status" in filters:
        status_filter = filters["dashboard_filter_status"]["selected_option"]["value"]

    # 2. Show loading state immediately
    search_text = f"'{keyword}'" if keyword else "모든 리소스"
    loading_view = {
        "type": "modal",
        "callback_id": "dashboard_modal_view",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Tencent Media Dashboard"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"🔍 {search_text} 검색 중...", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "텐센트 클라우드에서 리소스를 검색하고 있습니다."}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": ":hourglass_flowing_sand: _잠시만 기다려 주세요..._"}]}
        ]
    }
    client.views_update(view_id=view_id, view=loading_view)
    
    # 3. Async load and update
    import threading
    def async_search():
        try:
            update_dashboard_modal(client, view_id, channel_id, service_filter, status_filter, keyword)
        except Exception as e:
            logger.error(f"Async search failed: {e}", exc_info=True)
            try:
                client.views_update(view_id=view_id, view={
                    "type": "modal",
                    "callback_id": "dashboard_modal_view",
                    "private_metadata": channel_id,
                    "title": {"type": "plain_text", "text": "오류 발생"},
                    "close": {"type": "plain_text", "text": "닫기"},
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ 검색 중 오류가 발생했습니다: {str(e)}"}}]
                })
            except Exception:
                pass
    threading.Thread(target=async_search, daemon=True).start()


@app.action("dashboard_filter_service")
def handle_dashboard_filter_service(ack, body, client, logger):
    """Handle service filter change in modal."""
    ack()

    state = extract_modal_filter_state(body["view"])
    # Override service_filter from the action (newly selected value)
    service_filter = body["actions"][0]["selected_option"]["value"]

    async_update_modal(
        client,
        state["view_id"],
        state["channel_id"],
        service_filter,
        state["status_filter"],
        state["keyword"]
    )


@app.action("dashboard_filter_status")
def handle_dashboard_filter_status(ack, body, client, logger):
    """Handle status filter change in modal."""
    ack()

    state = extract_modal_filter_state(body["view"])
    # Override status_filter from the action (newly selected value)
    status_filter = body["actions"][0]["selected_option"]["value"]

    async_update_modal(
        client,
        state["view_id"],
        state["channel_id"],
        state["service_filter"],
        status_filter,
        state["keyword"]
    )


@app.action("dashboard_refresh")
def handle_dashboard_refresh(ack, body, client, logger):
    """Handle refresh button in modal."""
    ack()

    state = extract_modal_filter_state(body["view"])

    # Show refreshing state
    refresh_view = {
        "type": "modal",
        "callback_id": "dashboard_modal_view",
        "private_metadata": state["channel_id"],
        "title": {"type": "plain_text", "text": "Tencent Media Dashboard"},
        "close": {"type": "plain_text", "text": "닫기"},
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🔄 새로고침 중...", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "텐센트 클라우드에서 최신 데이터를 가져오고 있습니다."}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": ":arrows_counterclockwise: _캐시를 우회하여 새로운 데이터를 로드합니다..._"}]}
        ]
    }
    client.views_update(view_id=state["view_id"], view=refresh_view)

    # Clear cache and fetch fresh data (reset to first page)
    async_update_modal(
        client,
        state["view_id"],
        state["channel_id"],
        state["service_filter"],
        state["status_filter"],
        state["keyword"],
        clear_cache=True,
        page=0  # Reset to first page on refresh
    )


@app.action("dashboard_page_prev")
def handle_dashboard_page_prev(ack, body, client, logger):
    """Handle previous page button."""
    ack()

    state = extract_modal_filter_state(body["view"])
    new_page = max(0, state["page"] - 1)
    logger.info(f"Page prev: {state['page']} -> {new_page}")

    async_update_modal(
        client,
        state["view_id"],
        state["channel_id"],
        state["service_filter"],
        state["status_filter"],
        state["keyword"],
        page=new_page
    )


@app.action("dashboard_page_next")
def handle_dashboard_page_next(ack, body, client, logger):
    """Handle next page button."""
    ack()

    state = extract_modal_filter_state(body["view"])
    new_page = state["page"] + 1
    logger.info(f"Page next: {state['page']} -> {new_page}")

    async_update_modal(
        client,
        state["view_id"],
        state["channel_id"],
        state["service_filter"],
        state["status_filter"],
        state["keyword"],
        page=new_page
    )


@app.action("dashboard_page_info")
def handle_dashboard_page_info(ack, body, client, logger):
    """Handle page info button (no-op, just for display)."""
    ack()
    # This button is just for showing page info, no action needed


# ==============================================================================
# Filter Tab Handlers
# ==============================================================================

@app.action("filter_tab_all")
def handle_filter_tab_all(ack, body, client, logger):
    """Handle All filter tab."""
    ack()
    state = extract_modal_filter_state(body["view"])
    async_update_modal(
        client, state["view_id"], state["channel_id"],
        "all", "all", state["keyword"], page=0
    )

@app.action("filter_tab_live")
def handle_filter_tab_live(ack, body, client, logger):
    """Handle Live (StreamLive) filter tab."""
    ack()
    state = extract_modal_filter_state(body["view"])
    async_update_modal(
        client, state["view_id"], state["channel_id"],
        "StreamLive", state["status_filter"], state["keyword"], page=0
    )

@app.action("filter_tab_link")
def handle_filter_tab_link(ack, body, client, logger):
    """Handle Link (StreamLink) filter tab."""
    ack()
    state = extract_modal_filter_state(body["view"])
    async_update_modal(
        client, state["view_id"], state["channel_id"],
        "StreamLink", state["status_filter"], state["keyword"], page=0
    )

@app.action("filter_tab_running")
def handle_filter_tab_running(ack, body, client, logger):
    """Handle Running status filter tab."""
    ack()
    state = extract_modal_filter_state(body["view"])
    async_update_modal(
        client, state["view_id"], state["channel_id"],
        state["service_filter"], "running", state["keyword"], page=0
    )

@app.action("filter_tab_idle")
def handle_filter_tab_idle(ack, body, client, logger):
    """Handle Idle status filter tab."""
    ack()
    state = extract_modal_filter_state(body["view"])
    async_update_modal(
        client, state["view_id"], state["channel_id"],
        state["service_filter"], "idle", state["keyword"], page=0
    )


# ==============================================================================
# Tab Navigation Handlers
# ==============================================================================

@app.action("tab_channels")
def handle_tab_channels(ack, body, client, logger):
    """Handle channels tab button."""
    ack()

    view = body["view"]
    view_id = view["id"]

    # Parse metadata to get channel_id
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")

    # Show loading and then load channels tab (which is the default dashboard)
    async_update_modal(client, view_id, channel_id, "all", "all", "", page=0)


@app.action("tab_schedules")
def handle_tab_schedules(ack, body, client, logger):
    """Handle schedules tab button."""
    ack()

    view = body["view"]
    view_id = view["id"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
        selected_date_str = metadata.get("selected_date", "")
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")
        selected_date_str = ""

    # Get today's date if not specified
    if not selected_date_str:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date_str = today

    # Parse selected date and calculate month range
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime("%Y-%m-%d")

    # Calculate month start and end (first day to last day of the month)
    month_start = selected_date.replace(day=1)
    if selected_date.month == 12:
        month_end = selected_date.replace(day=31)
    else:
        next_month = selected_date.replace(month=selected_date.month + 1, day=1)
        month_end = next_month - timedelta(days=1)

    # Fetch schedules for the entire month
    schedules = schedule_manager.get_schedules_for_range(month_start, month_end)

    # Create and update view
    modal_view = slack_ui.create_schedule_tab_modal(
        schedules=schedules,
        selected_date=selected_date_str,
        channel_id=channel_id,
        month_view=True  # Indicate this is a month view
    )

    client.views_update(view_id=view_id, view=modal_view)


@app.action("tab_status")
def handle_tab_status(ack, body, client, logger):
    """Handle status tab button."""
    ack()

    view = body["view"]
    view_id = view["id"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")

    # Fetch data for status tab
    channels = tencent_client.list_all_resources()
    today_date = datetime.now().date()
    schedules_today = schedule_manager.get_schedules_for_date(today_date)
    schedules_upcoming = schedule_manager.get_upcoming_schedules(hours=24)

    # Create and update view
    modal_view = slack_ui.create_status_tab_modal(
        channels=channels,
        schedules_today=schedules_today,
        schedules_upcoming=schedules_upcoming,
        channel_id=channel_id
    )

    client.views_update(view_id=view_id, view=modal_view)


# ==============================================================================
# Schedule Tab Action Handlers
# ==============================================================================

@app.action("schedule_date_picker")
def handle_schedule_date_picker(ack, body, client, logger):
    """Handle date picker in schedule tab."""
    ack()

    view = body["view"]
    view_id = view["id"]
    selected_date = body["actions"][0]["selected_date"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")

    # Fetch schedules for selected date
    try:
        date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        schedules = schedule_manager.get_schedules_for_date(date_obj)
    except Exception as e:
        logger.error(f"Error fetching schedules for date {selected_date}: {e}")
        schedules = []

    # Update view
    modal_view = slack_ui.create_schedule_tab_modal(
        schedules=schedules,
        selected_date=selected_date,
        channel_id=channel_id
    )

    client.views_update(view_id=view_id, view=modal_view)


@app.action("schedule_add_button")
def handle_schedule_add_button(ack, body, client, logger):
    """Handle add schedule button - opens a new modal."""
    ack()

    view = body["view"]

    # Get current metadata to pass to the add modal
    parent_metadata = view.get("private_metadata", "")

    # Parse selected_date from metadata
    import json
    try:
        metadata = json.loads(parent_metadata)
        selected_date = metadata.get("selected_date", datetime.now().strftime("%Y-%m-%d"))
    except (json.JSONDecodeError, TypeError):
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch channels for dropdown (StreamLive only)
    all_resources = tencent_client.list_all_resources()
    channels = [r for r in all_resources if r.get("service") == "StreamLive"]

    # Create add schedule modal
    add_modal = slack_ui.create_schedule_add_modal(
        channels=channels,
        parent_metadata=parent_metadata,
        selected_date=selected_date
    )

    # Push the modal on top of current view
    client.views_push(
        trigger_id=body["trigger_id"],
        view=add_modal
    )


@app.action("schedule_refresh")
def handle_schedule_refresh(ack, body, client, logger):
    """Handle refresh button in schedule tab."""
    ack()

    view = body["view"]
    view_id = view["id"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
        selected_date = metadata.get("selected_date", datetime.now().strftime("%Y-%m-%d"))
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # Parse selected date and calculate month range
    try:
        date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except:
        date_obj = datetime.now().date()
        selected_date = date_obj.strftime("%Y-%m-%d")

    # Calculate month start and end (first day to last day of the month)
    month_start = date_obj.replace(day=1)
    if date_obj.month == 12:
        month_end = date_obj.replace(day=31)
    else:
        next_month = date_obj.replace(month=date_obj.month + 1, day=1)
        month_end = next_month - timedelta(days=1)

    # Fetch schedules for the entire month
    schedules = schedule_manager.get_schedules_for_range(month_start, month_end)

    # Update view
    modal_view = slack_ui.create_schedule_tab_modal(
        schedules=schedules,
        selected_date=selected_date,
        channel_id=channel_id,
        month_view=True  # Indicate this is a month view
    )

    client.views_update(view_id=view_id, view=modal_view)


@app.action("status_refresh")
def handle_status_refresh(ack, body, client, logger):
    """Handle refresh button in status tab."""
    ack()

    view = body["view"]
    view_id = view["id"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        channel_id = view.get("private_metadata", "")

    # Fetch fresh data
    tencent_client.clear_cache()  # Clear cache for fresh data
    channels = tencent_client.list_all_resources()
    today_date = datetime.now().date()
    schedules_today = schedule_manager.get_schedules_for_date(today_date)
    schedules_upcoming = schedule_manager.get_upcoming_schedules(hours=24)

    # Update view
    modal_view = slack_ui.create_status_tab_modal(
        channels=channels,
        schedules_today=schedules_today,
        schedules_upcoming=schedules_upcoming,
        channel_id=channel_id
    )

    client.views_update(view_id=view_id, view=modal_view)


@app.view("schedule_add_modal_submit")
def handle_schedule_add_submit(ack, body, client, view, logger):
    """Handle schedule add modal submission."""
    import json

    # Extract form values
    values = view["state"]["values"]

    title = values["schedule_title_block"]["schedule_title_input"]["value"]
    channel_value = values["schedule_channel_block"]["schedule_channel_select"]["selected_option"]["value"]
    start_date_value = values["schedule_start_date_block"]["schedule_start_date_input"]["selected_date"]
    start_time = values["schedule_start_time_block"]["schedule_start_time_input"]["selected_time"]
    end_date_value = values["schedule_end_date_block"]["schedule_end_date_input"]["selected_date"]
    end_time = values["schedule_end_time_block"]["schedule_end_time_input"]["selected_time"]
    assignee_id = values["schedule_assignee_block"]["schedule_assignee_select"]["selected_user"]

    # Parse channel value (service:id)
    if ":" in channel_value:
        service, channel_id = channel_value.split(":", 1)
                else:
        service = "Unknown"
        channel_id = channel_value

    # Get channel name from resources
    channel_name = channel_id
    try:
        all_resources = tencent_client.list_all_resources()
        for res in all_resources:
            if res.get("id") == channel_id:
                channel_name = res.get("name", channel_id)
                break
    except Exception:
        pass

    # Get assignee name
    assignee_name = assignee_id
    try:
        user_info = client.users_info(user=assignee_id)
        if user_info["ok"]:
            assignee_name = user_info["user"].get("real_name") or user_info["user"].get("name", assignee_id)
    except Exception:
        pass

    # Parse options
    options_block = values.get("schedule_options_block", {}).get("schedule_options_input", {})
    selected_options = options_block.get("selected_options") or []
    option_values = [opt["value"] for opt in selected_options]

    notify_2h = "notify_2h" in option_values
    notify_30m = "notify_30m" in option_values
    auto_start = False  # 자동 시작 옵션 제거
    auto_stop = False  # 자동 종료 옵션 제거
    
    # Parse repeat settings
    repeat_block = values.get("schedule_repeat_block", {}).get("schedule_repeat_select", {})
    repeat_type = repeat_block.get("selected_option", {}).get("value", "none")
    
    repeat_count_block = values.get("schedule_repeat_count_block", {}).get("schedule_repeat_count_input", {})
    repeat_count_value = repeat_count_block.get("value", "").strip()

    # Get notes
    notes_block = values.get("schedule_notes_block", {}).get("schedule_notes_input", {})
    notes = notes_block.get("value") or ""

    # Parse datetime
    try:
        start_datetime = datetime.strptime(f"{start_date_value} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.strptime(f"{end_date_value} {end_time}", "%Y-%m-%d %H:%M")
    except Exception as e:
        ack(response_action="errors", errors={"schedule_start_date_block": f"날짜/시간 형식 오류: {e}"})
        return

    # Validate end datetime
    if end_datetime <= start_datetime:
        ack(response_action="errors", errors={"schedule_end_date_block": "종료 날짜/시간은 시작 날짜/시간 이후여야 합니다."})
        return

    # Parse repeat settings
    # For repeat schedules, use end_date_value as the repeat end date if repeat_count_value is not provided
    repeat_end_date = None
    repeat_times = None
    
    if repeat_type != "none":
        if repeat_count_value:
            # Try to parse as date first (YYYY-MM-DD)
            try:
                repeat_end_date = datetime.strptime(repeat_count_value, "%Y-%m-%d").date()
            except ValueError:
                # Try to parse as number (repeat count)
                try:
                    repeat_times = int(repeat_count_value)
                    if repeat_times < 1:
                        ack(response_action="errors", errors={"schedule_repeat_count_block": "반복 횟수는 1 이상이어야 합니다."})
                        return
                except ValueError:
                    ack(response_action="errors", errors={"schedule_repeat_count_block": "반복 횟수는 숫자 또는 날짜(YYYY-MM-DD) 형식이어야 합니다."})
                    return
        else:
            # If repeat_count_value is not provided, use end_date_value as repeat end date
            try:
                repeat_end_date = datetime.strptime(end_date_value, "%Y-%m-%d").date()
            except Exception:
                # If end_date_value is same as start_date_value, require repeat_count_value
                if start_date_value == end_date_value:
                    ack(response_action="errors", errors={"schedule_repeat_count_block": "반복 주기가 선택된 경우 반복 횟수 또는 종료 날짜를 입력해주세요."})
                    return

    # Get creator user_id
    created_by = body["user"]["id"]

    # Generate schedules based on repeat settings
    schedules_to_create = []
    
    if repeat_type == "none":
        # Single schedule
        schedules_to_create.append({
            "start_time": start_datetime,
            "end_time": end_datetime
        })
    else:
        # Generate multiple schedules based on repeat type
        current_start = start_datetime
        current_end = end_datetime
        duration = end_datetime - start_datetime
        count = 0
        
        while True:
            # Check if we should stop
            if repeat_times and count >= repeat_times:
                break
            if repeat_end_date and current_start.date() > repeat_end_date:
                break
            
            schedules_to_create.append({
                "start_time": current_start,
                "end_time": current_end
            })
            count += 1
            
            # Calculate next occurrence
            if repeat_type == "daily":
                current_start = current_start + timedelta(days=1)
                current_end = current_end + timedelta(days=1)
            elif repeat_type == "weekly":
                current_start = current_start + timedelta(weeks=1)
                current_end = current_end + timedelta(weeks=1)
            elif repeat_type == "monthly":
                # Add one month (approximate)
                if current_start.month == 12:
                    current_start = current_start.replace(year=current_start.year + 1, month=1)
                else:
                    current_start = current_start.replace(month=current_start.month + 1)
                current_end = current_start + duration
            
            # Safety limit: prevent infinite loops
            if count > 365:
                break

    # Create all schedules
    created_schedules = []
    errors = []
    
    for schedule_data in schedules_to_create:
        result = schedule_manager.add_schedule(
            channel_id=channel_id,
            channel_name=channel_name,
            service=service,
            title=title,
            start_time=schedule_data["start_time"],
            end_time=schedule_data["end_time"],
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            auto_start=auto_start,
            auto_stop=auto_stop,
            notify_2h=notify_2h,
            notify_30m=notify_30m,
            created_by=created_by,
            notes=notes
        )
        
        if result["success"]:
            created_schedules.append(result)
        else:
            errors.append(result.get("error", "등록 실패"))

    if errors:
        ack(response_action="errors", errors={"schedule_title_block": f"일부 스케줄 등록 실패: {', '.join(errors[:3])}"})
        return

    if not created_schedules:
        ack(response_action="errors", errors={"schedule_title_block": "등록할 스케줄이 없습니다."})
        return

    # Success - close modal
    ack()

    # Parse parent metadata to get slack channel_id
    try:
        parent_metadata = json.loads(view.get("private_metadata", "{}"))
        slack_channel_id = parent_metadata.get("channel_id", "")
    except (json.JSONDecodeError, TypeError):
        slack_channel_id = ""

    # Notify channel about new schedules
    if slack_channel_id:
        if len(created_schedules) == 1:
            schedule = created_schedules[0]["schedule"]
            start_dt = datetime.fromisoformat(schedule["start_time_iso"])
            end_dt = datetime.fromisoformat(schedule["end_time_iso"])
            client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📅 새로운 스케줄이 등록되었습니다!\n"
                     f"*{title}* ({start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%H:%M')})\n"
                     f"채널: {channel_name} | 담당자: <@{assignee_id}>"
            )
        else:
            first_schedule = created_schedules[0]["schedule"]
            last_schedule = created_schedules[-1]["schedule"]
            first_start = datetime.fromisoformat(first_schedule["start_time_iso"])
            last_start = datetime.fromisoformat(last_schedule["start_time_iso"])
            
            repeat_text = {
                "daily": "매일",
                "weekly": "매주",
                "monthly": "매월"
            }.get(repeat_type, "반복")
            
            client.chat_postMessage(
                channel=slack_channel_id,
                text=f"📅 *{len(created_schedules)}개의 스케줄*이 등록되었습니다!\n"
                     f"*{title}* ({repeat_text})\n"
                     f"기간: {first_start.strftime('%Y-%m-%d')} ~ {last_start.strftime('%Y-%m-%d')}\n"
                     f"채널: {channel_name} | 담당자: <@{assignee_id}>"
            )


@app.action(re.compile(r"schedule_menu_.*"))
def handle_schedule_menu(ack, body, client, logger):
    """Handle schedule overflow menu actions (edit/delete)."""
    ack()

    action = body["actions"][0]
    selected_value = action["selected_option"]["value"]

    # Parse action:schedule_id
    if ":" in selected_value:
        action_type, schedule_id = selected_value.split(":", 1)
            else:
        logger.error(f"Invalid schedule menu value: {selected_value}")
        return

    view = body["view"]
    view_id = view["id"]

    # Parse metadata
    import json
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
        selected_date = metadata.get("selected_date", datetime.now().strftime("%Y-%m-%d"))
    except (json.JSONDecodeError, TypeError):
        channel_id = ""
        selected_date = datetime.now().strftime("%Y-%m-%d")

    if action_type == "delete":
        # Delete schedule
        result = schedule_manager.delete_schedule(schedule_id)

        if result["success"]:
            # Notify channel
            if channel_id:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"🗑️ 스케줄이 삭제되었습니다: {result.get('message', schedule_id)}"
                )

        # Refresh schedule tab
        try:
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
            schedules = schedule_manager.get_schedules_for_date(date_obj)
        except Exception:
            schedules = []

        modal_view = slack_ui.create_schedule_tab_modal(
            schedules=schedules,
            selected_date=selected_date,
            channel_id=channel_id
        )

        client.views_update(view_id=view_id, view=modal_view)

    elif action_type == "edit":
        # TODO: Implement edit functionality (push edit modal)
        # For now, just show a message
        user_id = body["user"]["id"]
        client.chat_postEphemeral(
            channel=channel_id or body.get("channel", {}).get("id", ""),
            user=user_id,
            text="✏️ 스케줄 수정 기능은 곧 추가될 예정입니다."
        )


# Placeholder action handlers for schedule form elements (to prevent errors)
@app.action("schedule_channel_select")
def handle_schedule_channel_select(ack, body, client, logger):
    """Handle channel select in schedule form."""
    ack()


@app.action("schedule_date_input")
def handle_schedule_date_input(ack, body, client, logger):
    """Handle date input in schedule form."""
    ack()


@app.action("schedule_start_time_input")
def handle_schedule_start_time_input(ack, body, client, logger):
    """Handle start time input in schedule form."""
    ack()


@app.action("schedule_end_time_input")
def handle_schedule_end_time_input(ack, body, client, logger):
    """Handle end time input in schedule form."""
    ack()


@app.action("schedule_assignee_select")
def handle_schedule_assignee_select(ack, body, client, logger):
    """Handle assignee select in schedule form."""
    ack()


@app.action("schedule_options_input")
def handle_schedule_options_input(ack, body, client, logger):
    """Handle options checkboxes in schedule form."""
    ack()


# Control Buttons (Start/Stop/Restart) - now inside Modal
@app.action(re.compile(r"(start|stop|restart)_.*"))
def handle_control_action_modal(ack, body, client, logger):
    """Handle control buttons directly from Modal."""
    ack()

    action_data = body["actions"][0]
    action_id = action_data["action_id"]
    value = action_data["value"]  # "Service:ChannelID" or just "ChannelID"

    view = body["view"]
    view_id = view["id"]
    state = extract_modal_filter_state(view)
    channel_id = state["channel_id"]

    # Parse action
    action_type = action_id.split("_")[0]  # start, stop, restart
    target_id = action_id.split("_")[1]

    # If value contains service, extract it
    service_type = None
    if ":" in value:
        service_type, _ = value.split(":")

    user_id = body["user"]["id"]

    # Get resource name for better notification
    resource_name = target_id  # Default to ID if name not found
    try:
        if service_type:
            details = tencent_client.get_resource_details(target_id, service_type)
            if details and details.get("name"):
                resource_name = details["name"]
        else:
            # Try to find in all resources
            all_resources = tencent_client.list_all_resources()
            for res in all_resources:
                if res.get("id") == target_id:
                    resource_name = res.get("name", target_id)
                    break
    except Exception as e:
        logger.debug(f"Failed to get resource name: {e}")
        # Continue with ID as fallback

    # Notify channel (Audit Log)
    if channel_id:
        client.chat_postMessage(
            channel=channel_id,
            text=f"⚙️ <@{user_id}> requested *{action_type.upper()}* on `{resource_name}` (`{target_id}`)..."
        )

    result = tencent_client.control_resource(target_id, service_type, action_type)
    success = result["success"]
    message = result["message"]

    # Result Notification
    result_icon = "✅" if success else "❌"
    if channel_id:
        client.chat_postMessage(
            channel=channel_id,
            text=f"{result_icon} *{action_type.upper()}* `{resource_name}` (`{target_id}`): {message}"
        )

    # Refresh Modal to show new status (stay on current page)
    # Clear cache to ensure fresh status is fetched
    async_update_modal(
        client, view_id, channel_id,
        state["service_filter"], state["status_filter"], state["keyword"],
        clear_cache=True, page=state["page"]
    )


@app.action(re.compile(r"dashboard_bulk_(start|stop)"))
def handle_bulk_control(ack, body, client, logger):
    """Handle bulk start/stop actions for all filtered items."""
    ack()

    action_data = body["actions"][0]
    action_id = action_data["action_id"]
    action_type = "start" if "start" in action_id else "stop"

    view = body["view"]
    view_id = view["id"]
    state = extract_modal_filter_state(view)
    channel_id = state["channel_id"]
    user_id = body["user"]["id"]

    # Use extracted filter state
    service_filter = state["service_filter"]
    status_filter = state["status_filter"]
    keyword = state["keyword"]

    # 2. Fetch and apply Hierarchy-Aware Filtering (Same as UI)
    all_resources = tencent_client.list_all_resources()
    hierarchy = SlackUI._group_channels(all_resources, service_filter, status_filter, keyword)
    
    # Flatten hierarchy to get targets
    filtered_list = []
    for h in hierarchy:
        filtered_list.append(h["parent"])
        filtered_list.extend(h["children"])

    targets = []
    for r in filtered_list:
        # Only add if the action is relevant
        if action_type == "start" and r.get("status") in ["stopped", "idle"]:
            targets.append(r)
        elif action_type == "stop" and r.get("status") == "running":
            targets.append(r)

    if not targets:
        if channel_id:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"⚠️ {action_type.upper()}를 실행할 대상이 없습니다. (필터 확인 필요)"
            )
        return

    # 3. Limit bulk count to prevent system load
    MAX_BULK = 10
    execution_targets = targets[:MAX_BULK]
    remaining_count = len(targets) - MAX_BULK

    # 4. Notify channel (Audit Log)
    target_names = ", ".join([f"`{t['name']}`" for t in execution_targets])
    if channel_id:
        client.chat_postMessage(
            channel=channel_id,
            text=f"🏗️ <@{user_id}> requested *BULK {action_type.upper()}* on {len(execution_targets)} items: {target_names}" +
                 (f" (and {remaining_count} more...)" if remaining_count > 0 else "")
        )

    # 5. Execute Action
    results = []
    for target in execution_targets:
        res = tencent_client.control_resource(target["id"], target.get("service"), action_type)
        results.append(res["success"])
    
    # 6. Summary Result
    success_count = sum(1 for r in results if r)
    fail_count = len(results) - success_count
    
    if channel_id:
        client.chat_postMessage(
            channel=channel_id,
            text=f"✅ *BULK {action_type.upper()}* Finished: {success_count} success, {fail_count} failed."
        )

    # 7. Refresh View (stay on current page)
    update_dashboard_modal(client, view_id, channel_id, service_filter, status_filter, keyword, state["page"])


def handle_tencent_command_internal(
    command_text, channel_id, user_id, trigger_id, client, respond
):
    """
    Handle the /tencent command logic.
    Refactored to open Modal Dashboard for 'list' command.
    """
    cmd_parts = command_text.split()
    sub_cmd = cmd_parts[0].lower() if cmd_parts else "help"
    
    if sub_cmd in ["list", "ls", "dashboard"]:
        # Open Loading Modal Immediately
        try:
            loading_view = slack_ui.create_loading_modal(channel_id=channel_id)
            resp = client.views_open(trigger_id=trigger_id, view=loading_view)
            view_id = resp["view"]["id"]

            # Initial Keyword?
            initial_keyword = ""
            if len(cmd_parts) > 1:
                initial_keyword = " ".join(cmd_parts[1:])

            # Start Async Refresh
            import threading
            def async_load():
                try:
                    update_dashboard_modal(client, view_id, channel_id, keyword=initial_keyword)
                except Exception as ex:
                    logger.error(f"Async dashboard load failed: {ex}", exc_info=True)
                    try:
                        client.views_update(view_id=view_id, view={
                            "type": "modal",
                            "callback_id": "dashboard_modal_view",
                            "private_metadata": channel_id,
                            "title": {"type": "plain_text", "text": "오류 발생"},
                            "close": {"type": "plain_text", "text": "닫기"},
                            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ 대시보드 로드 중 오류가 발생했습니다: {str(ex)}"}}]
                        })
        except Exception:
            pass

            threading.Thread(target=async_load, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error opening loading modal: {e}")
            respond(f"❌ 대시보드 로드 중 오류 발생: {str(e)}")
            
    elif sub_cmd == "help":
        blocks = slack_ui.create_help_blocks()
        respond(blocks=blocks)
    else:
        # Fallback to Command Agent for other subcommands (though 'list' covers most)
        # Or simple help
        respond(blocks=slack_ui.create_help_blocks())


@app.command("/tencent")
def handle_tencent_command(ack, body, client, respond):
    """Handle /tencent slash command."""
    ack()
    
    command_text = body.get("text", "").strip()
    channel_id = body["channel_id"]
    user_id = body["user_id"]
    trigger_id = body["trigger_id"]

    if not is_user_allowed(user_id):
        respond("🚫 접근 권한이 없습니다.")
        return

    handle_tencent_command_internal(
        command_text, channel_id, user_id, trigger_id, client, respond
    )


@app.command("/tecent")
def handle_tecent_command(ack, command, say, logger):
    # This command is a typo, but we'll keep it for now and route it to the new internal handler
    ack()
    
    command_text = command.get("text", "").strip()
    channel_id = command["channel_id"]
    user_id = command["user_id"]
    trigger_id = command["trigger_id"]

    if not is_user_allowed(user_id):
        say("🚫 접근 권한이 없습니다.")
        return

    # Note: 'say' is used here, but handle_tencent_command_internal expects 'respond'
    # For /tecent, we'll just use the old behavior for now or adapt.
    # Given the refactor, it's better to route it through the new internal handler.
    # We need to pass 'client' and 'respond' (which is 'say' in this context for non-modal responses)
    handle_tencent_command_internal(
        command_text, channel_id, user_id, trigger_id, app.client, say
    )


# ===== existing Action Handlers (old dashboard message actions removed) =====


@app.action(re.compile(r"^analyze_"))
def handle_analyze_action(ack, body, say, logger):
    ack()
    # Analysis logic (simplified)
    pass


@app.action(re.compile(r"^channel_info_"))
def handle_channel_info(ack, body, say, logger):
    """Handle channel info button."""
    ack()
    channel_id = body["actions"][0]["value"]
    # Fetch details and show
    # For now, just say "Details for ID..."
    say(f"ℹ️ Channel ID: `{channel_id}` details...")


@app.action(re.compile(r"^cancel_task_"))
def handle_cancel_task_action(ack, body, say, logger):
    ack()
    user_id = body["user"]["id"]
    task_id = body["actions"][0]["value"]
    result = task_scheduler.cancel_task(task_id)
    blocks = slack_ui.create_cancel_result_blocks(task_id, result["success"], result.get("message", ""))
    say(blocks=blocks)


# ===== Helper Functions =====


def process_command(user_id: str, text: str, say):
    """Process user message with simple command parser."""
    result = parse_command(text)

    if result.intent == Intent.HELP:
        say(get_help_message())
    elif result.intent == Intent.UNKNOWN:
        say(get_help_message())
    elif result.intent in (Intent.START, Intent.STOP, Intent.RESTART):
        # Control commands require dashboard buttons
        say(get_control_help_message(result.intent.value))
    elif result.intent in (Intent.SEARCH, Intent.STATUS):
        # Execute search
        channels = tencent_client.search_resources(
            result.keywords,
            service_filter=result.service or "all"
        )
        say(format_search_result(channels))


# ===== Main =====


def get_channel_status_for_notification(channel_id: str, service: str) -> str:
    """Get channel status for notification service."""
    try:
        details = tencent_client.get_resource_details(channel_id, service)
        return details.get("status", "unknown") if details else "unknown"
    except Exception:
        return "unknown"


def main():
    """Start the bot."""
    logger.info("Starting Tencent MCP Slack Bot (Dashboard Mode)...")

    # Initialize notification service if notification channel is configured
    if Config.NOTIFICATION_CHANNEL:
        logger.info(f"Initializing notification service (channel: {Config.NOTIFICATION_CHANNEL})")
        init_notification_service(
            slack_client=app.client,
            notification_channel=Config.NOTIFICATION_CHANNEL,
            get_channel_status_callback=get_channel_status_for_notification,
            auto_start_callback=scheduler_execute_callback,
        )
    else:
        logger.info("Notification channel not configured, skipping notification service")

    try:
        handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
