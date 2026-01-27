"""AI Assistant service using Claude API with MCP tools.

This service allows AI to use MCP tools to answer natural language queries.
"""
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available. Install with: pip install anthropic")


class AIAssistant:
    """AI Assistant that uses Claude API with MCP tools."""
    
    def __init__(self, api_key: str, tencent_client, schedule_manager):
        """Initialize AI Assistant.
        
        Args:
            api_key: Anthropic Claude API key
            tencent_client: TencentCloudClient instance
            schedule_manager: ScheduleManager instance
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not available. Install with: pip install anthropic")
        
        self.client = Anthropic(api_key=api_key)
        self.tencent_client = tencent_client
        self.schedule_manager = schedule_manager
        
        # Define MCP tools as Claude function calling tools
        self.tools = self._define_mcp_tools()
    
    def _define_mcp_tools(self) -> List[Dict]:
        """Define MCP tools as Claude function calling tools."""
        return [
            {
                "name": "list_channels",
                "description": "List all StreamLive channels and StreamLink flows with their current status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Filter by service type: 'StreamLive', 'StreamLink', or 'all'",
                            "enum": ["StreamLive", "StreamLink", "all"],
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by status: 'running', 'idle', 'stopped', 'error', or 'all'",
                            "enum": ["running", "idle", "stopped", "error", "all"],
                        },
                    },
                },
            },
            {
                "name": "search_resources",
                "description": "Search for channels or flows by keyword in their name",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Keyword to search for in resource names",
                        },
                    },
                    "required": ["keyword"],
                },
            },
            {
                "name": "get_channel_status",
                "description": "Get detailed status of a specific channel including input status (main/backup)",
                "input_schema": {
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
            },
            {
                "name": "get_input_status",
                "description": "Get active input status (main/backup) for a StreamLive channel with failover information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            },
            {
                "name": "get_streampackage_status",
                "description": "Get StreamPackage channel status including input status (main/backup)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamPackage channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            },
            {
                "name": "get_css_stream_status",
                "description": "Get CSS stream status",
                "input_schema": {
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
            },
            {
                "name": "get_full_status",
                "description": "Get integrated status for a channel (StreamLive + StreamPackage + CSS)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID",
                        },
                    },
                    "required": ["channel_id"],
                },
            },
            {
                "name": "list_schedules",
                "description": "List all upcoming broadcast schedules",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    
    def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute MCP tool and return result."""
        try:
            if tool_name == "list_channels":
                service = arguments.get("service", "all")
                status = arguments.get("status", "all")
                resources = self.tencent_client.list_all_resources()
                
                # Filter by service
                if service != "all":
                    resources = [r for r in resources if r.get("service") == service]
                
                # Filter by status
                if status != "all":
                    resources = [r for r in resources if r.get("status", "").lower() == status.lower()]
                
                return {
                    "success": True,
                    "count": len(resources),
                    "resources": resources,
                }
            
            elif tool_name == "search_resources":
                keyword = arguments.get("keyword", "")
                all_resources = self.tencent_client.list_all_resources()
                
                matched = []
                keyword_lower = keyword.lower()
                for resource in all_resources:
                    name = resource.get("name", "").lower()
                    resource_id = resource.get("id", "").lower()
                    if keyword_lower in name or keyword_lower in resource_id:
                        matched.append(resource)
                
                return {
                    "success": True,
                    "keyword": keyword,
                    "count": len(matched),
                    "resources": matched,
                }
            
            elif tool_name == "get_channel_status":
                channel_id = arguments.get("channel_id")
                service = arguments.get("service")
                details = self.tencent_client.get_resource_details(channel_id, service)
                
                if details:
                    return {"success": True, **details}
                else:
                    return {"success": False, "error": f"Channel {channel_id} not found"}
            
            elif tool_name == "get_input_status":
                channel_id = arguments.get("channel_id")
                input_status = self.tencent_client.get_channel_input_status(channel_id)
                
                if input_status:
                    return {"success": True, **input_status}
                else:
                    return {"success": False, "error": f"Input status not available for {channel_id}"}
            
            elif tool_name == "get_streampackage_status":
                channel_id = arguments.get("channel_id")
                details = self.tencent_client.get_streampackage_channel_details(channel_id)
                
                if details:
                    return {"success": True, **details}
                else:
                    return {"success": False, "error": f"StreamPackage channel {channel_id} not found"}
            
            elif tool_name == "get_css_stream_status":
                stream_name = arguments.get("stream_name")
                domain = arguments.get("domain")
                details = self.tencent_client.get_css_stream_details(stream_name, domain)
                
                if details:
                    return {"success": True, **details}
                else:
                    return {"success": False, "error": f"CSS stream {stream_name} not found"}
            
            elif tool_name == "get_full_status":
                channel_id = arguments.get("channel_id")
                # Get StreamLive status
                streamlive_details = self.tencent_client.get_resource_details(channel_id, "StreamLive")
                # Get StreamPackage status (if linked)
                streampackage_info = None
                # Get CSS status (if linked)
                css_info = None
                
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "streamlive": streamlive_details,
                    "streampackage": streampackage_info,
                    "css": css_info,
                }
            
            elif tool_name == "list_schedules":
                schedules = self.schedule_manager.get_all_upcoming_schedules()
                return {
                    "success": True,
                    "count": len(schedules),
                    "schedules": schedules,
                }
            
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def answer_query(self, query: str, system_prompt: Optional[str] = None) -> str:
        """Answer a natural language query using Claude API with MCP tools.
        
        Args:
            query: Natural language query
            system_prompt: Optional system prompt
        
        Returns:
            AI-generated response
        """
        if not ANTHROPIC_AVAILABLE:
            return "AI 기능을 사용하려면 Anthropic SDK가 필요합니다. pip install anthropic"
        
        default_system_prompt = """You are a helpful assistant for managing Tencent Cloud streaming resources.
You can help users check the status of StreamLive channels, StreamLink flows, StreamPackage channels, and CSS streams.
You have access to tools that can query these resources.

IMPORTANT RULES:
1. You can ONLY READ/QUERY information. You CANNOT start, stop, create, delete, or modify resources.
2. If a user asks to start, stop, create, delete, or modify anything, you must politely explain:
   "제어 작업(시작/중지/생성/삭제)은 Slack 대시보드에서만 가능합니다. /tencent 명령어로 대시보드를 열어주세요."
3. Always provide clear, helpful responses in Korean.
4. Use emojis to make responses more readable:
   - 🟢 for running/active
   - 🟡 for idle/waiting
   - 🔴 for stopped/error
   - 📊 for status information
   - 🔍 for search results
5. Be concise but informative.
"""
        
        system_prompt = system_prompt or default_system_prompt
        
        messages = [
            {
                "role": "user",
                "content": query,
            }
        ]
        
        # Convert tools to Claude format
        claude_tools = []
        for tool in self.tools:
            claude_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            })
        
        try:
            # First API call - Claude may request tools
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
                tools=claude_tools if claude_tools else None,
            )
            
            # Handle tool calls
            while response.stop_reason == "tool_use":
                # Execute tools
                tool_results = []
                for content in response.content:
                    if content.type == "tool_use":
                        tool_name = content.name
                        tool_id = content.id
                        arguments = content.input
                        
                        logger.info(f"Claude requested tool: {tool_name} with args: {arguments}")
                        result = self._execute_tool(tool_name, arguments)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                
                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
                
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=messages,
                    tools=claude_tools if claude_tools else None,
                )
            
            # Extract text response
            text_parts = []
            for content in response.content:
                if content.type == "text":
                    text_parts.append(content.text)
            
            return "\n".join(text_parts) if text_parts else "응답을 생성할 수 없습니다."
        
        except Exception as e:
            logger.error(f"Error in AI assistant: {e}", exc_info=True)
            return f"오류가 발생했습니다: {str(e)}"
