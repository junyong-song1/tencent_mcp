"""Slack event handlers."""
from slack_bolt import App


def register_all_handlers(app: App, services):
    """Register all Slack handlers with the app.

    Args:
        app: Slack Bolt App instance
        services: ServiceContainer with all services
    """
    from . import commands, dashboard, schedule_tab, status_tab, control

    commands.register(app, services)
    dashboard.register(app, services)
    schedule_tab.register(app, services)
    status_tab.register(app, services)
    control.register(app, services)
