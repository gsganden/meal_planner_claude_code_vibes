"""Test WebSocket timing-related requirements."""
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
import tempfile
import os

from src.main import app
from src.db.database import Base, get_db
from src.db.models import User, Recipe


@pytest_asyncio.fixture
async def test_client_with_recipe():
    """Create test client with authenticated user and recipe for WebSocket testing"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Set test database URL
    database_url = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["TESTING"] = "true"  # Disable rate limiting in tests
    
    # Create engine for this test
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=None  # Disable connection pooling for tests
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Override the get_db dependency
    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client - using regular TestClient for WebSocket
    client = TestClient(app)
    
    # Create user and get token
    signup_response = client.post("/v1/auth/signup", json={
        "email": "ws_test@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    
    if signup_response.status_code != 201:
        print(f"Signup failed: {signup_response.status_code}")
        print(f"Response: {signup_response.json()}")
        raise Exception(f"Signup failed: {signup_response.json()}")
    
    token = signup_response.json()["access_token"]
    
    # Create a recipe
    client.headers["Authorization"] = f"Bearer {token}"
    recipe_response = client.post("/v1/recipes", json={
        # Empty recipe to start
    })
    recipe_id = recipe_response.json()["id"]
    
    yield client, token, recipe_id
    
    # Cleanup
    await engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)
    
    # Clear dependency override
    app.dependency_overrides.clear()


def test_websocket_5_second_auth_timeout_actual(test_client_with_recipe):
    """Test that WebSocket actually closes after 5 seconds without auth."""
    client, token, recipe_id = test_client_with_recipe
    
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Don't send auth message, just wait
            # The server should close the connection after 5 seconds
            start_time = time.time()
            
            # Try to receive - should raise WebSocketDisconnect
            websocket.receive_json()
    
    # Verify it took approximately 5 seconds
    elapsed = time.time() - start_time
    assert 4.5 < elapsed < 5.5, f"Timeout took {elapsed} seconds, expected ~5"
    
    # Verify close code is 1008 (Policy Violation)
    assert exc_info.value.code == 1008
    assert "Authentication timeout" in exc_info.value.reason


def test_websocket_close_code_1008_for_invalid_auth(test_client_with_recipe):
    """Test that invalid authentication closes with code 1008."""
    client, token, recipe_id = test_client_with_recipe
    
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Send invalid auth message
            websocket.send_json({
                "type": "auth",
                "id": "test_1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"token": "invalid-token"}
            })
            
            # Try to receive - should raise WebSocketDisconnect
            websocket.receive_json()
    
    # Verify close code is 1008 (Policy Violation)
    assert exc_info.value.code == 1008
    assert "Invalid token" in exc_info.value.reason


def test_websocket_close_code_1008_for_non_auth_first_message(test_client_with_recipe):
    """Test that sending non-auth message first closes with code 1008."""
    client, token, recipe_id = test_client_with_recipe
    
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Send chat message before auth
            websocket.send_json({
                "type": "chat_message",
                "id": "test_1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"content": "Hello"}
            })
            
            # Try to receive - should raise WebSocketDisconnect
            websocket.receive_json()
    
    # Verify close code is 1008 (Policy Violation)
    assert exc_info.value.code == 1008
    assert "First message must be auth" in exc_info.value.reason


@pytest.mark.asyncio 
async def test_websocket_14_minute_reauth_trigger():
    """Test that auth_required is sent after 14 minutes."""
    from src.chat.websocket import manager
    from src.db.models import User, Recipe
    
    # Create mock user and recipe
    mock_user = Mock(spec=User)
    mock_user.id = "test-user-id"
    mock_recipe = Mock(spec=Recipe)
    mock_recipe.id = "test-recipe-id"
    mock_recipe.user_id = mock_user.id
    
    # Mock websocket
    mock_websocket = AsyncMock()
    mock_websocket.client_state = {"accepted": True}
    
    # Mock database session
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_recipe
    
    # Track messages sent
    messages_sent = []
    async def mock_send_json(data):
        messages_sent.append(data)
    mock_websocket.send_json = mock_send_json
    
    # Mock time to control the 14-minute check
    with patch('time.time') as mock_time:
        # Initial time
        start_time = 1000
        mock_time.return_value = start_time
        
        # Add connection to manager
        manager.active_connections["conn-1"] = {
            "websocket": mock_websocket,
            "user": mock_user,
            "recipe_id": mock_recipe.id,
            "auth_time": start_time,
            "token_exp": start_time + 15 * 60  # 15 minute expiry
        }
        
        # Jump to 14 minutes later
        mock_time.return_value = start_time + 14 * 60
        
        # Run the token check
        await manager._check_token_expiry()
        
        # Verify auth_required was sent
        auth_required_messages = [
            msg for msg in messages_sent 
            if msg.get("type") == "auth_required"
        ]
        assert len(auth_required_messages) == 1
        assert auth_required_messages[0]["payload"]["message"] == "Token expiring soon"


def test_websocket_rate_limit_30_messages_per_minute(test_client_with_recipe):
    """Test that WebSocket enforces 30 messages/minute rate limit."""
    client, token, recipe_id = test_client_with_recipe
    
    with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
        # Send auth
        websocket.send_json({
            "type": "auth",
            "id": "auth_1",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {"token": token}
        })
        
        # Receive auth confirmation
        response = websocket.receive_json()
        assert response["type"] == "recipe_update"
        
        # Try to send 31 messages rapidly
        with patch('time.time') as mock_time:
            # Fix time so all messages are in same minute
            mock_time.return_value = 1000
            
            for i in range(31):
                try:
                    print(f"Sending message {i}")
                    websocket.send_json({
                        "type": "chat_message",
                        "id": f"msg_{i}",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "payload": {"content": f"Message {i}"}
                    })
                    
                    # Try to receive response
                    if i < 30:
                        response = websocket.receive_json()
                        assert response["type"] == "recipe_update"
                        print(f"Received response for message {i}")
                    else:
                        # 31st message should cause disconnect
                        print(f"Expecting disconnect on message {i}")
                        with pytest.raises(WebSocketDisconnect) as exc_info:
                            websocket.receive_json()
                        assert exc_info.value.code == 1008
                        assert "Rate limit exceeded" in exc_info.value.reason
                        break
                except WebSocketDisconnect as e:
                    # Should happen on 31st message
                    print(f"Disconnected on message {i} with code {e.code}: {e.reason}")
                    assert i == 30, f"Expected disconnect on message 30, but got it on message {i}"
                    assert e.code == 1008
                    assert "Rate limit exceeded" in e.reason
                    break


def test_websocket_5_concurrent_connections_limit(test_client_with_recipe):
    """Test that only 5 concurrent connections per user are allowed."""
    client, token, recipe_id = test_client_with_recipe
    
    connections = []
    
    try:
        # Create 5 connections
        for i in range(5):
            ws = client.websocket_connect(f"/v1/chat/{recipe_id}").__enter__()
            connections.append(ws)
            
            # Auth each connection
            ws.send_json({
                "type": "auth",
                "id": f"auth_{i}",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"token": token}
            })
            
            # Verify connected
            response = ws.receive_json()
            assert response["type"] == "recipe_update"
        
        # Try to create 6th connection
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws6 = client.websocket_connect(f"/v1/chat/{recipe_id}").__enter__()
            connections.append(ws6)
            
            # Try to auth - should fail
            ws6.send_json({
                "type": "auth",
                "id": "auth_6",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"token": token}
            })
            ws6.receive_json()
        
        # Verify it was rejected due to connection limit
        assert exc_info.value.code == 1008
        assert "Connection limit exceeded" in exc_info.value.reason
        
    finally:
        # Clean up connections
        for ws in connections:
            try:
                ws.__exit__(None, None, None)
            except:
                pass


def test_websocket_message_size_limit_64kb(test_client_with_recipe):
    """Test that messages over 64KB are rejected."""
    client, token, recipe_id = test_client_with_recipe
    
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Send auth
            websocket.send_json({
                "type": "auth",
                "id": "auth_1",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"token": token}
            })
            
            # Receive auth confirmation
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            
            # Send message over 64KB
            large_content = "x" * (65 * 1024)  # 65KB
            websocket.send_json({
                "type": "chat_message",
                "id": "large_msg",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"content": large_content}
            })
            
            # Should disconnect
            websocket.receive_json()
    
    assert exc_info.value.code == 1009  # CLOSE_TOO_LARGE
    assert "Message too large" in exc_info.value.reason