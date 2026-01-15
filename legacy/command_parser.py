"""Simple command parser for Slack bot messages."""
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent types."""
    SEARCH = "search"
    STATUS = "status"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result of parsing a user message."""
    intent: Intent
    keywords: List[str]
    service: Optional[str] = None  # "StreamLive", "StreamLink", or None for all
    raw_text: str = ""


class CommandParser:
    """
    Simple keyword-based command parser.
    No complex regex - just straightforward keyword matching.
    """

    # Keywords for each intent (Korean + English)
    INTENT_KEYWORDS = {
        Intent.START: ["시작", "start", "켜", "run", "실행"],
        Intent.STOP: ["중지", "stop", "꺼", "멈춰", "종료"],
        Intent.RESTART: ["재시작", "restart", "리스타트", "다시시작"],
        Intent.STATUS: ["상태", "status", "현황"],
        Intent.HELP: ["도움", "help", "도움말", "사용법"],
        Intent.SEARCH: ["검색", "찾아", "조회", "목록", "리스트", "list", "search", "find", "보여"],
    }

    # Service detection keywords
    SERVICE_KEYWORDS = {
        "StreamLive": ["streamlive", "라이브", "mdl", "live"],
        "StreamLink": ["streamlink", "링크", "mdc", "link"],
    }

    # Words to exclude from keyword extraction
    STOPWORDS = frozenset([
        # Korean
        "채널", "스트림", "검색", "찾아", "찾아줘", "조회", "해줘", "줘", "알려",
        "보여줘", "시작", "중지", "재시작", "목록", "리스트", "상태", "어때",
        "좀", "해", "보여", "을", "를", "의", "이", "가", "에", "로", "으로",
        # English
        "start", "stop", "restart", "search", "find", "list", "show",
        "get", "give", "tell", "channel", "stream", "flow", "the", "a", "an",
    ])

    def parse(self, text: str) -> ParseResult:
        """
        Parse user message to extract intent and keywords.

        Args:
            text: User's message text

        Returns:
            ParseResult with intent, keywords, and optional service filter
        """
        if not text or not text.strip():
            return ParseResult(intent=Intent.UNKNOWN, keywords=[], raw_text=text)

        text_lower = text.lower().strip()

        # 1. Detect intent (order matters - more specific first)
        intent = self._detect_intent(text_lower)

        # 2. Extract service filter
        service = self._detect_service(text_lower)

        # 3. Extract keywords
        keywords = self._extract_keywords(text)

        # 4. If no specific intent but has keywords, treat as search
        if intent == Intent.UNKNOWN and keywords:
            intent = Intent.SEARCH

        return ParseResult(
            intent=intent,
            keywords=keywords,
            service=service,
            raw_text=text
        )

    def _detect_intent(self, text: str) -> Intent:
        """Detect user intent from text."""
        # Check intents in priority order (control commands first)
        priority_order = [
            Intent.RESTART,  # Most specific
            Intent.START,
            Intent.STOP,
            Intent.STATUS,
            Intent.HELP,
            Intent.SEARCH,   # Least specific
        ]

        for intent in priority_order:
            keywords = self.INTENT_KEYWORDS.get(intent, [])
            if any(kw in text for kw in keywords):
                return intent

        return Intent.UNKNOWN

    def _detect_service(self, text: str) -> Optional[str]:
        """Detect service type from text."""
        for service, keywords in self.SERVICE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return service
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Extract words (Korean, English, numbers, hyphens, underscores)
        words = re.findall(r'[a-zA-Z0-9가-힣_-]+', text)

        # Filter out stopwords and short words
        keywords = [
            w for w in words
            if w.lower() not in self.STOPWORDS and len(w) > 1
        ]

        # Return up to 5 keywords
        return keywords[:5]


# Singleton instance for convenience
_parser = CommandParser()


def parse_command(text: str) -> ParseResult:
    """Convenience function to parse a command."""
    return _parser.parse(text)


# ===== Response Formatting =====

STATUS_EMOJI = {
    "running": "🟢",
    "idle": "🟡",
    "stopped": "🔴",
    "error": "🔴",
}


def format_search_result(channels: list) -> str:
    """Format search results for display."""
    if not channels:
        return "검색 결과가 없습니다."

    lines = [f"총 {len(channels)}개의 채널/스트림을 찾았습니다:\n"]
    for item in channels[:10]:
        emoji = STATUS_EMOJI.get(item.get("status", "").lower(), "⚪")
        lines.append(f"{emoji} **{item['name']}** ({item['service']}) - {item['status']}")

    if len(channels) > 10:
        lines.append(f"\n... 그 외 {len(channels) - 10}개")

    return "\n".join(lines)


def format_control_result(result: dict) -> str:
    """Format control result for display."""
    if result.get("success"):
        return f"✅ {result.get('message', '성공')}"
    return f"❌ {result.get('message', '실패')}"


def get_help_message() -> str:
    """Return help message for users."""
    return """사용 가능한 명령어:

**검색**
- `채널 검색` 또는 `목록` - 모든 채널/Flow 조회
- `TVING 검색` - TVING 키워드로 검색
- `StreamLink 목록` - StreamLink 서비스만 조회

**제어**
- 검색 결과의 버튼을 클릭하여 제어하세요.

**상태**
- `상태` 또는 `현황` - 전체 상태 조회"""


def get_control_help_message(action: str) -> str:
    """Return control help message."""
    action_kr = {"start": "시작", "stop": "중지", "restart": "재시작"}.get(action, action)
    return f"'{action_kr}' 명령은 대시보드 버튼을 통해서만 가능합니다. `/search`로 대시보드를 열어주세요."
