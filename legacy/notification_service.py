"""Background notification service for broadcast schedules."""
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from broadcast_schedule import get_schedule_manager
from slack_ui import SlackUI

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Background service that checks for pending notifications and auto-start schedules.
    Runs in a separate thread and checks every minute.
    """

    def __init__(
        self,
        slack_client,
        notification_channel: str,
        get_channel_status_callback: Optional[Callable] = None,
        auto_start_callback: Optional[Callable] = None,
        check_interval: int = 60,  # seconds
    ):
        """
        Initialize the notification service.

        Args:
            slack_client: Slack WebClient for sending messages
            notification_channel: Default Slack channel ID for notifications
            get_channel_status_callback: Callback to get current channel status
            auto_start_callback: Callback to auto-start a channel
            check_interval: How often to check for notifications (seconds)
        """
        self.slack_client = slack_client
        self.notification_channel = notification_channel
        self.get_channel_status = get_channel_status_callback
        self.auto_start_callback = auto_start_callback
        self.check_interval = check_interval

        self._schedule_manager = get_schedule_manager()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._slack_ui = SlackUI()

    def start(self):
        """Start the background notification checker thread."""
        if self._running:
            logger.warning("NotificationService is already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_checker, daemon=True)
        self._thread.start()
        logger.info("NotificationService started")

    def stop(self):
        """Stop the background notification checker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("NotificationService stopped")

    def _run_checker(self):
        """Main loop for checking notifications."""
        while self._running:
            try:
                self._check_notifications()
                self._check_auto_start()
            except Exception as e:
                logger.error(f"Error in notification checker: {e}", exc_info=True)

            # Sleep for the interval
            time.sleep(self.check_interval)

    def _check_notifications(self):
        """Check for pending notifications and send them."""
        pending = self._schedule_manager.get_pending_notifications()

        # Process 2-hour notifications
        for schedule in pending.get("notify_2h", []):
            self._send_notification(schedule, "2h")
            self._schedule_manager.mark_notified(schedule["schedule_id"], "2h")

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
            self._schedule_manager.mark_notified(schedule["schedule_id"], "30m")

    def _send_notification(
        self,
        schedule: dict,
        notification_type: str,
        channel_status: str = None
    ):
        """Send a notification message to Slack."""
        try:
            # Create notification blocks
            blocks = self._slack_ui.create_schedule_notification_blocks(
                schedule=schedule,
                notification_type=notification_type,
                channel_status=channel_status
            )

            assignee_id = schedule.get("assignee_id", "")

            # Send DM to assignee
            if assignee_id:
                try:
                    # Open DM channel with assignee
                    dm_response = self.slack_client.conversations_open(users=[assignee_id])
                    if dm_response["ok"]:
                        dm_channel = dm_response["channel"]["id"]
                        self.slack_client.chat_postMessage(
                            channel=dm_channel,
                            blocks=blocks,
                            text=f"방송 알림: {schedule.get('title', 'Untitled')}"
                        )
                        logger.info(f"Sent {notification_type} notification to {assignee_id} for {schedule['schedule_id']}")
                except Exception as e:
                    logger.error(f"Failed to send DM notification: {e}")

            # Also send to notification channel if configured
            if self.notification_channel:
                try:
                    # Add mention to assignee in channel message
                    channel_blocks = blocks.copy()
                    channel_blocks.append({
                        "type": "context",
                        "elements": [{
                            "type": "mrkdwn",
                            "text": f"cc: <@{assignee_id}>"
                        }]
                    })

                    self.slack_client.chat_postMessage(
                        channel=self.notification_channel,
                        blocks=channel_blocks,
                        text=f"방송 알림: {schedule.get('title', 'Untitled')} - <@{assignee_id}>"
                    )
                except Exception as e:
                    logger.error(f"Failed to send channel notification: {e}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

    def _check_auto_start(self):
        """Check for schedules that need auto-start."""
        if not self.auto_start_callback:
            return

        auto_start_schedules = self._schedule_manager.get_auto_start_schedules()

        for schedule in auto_start_schedules:
            try:
                logger.info(f"Auto-starting channel for schedule {schedule['schedule_id']}")

                # Call auto-start callback
                result = self.auto_start_callback(
                    schedule["channel_id"],
                    schedule["service"],
                    "start"
                )

                # Mark as auto-started regardless of result
                self._schedule_manager.mark_auto_started(schedule["schedule_id"])

                # Send notification about auto-start
                if self.notification_channel:
                    success = result.get("success", False)
                    status_emoji = "✅" if success else "❌"
                    message = result.get("message", "Unknown")

                    self.slack_client.chat_postMessage(
                        channel=self.notification_channel,
                        text=f"{status_emoji} *자동 시작* - {schedule.get('title', 'Untitled')}\n"
                             f"채널: {schedule.get('channel_name', 'Unknown')}\n"
                             f"결과: {message}\n"
                             f"담당자: <@{schedule.get('assignee_id', '')}>"
                    )

            except Exception as e:
                logger.error(f"Failed to auto-start schedule {schedule['schedule_id']}: {e}")

    def check_now(self):
        """Force an immediate check (for testing or manual trigger)."""
        self._check_notifications()
        self._check_auto_start()


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> Optional[NotificationService]:
    """Get the singleton notification service instance."""
    return _notification_service


def init_notification_service(
    slack_client,
    notification_channel: str,
    get_channel_status_callback: Callable = None,
    auto_start_callback: Callable = None,
) -> NotificationService:
    """
    Initialize and start the notification service.

    Args:
        slack_client: Slack WebClient
        notification_channel: Default channel for notifications
        get_channel_status_callback: Callback to get channel status
        auto_start_callback: Callback to auto-start channels

    Returns:
        NotificationService instance
    """
    global _notification_service

    if _notification_service is not None:
        logger.warning("NotificationService already initialized, stopping existing instance")
        _notification_service.stop()

    _notification_service = NotificationService(
        slack_client=slack_client,
        notification_channel=notification_channel,
        get_channel_status_callback=get_channel_status_callback,
        auto_start_callback=auto_start_callback,
    )
    _notification_service.start()

    return _notification_service


def stop_notification_service():
    """Stop the notification service."""
    global _notification_service
    if _notification_service:
        _notification_service.stop()
        _notification_service = None
