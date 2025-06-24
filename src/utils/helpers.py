import json
from datetime import datetime
from typing import Any
import uuid


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling UUIDs and datetime objects"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def json_dumps(obj: Any) -> str:
    """JSON dumps with custom encoder"""
    return json.dumps(obj, cls=CustomJSONEncoder)


def get_next_recipe_number(user_id: str, existing_count: int) -> int:
    """Get the next recipe number for auto-generated titles"""
    return existing_count + 1


def generate_recipe_title(recipe_number: int) -> str:
    """Generate auto-incremented recipe title"""
    return f"Untitled Recipe {recipe_number}"