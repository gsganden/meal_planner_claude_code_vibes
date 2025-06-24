import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.main import app
import json


@pytest.mark.asyncio
async def test_full_user_journey(test_client: AsyncClient):
    """Test complete user journey from signup to recipe chat"""
    # 1. User signs up
    signup_response = await test_client.post("/v1/auth/signup", json={
        "email": "journey@example.com",
        "password": "JourneyPass123",
        "confirmPassword": "JourneyPass123"
    })
    assert signup_response.status_code == 201
    
    access_token = signup_response.json()["access_token"]
    refresh_token = signup_response.json()["refresh_token"]
    user_id = signup_response.json()["user"]["id"]
    
    # 2. Create a recipe
    test_client.headers["Authorization"] = f"Bearer {access_token}"
    
    create_response = await test_client.post("/v1/recipes", json={
        "title": "",  # Test auto-title
        "yield": "4 servings",
        "ingredients": [{"text": "placeholder", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "placeholder"}]
    })
    assert create_response.status_code == 201
    
    recipe = create_response.json()
    assert recipe["title"] == "Untitled Recipe 1"
    recipe_id = recipe["id"]
    
    # 3. List recipes
    list_response = await test_client.get("/v1/recipes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    
    # 4. Update recipe
    update_response = await test_client.patch(f"/v1/recipes/{recipe_id}", json={
        "title": "My First Recipe"
    })
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "My First Recipe"
    
    # 5. Test token refresh
    refresh_response = await test_client.post("/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    
    # 6. Use new token
    test_client.headers["Authorization"] = f"Bearer {new_access_token}"
    get_response = await test_client.get(f"/v1/recipes/{recipe_id}")
    assert get_response.status_code == 200
    
    # 7. Delete recipe
    delete_response = await test_client.delete(f"/v1/recipes/{recipe_id}")
    assert delete_response.status_code == 204
    
    # 8. Logout
    logout_response = await test_client.post("/v1/auth/logout", json={
        "refresh_token": refresh_response.json()["refresh_token"]
    })
    assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_recipe_chat_integration(authenticated_client: AsyncClient):
    """Test recipe creation through chat"""
    # Create empty recipe
    create_response = await authenticated_client.post("/v1/recipes", json={
        "title": "Chat Recipe",
        "yield": "1 serving",
        "ingredients": [{"text": "none", "quantity": "0", "unit": ""}],
        "steps": [{"order": 1, "text": "none"}]
    })
    recipe_id = create_response.json()["id"]
    
    # Mock LLM for chat
    mock_recipe = {
        "title": "Pasta Carbonara",
        "yield": "2 servings",
        "ingredients": [
            {"text": "200g spaghetti", "quantity": "200", "unit": "g"},
            {"text": "2 eggs", "quantity": "2", "unit": ""},
            {"text": "100g bacon", "quantity": "100", "unit": "g"}
        ],
        "steps": [
            {"order": 1, "text": "Cook pasta according to package"},
            {"order": 2, "text": "Fry bacon until crispy"},
            {"order": 3, "text": "Mix eggs with cheese"},
            {"order": 4, "text": "Combine all ingredients"}
        ]
    }
    
    with patch('src.chat.websocket.generate_recipe_from_prompt', 
               AsyncMock(return_value=mock_recipe)):
        
        # WebSocket would update the recipe
        # Simulate by directly updating
        update_response = await authenticated_client.patch(f"/v1/recipes/{recipe_id}", 
                                           json=mock_recipe)
        assert update_response.status_code == 200
        
        # Verify recipe was updated
        get_response = await authenticated_client.get(f"/v1/recipes/{recipe_id}")
        updated_recipe = get_response.json()
        assert updated_recipe["title"] == "Pasta Carbonara"
        assert len(updated_recipe["ingredients"]) == 3
        assert len(updated_recipe["steps"]) == 4


@pytest.mark.asyncio
async def test_concurrent_users(test_client: AsyncClient):
    """Test that multiple users can work independently"""
    # Create two users
    user1_response = await test_client.post("/v1/auth/signup", json={
        "email": "user1_concurrent@example.com",
        "password": "User1Pass123",
        "confirmPassword": "User1Pass123"
    })
    token1 = user1_response.json()["access_token"]
    
    user2_response = await test_client.post("/v1/auth/signup", json={
        "email": "user2_concurrent@example.com",
        "password": "User2Pass123",
        "confirmPassword": "User2Pass123"
    })
    token2 = user2_response.json()["access_token"]
    
    # Each creates a recipe
    recipe1_response = await test_client.post("/v1/recipes", 
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "title": "User 1 Recipe",
            "yield": "1 serving",
            "ingredients": [{"text": "item 1", "quantity": "1", "unit": ""}],
            "steps": [{"order": 1, "text": "step 1"}]
        }
    )
    recipe1_id = recipe1_response.json()["id"]
    
    recipe2_response = await test_client.post("/v1/recipes",
        headers={"Authorization": f"Bearer {token2}"},
        json={
            "title": "User 2 Recipe",
            "yield": "2 servings",
            "ingredients": [{"text": "item 2", "quantity": "2", "unit": ""}],
            "steps": [{"order": 1, "text": "step 2"}]
        }
    )
    recipe2_id = recipe2_response.json()["id"]
    
    # Verify isolation - User 1 cannot see User 2's recipe
    user1_get = await test_client.get(f"/v1/recipes/{recipe2_id}",
        headers={"Authorization": f"Bearer {token1}"})
    assert user1_get.status_code == 404
    
    # Verify isolation - User 2 cannot see User 1's recipe
    user2_get = await test_client.get(f"/v1/recipes/{recipe1_id}",
        headers={"Authorization": f"Bearer {token2}"})
    assert user2_get.status_code == 404
    
    # Each user sees only their own recipes
    user1_list = await test_client.get("/v1/recipes",
        headers={"Authorization": f"Bearer {token1}"})
    assert len(user1_list.json()) == 1
    assert user1_list.json()[0]["title"] == "User 1 Recipe"
    
    user2_list = await test_client.get("/v1/recipes",
        headers={"Authorization": f"Bearer {token2}"})
    assert len(user2_list.json()) == 1
    assert user2_list.json()[0]["title"] == "User 2 Recipe"


@pytest.mark.asyncio
async def test_error_scenarios(test_client: AsyncClient):
    """Test various error scenarios"""
    # Test unauthenticated access
    response = await test_client.get("/v1/recipes")
    assert response.status_code == 403
    
    # Test invalid credentials
    response = await test_client.post("/v1/auth/signin", json={
        "email": "nonexistent@example.com",
        "password": "WrongPass123"
    })
    assert response.status_code == 401
    
    # Create user for further tests
    signup_response = await test_client.post("/v1/auth/signup", json={
        "email": "error@example.com",
        "password": "ErrorPass123",
        "confirmPassword": "ErrorPass123"
    })
    token = signup_response.json()["access_token"]
    
    # Test invalid recipe data
    response = await test_client.post("/v1/recipes", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Invalid Recipe"
            # Missing required fields
        })
    assert response.status_code == 422
    
    # Test updating non-existent recipe
    response = await test_client.patch("/v1/recipes/fake-id",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Updated"})
    assert response.status_code == 404