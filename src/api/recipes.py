from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime
from src.db.database import get_db
from src.db.models import Recipe, User
from src.models.schemas import Recipe as RecipeSchema, RecipeSummary, RecipePatch, ErrorResponse
from src.auth.dependencies import get_current_user
from src.utils.helpers import generate_recipe_title
from src.utils.validation import sanitize_recipe_data, validate_recipe_completeness
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=RecipeSchema, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe_data: RecipeSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a recipe for the authenticated user"""
    # Generate ID if not provided
    if not recipe_data.id:
        recipe_data.id = str(uuid.uuid4())
    
    # Auto-generate title if needed
    if not recipe_data.title or recipe_data.title.strip() == "":
        # Count existing recipes for this user
        count_result = await db.execute(
            select(func.count(Recipe.id)).where(Recipe.owner_id == current_user.id)
        )
        recipe_count = count_result.scalar() or 0
        recipe_data.title = generate_recipe_title(recipe_count + 1)
    
    # Set timestamps
    now = datetime.utcnow()
    recipe_data.created_at = now
    recipe_data.updated_at = now
    
    # Sanitize recipe data
    recipe_dict = recipe_data.model_dump(by_alias=True, mode='json')
    recipe_dict = sanitize_recipe_data(recipe_dict)
    
    # Validate completeness
    issues = validate_recipe_completeness(recipe_dict)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": "Recipe validation failed", "issues": issues}
        )
    
    # Create recipe record
    recipe = Recipe(
        id=recipe_data.id,
        owner_id=current_user.id,
        recipe_data=recipe_dict
    )
    
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)
    
    # Return the recipe data
    return RecipeSchema(**recipe.recipe_data)


@router.get("", response_model=List[RecipeSummary])
async def list_recipes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all recipes for the authenticated user in reverse chronological order"""
    result = await db.execute(
        select(Recipe)
        .where(Recipe.owner_id == current_user.id)
        .order_by(Recipe.updated_at.desc())
    )
    recipes = result.scalars().all()
    
    # Convert to summary format
    summaries = []
    for recipe in recipes:
        data = recipe.recipe_data
        summaries.append(RecipeSummary(
            id=data.get("id", recipe.id),
            title=data.get("title", "Untitled"),
            yield_=data.get("yield", "1 serving"),
            updated_at=recipe.updated_at
        ))
    
    return summaries


@router.get("/{recipe_id}", response_model=RecipeSchema)
async def get_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch a recipe owned by the authenticated user"""
    result = await db.execute(
        select(Recipe).where(
            and_(
                Recipe.id == recipe_id,
                Recipe.owner_id == current_user.id
            )
        )
    )
    recipe = result.scalar_one_or_none()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "recipe_not_found", "message": "Recipe not found"}
        )
    
    return RecipeSchema(**recipe.recipe_data)


@router.patch("/{recipe_id}", response_model=RecipeSchema)
async def update_recipe(
    recipe_id: str,
    recipe_patch: RecipePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a recipe owned by the authenticated user"""
    # Get existing recipe
    result = await db.execute(
        select(Recipe).where(
            and_(
                Recipe.id == recipe_id,
                Recipe.owner_id == current_user.id
            )
        )
    )
    recipe = result.scalar_one_or_none()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "recipe_not_found", "message": "Recipe not found"}
        )
    
    # Get current recipe data
    current_data = recipe.recipe_data.copy()
    
    # Apply patch (only non-None values)
    patch_data = recipe_patch.model_dump(exclude_unset=True, by_alias=True)
    
    # Update fields
    for field, value in patch_data.items():
        if value is not None:
            current_data[field] = value
    
    # Update timestamp
    current_data["updated_at"] = datetime.utcnow().isoformat()
    
    # Validate the complete recipe
    try:
        validated_recipe = RecipeSchema(**current_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": str(e)}
        )
    
    # Update database
    recipe.recipe_data = validated_recipe.model_dump(by_alias=True, mode='json')
    recipe.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(recipe)
    
    return RecipeSchema(**recipe.recipe_data)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a recipe owned by the authenticated user"""
    # Get recipe
    result = await db.execute(
        select(Recipe).where(
            and_(
                Recipe.id == recipe_id,
                Recipe.owner_id == current_user.id
            )
        )
    )
    recipe = result.scalar_one_or_none()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "recipe_not_found", "message": "Recipe not found"}
        )
    
    # Delete recipe
    await db.delete(recipe)
    await db.commit()
    
    return None