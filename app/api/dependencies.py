"""FastAPI dependency injection setup."""
from functools import lru_cache
from typing import Optional

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.tencent_client import TencentCloudClient, AsyncTencentClient
from app.services.schedule_manager import ScheduleManager
from app.storage.json_storage import ScheduleStorage


def get_tencent_client(
    settings: Settings = Depends(get_settings),
) -> TencentCloudClient:
    """Get Tencent Cloud client instance."""
    return TencentCloudClient(
        secret_id=settings.TENCENT_SECRET_ID,
        secret_key=settings.TENCENT_SECRET_KEY,
        region=settings.TENCENT_REGION,
    )


def get_async_tencent_client(
    settings: Settings = Depends(get_settings),
) -> AsyncTencentClient:
    """Get async Tencent Cloud client instance."""
    sync_client = TencentCloudClient(
        secret_id=settings.TENCENT_SECRET_ID,
        secret_key=settings.TENCENT_SECRET_KEY,
        region=settings.TENCENT_REGION,
    )
    return AsyncTencentClient(sync_client)


def get_schedule_storage(
    settings: Settings = Depends(get_settings),
) -> ScheduleStorage:
    """Get schedule storage instance."""
    return ScheduleStorage(base_path=settings.DATA_DIR)


def get_schedule_manager(
    storage: ScheduleStorage = Depends(get_schedule_storage),
) -> ScheduleManager:
    """Get schedule manager instance."""
    return ScheduleManager(storage=storage)


class ServiceContainer:
    """Container for services used in Slack handlers.

    This is used because Slack Bolt handlers don't support FastAPI's
    dependency injection system directly.
    """

    _instance: Optional["ServiceContainer"] = None

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize service container."""
        self.settings = settings or get_settings()
        self._tencent_client: Optional[TencentCloudClient] = None
        self._schedule_manager: Optional[ScheduleManager] = None
        self._slack_client = None

    @property
    def tencent_client(self) -> TencentCloudClient:
        """Get Tencent Cloud client (lazy initialization)."""
        if self._tencent_client is None:
            self._tencent_client = TencentCloudClient(
                secret_id=self.settings.TENCENT_SECRET_ID,
                secret_key=self.settings.TENCENT_SECRET_KEY,
                region=self.settings.TENCENT_REGION,
            )
        return self._tencent_client

    @property
    def schedule_manager(self) -> ScheduleManager:
        """Get schedule manager (lazy initialization)."""
        if self._schedule_manager is None:
            storage = ScheduleStorage(base_path=self.settings.DATA_DIR)
            self._schedule_manager = ScheduleManager(storage=storage)
        return self._schedule_manager

    @property
    def slack_client(self):
        """Get Slack client (set externally)."""
        return self._slack_client

    @slack_client.setter
    def slack_client(self, client):
        """Set Slack client."""
        self._slack_client = client

    @classmethod
    def get_instance(cls) -> "ServiceContainer":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None


def get_service_container() -> ServiceContainer:
    """Get the service container singleton."""
    return ServiceContainer.get_instance()
