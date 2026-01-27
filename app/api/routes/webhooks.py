"""Webhook endpoints for receiving external notifications."""
import logging
from typing import Dict

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/streamlive")
async def streamlive_webhook(request: Request):
    """
    Receive StreamLive stream push callback notifications.

    Tencent Cloud StreamLive sends webhooks for:
    - event_type 329: Stream push success (start)
    - event_type 330: Stream push interrupted (stop)

    Payload format:
    {
        "data": {
            "appid": 12345,
            "channel_id": "...",
            "event_type": 329 or 330,
            "input_id": "...",
            "interface": "general_callback",
            "pipeline": 0 or 1,
            "sign": "MD5(key + t)",
            "stream_id": "",
            "t": 1234567890
        }
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received StreamLive webhook: {payload.get('data', {}).get('event_type', 'unknown')}")

        # Get alert monitor service
        from app.services.alert_monitor import get_alert_monitor

        alert_monitor = get_alert_monitor()
        if not alert_monitor:
            logger.warning("Alert monitor not initialized, webhook ignored")
            return {"success": True, "message": "Alert monitor not configured"}

        result = alert_monitor.process_webhook_event(payload)
        return result

    except Exception as e:
        logger.error(f"Failed to process StreamLive webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streamlink")
async def streamlink_webhook(request: Request):
    """
    Receive StreamLink callback notifications.

    Placeholder for StreamLink webhooks if supported.
    """
    try:
        payload = await request.json()
        logger.info(f"Received StreamLink webhook: {payload}")

        # Get alert monitor service
        from app.services.alert_monitor import get_alert_monitor

        alert_monitor = get_alert_monitor()
        if not alert_monitor:
            logger.warning("Alert monitor not initialized, webhook ignored")
            return {"success": True, "message": "Alert monitor not configured"}

        # Process similar to StreamLive (adjust based on actual payload format)
        result = alert_monitor.process_webhook_event(payload)
        return result

    except Exception as e:
        logger.error(f"Failed to process StreamLink webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cloud-function")
async def cloud_function_webhook(request: Request):
    """
    Receive alerts forwarded from Tencent Serverless Cloud Function.
    
    This endpoint is designed to receive alerts from Cloud Function that
    is already receiving StreamLive callbacks. The Cloud Function should
    forward the same alert data to this endpoint.
    
    Expected payload format (from Cloud Function):
    {
        "data": {
            "appid": 12345,
            "channel_id": "...",
            "event_type": 329 or 330,
            "input_id": "...",
            "interface": "general_callback",
            "pipeline": 0 or 1,
            "sign": "...",
            "stream_id": "",
            "t": 1234567890
        },
        "source": "cloud-function",
        "original_notification": {
            "channel": "ops_cloud-notification",
            "sent_at": "2024-01-27T19:15:23Z"
        }
    }
    
    Or simplified format:
    {
        "channel_id": "...",
        "event_type": 329 or 330,
        "alert_type": "StreamStart" or "StreamStop",
        "pipeline": 0 or 1,
        "timestamp": "2024-01-27T19:15:23Z",
        "message": "Optional message"
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received Cloud Function webhook: {payload.get('data', {}).get('event_type', payload.get('event_type', 'unknown'))}")

        # Get alert monitor service
        from app.services.alert_monitor import get_alert_monitor

        alert_monitor = get_alert_monitor()
        if not alert_monitor:
            logger.warning("Alert monitor not initialized, webhook ignored")
            return {"success": True, "message": "Alert monitor not configured"}

        # Normalize payload format
        # Cloud Function may send in different formats
        normalized_payload = _normalize_cloud_function_payload(payload)
        
        # Process the webhook event
        result = alert_monitor.process_webhook_event(normalized_payload)
        
        logger.info(f"Processed Cloud Function webhook: {result.get('success', False)}")
        return result

    except Exception as e:
        logger.error(f"Failed to process Cloud Function webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_cloud_function_payload(payload: Dict) -> Dict:
    """
    Normalize Cloud Function payload to standard webhook format.
    
    Handles different payload formats from Cloud Function.
    """
    # If already in standard format, return as-is
    if "data" in payload and "event_type" in payload.get("data", {}):
        return payload
    
    # If in simplified format, convert to standard format
    if "channel_id" in payload or "event_type" in payload:
        event_type = payload.get("event_type")
        channel_id = payload.get("channel_id", "")
        
        # Map alert_type to event_type if needed
        if "alert_type" in payload:
            alert_type = payload.get("alert_type")
            if alert_type == "StreamStart":
                event_type = 329
            elif alert_type == "StreamStop":
                event_type = 330
        
        return {
            "data": {
                "channel_id": channel_id,
                "event_type": event_type,
                "input_id": payload.get("input_id", ""),
                "pipeline": payload.get("pipeline", 0),
                "t": int(payload.get("timestamp", "").replace(":", "").replace("-", "").replace("T", "").replace("Z", "")[:10]) if payload.get("timestamp") else 0,
                "sign": payload.get("sign", ""),
                "stream_id": payload.get("stream_id", ""),
            }
        }
    
    # Return as-is if format is unknown
    logger.warning(f"Unknown Cloud Function payload format: {payload}")
    return payload


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    from app.services.alert_monitor import get_alert_monitor

    alert_monitor = get_alert_monitor()

    return {
        "status": "ok",
        "alert_monitor_initialized": alert_monitor is not None,
        "endpoints": {
            "streamlive": "/api/v1/webhooks/streamlive",
            "streamlink": "/api/v1/webhooks/streamlink",
            "cloud_function": "/api/v1/webhooks/cloud-function",
        }
    }
