import re
import html
from typing import Any, Dict, List, Optional
import bleach
import logging

logger = logging.getLogger(__name__)

# Allowed HTML tags for recipe content (very limited)
ALLOWED_TAGS = []  # No HTML tags allowed in recipe content
ALLOWED_ATTRIBUTES = {}


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string input:
    - Strip HTML tags
    - Trim whitespace
    - Limit length
    """
    if not isinstance(value, str):
        return ""
    
    # Strip any HTML tags (bleach will escape any remaining special chars)
    value = bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length if specified
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


def sanitize_recipe_data(recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all string fields in recipe data"""
    sanitized = recipe_data.copy()
    
    # Sanitize string fields
    string_fields = ["title", "description", "yield"]
    for field in string_fields:
        if field in sanitized and sanitized[field]:
            sanitized[field] = sanitize_string(
                sanitized[field],
                max_length=500 if field == "description" else 200
            )
    
    # Sanitize ingredients
    if "ingredients" in sanitized and isinstance(sanitized["ingredients"], list):
        for ingredient in sanitized["ingredients"]:
            if isinstance(ingredient, dict):
                if "text" in ingredient:
                    ingredient["text"] = sanitize_string(ingredient["text"], max_length=200)
                if "unit" in ingredient:
                    ingredient["unit"] = sanitize_string(ingredient["unit"], max_length=50)
                if "canonical_name" in ingredient:
                    ingredient["canonical_name"] = sanitize_string(ingredient["canonical_name"], max_length=100)
    
    # Sanitize steps
    if "steps" in sanitized and isinstance(sanitized["steps"], list):
        for step in sanitized["steps"]:
            if isinstance(step, dict) and "text" in step:
                step["text"] = sanitize_string(step["text"], max_length=1000)
    
    # Sanitize tags
    if "tags" in sanitized and isinstance(sanitized["tags"], list):
        sanitized["tags"] = [
            sanitize_string(tag, max_length=50) 
            for tag in sanitized["tags"] 
            if isinstance(tag, str)
        ][:20]  # Limit to 20 tags
    
    # Sanitize source
    if "source" in sanitized and isinstance(sanitized["source"], dict):
        if "url" in sanitized["source"]:
            # Validate URL format
            url = sanitized["source"]["url"]
            if not is_valid_url(url):
                sanitized["source"]["url"] = ""
        if "file_name" in sanitized["source"] and sanitized["source"]["file_name"]:
            sanitized["source"]["file_name"] = sanitize_filename(
                sanitized["source"]["file_name"], 
                max_length=255
            )
    
    return sanitized


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)$'
    return bool(re.match(pattern, url))


def validate_password_strength(password: str) -> List[str]:
    """
    Validate password strength and return list of issues
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not re.search(r"[a-zA-Z]", password):
        issues.append("Password must contain at least one letter")
    
    if not re.search(r"\d", password):
        issues.append("Password must contain at least one number")
    
    # Additional checks for stronger passwords (optional)
    if len(password) >= 8:
        if not re.search(r"[A-Z]", password):
            logger.info("Password missing uppercase letter (optional)")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
            logger.info("Password missing special character (optional)")
    
    return issues


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a filename to be safe for storage"""
    # Remove any path components
    filename = filename.split("/")[-1].split("\\")[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple dots (except for extension)
    parts = filename.split('.')
    if len(parts) > 1:
        name = '.'.join(parts[:-1])
        name = re.sub(r'\.+', '_', name)  # Replace dots in name with underscores
        ext = parts[-1]
        filename = f"{name}.{ext}"
    
    # Limit length
    if len(filename) > max_length:
        parts = filename.split('.')
        if len(parts) > 1:
            name = parts[0][:max_length - len(parts[-1]) - 1]
            filename = f"{name}.{parts[-1]}"
        else:
            filename = filename[:max_length]
    
    return filename


def validate_recipe_completeness(recipe_data: Dict[str, Any]) -> List[str]:
    """
    Validate that a recipe has minimum required content
    Returns list of missing/invalid fields
    """
    issues = []
    
    # Check required fields - only title is required per spec
    if not recipe_data.get("title") or not recipe_data["title"].strip():
        issues.append("Recipe must have a title")
    
    # Optional field validation - only validate if present
    if "yield" in recipe_data and recipe_data["yield"] is not None:
        if not isinstance(recipe_data["yield"], str) or not recipe_data["yield"].strip():
            issues.append("Yield must be a non-empty string if provided")
    
    # Check ingredients if present
    if "ingredients" in recipe_data and recipe_data["ingredients"] is not None:
        ingredients = recipe_data["ingredients"]
        if not isinstance(ingredients, list):
            issues.append("Ingredients must be a list")
        else:
            for i, ingredient in enumerate(ingredients):
                if not isinstance(ingredient, dict):
                    issues.append(f"Ingredient {i+1} is invalid")
                elif not ingredient.get("text") or not ingredient["text"].strip():
                    issues.append(f"Ingredient {i+1} must have text")
    
    # Check steps if present
    if "steps" in recipe_data and recipe_data["steps"] is not None:
        steps = recipe_data["steps"]
        if not isinstance(steps, list):
            issues.append("Steps must be a list")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    issues.append(f"Step {i+1} is invalid")
                elif not step.get("text") or not step["text"].strip():
                    issues.append(f"Step {i+1} must have text")
                elif "order" in step and (not isinstance(step["order"], int) or step["order"] < 1):
                    issues.append(f"Step {i+1} must have valid order number if order is provided")
    
    return issues