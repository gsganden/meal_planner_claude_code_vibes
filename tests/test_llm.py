import pytest
from unittest.mock import AsyncMock, patch
from src.llm.recipe_processor import (
    extract_recipe_from_text, 
    generate_recipe_from_prompt,
    modify_recipe,
    get_recipe_suggestions
)
import json


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing"""
    def _mock_response(content: str):
        mock = AsyncMock()
        mock.return_value = content
        return mock
    return _mock_response


@pytest.mark.asyncio
async def test_extract_recipe_from_text(mock_llm_response):
    """Test extracting recipe from text"""
    mock_recipe = {
        "title": "Simple Pasta",
        "yield": "2 servings",
        "ingredients": [
            {"text": "200g pasta", "quantity": "200", "unit": "g"},
            {"text": "2 tbsp olive oil", "quantity": "2", "unit": "tbsp"}
        ],
        "steps": [
            {"order": 1, "text": "Boil water"},
            {"order": 2, "text": "Cook pasta"}
        ]
    }
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(json.dumps(mock_recipe))):
        
        result = await extract_recipe_from_text("Cook pasta with olive oil")
        
        assert result["title"] == "Simple Pasta"
        assert result["yield"] == "2 servings"
        assert len(result["ingredients"]) == 2
        assert len(result["steps"]) == 2


@pytest.mark.asyncio
async def test_extract_recipe_with_markdown(mock_llm_response):
    """Test extracting recipe when LLM returns markdown code blocks"""
    mock_recipe = {
        "title": "Test Recipe",
        "yield": "1 serving",
        "ingredients": [{"text": "1 item", "quantity": "1", "unit": ""}],
        "steps": [{"order": 1, "text": "Do something"}]
    }
    
    # Mock response with markdown code blocks
    markdown_response = f"```json\n{json.dumps(mock_recipe, indent=2)}\n```"
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(markdown_response)):
        
        result = await extract_recipe_from_text("Some recipe text")
        assert result["title"] == "Test Recipe"


@pytest.mark.asyncio
async def test_extract_recipe_invalid_json(mock_llm_response):
    """Test handling of invalid JSON from LLM"""
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response("This is not JSON")):
        
        with pytest.raises(ValueError, match="Unable to understand the recipe format"):
            await extract_recipe_from_text("Some recipe text")


@pytest.mark.asyncio
async def test_extract_recipe_incomplete(mock_llm_response):
    """Test handling of incomplete recipe data"""
    incomplete_recipe = {
        "title": "Incomplete Recipe",
        # Missing required fields
    }
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(json.dumps(incomplete_recipe))):
        
        with pytest.raises(ValueError, match="The extracted recipe is incomplete"):
            await extract_recipe_from_text("Some recipe text")


@pytest.mark.asyncio
async def test_generate_recipe_from_prompt(mock_llm_response):
    """Test generating a recipe from a prompt"""
    mock_recipe = {
        "title": "Vegetable Stir Fry",
        "yield": "4 servings",
        "description": "Quick and healthy vegetable stir fry",
        "prep_time_minutes": 15,
        "cook_time_minutes": 10,
        "ingredients": [
            {"text": "2 cups mixed vegetables", "quantity": "2", "unit": "cup"},
            {"text": "2 tbsp soy sauce", "quantity": "2", "unit": "tbsp"}
        ],
        "steps": [
            {"order": 1, "text": "Heat oil in wok"},
            {"order": 2, "text": "Add vegetables and stir fry"}
        ],
        "tags": ["vegetarian", "quick", "healthy"]
    }
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(json.dumps(mock_recipe))):
        
        result = await generate_recipe_from_prompt("Create a healthy vegetable stir fry")
        
        assert result["title"] == "Vegetable Stir Fry"
        assert result["prep_time_minutes"] == 15
        assert "vegetarian" in result["tags"]


@pytest.mark.asyncio
async def test_modify_recipe(mock_llm_response):
    """Test modifying an existing recipe"""
    current_recipe = {
        "id": "123",
        "title": "Chicken Pasta",
        "yield": "4 servings",
        "ingredients": [
            {"text": "500g chicken", "quantity": "500", "unit": "g"},
            {"text": "300g pasta", "quantity": "300", "unit": "g"}
        ],
        "steps": [
            {"order": 1, "text": "Cook chicken"},
            {"order": 2, "text": "Cook pasta"}
        ],
        "created_at": "2025-01-01T00:00:00"
    }
    
    modified_recipe = current_recipe.copy()
    modified_recipe["title"] = "Vegan Pasta"
    modified_recipe["ingredients"][0] = {"text": "500g tofu", "quantity": "500", "unit": "g"}
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(json.dumps(modified_recipe))):
        
        result = await modify_recipe(current_recipe, "Make this recipe vegan")
        
        assert result["title"] == "Vegan Pasta"
        assert result["ingredients"][0]["text"] == "500g tofu"
        # Should preserve ID and created_at
        assert result["id"] == "123"
        assert result["created_at"] == "2025-01-01T00:00:00"


@pytest.mark.asyncio
async def test_get_recipe_suggestions(mock_llm_response):
    """Test getting recipe suggestions"""
    recipe = {
        "title": "Chocolate Cake",
        "ingredients": [
            {"text": "2 cups flour", "quantity": "2", "unit": "cup"},
            {"text": "1 cup sugar", "quantity": "1", "unit": "cup"}
        ]
    }
    
    suggestion = "To make this cake gluten-free, replace the all-purpose flour with a gluten-free flour blend."
    
    with patch('src.llm.recipe_processor.generate_completion', 
               mock_llm_response(suggestion)):
        
        result = await get_recipe_suggestions(recipe, "How to make this gluten-free?")
        assert "gluten-free" in result


@pytest.mark.asyncio
async def test_llm_client_initialization():
    """Test LLM client initialization"""
    from src.llm.client import get_llm_client, reset_llm_client
    
    # Reset client first
    reset_llm_client()
    
    # Mock the settings
    with patch('src.llm.client.get_settings') as mock_settings:
        mock_settings.return_value.google_api_key = "test-key"
        mock_settings.return_value.google_openai_base_url = "https://test.url"
        
        client = get_llm_client()
        assert client is not None
        assert client.api_key == "test-key"
        assert client.base_url == "https://test.url"
        
        # Should return same instance
        client2 = get_llm_client()
        assert client is client2