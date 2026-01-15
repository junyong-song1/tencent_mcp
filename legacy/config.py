"""Configuration management for Tencent MCP Slack Bot."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

    # Tencent Cloud SDK Configuration
    TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
    TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
    TENCENT_REGION = os.getenv("TENCENT_REGION", "ap-seoul")

    # Server Configuration
    PORT = int(os.getenv("PORT", 3000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Security
    ALLOWED_USERS = [
        user_id.strip()
        for user_id in os.getenv("ALLOWED_USERS", "").split(",")
        if user_id.strip()
    ]

    # ===== Performance Tuning =====

    # Cache TTL in seconds (how long to cache API responses)
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 120))

    # Thread pool max workers for parallel API calls
    THREAD_POOL_WORKERS = int(os.getenv("THREAD_POOL_WORKERS", 10))

    # HTTP request timeout for Tencent Cloud SDK (seconds)
    API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", 20))

    # ===== UI Limits =====

    # Maximum parent groups to display in modal
    MAX_PARENT_GROUPS = int(os.getenv("MAX_PARENT_GROUPS", 30))

    # Maximum resources for bulk operations
    MAX_BULK_OPERATIONS = int(os.getenv("MAX_BULK_OPERATIONS", 10))

    # ===== Notification Settings =====

    # Slack channel ID for broadcast schedule notifications (optional)
    NOTIFICATION_CHANNEL = os.getenv("NOTIFICATION_CHANNEL", "")

    # ===== Scheduler Settings =====

    # Cleanup interval for old tasks (seconds)
    SCHEDULER_CLEANUP_INTERVAL = int(os.getenv("SCHEDULER_CLEANUP_INTERVAL", 3600))

    # Max age of completed tasks before cleanup (hours)
    SCHEDULER_TASK_MAX_AGE_HOURS = int(os.getenv("SCHEDULER_TASK_MAX_AGE_HOURS", 24))

    # ===== Linkage Settings =====

    # Minimum stream key length to consider for matching
    MIN_STREAM_KEY_LENGTH = int(os.getenv("MIN_STREAM_KEY_LENGTH", 10))

    # Default SRT port
    DEFAULT_SRT_PORT = int(os.getenv("DEFAULT_SRT_PORT", 57716))

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        required_vars = [
            "SLACK_BOT_TOKEN",
            "SLACK_SIGNING_SECRET",
            "SLACK_APP_TOKEN",
            "TENCENT_SECRET_ID",
            "TENCENT_SECRET_KEY",
        ]

        missing = [var for var in required_vars if not getattr(cls, var)]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
