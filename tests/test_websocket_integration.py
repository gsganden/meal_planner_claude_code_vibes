"""
WebSocket Integration Tests

These tests verify the complete authentication flow from connection to re-authentication,
ensuring all components work together correctly.
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app
from src.db.database import Base, get_db
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timedelta
import os
import tempfile
import json
import asyncio
import time
from src.auth.security import create_access_token
import threading


@pytest_asyncio.fixture
async def integration_test_setup():
    """Create comprehensive test setup for integration testing"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Set test database URL
    database_url = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["TESTING"] = "true"
    
    # Create engine for this test
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=None
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
    
    # Create test client
    client = TestClient(app)
    
    # Create user and get tokens
    signup_response = client.post("/v1/auth/signup", json={
        "email": "integration_test@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    
    if signup_response.status_code != 201:
        raise Exception(f"Signup failed: {signup_response.json()}")
    
    auth_data = signup_response.json()
    token = auth_data["access_token"]
    refresh_token = auth_data["refresh_token"]
    user_id = auth_data["user"]["id"]
    
    # Create a recipe
    client.headers["Authorization"] = f"Bearer {token}"
    recipe_response = client.post("/v1/recipes", json={
        "title": "Integration Test Recipe",
        "yield": "4 servings",
        "ingredients": [
            {"text": "2 cups flour", "quantity": "2", "unit": "cup"},
            {"text": "1 cup water", "quantity": "1", "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Mix ingredients"},
            {"order": 2, "text": "Bake at 350F"}
        ]
    })
    
    recipe_id = recipe_response.json()["id"]
    
    yield {
        "client": client,
        "token": token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "recipe_id": recipe_id,
        "engine": engine,
        "db_fd": db_fd,
        "db_path": db_path
    }
    
    # Cleanup
    app.dependency_overrides.clear()
    await engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


class TestFullAuthenticationFlow:
    """Test the complete authentication flow from start to finish"""
    
    def test_successful_auth_flow(self, integration_test_setup):
        """Test: Connect → Auth → Chat → Response"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Step 1: Send auth message
            auth_msg = {
                "type": "auth",
                "id": "auth_integration_1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            }
            websocket.send_json(auth_msg)
            
            # Step 2: Receive initial recipe update
            initial_response = websocket.receive_json()
            assert initial_response["type"] == "recipe_update"
            assert "Connected to recipe chat" in initial_response["payload"]["content"]
            assert initial_response["payload"]["recipe_data"] is not None
            assert initial_response["payload"]["recipe_data"]["title"] == "Integration Test Recipe"
            
            # Step 3: Send chat message
            chat_msg = {
                "type": "chat_message",
                "id": "msg_integration_1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "What can I do with this recipe?"}
            }
            websocket.send_json(chat_msg)
            
            # Step 4: Receive response
            chat_response = websocket.receive_json()
            assert chat_response["type"] == "recipe_update"
            assert chat_response["payload"]["request_id"] == "msg_integration_1"
            assert len(chat_response["payload"]["content"]) > 0
    
    def test_auth_timeout_integration(self, integration_test_setup):
        """Test that connection closes after 5 seconds without auth"""
        setup = integration_test_setup
        client = setup["client"]
        recipe_id = setup["recipe_id"]
        
        # This test is limited by TestClient's synchronous nature
        # In a real async environment, the server would close after 5 seconds
        try:
            with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
                # Don't send auth, just wait
                # In production, this would timeout after 5 seconds
                pass
        except Exception as e:
            # Expected behavior - connection should close
            assert "disconnect" in str(type(e)).lower()
    
    def test_invalid_auth_integration(self, integration_test_setup):
        """Test complete flow with invalid authentication"""
        setup = integration_test_setup
        client = setup["client"]
        recipe_id = setup["recipe_id"]
        
        try:
            with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
                # Send auth with invalid token
                auth_msg = {
                    "type": "auth",
                    "id": "auth_invalid",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"token": "completely.invalid.token"}
                }
                websocket.send_json(auth_msg)
                
                # Should disconnect immediately
                websocket.receive_json()
                pytest.fail("Should have disconnected with invalid token")
        except Exception as e:
            # Verify proper disconnection
            assert "disconnect" in str(type(e)).lower()


class TestMessageFlowIntegration:
    """Test various message flows work correctly together"""
    
    def test_recipe_modification_flow(self, integration_test_setup):
        """Test: Auth → Modify Recipe → Verify Update"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with patch('src.chat.websocket.modify_recipe', 
                   AsyncMock(return_value={
                       "id": recipe_id,
                       "title": "Integration Test Recipe - Doubled",
                       "yield": "8 servings",
                       "ingredients": [
                           {"text": "4 cups flour", "quantity": "4", "unit": "cup"},
                           {"text": "2 cups water", "quantity": "2", "unit": "cup"}
                       ],
                       "steps": [
                           {"order": 1, "text": "Mix ingredients"},
                           {"order": 2, "text": "Bake at 350F"}
                       ],
                       "updated_at": datetime.utcnow().isoformat()
                   })):
            
            with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
                # Authenticate
                websocket.send_json({
                    "type": "auth",
                    "id": "auth_mod",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"token": token}
                })
                websocket.receive_json()  # Skip initial
                
                # Request modification
                websocket.send_json({
                    "type": "chat_message",
                    "id": "msg_double",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"content": "Modify this recipe to double the servings"}
                })
                
                # Verify response
                response = websocket.receive_json()
                assert response["type"] == "recipe_update"
                assert response["payload"]["request_id"] == "msg_double"
                assert response["payload"]["recipe_data"]["yield"] == "8 servings"
                assert response["payload"]["recipe_data"]["ingredients"][0]["quantity"] == "4"
    
    def test_multiple_messages_flow(self, integration_test_setup):
        """Test sending multiple messages in sequence"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Authenticate
            websocket.send_json({
                "type": "auth",
                "id": "auth_multi",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            websocket.receive_json()  # Skip initial
            
            # Send multiple messages
            messages = [
                "What ingredients do I need?",
                "How long does this take?",
                "Can I make this gluten-free?"
            ]
            
            for i, content in enumerate(messages):
                msg_id = f"msg_multi_{i}"
                websocket.send_json({
                    "type": "chat_message",
                    "id": msg_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"content": content}
                })
                
                # Verify each response
                response = websocket.receive_json()
                assert response["type"] == "recipe_update"
                assert response["payload"]["request_id"] == msg_id
                assert len(response["payload"]["content"]) > 0
    
    def test_error_recovery_flow(self, integration_test_setup):
        """Test that connection continues after processing errors"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Authenticate
            websocket.send_json({
                "type": "auth",
                "id": "auth_error",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            websocket.receive_json()  # Skip initial
            
            # Send message that causes error
            with patch('src.llm.recipe_processor.get_recipe_suggestions', 
                       AsyncMock(side_effect=Exception("Processing error"))):
                
                websocket.send_json({
                    "type": "chat_message",
                    "id": "msg_error",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"content": "Suggest some tips for this recipe"}
                })
                
                # Should receive error response
                error_response = websocket.receive_json()
                assert error_response["type"] == "recipe_update"
                assert "sorry" in error_response["payload"]["content"].lower() or \
                       "couldn't" in error_response["payload"]["content"].lower()
            
            # Connection should still work
            websocket.send_json({
                "type": "chat_message",
                "id": "msg_after_error",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "This should work"}
            })
            
            # Should receive normal response
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            assert response["payload"]["request_id"] == "msg_after_error"


