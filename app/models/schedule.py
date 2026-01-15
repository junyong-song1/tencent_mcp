"""Broadcast schedule data model."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enums import ScheduleStatus


class BroadcastSchedule(BaseModel):
    """Broadcast schedule entry."""

    schedule_id: str
    channel_id: str
    channel_name: str
    service: str
    title: str
    start_time: datetime
    end_time: datetime
    assignee_id: str
    assignee_name: str
    auto_start: bool = False
    auto_stop: bool = False
    notify_2h: bool = True
    notify_30m: bool = True
    notified_2h: bool = False
    notified_30m: bool = False
    auto_started: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = ""
    status: ScheduleStatus = ScheduleStatus.SCHEDULED
    notes: str = ""

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    class Config:
        use_enum_values = True

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO format datetimes."""
        return {
            "schedule_id": self.schedule_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "service": self.service,
            "title": self.title,
            "start_time_iso": self.start_time.isoformat(),
            "end_time_iso": self.end_time.isoformat(),
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "auto_start": self.auto_start,
            "auto_stop": self.auto_stop,
            "notify_2h": self.notify_2h,
            "notify_30m": self.notify_30m,
            "notified_2h": self.notified_2h,
            "notified_30m": self.notified_30m,
            "auto_started": self.auto_started,
            "created_at_iso": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BroadcastSchedule":
        """Create from dictionary with ISO format datetimes."""
        return cls(
            schedule_id=data["schedule_id"],
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            service=data["service"],
            title=data["title"],
            start_time=datetime.fromisoformat(data["start_time_iso"]),
            end_time=datetime.fromisoformat(data["end_time_iso"]),
            assignee_id=data["assignee_id"],
            assignee_name=data["assignee_name"],
            auto_start=data.get("auto_start", False),
            auto_stop=data.get("auto_stop", False),
            notify_2h=data.get("notify_2h", True),
            notify_30m=data.get("notify_30m", True),
            notified_2h=data.get("notified_2h", False),
            notified_30m=data.get("notified_30m", False),
            auto_started=data.get("auto_started", False),
            created_at=datetime.fromisoformat(data.get("created_at_iso", datetime.now().isoformat())),
            created_by=data.get("created_by", ""),
            status=data.get("status", ScheduleStatus.SCHEDULED),
            notes=data.get("notes", ""),
        )
