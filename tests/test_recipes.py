import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_create_recipe_minimal(authenticated_client: AsyncClient):
    """Test creating a recipe with minimal data"""
    response = await authenticated_client.post("/v1/recipes", json={
        "title": "Simple Pasta",
        "yield": "2 servings",
        "ingredients": [
            {"text": "200g pasta", "quantity": "200", "unit": "g"}
        ],
        "steps": [
            {"order": 1, "text": "Boil water and cook pasta"}
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Simple Pasta"
    assert data["yield"] == "2 servings"
    assert len(data["ingredients"]) == 1
    assert len(data["steps"]) == 1
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_create_recipe_auto_title(authenticated_client: AsyncClient):
    """Test creating a recipe with auto-generated title"""
    response = await authenticated_client.post("/v1/recipes", json={
        "title": "",
        "yield": "1 serving",
        "ingredients": [
            {"text": "1 apple", "quantity": "1", "unit": ""}
        ],
        "steps": [
            {"order": 1, "text": "Eat the apple"}
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Untitled Recipe 1"


@pytest.mark.asyncio
async def test_create_recipe_full_data(authenticated_client: AsyncClient):
    """Test creating a recipe with all fields"""
    response = await authenticated_client.post("/v1/recipes", json={
        "title": "Chocolate Chip Cookies",
        "yield": "24 cookies",
        "description": "Classic chocolate chip cookies",
        "prep_time_minutes": 15,
        "cook_time_minutes": 12,
        "tags": ["dessert", "cookies"],
        "ingredients": [
            {"text": "2 cups flour", "quantity": 2, "unit": "cup"},
            {"text": "1 cup butter", "quantity": 1, "unit": "cup"},
            {"text": "1 cup chocolate chips", "quantity": 1, "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Preheat oven to 350°F"},
            {"order": 2, "text": "Mix dry ingredients"},
            {"order": 3, "text": "Cream butter and sugar"},
            {"order": 4, "text": "Combine and bake"}
        ],
        "source": {"type": "url", "url": "https://example.com/cookies"}
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Chocolate Chip Cookies"
    assert data["prep_time_minutes"] == 15
    assert data["cook_time_minutes"] == 12
    assert len(data["tags"]) == 2
    assert len(data["ingredients"]) == 3
    assert len(data["steps"]) == 4


@pytest.mark.asyncio
async def test_list_recipes(authenticated_client: AsyncClient):
    """Test listing user's recipes"""
    # Create multiple recipes
    recipes = [
        {"title": "Recipe 1", "yield": "1 serving"},
        {"title": "Recipe 2", "yield": "2 servings"},
        {"title": "Recipe 3", "yield": "3 servings"}
    ]
    
    import asyncio
    for recipe in recipes:
        await authenticated_client.post("/v1/recipes", json={
            **recipe,
            "ingredients": [{"text": "1 item", "quantity": "1", "unit": ""}],
            "steps": [{"order": 1, "text": "Do something"}]
        })
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
    
    # List recipes
    response = await authenticated_client.get("/v1/recipes")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
    
    # Check that all recipes are returned
    titles = [item["title"] for item in data]
    assert set(titles) == {"Recipe 1", "Recipe 2", "Recipe 3"}


@pytest.mark.asyncio
async def test_get_recipe(authenticated_client: AsyncClient):
    """Test getting a specific recipe"""
    # Create a recipe
    create_response = await authenticated_client.post("/v1/recipes", json={
        "title": "Test Recipe",
        "yield": "4 servings",
        "ingredients": [{"text": "1 test", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "Test step"}]
    })
    
    recipe_id = create_response.json()["id"]
    
    # Get the recipe
    response = await authenticated_client.get(f"/v1/recipes/{recipe_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == recipe_id
    assert data["title"] == "Test Recipe"


@pytest.mark.asyncio
async def test_get_nonexistent_recipe(authenticated_client: AsyncClient):
    """Test getting a recipe that doesn't exist"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await authenticated_client.get(f"/v1/recipes/{fake_id}")
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "recipe_not_found"


@pytest.mark.asyncio
async def test_update_recipe(authenticated_client: AsyncClient):
    """Test updating a recipe"""
    # Create a recipe
    create_response = await authenticated_client.post("/v1/recipes", json={
        "title": "Original Title",
        "yield": "2 servings",
        "ingredients": [{"text": "1 item", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "Original step"}]
    })
    
    recipe_id = create_response.json()["id"]
    
    # Update the recipe
    response = await authenticated_client.patch(f"/v1/recipes/{recipe_id}", json={
        "title": "Updated Title",
        "yield": "4 servings",
        "tags": ["updated", "test"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["yield"] == "4 servings"
    assert data["tags"] == ["updated", "test"]
    # Original fields should remain
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["text"] == "1 item"


@pytest.mark.asyncio
async def test_delete_recipe(authenticated_client: AsyncClient):
    """Test deleting a recipe"""
    # Create a recipe
    create_response = await authenticated_client.post("/v1/recipes", json={
        "title": "To Delete",
        "yield": "1 serving",
        "ingredients": [{"text": "1 item", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "Step"}]
    })
    
    recipe_id = create_response.json()["id"]
    
    # Delete the recipe
    response = await authenticated_client.delete(f"/v1/recipes/{recipe_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = await authenticated_client.get(f"/v1/recipes/{recipe_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_recipe_isolation(test_client: AsyncClient):
    """Test that users can only access their own recipes"""
    # Create first user and recipe
    signup1 = await test_client.post("/v1/auth/signup", json={
        "email": "user1@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    token1 = signup1.json()["access_token"]
    
    # Create recipe with first user
    headers1 = {"Authorization": f"Bearer {token1}"}
    create_response = await test_client.post("/v1/recipes", 
        headers=headers1,
        json={
            "title": "User 1 Recipe",
            "yield": "1 serving",
            "ingredients": [{"text": "1 item", "quantity": "1", "unit": ""}],
            "steps": [{"order": 1, "text": "Step"}]
        }
    )
    
    recipe_id = create_response.json()["id"]
    
    # Create second user
    signup2 = await test_client.post("/v1/auth/signup", json={
        "email": "user2@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    token2 = signup2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Try to access first user's recipe with second user
    response = await test_client.get(f"/v1/recipes/{recipe_id}", headers=headers2)
    assert response.status_code == 404
    
    # Try to update first user's recipe
    response = await test_client.patch(f"/v1/recipes/{recipe_id}", 
        headers=headers2,
        json={"title": "Hacked!"}
    )
    assert response.status_code == 404
    
    # Try to delete first user's recipe
    response = await test_client.delete(f"/v1/recipes/{recipe_id}", headers=headers2)
    assert response.status_code == 404