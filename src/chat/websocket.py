from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.database import get_db
from src.db.models import Recipe, User
from src.models.schemas import (
    ChatMessage, RecipeUpdate, Recipe as RecipeSchema,
    AuthMessage, AuthRequiredMessage, ErrorMessage, MessageType
)
from src.auth.security import decode_access_token, is_token_expired
from src.llm.recipe_processor import (
    extract_recipe_from_text,
    generate_recipe_from_prompt,
    modify_recipe,
    get_recipe_suggestions
)
from datetime import datetime, timedelta
import asyncio
import json
import logging
import time
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Metrics tracking
websocket_metrics = {
    "total_connections": 0,
    "active_connections": 0,
    "auth_success": 0,
    "auth_failures": 0,
    "auth_timeouts": 0,
    "messages_received": 0,
    "messages_sent": 0,
    "reauth_attempts": 0,
    "reauth_success": 0,
}


class ConnectionManager:
    """Manages WebSocket connections with rate limiting and connection limits"""
    
    def __init__(self):
        self.active_connections: Dict[str, dict] = {}
        self.user_connections: Dict[str, set] = {}  # user_id -> set of connection_ids
        self.message_counts: Dict[str, list] = {}  # connection_id -> list of timestamps
        self.MAX_CONNECTIONS_PER_USER = 5
        self.MAX_MESSAGES_PER_MINUTE = 30
        self.MAX_MESSAGE_SIZE = 64 * 1024  # 64KB
    
    async def connect(self, websocket: WebSocket, client_id: str, user_id: str = None):
        # Check user connection limit
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            
            if len(self.user_connections[user_id]) >= self.MAX_CONNECTIONS_PER_USER:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Connection limit exceeded"
                )
                return False
            
            self.user_connections[user_id].add(client_id)
        
        self.active_connections[client_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "auth_time": None,
            "token_exp": None
        }
        self.message_counts[client_id] = []
        logger.info(f"Client {client_id} connected")
        return True
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            conn_info = self.active_connections[client_id]
            user_id = conn_info.get("user_id")
            
            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(client_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            del self.active_connections[client_id]
            
            # Clean up message counts
            if client_id in self.message_counts:
                del self.message_counts[client_id]
            
            logger.info(f"Client {client_id} disconnected")
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        if client_id not in self.message_counts:
            self.message_counts[client_id] = []
        
        current_time = time.time()
        # Remove messages older than 1 minute
        self.message_counts[client_id] = [
            t for t in self.message_counts[client_id]
            if current_time - t < 60
        ]
        
        # Check if exceeding limit
        if len(self.message_counts[client_id]) >= self.MAX_MESSAGES_PER_MINUTE:
            logger.info(f"Rate limit exceeded for {client_id}: {len(self.message_counts[client_id])} messages in last minute")
            return False
        
        # Add current message
        self.message_counts[client_id].append(current_time)
        logger.debug(f"Message count for {client_id}: {len(self.message_counts[client_id])}")
        return True
    
    def check_message_size(self, message: str) -> bool:
        """Check if message exceeds size limit"""
        return len(message.encode('utf-8')) <= self.MAX_MESSAGE_SIZE
    
    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()


async def _check_token_expiry():
    """Check all connections for token expiry - used for testing"""
    current_time = time.time()
    
    for client_id, conn_info in list(manager.active_connections.items()):
        if isinstance(conn_info, dict):
            token_exp = conn_info.get("token_exp", 0)
            auth_time = conn_info.get("auth_time", 0)
            
            # Check if 14 minutes have passed since auth
            if auth_time and current_time - auth_time >= 14 * 60:
                websocket = conn_info.get("websocket")
                if websocket:
                    # Send auth_required message
                    auth_required = AuthRequiredMessage(
                        payload={"message": "Token expiring soon"}
                    )
                    await websocket.send_json(json.loads(auth_required.model_dump_json()))
                    logger.info(f"Sent auth_required to {client_id} for testing")


# Expose for testing
manager._check_token_expiry = _check_token_expiry


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


async def monitor_token_expiry(
    websocket: WebSocket,
    token_expiry: int,
    client_id: str
):
    """Monitor token expiry and send auth_required message at 14 minutes"""
    try:
        # Calculate time until 14 minutes (1 minute before token expires)
        current_time = datetime.utcnow().timestamp()
        time_until_warning = max(0, token_expiry - current_time - 60)  # 60 seconds before expiry
        
        if time_until_warning > 0:
            await asyncio.sleep(time_until_warning)
            
            # Send auth_required message
            auth_required = AuthRequiredMessage(
                payload={"reason": "Token expiring soon"}
            )
            await websocket.send_json(json.loads(auth_required.model_dump_json()))
            logger.info(f"Sent auth_required to {client_id}")
            
            # Wait for re-authentication (30 seconds)
            try:
                reauth_msg = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # Validate it's an auth message
                if reauth_msg.get("type") != MessageType.AUTH.value:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Expected auth message")
                    return
                
                auth_msg = AuthMessage(**reauth_msg)
                new_token = auth_msg.payload.get("token")
                
                # Validate new token
                payload = decode_access_token(new_token)
                if not payload:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                    return
                
                # Continue monitoring with new token
                new_expiry = payload.get("exp", 0)
                await monitor_token_expiry(websocket, new_expiry, client_id)
                
            except asyncio.TimeoutError:
                logger.warning(f"Re-authentication timeout for {client_id}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Re-authentication timeout")
                
    except asyncio.CancelledError:
        logger.info(f"Token monitoring cancelled for {client_id}")
    except Exception as e:
        logger.error(f"Error in token monitoring for {client_id}: {str(e)}")


async def handle_chat(
    websocket: WebSocket,
    recipe_id: str,
    db: AsyncSession
):
    """Handle WebSocket chat connection with message-based authentication"""
    # Accept the connection first
    await websocket.accept()
    
    client_id = None
    monitoring_task = None
    
    try:
        # Wait for auth message (5 second timeout)
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
            return
        
        # Validate first message is auth
        if auth_data.get("type") != MessageType.AUTH.value:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="First message must be auth")
            return
        
        # Parse auth message
        try:
            auth_msg = AuthMessage(**auth_data)
        except Exception as e:
            logger.error(f"Invalid auth message format: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid auth message format")
            return
        
        # Extract and validate token
        token = auth_msg.payload.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
            return
        
        # Decode token and get user
        payload = decode_access_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        # Check if token is expired
        if is_token_expired(payload.get("exp", 0)):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
            return
        
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
            return
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return
        
        # Get recipe and verify ownership
        recipe = await get_recipe_for_user(recipe_id, user.id, db)
        if not recipe:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Recipe not found or access denied")
            return
        
        # Register client with connection limit check
        client_id = f"{user.id}:{recipe_id}:{id(websocket)}"  # Add unique ID for multiple connections
        if not await manager.connect(websocket, client_id, user.id):
            websocket_metrics["auth_failures"] += 1
            return  # Connection was rejected due to limit
        
        # Update connection info with auth details
        manager.active_connections[client_id]["auth_time"] = time.time()
        manager.active_connections[client_id]["token_exp"] = payload.get("exp", 0)
        websocket_metrics["auth_success"] += 1
        
        # Start token expiry monitoring
        token_expiry = payload.get("exp", 0)
        monitoring_task = asyncio.create_task(
            monitor_token_expiry(websocket, token_expiry, client_id)
        )
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
            try:
                data = await websocket.receive_json()
                
                # Check message size (convert back to string to check size)
                raw_message = json.dumps(data)
                if not manager.check_message_size(raw_message):
                    await websocket.close(code=1009, reason="Message too large")
                    return
            except json.JSONDecodeError:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JSON")
                return
            except Exception as e:
                # Handle other receive errors
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid message format")
                return
            
            # Check rate limit
            if not manager.check_rate_limit(client_id):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
                return
            
            try:
                message_type = data.get("type")
                
                # Handle re-authentication
                if message_type == MessageType.AUTH.value:
                    auth_msg = AuthMessage(**data)
                    new_token = auth_msg.payload.get("token")
                    
                    # Validate new token
                    new_payload = decode_access_token(new_token)
                    if not new_payload or is_token_expired(new_payload.get("exp", 0)):
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
                        return
                    
                    # Cancel old monitoring task and start new one
                    if monitoring_task:
                        monitoring_task.cancel()
                    
                    token_expiry = new_payload.get("exp", 0)
                    monitoring_task = asyncio.create_task(
                        monitor_token_expiry(websocket, token_expiry, client_id)
                    )
                    
                    logger.info(f"Client {client_id} re-authenticated successfully")
                    continue
                
                # Handle chat messages
                if message_type == MessageType.CHAT_MESSAGE.value:
                    msg = ChatMessage(**data)
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
                else:
                    logger.warning(f"Unexpected message type from {client_id}: {message_type}")
                    
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {str(e)}")
                # Spec 6.2: All errors communicated via recipe_update messages
                error_response = RecipeUpdate(
                    payload={
                        "request_id": msg.id if 'msg' in locals() else None,
                        "content": "Sorry, I couldn't process that request. Please try again.",
                        "recipe_data": None  # No recipe changes when error occurs
                    }
                )
                await manager.send_json(websocket, json.loads(error_response.model_dump_json()))
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {str(e)}")
    finally:
        # Cancel monitoring task
        if monitoring_task:
            monitoring_task.cancel()
        
        # Disconnect client
        if client_id:
            manager.disconnect(client_id)