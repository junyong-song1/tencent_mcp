"""Schedule tab handlers."""
import json
import logging
import re
from datetime import datetime, timedelta

from slack_bolt import App

from app.slack.ui.schedule import ScheduleUI

logger = logging.getLogger(__name__)


def register(app: App, services):
    """Register schedule tab handlers."""

    @app.action("tab_schedules")
    def handle_tab_schedules(ack, body, client, logger):
        """Handle schedules tab button."""
        ack()

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")

        # Show all upcoming schedules by default
        schedules = services.schedule_manager.get_all_upcoming_schedules()

        modal_view = ScheduleUI.create_schedule_tab_modal(
            schedules=schedules,
            selected_date=None,  # None means "all upcoming"
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)

    @app.action("schedule_date_picker")
    def handle_date_picker(ack, body, client, logger):
        """Handle date picker in schedule tab."""
        ack()

        view = body["view"]
        view_id = view["id"]
        selected_date = body["actions"][0]["selected_date"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")

        try:
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
            schedules = services.schedule_manager.get_schedules_for_date(date_obj)
        except Exception as e:
            logger.error(f"Error fetching schedules: {e}")
            schedules = []

        modal_view = ScheduleUI.create_schedule_tab_modal(
            schedules=schedules,
            selected_date=selected_date,
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)

    @app.action("schedule_add_button")
    def handle_add_button(ack, body, client, logger):
        """Handle add schedule button."""
        ack()

        view = body["view"]
        parent_metadata = view.get("private_metadata", "")

        try:
            metadata = json.loads(parent_metadata)
            selected_date = metadata.get("selected_date", datetime.now().strftime("%Y-%m-%d"))
        except (json.JSONDecodeError, TypeError):
            selected_date = datetime.now().strftime("%Y-%m-%d")

        channels = services.tencent_client.list_all_resources()
        streamlive_channels = [r for r in channels if r.get("service") == "StreamLive"]

        add_modal = ScheduleUI.create_schedule_add_modal(
            channels=streamlive_channels,
            parent_metadata=parent_metadata,
            selected_date=selected_date,
        )

        client.views_push(trigger_id=body["trigger_id"], view=add_modal)

    @app.action("schedule_refresh")
    def handle_refresh(ack, body, client, logger):
        """Handle refresh button in schedule tab."""
        ack()

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
            selected_date = metadata.get("selected_date")  # Can be None for "all upcoming"
        except (json.JSONDecodeError, TypeError):
            channel_id = view.get("private_metadata", "")
            selected_date = None

        if selected_date:
            try:
                date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
                schedules = services.schedule_manager.get_schedules_for_date(date_obj)
            except Exception:
                schedules = []
        else:
            # Show all upcoming schedules
            schedules = services.schedule_manager.get_all_upcoming_schedules()

        modal_view = ScheduleUI.create_schedule_tab_modal(
            schedules=schedules,
            selected_date=selected_date,
            channel_id=channel_id,
        )

        client.views_update(view_id=view_id, view=modal_view)

    @app.view("schedule_add_modal_submit")
    def handle_schedule_submit(ack, body, client, view, logger):
        """Handle schedule add modal submission."""
        values = view["state"]["values"]

        title = values["schedule_title_block"]["schedule_title_input"]["value"]
        channel_value = values["schedule_channel_block"]["schedule_channel_select"]["selected_option"]["value"]
        start_date = values["schedule_start_date_block"]["schedule_start_date_input"]["selected_date"]
        start_time = values["schedule_start_time_block"]["schedule_start_time_input"]["selected_time"]
        end_date = values["schedule_end_date_block"]["schedule_end_date_input"]["selected_date"]
        end_time = values["schedule_end_time_block"]["schedule_end_time_input"]["selected_time"]
        assignee_id = values["schedule_assignee_block"]["schedule_assignee_select"]["selected_user"]

        if ":" in channel_value:
            service, channel_id = channel_value.split(":", 1)
        else:
            service = "Unknown"
            channel_id = channel_value

        channel_name = channel_id
        try:
            channels = services.tencent_client.list_all_resources()
            for ch in channels:
                if ch.get("id") == channel_id:
                    channel_name = ch.get("name", channel_id)
                    break
        except Exception:
            pass

        assignee_name = assignee_id
        try:
            user_info = client.users_info(user=assignee_id)
            if user_info["ok"]:
                assignee_name = user_info["user"].get("real_name") or user_info["user"].get("name", assignee_id)
        except Exception:
            pass

        options_block = values.get("schedule_options_block", {}).get("schedule_options_input", {})
        selected_options = options_block.get("selected_options") or []
        option_values = [opt["value"] for opt in selected_options]

        notify_2h = "notify_2h" in option_values
        notify_30m = "notify_30m" in option_values

        notes_block = values.get("schedule_notes_block", {}).get("schedule_notes_input", {})
        notes = notes_block.get("value") or ""

        try:
            start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        except Exception as e:
            ack(response_action="errors", errors={"schedule_start_date_block": f"날짜/시간 형식 오류: {e}"})
            return

        if end_datetime <= start_datetime:
            ack(response_action="errors", errors={"schedule_end_date_block": "종료 시간은 시작 시간 이후여야 합니다."})
            return

        created_by = body["user"]["id"]

        result = services.schedule_manager.add_schedule(
            channel_id=channel_id,
            channel_name=channel_name,
            service=service,
            title=title,
            start_time=start_datetime,
            end_time=end_datetime,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            auto_start=False,
            auto_stop=False,
            notify_2h=notify_2h,
            notify_30m=notify_30m,
            created_by=created_by,
            notes=notes,
        )

        if not result["success"]:
            ack(response_action="errors", errors={"schedule_title_block": result.get("error", "등록 실패")})
            return

        ack()

        try:
            parent_metadata = json.loads(view.get("private_metadata", "{}"))
            slack_channel_id = parent_metadata.get("channel_id", "")
        except (json.JSONDecodeError, TypeError):
            slack_channel_id = ""

        if slack_channel_id:
            client.chat_postMessage(
                channel=slack_channel_id,
                text=f"새로운 스케줄이 등록되었습니다!\n"
                     f"*{title}* ({start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%H:%M')})\n"
                     f"채널: {channel_name} | 담당자: <@{assignee_id}>",
            )

    @app.action(re.compile(r"schedule_menu_.*"))
    def handle_schedule_menu(ack, body, client, logger):
        """Handle schedule overflow menu actions."""
        ack()

        action = body["actions"][0]
        selected_value = action["selected_option"]["value"]

        if ":" in selected_value:
            action_type, schedule_id = selected_value.split(":", 1)
        else:
            logger.error(f"Invalid schedule menu value: {selected_value}")
            return

        view = body["view"]
        view_id = view["id"]

        try:
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", "")
            selected_date = metadata.get("selected_date", datetime.now().strftime("%Y-%m-%d"))
        except (json.JSONDecodeError, TypeError):
            channel_id = ""
            selected_date = datetime.now().strftime("%Y-%m-%d")

        if action_type == "delete":
            result = services.schedule_manager.delete_schedule(schedule_id)

            if result["success"] and channel_id:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"스케줄이 삭제되었습니다: {result.get('message', schedule_id)}",
                )

            try:
                date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
                schedules = services.schedule_manager.get_schedules_for_date(date_obj)
            except Exception:
                schedules = []

            modal_view = ScheduleUI.create_schedule_tab_modal(
                schedules=schedules,
                selected_date=selected_date,
                channel_id=channel_id,
            )

            client.views_update(view_id=view_id, view=modal_view)

        elif action_type == "edit":
            user_id = body["user"]["id"]
            client.chat_postEphemeral(
                channel=channel_id or body.get("channel", {}).get("id", ""),
                user=user_id,
                text="스케줄 수정 기능은 곧 추가될 예정입니다.",
            )

    # Placeholder handlers for form elements
    @app.action("schedule_channel_select")
    def handle_channel_select(ack, body, client, logger):
        ack()

    @app.action("schedule_start_date_input")
    def handle_start_date(ack, body, client, logger):
        ack()

    @app.action("schedule_start_time_input")
    def handle_start_time(ack, body, client, logger):
        ack()

    @app.action("schedule_end_date_input")
    def handle_end_date(ack, body, client, logger):
        ack()

    @app.action("schedule_end_time_input")
    def handle_end_time(ack, body, client, logger):
        ack()

    @app.action("schedule_assignee_select")
    def handle_assignee(ack, body, client, logger):
        ack()

    @app.action("schedule_options_input")
    def handle_options(ack, body, client, logger):
        ack()

    @app.action("schedule_repeat_select")
    def handle_repeat(ack, body, client, logger):
        ack()
