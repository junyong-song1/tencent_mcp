"""Broadcast schedule management module."""
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

# Default persistence file path
DEFAULT_SCHEDULES_FILE = Path(__file__).parent / "broadcast_schedules.json"


@dataclass
class BroadcastSchedule:
    """Represents a broadcast schedule entry."""
    schedule_id: str
    channel_id: str                    # Tencent channel/flow ID
    channel_name: str                  # Display name
    service: str                       # StreamLive or StreamLink
    title: str                         # Broadcast title (e.g., "KBO 개막전")
    start_time: datetime
    end_time: datetime
    assignee_id: str                   # Slack user ID
    assignee_name: str                 # Slack display name
    auto_start: bool = True            # Auto-start channel at start_time
    auto_stop: bool = False            # Auto-stop channel at end_time
    notify_2h: bool = True             # Notify 2 hours before
    notify_30m: bool = True            # Notify 30 minutes before (with status check)
    notified_2h: bool = False          # Already sent 2h notification
    notified_30m: bool = False         # Already sent 30m notification
    auto_started: bool = False         # Already auto-started
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""               # Slack user ID who created
    status: str = "scheduled"          # scheduled, active, completed, cancelled
    notes: str = ""                    # Optional notes


class BroadcastScheduleManager:
    """
    Manager for broadcast schedules.
    Handles CRUD operations and persistence.
    """

    def __init__(self, schedules_file: Path = None):
        """Initialize schedule manager."""
        self.schedules: Dict[str, BroadcastSchedule] = {}
        self._lock = threading.Lock()
        self._schedules_file = schedules_file or DEFAULT_SCHEDULES_FILE

        # Load persisted schedules
        self._load_schedules()
        logger.info(f"BroadcastScheduleManager initialized (persistence: {self._schedules_file})")

    def add_schedule(
        self,
        channel_id: str,
        channel_name: str,
        service: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        assignee_id: str,
        assignee_name: str,
        auto_start: bool = True,
        auto_stop: bool = False,
        notify_2h: bool = True,
        notify_30m: bool = True,
        created_by: str = "",
        notes: str = "",
    ) -> Dict:
        """
        Add a new broadcast schedule.

        Returns:
            Dict with success status and schedule info
        """
        # Validate times
        if start_time <= datetime.now():
            return {
                "success": False,
                "error": "시작 시간은 현재 시간 이후여야 합니다."
            }

        if end_time <= start_time:
            return {
                "success": False,
                "error": "종료 시간은 시작 시간 이후여야 합니다."
            }

        schedule_id = str(uuid.uuid4())[:8]
        schedule = BroadcastSchedule(
            schedule_id=schedule_id,
            channel_id=channel_id,
            channel_name=channel_name,
            service=service,
            title=title,
            start_time=start_time,
            end_time=end_time,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            auto_start=auto_start,
            auto_stop=auto_stop,
            notify_2h=notify_2h,
            notify_30m=notify_30m,
            created_by=created_by,
            notes=notes,
        )

        with self._lock:
            self.schedules[schedule_id] = schedule

        self._save_schedules()
        logger.info(f"Added schedule {schedule_id}: {title} at {start_time}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "schedule": self._schedule_to_dict(schedule),
            "message": f"'{title}' 스케줄이 등록되었습니다. ({start_time.strftime('%Y-%m-%d %H:%M')})"
        }

    def update_schedule(self, schedule_id: str, **kwargs) -> Dict:
        """Update an existing schedule."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "error": f"스케줄을 찾을 수 없습니다: {schedule_id}"
                }

            if schedule.status in ["completed", "cancelled"]:
                return {
                    "success": False,
                    "error": f"이미 {schedule.status} 상태인 스케줄은 수정할 수 없습니다."
                }

            # Update allowed fields
            allowed_fields = [
                "title", "start_time", "end_time", "assignee_id", "assignee_name",
                "auto_start", "auto_stop", "notify_2h", "notify_30m", "notes"
            ]
            for field_name, value in kwargs.items():
                if field_name in allowed_fields and value is not None:
                    setattr(schedule, field_name, value)

        self._save_schedules()
        logger.info(f"Updated schedule {schedule_id}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "스케줄이 수정되었습니다."
        }

    def delete_schedule(self, schedule_id: str) -> Dict:
        """Delete a schedule."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "error": f"스케줄을 찾을 수 없습니다: {schedule_id}"
                }

            # Mark as cancelled instead of deleting for history
            schedule.status = "cancelled"

        self._save_schedules()
        logger.info(f"Cancelled schedule {schedule_id}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": f"스케줄 '{schedule.title}'이(가) 취소되었습니다."
        }

    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        """Get a single schedule by ID."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return None
            return self._schedule_to_dict(schedule)

    def get_schedules_for_date(self, date: datetime.date, include_cancelled: bool = False) -> List[Dict]:
        """Get all schedules for a specific date."""
        result = []
        with self._lock:
            for schedule in self.schedules.values():
                if schedule.start_time.date() == date:
                    if not include_cancelled and schedule.status == "cancelled":
                        continue
                    result.append(self._schedule_to_dict(schedule))

        # Sort by start time
        result.sort(key=lambda x: x["start_time"])
        return result

    def get_schedules_for_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        include_cancelled: bool = False
    ) -> List[Dict]:
        """Get all schedules within a date range."""
        result = []
        with self._lock:
            for schedule in self.schedules.values():
                schedule_date = schedule.start_time.date()
                if start_date <= schedule_date <= end_date:
                    if not include_cancelled and schedule.status == "cancelled":
                        continue
                    result.append(self._schedule_to_dict(schedule))

        result.sort(key=lambda x: x["start_time"])
        return result

    def get_upcoming_schedules(self, hours: int = 24) -> List[Dict]:
        """Get schedules starting within the next N hours."""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        result = []

        with self._lock:
            for schedule in self.schedules.values():
                if schedule.status in ["scheduled"] and now < schedule.start_time <= cutoff:
                    result.append(self._schedule_to_dict(schedule))

        result.sort(key=lambda x: x["start_time"])
        return result

    def get_pending_notifications(self) -> Dict[str, List]:
        """
        Get schedules that need notifications sent.

        Returns:
            Dict with "notify_2h" and "notify_30m" lists
        """
        now = datetime.now()
        notify_2h = []
        notify_30m = []

        with self._lock:
            for schedule in self.schedules.values():
                if schedule.status != "scheduled":
                    continue

                time_until_start = (schedule.start_time - now).total_seconds() / 60  # in minutes

                # 2 hour notification (between 115-125 minutes before)
                if schedule.notify_2h and not schedule.notified_2h:
                    if 115 <= time_until_start <= 125:
                        notify_2h.append(self._schedule_to_dict(schedule))

                # 30 minute notification (between 25-35 minutes before)
                if schedule.notify_30m and not schedule.notified_30m:
                    if 25 <= time_until_start <= 35:
                        notify_30m.append(self._schedule_to_dict(schedule))

        return {
            "notify_2h": notify_2h,
            "notify_30m": notify_30m
        }

    def get_auto_start_schedules(self) -> List[Dict]:
        """Get schedules that need auto-start (within 2 minutes of start time)."""
        now = datetime.now()
        result = []

        with self._lock:
            for schedule in self.schedules.values():
                if schedule.status != "scheduled":
                    continue
                if not schedule.auto_start or schedule.auto_started:
                    continue

                time_until_start = (schedule.start_time - now).total_seconds() / 60
                # Auto-start within 2 minutes of scheduled time
                if -2 <= time_until_start <= 2:
                    result.append(self._schedule_to_dict(schedule))

        return result

    def mark_notified(self, schedule_id: str, notification_type: str) -> bool:
        """Mark a schedule as notified (2h or 30m)."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return False

            if notification_type == "2h":
                schedule.notified_2h = True
            elif notification_type == "30m":
                schedule.notified_30m = True
            else:
                return False

        self._save_schedules()
        return True

    def mark_auto_started(self, schedule_id: str) -> bool:
        """Mark a schedule as auto-started."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return False
            schedule.auto_started = True
            schedule.status = "active"

        self._save_schedules()
        return True

    def mark_completed(self, schedule_id: str) -> bool:
        """Mark a schedule as completed."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return False
            schedule.status = "completed"

        self._save_schedules()
        return True

    def cleanup_old_schedules(self, days: int = 30):
        """Remove old completed/cancelled schedules."""
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []

        with self._lock:
            for schedule_id, schedule in self.schedules.items():
                if schedule.status in ["completed", "cancelled"]:
                    if schedule.start_time < cutoff:
                        to_remove.append(schedule_id)

            for schedule_id in to_remove:
                del self.schedules[schedule_id]

        if to_remove:
            self._save_schedules()
            logger.info(f"Cleaned up {len(to_remove)} old schedules")

    def _schedule_to_dict(self, schedule: BroadcastSchedule) -> Dict:
        """Convert schedule to dictionary for JSON serialization."""
        return {
            "schedule_id": schedule.schedule_id,
            "channel_id": schedule.channel_id,
            "channel_name": schedule.channel_name,
            "service": schedule.service,
            "title": schedule.title,
            "start_time": schedule.start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": schedule.end_time.strftime("%Y-%m-%d %H:%M"),
            "start_time_iso": schedule.start_time.isoformat(),
            "end_time_iso": schedule.end_time.isoformat(),
            "assignee_id": schedule.assignee_id,
            "assignee_name": schedule.assignee_name,
            "auto_start": schedule.auto_start,
            "auto_stop": schedule.auto_stop,
            "notify_2h": schedule.notify_2h,
            "notify_30m": schedule.notify_30m,
            "notified_2h": schedule.notified_2h,
            "notified_30m": schedule.notified_30m,
            "auto_started": schedule.auto_started,
            "created_at": schedule.created_at.strftime("%Y-%m-%d %H:%M"),
            "created_by": schedule.created_by,
            "status": schedule.status,
            "notes": schedule.notes,
        }

    def _save_schedules(self):
        """Save schedules to JSON file."""
        try:
            schedules_data = []
            with self._lock:
                for schedule in self.schedules.values():
                    data = {
                        "schedule_id": schedule.schedule_id,
                        "channel_id": schedule.channel_id,
                        "channel_name": schedule.channel_name,
                        "service": schedule.service,
                        "title": schedule.title,
                        "start_time": schedule.start_time.isoformat(),
                        "end_time": schedule.end_time.isoformat(),
                        "assignee_id": schedule.assignee_id,
                        "assignee_name": schedule.assignee_name,
                        "auto_start": schedule.auto_start,
                        "auto_stop": schedule.auto_stop,
                        "notify_2h": schedule.notify_2h,
                        "notify_30m": schedule.notify_30m,
                        "notified_2h": schedule.notified_2h,
                        "notified_30m": schedule.notified_30m,
                        "auto_started": schedule.auto_started,
                        "created_at": schedule.created_at.isoformat(),
                        "created_by": schedule.created_by,
                        "status": schedule.status,
                        "notes": schedule.notes,
                    }
                    schedules_data.append(data)

            with open(self._schedules_file, 'w', encoding='utf-8') as f:
                json.dump(schedules_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved {len(schedules_data)} schedules to {self._schedules_file}")
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def _load_schedules(self):
        """Load schedules from JSON file."""
        if not self._schedules_file.exists():
            logger.info("No persisted schedules file found, starting fresh")
            return

        try:
            with open(self._schedules_file, 'r', encoding='utf-8') as f:
                schedules_data = json.load(f)

            loaded_count = 0
            for data in schedules_data:
                try:
                    schedule = BroadcastSchedule(
                        schedule_id=data["schedule_id"],
                        channel_id=data["channel_id"],
                        channel_name=data["channel_name"],
                        service=data["service"],
                        title=data["title"],
                        start_time=datetime.fromisoformat(data["start_time"]),
                        end_time=datetime.fromisoformat(data["end_time"]),
                        assignee_id=data["assignee_id"],
                        assignee_name=data["assignee_name"],
                        auto_start=data.get("auto_start", True),
                        auto_stop=data.get("auto_stop", False),
                        notify_2h=data.get("notify_2h", True),
                        notify_30m=data.get("notify_30m", True),
                        notified_2h=data.get("notified_2h", False),
                        notified_30m=data.get("notified_30m", False),
                        auto_started=data.get("auto_started", False),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        created_by=data.get("created_by", ""),
                        status=data.get("status", "scheduled"),
                        notes=data.get("notes", ""),
                    )

                    with self._lock:
                        self.schedules[schedule.schedule_id] = schedule
                    loaded_count += 1

                except Exception as e:
                    logger.warning(f"Failed to load schedule: {e}")

            logger.info(f"Loaded {loaded_count} schedules from {self._schedules_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schedules file: {e}")
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")


# Singleton instance
_schedule_manager: Optional[BroadcastScheduleManager] = None


def get_schedule_manager() -> BroadcastScheduleManager:
    """Get the singleton schedule manager instance."""
    global _schedule_manager
    if _schedule_manager is None:
        _schedule_manager = BroadcastScheduleManager()
    return _schedule_manager
