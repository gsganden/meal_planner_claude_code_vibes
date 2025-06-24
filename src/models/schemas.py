from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Union, Any
from datetime import datetime
import re
import uuid


# Recipe Schema (matching recipe-schema.json)
class RecipeIngredient(BaseModel):
    text: str = Field(..., min_length=1, description="Human-readable ingredient line")
    quantity: Union[float, str] = Field(..., description="Numeric amount or free text")
    unit: str = Field(..., description="Unit of measure")
    canonical_name: Optional[str] = None


class RecipeStep(BaseModel):
    order: int = Field(..., ge=1, description="1-based sequence index")
    text: str = Field(..., min_length=1, description="Instruction text")
    image_url: Optional[str] = None


class RecipeSource(BaseModel):
    type: str = Field(..., pattern="^(url|video|pdf|image|text)$")
    url: Optional[str] = None
    file_name: Optional[str] = None


class Recipe(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(...)  # Allow empty string for auto-generation
    yield_: str = Field(..., alias="yield", min_length=1)
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = []
    ingredients: List[RecipeIngredient] = Field(..., min_length=1)
    steps: List[RecipeStep] = Field(..., min_length=1)
    images: Optional[List[str]] = []
    source: Optional[RecipeSource] = None
    visibility: str = Field(default="private", pattern="^private$")


class RecipeSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    title: str
    yield_: str = Field(..., alias="yield")
    updated_at: datetime


class RecipePatch(BaseModel):
    title: Optional[str] = None
    yield_: Optional[str] = Field(None, alias="yield")
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    ingredients: Optional[List[RecipeIngredient]] = None
    steps: Optional[List[RecipeStep]] = None
    images: Optional[List[str]] = None
    source: Optional[RecipeSource] = None
    visibility: Optional[str] = Field(None, pattern="^private$")


# Authentication Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirmPassword: str = Field(..., min_length=8, alias="confirmPassword")
    
    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v
    
    @field_validator("confirmPassword")
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str = Field(..., min_length=8, alias="newPassword")
    
    @field_validator("newPassword")
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


# WebSocket Schemas
class ChatMessage(BaseModel):
    type: str = Field(default="chat_message", pattern="^chat_message$")
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any]


class RecipeUpdate(BaseModel):
    type: str = Field(default="recipe_update", pattern="^recipe_update$")
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any]


# Error Schemas
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict[str, Any]] = None