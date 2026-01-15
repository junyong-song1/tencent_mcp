"""Scheduled task data model."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .enums import TaskStatus


class ScheduledTask(BaseModel):
    """Scheduled task for delayed channel operations."""

    task_id: str
    channel_id: str
    channel_name: str
    service: str
    action: str  # "start", "stop", "restart"
    scheduled_time: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result_message: Optional[str] = None
    executed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO format datetimes."""
        return {
            "task_id": self.task_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "service": self.service,
            "action": self.action,
            "scheduled_time_iso": self.scheduled_time.isoformat(),
            "created_at_iso": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "result_message": self.result_message,
            "executed_at_iso": self.executed_at.isoformat() if self.executed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        """Create from dictionary with ISO format datetimes."""
        executed_at = None
        if data.get("executed_at_iso"):
            executed_at = datetime.fromisoformat(data["executed_at_iso"])

        return cls(
            task_id=data["task_id"],
            channel_id=data["channel_id"],
            channel_name=data.get("channel_name", ""),
            service=data["service"],
            action=data["action"],
            scheduled_time=datetime.fromisoformat(data["scheduled_time_iso"]),
            created_at=datetime.fromisoformat(data.get("created_at_iso", datetime.now().isoformat())),
            created_by=data.get("created_by", ""),
            status=data.get("status", TaskStatus.PENDING),
            result_message=data.get("result_message"),
            executed_at=executed_at,
        )
