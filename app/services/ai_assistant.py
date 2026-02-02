"""AI Assistant service using Claude API with MCP tools.

This service allows AI to use MCP tools to answer natural language queries.
"""
import json
import logging
from typing import Dict, List, Optional, Any

from app.services.alert_utils import get_channel_alerts

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
            {
                "name": "get_alerts",
                "description": "Get current alerts from running StreamLive channels. Returns alerts categorized by severity (critical, warning, info). Use this to check if there are any active alerts.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Optional: Filter alerts for a specific channel ID",
                        },
                        "severity": {
                            "type": "string",
                            "description": "Optional: Filter by severity level",
                            "enum": ["critical", "warning", "info", "all"],
                        },
                    },
                },
            },
            {
                "name": "analyze_alert",
                "description": "Analyze alerts for a specific channel and provide context, possible causes, and suggested actions. Use this when investigating channel issues or when user asks 'why' an alert occurred.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The StreamLive channel ID with the alert",
                        },
                        "alert_type": {
                            "type": "string",
                            "description": "Optional: Specific alert type to analyze (e.g., 'No Input Data', 'PipelineFailover')",
                        },
                    },
                    "required": ["channel_id"],
                },
            },
            {
                "name": "get_health_summary",
                "description": "Get overall system health summary including channel counts, alert status, and any issues requiring attention. Use this for system-wide status checks.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def _analyze_single_alert(
        self,
        alert: Dict,
        input_status: Optional[Dict],
        linked_flows: List[Dict],
    ) -> Dict:
        """Analyze a single alert and provide context and suggestions."""
        alert_type = alert.get("type", "Unknown")
        pipeline = alert.get("pipeline", "")

        context = {
            "alert": alert,
            "upstream_status": None,
            "possible_causes": [],
        }

        suggested_actions = []

        if alert_type == "No Input Data":
            flow_status_summary = []
            for flow in linked_flows:
                flow_status = flow.get("status", "unknown")
                flow_status_summary.append(f"{flow.get('name', flow.get('id'))}: {flow_status}")
                if flow_status != "running":
                    context["possible_causes"].append(
                        f"StreamLink flow '{flow.get('name')}' is not running (status: {flow_status})"
                    )

            context["upstream_status"] = ", ".join(flow_status_summary) if flow_status_summary else "No linked flows"
            context["possible_causes"].extend([
                "입력 소스가 끊어졌거나 연결되지 않음",
                "네트워크 연결 문제",
                "송출 장비 문제",
            ])
            suggested_actions = [
                "StreamLink flow 상태 확인",
                "소스 장비의 송출 상태 확인",
                "네트워크 연결 점검",
                "소스가 정상이면 flow 재시작",
            ]

        elif alert_type == "PipelineFailover":
            is_main_affected = "Main" in pipeline or "Pipeline A" in pipeline
            context["possible_causes"] = [
                f"{'메인' if is_main_affected else '백업'} 파이프라인의 입력 소스 손실",
                "해당 입력의 네트워크 연결 문제",
                "자동 failover 발생",
            ]
            if input_status:
                context["upstream_status"] = f"Active input: {input_status.get('active_input')}"
            suggested_actions = [
                "현재 활성 입력 상태 확인",
                f"{'메인' if is_main_affected else '백업'} 입력 소스 연결 점검",
                "소스 복구 시 자동 정상화",
            ]

        elif alert_type == "PipelineRecover":
            context["possible_causes"] = ["이전에 실패했던 파이프라인 복구됨"]
            suggested_actions = ["정상 복구됨 - 추가 조치 불필요"]

        elif alert_type == "StreamStop":
            context["possible_causes"] = ["스트림 푸시 중단", "송출 장비 중지", "네트워크 문제"]
            suggested_actions = ["송출 장비 확인", "의도적 중지인지 확인"]

        else:
            context["possible_causes"] = ["알 수 없는 알람"]
            suggested_actions = ["채널 상세 확인"]

        return {
            "alert": alert,
            "context": context,
            "suggested_actions": suggested_actions,
        }

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

            elif tool_name == "get_alerts":
                channel_id_filter = arguments.get("channel_id")
                severity_filter = arguments.get("severity", "all")

                resources = self.tencent_client.list_all_resources()
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
                    alerts = get_channel_alerts(self.tencent_client, ch_id, ch_name)
                    all_alerts.extend(alerts)

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
                        "channels_checked": len(running_channels),
                    },
                    "alerts": all_alerts,
                }

            elif tool_name == "analyze_alert":
                channel_id = arguments.get("channel_id")
                alert_type_filter = arguments.get("alert_type")

                # Get channel details
                channel_details = self.tencent_client.get_resource_details(channel_id, "StreamLive")
                if not channel_details:
                    return {"success": False, "error": f"Channel not found: {channel_id}"}

                channel_name = channel_details.get("name", channel_id)

                # Get current alerts
                alerts = get_channel_alerts(self.tencent_client, channel_id, channel_name)

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

                # Get input status
                input_status = self.tencent_client.get_channel_input_status(channel_id)

                # Get linked StreamLink flows
                from app.services.linkage import ResourceHierarchyBuilder
                resources = self.tencent_client.list_all_resources()
                hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

                linked_flows = []
                for h in hierarchy:
                    if h["parent"].get("id") == channel_id:
                        linked_flows = h["children"]
                        break

                # Analyze each alert
                analyzed_alerts = []
                for alert in alerts:
                    analysis = self._analyze_single_alert(alert, input_status, linked_flows)
                    analyzed_alerts.append(analysis)

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
                        {"id": f.get("id"), "name": f.get("name"), "status": f.get("status")}
                        for f in linked_flows
                    ],
                }

            elif tool_name == "get_health_summary":
                resources = self.tencent_client.list_all_resources()

                streamlive_channels = [r for r in resources if r.get("service") == "StreamLive"]
                streamlink_flows = [r for r in resources if r.get("service") == "StreamLink"]

                running_streamlive = [r for r in streamlive_channels if r.get("status") == "running"]
                running_streamlink = [r for r in streamlink_flows if r.get("status") == "running"]

                # Get alerts
                all_alerts = []
                for channel in running_streamlive:
                    ch_id = channel.get("id", "")
                    ch_name = channel.get("name", "")
                    alerts = get_channel_alerts(self.tencent_client, ch_id, ch_name)
                    all_alerts.extend(alerts)

                critical_alerts = [a for a in all_alerts if a.get("severity") == "critical"]
                warning_alerts = [a for a in all_alerts if a.get("severity") == "warning"]

                # Determine health
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

                # Build issues list
                issues = []
                for alert in critical_alerts + warning_alerts:
                    issues.append({
                        "severity": alert.get("severity"),
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
                        "streamlink_total": len(streamlink_flows),
                        "streamlink_running": len(running_streamlink),
                        "total_alerts": len(all_alerts),
                        "critical_alerts": len(critical_alerts),
                        "warning_alerts": len(warning_alerts),
                    },
                    "issues": issues,
                    "running_channels": [
                        {"id": ch.get("id"), "name": ch.get("name")}
                        for ch in running_streamlive
                    ],
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
You can help users check the status of StreamLive channels, StreamLink flows, and analyze alerts.
You have access to tools that can query these resources and analyze issues.

AVAILABLE TOOLS:
- get_health_summary: Overall system status - use this for "시스템 상태", "전체 상태", "상태 어때"
- get_alerts: Current alerts - use this for "알람 있어?", "경고", "문제 있어?"
- analyze_alert: Alert analysis with causes and actions - use this for "왜", "원인", "분석해줘"
- list_channels: Channel list - use for listing channels
- search_resources: Search by keyword
- get_channel_status: Specific channel status
- get_input_status: Main/backup input status
- get_full_status: Integrated status (StreamLive + StreamPackage + CSS)

IMPORTANT RULES:
1. You can ONLY READ/QUERY information. You CANNOT start, stop, create, delete, or modify resources.
2. If a user asks to start, stop, create, delete, or modify anything, politely explain:
   "제어 작업(시작/중지/생성/삭제)은 Slack 대시보드에서만 가능합니다. /tencent 명령어로 대시보드를 열어주세요."
3. Always provide clear, helpful responses in Korean.
4. When analyzing alerts, explain:
   - What the alert means
   - Possible causes
   - Recommended actions
5. Use emojis to make responses more readable:
   - 🟢 for running/active/healthy
   - 🟡 for idle/warning
   - 🔴 for stopped/error/critical
   - 🚨 for critical alerts
   - ⚠️ for warnings
   - 📊 for status information
   - 🔍 for search results
6. Be concise but informative. For alert analysis, be thorough.
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
