"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/detailed")
async def detailed_health():
    """Detailed health check endpoint."""
    return {"status": "healthy", "services": {"slack": "connected", "scheduler": "running"}}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}
