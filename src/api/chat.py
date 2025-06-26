from fastapi import APIRouter, WebSocket, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.chat.websocket import handle_chat

router = APIRouter()


@router.websocket("/{recipe_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    recipe_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for recipe chat"""
    await handle_chat(websocket, recipe_id, db)