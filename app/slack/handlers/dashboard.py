"""Dashboard action handlers."""
import json
import logging
import re
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

    # ========== StreamLink Only Dashboard Handlers ==========

    def _build_failover_map(services, hierarchy: list) -> dict:
        """Build a map of channel_id to failover status.

        Args:
            services: Services container
            hierarchy: List of {parent: resource, children: [resources]}

        Returns:
            {channel_id: {"active_input": str, "failover_info": dict}}
        """
        failover_map = {}

        for group in hierarchy:
            parent = group["parent"]
            children = group["children"]

            # Only process StreamLive parents with children
            if parent.get("service") != "StreamLive" or not children:
                continue

            channel_id = parent.get("id", "")
            try:
                input_status = services.tencent_client.get_channel_input_status(channel_id)
                if input_status:
                    failover_map[channel_id] = {
                        "active_input": input_status.get("active_input"),
                        "failover_info": input_status.get("log_based_detection", {}),
                    }
            except Exception as e:
                logger.debug(f"Could not get failover status for {channel_id}: {e}")

        return failover_map

    def extract_streamlink_modal_state(view: dict) -> dict:
        """Extract filter state from StreamLink-only modal view."""
        filters = view.get("state", {}).get("values", {}).get("streamlink_only_filters", {})
        search_block = view.get("state", {}).get("values", {}).get("streamlink_only_search_block", {})

        private_metadata = view.get("private_metadata", "")
        channel_id = ""
        page = 0
        status_filter = "all"
        keyword = ""

        try:
            metadata = json.loads(private_metadata)
            channel_id = metadata.get("channel_id", "")
            page = metadata.get("page", 0)
            status_filter = metadata.get("status_filter", "all")
            keyword = metadata.get("keyword", "")
        except (json.JSONDecodeError, TypeError):
            pass

        # Override with current UI state
        if "streamlink_only_filter_status" in filters:
            selected = filters["streamlink_only_filter_status"].get("selected_option")
            if selected:
                status_filter = selected.get("value", "all")

        if "streamlink_only_search_input" in search_block:
            keyword = search_block["streamlink_only_search_input"].get("value") or ""

        return {
            "view_id": view.get("id"),
            "channel_id": channel_id,
            "status_filter": status_filter,
            "keyword": keyword,
            "page": page,
        }

    def async_update_streamlink_modal(
        client, view_id, channel_id, status_filter, keyword, page=0, clear_cache=False, fetch_failover=False
    ):
        """Update StreamLink-only modal asynchronously.

        Args:
            fetch_failover: If True, fetch failover status for each channel (slow).
        """
        def _update():
            try:
                if clear_cache:
                    services.tencent_client.clear_cache()

                all_resources = services.tencent_client.list_all_resources()

                # Build hierarchy (same as full dashboard)
                from app.services.linkage import ResourceHierarchyBuilder
                hierarchy = ResourceHierarchyBuilder.build_hierarchy(all_resources)

                # Build failover map if requested
                failover_map = {}
                if fetch_failover:
                    failover_map = _build_failover_map(services, hierarchy)

                modal_view = DashboardUI.create_streamlink_only_modal(
                    hierarchy=hierarchy,
                    status_filter=status_filter,
                    keyword=keyword,
                    channel_id=channel_id,
                    page=page,
                    failover_map=failover_map,
                )
                client.views_update(view_id=view_id, view=modal_view)
            except Exception as e:
                logger.error(f"StreamLink modal update failed: {e}")
                try:
                    client.views_update(
                        view_id=view_id,
                        view={
                            "type": "modal",
                            "callback_id": "streamlink_only_modal_view",
                            "private_metadata": json.dumps({"channel_id": channel_id}),
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

    @app.action("streamlink_only_filter_status")
    def handle_streamlink_filter_status(ack, body, client, logger):
        """Handle status filter change in StreamLink-only dashboard."""
        ack()
        state = extract_streamlink_modal_state(body["view"])
        status_filter = body["actions"][0]["selected_option"]["value"]
        async_update_streamlink_modal(
            client,
            state["view_id"],
            state["channel_id"],
            status_filter,
            state["keyword"],
            page=0,  # Reset to first page on filter change
        )

    @app.action("streamlink_only_search_input")
    def handle_streamlink_search_input(ack, body, client, logger):
        """Handle search input in StreamLink-only dashboard."""
        ack()
        state = extract_streamlink_modal_state(body["view"])
        async_update_streamlink_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["status_filter"],
            state["keyword"],
            page=0,  # Reset to first page on search
        )

    @app.action("streamlink_only_refresh")
    def handle_streamlink_refresh(ack, body, client, logger):
        """Handle refresh button in StreamLink-only dashboard."""
        ack()
        state = extract_streamlink_modal_state(body["view"])

        # Show loading state
        client.views_update(
            view_id=state["view_id"],
            view={
                "type": "modal",
                "callback_id": "streamlink_only_modal_view",
                "private_metadata": json.dumps({"channel_id": state["channel_id"]}),
                "title": {"type": "plain_text", "text": "StreamLink"},
                "close": {"type": "plain_text", "text": "닫기"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": ":hourglass_flowing_sand: 새로고침 중..."}},
                ],
            },
        )

        async_update_streamlink_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["status_filter"],
            state["keyword"],
            page=0,
            clear_cache=True,
            fetch_failover=True,  # Fetch failover status on refresh
        )

    @app.action("streamlink_only_page_prev")
    def handle_streamlink_page_prev(ack, body, client, logger):
        """Handle previous page button in StreamLink-only dashboard."""
        ack()
        state = extract_streamlink_modal_state(body["view"])
        new_page = max(0, state["page"] - 1)
        async_update_streamlink_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["status_filter"],
            state["keyword"],
            page=new_page,
        )

    @app.action("streamlink_only_page_next")
    def handle_streamlink_page_next(ack, body, client, logger):
        """Handle next page button in StreamLink-only dashboard."""
        ack()
        state = extract_streamlink_modal_state(body["view"])
        new_page = state["page"] + 1
        async_update_streamlink_modal(
            client,
            state["view_id"],
            state["channel_id"],
            state["status_filter"],
            state["keyword"],
            page=new_page,
        )

    @app.action("streamlink_only_page_info")
    def handle_streamlink_page_info(ack, body, client, logger):
        """Handle page info button (no-op)."""
        ack()

    @app.action(re.compile(r"^streamlink_only_start_.*$"))
    def handle_streamlink_start(ack, body, client, logger):
        """Handle start button for StreamLink flow."""
        ack()
        action = body["actions"][0]
        action_id = action["action_id"]
        value = action["value"]  # "StreamLink:flow_id"

        service, resource_id = value.split(":", 1)
        state = extract_streamlink_modal_state(body["view"])

        # Show processing state
        client.views_update(
            view_id=state["view_id"],
            view={
                "type": "modal",
                "callback_id": "streamlink_only_modal_view",
                "private_metadata": json.dumps({"channel_id": state["channel_id"]}),
                "title": {"type": "plain_text", "text": "StreamLink"},
                "close": {"type": "plain_text", "text": "닫기"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f":hourglass_flowing_sand: Flow를 시작하고 있습니다..."}},
                ],
            },
        )

        def async_start_and_refresh():
            try:
                # Start the flow
                result = services.tencent_client.start_resource(resource_id, service)
                logger.info(f"StreamLink flow started: {resource_id}, result: {result}")

                # Wait for status to stabilize and failover to occur
                import time
                time.sleep(8)

                # Clear cache and refresh
                services.tencent_client.clear_cache()

                all_resources = services.tencent_client.list_all_resources()

                # Build hierarchy
                from app.services.linkage import ResourceHierarchyBuilder
                hierarchy = ResourceHierarchyBuilder.build_hierarchy(all_resources)

                # Build failover map (to show failover status after action)
                failover_map = _build_failover_map(services, hierarchy)

                modal_view = DashboardUI.create_streamlink_only_modal(
                    hierarchy=hierarchy,
                    status_filter=state["status_filter"],
                    keyword=state["keyword"],
                    channel_id=state["channel_id"],
                    page=state["page"],
                    failover_map=failover_map,
                )
                client.views_update(view_id=state["view_id"], view=modal_view)

            except Exception as e:
                logger.error(f"Failed to start StreamLink flow: {e}")
                client.views_update(
                    view_id=state["view_id"],
                    view={
                        "type": "modal",
                        "callback_id": "streamlink_only_modal_view",
                        "private_metadata": json.dumps({"channel_id": state["channel_id"]}),
                        "title": {"type": "plain_text", "text": "오류"},
                        "close": {"type": "plain_text", "text": "닫기"},
                        "blocks": [
                            {"type": "section", "text": {"type": "mrkdwn", "text": f":x: 시작 실패: {str(e)}"}},
                        ],
                    },
                )

        threading.Thread(target=async_start_and_refresh, daemon=True).start()

    @app.action(re.compile(r"^streamlink_only_stop_.*$"))
    def handle_streamlink_stop(ack, body, client, logger):
        """Handle stop button for StreamLink flow."""
        ack()
        action = body["actions"][0]
        value = action["value"]  # "StreamLink:flow_id"

        service, resource_id = value.split(":", 1)
        state = extract_streamlink_modal_state(body["view"])

        # Show processing state
        client.views_update(
            view_id=state["view_id"],
            view={
                "type": "modal",
                "callback_id": "streamlink_only_modal_view",
                "private_metadata": json.dumps({"channel_id": state["channel_id"]}),
                "title": {"type": "plain_text", "text": "StreamLink"},
                "close": {"type": "plain_text", "text": "닫기"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f":hourglass_flowing_sand: Flow를 중지하고 있습니다..."}},
                ],
            },
        )

        def async_stop_and_refresh():
            try:
                # Stop the flow
                result = services.tencent_client.stop_resource(resource_id, service)
                logger.info(f"StreamLink flow stopped: {resource_id}, result: {result}")

                # Wait for status to stabilize and failover to occur
                import time
                time.sleep(8)

                # Clear cache and refresh
                services.tencent_client.clear_cache()

                all_resources = services.tencent_client.list_all_resources()

                # Build hierarchy
                from app.services.linkage import ResourceHierarchyBuilder
                hierarchy = ResourceHierarchyBuilder.build_hierarchy(all_resources)

                # Build failover map (to show failover status after action)
                failover_map = _build_failover_map(services, hierarchy)

                modal_view = DashboardUI.create_streamlink_only_modal(
                    hierarchy=hierarchy,
                    status_filter=state["status_filter"],
                    keyword=state["keyword"],
                    channel_id=state["channel_id"],
                    page=state["page"],
                    failover_map=failover_map,
                )
                client.views_update(view_id=state["view_id"], view=modal_view)

            except Exception as e:
                logger.error(f"Failed to stop StreamLink flow: {e}")
                client.views_update(
                    view_id=state["view_id"],
                    view={
                        "type": "modal",
                        "callback_id": "streamlink_only_modal_view",
                        "private_metadata": json.dumps({"channel_id": state["channel_id"]}),
                        "title": {"type": "plain_text", "text": "오류"},
                        "close": {"type": "plain_text", "text": "닫기"},
                        "blocks": [
                            {"type": "section", "text": {"type": "mrkdwn", "text": f":x: 중지 실패: {str(e)}"}},
                        ],
                    },
                )

        threading.Thread(target=async_stop_and_refresh, daemon=True).start()

    @app.action(re.compile(r"^streamlink_only_info_.*$"))
    def handle_streamlink_info(ack, body, client, logger):
        """Handle info button for StreamLink flow (no-op for now)."""
        ack()
