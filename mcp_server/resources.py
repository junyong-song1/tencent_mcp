"""MCP Resources for Tencent Cloud.

Resources provide read-only access to data sources.
"""

import json
import logging
from typing import List, Dict, Any

from mcp.server import Server
from mcp.types import Resource, TextContent

logger = logging.getLogger(__name__)


def register_resources(server: Server, get_tencent_client, get_schedule_manager):
    """Register all MCP resources.
    
    Args:
        server: MCP Server instance
        get_tencent_client: Callable that returns TencentCloudClient
        get_schedule_manager: Callable that returns ScheduleManager
    """
    
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List all available resources."""
        return [
            Resource(
                uri="tencent://streamlive/channels",
                name="StreamLive Channels",
                description="List of all Tencent Cloud StreamLive (MDL) channels with their status",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://streamlink/flows",
                name="StreamLink Flows",
                description="List of all Tencent Cloud StreamLink (MDC) flows with their status",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://resources/all",
                name="All Resources",
                description="Combined list of all StreamLive channels and StreamLink flows",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://resources/hierarchy",
                name="Resource Hierarchy",
                description="StreamLive channels with linked StreamLink flows (parent-child relationships)",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://schedules/upcoming",
                name="Upcoming Schedules",
                description="List of upcoming broadcast schedules",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://streampackage/channels",
                name="StreamPackage Channels",
                description="List of all Tencent Cloud StreamPackage (MDP) channels",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://css/domains",
                name="CSS Domains",
                description="List of all CSS (Cloud Streaming Service) domains",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://css/streams",
                name="CSS Streams",
                description="List of active CSS streams",
                mimeType="application/json",
            ),
            Resource(
                uri="tencent://logs/integrated",
                name="Integrated Logs",
                description="Integrated logs from StreamLive, StreamLink, StreamPackage, and CSS",
                mimeType="application/json",
            ),
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific resource by URI."""
        client = get_tencent_client()
        schedule_manager = get_schedule_manager()
        
        if uri == "tencent://streamlive/channels":
            channels = client.list_mdl_channels()
            return json.dumps({
                "type": "streamlive_channels",
                "count": len(channels),
                "channels": channels,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://streamlink/flows":
            flows = client.list_streamlink_inputs()
            return json.dumps({
                "type": "streamlink_flows",
                "count": len(flows),
                "flows": flows,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://resources/all":
            resources = client.list_all_resources()
            streamlive = [r for r in resources if r.get("service") == "StreamLive"]
            streamlink = [r for r in resources if r.get("service") == "StreamLink"]
            return json.dumps({
                "type": "all_resources",
                "total_count": len(resources),
                "streamlive_count": len(streamlive),
                "streamlink_count": len(streamlink),
                "resources": resources,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://resources/hierarchy":
            # Build hierarchy with linkage
            from app.services.linkage import LinkageService
            resources = client.list_all_resources()
            linkage_service = LinkageService()
            hierarchy = linkage_service.build_hierarchy(resources)
            return json.dumps({
                "type": "resource_hierarchy",
                "parent_count": len(hierarchy),
                "hierarchy": [h.to_dict() for h in hierarchy],
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://schedules/upcoming":
            schedules = schedule_manager.get_all_upcoming_schedules()
            return json.dumps({
                "type": "upcoming_schedules",
                "count": len(schedules),
                "schedules": schedules,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://streampackage/channels":
            channels = client.list_streampackage_channels()
            return json.dumps({
                "type": "streampackage_channels",
                "count": len(channels),
                "channels": channels,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://css/domains":
            domains = client.list_css_domains()
            return json.dumps({
                "type": "css_domains",
                "count": len(domains),
                "domains": domains,
            }, indent=2, ensure_ascii=False)
        
        elif uri == "tencent://css/streams":
            streams = client.list_css_streams()
            return json.dumps({
                "type": "css_streams",
                "count": len(streams),
                "streams": streams,
            }, indent=2, ensure_ascii=False)
        
        elif uri.startswith("tencent://logs/integrated"):
            # Parse channel_id from URI if provided
            # Format: tencent://logs/integrated?channel_id=xxx&hours=24
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(uri)
            params = parse_qs(parsed.query)
            channel_id = params.get("channel_id", [None])[0]
            hours = int(params.get("hours", ["24"])[0])
            
            if not channel_id:
                return json.dumps({
                    "type": "integrated_logs",
                    "error": "channel_id parameter required",
                }, indent=2, ensure_ascii=False)
            
            logs_data = client.get_integrated_logs(channel_id=channel_id, hours=hours)
            return json.dumps({
                "type": "integrated_logs",
                **logs_data,
            }, indent=2, ensure_ascii=False)
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
