"""MCP Tools for Tencent Cloud.

Tools provide executable functions for controlling resources.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


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
    
    # List channels
    if name == "list_channels":
        service_filter = arguments.get("service", "all")
        status_filter = arguments.get("status", "all")
        
        resources = client.list_all_resources()
        
        # Apply filters
        if service_filter != "all":
            resources = [r for r in resources if r.get("service") == service_filter]
        
        if status_filter != "all":
            resources = [r for r in resources if r.get("status") == status_filter]
        
        # Group by service
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
    
    # Search resources
    elif name == "search_resources":
        keyword = arguments.get("keyword", "")
        results = client.search_resources([keyword])
        return {
            "success": True,
            "keyword": keyword,
            "count": len(results),
            "results": results,
        }
    
    # Get channel status
    elif name == "get_channel_status":
        channel_id = arguments["channel_id"]
        service = arguments["service"]
        
        details = client.get_resource_details(channel_id, service)
        if not details:
            return {
                "success": False,
                "error": f"Channel not found: {channel_id}",
            }
        
        return {
            "success": True,
            "channel": details,
        }
    
    # Get input status (main/backup)
    elif name == "get_input_status":
        channel_id = arguments["channel_id"]
        input_status = client.get_channel_input_status(channel_id)
        
        if not input_status:
            return {
                "success": False,
                "error": f"Could not get input status for channel: {channel_id}",
            }
        
        return {
            "success": True,
            **input_status,
        }
    
    # Start channel
    elif name == "start_channel":
        channel_id = arguments["channel_id"]
        service = arguments["service"]
        
        result = client.control_resource(channel_id, service, "start")
        return {
            "success": result.get("success", False),
            "channel_id": channel_id,
            "service": service,
            "action": "start",
            "message": result.get("message", ""),
        }
    
    # Stop channel
    elif name == "stop_channel":
        channel_id = arguments["channel_id"]
        service = arguments["service"]
        
        result = client.control_resource(channel_id, service, "stop")
        return {
            "success": result.get("success", False),
            "channel_id": channel_id,
            "service": service,
            "action": "stop",
            "message": result.get("message", ""),
        }
    
    # Restart channel
    elif name == "restart_channel":
        channel_id = arguments["channel_id"]
        service = arguments["service"]
        
        result = client.control_resource(channel_id, service, "restart")
        return {
            "success": result.get("success", False),
            "channel_id": channel_id,
            "service": service,
            "action": "restart",
            "message": result.get("message", ""),
        }
    
    # List schedules
    elif name == "list_schedules":
        from datetime import date, timedelta
        
        date_str = arguments.get("date")
        days = arguments.get("days", 7)
        
        if date_str:
            start_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            start_date = date.today()
        
        end_date = start_date + timedelta(days=days)
        schedules = schedule_manager.get_schedules_for_range(start_date, end_date)
        
        return {
            "success": True,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "count": len(schedules),
            "schedules": schedules,
        }
    
    # Create schedule
    elif name == "create_schedule":
        start_time = datetime.fromisoformat(arguments["start_time"])
        end_time = datetime.fromisoformat(arguments["end_time"])
        
        result = schedule_manager.add_schedule(
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
        
        return result
    
    # Delete schedule
    elif name == "delete_schedule":
        schedule_id = arguments["schedule_id"]
        result = schedule_manager.delete_schedule(schedule_id)
        return result
    
    # Get linked resources
    elif name == "get_linked_resources":
        from app.services.linkage import LinkageService
        
        channel_id = arguments["channel_id"]
        service = arguments["service"]
        
        resources = client.list_all_resources()
        linkage_service = LinkageService()
        
        # Find the resource
        target_resource = None
        for r in resources:
            if r.get("id") == channel_id and r.get("service") == service:
                target_resource = r
                break
        
        if not target_resource:
            return {
                "success": False,
                "error": f"Resource not found: {channel_id}",
            }
        
        # Build hierarchy and find linked resources
        hierarchy = linkage_service.build_hierarchy(resources)
        linked = []
        
        if service == "StreamLive":
            # Find children (StreamLink flows)
            for h in hierarchy:
                if h.parent.get("id") == channel_id:
                    linked = h.children
                    break
        else:
            # Find parent (StreamLive channel)
            for h in hierarchy:
                for child in h.children:
                    if child.get("id") == channel_id:
                        linked = [h.parent]
                        break
        
        return {
            "success": True,
            "source": target_resource,
            "linked_resources": linked,
            "linked_count": len(linked),
        }
    
    # Start integrated
    elif name == "start_integrated":
        channel_id = arguments["channel_id"]
        
        # First, get linked resources
        from app.services.linkage import LinkageService
        
        resources = client.list_all_resources()
        linkage_service = LinkageService()
        hierarchy = linkage_service.build_hierarchy(resources)
        
        # Find the channel and its children
        target_hierarchy = None
        for h in hierarchy:
            if h.parent.get("id") == channel_id:
                target_hierarchy = h
                break
        
        if not target_hierarchy:
            return {
                "success": False,
                "error": f"StreamLive channel not found: {channel_id}",
            }
        
        results = []
        
        # Start children first (StreamLink flows)
        for child in target_hierarchy.children:
            result = client.control_resource(child["id"], "StreamLink", "start")
            results.append({
                "id": child["id"],
                "name": child.get("name", ""),
                "service": "StreamLink",
                **result,
            })
        
        # Then start parent (StreamLive channel)
        parent_result = client.control_resource(channel_id, "StreamLive", "start")
        results.append({
            "id": channel_id,
            "name": target_hierarchy.parent.get("name", ""),
            "service": "StreamLive",
            **parent_result,
        })
        
        all_success = all(r.get("success", False) for r in results)
        
        return {
            "success": all_success,
            "action": "start_integrated",
            "results": results,
        }
    
    # Stop integrated
    elif name == "stop_integrated":
        channel_id = arguments["channel_id"]
        
        from app.services.linkage import LinkageService
        
        resources = client.list_all_resources()
        linkage_service = LinkageService()
        hierarchy = linkage_service.build_hierarchy(resources)
        
        # Find the channel and its children
        target_hierarchy = None
        for h in hierarchy:
            if h.parent.get("id") == channel_id:
                target_hierarchy = h
                break
        
        if not target_hierarchy:
            return {
                "success": False,
                "error": f"StreamLive channel not found: {channel_id}",
            }
        
        results = []
        
        # Stop parent first (StreamLive channel)
        parent_result = client.control_resource(channel_id, "StreamLive", "stop")
        results.append({
            "id": channel_id,
            "name": target_hierarchy.parent.get("name", ""),
            "service": "StreamLive",
            **parent_result,
        })
        
        # Then stop children (StreamLink flows)
        for child in target_hierarchy.children:
            result = client.control_resource(child["id"], "StreamLink", "stop")
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
    
    # List StreamPackage channels
    elif name == "list_streampackage_channels":
        channels = client.list_streampackage_channels()
        return {
            "success": True,
            "count": len(channels),
            "channels": channels,
        }
    
    # Get StreamPackage status
    elif name == "get_streampackage_status":
        channel_id = arguments["channel_id"]
        details = client.get_streampackage_channel_details(channel_id)
        
        if not details:
            return {
                "success": False,
                "error": f"StreamPackage channel not found: {channel_id}",
            }
        
        return {
            "success": True,
            **details,
        }
    
    # List CSS domains
    elif name == "list_css_domains":
        domains = client.list_css_domains()
        return {
            "success": True,
            "count": len(domains),
            "domains": domains,
        }
    
    # List CSS streams
    elif name == "list_css_streams":
        domain = arguments.get("domain")
        streams = client.list_css_streams(domain)
        return {
            "success": True,
            "domain": domain or "all",
            "count": len(streams),
            "streams": streams,
        }
    
    # Get CSS stream status
    elif name == "get_css_stream_status":
        stream_name = arguments["stream_name"]
        domain = arguments.get("domain")
        
        details = client.get_css_stream_details(stream_name, domain)
        
        if not details:
            return {
                "success": False,
                "error": f"CSS stream not found: {stream_name}",
            }
        
        return {
            "success": True,
            **details,
        }
    
    # Get CSS stream bandwidth
    elif name == "get_css_stream_bandwidth":
        stream_name = arguments["stream_name"]
        domain = arguments.get("domain")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        
        bandwidth_info = client.get_css_stream_bandwidth(
            stream_name=stream_name,
            domain=domain,
            start_time=start_time,
            end_time=end_time,
        )
        
        if not bandwidth_info:
            return {
                "success": False,
                "error": f"Could not get bandwidth info for: {stream_name}",
            }
        
        return {
            "success": True,
            **bandwidth_info,
        }
    
    # Get CSS stream quality
    elif name == "get_css_stream_quality":
        stream_name = arguments["stream_name"]
        domain = arguments.get("domain")
        
        quality_info = client.get_css_stream_quality(stream_name, domain)
        
        if not quality_info:
            return {
                "success": False,
                "error": f"Could not get quality info for: {stream_name}",
            }
        
        return {
            "success": True,
            **quality_info,
        }
    
    # Get CSS stream events
    elif name == "get_css_stream_events":
        stream_name = arguments["stream_name"]
        domain = arguments.get("domain")
        hours = arguments.get("hours", 24)
        
        events = client.get_css_stream_events(
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
    
    # Get full status (integrated)
    elif name == "get_full_status":
        channel_id = arguments["channel_id"]
        
        # Get StreamLive channel status
        channel_status = client.get_channel_input_status(channel_id)
        if not channel_status:
            return {
                "success": False,
                "error": f"StreamLive channel not found: {channel_id}",
            }
        
        result = {
            "success": True,
            "streamlive": channel_status,
        }
        
        # Get StreamPackage status if connected
        streampackage_id = channel_status.get("streampackage_verification", {}).get("streampackage_id")
        if streampackage_id:
            sp_status = client.get_streampackage_channel_details(streampackage_id)
            if sp_status:
                result["streampackage"] = sp_status
        
        # Get CSS status if available
        css_verification = channel_status.get("css_verification")
        if css_verification:
            result["css"] = css_verification
        
        # Get linked StreamLink flows
        from app.services.linkage import LinkageService
        resources = client.list_all_resources()
        linkage_service = LinkageService()
        hierarchy = linkage_service.build_hierarchy(resources)
        
        for h in hierarchy:
            if h.parent.get("id") == channel_id:
                result["linked_streamlink_flows"] = h.children
                break
        
        return result
    
    # Get channel logs
    elif name == "get_channel_logs":
        channel_id = arguments["channel_id"]
        hours = arguments.get("hours", 24)
        event_types = arguments.get("event_types")
        
        logs = client.get_streamlive_channel_logs(
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
    
    # Get integrated logs
    elif name == "get_integrated_logs":
        channel_id = arguments["channel_id"]
        hours = arguments.get("hours", 24)
        services = arguments.get("services")
        event_types = arguments.get("event_types")
        
        result = client.get_integrated_logs(
            channel_id=channel_id,
            hours=hours,
            services=services,
            event_types=event_types,
        )
        
        return {
            "success": True,
            **result,
        }
    
    # Analyze logs
    elif name == "analyze_logs":
        channel_id = arguments["channel_id"]
        hours = arguments.get("hours", 24)
        
        # Get integrated logs
        logs_data = client.get_integrated_logs(
            channel_id=channel_id,
            hours=hours,
        )
        
        if not logs_data or "logs" not in logs_data:
            return {
                "success": False,
                "error": "Could not retrieve logs",
            }
        
        all_logs = logs_data.get("logs", [])
        service_counts = logs_data.get("service_counts", {})
        event_counts = logs_data.get("event_counts", {})
        
        # Analyze patterns
        analysis = {
            "channel_id": channel_id,
            "analysis_period_hours": hours,
            "total_events": len(all_logs),
            "service_distribution": service_counts,
            "event_distribution": event_counts,
            "insights": [],
            "recommendations": [],
        }
        
        # Analyze failover patterns
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
        
        # Analyze error patterns
        error_events = [log for log in all_logs if "error" in log.get("event_type", "").lower() or "Error" in log.get("message", "")]
        if error_events:
            analysis["insights"].append({
                "type": "error_analysis",
                "error_count": len(error_events),
                "recent_errors": error_events[:5],
            })
            
            analysis["recommendations"].append(
                f"⚠️ 오류 이벤트 {len(error_events)}개 발견. 상세 로그를 확인하세요."
            )
        
        # Analyze service health
        service_health = {}
        for service, count in service_counts.items():
            if count > 0:
                service_health[service] = "active"
            else:
                service_health[service] = "no_events"
        
        analysis["service_health"] = service_health
        
        # Time-based analysis
        if all_logs:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            
            recent_logs = [log for log in all_logs[:10]]  # Last 10 events
            analysis["recent_events"] = recent_logs
            
            # Check for gaps in logging
            if len(all_logs) < 5:
                analysis["recommendations"].append(
                    "ℹ️ 로그 이벤트가 적습니다. 정상 작동 중이거나 로그 수집 문제일 수 있습니다."
                )
        
        return {
            "success": True,
            **analysis,
        }
    
    else:
        raise ValueError(f"Unknown tool: {name}")
