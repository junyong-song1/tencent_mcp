"""Alert monitoring service for StreamLive/StreamLink channels."""
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from app.config import get_settings
from app.services.scheduler import SchedulerService

try:
    from dateutil import parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-dateutil not available. Install with: pip install python-dateutil")

logger = logging.getLogger(__name__)


class AlertMonitorService:
    """
    Monitor StreamLive/StreamLink channels for alerts and send notifications.

    Supports:
    - Periodic polling of channel alerts via API
    - Webhook callbacks for stream push events (RTMP only)
    - Slack notifications for new alerts
    """

    # Alert types to monitor
    CRITICAL_ALERTS = {"No Input Data", "PipelineFailover"}
    WARNING_ALERTS = {"PipelineRecover", "StreamStop"}
    INFO_ALERTS = {"StreamStart"}

    def __init__(
        self,
        tencent_client: Any = None,
        slack_client: Any = None,
        scheduler: Optional[SchedulerService] = None,
        notification_channel: str = "",
        max_age_hours: int = 1,
    ):
        """
        Initialize the alert monitor service.

        Args:
            tencent_client: TencentCloudClient instance
            slack_client: Slack WebClient for sending messages
            scheduler: APScheduler service instance
            notification_channel: Slack channel ID for notifications
            max_age_hours: Only notify for alerts that occurred within this many hours; 0 = 24h
        """
        self.tencent_client = tencent_client
        self.slack_client = slack_client
        self.scheduler = scheduler
        self.notification_channel = notification_channel
        self._max_age_hours = max_age_hours if max_age_hours > 0 else 24

        # Track sent alerts to avoid duplicates
        # Key: "{channel_id}:{pipeline}:{alert_type}:{set_time}"
        self._sent_alerts: Set[str] = set()

        # Track last check time per channel
        self._last_check: Dict[str, datetime] = {}

        # Webhook key for signature verification
        self._webhook_key: str = ""

    def set_slack_client(self, slack_client: Any):
        """Set or update the Slack client."""
        self.slack_client = slack_client

    def set_notification_channel(self, channel_id: str):
        """Set or update the notification channel."""
        self.notification_channel = channel_id

    def set_webhook_key(self, key: str):
        """Set the webhook key for signature verification."""
        self._webhook_key = key

    def register_jobs(self, check_interval_minutes: int = 2):
        """
        Register periodic jobs with the scheduler.

        Args:
            check_interval_minutes: How often to check for alerts (default: 2 min)
        """
        if not self.scheduler:
            logger.warning("No scheduler provided, alert monitoring will not run automatically")
            return

        self.scheduler.add_interval_job(
            func=self.check_all_channel_alerts,
            job_id="alert_monitor_check",
            minutes=check_interval_minutes,
        )

        logger.info(f"Alert monitor jobs registered (interval: {check_interval_minutes} min)")

    def check_all_channel_alerts(self):
        """Check alerts for all running channels."""
        if not self.tencent_client:
            logger.debug("Tencent client not set, skipping alert check")
            return

        if not self.slack_client:
            logger.debug("Slack client not set, skipping alert check")
            return

        try:
            # Get all resources
            resources = self.tencent_client.list_all_resources()

            # Filter running StreamLive channels
            running_channels = [
                r for r in resources
                if r.get("service") in ["StreamLive", "MediaLive"]
                and r.get("status") == "running"
            ]

            logger.debug(f"Checking alerts for {len(running_channels)} running channels")

            for channel in running_channels:
                try:
                    self._check_channel_alerts(
                        channel_id=channel.get("id", ""),
                        channel_name=channel.get("name", ""),
                    )
                except Exception as e:
                    logger.error(f"Failed to check alerts for channel {channel.get('id')}: {e}")

        except Exception as e:
            logger.error(f"Error in alert check: {e}", exc_info=True)

    def _check_channel_alerts(self, channel_id: str, channel_name: str):
        """
        Check alerts for a specific channel.

        Args:
            channel_id: StreamLive channel ID
            channel_name: Channel display name
        """
        try:
            from tencentcloud.mdl.v20200326 import models as mdl_models

            client = self.tencent_client._get_mdl_client()

            # Get channel alerts
            alert_req = mdl_models.DescribeStreamLiveChannelAlertsRequest()
            alert_req.ChannelId = channel_id
            alert_resp = client.DescribeStreamLiveChannelAlerts(alert_req)

            if not alert_resp.Infos:
                return

            infos = alert_resp.Infos
            new_alerts = []

            # Check Pipeline0 alerts
            for alert in getattr(infos, 'Pipeline0', []) or []:
                if self._is_new_alert(channel_id, alert, "Pipeline0"):
                    new_alerts.append({
                        "pipeline": "Pipeline A (Main)",
                        "type": getattr(alert, 'Type', 'Unknown'),
                        "message": getattr(alert, 'Message', ''),
                        "set_time": getattr(alert, 'SetTime', ''),
                        "clear_time": getattr(alert, 'ClearTime', ''),
                    })

            # Check Pipeline1 alerts
            for alert in getattr(infos, 'Pipeline1', []) or []:
                if self._is_new_alert(channel_id, alert, "Pipeline1"):
                    new_alerts.append({
                        "pipeline": "Pipeline B (Backup)",
                        "type": getattr(alert, 'Type', 'Unknown'),
                        "message": getattr(alert, 'Message', ''),
                        "set_time": getattr(alert, 'SetTime', ''),
                        "clear_time": getattr(alert, 'ClearTime', ''),
                    })

            # Send notifications for new alerts
            for alert in new_alerts:
                self._send_alert_notification(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    alert=alert,
                )

        except Exception as e:
            logger.error(f"Failed to check alerts for {channel_id}: {e}")

    def _is_new_alert(self, channel_id: str, alert: Any, pipeline: str) -> bool:
        """
        Check if this alert is new (not previously sent) and active.

        Args:
            channel_id: Channel ID
            alert: Alert object from API
            pipeline: Pipeline identifier

        Returns:
            True if this is a new, active alert
        """
        alert_type = getattr(alert, 'Type', 'Unknown')
        set_time = getattr(alert, 'SetTime', '')
        clear_time = getattr(alert, 'ClearTime', '')

        # Skip alerts that are already cleared (resolved)
        if clear_time:
            logger.debug(f"Skipping cleared alert: {channel_id}:{alert_type} (cleared at {clear_time})")
            return False

        # Skip alerts that are too old (older than max_age_hours)
        # This prevents "same old alert" from being sent repeatedly throughout the day
        max_h = self._max_age_hours
        if DATEUTIL_AVAILABLE:
            try:
                if set_time:
                    set_datetime = parser.parse(set_time)
                    if set_datetime.tzinfo is None:
                        set_datetime = set_datetime.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age_hours = (now - set_datetime).total_seconds() / 3600
                    if age_hours > max_h:
                        logger.debug(
                            f"Skipping old alert: {channel_id}:{alert_type} (age: {age_hours:.1f}h > {max_h}h)"
                        )
                        return False
            except Exception as e:
                logger.debug(f"Could not parse set_time {set_time}: {e}")
        else:
            try:
                if set_time and "T" in set_time:
                    date_part = set_time.split("T")[0]
                    today = datetime.now(timezone.utc).date()
                    alert_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                    days_old = (today - alert_date).days
                    hours_cap_days = max(1, max_h // 24)
                    if days_old >= hours_cap_days:
                        logger.debug(
                            f"Skipping old alert: {channel_id}:{alert_type} (age: {days_old} days >= {hours_cap_days})"
                        )
                        return False
            except Exception:
                pass

        # Create unique key for this alert
        alert_key = f"{channel_id}:{pipeline}:{alert_type}:{set_time}"

        if alert_key in self._sent_alerts:
            return False

        # Mark as sent
        self._sent_alerts.add(alert_key)

        # Cleanup old entries (keep last 1000)
        if len(self._sent_alerts) > 1000:
            # Remove oldest entries (simple approach: clear half)
            self._sent_alerts = set(list(self._sent_alerts)[-500:])

        return True

    def _send_alert_notification(
        self,
        channel_id: str,
        channel_name: str,
        alert: Dict,
        use_detailed_format: bool = True,
    ):
        """
        Send an alert notification to Slack.

        Args:
            channel_id: Channel ID
            channel_name: Channel display name
            alert: Alert data dictionary
            use_detailed_format: Whether to use detailed alert format (default: True)
        """
        if not self.slack_client or not self.notification_channel:
            logger.warning("Slack client or notification channel not configured")
            return

        try:
            alert_type = alert.get("type", "Unknown")
            pipeline = alert.get("pipeline", "Unknown")
            set_time = alert.get("set_time", "")
            clear_time = alert.get("clear_time", "")
            message = alert.get("message", "")

            # Determine severity
            if alert_type in self.CRITICAL_ALERTS:
                severity = "critical"
            elif alert_type in self.WARNING_ALERTS:
                severity = "warning"
            else:
                severity = "info"

            # Use detailed format if enabled
            if use_detailed_format:
                from app.slack.ui.detailed_alert import create_channel_alert_blocks
                
                # Get additional channel information
                channel_details = None
                input_status = None
                streampackage_info = None
                css_info = None
                
                try:
                    if self.tencent_client:
                        # Get channel details
                        channel_details = self.tencent_client.get_resource_details(
                            channel_id, "StreamLive"
                        )
                        
                        # Get input status
                        input_status = self.tencent_client.get_channel_input_status(channel_id)
                        
                        # Extract StreamPackage info from input_status
                        if input_status and "streampackage_verification" in input_status:
                            streampackage_info = input_status["streampackage_verification"]
                        
                        # Extract CSS info from input_status
                        if input_status and "css_verification" in input_status:
                            css_info = input_status["css_verification"]
                except Exception as e:
                    logger.debug(f"Could not fetch additional channel info: {e}")

                # Create detailed alert blocks
                blocks = create_channel_alert_blocks(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    alert_type=alert_type,
                    alert_message=message,
                    severity=severity,
                    pipeline=pipeline,
                    set_time=set_time,
                    clear_time=clear_time,
                    channel_details=channel_details,
                    input_status=input_status,
                    streampackage_info=streampackage_info,
                    css_info=css_info,
                )
            else:
                # Fallback to simple format
                if alert_type in self.CRITICAL_ALERTS:
                    emoji = ":rotating_light:"
                    severity_display = "CRITICAL"
                elif alert_type in self.WARNING_ALERTS:
                    emoji = ":warning:"
                    severity_display = "WARNING"
                else:
                    emoji = ":information_source:"
                    severity_display = "INFO"

                # Format time
                if set_time and "T" in set_time:
                    set_time_display = set_time.replace("T", " ").replace("Z", " UTC")[:19]
                else:
                    set_time_display = set_time or "Unknown"

                # Build simple message blocks
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} StreamLive Alert: {alert_type}",
                            "emoji": True,
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*채널:*\n{channel_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*파이프라인:*\n{pipeline}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*심각도:*\n{severity_display}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*발생 시간:*\n{set_time_display}"
                            },
                        ]
                    },
                ]

                # Add message if available
                if message:
                    blocks.append({
                        "type": "context",
                        "elements": [{
                            "type": "mrkdwn",
                            "text": f"_{message}_"
                        }]
                    })

                # Add channel ID for reference
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"Channel ID: `{channel_id}`"
                    }]
                })

            # Send to Slack
            self.slack_client.chat_postMessage(
                channel=self.notification_channel,
                blocks=blocks,
                text=f"🚨 StreamLive Alert: {alert_type} - {channel_name}",
            )

            logger.info(f"Sent alert notification: {alert_type} for {channel_name}")

        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}", exc_info=True)

    def process_webhook_event(self, payload: Dict) -> Dict:
        """
        Process a webhook event from StreamLive.

        Webhook payload format:
        {
            "data": {
                "appid": 12345,
                "channel_id": "...",
                "event_type": 329 or 330,
                "input_id": "...",
                "interface": "general_callback",
                "pipeline": 0 or 1,
                "sign": "...",
                "stream_id": "",
                "t": 1234567890
            }
        }

        Event types:
        - 329: Stream push success (start)
        - 330: Stream push interrupted (stop)

        Args:
            payload: Webhook payload dictionary

        Returns:
            Processing result
        """
        try:
            data = payload.get("data", {})

            # Verify signature if key is configured
            if self._webhook_key:
                sign = data.get("sign", "")
                t = data.get("t", 0)
                expected_sign = hashlib.md5(f"{self._webhook_key}{t}".encode()).hexdigest()

                if sign != expected_sign:
                    logger.warning("Webhook signature verification failed")
                    return {"success": False, "error": "Invalid signature"}

                # Check timestamp (10 minute validity)
                current_time = int(datetime.now(timezone.utc).timestamp())
                if abs(current_time - t) > 600:
                    logger.warning("Webhook timestamp expired")
                    return {"success": False, "error": "Timestamp expired"}

            channel_id = data.get("channel_id", "")
            event_type = data.get("event_type", 0)
            input_id = data.get("input_id", "")
            pipeline = data.get("pipeline", 0)

            # Map event type to alert
            if event_type == 329:
                alert_type = "StreamStart"
                alert_message = "Stream push started"
            elif event_type == 330:
                alert_type = "StreamStop"
                alert_message = "Stream push interrupted"
            else:
                logger.debug(f"Unknown webhook event type: {event_type}")
                return {"success": True, "message": "Unknown event type, ignored"}

            # Get channel name
            channel_name = channel_id
            try:
                if self.tencent_client:
                    details = self.tencent_client.get_resource_details(channel_id, "StreamLive")
                    if details:
                        channel_name = details.get("name", channel_id)
            except Exception:
                pass

            # Send notification
            alert = {
                "pipeline": f"Pipeline {'A (Main)' if pipeline == 0 else 'B (Backup)'}",
                "type": alert_type,
                "message": alert_message,
                "set_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "input_id": input_id,
            }

            self._send_alert_notification(
                channel_id=channel_id,
                channel_name=channel_name,
                alert=alert,
            )

            return {"success": True, "message": f"Processed {alert_type} event"}

        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def check_now(self):
        """Force an immediate check (for testing or manual trigger)."""
        self.check_all_channel_alerts()


