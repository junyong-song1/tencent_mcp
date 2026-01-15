"""Dashboard action handlers."""
import json
import logging
import threading

from slack_bolt import App

from app.slack.ui.dashboard import DashboardUI

logger = logging.getLogger(__name__)


def register(app: App, services):
    """Register dashboard action handlers."""

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

            if isinstance(channel_id, str) and channel_id.strip().startswith("{"):
                try:
                    nested = json.loads(channel_id)
                    channel_id = nested.get("channel_id", channel_id)
                except (json.JSONDecodeError, TypeError):
                    pass
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

    def async_update_modal(
        client, view_id, channel_id, service_filter, status_filter, keyword,
        clear_cache=False, page=0
    ):
        """Update modal asynchronously."""
        def _update():
            try:
                if clear_cache:
                    services.tencent_client.clear_cache()

                channels = services.tencent_client.list_all_resources()
                modal_view = DashboardUI.create_dashboard_modal(
                    channels=channels,
                    service_filter=service_filter,
                    status_filter=status_filter,
                    keyword=keyword,
                    channel_id=channel_id,
                    page=page,
                )
                client.views_update(view_id=view_id, view=modal_view)
            except Exception as e:
                logger.error(f"Async modal update failed: {e}")
                try:
                    client.views_update(
                        view_id=view_id,
                        view={
                            "type": "modal",
                            "callback_id": "dashboard_modal_view",
                            "private_metadata": channel_id,
                            "title": {"type": "plain_text", "text": "오류 발생"},
                            "close": {"type": "plain_text", "text": "닫기"},
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": f"업데이트 중 오류: {str(e)}"},
                                }
                            ],
                        },
                    )
                except Exception:
                    pass

        threading.Thread(target=_update, daemon=True).start()

    @app.action("dashboard_search_input")
    def handle_search_input(ack, body, client, logger):
        """Handle search input."""
        ack()
        state = extract_modal_filter_state(body["view"])
        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["service_filter"],
            state["status_filter"],
            state["keyword"],
        )

    @app.action("dashboard_filter_service")
    def handle_filter_service(ack, body, client, logger):
        """Handle service filter change."""
        ack()
        state = extract_modal_filter_state(body["view"])
        service_filter = body["actions"][0]["selected_option"]["value"]
        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            service_filter,
            state["status_filter"],
            state["keyword"],
        )

    @app.action("dashboard_filter_status")
    def handle_filter_status(ack, body, client, logger):
        """Handle status filter change."""
        ack()
        state = extract_modal_filter_state(body["view"])
        status_filter = body["actions"][0]["selected_option"]["value"]
        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["service_filter"],
            status_filter,
            state["keyword"],
        )

    @app.action("dashboard_refresh")
    def handle_refresh(ack, body, client, logger):
        """Handle refresh button."""
        ack()
        state = extract_modal_filter_state(body["view"])

        # Show loading state
        client.views_update(
            view_id=state["view_id"],
            view={
                "type": "modal",
                "callback_id": "dashboard_modal_view",
                "private_metadata": state["channel_id"],
                "title": {"type": "plain_text", "text": "Tencent Media Dashboard"},
                "close": {"type": "plain_text", "text": "닫기"},
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": "새로고침 중...", "emoji": True}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "최신 데이터를 가져오고 있습니다."}},
                ],
            },
        )

        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["service_filter"],
            state["status_filter"],
            state["keyword"],
            clear_cache=True,
            page=0,
        )

    @app.action("dashboard_page_prev")
    def handle_page_prev(ack, body, client, logger):
        """Handle previous page button."""
        ack()
        state = extract_modal_filter_state(body["view"])
        new_page = max(0, state["page"] - 1)
        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["service_filter"],
            state["status_filter"],
            state["keyword"],
            page=new_page,
        )

    @app.action("dashboard_page_next")
    def handle_page_next(ack, body, client, logger):
        """Handle next page button."""
        ack()
        state = extract_modal_filter_state(body["view"])
        new_page = state["page"] + 1
        async_update_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["service_filter"],
            state["status_filter"],
            state["keyword"],
            page=new_page,
        )

    @app.action("dashboard_page_info")
    def handle_page_info(ack, body, client, logger):
        """Handle page info button (no-op)."""
        ack()
