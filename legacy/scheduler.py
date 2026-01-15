"""Scheduler module for scheduled channel actions."""
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from config import Config

logger = logging.getLogger(__name__)

# Default persistence file path
DEFAULT_TASKS_FILE = Path(__file__).parent / "scheduled_tasks.json"


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    task_id: str
    channel_id: str
    channel_name: str
    service: str
    action: str  # start, stop
    scheduled_time: datetime
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    status: str = "pending"  # pending, running, completed, cancelled, failed
    result: Optional[str] = None
    timer: Optional[threading.Timer] = None


class TaskScheduler:
    """
    Scheduler for channel actions (start/stop).

    Supports scheduling actions at specific times or relative times.
    Persists tasks to JSON file for recovery after restart.
    """

    def __init__(self, execute_callback: Callable = None, tasks_file: Path = None):
        """
        Initialize scheduler.

        Args:
            execute_callback: Callback function to execute when task runs.
                              Signature: callback(channel_id, service, action) -> Dict
            tasks_file: Path to JSON file for task persistence (optional)
        """
        self.tasks: Dict[str, ScheduledTask] = {}
        self.execute_callback = execute_callback
        self._lock = threading.Lock()
        self._tasks_file = tasks_file or DEFAULT_TASKS_FILE

        # Load persisted tasks on startup
        self._load_tasks()

        # Start cleanup timer
        self._cleanup_timer = threading.Timer(Config.SCHEDULER_CLEANUP_INTERVAL, self._periodic_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

        logger.info(f"TaskScheduler initialized (persistence: {self._tasks_file})")

    def parse_time(self, time_str: str) -> Optional[datetime]:
        """
        Parse time string to datetime.

        Supports:
        - Absolute: "2024-01-15 14:30", "2024-01-15T14:30:00"
        - Relative Korean: "30분 후", "1시간 후", "2시간 30분 후"
        - Relative English: "in 30 minutes", "in 1 hour"
        - Tomorrow: "내일 09:00", "tomorrow 09:00"

        Args:
            time_str: Time string to parse

        Returns:
            datetime object or None if parsing fails
        """
        now = datetime.now()
        time_str = time_str.strip()

        # Try absolute datetime formats
        absolute_formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%m-%d %H:%M",
            "%H:%M",
        ]

        for fmt in absolute_formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                # Handle time-only format
                if fmt == "%H:%M":
                    parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                    if parsed < now:
                        parsed += timedelta(days=1)
                # Handle month-day format
                elif fmt == "%m-%d %H:%M":
                    parsed = parsed.replace(year=now.year)
                return parsed
            except ValueError:
                continue

        # Parse relative Korean time
        # "30분 후", "1시간 후", "1시간 30분 후"
        korean_pattern = r'(?:(\d+)\s*시간)?\s*(?:(\d+)\s*분)?\s*후'
        match = re.search(korean_pattern, time_str)
        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            if hours or minutes:
                return now + timedelta(hours=hours, minutes=minutes)

        # Parse relative English time
        # "in 30 minutes", "in 1 hour", "in 2 hours"
        english_pattern = r'in\s+(\d+)\s*(minute|minutes|hour|hours|min|hr)'
        match = re.search(english_pattern, time_str.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if 'hour' in unit or 'hr' in unit:
                return now + timedelta(hours=value)
            else:
                return now + timedelta(minutes=value)

        # Parse "내일" (tomorrow)
        tomorrow_pattern = r'내일\s*(\d{1,2}):(\d{2})'
        match = re.search(tomorrow_pattern, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Parse "tomorrow"
        tomorrow_en_pattern = r'tomorrow\s*(\d{1,2}):(\d{2})'
        match = re.search(tomorrow_en_pattern, time_str.lower())
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Parse simple "내일" without time
        if "내일" in time_str or "tomorrow" in time_str.lower():
            # Default to tomorrow 09:00
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

        logger.warning(f"Could not parse time string: {time_str}")
        return None

    def schedule_task(
        self,
        channel_id: str,
        channel_name: str,
        service: str,
        action: str,
        scheduled_time_str: str,
        created_by: str = "",
    ) -> Dict:
        """
        Schedule a task.

        Args:
            channel_id: Channel/flow ID
            channel_name: Channel/flow name for display
            service: Service name (MediaLive, MediaConnect, etc.)
            action: Action to perform (start, stop)
            scheduled_time_str: Time string (parsed by parse_time)
            created_by: User ID who created the task

        Returns:
            Dict with success status and task info
        """
        # Parse time
        scheduled_time = self.parse_time(scheduled_time_str)
        if not scheduled_time:
            return {
                "success": False,
                "error": f"시간을 파싱할 수 없습니다: {scheduled_time_str}",
            }

        # Validate time is in future
        if scheduled_time <= datetime.now():
            return {
                "success": False,
                "error": "예약 시간은 현재 시간 이후여야 합니다.",
            }

        # Create task
        task_id = str(uuid.uuid4())[:8]
        task = ScheduledTask(
            task_id=task_id,
            channel_id=channel_id,
            channel_name=channel_name,
            service=service,
            action=action,
            scheduled_time=scheduled_time,
            created_by=created_by,
        )

        # Calculate delay
        delay_seconds = (scheduled_time - datetime.now()).total_seconds()

        # Create timer
        timer = threading.Timer(delay_seconds, self._execute_task, args=[task_id])
        task.timer = timer

        # Store task
        with self._lock:
            self.tasks[task_id] = task

        # Start timer
        timer.start()

        # Persist to disk
        self._save_tasks()

        logger.info(
            f"Scheduled task {task_id}: {action} {service}:{channel_id} at {scheduled_time}"
        )

        return {
            "success": True,
            "task_id": task_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "service": service,
            "action": action,
            "scheduled_time": scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"'{channel_name}' {action} 작업이 {scheduled_time.strftime('%Y-%m-%d %H:%M')}에 예약되었습니다.",
        }

    def _execute_task(self, task_id: str):
        """Execute a scheduled task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "pending":
                return

            task.status = "running"

        logger.info(f"Executing scheduled task {task_id}: {task.action} {task.service}:{task.channel_id}")

        try:
            if self.execute_callback:
                result = self.execute_callback(task.channel_id, task.service, task.action)
                task.result = str(result)
                task.status = "completed" if result.get("success") else "failed"
            else:
                task.status = "failed"
                task.result = "No execute callback configured"
        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {e}")
            task.status = "failed"
            task.result = str(e)

        # Persist changes after execution
        self._save_tasks()

    def cancel_task(self, task_id: str) -> Dict:
        """
        Cancel a scheduled task.

        Args:
            task_id: Task ID to cancel

        Returns:
            Dict with success status
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return {
                    "success": False,
                    "error": f"작업을 찾을 수 없습니다: {task_id}",
                }

            if task.status != "pending":
                return {
                    "success": False,
                    "error": f"이미 {task.status} 상태인 작업은 취소할 수 없습니다.",
                }

            # Cancel timer
            if task.timer:
                task.timer.cancel()

            task.status = "cancelled"

        # Persist changes
        self._save_tasks()
        logger.info(f"Cancelled task {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": f"작업 {task_id}이(가) 취소되었습니다.",
        }

    def list_tasks(self, channel_id: str = None, include_completed: bool = False) -> List[Dict]:
        """
        List scheduled tasks.

        Args:
            channel_id: Filter by channel ID (optional)
            include_completed: Include completed/cancelled tasks

        Returns:
            List of task dictionaries
        """
        result = []

        with self._lock:
            for task in self.tasks.values():
                # Filter by status
                if not include_completed and task.status in ["completed", "cancelled", "failed"]:
                    continue

                # Filter by channel
                if channel_id and task.channel_id != channel_id:
                    continue

                result.append({
                    "task_id": task.task_id,
                    "channel_id": task.channel_id,
                    "channel_name": task.channel_name,
                    "service": task.service,
                    "action": task.action,
                    "scheduled_time": task.scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": task.status,
                    "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "created_by": task.created_by,
                })

        # Sort by scheduled time
        result.sort(key=lambda x: x["scheduled_time"])

        return result

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task details by ID."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            return {
                "task_id": task.task_id,
                "channel_id": task.channel_id,
                "channel_name": task.channel_name,
                "service": task.service,
                "action": task.action,
                "scheduled_time": task.scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": task.status,
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": task.created_by,
                "result": task.result,
            }

    def cleanup_old_tasks(self, max_age_hours: int = None):
        """Remove old completed/cancelled/failed tasks."""
        if max_age_hours is None:
            max_age_hours = Config.SCHEDULER_TASK_MAX_AGE_HOURS
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            to_remove = [
                task_id
                for task_id, task in self.tasks.items()
                if task.status in ["completed", "cancelled", "failed"]
                and task.created_at < cutoff
            ]

            for task_id in to_remove:
                del self.tasks[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")
            self._save_tasks()

    def shutdown(self):
        """Shutdown scheduler and cancel all pending tasks."""
        # Cancel cleanup timer
        if hasattr(self, '_cleanup_timer') and self._cleanup_timer:
            self._cleanup_timer.cancel()

        with self._lock:
            for task in self.tasks.values():
                if task.status == "pending" and task.timer:
                    task.timer.cancel()
                    task.status = "cancelled"

        # Save final state
        self._save_tasks()
        logger.info("TaskScheduler shutdown complete")

    # ===== Persistence Methods =====

    def _save_tasks(self):
        """Save tasks to JSON file for persistence."""
        try:
            tasks_data = []
            with self._lock:
                for task in self.tasks.values():
                    # Only save pending tasks (completed ones will be cleaned up)
                    if task.status == "pending":
                        tasks_data.append({
                            "task_id": task.task_id,
                            "channel_id": task.channel_id,
                            "channel_name": task.channel_name,
                            "service": task.service,
                            "action": task.action,
                            "scheduled_time": task.scheduled_time.isoformat(),
                            "created_at": task.created_at.isoformat(),
                            "created_by": task.created_by,
                            "status": task.status,
                        })

            with open(self._tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved {len(tasks_data)} pending tasks to {self._tasks_file}")
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    def _load_tasks(self):
        """Load tasks from JSON file and reschedule pending ones."""
        if not self._tasks_file.exists():
            logger.info("No persisted tasks file found, starting fresh")
            return

        try:
            with open(self._tasks_file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)

            now = datetime.now()
            restored_count = 0
            expired_count = 0

            for task_data in tasks_data:
                try:
                    scheduled_time = datetime.fromisoformat(task_data["scheduled_time"])
                    created_at = datetime.fromisoformat(task_data["created_at"])

                    # Skip tasks that have already passed
                    if scheduled_time <= now:
                        expired_count += 1
                        continue

                    # Recreate the task
                    task = ScheduledTask(
                        task_id=task_data["task_id"],
                        channel_id=task_data["channel_id"],
                        channel_name=task_data["channel_name"],
                        service=task_data["service"],
                        action=task_data["action"],
                        scheduled_time=scheduled_time,
                        created_at=created_at,
                        created_by=task_data.get("created_by", ""),
                        status="pending",
                    )

                    # Reschedule the timer
                    delay_seconds = (scheduled_time - now).total_seconds()
                    timer = threading.Timer(delay_seconds, self._execute_task, args=[task.task_id])
                    task.timer = timer

                    with self._lock:
                        self.tasks[task.task_id] = task

                    timer.start()
                    restored_count += 1

                except Exception as e:
                    logger.warning(f"Failed to restore task: {e}")

            logger.info(f"Restored {restored_count} pending tasks, skipped {expired_count} expired tasks")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tasks file: {e}")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    def _periodic_cleanup(self):
        """Periodically clean up old tasks and reschedule cleanup timer."""
        try:
            self.cleanup_old_tasks()
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {e}")

        # Reschedule cleanup timer
        self._cleanup_timer = threading.Timer(Config.SCHEDULER_CLEANUP_INTERVAL, self._periodic_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
