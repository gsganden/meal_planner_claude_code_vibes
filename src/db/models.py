from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Integer
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from src.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    recipes = relationship("Recipe", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    recipe_data = Column(SQLiteJSON, nullable=False)  # Stores full recipe JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="recipes")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(Integer, nullable=False)  # Unix timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(Integer, nullable=False)  # Unix timestamp
    used = Column(Integer, default=0)  # 0 = unused, 1 = used
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")