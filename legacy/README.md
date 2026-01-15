# Legacy Files

This folder contains the original monolithic implementation before the FastAPI migration.

## Migrated Files

| File | New Location | Description |
|------|--------------|-------------|
| `app_v2.py` | `app/main.py` + `app/slack/handlers/` | Main entry point (split into handlers) |
| `tencent_cloud_client.py` | `app/services/tencent_client.py` | Tencent Cloud API client |
| `slack_ui.py` | `app/slack/ui/` | Slack Block Kit UI components |
| `scheduler.py` | `app/services/scheduler.py` | APScheduler-based task scheduler |
| `broadcast_schedule.py` | `app/services/schedule_manager.py` | Schedule management service |
| `notification_service.py` | `app/services/notification.py` | Notification service |
| `linkage_service.py` | `app/services/linkage.py` | Resource linkage service |
| `command_parser.py` | `app/slack/command_parser.py` | Command parsing |
| `config.py` | `app/config.py` | Configuration (Pydantic BaseSettings) |

## Purpose

These files are kept for:
1. Reference during development
2. Supporting legacy tests in `tests/`
3. Rollback capability if needed

## Usage

The tests in `tests/` directory still import from these legacy files through `conftest.py` path configuration.

## Deprecation

These files are deprecated and should not be modified. All new development should be done in the `app/` directory.
