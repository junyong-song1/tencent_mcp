"""Tests for app.services.schedule_manager module."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.schedule_manager import ScheduleManager
from app.models.enums import ScheduleStatus


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    storage = Mock()
    storage.list_all.return_value = {}
    storage.save.return_value = None
    storage.delete.return_value = None
    return storage


@pytest.fixture
def schedule_manager(mock_storage):
    """Create ScheduleManager with mock storage."""
    return ScheduleManager(storage=mock_storage)


class TestScheduleManager:
    """Tests for ScheduleManager class."""

    def test_add_schedule_success(self, schedule_manager):
        """Test adding a valid schedule."""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=2)

        result = schedule_manager.add_schedule(
            channel_id="ch123",
            channel_name="Test Channel",
            service="StreamLive",
            title="Test Broadcast",
            start_time=start_time,
            end_time=end_time,
            assignee_id="U123",
            assignee_name="Test User",
        )

        assert result["success"] is True
        assert "schedule_id" in result
        assert "schedule" in result

    def test_add_schedule_past_start_time(self, schedule_manager):
        """Test that adding a schedule with past start time fails."""
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)

        result = schedule_manager.add_schedule(
            channel_id="ch123",
            channel_name="Test Channel",
            service="StreamLive",
            title="Test Broadcast",
            start_time=start_time,
            end_time=end_time,
            assignee_id="U123",
            assignee_name="Test User",
        )

        assert result["success"] is False
        assert "error" in result

    def test_add_schedule_end_before_start(self, schedule_manager):
        """Test that end time must be after start time."""
        start_time = datetime.now() + timedelta(hours=2)
        end_time = datetime.now() + timedelta(hours=1)

        result = schedule_manager.add_schedule(
            channel_id="ch123",
            channel_name="Test Channel",
            service="StreamLive",
            title="Test Broadcast",
            start_time=start_time,
            end_time=end_time,
            assignee_id="U123",
            assignee_name="Test User",
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_all_upcoming_schedules(self, schedule_manager):
        """Test getting all upcoming schedules."""
        # Add a schedule first
        start_time = datetime.now() + timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=2)

        schedule_manager.add_schedule(
            channel_id="ch123",
            channel_name="Test Channel",
            service="StreamLive",
            title="Test Broadcast",
            start_time=start_time,
            end_time=end_time,
            assignee_id="U123",
            assignee_name="Test User",
        )

        schedules = schedule_manager.get_all_upcoming_schedules()
        assert len(schedules) == 1
        assert schedules[0]["title"] == "Test Broadcast"

    def test_delete_schedule(self, schedule_manager):
        """Test deleting a schedule."""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=2)

        result = schedule_manager.add_schedule(
            channel_id="ch123",
            channel_name="Test Channel",
            service="StreamLive",
            title="Test Broadcast",
            start_time=start_time,
            end_time=end_time,
            assignee_id="U123",
            assignee_name="Test User",
        )

        schedule_id = result["schedule_id"]
        delete_result = schedule_manager.delete_schedule(schedule_id)

        assert delete_result["success"] is True

        # Schedule should be cancelled but still exist
        schedule = schedule_manager.get_schedule(schedule_id)
        assert schedule["status"] == ScheduleStatus.CANCELLED.value
