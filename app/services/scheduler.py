"""APScheduler-based scheduling service."""
import logging
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.models.schedule import BroadcastSchedule

logger = logging.getLogger(__name__)


class SchedulerService:
    """APScheduler-based scheduling service for channel operations."""

    def __init__(
        self,
        execute_callback: Optional[Callable] = None,
        use_async: bool = False,
    ):
        """Initialize scheduler service.

        Args:
            execute_callback: Callback for executing channel actions
            use_async: Use AsyncIOScheduler instead of BackgroundScheduler
        """
        self.execute_callback = execute_callback

        if use_async:
            self.scheduler = AsyncIOScheduler()
        else:
            self.scheduler = BackgroundScheduler()

        self._is_async = use_async
        logger.info(f"SchedulerService initialized (async={use_async})")

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started")

            # Add cleanup job
            self.scheduler.add_job(
                self._cleanup_old_jobs,
                trigger=IntervalTrigger(hours=1),
                id="cleanup_job",
                replace_existing=True,
            )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("APScheduler shutdown complete")

    def schedule_channel_action(
        self,
        schedule_id: str,
        channel_id: str,
        service: str,
        action: str,
        run_time: datetime,
        channel_name: str = "",
    ) -> str:
        """Schedule a channel action at a specific time.

        Args:
            schedule_id: Schedule ID for tracking
            channel_id: Channel/Flow ID
            service: Service type (StreamLive, StreamLink)
            action: Action to perform (start, stop)
            run_time: When to execute
            channel_name: Display name for logging

        Returns:
            Job ID
        """
        job_id = f"{action}_{schedule_id}"

        self.scheduler.add_job(
            self._execute_action,
            trigger=DateTrigger(run_date=run_time),
            id=job_id,
            args=[channel_id, service, action, channel_name],
            replace_existing=True,
        )

        logger.info(f"Scheduled {action} for {channel_name or channel_id} at {run_time}")
        return job_id

    def schedule_notification(
        self,
        schedule_id: str,
        notification_type: str,
        run_time: datetime,
        callback: Callable,
        schedule_data: dict,
    ) -> str:
        """Schedule a notification.

        Args:
            schedule_id: Schedule ID
            notification_type: "2h" or "30m"
            run_time: When to send notification
            callback: Function to call for sending notification
            schedule_data: Schedule data to pass to callback

        Returns:
            Job ID
        """
        job_id = f"notify_{notification_type}_{schedule_id}"

        self.scheduler.add_job(
            callback,
            trigger=DateTrigger(run_date=run_time),
            id=job_id,
            args=[schedule_data, notification_type],
            replace_existing=True,
        )

        logger.info(f"Scheduled {notification_type} notification for {schedule_id}")
        return job_id

    def schedule_periodic_check(
        self,
        job_id: str,
        callback: Callable,
        interval_seconds: int = 60,
    ) -> str:
        """Schedule a periodic check (e.g., for notifications).

        Args:
            job_id: Unique job identifier
            callback: Function to call periodically
            interval_seconds: Check interval

        Returns:
            Job ID
        """
        self.scheduler.add_job(
            callback,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            replace_existing=True,
        )

        logger.info(f"Scheduled periodic job {job_id} every {interval_seconds}s")
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel job {job_id}: {e}")
            return False

    def get_job(self, job_id: str):
        """Get a job by ID."""
        return self.scheduler.get_job(job_id)

    def get_jobs(self) -> list:
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        **kwargs,
    ) -> str:
        """Add an interval-based job.

        Args:
            func: Function to call periodically
            job_id: Unique job identifier
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            **kwargs: Additional arguments passed to the function

        Returns:
            Job ID
        """
        self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=seconds, minutes=minutes, hours=hours),
            id=job_id,
            replace_existing=True,
            **kwargs,
        )

        interval_str = []
        if hours:
            interval_str.append(f"{hours}h")
        if minutes:
            interval_str.append(f"{minutes}m")
        if seconds:
            interval_str.append(f"{seconds}s")

        logger.info(f"Added interval job {job_id} every {' '.join(interval_str) or '0s'}")
        return job_id

    def _execute_action(
        self,
        channel_id: str,
        service: str,
        action: str,
        channel_name: str = "",
    ) -> None:
        """Execute a scheduled channel action."""
        if self.execute_callback:
            try:
                result = self.execute_callback(channel_id, service, action)
                logger.info(
                    f"Executed {action} on {channel_name or channel_id}: "
                    f"{'success' if result.get('success') else 'failed'}"
                )
            except Exception as e:
                logger.error(f"Failed to execute {action} on {channel_id}: {e}")
        else:
            logger.warning("No execute callback configured")

    def _cleanup_old_jobs(self) -> None:
        """Cleanup job (APScheduler handles completed jobs automatically)."""
        logger.debug("Running scheduler cleanup")


# Singleton instance for backward compatibility
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service(
    execute_callback: Optional[Callable] = None,
) -> SchedulerService:
    """Get the singleton scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService(execute_callback=execute_callback)
    return _scheduler_service


def init_scheduler_service(execute_callback: Callable) -> SchedulerService:
    """Initialize and start the scheduler service."""
    global _scheduler_service
    _scheduler_service = SchedulerService(execute_callback=execute_callback)
    _scheduler_service.start()
    return _scheduler_service
