"""Tests for command_parser module."""
import pytest
from command_parser import (
    CommandParser, Intent, ParseResult, parse_command,
    format_search_result, get_help_message, get_control_help_message
)


@pytest.fixture
def parser():
    return CommandParser()


class TestCommandParser:
    """Tests for CommandParser class."""

    def test_parse_empty_text(self, parser):
        """Empty text should return UNKNOWN intent."""
        result = parser.parse("")
        assert result.intent == Intent.UNKNOWN
        assert result.keywords == []

    def test_parse_whitespace_only(self, parser):
        """Whitespace-only text should return UNKNOWN intent."""
        result = parser.parse("   ")
        assert result.intent == Intent.UNKNOWN

    # Search intent tests
    def test_parse_search_korean(self, parser):
        """Korean search keywords should be detected."""
        result = parser.parse("채널 검색해줘")
        assert result.intent == Intent.SEARCH

    def test_parse_search_english(self, parser):
        """English search keywords should be detected."""
        result = parser.parse("search channels")
        assert result.intent == Intent.SEARCH

    def test_parse_search_with_keyword(self, parser):
        """Keywords should be extracted from search queries."""
        result = parser.parse("TVING 채널 찾아줘")
        assert result.intent == Intent.SEARCH
        assert "TVING" in result.keywords

    def test_parse_list_command(self, parser):
        """List command should trigger SEARCH intent."""
        result = parser.parse("목록")
        assert result.intent == Intent.SEARCH

    # Control intent tests
    def test_parse_start_korean(self, parser):
        """Korean start command should be detected."""
        result = parser.parse("채널 시작해줘")
        assert result.intent == Intent.START

    def test_parse_stop_korean(self, parser):
        """Korean stop command should be detected."""
        result = parser.parse("채널 중지해줘")
        assert result.intent == Intent.STOP

    def test_parse_restart_korean(self, parser):
        """Korean restart command should be detected."""
        result = parser.parse("재시작해줘")
        assert result.intent == Intent.RESTART

    def test_parse_start_english(self, parser):
        """English start command should be detected."""
        result = parser.parse("start channel")
        assert result.intent == Intent.START

    def test_parse_stop_english(self, parser):
        """English stop command should be detected."""
        result = parser.parse("stop channel")
        assert result.intent == Intent.STOP

    # Priority tests (restart > start > stop)
    def test_restart_priority_over_start(self, parser):
        """Restart should have higher priority than start."""
        result = parser.parse("재시작 시작")
        assert result.intent == Intent.RESTART

    # Status intent tests
    def test_parse_status_korean(self, parser):
        """Korean status command should be detected."""
        result = parser.parse("상태 확인")
        assert result.intent == Intent.STATUS

    def test_parse_status_english(self, parser):
        """English status command should be detected."""
        result = parser.parse("status check")
        assert result.intent == Intent.STATUS

    # Help intent tests
    def test_parse_help_korean(self, parser):
        """Korean help command should be detected."""
        result = parser.parse("도움말")
        assert result.intent == Intent.HELP

    def test_parse_help_english(self, parser):
        """English help command should be detected."""
        result = parser.parse("help")
        assert result.intent == Intent.HELP

    # Service detection tests
    def test_detect_streamlive_service(self, parser):
        """StreamLive service should be detected."""
        result = parser.parse("streamlive 채널 검색")
        assert result.service == "StreamLive"

    def test_detect_streamlink_service(self, parser):
        """StreamLink service should be detected."""
        result = parser.parse("streamlink 목록")
        assert result.service == "StreamLink"

    def test_detect_mdl_service(self, parser):
        """MDL keyword should map to StreamLive."""
        result = parser.parse("mdl 검색")
        assert result.service == "StreamLive"

    def test_detect_mdc_service(self, parser):
        """MDC keyword should map to StreamLink."""
        result = parser.parse("mdc 검색")
        assert result.service == "StreamLink"

    def test_no_service_filter(self, parser):
        """No service keywords should return None."""
        result = parser.parse("채널 검색")
        assert result.service is None

    # Keyword extraction tests
    def test_extract_keywords_multiple(self, parser):
        """Multiple keywords should be extracted."""
        result = parser.parse("TVING KBO 채널 찾아줘")
        assert "TVING" in result.keywords
        assert "KBO" in result.keywords

    def test_extract_keywords_limit(self, parser):
        """Keywords should be limited to 5."""
        result = parser.parse("one two three four five six seven eight")
        assert len(result.keywords) <= 5

    def test_stopwords_filtered(self, parser):
        """Stopwords should be filtered out."""
        result = parser.parse("채널 검색 해줘 줘 좀")
        assert "해줘" not in result.keywords
        assert "줘" not in result.keywords

    # Keyword-only search
    def test_keyword_only_triggers_search(self, parser):
        """Just a keyword should trigger search."""
        result = parser.parse("blackpaper")
        assert result.intent == Intent.SEARCH
        assert "blackpaper" in result.keywords


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_parse_command_function(self):
        """parse_command should work like parser.parse."""
        result = parse_command("채널 검색")
        assert isinstance(result, ParseResult)
        assert result.intent == Intent.SEARCH

    def test_format_search_result_empty(self):
        """Empty results should return appropriate message."""
        result = format_search_result([])
        assert "검색 결과가 없습니다" in result

    def test_format_search_result_with_channels(self):
        """Channels should be formatted correctly."""
        channels = [
            {"name": "Test1", "service": "StreamLive", "status": "running"},
            {"name": "Test2", "service": "StreamLink", "status": "stopped"},
        ]
        result = format_search_result(channels)
        assert "Test1" in result
        assert "Test2" in result
        assert "🟢" in result  # running emoji
        assert "🔴" in result  # stopped emoji

    def test_format_search_result_truncation(self):
        """More than 10 results should show truncation message."""
        channels = [{"name": f"Ch{i}", "service": "StreamLive", "status": "running"}
                    for i in range(15)]
        result = format_search_result(channels)
        assert "그 외 5개" in result

    def test_get_help_message(self):
        """Help message should contain key information."""
        result = get_help_message()
        assert "검색" in result
        assert "제어" in result

    def test_get_control_help_message(self):
        """Control help message should mention dashboard."""
        result = get_control_help_message("start")
        assert "대시보드" in result or "버튼" in result
