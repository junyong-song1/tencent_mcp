"""Natural language handler for Slack mentions.

Allows users to query Tencent Cloud status using natural language in Slack channels.
Uses Claude API with MCP tools for intelligent responses.
"""
import logging
import re
from typing import Optional, Dict, List

from slack_bolt import App

logger = logging.getLogger(__name__)


def _extract_channel_id(text: str) -> Optional[str]:
    """Extract channel ID from text (e.g., 'channel-123', 'sp-channel-456')."""
    # Match patterns like: channel-123, sp-channel-456, css-stream-name
    patterns = [
        r"(?:channel|ch|채널)[-:]?\s*([a-z0-9-]+)",
        r"(sp-channel|streampackage)[-:]?\s*([a-z0-9-]+)",
        r"([a-z0-9-]+channel[a-z0-9-]+)",
        r"([a-z0-9-]+-[0-9]+)",  # Generic ID pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if len(match.groups()) == 1 else match.group(2)
    
    return None


def _extract_keyword(text: str) -> Optional[str]:
    """Extract search keyword from text."""
    # Remove common query words
    query_words = [
        "상태", "확인", "조회", "보여", "알려", "status", "check", "show", "tell",
        "채널", "channel", "스트림", "stream", "플로우", "flow",
        "어떤", "무엇", "what", "which", "어디", "where",
        "해줘", "해주세요", "줘", "please",
    ]
    
    words = text.split()
    keywords = [w for w in words if w.lower() not in [qw.lower() for qw in query_words]]
    
    # Remove special characters and extract meaningful words
    meaningful = []
    for word in keywords:
        cleaned = re.sub(r'[^\w가-힣-]', '', word)
        if len(cleaned) >= 2:  # At least 2 characters
            meaningful.append(cleaned)
    
    return " ".join(meaningful[:3]) if meaningful else None  # Max 3 words


def _extract_service_type(text: str) -> Optional[str]:
    """Extract service type from text."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["streampackage", "패키지", "sp-"]):
        return "StreamPackage"
    elif any(word in text_lower for word in ["css", "live", "라이브"]):
        return "CSS"
    elif any(word in text_lower for word in ["streamlink", "링크", "mdc"]):
        return "StreamLink"
    elif any(word in text_lower for word in ["streamlive", "라이브", "mdl"]):
        return "StreamLive"
    
    return None


def _parse_natural_language_query(text: str) -> Dict:
    """Parse natural language query and extract intent."""
    text_lower = text.lower()
    
    # Check if it's a status query
    status_keywords = [
        "상태", "확인", "조회", "보여", "알려", "어떤", "무엇",
        "status", "check", "show", "tell", "what", "which",
        "실행", "동작", "작동", "running", "active", "활성",
    ]
    
    is_status_query = any(keyword in text_lower for keyword in status_keywords)
    
    # Extract channel ID
    channel_id = _extract_channel_id(text)
    
    # Extract keyword for search
    keyword = _extract_keyword(text) if not channel_id else None
    
    # Extract service type
    service_type = _extract_service_type(text)
    
    return {
        "is_status_query": is_status_query,
        "channel_id": channel_id,
        "keyword": keyword,
        "service_type": service_type,
    }


def _format_channel_status(channel: Dict, service: str) -> str:
    """Format channel status for Slack message."""
    name = channel.get("name", channel.get("id", "Unknown"))
    status = channel.get("status", "unknown")
    status_emoji = {
        "running": "🟢",
        "idle": "🟡",
        "stopped": "🔴",
        "error": "❌",
    }.get(status.lower(), "⚪")
    
    lines = [
        f"{status_emoji} *{name}* ({service})",
        f"   상태: {status}",
    ]
    
    # Add input status if available
    input_status = channel.get("input_status")
    if input_status:
        input_type = input_status.get("type", "unknown")
        input_emoji = "🟢" if input_type == "main" else "🟡"
        lines.append(f"   입력: {input_emoji} {input_type}")
    
    return "\n".join(lines)


def _format_search_results(resources: List[Dict], keyword: str) -> str:
    """Format search results for Slack message."""
    if not resources:
        return f":mag: '{keyword}' 검색 결과가 없습니다."
    
    lines = [f":mag: '{keyword}' 검색 결과 ({len(resources)}개):\n"]
    
    for resource in resources[:10]:  # Max 10 results
        name = resource.get("name", resource.get("id", "Unknown"))
        service = resource.get("service", "Unknown")
        status = resource.get("status", "unknown")
        status_emoji = {
            "running": "🟢",
            "idle": "🟡",
            "stopped": "🔴",
            "error": "❌",
        }.get(status.lower(), "⚪")
        
        lines.append(f"{status_emoji} *{name}* ({service}) - {status}")
    
    if len(resources) > 10:
        lines.append(f"\n... 외 {len(resources) - 10}개")
    
    return "\n".join(lines)


def register(app: App, services):
    """Register natural language handlers."""
    
    # Initialize AI Assistant if API key is available
    ai_assistant = None
    try:
        from app.services.ai_assistant import AIAssistant
        
        settings = services.settings
        if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            ai_assistant = AIAssistant(
                api_key=settings.ANTHROPIC_API_KEY,
                tencent_client=services.tencent_client,
                schedule_manager=services.schedule_manager,
            )
            logger.info("AI Assistant initialized with Claude API")
        else:
            logger.info("ANTHROPIC_API_KEY not set, using fallback keyword matching")
    except ImportError:
        logger.warning("Anthropic SDK not available, using fallback keyword matching")
    except Exception as e:
        logger.error(f"Failed to initialize AI Assistant: {e}")
    
    @app.event("app_mention")
    def handle_mention(event, client, say):
        """Handle bot mentions in Slack channels."""
        try:
            text = event.get("text", "").strip()
            user_id = event.get("user")
            channel_id = event.get("channel")
            
            # Remove bot mention from text
            text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
            
            if not text:
                say("안녕하세요! Tencent Cloud 상태를 확인해드릴 수 있습니다.\n"
                    "예: `KBO 채널 상태 확인해줘`, `channel-123 상태 알려줘`")
                return
            
            # Check user permission
            settings = services.settings
            if settings.allowed_users_list and user_id not in settings.allowed_users_list:
                say("접근 권한이 없습니다.")
                return
            
            # Use AI Assistant if available
            if ai_assistant:
                try:
                    response = ai_assistant.answer_query(text)
                    say(response)
                    return
                except Exception as e:
                    logger.error(f"AI Assistant error: {e}", exc_info=True)
                    # Fall through to keyword matching
            
            # Fallback to keyword matching
            # Parse natural language query
            query = _parse_natural_language_query(text)
            
            if not query["is_status_query"]:
                say("상태 확인 요청으로 이해했습니다. 다음 형식으로 질문해주세요:\n"
                    "• `KBO 채널 상태 확인해줘`\n"
                    "• `channel-123 상태 알려줘`\n"
                    "• `모든 채널 목록 보여줘`")
                return
            
            # Handle channel ID query
            if query["channel_id"]:
                channel_id_str = query["channel_id"]
                service_type = query["service_type"] or "StreamLive"
                
                # Try to get channel status
                try:
                    if service_type == "StreamPackage":
                        details = services.tencent_client.get_streampackage_channel_details(channel_id_str)
                    elif service_type == "CSS":
                        # For CSS, channel_id is actually stream_name
                        details = services.tencent_client.get_css_stream_details(channel_id_str)
                    else:
                        details = services.tencent_client.get_resource_details(channel_id_str, service_type)
                    
                    if details:
                        status_text = _format_channel_status(details, service_type)
                        say(status_text)
                    else:
                        say(f":question: `{channel_id_str}` 채널을 찾을 수 없습니다.")
                except Exception as e:
                    logger.error(f"Error getting channel status: {e}")
                    say(f":x: 채널 상태 조회 중 오류가 발생했습니다: {str(e)}")
            
            # Handle keyword search
            elif query["keyword"]:
                keyword = query["keyword"]
                try:
                    all_resources = services.tencent_client.list_all_resources()
                    
                    # Filter by keyword
                    matched = []
                    keyword_lower = keyword.lower()
                    for resource in all_resources:
                        name = resource.get("name", "").lower()
                        resource_id = resource.get("id", "").lower()
                        if keyword_lower in name or keyword_lower in resource_id:
                            matched.append(resource)
                    
                    if matched:
                        result_text = _format_search_results(matched, keyword)
                        say(result_text)
                    else:
                        say(f":mag: '{keyword}' 검색 결과가 없습니다.")
                except Exception as e:
                    logger.error(f"Error searching resources: {e}")
                    say(f":x: 검색 중 오류가 발생했습니다: {str(e)}")
            
            # Handle list all request
            else:
                try:
                    all_resources = services.tencent_client.list_all_resources()
                    
                    if not all_resources:
                        say(":information_source: 등록된 채널이 없습니다.")
                        return
                    
                    # Group by service
                    by_service = {}
                    for resource in all_resources:
                        service = resource.get("service", "Unknown")
                        if service not in by_service:
                            by_service[service] = []
                        by_service[service].append(resource)
                    
                    lines = [f":clipboard: 전체 채널 목록 ({len(all_resources)}개):\n"]
                    
                    for service, resources in by_service.items():
                        lines.append(f"\n*{service}* ({len(resources)}개):")
                        for resource in resources[:5]:  # Max 5 per service
                            name = resource.get("name", resource.get("id", "Unknown"))
                            status = resource.get("status", "unknown")
                            status_emoji = {
                                "running": "🟢",
                                "idle": "🟡",
                                "stopped": "🔴",
                                "error": "❌",
                            }.get(status.lower(), "⚪")
                            lines.append(f"  {status_emoji} {name} - {status}")
                        
                        if len(resources) > 5:
                            lines.append(f"  ... 외 {len(resources) - 5}개")
                    
                    say("\n".join(lines))
                except Exception as e:
                    logger.error(f"Error listing resources: {e}")
                    say(f":x: 채널 목록 조회 중 오류가 발생했습니다: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error handling mention: {e}", exc_info=True)
            say(":x: 요청 처리 중 오류가 발생했습니다. 다시 시도해주세요.")
