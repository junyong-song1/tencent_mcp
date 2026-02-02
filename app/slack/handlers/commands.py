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
        logger.info(f"/tencent command received")

        command_text = body.get("text", "").strip()
        channel_id = body["channel_id"]
        user_id = body["user_id"]
        trigger_id = body["trigger_id"]
        logger.info(f"/tencent: user={user_id}, text='{command_text}')")

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
                logger.info(f"/tencent: Opening loading modal...")
                loading_view = DashboardUI.create_loading_modal(channel_id)
                resp = client.views_open(trigger_id=trigger_id, view=loading_view)
                view_id = resp["view"]["id"]
                logger.info(f"/tencent: Loading modal opened, view_id={view_id}")

                # Parse initial keyword
                initial_keyword = ""
                if len(cmd_parts) > 1:
                    initial_keyword = " ".join(cmd_parts[1:])

                # Load resources in background
                def async_load():
                    try:
                        logger.info(f"/tencent: Fetching resources...")
                        channels = services.tencent_client.list_all_resources()
                        logger.info(f"/tencent: Got {len(channels)} resources, building modal...")
                        modal_view = DashboardUI.create_dashboard_modal(
                            channels=channels,
                            keyword=initial_keyword,
                            channel_id=channel_id,
                        )
                        logger.info(f"/tencent: Updating modal view...")
                        client.views_update(view_id=view_id, view=modal_view)
                        logger.info(f"/tencent: Modal updated successfully")
                    except Exception as e:
                        logger.error(f"Async dashboard load failed: {e}", exc_info=True)
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

        elif sub_cmd in ["stats", "통계", "stat"]:
            # /tencent stats <flow_name or flow_id>
            if len(cmd_parts) < 2:
                respond(
                    ":information_source: *사용법*: `/tencent stats <flow_name 또는 flow_id>`\n"
                    "예시: `/tencent stats my_flow_name`"
                )
                return

            search_term = " ".join(cmd_parts[1:])
            respond(f":hourglass_flowing_sand: `{search_term}` Flow 통계를 가져오고 있습니다...")

            def async_fetch_stats():
                try:
                    # Find the flow by name or ID
                    all_resources = services.tencent_client.list_all_resources()
                    flows = [r for r in all_resources if r.get("service") == "StreamLink"]

                    # Find matching flow
                    matched_flow = None
                    search_lower = search_term.lower()

                    for flow in flows:
                        flow_id = flow.get("id", "")
                        flow_name = flow.get("name", "")
                        if flow_id == search_term or flow_name.lower() == search_lower:
                            matched_flow = flow
                            break
                        elif search_lower in flow_name.lower():
                            matched_flow = flow

                    if not matched_flow:
                        client.chat_postMessage(
                            channel=channel_id,
                            text=f":x: Flow를 찾을 수 없습니다: `{search_term}`\n검색어를 확인해 주세요."
                        )
                        return

                    flow_id = matched_flow.get("id")
                    flow_name = matched_flow.get("name")
                    flow_status = matched_flow.get("status", "unknown")

                    # Get flow statistics
                    stats = services.tencent_client.get_flow_statistics(flow_id)

                    # Build response message
                    blocks = _build_flow_stats_blocks(flow_name, flow_id, flow_status, stats)

                    client.chat_postMessage(
                        channel=channel_id,
                        blocks=blocks,
                        text=f"Flow 통계: {flow_name}",
                    )

                except Exception as e:
                    logger.error(f"Failed to fetch flow stats: {e}", exc_info=True)
                    client.chat_postMessage(
                        channel=channel_id,
                        text=f":x: Flow 통계 조회 중 오류 발생: {str(e)}"
                    )

            threading.Thread(target=async_fetch_stats, daemon=True).start()

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
- `/tencent stats <flow_name>` - Flow 실시간 통계 조회
- `/tencent schedule` (또는 `일정`, `스케줄`) - 스케줄 관리 화면 열기
- `/tencent help` - 도움말 보기

*대시보드 기능:*
- 채널 탭: StreamLive/StreamLink 리소스 조회 및 제어
- 스케줄 탭: 방송 스케줄 관리 (추가/수정/삭제)
"""


def _build_flow_stats_blocks(flow_name: str, flow_id: str, status: str, stats: dict) -> list:
    """Build Slack blocks for flow statistics display."""
    status_emoji = {
        "running": ":large_green_circle:",
        "stopped": ":red_circle:",
        "idle": ":white_circle:",
        "error": ":warning:",
    }.get(status, ":grey_question:")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Flow: {flow_name}", "emoji": True}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Flow ID:*\n`{flow_id}`"},
                {"type": "mrkdwn", "text": f"*상태:*\n{status_emoji} {status}"},
            ]
        },
        {"type": "divider"},
    ]

    if not stats:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":information_source: 통계 정보를 가져올 수 없습니다.\nFlow가 실행 중이 아니거나 데이터가 없을 수 있습니다."}
        })
        return blocks

    # Input statistics section
    input_text = "*:inbox_tray: 입력 통계*\n"
    bitrate_mbps = stats.get("bitrate_mbps", "0")
    fps = stats.get("fps", 0)
    state = stats.get("state", "unknown")
    connected_time = stats.get("connected_time", "")

    input_text += f"- 비트레이트: *{bitrate_mbps} Mbps*\n"
    if fps > 0:
        input_text += f"- 프레임레이트: *{fps} fps*\n"
    input_text += f"- 연결 상태: {state}\n"
    if connected_time:
        input_text += f"- 연결 시간: {connected_time}\n"

    # Video/Audio codec info if available
    if stats.get("video_codec"):
        input_text += f"- 비디오 코덱: {stats['video_codec']}\n"
    if stats.get("audio_codec"):
        input_text += f"- 오디오 코덱: {stats['audio_codec']}\n"
    if stats.get("resolution"):
        input_text += f"- 해상도: {stats['resolution']}\n"

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": input_text}
    })

    # Input details (multiple sources)
    inputs = stats.get("inputs", [])
    if inputs:
        blocks.append({"type": "divider"})
        for idx, inp in enumerate(inputs[:3]):  # Limit to 3 inputs
            inp_bitrate = inp.get("bitrate_mbps", "0")
            inp_state = inp.get("state", "unknown")
            inp_id = inp.get("input_id", f"Input {idx+1}")

            state_emoji = ":large_green_circle:" if inp_state.lower() in ["running", "connected"] else ":white_circle:"
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"{state_emoji} *Input {inp_id}*: {inp_bitrate} Mbps ({inp_state})"}
                ]
            })

    # Output statistics section
    outputs = stats.get("outputs", [])
    if outputs:
        blocks.append({"type": "divider"})
        output_text = "*:outbox_tray: 출력 통계*\n"
        for idx, out in enumerate(outputs[:3]):  # Limit to 3 outputs
            out_bitrate = out.get("bitrate_mbps", "0")
            out_state = out.get("state", "unknown")
            out_id = out.get("output_id", f"Output {idx+1}")
            output_text += f"- Output {out_id}: {out_bitrate} Mbps ({out_state})\n"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": output_text}
        })

    # Timestamp
    blocks.append({"type": "divider"})
    from datetime import datetime
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        ]
    })

    return blocks
