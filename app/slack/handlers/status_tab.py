"""Status tab handlers."""
import json
import logging
from datetime import datetime

from slack_bolt import App

from app.slack.ui.status import StatusUI
from app.slack.ui.dashboard import DashboardUI

logger = logging.getLogger(__name__)


def register(app: App, services):
    """Register status tab handlers."""

    @app.action("tab_channels")
    def handle_tab_channels(ack, body, client, logger):
        """Handle channels tab button."""
        ack()

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")

        channels = services.tencent_client.list_all_resources()
        modal_view = DashboardUI.create_dashboard_modal(
            channels=channels,
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)

    @app.action("tab_status")
    def handle_tab_status(ack, body, client, logger):
        """Handle status tab button."""
        ack()

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")

        channels = services.tencent_client.list_all_resources()
        today_date = datetime.now().date()
        schedules_today = services.schedule_manager.get_schedules_for_date(today_date)
        schedules_upcoming = services.schedule_manager.get_upcoming_schedules(hours=24)

        modal_view = StatusUI.create_status_tab_modal(
            channels=channels,
            schedules_today=schedules_today,
            schedules_upcoming=schedules_upcoming,
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)

    @app.action("status_refresh")
    def handle_status_refresh(ack, body, client, logger):
        """Handle refresh button in status tab."""
        ack()

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")

        services.tencent_client.clear_cache()
        channels = services.tencent_client.list_all_resources()
        today_date = datetime.now().date()
        schedules_today = services.schedule_manager.get_schedules_for_date(today_date)
        schedules_upcoming = services.schedule_manager.get_upcoming_schedules(hours=24)

        modal_view = StatusUI.create_status_tab_modal(
            channels=channels,
            schedules_today=schedules_today,
            schedules_upcoming=schedules_upcoming,
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)
