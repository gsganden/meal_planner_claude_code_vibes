from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.database import get_db
from src.db.models import Recipe, User
from src.models.schemas import ChatMessage, RecipeUpdate, Recipe as RecipeSchema
from src.auth.security import decode_access_token
from src.llm.recipe_processor import (
    extract_recipe_from_text,
    generate_recipe_from_prompt,
    modify_recipe,
    get_recipe_suggestions
)
from datetime import datetime
import json
import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Get user from JWT token"""
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_recipe_for_user(recipe_id: str, user_id: str, db: AsyncSession) -> Optional[Recipe]:
    """Get recipe if user owns it"""
    result = await db.execute(
        select(Recipe).where(
            and_(
                Recipe.id == recipe_id,
                Recipe.owner_id == user_id
            )
        )
    )
    return result.scalar_one_or_none()


async def process_chat_message(
    message: str,
    recipe: Recipe,
    db: AsyncSession
) -> tuple[str, Optional[Dict[str, Any]]]:
    """Process a chat message and return response content and optional recipe data"""
    
    try:
        # Current recipe data
        current_recipe_data = recipe.recipe_data
        
        # Detect message intent
        message_lower = message.lower()
        
        # Extract recipe from pasted text
        if any(keyword in message_lower for keyword in ["extract", "paste", "copy"]):
            # Extract the text after the command
            text_match = re.search(r'(?:extract|paste|copy).*?:\s*(.*)', message, re.IGNORECASE | re.DOTALL)
            if text_match:
                text_to_extract = text_match.group(1).strip()
                recipe_data = await extract_recipe_from_text(text_to_extract)
                
                # Update recipe in database
                recipe_data["id"] = recipe.id
                recipe_data["created_at"] = current_recipe_data.get("created_at", datetime.utcnow().isoformat())
                recipe_data["updated_at"] = datetime.utcnow().isoformat()
                
                recipe.recipe_data = recipe_data
                recipe.updated_at = datetime.utcnow()
                await db.commit()
                
                return "I've extracted the recipe from your text. Here's what I found:", recipe_data
            else:
                return "Please paste the recipe text after 'Extract recipe from:' and I'll help you structure it.", None
        
        # Generate new recipe
        elif any(keyword in message_lower for keyword in ["create", "make", "generate", "recipe for"]):
            logger.info(f"Generating recipe from prompt: {message[:100]}...")
            recipe_data = await generate_recipe_from_prompt(message)
            logger.info(f"Recipe generated: {recipe_data.get('title', 'Unknown')}")
            
            # Update recipe in database
            recipe_data["id"] = recipe.id
            recipe_data["created_at"] = current_recipe_data.get("created_at", datetime.utcnow().isoformat())
            recipe_data["updated_at"] = datetime.utcnow().isoformat()
            
            recipe.recipe_data = recipe_data
            recipe.updated_at = datetime.utcnow()
            await db.commit()
            
            return f"I've created a {recipe_data['title']} recipe for you!", recipe_data
        
        # Modify existing recipe
        elif current_recipe_data.get("ingredients") and any(
            keyword in message_lower for keyword in 
            ["change", "modify", "update", "make it", "convert", "substitute", "replace"]
        ):
            recipe_data = await modify_recipe(current_recipe_data, message)
            
            # Update recipe in database
            recipe_data["updated_at"] = datetime.utcnow().isoformat()
            recipe.recipe_data = recipe_data
            recipe.updated_at = datetime.utcnow()
            await db.commit()
            
            return "I've updated your recipe based on your request.", recipe_data
        
        # Get suggestions
        elif current_recipe_data.get("ingredients") and any(
            keyword in message_lower for keyword in ["suggest", "tip", "help", "advice"]
        ):
            suggestions = await get_recipe_suggestions(current_recipe_data, message)
            return suggestions, current_recipe_data
        
        # Default: try to understand intent
        else:
            if not current_recipe_data.get("ingredients"):
                return (
                    "I can help you create a recipe! You can:\n"
                    "- Ask me to create a specific recipe (e.g., 'Create a pasta recipe for 4')\n"
                    "- Paste a recipe text for me to extract (e.g., 'Extract recipe from: [your text]')\n"
                    "- Or describe what you'd like to cook!",
                    None
                )
            else:
                return (
                    "I can help you with this recipe. You can ask me to:\n"
                    "- Modify it (e.g., 'Make it vegetarian')\n"
                    "- Get suggestions (e.g., 'Suggest wine pairings')\n"
                    "- Convert units or scale servings\n"
                    "What would you like to do?",
                    current_recipe_data
                )
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return f"Sorry, I couldn't process that request. {str(e)}", None


async def handle_chat(
    websocket: WebSocket,
    recipe_id: str,
    db: AsyncSession
):
    """Handle WebSocket chat connection"""
    # Accept the connection first (required before we can close with a code)
    await websocket.accept()
    
    # Extract token from headers or query params
    auth_header = websocket.headers.get("authorization", "")
    token = None
    
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Check query params as fallback
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Get recipe
    recipe = await get_recipe_for_user(recipe_id, user.id, db)
    if not recipe:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Register client
    client_id = f"{user.id}:{recipe_id}"
    manager.active_connections[client_id] = websocket
    logger.info(f"Client {client_id} connected")
    
    try:
        # Send initial recipe state
        initial_update = RecipeUpdate(
            payload={
                "request_id": None,
                "content": "Connected to recipe chat. How can I help you with this recipe?",
                "recipe_data": recipe.recipe_data if recipe.recipe_data.get("ingredients") else None
            }
        )
        await manager.send_json(websocket, json.loads(initial_update.model_dump_json()))
        
        # Handle messages
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            try:
                # Parse message
                msg = ChatMessage(**data)
                
                if msg.type != "chat_message":
                    continue
                
                user_message = msg.payload.get("content", "")
                if not user_message:
                    continue
                
                logger.info(f"Received message from {client_id}: {user_message[:100]}...")
                
                # Process message
                response_content, recipe_data = await process_chat_message(
                    user_message, recipe, db
                )
                
                logger.info(f"Response generated for {client_id}: {response_content[:100]}...")
                
                # Send response
                response = RecipeUpdate(
                    payload={
                        "request_id": msg.id,
                        "content": response_content,
                        "recipe_data": recipe_data
                    }
                )
                await manager.send_json(websocket, json.loads(response.model_dump_json()))
                
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                error_response = RecipeUpdate(
                    payload={
                        "request_id": data.get("id"),
                        "content": "Sorry, I couldn't process that request. Please try again.",
                        "recipe_data": None
                    }
                )
                await manager.send_json(websocket, json.loads(error_response.model_dump_json()))
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(client_id)