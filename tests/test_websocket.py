import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from src.main import app
from src.db.database import Base, get_db
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import os
import tempfile
import json


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
        "title": "Test Recipe",
        "yield": "2 servings",
        "ingredients": [{"text": "1 test item", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "Test step"}]
    })
    
    recipe_id = recipe_response.json()["id"]
    
    yield client, token, recipe_id
    
    # Cleanup
    app.dependency_overrides.clear()
    await engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


def test_websocket_authentication(test_client_with_recipe):
    """Test WebSocket connection requires authentication"""
    client, token, recipe_id = test_client_with_recipe
    
    # Note: Due to how TestClient handles WebSocket authentication,
    # we'll test that invalid tokens are rejected instead
    # Try with an invalid token
    try:
        with client.websocket_connect(
            f"/v1/chat/{recipe_id}",
            headers={"Authorization": "Bearer invalid_token"}
        ) as websocket:
            # Should close immediately due to invalid token
            data = websocket.receive_json()
            pytest.fail("Should not receive data with invalid token")
    except Exception as e:
        # Should get WebSocketDisconnect exception
        assert "WebSocketDisconnect" in str(type(e)) or "disconnect" in str(e).lower()


def test_websocket_connection_success(test_client_with_recipe):
    """Test successful WebSocket connection"""
    client, token, recipe_id = test_client_with_recipe
    
    # Connect with valid token
    with client.websocket_connect(
        f"/v1/chat/{recipe_id}",
        headers={"Authorization": f"Bearer {token}"}
    ) as websocket:
        # Should receive initial recipe update
        data = websocket.receive_json()
        assert data["type"] == "recipe_update"
        assert "payload" in data
        assert "content" in data["payload"]
        assert "Connected to recipe chat" in data["payload"]["content"]
        # Recipe data should be present since we created a recipe
        assert data["payload"]["recipe_data"] is not None
        assert data["payload"]["recipe_data"]["id"] == recipe_id
        assert data["payload"]["recipe_data"]["title"] == "Test Recipe"


def test_websocket_chat_message(test_client_with_recipe):
    """Test sending chat message through WebSocket"""
    client, token, recipe_id = test_client_with_recipe
    
    with client.websocket_connect(
        f"/v1/chat/{recipe_id}",
        headers={"Authorization": f"Bearer {token}"}
    ) as websocket:
        # Skip initial recipe message
        websocket.receive_json()
        
        # Send chat message
        websocket.send_json({
            "type": "chat_message",
            "payload": {
                "content": "Give me tips for this recipe"
            }
        })
        
        # Should receive recipe update response
        response = websocket.receive_json()
        assert response["type"] == "recipe_update"
        assert "payload" in response
        assert "content" in response["payload"]
        # The response should contain helpful text about the recipe
        assert response["payload"]["content"] is not None
        assert len(response["payload"]["content"]) > 0


