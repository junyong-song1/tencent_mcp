"""Detailed alert notification UI components.

Creates rich, detailed alert notifications similar to monitoring systems
with comprehensive metric information and action buttons.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Korea Standard Time (UTC+9)
KST = timezone(timedelta(hours=9))


def create_detailed_alert_blocks(
    app_name: str = "Tencent Cloud MCP",
    app_icon: str = ":cloud:",
    alert_title: str = "",
    alert_emoji: str = ":rotating_light:",
    severity: str = "high",
    event_time: Optional[datetime] = None,
    metric_info: Optional[Dict[str, Any]] = None,
    action_buttons: Optional[List[Dict[str, str]]] = None,
    footer_text: Optional[str] = None,
) -> List[Dict]:
    """
    Create detailed alert notification blocks similar to monitoring systems.
    
    Args:
        app_name: Application name (e.g., "천리마-24x365 앱")
        app_icon: App icon emoji
        alert_title: Main alert title (e.g., "No Input Data")
        alert_emoji: Emoji for alert (e.g., ":fire::fire::fire:")
        severity: Alert severity ("critical", "high", "medium", "low")
        event_time: Event timestamp
        metric_info: Dictionary of key-value pairs for detailed info
        action_buttons: List of action buttons [{"label": "...", "url": "...", "style": "primary|danger"}]
        footer_text: Footer text with timestamp
    
    Returns:
        List of Slack Block Kit blocks
    """
    blocks = []
    
    # Header: App name and status icons
    header_text = f"{app_icon} *{app_name}*"
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": header_text
        },
        "accessory": {
            "type": "image",
            "image_url": "https://api.slack.com/img/blocks/bkb_template_images/approvalsNewDevice.png",
            "alt_text": "status"
        }
    })
    
    # Alert title with emoji
    if alert_title:
        title_text = f"{alert_emoji} *{alert_title}*"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": title_text
            }
        })
    
    # Event time (convert to KST)
    if event_time:
        if isinstance(event_time, datetime):
            # Convert to KST if timezone-aware, otherwise assume UTC
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            kst_time = event_time.astimezone(KST)
            time_str = kst_time.strftime("%Y-%m-%d %H:%M")
        else:
            time_str = str(event_time)
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"*Event Time:* `start: {time_str} (KST)`"
            }]
        })
    
    # Metric info section (Key-Value pairs)
    if metric_info:
        # Split into fields (max 10 fields per section, 2 columns = 5 rows)
        fields = []
        for key, value in list(metric_info.items())[:10]:  # Limit to 10 fields
            # Format value
            if isinstance(value, bool):
                value_str = "✅" if value else "❌"
            elif isinstance(value, (int, float)):
                value_str = str(value)
            elif value is None:
                value_str = "N/A"
            else:
                value_str = str(value)
            
            fields.append({
                "type": "mrkdwn",
                "text": f"*{key}:*\n`{value_str}`"
            })
        
        # Split fields into sections (10 fields max per section)
        for i in range(0, len(fields), 10):
            section_fields = fields[i:i+10]
            blocks.append({
                "type": "section",
                "fields": section_fields
            })
        
        # If there are more than 10 fields, add remaining in context
        if len(metric_info) > 10:
            remaining = list(metric_info.items())[10:]
            remaining_text = ", ".join([f"{k}: {v}" for k, v in remaining[:5]])
            if len(remaining) > 5:
                remaining_text += f" ... (+{len(remaining)-5} more)"
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"_{remaining_text}_"
                }]
            })
    
    # Action buttons
    if action_buttons:
        actions = {
            "type": "actions",
            "elements": []
        }
        
        for btn in action_buttons:
            label = btn.get("label", "Action")
            url = btn.get("url", "#")
            style = btn.get("style", "default")
            
            button = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": label
                },
                "url": url,
            }
            
            if style == "primary":
                button["style"] = "primary"
            elif style == "danger":
                button["style"] = "danger"
            
            actions["elements"].append(button)
        
        blocks.append(actions)
    
    # Footer with timestamp
    if footer_text:
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": footer_text
            }]
        })
    elif event_time:
        now = datetime.now()
        time_ago = _format_time_ago(event_time, now) if isinstance(event_time, datetime) else ""
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_{time_ago}_"
            }]
        })
    
    return blocks


def create_channel_alert_blocks(
    channel_id: str,
    channel_name: str,
    alert_type: str,
    alert_message: str,
    severity: str = "high",
    pipeline: str = "Unknown",
    set_time: Optional[str] = None,
    clear_time: Optional[str] = None,
    channel_details: Optional[Dict] = None,
    input_status: Optional[Dict] = None,
    streampackage_info: Optional[Dict] = None,
    css_info: Optional[Dict] = None,
) -> List[Dict]:
    """
    Create detailed channel alert notification with comprehensive information.
    
    Args:
        channel_id: StreamLive channel ID
        channel_name: Channel display name
        alert_type: Alert type (e.g., "PipelineFailover", "No Input Data")
        alert_message: Alert message
        severity: Alert severity
        pipeline: Pipeline identifier
        set_time: Alert set time
        clear_time: Alert clear time
        channel_details: Additional channel details
        input_status: Input status information
        streampackage_info: StreamPackage information
        css_info: CSS information
    
    Returns:
        List of Slack Block Kit blocks
    """
    # Determine severity and emoji
    severity_map = {
        "critical": (":rotating_light:", "high"),
        "high": (":fire:", "high"),
        "medium": (":warning:", "medium"),
        "low": (":information_source:", "low"),
    }
    
    emoji, severity_level = severity_map.get(severity.lower(), (":warning:", "medium"))
    
    # Extract service type from channel_details
    service_type = "StreamLive"  # Default
    if channel_details:
        service_type = channel_details.get("service", "StreamLive")
    
    # Include service in alert title for clarity
    alert_title = f"[{service_type}] {alert_type}"
    
    # Parse event time
    event_time = None
    if set_time:
        try:
            if "T" in set_time:
                event_time = datetime.fromisoformat(set_time.replace("Z", "+00:00"))
            else:
                event_time = datetime.fromisoformat(set_time)
        except Exception:
            pass
    
    # Helper function to convert UTC time to KST string
    def _utc_to_kst_str(utc_time_str: str) -> str:
        """Convert UTC ISO time string to KST string."""
        try:
            if "T" in utc_time_str:
                utc_dt = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
            else:
                utc_dt = datetime.fromisoformat(utc_time_str)
            
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            
            kst_dt = utc_dt.astimezone(KST)
            return kst_dt.strftime("%Y-%m-%d %H:%M:%S (KST)")
        except Exception:
            return utc_time_str  # Return original if parsing fails
    
    # Build metric info
    metric_info = {
        "alert_type": alert_type,
        "severity": severity_level,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "pipeline": pipeline,
        "service": service_type,  # Always include service
    }
    
    if set_time:
        metric_info["set_time"] = _utc_to_kst_str(set_time)
    if clear_time:
        metric_info["clear_time"] = _utc_to_kst_str(clear_time)
    
    # Add channel details
    if channel_details:
        metric_info.update({
            "channel_status": channel_details.get("status", "unknown"),
        })
    
    # Add input status
    if input_status:
        metric_info.update({
            "active_input": input_status.get("active_input", "unknown"),
            "active_input_id": input_status.get("active_input_id", "N/A"),
            "verification_sources": ", ".join(input_status.get("verification_sources", [])),
        })
    
    # Add StreamPackage info
    if streampackage_info:
        metric_info.update({
            "streampackage_id": streampackage_info.get("streampackage_id", "N/A"),
            "streampackage_active_input": streampackage_info.get("active_input", "unknown"),
        })
    
    # Add CSS info
    if css_info:
        metric_info.update({
            "css_stream_flowing": css_info.get("stream_flowing", False),
            "css_streampackage_connected": css_info.get("streampackage_connected", False),
        })
    
    # Action buttons
    action_buttons = [
        {
            "label": "상태 확인",
            "url": f"slack://app?team=&id=&tab=home",  # Can be replaced with actual dashboard URL
            "style": "primary"
        },
        {
            "label": "채널 상세",
            "url": f"slack://app?team=&id=&tab=home",  # Can be replaced with actual detail URL
            "style": "default"
        }
    ]
    
    # Footer with service info (KST)
    now_kst = datetime.now(KST)
    footer_text = f"Tencent Cloud MCP - {service_type} | {now_kst.strftime('%Y-%m-%d %H:%M')} (KST)"
    
    return create_detailed_alert_blocks(
        app_name=f"Tencent Cloud MCP - {service_type}",
        app_icon=":cloud:",
        alert_title=alert_title,
        alert_emoji=f"{emoji}{emoji}{emoji}",
        severity=severity_level,
        event_time=event_time,
        metric_info=metric_info,
        action_buttons=action_buttons,
        footer_text=footer_text,
    )


def _format_time_ago(event_time: datetime, now: datetime) -> str:
    """Format time ago string."""
    delta = now - event_time
    
    if delta.days > 0:
        return f"{delta.days}일 전"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours}시간 전"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes}분 전"
    else:
        return "방금 전"
