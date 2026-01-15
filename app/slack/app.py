"""Slack Bolt App instance."""
from slack_bolt import App

from app.config import get_settings

_app: App = None


def get_slack_app() -> App:
    """Get the Slack Bolt App instance."""
    global _app
    if _app is None:
        settings = get_settings()
        _app = App(token=settings.SLACK_BOT_TOKEN)
    return _app
