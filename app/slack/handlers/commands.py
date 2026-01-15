"""Slack command handlers."""
import logging
import threading

from slack_bolt import App

from app.slack.ui.dashboard import DashboardUI

logger = logging.getLogger(__name__)


def register(app: App, services):
    """Register command handlers."""

    @app.command("/tencent")
    def handle_tencent_command(ack, body, client, respond):
        """Handle /tencent slash command."""
        ack()

        command_text = body.get("text", "").strip()
        channel_id = body["channel_id"]
        user_id = body["user_id"]
        trigger_id = body["trigger_id"]

        # Check user permission
        settings = services.settings
        if settings.allowed_users_list and user_id not in settings.allowed_users_list:
            respond("접근 권한이 없습니다.")
            return

        cmd_parts = command_text.split()
        sub_cmd = cmd_parts[0].lower() if cmd_parts else "list"

        if sub_cmd in ["list", "ls", "dashboard", ""]:
            try:
                # Show loading modal
                loading_view = DashboardUI.create_loading_modal(channel_id)
                resp = client.views_open(trigger_id=trigger_id, view=loading_view)
                view_id = resp["view"]["id"]

                # Parse initial keyword
                initial_keyword = ""
                if len(cmd_parts) > 1:
                    initial_keyword = " ".join(cmd_parts[1:])

                # Load resources in background
                def async_load():
                    try:
                        channels = services.tencent_client.list_all_resources()
                        modal_view = DashboardUI.create_dashboard_modal(
                            channels=channels,
                            keyword=initial_keyword,
                            channel_id=channel_id,
                        )
                        client.views_update(view_id=view_id, view=modal_view)
                    except Exception as e:
                        logger.error(f"Async dashboard load failed: {e}")
                        client.views_update(
                            view_id=view_id,
                            view={
                                "type": "modal",
                                "callback_id": "dashboard_modal_view",
                                "private_metadata": channel_id,
                                "title": {"type": "plain_text", "text": "오류 발생"},
                                "close": {"type": "plain_text", "text": "닫기"},
                                "blocks": [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"대시보드 로드 중 오류가 발생했습니다: {str(e)}",
                                        },
                                    }
                                ],
                            },
                        )

                threading.Thread(target=async_load, daemon=True).start()

            except Exception as e:
                logger.error(f"Error opening loading modal: {e}")
                respond(f"대시보드 로드 중 오류 발생: {str(e)}")

        elif sub_cmd == "help":
            respond(_get_help_text())

        else:
            respond(_get_help_text())


def _get_help_text() -> str:
    """Get help text for the /tencent command."""
    return """*Tencent MCP Slack Bot*

*사용법:*
- `/tencent` 또는 `/tencent list` - 대시보드 열기
- `/tencent list <검색어>` - 채널 검색
- `/tencent help` - 도움말 보기

*대시보드 기능:*
- 채널 탭: StreamLive/StreamLink 리소스 조회 및 제어
- 스케줄 탭: 방송 스케줄 관리
- 상태 탭: 전체 시스템 현황
"""
