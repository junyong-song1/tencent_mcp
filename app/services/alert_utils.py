"""Centralized alert utilities for StreamLive channels.

This module provides common alert-related constants and functions
used across MCP server, AI assistant, and alert monitor services.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


# Alert severity classification
CRITICAL_ALERTS = frozenset({"No Input Data", "PipelineFailover"})
WARNING_ALERTS = frozenset({"PipelineRecover", "StreamStop"})
INFO_ALERTS = frozenset({"StreamStart"})


def classify_alert_severity(alert_type: str) -> str:
    """Classify alert type into severity level.

    Args:
        alert_type: The alert type string

    Returns:
        Severity level: "critical", "warning", or "info"
    """
    if alert_type in CRITICAL_ALERTS:
        return "critical"
    elif alert_type in WARNING_ALERTS:
        return "warning"
    return "info"


def get_channel_alerts(client: Any, channel_id: str, channel_name: str) -> List[Dict]:
    """Get alerts for a specific StreamLive channel.

    Args:
        client: TencentCloudClient instance
        channel_id: StreamLive channel ID
        channel_name: Channel display name

    Returns:
        List of alert dictionaries with severity classification
    """
    alerts = []
    try:
        from tencentcloud.mdl.v20200326 import models as mdl_models

        mdl_client = client._get_mdl_client()

        # Get channel alerts
        alert_req = mdl_models.DescribeStreamLiveChannelAlertsRequest()
        alert_req.ChannelId = channel_id
        alert_resp = mdl_client.DescribeStreamLiveChannelAlerts(alert_req)

        if not alert_resp.Infos:
            return alerts

        infos = alert_resp.Infos

        # Process Pipeline0 alerts
        for alert in getattr(infos, 'Pipeline0', []) or []:
            clear_time = getattr(alert, 'ClearTime', '')
            if clear_time:  # Skip cleared alerts
                continue

            alert_type = getattr(alert, 'Type', 'Unknown')
            severity = classify_alert_severity(alert_type)

            alerts.append({
                "channel_id": channel_id,
                "channel_name": channel_name,
                "pipeline": "Pipeline A (Main)",
                "type": alert_type,
                "message": getattr(alert, 'Message', ''),
                "set_time": getattr(alert, 'SetTime', ''),
                "severity": severity,
            })

        # Process Pipeline1 alerts
        for alert in getattr(infos, 'Pipeline1', []) or []:
            clear_time = getattr(alert, 'ClearTime', '')
            if clear_time:  # Skip cleared alerts
                continue

            alert_type = getattr(alert, 'Type', 'Unknown')
            severity = classify_alert_severity(alert_type)

            alerts.append({
                "channel_id": channel_id,
                "channel_name": channel_name,
                "pipeline": "Pipeline B (Backup)",
                "type": alert_type,
                "message": getattr(alert, 'Message', ''),
                "set_time": getattr(alert, 'SetTime', ''),
                "severity": severity,
            })

    except Exception as e:
        logger.error(f"Failed to get alerts for channel {channel_id}: {e}")

    return alerts
