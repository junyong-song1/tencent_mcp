"""Broadcast schedule management service."""
import logging
import threading
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

from app.models.schedule import BroadcastSchedule
from app.models.enums import ScheduleStatus
from app.storage.json_storage import ScheduleStorage

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Manager for broadcast schedules with storage abstraction."""

    def __init__(self, storage: Optional[ScheduleStorage] = None):
        """Initialize schedule manager.

        Args:
            storage: Storage backend (defaults to JSON file storage)
        """
        self._storage = storage or ScheduleStorage()
        self._lock = threading.Lock()
        self._schedules: Dict[str, BroadcastSchedule] = {}
        self._load_schedules()
        logger.info("ScheduleManager initialized")

    def _load_schedules(self) -> None:
        """Load schedules from storage."""
        data = self._storage.list_all()
        for schedule_id, schedule_data in data.items():
            try:
                schedule = BroadcastSchedule.from_dict(schedule_data)
                self._schedules[schedule_id] = schedule
            except Exception as e:
                logger.warning(f"Failed to load schedule {schedule_id}: {e}")
        logger.info(f"Loaded {len(self._schedules)} schedules")

    def _save_schedule(self, schedule: BroadcastSchedule) -> None:
        """Save a single schedule to storage."""
        self._storage.save(schedule.schedule_id, schedule.to_dict())

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
        auto_start: bool = False,
        auto_stop: bool = False,
        notify_2h: bool = True,
        notify_30m: bool = True,
        created_by: str = "",
        notes: str = "",
    ) -> Dict:
        """Add a new broadcast schedule."""
        if start_time <= datetime.now():
            return {
                "success": False,
                "error": "시작 시간은 현재 시간 이후여야 합니다.",
            }

        if end_time <= start_time:
            return {
                "success": False,
                "error": "종료 시간은 시작 시간 이후여야 합니다.",
            }

        schedule_id = str(uuid.uuid4())[:8]

        try:
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
        except ValueError as e:
            return {"success": False, "error": str(e)}

        with self._lock:
            self._schedules[schedule_id] = schedule

        self._save_schedule(schedule)
        logger.info(f"Added schedule {schedule_id}: {title} at {start_time}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "schedule": schedule.to_dict(),
            "message": f"'{title}' 스케줄이 등록되었습니다. ({start_time.strftime('%Y-%m-%d %H:%M')})",
        }

    def update_schedule(self, schedule_id: str, **kwargs) -> Dict:
        """Update an existing schedule."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "error": f"스케줄을 찾을 수 없습니다: {schedule_id}",
                }

            if schedule.status in [ScheduleStatus.COMPLETED, ScheduleStatus.CANCELLED]:
                return {
                    "success": False,
                    "error": f"이미 {schedule.status} 상태인 스케줄은 수정할 수 없습니다.",
                }

            allowed_fields = [
                "title", "start_time", "end_time", "assignee_id", "assignee_name",
                "auto_start", "auto_stop", "notify_2h", "notify_30m", "notes",
            ]

            for field_name, value in kwargs.items():
                if field_name in allowed_fields and value is not None:
                    setattr(schedule, field_name, value)

        self._save_schedule(schedule)
        logger.info(f"Updated schedule {schedule_id}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "스케줄이 수정되었습니다.",
        }

    def delete_schedule(self, schedule_id: str) -> Dict:
        """Delete (cancel) a schedule."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "error": f"스케줄을 찾을 수 없습니다: {schedule_id}",
                }

            schedule.status = ScheduleStatus.CANCELLED

        self._save_schedule(schedule)
        logger.info(f"Cancelled schedule {schedule_id}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": f"스케줄 '{schedule.title}'이(가) 취소되었습니다.",
        }

    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        """Get a single schedule by ID."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return None
            return schedule.to_dict()

    def get_schedules_for_date(
        self, target_date: date, include_cancelled: bool = False
    ) -> List[Dict]:
        """Get all schedules for a specific date."""
        result = []
        with self._lock:
            for schedule in self._schedules.values():
                if schedule.start_time.date() == target_date:
                    if not include_cancelled and schedule.status == ScheduleStatus.CANCELLED:
                        continue
                    result.append(schedule.to_dict())

        result.sort(key=lambda x: x["start_time_iso"])
        return result

    def get_schedules_for_range(
        self,
        start_date: date,
        end_date: date,
        include_cancelled: bool = False,
    ) -> List[Dict]:
        """Get all schedules within a date range."""
        result = []
        with self._lock:
            for schedule in self._schedules.values():
                schedule_date = schedule.start_time.date()
                if start_date <= schedule_date <= end_date:
                    if not include_cancelled and schedule.status == ScheduleStatus.CANCELLED:
                        continue
                    result.append(schedule.to_dict())

        result.sort(key=lambda x: x["start_time_iso"])
        return result

    def get_upcoming_schedules(self, hours: int = 24) -> List[Dict]:
        """Get schedules starting within the next N hours."""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        result = []

        with self._lock:
            for schedule in self._schedules.values():
                if schedule.status == ScheduleStatus.SCHEDULED:
                    if now < schedule.start_time <= cutoff:
                        result.append(schedule.to_dict())

        result.sort(key=lambda x: x["start_time_iso"])
        return result

    def get_all_upcoming_schedules(self) -> List[Dict]:
        """Get all schedules with start_time in the future."""
        now = datetime.now()
        result = []

        with self._lock:
            for schedule in self._schedules.values():
                if schedule.status in [ScheduleStatus.SCHEDULED, ScheduleStatus.ACTIVE]:
                    if schedule.start_time > now or schedule.end_time > now:
                        result.append(schedule.to_dict())

        result.sort(key=lambda x: x["start_time_iso"])
        return result

    def get_pending_notifications(self) -> Dict[str, List[Dict]]:
        """Get schedules that need notifications sent."""
        now = datetime.now()
        notify_2h = []
        notify_30m = []

        with self._lock:
            for schedule in self._schedules.values():
                if schedule.status != ScheduleStatus.SCHEDULED:
                    continue

                time_until_start = (schedule.start_time - now).total_seconds() / 60

                if schedule.notify_2h and not schedule.notified_2h:
                    if 115 <= time_until_start <= 125:
                        notify_2h.append(schedule.to_dict())

                if schedule.notify_30m and not schedule.notified_30m:
                    if 25 <= time_until_start <= 35:
                        notify_30m.append(schedule.to_dict())

        return {"notify_2h": notify_2h, "notify_30m": notify_30m}

    def get_auto_start_schedules(self) -> List[Dict]:
        """Get schedules that need auto-start."""
        now = datetime.now()
        result = []

        with self._lock:
            for schedule in self._schedules.values():
                if schedule.status != ScheduleStatus.SCHEDULED:
                    continue
                if not schedule.auto_start or schedule.auto_started:
                    continue

                time_until_start = (schedule.start_time - now).total_seconds() / 60
                if -2 <= time_until_start <= 2:
                    result.append(schedule.to_dict())

        return result

    def mark_notified(self, schedule_id: str, notification_type: str) -> bool:
        """Mark a schedule as notified."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return False

            if notification_type == "2h":
                schedule.notified_2h = True
            elif notification_type == "30m":
                schedule.notified_30m = True
            else:
                return False

        self._save_schedule(schedule)
        return True

    def mark_auto_started(self, schedule_id: str) -> bool:
        """Mark a schedule as auto-started."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return False
            schedule.auto_started = True
            schedule.status = ScheduleStatus.ACTIVE

        self._save_schedule(schedule)
        return True

    def mark_completed(self, schedule_id: str) -> bool:
        """Mark a schedule as completed."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return False
            schedule.status = ScheduleStatus.COMPLETED

        self._save_schedule(schedule)
        return True

    def cleanup_old_schedules(self, days: int = 30) -> int:
        """Remove old completed/cancelled schedules."""
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []

        with self._lock:
            for schedule_id, schedule in self._schedules.items():
                if schedule.status in [ScheduleStatus.COMPLETED, ScheduleStatus.CANCELLED]:
                    if schedule.start_time < cutoff:
                        to_remove.append(schedule_id)

            for schedule_id in to_remove:
                del self._schedules[schedule_id]
                self._storage.delete(schedule_id)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old schedules")

        return len(to_remove)


# Singleton instance for backward compatibility
_manager: Optional[ScheduleManager] = None


def get_schedule_manager() -> ScheduleManager:
    """Get the singleton schedule manager instance."""
    global _manager
    if _manager is None:
        _manager = ScheduleManager()
    return _manager
