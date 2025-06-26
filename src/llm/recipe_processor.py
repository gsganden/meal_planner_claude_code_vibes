import json
import re
from typing import Dict, Any, Optional
from src.llm.client import generate_completion
from src.models.schemas import Recipe as RecipeSchema
import logging

logger = logging.getLogger(__name__)


async def extract_recipe_from_text(text: str) -> Dict[str, Any]:
    """Extract a structured recipe from unstructured text"""
    
    # Get the recipe schema for the prompt
    schema_example = {
        "title": "Recipe Name",
        "yield": "Number of servings",
        "ingredients": [
            {"text": "ingredient line", "quantity": "amount", "unit": "unit"}
        ],
        "steps": [
            {"order": 1, "text": "instruction text"}
        ]
    }
    
    messages = [
        {
            "role": "system",
            "content": """You are a recipe extraction assistant. Extract recipe information from the provided text and return it as valid JSON.
            
The JSON must match this structure exactly:
{
  "title": "Recipe Name",
  "yield": "Number of servings",
  "ingredients": [
    {"text": "ingredient line", "quantity": "amount", "unit": "unit"}
  ],
  "steps": [
    {"order": 1, "text": "instruction text"}
  ]
}

Important rules:
- Always include title, yield, ingredients, and steps
- For ingredients, break down into text (full line), quantity (number or string), and unit
- Use empty string for unit if no unit is specified
- Steps must have sequential order numbers starting from 1
- Return ONLY valid JSON, no other text"""
        },
        {
            "role": "user",
            "content": f"Extract the recipe from this text:\n\n{text}"
        }
    ]
    
    response = await generate_completion(messages, temperature=0.1)
    
    # Clean up response and parse JSON
    try:
        # Remove any markdown code blocks if present
        json_text = response.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r'^```(?:json)?\n?', '', json_text)
            json_text = re.sub(r'\n?```$', '', json_text)
        
        recipe_data = json.loads(json_text)
        
        # Validate against schema
        RecipeSchema(**recipe_data)
        
        return recipe_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("Unable to understand the recipe format. Please try again.")
    except Exception as e:
        logger.error(f"Recipe validation failed: {e}")
        raise ValueError("The extracted recipe is incomplete. Please provide more details.")


async def generate_recipe_from_prompt(prompt: str) -> Dict[str, Any]:
    """Generate a new recipe based on a natural language prompt"""
    
    messages = [
        {
            "role": "system",
            "content": """You are a recipe creation assistant. Create recipes based on user requests and return them as valid JSON.
            
The JSON must match this structure exactly:
{
  "title": "Recipe Name",
  "yield": "Number of servings",
  "description": "Brief description (optional)",
  "prep_time_minutes": 15,
  "cook_time_minutes": 30,
  "ingredients": [
    {"text": "ingredient line", "quantity": "amount", "unit": "unit"}
  ],
  "steps": [
    {"order": 1, "text": "instruction text"}
  ],
  "tags": ["tag1", "tag2"]
}

Important rules:
- Always include title, yield, ingredients, and steps
- Create realistic, detailed recipes
- Include prep_time_minutes and cook_time_minutes when appropriate
- Add relevant tags for cuisine, diet, meal type, etc.
- Return ONLY valid JSON, no other text"""
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    response = await generate_completion(messages, temperature=0.3)
    
    # Clean up response and parse JSON
    try:
        # Remove any markdown code blocks if present
        json_text = response.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r'^```(?:json)?\n?', '', json_text)
            json_text = re.sub(r'\n?```$', '', json_text)
        
        recipe_data = json.loads(json_text)
        
        # Validate against schema
        RecipeSchema(**recipe_data)
        
        return recipe_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("Unable to generate recipe. Please try again.")
    except Exception as e:
        logger.error(f"Recipe validation failed: {e}")
        raise ValueError("The generated recipe is incomplete. Please try again.")


async def modify_recipe(current_recipe: Dict[str, Any], modification_request: str) -> Dict[str, Any]:
    """Modify an existing recipe based on user request"""
    
    messages = [
        {
            "role": "system",
            "content": """You are a recipe modification assistant. Modify recipes based on user requests and return the updated recipe as valid JSON.

The JSON must maintain the same structure as the input recipe.
Make only the requested changes while preserving all other recipe details.
Return ONLY valid JSON, no other text."""
        },
        {
            "role": "user",
            "content": f"""Current recipe:
{json.dumps(current_recipe, indent=2)}

Modification request: {modification_request}

Return the modified recipe as JSON."""
        }
    ]
    
    response = await generate_completion(messages, temperature=0.1)
    
    # Clean up response and parse JSON
    try:
        # Remove any markdown code blocks if present
        json_text = response.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r'^```(?:json)?\n?', '', json_text)
            json_text = re.sub(r'\n?```$', '', json_text)
        
        recipe_data = json.loads(json_text)
        
        # Preserve ID and timestamps from original
        if "id" in current_recipe:
            recipe_data["id"] = current_recipe["id"]
        if "created_at" in current_recipe:
            recipe_data["created_at"] = current_recipe["created_at"]
        
        # Validate against schema
        RecipeSchema(**recipe_data)
        
        return recipe_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("Unable to modify recipe. Please try again.")
    except Exception as e:
        logger.error(f"Recipe validation failed: {e}")
        raise ValueError("The modified recipe is invalid. Please try again.")


async def get_recipe_suggestions(recipe: Dict[str, Any], suggestion_type: str) -> str:
    """Get suggestions for a recipe (substitutions, tips, etc.)"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful cooking assistant. Provide clear, practical suggestions for recipes."
        },
        {
            "role": "user",
            "content": f"""Recipe: {recipe.get('title', 'Untitled')}

Ingredients:
{chr(10).join(f"- {ing['text']}" for ing in recipe.get('ingredients', []))}

Request: {suggestion_type}"""
        }
    ]
    
    response = await generate_completion(messages, temperature=0.3, max_tokens=500)
    return response.strip()