def test_websocket_recipe_update(test_client_with_recipe):
    """Test recipe update through WebSocket"""
    client, token, recipe_id = test_client_with_recipe
    
    mock_updated_recipe = {
        "id": recipe_id,
        "title": "Updated Recipe",
        "yield": "4 servings",
        "ingredients": [
            {"text": "2 cups flour", "quantity": "2", "unit": "cup"},
            {"text": "1 cup water", "quantity": "1", "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Mix ingredients"},
            {"order": 2, "text": "Bake"}
        ]
    }
    
    with patch('src.chat.websocket.modify_recipe', 
               AsyncMock(return_value=mock_updated_recipe)):
        
        with client.websocket_connect(
            f"/v1/chat/{recipe_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            # Skip initial recipe message
            websocket.receive_json()
            
            # Send modification request
            websocket.send_json({
                "type": "chat_message",
                "payload": {
                    "content": "Change this recipe to serve 4 people"
                }
            })
            
            # Should receive updated recipe
            updated = websocket.receive_json()
            assert updated["type"] == "recipe_update"
            assert "payload" in updated
            # The response should contain the updated content message
            assert "updated your recipe" in updated["payload"]["content"]
            # And the updated recipe data
            assert "recipe_data" in updated["payload"]
            assert updated["payload"]["recipe_data"]["title"] == "Updated Recipe"
            assert updated["payload"]["recipe_data"]["yield"] == "4 servings"


def test_websocket_invalid_recipe_id(test_client_with_recipe):
    """Test WebSocket connection with invalid recipe ID"""
    client, token, _ = test_client_with_recipe
    
    # Try to connect to non-existent recipe
    fake_id = "00000000-0000-0000-0000-000000000000"
    try:
        with client.websocket_connect(
            f"/v1/chat/{fake_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            # Should close immediately as recipe doesn't exist
            data = websocket.receive_json()
            pytest.fail("Should not receive data for non-existent recipe")
    except Exception as e:
        # Should get WebSocketDisconnect due to policy violation
        assert "WebSocketDisconnect" in str(type(e)) or "disconnect" in str(e).lower()


def test_websocket_invalid_message_type(test_client_with_recipe):
    """Test sending invalid message type"""
    client, token, recipe_id = test_client_with_recipe
    
    with client.websocket_connect(
        f"/v1/chat/{recipe_id}",
        headers={"Authorization": f"Bearer {token}"}
    ) as websocket:
        # Skip initial recipe message
        websocket.receive_json()
        
        # Send invalid message type - the handler ignores messages with wrong type
        websocket.send_json({
            "type": "invalid_type",
            "payload": {"content": "test"}
        })
        
        # Send a valid message to ensure connection is still alive
        websocket.send_json({
            "type": "chat_message",
            "payload": {"content": "hello"}
        })
        
        # Should receive response to valid message (invalid one is ignored)
        response = websocket.receive_json()
        assert response["type"] == "recipe_update"


def test_websocket_error_handling(test_client_with_recipe):
    """Test error handling in WebSocket"""
    client, token, recipe_id = test_client_with_recipe
    
    with patch('src.llm.recipe_processor.get_recipe_suggestions', 
               AsyncMock(side_effect=Exception("LLM Error"))):
        
        with client.websocket_connect(
            f"/v1/chat/{recipe_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            # Skip initial recipe message
            websocket.receive_json()
            
            # Send chat message that will cause error
            websocket.send_json({
                "type": "chat_message",
                "payload": {"content": "Give me suggestions for this recipe"}
            })
            
            # Should receive response with error info
            error_response = websocket.receive_json()
            assert error_response["type"] == "recipe_update"
            assert "payload" in error_response
            assert "content" in error_response["payload"]
            # The error is handled gracefully and returned in the content
            content = error_response["payload"]["content"]
            assert any(word in content.lower() for word in ["sorry", "couldn't", "error", "help"])


def test_websocket_create_recipe(test_client_with_recipe):
    """Test creating a new recipe through WebSocket"""
    client, token, recipe_id = test_client_with_recipe
    
    mock_new_recipe = {
        "id": recipe_id,
        "title": "Chocolate Cake",
        "yield": "8 servings",
        "ingredients": [
            {"text": "2 cups flour", "quantity": "2", "unit": "cup"},
            {"text": "1 cup sugar", "quantity": "1", "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Mix dry ingredients"},
            {"order": 2, "text": "Bake at 350F"}
        ]
    }
    
    with patch('src.chat.websocket.generate_recipe_from_prompt', 
               AsyncMock(return_value=mock_new_recipe)):
        
        with client.websocket_connect(
            f"/v1/chat/{recipe_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            # Skip initial recipe message
            websocket.receive_json()
            
            # Send create recipe request
            websocket.send_json({
                "type": "chat_message",
                "payload": {"content": "Create a chocolate cake recipe"}
            })
            
            # Should receive new recipe
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            assert "payload" in response
            assert "recipe_data" in response["payload"]
            assert response["payload"]["recipe_data"]["title"] == "Chocolate Cake"
            # Check for a valid response message about creating the recipe
            content = response["payload"]["content"]
            assert "Chocolate Cake" in content or "created" in content.lower()


def test_websocket_extract_recipe(test_client_with_recipe):
    """Test extracting recipe from text through WebSocket"""
    client, token, recipe_id = test_client_with_recipe
    
    mock_extracted_recipe = {
        "id": recipe_id,
        "title": "Simple Pasta",
        "yield": "2 servings",
        "ingredients": [
            {"text": "200g pasta", "quantity": "200", "unit": "g"},
            {"text": "2 cloves garlic", "quantity": "2", "unit": ""}
        ],
        "steps": [
            {"order": 1, "text": "Boil pasta"},
            {"order": 2, "text": "Add garlic"}
        ]
    }
    
    with patch('src.chat.websocket.extract_recipe_from_text', 
               AsyncMock(return_value=mock_extracted_recipe)):
        
        with client.websocket_connect(
            f"/v1/chat/{recipe_id}",
            headers={"Authorization": f"Bearer {token}"}
        ) as websocket:
            # Skip initial recipe message
            websocket.receive_json()
            
            # Send extract recipe request
            websocket.send_json({
                "type": "chat_message",
                "payload": {"content": "Extract recipe from: Boil 200g pasta. Add 2 cloves garlic. Serves 2."}
            })
            
            # Should receive extracted recipe
            response = websocket.receive_json()
            assert response["type"] == "recipe_update"
            assert "payload" in response
            assert "recipe_data" in response["payload"]
            assert response["payload"]["recipe_data"]["title"] == "Simple Pasta"
            # Check for extraction message
            content = response["payload"]["content"]
            assert "extracted" in content.lower() or "found" in content.lower()


def test_websocket_query_params_auth(test_client_with_recipe):
    """Test WebSocket authentication via query parameters"""
    client, token, recipe_id = test_client_with_recipe
    
    # Connect with token in query params instead of headers
    with client.websocket_connect(
        f"/v1/chat/{recipe_id}?token={token}"
    ) as websocket:
        # Should receive initial recipe update
        data = websocket.receive_json()
        assert data["type"] == "recipe_update"
        assert "payload" in data
        assert "Connected to recipe chat" in data["payload"]["content"]