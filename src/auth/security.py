from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
from src.config import get_settings
import secrets
import time

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Store expiration as Unix timestamp
    to_encode.update({"exp": int(expire.timestamp())})
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token() -> tuple[str, int]:
    """Create a refresh token and its expiration timestamp"""
    token = secrets.token_urlsafe(32)
    expires_at = int((datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)).timestamp())
    return token, expires_at


def create_password_reset_token() -> tuple[str, int]:
    """Create a password reset token and its expiration timestamp (1 hour)"""
    token = secrets.token_urlsafe(32)
    expires_at = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    return token, expires_at


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT access token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def is_token_expired(expires_at: int) -> bool:
    """Check if a token has expired based on Unix timestamp"""
    return int(time.time()) > expires_at