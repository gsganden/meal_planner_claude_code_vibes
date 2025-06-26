from fastapi import APIRouter, Depends
from src.auth.dependencies import get_current_user_admin
from src.chat.websocket import websocket_metrics
from datetime import datetime

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])

@router.get("/websocket")
async def get_websocket_metrics():
    """
    Get WebSocket connection metrics.
    
    This endpoint is public for now but should be protected in production.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": websocket_metrics
    }

@router.post("/websocket/reset")
async def reset_websocket_metrics():
    """Reset WebSocket metrics to zero."""
    for key in websocket_metrics:
        if key != "active_connections":  # Don't reset active connections
            websocket_metrics[key] = 0
    return {"message": "Metrics reset successfully"}