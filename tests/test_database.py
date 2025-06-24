import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User, Recipe


@pytest.mark.asyncio
async def test_database_initialization(test_db_session: AsyncSession):
    """Test that database initializes correctly"""
    # Check that we have a valid session
    assert test_db_session is not None
    assert isinstance(test_db_session, AsyncSession)


@pytest.mark.asyncio
async def test_user_creation(test_db_session: AsyncSession):
    """Test creating a user"""
    # Create a user
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User"
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    # Verify user was created
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_recipe_creation(test_db_session: AsyncSession):
    """Test creating a recipe"""
    # First create a user
    user = User(
        email="chef@example.com",
        password_hash="hashed_password",
        name="Chef User"
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    # Create a recipe
    recipe_data = {
        "title": "Test Recipe",
        "yield": "4 servings",
        "ingredients": [
            {"text": "1 cup flour", "quantity": 1, "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Mix ingredients"}
        ]
    }
    
    recipe = Recipe(
        owner_id=user.id,
        recipe_data=recipe_data
    )
    test_db_session.add(recipe)
    await test_db_session.commit()
    await test_db_session.refresh(recipe)
    
    # Verify recipe was created
    assert recipe.id is not None
    assert recipe.owner_id == user.id
    assert recipe.recipe_data["title"] == "Test Recipe"
    assert recipe.created_at is not None
    assert recipe.updated_at is not None