"""FastAPI application with Slack Bolt integration.

This is the main entry point for the Tencent MCP Slack Bot.
It integrates FastAPI for REST APIs with Slack Bolt for Slack interactions.
"""
import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.config import get_settings
from app.api.dependencies import ServiceContainer
from app.api.routes import health, resources, schedules, webhooks
from app.slack.handlers import register_all_handlers
from app.services.scheduler import SchedulerService
from app.services.notification import NotificationService, init_notification_service
from app.services.alert_monitor import AlertMonitorService, init_alert_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
_slack_handler: Optional[SocketModeHandler] = None
_slack_thread: Optional[threading.Thread] = None
_services: Optional[ServiceContainer] = None
_scheduler: Optional[SchedulerService] = None
_notification_service: Optional[NotificationService] = None
_alert_monitor: Optional[AlertMonitorService] = None


def create_slack_app() -> App:
    """Create and configure Slack Bolt App."""
    settings = get_settings()

    app = App(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET,
    )

    return app


def setup_scheduler(services: ServiceContainer) -> SchedulerService:
    """Set up APScheduler for background tasks."""
    settings = get_settings()

    def execute_task(task_id: str, action: str, resource_id: str, service_type: str):
        """Execute a scheduled task."""
        logger.info(f"Executing scheduled task {task_id}: {action} on {resource_id}")
        try:
            result = services.tencent_client.control_resource(
                resource_id, service_type, action
            )
            logger.info(f"Task {task_id} result: {result}")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")

    scheduler = SchedulerService(
        execute_callback=execute_task,
        use_async=False,  # Use BackgroundScheduler for thread safety
    )

    return scheduler


def setup_notification_service(
    scheduler: SchedulerService,
    services: ServiceContainer,
    slack_client=None,
) -> NotificationService:
    """Set up the notification service with APScheduler jobs."""
    settings = get_settings()

    def get_channel_status(channel_id: str, service: str) -> str:
        """Get channel status from Tencent Cloud."""
        try:
            details = services.tencent_client.get_resource_details(channel_id, service)
            return details.get("status", "unknown") if details else "unknown"
        except Exception:
            return "unknown"

    def auto_start_callback(channel_id: str, service: str, action: str) -> dict:
        """Auto-start a channel."""
        return services.tencent_client.control_resource(channel_id, service, action)

    notification_service = init_notification_service(
        schedule_manager=services.schedule_manager,
        slack_client=slack_client,
        scheduler=scheduler,
        notification_channel=settings.NOTIFICATION_CHANNEL if hasattr(settings, 'NOTIFICATION_CHANNEL') else "",
        get_channel_status_callback=get_channel_status,
        auto_start_callback=auto_start_callback,
        register_jobs=True,
    )

    return notification_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    global _slack_handler, _slack_thread, _services, _scheduler, _notification_service

    settings = get_settings()
    logger.info("Starting Tencent MCP Slack Bot...")

    # Initialize services
    _services = ServiceContainer()
    logger.info("Services initialized")

    # Prewarm Tencent Cloud cache
    try:
        _services.tencent_client.prewarm_cache()
        logger.info("Tencent Cloud cache prewarmed")
    except Exception as e:
        logger.warning(f"Cache prewarm failed: {e}")

    # Initialize scheduler
    _scheduler = setup_scheduler(_services)
    _scheduler.start()
    logger.info("Scheduler started")

    # Create and configure Slack app
    slack_app = create_slack_app()
    register_all_handlers(slack_app, _services)
    logger.info("Slack handlers registered")

    # Initialize notification service with Slack client
    _notification_service = setup_notification_service(
        scheduler=_scheduler,
        services=_services,
        slack_client=slack_app.client,
    )
    logger.info("Notification service initialized")

    # Initialize alert monitor service (periodic alert search can be disabled via ALERT_MONITOR_ENABLED)
    alert_monitor_enabled = getattr(settings, "ALERT_MONITOR_ENABLED", False)
    alert_check_interval = getattr(settings, "ALERT_CHECK_INTERVAL_MINUTES", 5)
    _alert_monitor = init_alert_monitor(
        tencent_client=_services.tencent_client,
        slack_client=slack_app.client,
        scheduler=_scheduler,
        notification_channel=settings.NOTIFICATION_CHANNEL if hasattr(settings, "NOTIFICATION_CHANNEL") else "",
        register_jobs=alert_monitor_enabled,
        check_interval_minutes=alert_check_interval,
    )
    if alert_monitor_enabled:
        logger.info(f"Alert monitor service initialized (interval: {alert_check_interval} min)")
    else:
        logger.info("Alert monitor service loaded; periodic alert search is disabled (ALERT_MONITOR_ENABLED=false)")

    # Start Slack Socket Mode in background thread
    _slack_handler = SocketModeHandler(slack_app, settings.SLACK_APP_TOKEN)

    def run_slack():
        try:
            _slack_handler.start()
        except Exception as e:
            logger.error(f"Slack handler error: {e}")

    _slack_thread = threading.Thread(target=run_slack, daemon=True)
    _slack_thread.start()
    logger.info("Slack Socket Mode handler started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")

    if _slack_handler:
        try:
            _slack_handler.close()
            logger.info("Slack handler closed")
        except Exception as e:
            logger.warning(f"Error closing Slack handler: {e}")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Tencent MCP Slack Bot",
        description="Slack Bot for managing Tencent Cloud StreamLive and StreamLink resources",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Include API routers
    app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
    app.include_router(resources.router, prefix="/api/v1/resources", tags=["resources"])
    app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    @app.get("/")
    async def root():
        return {
            "name": "Tencent MCP Slack Bot",
            "version": "2.0.0",
            "status": "running",
        }

    return app


# Create app instance
app = create_app()


def get_services() -> Optional[ServiceContainer]:
    """Get the global services container."""
    return _services


def get_scheduler() -> Optional[SchedulerService]:
    """Get the global scheduler."""
    return _scheduler


def get_notification_service() -> Optional[NotificationService]:
    """Get the global notification service."""
    return _notification_service


def get_alert_monitor() -> Optional[AlertMonitorService]:
    """Get the global alert monitor service."""
    return _alert_monitor


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
