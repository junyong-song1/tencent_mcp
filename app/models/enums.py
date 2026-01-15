"""Enumeration types for the application."""
from enum import Enum


class ServiceType(str, Enum):
    """Service type enumeration."""

    STREAMLIVE = "StreamLive"
    STREAMLINK = "StreamLink"


class ChannelStatus(str, Enum):
    """Channel status enumeration."""

    RUNNING = "running"
    IDLE = "idle"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class ScheduleStatus(str, Enum):
    """Broadcast schedule status enumeration."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Scheduled task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
