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


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    from app.services.alert_monitor import get_alert_monitor

    alert_monitor = get_alert_monitor()

    return {
        "status": "ok",
        "alert_monitor_initialized": alert_monitor is not None,
    }
