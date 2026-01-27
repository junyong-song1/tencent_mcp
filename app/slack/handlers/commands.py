"""Slack command handlers."""
import logging
import re
import threading

from slack_bolt import App

from app.slack.ui.dashboard import DashboardUI
from app.slack.ui.schedule import ScheduleUI

logger = logging.getLogger(__name__)

# 제어 명령어 차단 키워드 (생성/수정/삭제 관련)
BLOCKED_KEYWORDS = {
    # 생성 관련
    "생성", "만들기", "추가", "create", "add", "make", "new", "생성해", "만들어", "추가해",
    "생성해줘", "만들어줘", "추가해줘", "생성해주세요", "만들어주세요", "추가해주세요",
    # 수정 관련
    "수정", "변경", "업데이트", "modify", "update", "change", "edit", "수정해", "변경해",
    "수정해줘", "변경해줘", "업데이트해줘", "수정해주세요", "변경해주세요", "업데이트해주세요",
    # 삭제 관련
    "삭제", "지우기", "제거", "delete", "remove", "drop", "삭제해", "지워", "제거해",
    "삭제해줘", "지워줘", "제거해줘", "삭제해주세요", "지워주세요", "제거해주세요",
}


def _contains_blocked_keywords(text: str) -> bool:
    """Check if text contains blocked control keywords."""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # 키워드 확인
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # 정규식 패턴으로 더 정확한 검사 (예: "생성해줘", "수정해줘" 등)
    patterns = [
        r"생성\S*",
        r"만들\S*",
        r"추가\S*",
        r"수정\S*",
        r"변경\S*",
        r"업데이트\S*",
        r"삭제\S*",
        r"지우\S*",
        r"제거\S*",
        r"create\S*",
        r"add\S*",
        r"make\S*",
        r"new\S*",
        r"modify\S*",
        r"update\S*",
        r"change\S*",
        r"edit\S*",
        r"delete\S*",
        r"remove\S*",
        r"drop\S*",
    ]
    
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False


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

        # Block control commands (생성/수정/삭제)
        if _contains_blocked_keywords(command_text):
            respond(
                ":no_entry_sign: *제어 명령어는 지원하지 않습니다*\n\n"
                "생성, 수정, 삭제 등의 제어 작업은 대시보드의 버튼을 통해 수행해 주세요.\n"
                "`/tencent` 명령어로 대시보드를 열어주세요."
            )
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

        elif sub_cmd in ["schedule", "일정", "스케줄"]:
            try:
                # Get upcoming schedules
                schedules = services.schedule_manager.get_all_upcoming_schedules()

                modal_view = ScheduleUI.create_schedule_tab_modal(
                    schedules=schedules,
                    selected_date=None,  # Show all upcoming
                    channel_id=channel_id,
                )

                client.views_open(trigger_id=trigger_id, view=modal_view)

            except Exception as e:
                logger.error(f"Error opening schedule modal: {e}")
                respond(f"스케줄 화면 로드 중 오류 발생: {str(e)}")

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
- `/tencent schedule` (또는 `일정`, `스케줄`) - 스케줄 관리 화면 열기
- `/tencent help` - 도움말 보기

*대시보드 기능:*
- 채널 탭: StreamLive/StreamLink 리소스 조회 및 제어
- 스케줄 탭: 방송 스케줄 관리 (추가/수정/삭제)
"""
