"""Notification service using APScheduler for background tasks."""
import logging
from datetime import datetime
from typing import Callable, Optional, Any

from app.services.schedule_manager import ScheduleManager
from app.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification service that integrates with APScheduler for periodic checks.

    Handles:
    - 2-hour advance notifications
    - 30-minute advance notifications with channel status
    - Auto-start functionality
    """

    def __init__(
        self,
        schedule_manager: ScheduleManager,
        slack_client: Optional[Any] = None,
        scheduler: Optional[SchedulerService] = None,
        notification_channel: str = "",
        get_channel_status_callback: Optional[Callable] = None,
        auto_start_callback: Optional[Callable] = None,
    ):
        """
        Initialize the notification service.

        Args:
            schedule_manager: Schedule manager instance
            slack_client: Slack WebClient for sending messages
            scheduler: APScheduler service instance
            notification_channel: Default Slack channel ID for notifications
            get_channel_status_callback: Callback to get current channel status
            auto_start_callback: Callback to auto-start a channel
        """
        self.schedule_manager = schedule_manager
        self.slack_client = slack_client
        self.scheduler = scheduler
        self.notification_channel = notification_channel
        self.get_channel_status = get_channel_status_callback
        self.auto_start_callback = auto_start_callback

    def set_slack_client(self, slack_client: Any):
        """Set or update the Slack client."""
        self.slack_client = slack_client

    def set_notification_channel(self, channel_id: str):
        """Set or update the notification channel."""
        self.notification_channel = channel_id

    def register_jobs(self, check_interval_minutes: int = 5):
        """
        Register periodic jobs with the scheduler.

        Args:
            check_interval_minutes: How often to check for notifications
        """
        if not self.scheduler:
            logger.warning("No scheduler provided, notifications will not run automatically")
            return

        # Register notification check job
        self.scheduler.add_interval_job(
            func=self.check_upcoming_schedules,
            job_id="notification_check",
            minutes=check_interval_minutes,
        )

        # Register auto-start check job
        self.scheduler.add_interval_job(
            func=self.check_auto_start,
            job_id="auto_start_check",
            minutes=1,
        )

        logger.info(f"Notification jobs registered (interval: {check_interval_minutes} min)")

    def check_upcoming_schedules(self):
        """Check for pending notifications and send them."""
        if not self.slack_client:
            logger.debug("Slack client not set, skipping notification check")
            return

        try:
            pending = self.schedule_manager.get_pending_notifications()

            # Process 2-hour notifications
            for schedule in pending.get("notify_2h", []):
                self._send_notification(schedule, "2h")
                self.schedule_manager.mark_notified(schedule["schedule_id"], "2h")

            # Process 30-minute notifications (with status check)
            for schedule in pending.get("notify_30m", []):
                channel_status = None
                if self.get_channel_status:
                    try:
                        channel_status = self.get_channel_status(
                            schedule["channel_id"],
                            schedule["service"]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get channel status: {e}")

                self._send_notification(schedule, "30m", channel_status)
                self.schedule_manager.mark_notified(schedule["schedule_id"], "30m")

        except Exception as e:
            logger.error(f"Error checking upcoming schedules: {e}", exc_info=True)

    def _send_notification(
        self,
        schedule: dict,
        notification_type: str,
        channel_status: str = None
    ):
        """
        Send a notification message to Slack.

        Args:
            schedule: Schedule data dictionary
            notification_type: "2h" or "30m"
            channel_status: Current status of the channel (optional)
        """
        if not self.slack_client:
            logger.warning("No Slack client, skipping notification")
            return

        try:
            blocks = self._create_notification_blocks(
                schedule=schedule,
                notification_type=notification_type,
                channel_status=channel_status
            )

            assignee_id = schedule.get("assignee_id", "")
            title = schedule.get("title", "Untitled")

            # Send DM to assignee
            if assignee_id:
                try:
                    dm_response = self.slack_client.conversations_open(users=[assignee_id])
                    if dm_response["ok"]:
                        dm_channel = dm_response["channel"]["id"]
                        self.slack_client.chat_postMessage(
                            channel=dm_channel,
                            blocks=blocks,
                            text=f"방송 알림: {title}"
                        )
                        logger.info(
                            f"Sent {notification_type} notification to {assignee_id} "
                            f"for {schedule['schedule_id']}"
                        )
                except Exception as e:
                    logger.error(f"Failed to send DM notification: {e}")

            # Also send to notification channel if configured
            if self.notification_channel:
                try:
                    channel_blocks = blocks.copy()
                    if assignee_id:
                        channel_blocks.append({
                            "type": "context",
                            "elements": [{
                                "type": "mrkdwn",
                                "text": f"cc: <@{assignee_id}>"
                            }]
                        })

                    text = f"방송 알림: {title}"
                    if assignee_id:
                        text += f" - <@{assignee_id}>"

                    self.slack_client.chat_postMessage(
                        channel=self.notification_channel,
                        blocks=channel_blocks,
                        text=text
                    )
                except Exception as e:
                    logger.error(f"Failed to send channel notification: {e}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

    def _create_notification_blocks(
        self,
        schedule: dict,
        notification_type: str,
        channel_status: str = None
    ) -> list:
        """
        Create Slack Block Kit blocks for notification.

        Args:
            schedule: Schedule data
            notification_type: "2h" or "30m"
            channel_status: Optional channel status

        Returns:
            List of Block Kit blocks
        """
        time_label = "2시간" if notification_type == "2h" else "30분"
        emoji = ":bell:" if notification_type == "2h" else ":rotating_light:"

        title = schedule.get("title", "Untitled")
        channel_name = schedule.get("channel_name", "Unknown")
        start_time = schedule.get("start_time", "")
        end_time = schedule.get("end_time", "")
        assignee_name = schedule.get("assignee_name", "")

        # Format times
        if isinstance(start_time, datetime):
            start_str = start_time.strftime("%H:%M")
        else:
            start_str = str(start_time)

        if isinstance(end_time, datetime):
            end_str = end_time.strftime("%H:%M")
        else:
            end_str = str(end_time)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} 방송 {time_label} 전 알림",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*제목:*\n{title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*채널:*\n{channel_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*시간:*\n{start_str} ~ {end_str}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*담당자:*\n{assignee_name}"
                    }
                ]
            }
        ]

        # Add channel status if available (for 30m notifications)
        if channel_status and notification_type == "30m":
            status_emoji = ":large_green_circle:" if channel_status.lower() == "running" else ":red_circle:"
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"{status_emoji} 채널 상태: *{channel_status}*"
                }]
            })

        return blocks

    def check_auto_start(self):
        """Check for schedules that need auto-start."""
        if not self.auto_start_callback:
            return

        if not self.slack_client:
            logger.debug("Slack client not set, skipping auto-start check")
            return

        try:
            auto_start_schedules = self.schedule_manager.get_auto_start_schedules()

            for schedule in auto_start_schedules:
                try:
                    logger.info(f"Auto-starting channel for schedule {schedule['schedule_id']}")

                    result = self.auto_start_callback(
                        schedule["channel_id"],
                        schedule["service"],
                        "start"
                    )

                    self.schedule_manager.mark_auto_started(schedule["schedule_id"])

                    # Send notification about auto-start
                    if self.notification_channel:
                        success = result.get("success", False)
                        status_emoji = ":white_check_mark:" if success else ":x:"
                        message = result.get("message", "Unknown")

                        self.slack_client.chat_postMessage(
                            channel=self.notification_channel,
                            text=(
                                f"{status_emoji} *자동 시작* - {schedule.get('title', 'Untitled')}\n"
                                f"채널: {schedule.get('channel_name', 'Unknown')}\n"
                                f"결과: {message}\n"
                                f"담당자: <@{schedule.get('assignee_id', '')}>"
                            )
                        )

                except Exception as e:
                    logger.error(f"Failed to auto-start schedule {schedule['schedule_id']}: {e}")

        except Exception as e:
            logger.error(f"Error in auto-start check: {e}", exc_info=True)

    def check_now(self):
        """Force an immediate check (for testing or manual trigger)."""
        self.check_upcoming_schedules()
        self.check_auto_start()


# Module-level singleton
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> Optional[NotificationService]:
    """Get the singleton notification service instance."""
    return _notification_service


def init_notification_service(
    schedule_manager: ScheduleManager,
    slack_client: Any = None,
    scheduler: Optional[SchedulerService] = None,
    notification_channel: str = "",
    get_channel_status_callback: Callable = None,
    auto_start_callback: Callable = None,
    register_jobs: bool = True,
) -> NotificationService:
    """
    Initialize the notification service.

    Args:
        schedule_manager: Schedule manager instance
        slack_client: Slack WebClient
        scheduler: APScheduler service instance
        notification_channel: Default channel for notifications
        get_channel_status_callback: Callback to get channel status
        auto_start_callback: Callback to auto-start channels
        register_jobs: Whether to register periodic jobs

    Returns:
        NotificationService instance
    """
    global _notification_service

    _notification_service = NotificationService(
        schedule_manager=schedule_manager,
        slack_client=slack_client,
        scheduler=scheduler,
        notification_channel=notification_channel,
        get_channel_status_callback=get_channel_status_callback,
        auto_start_callback=auto_start_callback,
    )

    if register_jobs and scheduler:
        _notification_service.register_jobs()

    return _notification_service


def stop_notification_service():
    """Stop the notification service (jobs are managed by scheduler)."""
    global _notification_service
    _notification_service = None
