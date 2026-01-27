"""Configuration management using Pydantic BaseSettings."""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Slack Configuration
    SLACK_BOT_TOKEN: str = Field(..., description="Slack bot token (xoxb-...)")
    SLACK_SIGNING_SECRET: str = Field(..., description="Slack signing secret")
    SLACK_APP_TOKEN: str = Field(..., description="Slack app token (xapp-...)")

    # Tencent Cloud SDK Configuration
    TENCENT_SECRET_ID: str = Field(..., description="Tencent Cloud secret ID")
    TENCENT_SECRET_KEY: str = Field(..., description="Tencent Cloud secret key")
    TENCENT_REGION: str = Field(default="ap-seoul", description="Tencent Cloud region")

    # Server Configuration
    PORT: int = Field(default=8000, description="Server port")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # Security
    ALLOWED_USERS: str = Field(default="", description="Comma-separated allowed user IDs")

    # Performance Tuning
    CACHE_TTL_SECONDS: int = Field(default=120, description="Cache TTL in seconds")
    THREAD_POOL_WORKERS: int = Field(default=10, description="Thread pool max workers")
    API_REQUEST_TIMEOUT: int = Field(default=20, description="API request timeout in seconds")

    # UI Limits
    MAX_PARENT_GROUPS: int = Field(default=30, description="Max parent groups in modal")
    MAX_BULK_OPERATIONS: int = Field(default=10, description="Max bulk operations")

    # Notification Settings
    NOTIFICATION_CHANNEL: str = Field(default="", description="Notification channel ID")
    ALERT_CHECK_INTERVAL_MINUTES: int = Field(default=5, description="Alert check interval in minutes (1-60)")

    # Scheduler Settings
    SCHEDULER_CLEANUP_INTERVAL: int = Field(default=3600, description="Cleanup interval in seconds")
    SCHEDULER_TASK_MAX_AGE_HOURS: int = Field(default=24, description="Task max age in hours")

    # Linkage Settings
    MIN_STREAM_KEY_LENGTH: int = Field(default=10, description="Min stream key length for matching")
    DEFAULT_SRT_PORT: int = Field(default=57716, description="Default SRT port")

    # Data Storage
    DATA_DIR: str = Field(default="data", description="Data directory for JSON files")

    # AI Assistant (Claude API)
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic Claude API key for natural language queries")

    @property
    def allowed_users_list(self) -> List[str]:
        """Parse ALLOWED_USERS into a list."""
        if not self.ALLOWED_USERS:
            return []
        return [user_id.strip() for user_id in self.ALLOWED_USERS.split(",") if user_id.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Backward compatibility with old Config class
class Config:
    """Backward-compatible Config class wrapping Settings."""

    _settings: Optional[Settings] = None

    @classmethod
    def _get_settings(cls) -> Settings:
        if cls._settings is None:
            cls._settings = get_settings()
        return cls._settings

    @classmethod
    @property
    def SLACK_BOT_TOKEN(cls) -> str:
        return cls._get_settings().SLACK_BOT_TOKEN

    @classmethod
    @property
    def SLACK_SIGNING_SECRET(cls) -> str:
        return cls._get_settings().SLACK_SIGNING_SECRET

    @classmethod
    @property
    def SLACK_APP_TOKEN(cls) -> str:
        return cls._get_settings().SLACK_APP_TOKEN

    @classmethod
    @property
    def TENCENT_SECRET_ID(cls) -> str:
        return cls._get_settings().TENCENT_SECRET_ID

    @classmethod
    @property
    def TENCENT_SECRET_KEY(cls) -> str:
        return cls._get_settings().TENCENT_SECRET_KEY

    @classmethod
    @property
    def TENCENT_REGION(cls) -> str:
        return cls._get_settings().TENCENT_REGION

    @classmethod
    @property
    def PORT(cls) -> int:
        return cls._get_settings().PORT

    @classmethod
    @property
    def DEBUG(cls) -> bool:
        return cls._get_settings().DEBUG

    @classmethod
    @property
    def ALLOWED_USERS(cls) -> List[str]:
        return cls._get_settings().allowed_users_list

    @classmethod
    @property
    def CACHE_TTL_SECONDS(cls) -> int:
        return cls._get_settings().CACHE_TTL_SECONDS

    @classmethod
    @property
    def THREAD_POOL_WORKERS(cls) -> int:
        return cls._get_settings().THREAD_POOL_WORKERS

    @classmethod
    @property
    def API_REQUEST_TIMEOUT(cls) -> int:
        return cls._get_settings().API_REQUEST_TIMEOUT

    @classmethod
    @property
    def MAX_PARENT_GROUPS(cls) -> int:
        return cls._get_settings().MAX_PARENT_GROUPS

    @classmethod
    @property
    def MAX_BULK_OPERATIONS(cls) -> int:
        return cls._get_settings().MAX_BULK_OPERATIONS

    @classmethod
    @property
    def NOTIFICATION_CHANNEL(cls) -> str:
        return cls._get_settings().NOTIFICATION_CHANNEL

    @classmethod
    @property
    def SCHEDULER_CLEANUP_INTERVAL(cls) -> int:
        return cls._get_settings().SCHEDULER_CLEANUP_INTERVAL

    @classmethod
    @property
    def SCHEDULER_TASK_MAX_AGE_HOURS(cls) -> int:
        return cls._get_settings().SCHEDULER_TASK_MAX_AGE_HOURS

    @classmethod
    @property
    def MIN_STREAM_KEY_LENGTH(cls) -> int:
        return cls._get_settings().MIN_STREAM_KEY_LENGTH

    @classmethod
    @property
    def DEFAULT_SRT_PORT(cls) -> int:
        return cls._get_settings().DEFAULT_SRT_PORT

    @classmethod
    @property
    def DATA_DIR(cls) -> str:
        return cls._get_settings().DATA_DIR

    @classmethod
    def validate(cls):
        """Validate required configuration (Settings validates automatically)."""
        # Settings validates on instantiation via required fields
        cls._get_settings()
