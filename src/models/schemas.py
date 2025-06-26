from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Union, Any, Literal
from datetime import datetime
from enum import Enum
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



class Recipe(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = Field(default="")  # Allow empty for auto-generation
    yield_: Optional[str] = Field(None, alias="yield")
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = []
    ingredients: Optional[List[RecipeIngredient]] = []
    steps: Optional[List[RecipeStep]] = []
    images: Optional[List[str]] = []


class RecipeSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    title: str
    yield_: Optional[str] = Field(None, alias="yield")
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
class MessageType(str, Enum):
    AUTH = "auth"
    CHAT_MESSAGE = "chat_message"
    AUTH_REQUIRED = "auth_required"
    RECIPE_UPDATE = "recipe_update"
    ERROR = "error"


class AuthMessage(BaseModel):
    type: Literal["auth"] = "auth"
    id: str = Field(default_factory=lambda: f"auth_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, str]  # {"token": "..."}


class ChatMessage(BaseModel):
    type: Literal["chat_message"] = "chat_message"
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any]  # {"content": "..."}


class AuthRequiredMessage(BaseModel):
    type: Literal["auth_required"] = "auth_required"
    id: str = Field(default_factory=lambda: f"auth_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, str]  # {"reason": "Token expiring soon"}


class RecipeUpdate(BaseModel):
    type: Literal["recipe_update"] = "recipe_update"
    id: str = Field(default_factory=lambda: f"upd_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any]


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    id: str = Field(default_factory=lambda: f"err_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, str]  # {"error": "...", "message": "..."}


# Error Schemas
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict[str, Any]] = None