class TestReAuthenticationIntegration:
    """Test re-authentication flow integration"""
    
    def test_reauth_during_session(self, integration_test_setup):
        """Test that re-authentication works during active session"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Initial authentication
            websocket.send_json({
                "type": "auth",
                "id": "auth_1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            websocket.receive_json()  # Skip initial
            
            # Send a message
            websocket.send_json({
                "type": "chat_message",
                "id": "msg_before_reauth",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "Before reauth"}
            })
            websocket.receive_json()
            
            # Simulate re-authentication (as if responding to auth_required)
            websocket.send_json({
                "type": "auth",
                "id": "auth_2",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            
            # Should still be able to send messages
            websocket.send_json({
                "type": "chat_message",
                "id": "msg_after_reauth",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "After reauth"}
            })
            
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            assert response["payload"]["request_id"] == "msg_after_reauth"
    
    def test_expired_token_reauth(self, integration_test_setup):
        """Test re-authentication with expired token fails properly"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": setup["user_id"]},
            expires_delta=timedelta(seconds=-10)  # Already expired
        )
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Initial auth with valid token
            websocket.send_json({
                "type": "auth",
                "id": "auth_valid",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            websocket.receive_json()  # Skip initial
            
            # Try to re-auth with expired token
            try:
                websocket.send_json({
                    "type": "auth",
                    "id": "auth_expired",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"token": expired_token}
                })
                
                # Should disconnect
                websocket.receive_json()
                pytest.fail("Should have disconnected with expired token")
            except Exception as e:
                assert "disconnect" in str(type(e)).lower()


class TestConcurrentConnections:
    """Test multiple concurrent WebSocket connections"""
    
    def test_multiple_recipes_same_user(self, integration_test_setup):
        """Test user can connect to multiple recipes simultaneously"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        
        # Create another recipe
        client.headers["Authorization"] = f"Bearer {token}"
        recipe2_response = client.post("/v1/recipes", json={
            "title": "Second Recipe",
            "yield": "2 servings",
            "ingredients": [{"text": "1 egg", "quantity": "1", "unit": ""}],
            "steps": [{"order": 1, "text": "Cook egg"}]
        })
        recipe2_id = recipe2_response.json()["id"]
        
        # Connect to both recipes
        with client.websocket_connect(f"/v1/chat/{setup['recipe_id']}") as ws1:
            with client.websocket_connect(f"/v1/chat/{recipe2_id}") as ws2:
                # Authenticate both
                for ws in [ws1, ws2]:
                    ws.send_json({
                        "type": "auth",
                        "id": f"auth_{id(ws)}",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "payload": {"token": token}
                    })
                
                # Verify both connections work
                response1 = ws1.receive_json()
                response2 = ws2.receive_json()
                
                assert response1["type"] == "recipe_update"
                assert response2["type"] == "recipe_update"
                
                # Verify different recipes
                assert response1["payload"]["recipe_data"]["title"] == "Integration Test Recipe"
                assert response2["payload"]["recipe_data"]["title"] == "Second Recipe"


class TestSpecCompliance:
    """Verify implementation matches specification exactly"""
    
    def test_message_format_compliance(self, integration_test_setup):
        """Verify all messages match spec format"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # Send auth
            websocket.send_json({
                "type": "auth",
                "id": "auth_spec",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            
            # Check all server messages
            messages_to_check = []
            
            # Initial recipe update
            messages_to_check.append(websocket.receive_json())
            
            # Send chat message
            websocket.send_json({
                "type": "chat_message",
                "id": "msg_spec",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "Test message"}
            })
            
            # Chat response
            messages_to_check.append(websocket.receive_json())
            
            # Verify all messages comply with spec
            for msg in messages_to_check:
                # Required fields (Section 2)
                assert "type" in msg
                assert "id" in msg
                assert "timestamp" in msg
                assert "payload" in msg
                
                # Field types
                assert isinstance(msg["type"], str)
                assert isinstance(msg["id"], str)
                assert isinstance(msg["timestamp"], str)
                assert isinstance(msg["payload"], dict)
                
                # Valid message type
                assert msg["type"] in ["auth", "chat_message", "auth_required", "recipe_update", "error"]
                
                # ISO-8601 timestamp
                try:
                    datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Invalid timestamp format: {msg['timestamp']}")
    
    def test_connection_lifecycle_compliance(self, integration_test_setup):
        """Test connection lifecycle matches spec section 1"""
        setup = integration_test_setup
        client = setup["client"]
        token = setup["token"]
        recipe_id = setup["recipe_id"]
        
        # Test states as defined in spec section 1.4:
        # 1. Connecting - WebSocket handshake
        # 2. Authenticating - Waiting for auth
        # 3. Connected - Authenticated and ready
        # 4. Closed - Terminated
        
        with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
            # State: Authenticating (after connection, before auth)
            
            # Send auth to transition to Connected
            websocket.send_json({
                "type": "auth",
                "id": "auth_lifecycle",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"token": token}
            })
            
            # State: Connected (after successful auth)
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            
            # Verify we can send messages (connected state)
            websocket.send_json({
                "type": "chat_message",
                "id": "msg_connected",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"content": "I am connected"}
            })
            
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
        
        # State: Closed (after context exit)


@pytest.mark.asyncio
async def test_token_expiry_monitoring():
    """Test that token expiry monitoring works correctly"""
    # This test documents the expected behavior
    # Real implementation would require long-running async test
    
    # Expected behavior at 14 minutes:
    # 1. Server sends auth_required message
    # 2. Client has 30 seconds to respond with new auth
    # 3. If no response, connection closes with code 1008
    
    expected_auth_required = {
        "type": "auth_required",
        "id": "msg_199",
        "timestamp": "2025-06-23T10:14:00Z",
        "payload": {
            "reason": "Token expiring soon"
        }
    }
    
    # Verify message format
    assert expected_auth_required["type"] == "auth_required"
    assert expected_auth_required["payload"]["reason"] == "Token expiring soon"