# Module-level singleton
_alert_monitor: Optional[AlertMonitorService] = None


def get_alert_monitor() -> Optional[AlertMonitorService]:
    """Get the singleton alert monitor instance."""
    return _alert_monitor


def init_alert_monitor(
    tencent_client: Any = None,
    slack_client: Any = None,
    scheduler: Optional[SchedulerService] = None,
    notification_channel: str = "",
    register_jobs: bool = True,
    check_interval_minutes: int = 2,
    max_age_hours: Optional[int] = None,
) -> AlertMonitorService:
    """
    Initialize the alert monitor service.

    Args:
        tencent_client: TencentCloudClient instance
        slack_client: Slack WebClient
        scheduler: APScheduler service instance
        notification_channel: Slack channel for notifications
        register_jobs: Whether to register periodic jobs
        check_interval_minutes: Polling interval (default: 2 min)
        max_age_hours: Only notify for alerts within this many hours; None = from config (default 1)

    Returns:
        AlertMonitorService instance
    """
    global _alert_monitor

    if max_age_hours is None:
        max_age_hours = get_settings().ALERT_MAX_AGE_HOURS

    _alert_monitor = AlertMonitorService(
        tencent_client=tencent_client,
        slack_client=slack_client,
        scheduler=scheduler,
        notification_channel=notification_channel,
        max_age_hours=max_age_hours,
    )

    if register_jobs and scheduler:
        _alert_monitor.register_jobs(check_interval_minutes)

    return _alert_monitor


def stop_alert_monitor():
    """Stop the alert monitor service."""
    global _alert_monitor
    _alert_monitor = None
