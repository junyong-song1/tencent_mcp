"""JSON file-based storage implementation."""
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseStorage
from app.config import get_settings

logger = logging.getLogger(__name__)


class JSONStorage(BaseStorage[Dict[str, Any]]):
    """Thread-safe JSON file storage."""

    def __init__(self, base_path: str = ".", filename: str = "data.json"):
        """Initialize JSON storage.

        Args:
            base_path: Base directory for storage files
            filename: Name of the JSON file
        """
        self.base_path = Path(base_path)
        self.filename = filename
        self.file_path = self.base_path / filename
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load data from JSON file."""
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(f"Loaded {len(self._data)} items from {self.file_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load {self.file_path}: {e}")
            self._data = {}

    def _save_to_disk(self) -> None:
        """Save data to JSON file."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self._data)} items to {self.file_path}")
        except IOError as e:
            logger.error(f"Failed to save {self.file_path}: {e}")

    def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save data with the given key."""
        with self._lock:
            self._data[key] = data
            self._save_to_disk()

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data by key."""
        with self._lock:
            return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete data by key."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._save_to_disk()
                return True
            return False

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """List all stored data."""
        with self._lock:
            return dict(self._data)

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            return key in self._data

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self._data = {}
            self._save_to_disk()

    def save_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Replace all data at once."""
        with self._lock:
            self._data = dict(data)
            self._save_to_disk()

    def update(self, key: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in an existing record."""
        with self._lock:
            if key in self._data:
                self._data[key].update(updates)
                self._save_to_disk()
                return True
            return False


class ScheduleStorage(JSONStorage):
    """Specialized storage for broadcast schedules."""

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = get_settings().DATA_DIR
        super().__init__(base_path, "broadcast_schedules.json")


class TaskStorage(JSONStorage):
    """Specialized storage for scheduled tasks."""

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = get_settings().DATA_DIR
        super().__init__(base_path, "scheduled_tasks.json")
