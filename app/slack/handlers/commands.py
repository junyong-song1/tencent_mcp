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
        # User must be in ALLOWED_USERS or STREAMLINK_ONLY_USERS
        all_allowed_users = set(settings.allowed_users_list) | set(settings.streamlink_only_users_list)
        if all_allowed_users and user_id not in all_allowed_users:
            respond("접근 권한이 없습니다.")
            return

        cmd_parts = command_text.split()
        sub_cmd = cmd_parts[0].lower() if cmd_parts else "list"

        # Only block control-related sub-commands, not read-only commands like list, stats, trace
        read_only_commands = {"list", "ls", "dashboard", "", "schedule", "일정", "스케줄",
                             "stats", "통계", "stat", "trace", "chain", "추적", "help"}
        if sub_cmd not in read_only_commands and _contains_blocked_keywords(command_text):
            respond(
                ":no_entry_sign: *제어 명령어는 지원하지 않습니다*\n\n"
                "생성, 수정, 삭제 등의 제어 작업은 대시보드의 버튼을 통해 수행해 주세요.\n"
                "`/tencent` 명령어로 대시보드를 열어주세요."
            )
            return

        if sub_cmd in ["list", "ls", "dashboard", ""]:
            # Check if user is StreamLink-only user
            is_streamlink_only = settings.is_streamlink_only_user(user_id)

            try:
                # Show loading modal
                logger.info(f"/tencent: Opening loading modal... (streamlink_only={is_streamlink_only})")
                if is_streamlink_only:
                    loading_view = DashboardUI.create_streamlink_only_loading_modal(channel_id)
                else:
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
                        all_resources = services.tencent_client.list_all_resources()

                        if is_streamlink_only:
                            # StreamLink-only dashboard
                            flows = [r for r in all_resources if r.get("service") == "StreamLink"]
                            logger.info(f"/tencent: Got {len(flows)} StreamLink flows")

                            # Build flow to channel map (same hierarchy as full dashboard)
                            flow_to_channel_map = _build_flow_to_channel_map(
                                services, all_resources
                            )

                            modal_view = DashboardUI.create_streamlink_only_modal(
                                flows=flows,
                                flow_to_channel_map=flow_to_channel_map,
                                keyword=initial_keyword,
                                channel_id=channel_id,
                            )
                        else:
                            # Full dashboard
                            logger.info(f"/tencent: Got {len(all_resources)} resources, building modal...")
                            modal_view = DashboardUI.create_dashboard_modal(
                                channels=all_resources,
                                keyword=initial_keyword,
                                channel_id=channel_id,
                            )

                        logger.info(f"/tencent: Updating modal view...")
                        client.views_update(view_id=view_id, view=modal_view)
                        logger.info(f"/tencent: Modal updated successfully")
                    except Exception as e:
                        logger.error(f"Async dashboard load failed: {e}", exc_info=True)
                        callback_id = "streamlink_only_modal_view" if is_streamlink_only else "dashboard_modal_view"
                        client.views_update(
                            view_id=view_id,
                            view={
                                "type": "modal",
                                "callback_id": callback_id,
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

        elif sub_cmd in ["trace", "chain", "추적"]:
            # /tencent trace <channel_name> [--refresh]
            if len(cmd_parts) < 2:
                respond(
                    ":information_source: *사용법*: `/tencent trace <채널명>` [--refresh]\n"
                    "예시: `/tencent trace blackpaper`\n"
                    "예시: `/tencent trace blackpaper --refresh` (캐시 새로고침)\n\n"
                    "소스 체인을 추적하여 StreamLink → StreamLive → StreamPackage 연결 상태를 확인합니다."
                )
                return

            # Check for --refresh flag
            force_refresh = "--refresh" in cmd_parts or "-r" in cmd_parts
            search_parts = [p for p in cmd_parts[1:] if p not in ["--refresh", "-r"]]
            search_term = " ".join(search_parts)

            if force_refresh:
                respond(f":hourglass_flowing_sand: `{search_term}` 소스 체인을 추적하고 있습니다... (캐시 새로고침)")
            else:
                respond(f":hourglass_flowing_sand: `{search_term}` 소스 체인을 추적하고 있습니다...")

            def async_trace():
                try:
                    if force_refresh:
                        services.tencent_client.clear_cache()
                    blocks = _build_source_chain_blocks(services, search_term, force_refresh=force_refresh)
                    client.chat_postMessage(
                        channel=channel_id,
                        blocks=blocks,
                        text=f"Source Chain: {search_term}",
                    )
                except Exception as e:
                    logger.error(f"Failed to trace source chain: {e}", exc_info=True)
                    client.chat_postMessage(
                        channel=channel_id,
                        text=f":x: 소스 체인 추적 중 오류 발생: {str(e)}"
                    )

            threading.Thread(target=async_trace, daemon=True).start()

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
- `/tencent trace <채널명>` - 소스 체인 추적 (SRE 모니터링)
- `/tencent stats <flow_name>` - Flow 실시간 통계 조회
- `/tencent schedule` (또는 `일정`, `스케줄`) - 스케줄 관리 화면 열기
- `/tencent help` - 도움말 보기

*대시보드 기능:*
- 채널 탭: StreamLive/StreamLink 리소스 조회 및 제어
- 스케줄 탭: 방송 스케줄 관리 (추가/수정/삭제)
"""


def _build_flow_to_channel_map(services, all_resources: list, fetch_failover: bool = False) -> dict:
    """Build a map from flow_id to linked StreamLive channel info.

    Uses the same hierarchy logic as the full dashboard (ResourceHierarchyBuilder).

    Args:
        services: Services container
        all_resources: List of all resources (StreamLive + StreamLink)
        fetch_failover: If True, fetch failover status (slow). Default False for fast loading.

    Returns:
        {flow_id: {"channel_name": str, "channel_id": str, "active_input": str, "failover_info": dict}}
    """
    from app.services.linkage import ResourceHierarchyBuilder

    flow_to_channel_map = {}

    # Use the same hierarchy builder as the full dashboard
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(all_resources)

    # Process each group in hierarchy
    for group in hierarchy:
        parent = group["parent"]
        children = group["children"]

        # Skip if parent is StreamLink (unlinked flow - no parent channel)
        if parent.get("service") == "StreamLink":
            continue

        # Parent is StreamLive channel
        channel_id = parent.get("id", "")
        channel_name = parent.get("name", "")

        if children:
            active_input = None
            failover_info = {}

            # Only fetch failover status if requested (slow operation)
            if fetch_failover:
                try:
                    input_status = services.tencent_client.get_channel_input_status(channel_id)
                    active_input = input_status.get("active_input", "unknown") if input_status else "unknown"
                    failover_info = input_status.get("log_based_detection", {}) if input_status else {}
                except Exception as e:
                    logger.debug(f"Could not get input status for {channel_id}: {e}")
                    active_input = "unknown"

            # Map each child flow to this channel's info
            for flow in children:
                flow_id = flow.get("id", "")
                flow_to_channel_map[flow_id] = {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "active_input": active_input,
                    "failover_info": failover_info,
                }

    return flow_to_channel_map


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


def _build_source_chain_blocks(services, search_term: str, force_refresh: bool = False) -> list:
    """Build Slack blocks for source chain visualization."""
    from datetime import datetime
    from app.services.linkage import LinkageMatcher

    blocks = []
    status_emoji = {
        "running": ":large_green_circle:",
        "stopped": ":red_circle:",
        "idle": ":white_circle:",
        "error": ":warning:",
        "unknown": ":grey_question:",
    }

    # Get all resources (force_refresh if requested)
    all_resources = services.tencent_client.list_all_resources(force_refresh=force_refresh)
    streamlive_channels = [r for r in all_resources if r.get("service") == "StreamLive"]
    streamlink_flows = [r for r in all_resources if r.get("service") == "StreamLink"]

    # Find matching StreamLive channel
    search_lower = search_term.lower()
    matched_channel = None

    for ch in streamlive_channels:
        ch_name = ch.get("name", "").lower()
        ch_id = ch.get("id", "")
        if ch_id == search_term or ch_name == search_lower or search_lower in ch_name:
            matched_channel = ch
            break

    # If no StreamLive match, try StreamLink
    matched_flow = None
    if not matched_channel:
        for flow in streamlink_flows:
            flow_name = flow.get("name", "").lower()
            flow_id = flow.get("id", "")
            if flow_id == search_term or flow_name == search_lower or search_lower in flow_name:
                matched_flow = flow
                break

    if not matched_channel and not matched_flow:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":x: `{search_term}`와 일치하는 채널 또는 Flow를 찾을 수 없습니다."}
        }]

    # Header
    if matched_channel:
        title = matched_channel.get("name", "Unknown")
    else:
        title = matched_flow.get("name", "Unknown")

    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"🔗 Source Chain: {title}", "emoji": True}
    })
    blocks.append({"type": "divider"})

    # Find linked flows for the channel
    linked_flows = []
    if matched_channel:
        linked_flows = LinkageMatcher.find_linked_flows(matched_channel, streamlink_flows)
    elif matched_flow:
        linked_flows = [matched_flow]
        # Try to find the parent channel
        for ch in streamlive_channels:
            ch_linked = LinkageMatcher.find_linked_flows(ch, [matched_flow])
            if ch_linked:
                matched_channel = ch
                break

    # === StreamLink Flows ===
    if linked_flows:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📡 StreamLink Flows*"}
        })

        for flow in linked_flows:
            flow_name = flow.get("name", "Unknown")
            flow_id = flow.get("id", "")
            flow_status = flow.get("status", "unknown")
            emoji = status_emoji.get(flow_status, ":grey_question:")
            output_urls = flow.get("output_urls", [])
            monitor_url = flow.get("monitor_url")  # RTMP_PULL URL for playback

            flow_text = f"{emoji} *{flow_name}*\n"
            flow_text += f"└ ID: `{flow_id}`\n"
            flow_text += f"└ 상태: {flow_status}\n"

            if output_urls:
                for url in output_urls[:2]:
                    flow_text += f"└ Output: `{url[:60]}{'...' if len(url) > 60 else ''}`\n"

            # VLC playback - prefer monitor_url (RTMP_PULL) over output_urls
            if monitor_url:
                flow_text += f"└ 🎬 *모니터*: `{monitor_url}`\n"
                flow_text += f"└ 📋 VLC: `vlc \"{monitor_url}\"`\n"
            elif output_urls:
                first_url = output_urls[0]
                if "rtmp://" in first_url or "srt://" in first_url:
                    flow_text += f"└ ⚠️ _Push URL (재생 불가)_\n"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": flow_text}
            })

        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "↓"}]})

    # === StreamLive Channel ===
    if matched_channel:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📺 StreamLive Channel*"}
        })

        ch_name = matched_channel.get("name", "Unknown")
        ch_id = matched_channel.get("id", "")
        ch_status = matched_channel.get("status", "unknown")
        emoji = status_emoji.get(ch_status, ":grey_question:")

        ch_text = f"{emoji} *{ch_name}*\n"
        ch_text += f"└ ID: `{ch_id}`\n"
        ch_text += f"└ 상태: {ch_status}\n"

        # Get input status
        try:
            input_status = services.tencent_client.get_channel_input_status(ch_id)
            if input_status:
                active_input = input_status.get("active_input", "unknown")
                active_input_id = input_status.get("active_input_id")
                primary_input_id = input_status.get("primary_input_id")
                secondary_input_id = input_status.get("secondary_input_id")
                verification_sources = input_status.get("verification_sources", [])

                # Display active input with clear Main/Backup indicator
                if active_input == "main":
                    ch_text += f"└ 활성 입력: 🟢 *Main*\n"
                elif active_input == "backup":
                    ch_text += f"└ 활성 입력: 🟡 *Backup* (Failover)\n"
                elif active_input:
                    ch_text += f"└ 활성 입력: ⚪ {active_input}\n"

                # Show verification method
                if verification_sources:
                    ch_text += f"└ 검증: {', '.join(verification_sources)}\n"

                # Show input details with clear labels
                input_details = input_status.get("input_details", [])
                if input_details:
                    ch_text += f"└ 입력 목록:\n"
                    for inp in input_details[:4]:
                        inp_name = inp.get("name", "")
                        inp_id = inp.get("id", "")

                        # Determine role (Main/Backup)
                        role = ""
                        if inp_id == primary_input_id:
                            role = "(Main)"
                        elif inp_id == secondary_input_id:
                            role = "(Backup)"

                        # Check if active
                        is_active = inp_id == active_input_id
                        inp_emoji = "🟢" if is_active else "⚪"

                        # Display name and ID
                        if inp_name and inp_name != inp_id:
                            ch_text += f"   {inp_emoji} *{inp_name}* {role}\n"
                            ch_text += f"      `{inp_id}`\n"
                        else:
                            ch_text += f"   {inp_emoji} `{inp_id}` {role}\n"
        except Exception as e:
            logger.debug(f"Could not get input status: {e}")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ch_text}
        })

        # === StreamPackage ===
        try:
            sp_channels = services.tencent_client.list_streampackage_channels()

            # Try to find matching StreamPackage by name
            matched_sp = None
            for sp in sp_channels:
                sp_name = sp.get("name", "").lower()
                if search_lower in sp_name or ch_name.lower() in sp_name:
                    matched_sp = sp
                    break

            if matched_sp:
                # Only show arrow if StreamPackage exists
                blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "↓"}]})
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*📦 StreamPackage*"}
                })

                sp_name = matched_sp.get("name", "Unknown")
                sp_id = matched_sp.get("id", "")
                sp_status = matched_sp.get("status", "unknown")
                emoji = status_emoji.get(sp_status, ":grey_question:")

                sp_text = f"{emoji} *{sp_name}*\n"
                sp_text += f"└ ID: `{sp_id}`\n"

                # Get StreamPackage details for endpoints
                try:
                    sp_details = services.tencent_client.get_streampackage_channel_details(sp_id)
                    if sp_details:
                        input_details = sp_details.get("input_details", [])
                        for idx, inp in enumerate(input_details[:2]):
                            inp_name = inp.get("name", f"Input {idx+1}")
                            inp_url = inp.get("url", "")
                            if inp_url:
                                sp_text += f"└ {inp_name}: `{inp_url[:50]}...`\n"
                except Exception:
                    pass

                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": sp_text}
                })

                # HLS playback link (if available)
                # Note: Would need to get endpoint URL from StreamPackage API
                blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "💡 HLS 재생 URL은 StreamPackage 콘솔에서 확인하세요."}]
                })
        except Exception as e:
            logger.debug(f"Could not get StreamPackage info: {e}")

    # Timestamp
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"🕐 조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        ]
    })

    # Warning about content verification
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "⚠️ 콘텐츠 검증: 위 정보는 연결 상태만 표시합니다. 실제 콘텐츠 확인은 재생 링크로 직접 확인하세요."}
        ]
    })

    return blocks
