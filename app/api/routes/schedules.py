"""Schedule API endpoints."""
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_schedule_manager
from app.services.schedule_manager import ScheduleManager

router = APIRouter()


class ScheduleCreate(BaseModel):
    """Request body for creating a schedule."""

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
    created_by: str = ""
    notes: str = ""


class ScheduleUpdate(BaseModel):
    """Request body for updating a schedule."""

    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    auto_start: Optional[bool] = None
    auto_stop: Optional[bool] = None
    notify_2h: Optional[bool] = None
    notify_30m: Optional[bool] = None
    notes: Optional[str] = None


@router.get("")
async def list_schedules(
    date_str: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Range start (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Range end (YYYY-MM-DD)"),
    include_cancelled: bool = Query(False, description="Include cancelled schedules"),
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """List schedules with optional date filtering."""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            schedules = manager.get_schedules_for_date(target_date, include_cancelled)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    elif start_date and end_date:
        try:
            s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            schedules = manager.get_schedules_for_range(s_date, e_date, include_cancelled)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        # Default: upcoming 24 hours
        schedules = manager.get_upcoming_schedules(hours=24)

    return {
        "total": len(schedules),
        "schedules": schedules,
    }


@router.get("/upcoming")
async def get_upcoming_schedules(
    hours: int = Query(24, description="Hours to look ahead"),
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Get upcoming schedules."""
    schedules = manager.get_upcoming_schedules(hours=hours)
    return {
        "total": len(schedules),
        "schedules": schedules,
    }


@router.get("/pending-notifications")
async def get_pending_notifications(
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Get schedules that need notifications."""
    return manager.get_pending_notifications()


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Get a single schedule by ID."""
    schedule = manager.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("")
async def create_schedule(
    schedule_data: ScheduleCreate,
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Create a new schedule."""
    result = manager.add_schedule(
        channel_id=schedule_data.channel_id,
        channel_name=schedule_data.channel_name,
        service=schedule_data.service,
        title=schedule_data.title,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        assignee_id=schedule_data.assignee_id,
        assignee_name=schedule_data.assignee_name,
        auto_start=schedule_data.auto_start,
        auto_stop=schedule_data.auto_stop,
        notify_2h=schedule_data.notify_2h,
        notify_30m=schedule_data.notify_30m,
        created_by=schedule_data.created_by,
        notes=schedule_data.notes,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    updates: ScheduleUpdate,
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Update a schedule."""
    update_data = updates.model_dump(exclude_unset=True)
    result = manager.update_schedule(schedule_id, **update_data)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Delete (cancel) a schedule."""
    result = manager.delete_schedule(schedule_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.post("/{schedule_id}/mark-notified")
async def mark_schedule_notified(
    schedule_id: str,
    notification_type: str = Query(..., description="Notification type (2h, 30m)"),
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Mark a schedule as notified."""
    if notification_type not in ["2h", "30m"]:
        raise HTTPException(status_code=400, detail="Invalid notification type")

    success = manager.mark_notified(schedule_id, notification_type)
    return {"success": success}


@router.post("/cleanup")
async def cleanup_old_schedules(
    days: int = Query(30, description="Days to keep"),
    manager: ScheduleManager = Depends(get_schedule_manager),
):
    """Cleanup old schedules."""
    removed_count = manager.cleanup_old_schedules(days=days)
    return {"removed": removed_count}
