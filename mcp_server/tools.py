"""MCP Tools for Tencent Cloud.

Tools provide executable functions for controlling resources.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from app.services.alert_utils import get_channel_alerts, CRITICAL_ALERTS, WARNING_ALERTS

logger = logging.getLogger(__name__)


async def _call_in_thread(func, *args, **kwargs):
    """Run sync functions in a worker thread to avoid blocking."""
    return await asyncio.to_thread(func, *args, **kwargs)


def _error_response(message: str) -> Dict[str, Any]:
    return {"success": False, "error": message}


class ToolContext:
    """Request-scoped helpers for tool execution."""

    def __init__(self, client, schedule_manager):
        self.client = client
        self.schedule_manager = schedule_manager
        self._resources_cache = None

    async def call(self, func, *args, **kwargs):
        return await _call_in_thread(func, *args, **kwargs)

    async def get_all_resources(self):
        if self._resources_cache is None:
            self._resources_cache = await self.call(self.client.list_all_resources)
        return self._resources_cache


def _analyze_single_alert(
    alert: Dict,
    input_status: Optional[Dict],
    linked_flows: List[Dict],
    client,
) -> Dict:
    """Analyze a single alert and provide context and suggestions.

    Args:
        alert: Alert dictionary
        input_status: Channel input status (main/backup)
        linked_flows: Linked StreamLink flows
        client: TencentCloudClient instance

    Returns:
        Analysis result with context and suggestions
    """
    alert_type = alert.get("type", "Unknown")
    pipeline = alert.get("pipeline", "")

    # Build context
    context = {
        "alert": alert,
        "upstream_status": None,
        "last_good_state": None,
        "related_resources": [alert.get("channel_id")],
        "possible_causes": [],
    }

    # Add linked flow IDs to related resources
    for flow in linked_flows:
        context["related_resources"].append(flow.get("id"))

    # Analyze based on alert type
    suggested_actions = []

    if alert_type == "No Input Data":
        # Check StreamLink flow status
        flow_status_summary = []
        for flow in linked_flows:
            flow_status = flow.get("status", "unknown")
            flow_status_summary.append(f"{flow.get('name', flow.get('id'))}: {flow_status}")

            if flow_status != "running":
                context["possible_causes"].append(f"StreamLink flow '{flow.get('name')}' is not running (status: {flow_status})")

        context["upstream_status"] = ", ".join(flow_status_summary) if flow_status_summary else "No linked flows"

        # Add possible causes
        context["possible_causes"].extend([
            "입력 소스가 끊어졌거나 연결되지 않음",
            "네트워크 연결 문제",
            "송출 장비 문제",
            "StreamLink flow가 중지됨",
        ])

        # Add suggested actions
        suggested_actions = [
            "StreamLink flow 상태를 확인하세요 (get_linked_resources 도구 사용)",
            "소스 장비의 송출 상태를 확인하세요",
            "네트워크 연결을 점검하세요",
            "소스가 정상이면 flow를 재시작하세요 (start_channel 도구 사용)",
        ]

    elif alert_type == "PipelineFailover":
        # Check which pipeline is affected
        is_main_affected = "Main" in pipeline or "Pipeline A" in pipeline

        context["possible_causes"] = [
            f"{'메인' if is_main_affected else '백업'} 파이프라인의 입력 소스 손실",
            "해당 입력의 네트워크 연결 문제",
            "자동 failover가 발생하여 다른 파이프라인으로 전환됨",
        ]

        # Check input status
        if input_status:
            active_input = input_status.get("active_input")
            context["upstream_status"] = f"Active input: {active_input}"

        suggested_actions = [
            "현재 활성 입력(main/backup) 상태를 확인하세요",
            f"{'메인' if is_main_affected else '백업'} 입력 소스의 연결 상태를 점검하세요",
            "소스가 복구되면 자동으로 정상화됩니다",
            "필요시 입력 설정을 확인하세요",
        ]

    elif alert_type == "PipelineRecover":
        context["possible_causes"] = [
            "이전에 실패했던 파이프라인이 복구됨",
            "입력 소스가 다시 연결됨",
        ]

        suggested_actions = [
            "정상 복구되었습니다. 추가 조치가 필요하지 않습니다.",
            "반복적인 failover/recover가 발생하면 소스 안정성을 점검하세요",
        ]

    elif alert_type == "StreamStop":
        context["possible_causes"] = [
            "스트림 푸시가 중단됨",
            "송출 장비에서 스트림 전송을 중지함",
            "네트워크 연결 문제",
        ]

        suggested_actions = [
            "송출 장비의 스트림 상태를 확인하세요",
            "의도적인 중지인지 확인하세요",
            "네트워크 연결을 점검하세요",
        ]

    elif alert_type == "StreamStart":
        context["possible_causes"] = [
            "스트림 푸시가 시작됨",
        ]

        suggested_actions = [
            "정상적인 스트림 시작입니다. 추가 조치가 필요하지 않습니다.",
        ]

    else:
        context["possible_causes"] = [
            "알 수 없는 알람 유형입니다",
        ]

        suggested_actions = [
            "채널 상세 정보를 확인하세요 (get_channel_status 도구 사용)",
            "Tencent Cloud 콘솔에서 직접 확인하세요",
        ]

    return {
        "alert": alert,
        "context": context,
        "suggested_actions": suggested_actions,
    }


def register_tools(server: Server, get_tencent_client, get_schedule_manager):
    """Register all MCP tools.
    
    Args:
        server: MCP Server instance
        get_tencent_client: Callable that returns TencentCloudClient
        get_schedule_manager: Callable that returns ScheduleManager
    """
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List all available tools."""
        return [
            # Resource Control Tools
            Tool(
                name="list_channels",
                description="List all StreamLive channels and StreamLink flows with their current status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Filter by service type: 'StreamLive', 'StreamLink', or 'all' (default)",
                            "enum": ["StreamLive", "StreamLink", "all"],
                            "default": "all",
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by status: 'running', 'idle', 'stopped', 'error', or 'all' (default)",
                            "enum": ["running", "idle", "stopped", "error", "all"],
                            "default": "all",
                        },
                    },
                },
            ),
            Tool(
                name="search_resources",
                description="Search for channels or flows by keyword in their name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Keyword to search for in resource names",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
            Tool(
                name="get_channel_status",
                description="Get detailed status of a specific channel including input status (main/backup)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel ID to get status for",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type: 'StreamLive' or 'StreamLink'",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                    },
                    "required": ["channel_id", "service"],
                },
            ),
            Tool(
                name="get_input_status",
                description="Get active input status (main/backup) for a StreamLive channel with failover information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="start_channel",
                description="Start a StreamLive channel or StreamLink flow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel/flow ID to start",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type: 'StreamLive' or 'StreamLink'",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                    },
                    "required": ["channel_id", "service"],
                },
            ),
            Tool(
                name="stop_channel",
                description="Stop a StreamLive channel or StreamLink flow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel/flow ID to stop",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type: 'StreamLive' or 'StreamLink'",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                    },
                    "required": ["channel_id", "service"],
                },
            ),
            Tool(
                name="restart_channel",
                description="Restart a StreamLive channel or StreamLink flow (stop then start)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel/flow ID to restart",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type: 'StreamLive' or 'StreamLink'",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                    },
                    "required": ["channel_id", "service"],
                },
            ),
            # Schedule Tools
            Tool(
                name="list_schedules",
                description="List broadcast schedules for a date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (default: today)",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to include (default: 7)",
                            "default": 7,
                        },
                    },
                },
            ),
            Tool(
                name="create_schedule",
                description="Create a new broadcast schedule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel ID for the broadcast",
                        },
                        "channel_name": {
                            "type": "string",
                            "description": "The channel name for display",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type: 'StreamLive' or 'StreamLink'",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the broadcast",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "assignee_name": {
                            "type": "string",
                            "description": "Name of the person responsible",
                        },
                        "auto_start": {
                            "type": "boolean",
                            "description": "Whether to auto-start the channel at start_time",
                            "default": False,
                        },
                        "auto_stop": {
                            "type": "boolean",
                            "description": "Whether to auto-stop the channel at end_time",
                            "default": False,
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes for the schedule",
                        },
                    },
                    "required": ["channel_id", "channel_name", "service", "title", "start_time", "end_time", "assignee_name"],
                },
            ),
            Tool(
                name="delete_schedule",
                description="Cancel/delete a broadcast schedule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "string",
                            "description": "The schedule ID to delete",
                        },
                    },
                    "required": ["schedule_id"],
                },
            ),
            # Linkage Tools
            Tool(
                name="get_linked_resources",
                description="Get StreamLink flows linked to a StreamLive channel (or vice versa)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel/flow ID",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service type of the provided ID",
                            "enum": ["StreamLive", "StreamLink"],
                        },
                    },
                    "required": ["channel_id", "service"],
                },
            ),
            Tool(
                name="start_integrated",
                description="Start a StreamLive channel and all its linked StreamLink flows together",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="stop_integrated",
                description="Stop a StreamLive channel and all its linked StreamLink flows together",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            # StreamPackage Tools
            Tool(
                name="list_streampackage_channels",
                description="List all StreamPackage channels with their status and input information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_streampackage_status",
                description="Get detailed status of a StreamPackage channel including input status (main/backup)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamPackage channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            # CSS Tools
            Tool(
                name="list_css_domains",
                description="List all CSS (Cloud Streaming Service) domains",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="list_css_streams",
                description="List active CSS streams (optionally filtered by domain)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "CSS domain name (optional, lists all domains if not provided)",
                        },
                    },
                },
            ),
            Tool(
                name="get_css_stream_status",
                description="Get detailed status of a CSS stream including whether it's active",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name in format 'app/stream' or just 'stream'",
                        },
                        "domain": {
                            "type": "string",
                            "description": "CSS domain name (optional)",
                        },
                    },
                    "required": ["stream_name"],
                },
            ),
            Tool(
                name="get_css_stream_bandwidth",
                description="Get CSS stream bandwidth and traffic information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name in format 'app/stream'",
                        },
                        "domain": {
                            "type": "string",
                            "description": "CSS domain name (optional)",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in YYYY-MM-DD format (optional)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in YYYY-MM-DD format (optional)",
                        },
                    },
                    "required": ["stream_name"],
                },
            ),
            Tool(
                name="get_css_stream_quality",
                description="Get CSS stream quality information (bitrate, framerate, resolution, viewer count)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name in format 'app/stream'",
                        },
                        "domain": {
                            "type": "string",
                            "description": "CSS domain name (optional)",
                        },
                    },
                    "required": ["stream_name"],
                },
            ),
            Tool(
                name="get_css_stream_events",
                description="Get CSS stream events (start, stop, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream_name": {
                            "type": "string",
                            "description": "Stream name in format 'app/stream'",
                        },
                        "domain": {
                            "type": "string",
                            "description": "CSS domain name (optional)",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to look back (default: 24)",
                            "default": 24,
                        },
                    },
                    "required": ["stream_name"],
                },
            ),
            # Integrated Status Tools
            Tool(
                name="get_full_status",
                description="Get comprehensive status across StreamLive, StreamPackage, and CSS for a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            # Alert Analysis Tools
            Tool(
                name="get_alerts",
                description="Get current alerts from all running StreamLive channels. Returns alerts categorized by severity (critical, warning, info).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Optional: Filter alerts for a specific channel ID. If not provided, returns alerts from all running channels.",
                        },
                        "severity": {
                            "type": "string",
                            "description": "Optional: Filter by severity level",
                            "enum": ["critical", "warning", "info", "all"],
                            "default": "all",
                        },
                    },
                },
            ),
            Tool(
                name="analyze_alert",
                description="Analyze a specific alert and provide context, possible causes, and suggested actions. Use this when investigating channel issues.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID with the alert",
                        },
                        "alert_type": {
                            "type": "string",
                            "description": "Optional: Specific alert type to analyze (e.g., 'No Input Data', 'PipelineFailover'). If not provided, analyzes all current alerts.",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="get_health_summary",
                description="Get overall system health summary including channel counts, alert status, and any issues requiring attention.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # Log Analysis Tools
            Tool(
                name="get_channel_logs",
                description="Get logs from a StreamLive channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to look back (default: 24)",
                            "default": 24,
                        },
                        "event_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by event types (e.g., ['PipelineFailover', 'PipelineRecover'])",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="get_integrated_logs",
                description="Get integrated logs from StreamLive, StreamLink, StreamPackage, and CSS for a channel with analysis",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to look back (default: 24)",
                            "default": 24,
                        },
                        "services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by services (e.g., ['StreamLive', 'StreamLink', 'StreamPackage', 'CSS'])",
                        },
                        "event_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by event types (e.g., ['PipelineFailover', 'No Input Data'])",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="analyze_logs",
                description="Analyze integrated logs and provide insights (failover patterns, error trends, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to analyze (default: 24)",
                            "default": 24,
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool."""
        client = get_tencent_client()
        schedule_manager = get_schedule_manager()
        
        try:
            result = await _execute_tool(name, arguments, client, schedule_manager)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False),
            )]
        except Exception as e:
            logger.error(f"Tool execution failed: {name} - {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e),
                }, indent=2),
            )]


async def _execute_tool(
    name: str,
    arguments: Dict[str, Any],
    client,
    schedule_manager,
) -> Dict[str, Any]:
    """Execute a tool and return the result."""
    ctx = ToolContext(client, schedule_manager)
    handlers = {
        "list_channels": _handle_list_channels,
        "search_resources": _handle_search_resources,
        "get_channel_status": _handle_get_channel_status,
        "get_input_status": _handle_get_input_status,
        "start_channel": _handle_start_channel,
        "stop_channel": _handle_stop_channel,
        "restart_channel": _handle_restart_channel,
        "list_schedules": _handle_list_schedules,
        "create_schedule": _handle_create_schedule,
        "delete_schedule": _handle_delete_schedule,
        "get_linked_resources": _handle_get_linked_resources,
        "start_integrated": _handle_start_integrated,
        "stop_integrated": _handle_stop_integrated,
        "list_streampackage_channels": _handle_list_streampackage_channels,
        "get_streampackage_status": _handle_get_streampackage_status,
        "list_css_domains": _handle_list_css_domains,
        "list_css_streams": _handle_list_css_streams,
        "get_css_stream_status": _handle_get_css_stream_status,
        "get_css_stream_bandwidth": _handle_get_css_stream_bandwidth,
        "get_css_stream_quality": _handle_get_css_stream_quality,
        "get_css_stream_events": _handle_get_css_stream_events,
        "get_alerts": _handle_get_alerts,
        "analyze_alert": _handle_analyze_alert,
        "get_health_summary": _handle_get_health_summary,
        "get_full_status": _handle_get_full_status,
        "get_channel_logs": _handle_get_channel_logs,
        "get_integrated_logs": _handle_get_integrated_logs,
        "analyze_logs": _handle_analyze_logs,
    }
    handler = handlers.get(name)
    if not handler:
        return _error_response(f"Unknown tool: {name}")
    return await handler(ctx, arguments)


async def _handle_list_channels(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    service_filter = arguments.get("service", "all")
    status_filter = arguments.get("status", "all")

    resources = await ctx.get_all_resources()

    if service_filter != "all":
        resources = [r for r in resources if r.get("service") == service_filter]

    if status_filter != "all":
        resources = [r for r in resources if r.get("status") == status_filter]

    streamlive = [r for r in resources if r.get("service") == "StreamLive"]
    streamlink = [r for r in resources if r.get("service") == "StreamLink"]

    return {
        "success": True,
        "total_count": len(resources),
        "streamlive_count": len(streamlive),
        "streamlink_count": len(streamlink),
        "streamlive_channels": streamlive,
        "streamlink_flows": streamlink,
    }


async def _handle_search_resources(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    keyword = arguments.get("keyword", "")
    results = await ctx.call(ctx.client.search_resources, [keyword])
    return {
        "success": True,
        "keyword": keyword,
        "count": len(results),
        "results": results,
    }


async def _handle_get_channel_status(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    service = arguments["service"]

    details = await ctx.call(ctx.client.get_resource_details, channel_id, service)
    if not details:
        return _error_response(f"Channel not found: {channel_id}")

    return {
        "success": True,
        "channel": details,
    }


async def _handle_get_input_status(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    input_status = await ctx.call(ctx.client.get_channel_input_status, channel_id)

    if not input_status:
        return _error_response(f"Could not get input status for channel: {channel_id}")

    return {
        "success": True,
        **input_status,
    }


async def _handle_start_channel(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    service = arguments["service"]

    result = await ctx.call(ctx.client.control_resource, channel_id, service, "start")
    return {
        "success": result.get("success", False),
        "channel_id": channel_id,
        "service": service,
        "action": "start",
        "message": result.get("message", ""),
    }


async def _handle_stop_channel(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    service = arguments["service"]

    result = await ctx.call(ctx.client.control_resource, channel_id, service, "stop")
    return {
        "success": result.get("success", False),
        "channel_id": channel_id,
        "service": service,
        "action": "stop",
        "message": result.get("message", ""),
    }


async def _handle_restart_channel(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    service = arguments["service"]

    result = await ctx.call(ctx.client.control_resource, channel_id, service, "restart")
    return {
        "success": result.get("success", False),
        "channel_id": channel_id,
        "service": service,
        "action": "restart",
        "message": result.get("message", ""),
    }


async def _handle_list_schedules(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import date, timedelta

    date_str = arguments.get("date")
    days = arguments.get("days", 7)

    if date_str:
        start_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        start_date = date.today()

    end_date = start_date + timedelta(days=days)
    schedules = await ctx.call(
        ctx.schedule_manager.get_schedules_for_range, start_date, end_date
    )

    return {
        "success": True,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "count": len(schedules),
        "schedules": schedules,
    }


async def _handle_create_schedule(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    start_time = datetime.fromisoformat(arguments["start_time"])
    end_time = datetime.fromisoformat(arguments["end_time"])

    return await ctx.call(
        ctx.schedule_manager.add_schedule,
        channel_id=arguments["channel_id"],
        channel_name=arguments["channel_name"],
        service=arguments["service"],
        title=arguments["title"],
        start_time=start_time,
        end_time=end_time,
        assignee_id="mcp_user",
        assignee_name=arguments["assignee_name"],
        auto_start=arguments.get("auto_start", False),
        auto_stop=arguments.get("auto_stop", False),
        notes=arguments.get("notes", ""),
        created_by="MCP",
    )


async def _handle_delete_schedule(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    schedule_id = arguments["schedule_id"]
    return await ctx.call(ctx.schedule_manager.delete_schedule, schedule_id)


async def _handle_get_linked_resources(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.linkage import ResourceHierarchyBuilder

    channel_id = arguments["channel_id"]
    service = arguments["service"]

    resources = await ctx.get_all_resources()

    target_resource = None
    for resource in resources:
        if resource.get("id") == channel_id and resource.get("service") == service:
            target_resource = resource
            break

    if not target_resource:
        return _error_response(f"Resource not found: {channel_id}")

    hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)
    linked = []

    if service == "StreamLive":
        for h in hierarchy:
            if h["parent"].get("id") == channel_id:
                linked = h["children"]
                break
    else:
        for h in hierarchy:
            for child in h["children"]:
                if child.get("id") == channel_id:
                    linked = [h["parent"]]
                    break

    return {
        "success": True,
        "source": target_resource,
        "linked_resources": linked,
        "linked_count": len(linked),
    }


async def _handle_start_integrated(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.linkage import ResourceHierarchyBuilder

    channel_id = arguments["channel_id"]
    resources = await ctx.get_all_resources()
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

    target_hierarchy = None
    for h in hierarchy:
        if h["parent"].get("id") == channel_id:
            target_hierarchy = h
            break

    if not target_hierarchy:
        return _error_response(f"StreamLive channel not found: {channel_id}")

    results = []
    for child in target_hierarchy["children"]:
        result = await ctx.call(ctx.client.control_resource, child["id"], "StreamLink", "start")
        results.append({
            "id": child["id"],
            "name": child.get("name", ""),
            "service": "StreamLink",
            **result,
        })

    parent_result = await ctx.call(ctx.client.control_resource, channel_id, "StreamLive", "start")
    results.append({
        "id": channel_id,
        "name": target_hierarchy["parent"].get("name", ""),
        "service": "StreamLive",
        **parent_result,
    })

    all_success = all(r.get("success", False) for r in results)
    return {
        "success": all_success,
        "action": "start_integrated",
        "results": results,
    }


async def _handle_stop_integrated(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.linkage import ResourceHierarchyBuilder

    channel_id = arguments["channel_id"]
    resources = await ctx.get_all_resources()
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

    target_hierarchy = None
    for h in hierarchy:
        if h["parent"].get("id") == channel_id:
            target_hierarchy = h
            break

    if not target_hierarchy:
        return _error_response(f"StreamLive channel not found: {channel_id}")

    results = []
    parent_result = await ctx.call(ctx.client.control_resource, channel_id, "StreamLive", "stop")
    results.append({
        "id": channel_id,
        "name": target_hierarchy["parent"].get("name", ""),
        "service": "StreamLive",
        **parent_result,
    })

    for child in target_hierarchy["children"]:
        result = await ctx.call(ctx.client.control_resource, child["id"], "StreamLink", "stop")
        results.append({
            "id": child["id"],
            "name": child.get("name", ""),
            "service": "StreamLink",
            **result,
        })

    all_success = all(r.get("success", False) for r in results)
    return {
        "success": all_success,
        "action": "stop_integrated",
        "results": results,
    }


async def _handle_list_streampackage_channels(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channels = await ctx.call(ctx.client.list_streampackage_channels)
    return {
        "success": True,
        "count": len(channels),
        "channels": channels,
    }


async def _handle_get_streampackage_status(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    details = await ctx.call(ctx.client.get_streampackage_channel_details, channel_id)

    if not details:
        return _error_response(f"StreamPackage channel not found: {channel_id}")

    return {
        "success": True,
        **details,
    }


async def _handle_list_css_domains(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    domains = await ctx.call(ctx.client.list_css_domains)
    return {
        "success": True,
        "count": len(domains),
        "domains": domains,
    }


async def _handle_list_css_streams(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    domain = arguments.get("domain")
    streams = await ctx.call(ctx.client.list_css_streams, domain)
    return {
        "success": True,
        "domain": domain or "all",
        "count": len(streams),
        "streams": streams,
    }


async def _handle_get_css_stream_status(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    stream_name = arguments["stream_name"]
    domain = arguments.get("domain")
    details = await ctx.call(ctx.client.get_css_stream_details, stream_name, domain)

    if not details:
        return _error_response(f"CSS stream not found: {stream_name}")

    return {
        "success": True,
        **details,
    }


async def _handle_get_css_stream_bandwidth(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    stream_name = arguments["stream_name"]
    domain = arguments.get("domain")
    start_time = arguments.get("start_time")
    end_time = arguments.get("end_time")

    bandwidth_info = await ctx.call(
        ctx.client.get_css_stream_bandwidth,
        stream_name=stream_name,
        domain=domain,
        start_time=start_time,
        end_time=end_time,
    )

    if not bandwidth_info:
        return _error_response(f"Could not get bandwidth info for: {stream_name}")

    return {
        "success": True,
        **bandwidth_info,
    }


async def _handle_get_css_stream_quality(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    stream_name = arguments["stream_name"]
    domain = arguments.get("domain")

    quality_info = await ctx.call(ctx.client.get_css_stream_quality, stream_name, domain)
    if not quality_info:
        return _error_response(f"Could not get quality info for: {stream_name}")

    return {
        "success": True,
        **quality_info,
    }


async def _handle_get_css_stream_events(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    stream_name = arguments["stream_name"]
    domain = arguments.get("domain")
    hours = arguments.get("hours", 24)

    events = await ctx.call(
        ctx.client.get_css_stream_events,
        stream_name=stream_name,
        domain=domain,
        hours=hours,
    )

    return {
        "success": True,
        "stream_name": stream_name,
        "domain": domain,
        "hours": hours,
        "total_events": len(events),
        "events": events,
    }


async def _handle_get_alerts(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id_filter = arguments.get("channel_id")
    severity_filter = arguments.get("severity", "all")

    resources = await ctx.get_all_resources()
    running_channels = [
        r for r in resources
        if r.get("service") == "StreamLive" and r.get("status") == "running"
    ]

    if channel_id_filter:
        running_channels = [
            r for r in running_channels
            if r.get("id") == channel_id_filter
        ]

    all_alerts = []
    for channel in running_channels:
        ch_id = channel.get("id", "")
        ch_name = channel.get("name", "")
        try:
            alerts = await ctx.call(get_channel_alerts, ctx.client, ch_id, ch_name)
            all_alerts.extend(alerts)
        except Exception as e:
            logger.error(f"Failed to get alerts for channel {ch_id}: {e}")

    if severity_filter != "all":
        all_alerts = [a for a in all_alerts if a.get("severity") == severity_filter]

    critical_alerts = [a for a in all_alerts if a.get("severity") == "critical"]
    warning_alerts = [a for a in all_alerts if a.get("severity") == "warning"]

    return {
        "success": True,
        "summary": {
            "total_alerts": len(all_alerts),
            "critical": len(critical_alerts),
            "warning": len(warning_alerts),
            "info": len([a for a in all_alerts if a.get("severity") == "info"]),
            "channels_checked": len(running_channels),
        },
        "alerts": all_alerts,
        "critical_alerts": critical_alerts,
        "warning_alerts": warning_alerts,
    }


async def _handle_analyze_alert(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    alert_type_filter = arguments.get("alert_type")

    channel_details = await ctx.call(ctx.client.get_resource_details, channel_id, "StreamLive")
    if not channel_details:
        return _error_response(f"Channel not found: {channel_id}")

    channel_name = channel_details.get("name", channel_id)
    alerts = await ctx.call(get_channel_alerts, ctx.client, channel_id, channel_name)

    if alert_type_filter:
        alerts = [a for a in alerts if a.get("type") == alert_type_filter]

    if not alerts:
        return {
            "success": True,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "message": "현재 활성 알람이 없습니다.",
            "alerts": [],
        }

    input_status = await ctx.call(ctx.client.get_channel_input_status, channel_id)

    from app.services.linkage import ResourceHierarchyBuilder
    resources = await ctx.get_all_resources()
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

    linked_flows = []
    for h in hierarchy:
        if h["parent"].get("id") == channel_id:
            linked_flows = h["children"]
            break

    analyzed_alerts = []
    for alert in alerts:
        alert_analysis = _analyze_single_alert(
            alert=alert,
            input_status=input_status,
            linked_flows=linked_flows,
            client=ctx.client,
        )
        analyzed_alerts.append(alert_analysis)

    return {
        "success": True,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "total_alerts": len(analyzed_alerts),
        "analyzed_alerts": analyzed_alerts,
        "channel_status": {
            "state": channel_details.get("status"),
            "active_input": input_status.get("active_input") if input_status else None,
        },
        "linked_flows": [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "status": f.get("status"),
            }
            for f in linked_flows
        ],
    }


async def _handle_get_health_summary(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    resources = await ctx.get_all_resources()

    streamlive_channels = [r for r in resources if r.get("service") == "StreamLive"]
    streamlink_flows = [r for r in resources if r.get("service") == "StreamLink"]

    running_streamlive = [r for r in streamlive_channels if r.get("status") == "running"]
    idle_streamlive = [r for r in streamlive_channels if r.get("status") == "idle"]

    running_streamlink = [r for r in streamlink_flows if r.get("status") == "running"]
    idle_streamlink = [r for r in streamlink_flows if r.get("status") == "idle"]

    all_alerts = []
    for channel in running_streamlive:
        ch_id = channel.get("id", "")
        ch_name = channel.get("name", "")
        try:
            alerts = await ctx.call(get_channel_alerts, ctx.client, ch_id, ch_name)
            all_alerts.extend(alerts)
        except Exception:
            pass

    critical_alerts = [a for a in all_alerts if a.get("severity") == "critical"]
    warning_alerts = [a for a in all_alerts if a.get("severity") == "warning"]

    if critical_alerts:
        overall_health = "critical"
        health_message = f"{len(critical_alerts)}개의 심각한 알람이 발생 중입니다. 즉시 확인이 필요합니다."
    elif warning_alerts:
        overall_health = "warning"
        health_message = f"{len(warning_alerts)}개의 주의 알람이 있습니다."
    elif len(running_streamlive) == 0:
        overall_health = "idle"
        health_message = "실행 중인 채널이 없습니다."
    else:
        overall_health = "healthy"
        health_message = "모든 시스템이 정상 작동 중입니다."

    issues = []
    for alert in critical_alerts:
        issues.append({
            "severity": "critical",
            "channel": alert.get("channel_name"),
            "issue": alert.get("type"),
            "pipeline": alert.get("pipeline"),
        })
    for alert in warning_alerts:
        issues.append({
            "severity": "warning",
            "channel": alert.get("channel_name"),
            "issue": alert.get("type"),
            "pipeline": alert.get("pipeline"),
        })

    return {
        "success": True,
        "overall_health": overall_health,
        "health_message": health_message,
        "summary": {
            "streamlive_total": len(streamlive_channels),
            "streamlive_running": len(running_streamlive),
            "streamlive_idle": len(idle_streamlive),
            "streamlink_total": len(streamlink_flows),
            "streamlink_running": len(running_streamlink),
            "streamlink_idle": len(idle_streamlink),
            "total_alerts": len(all_alerts),
            "critical_alerts": len(critical_alerts),
            "warning_alerts": len(warning_alerts),
        },
        "issues": issues,
        "running_channels": [
            {
                "id": ch.get("id"),
                "name": ch.get("name"),
                "status": ch.get("status"),
            }
            for ch in running_streamlive
        ],
    }


async def _handle_get_full_status(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]

    channel_status = await ctx.call(ctx.client.get_channel_input_status, channel_id)
    if not channel_status:
        return _error_response(f"StreamLive channel not found: {channel_id}")

    result = {
        "success": True,
        "streamlive": channel_status,
    }

    streampackage_id = channel_status.get("streampackage_verification", {}).get("streampackage_id")
    if streampackage_id:
        sp_status = await ctx.call(ctx.client.get_streampackage_channel_details, streampackage_id)
        if sp_status:
            result["streampackage"] = sp_status

    css_verification = channel_status.get("css_verification")
    if css_verification:
        result["css"] = css_verification

    from app.services.linkage import ResourceHierarchyBuilder
    resources = await ctx.get_all_resources()
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

    for h in hierarchy:
        if h["parent"].get("id") == channel_id:
            result["linked_streamlink_flows"] = h["children"]
            break

    return result


async def _handle_get_channel_logs(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    hours = arguments.get("hours", 24)
    event_types = arguments.get("event_types")

    logs = await ctx.call(
        ctx.client.get_streamlive_channel_logs,
        channel_id=channel_id,
        hours=hours,
        event_types=event_types,
    )

    return {
        "success": True,
        "channel_id": channel_id,
        "hours": hours,
        "total_logs": len(logs),
        "logs": logs,
    }


async def _handle_get_integrated_logs(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    hours = arguments.get("hours", 24)
    services = arguments.get("services")
    event_types = arguments.get("event_types")

    result = await ctx.call(
        ctx.client.get_integrated_logs,
        channel_id=channel_id,
        hours=hours,
        services=services,
        event_types=event_types,
    )

    return {
        "success": True,
        **result,
    }


async def _handle_analyze_logs(ctx: ToolContext, arguments: Dict[str, Any]) -> Dict[str, Any]:
    channel_id = arguments["channel_id"]
    hours = arguments.get("hours", 24)

    logs_data = await ctx.call(
        ctx.client.get_integrated_logs,
        channel_id=channel_id,
        hours=hours,
    )

    if not logs_data or "logs" not in logs_data:
        return _error_response("Could not retrieve logs")

    all_logs = logs_data.get("logs", [])
    service_counts = logs_data.get("service_counts", {})
    event_counts = logs_data.get("event_counts", {})

    analysis = {
        "channel_id": channel_id,
        "analysis_period_hours": hours,
        "total_events": len(all_logs),
        "service_distribution": service_counts,
        "event_distribution": event_counts,
        "insights": [],
        "recommendations": [],
    }

    failover_events = [log for log in all_logs if "Failover" in log.get("event_type", "")]
    recover_events = [log for log in all_logs if "Recover" in log.get("event_type", "")]

    if failover_events:
        analysis["insights"].append({
            "type": "failover_analysis",
            "failover_count": len(failover_events),
            "recover_count": len(recover_events),
            "last_failover": failover_events[0] if failover_events else None,
            "last_recover": recover_events[0] if recover_events else None,
        })

        if len(failover_events) > 3:
            analysis["recommendations"].append(
                f"⚠️ 높은 failover 발생률: {len(failover_events)}회 발생. 입력 소스 상태를 확인하세요."
            )

    error_events = [
        log for log in all_logs
        if "error" in log.get("event_type", "").lower() or "Error" in log.get("message", "")
    ]
    if error_events:
        analysis["insights"].append({
            "type": "error_analysis",
            "error_count": len(error_events),
            "recent_errors": error_events[:5],
        })
        analysis["recommendations"].append(
            f"⚠️ 오류 이벤트 {len(error_events)}개 발견. 상세 로그를 확인하세요."
        )

    service_health = {}
    for service, count in service_counts.items():
        service_health[service] = "active" if count > 0 else "no_events"

    analysis["service_health"] = service_health

    if all_logs:
        analysis["recent_events"] = [log for log in all_logs[:10]]
        if len(all_logs) < 5:
            analysis["recommendations"].append(
                "ℹ️ 로그 이벤트가 적습니다. 정상 작동 중이거나 로그 수집 문제일 수 있습니다."
            )

    return {
        "success": True,
        **analysis,
    }
