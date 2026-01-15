"""Resource API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_async_tencent_client
from app.services.tencent_client import AsyncTencentClient

router = APIRouter()


@router.get("")
async def list_resources(
    service: Optional[str] = Query(None, description="Filter by service (StreamLive, StreamLink)"),
    status: Optional[str] = Query(None, description="Filter by status (running, stopped, idle)"),
    client: AsyncTencentClient = Depends(get_async_tencent_client),
):
    """List all resources with optional filtering."""
    resources = await client.list_all_resources()

    if service:
        resources = [r for r in resources if r.get("service") == service]

    if status:
        resources = [r for r in resources if r.get("status") == status]

    return {
        "total": len(resources),
        "resources": resources,
    }


@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    service: str = Query(..., description="Service type (StreamLive, StreamLink)"),
    client: AsyncTencentClient = Depends(get_async_tencent_client),
):
    """Get resource details by ID."""
    details = await client.get_resource_details(resource_id, service)

    if not details:
        return {"error": "Resource not found"}

    return details


@router.post("/{resource_id}/control")
async def control_resource(
    resource_id: str,
    action: str = Query(..., description="Action (start, stop, restart)"),
    service: str = Query(..., description="Service type (StreamLive, StreamLink)"),
    client: AsyncTencentClient = Depends(get_async_tencent_client),
):
    """Control a resource (start/stop/restart)."""
    if action not in ["start", "stop", "restart"]:
        return {"success": False, "error": "Invalid action"}

    result = await client.control_resource(resource_id, service, action)
    return result


@router.post("/cache/clear")
async def clear_cache(
    client: AsyncTencentClient = Depends(get_async_tencent_client),
):
    """Clear the resource cache."""
    client.clear_cache()
    return {"success": True, "message": "Cache cleared"}
