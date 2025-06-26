from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.database import get_db
from src.db.models import User, RefreshToken, PasswordResetToken
from src.models.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest,
    ErrorResponse
)
from src.auth.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, create_password_reset_token, is_token_expired
)
from src.auth.dependencies import get_current_user
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create new user account with email and password"""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "email_exists", "message": "Email already exists"}
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token_str, refresh_expires_at = create_refresh_token()
    
    # Store refresh token
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=refresh_expires_at
    )
    db.add(refresh_token)
    await db.commit()
    
    # Return tokens and user info
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at
        )
    )


@router.post("/signin", response_model=TokenResponse)
async def signin(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate existing user with email and password"""
    # Get user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials", "message": "Invalid email or password"}
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token_str, refresh_expires_at = create_refresh_token()
    
    # Store refresh token
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=refresh_expires_at
    )
    db.add(refresh_token)
    await db.commit()
    
    # Return tokens and user info
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at
        )
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    # Get refresh token from database
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == request.refresh_token)
    )
    token_obj = result.scalar_one_or_none()
    
    # Validate token
    if not token_obj or is_token_expired(token_obj.expires_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired refresh token"}
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": token_obj.user_id})
    new_refresh_token_str, new_refresh_expires_at = create_refresh_token()
    
    # Delete old refresh token
    await db.delete(token_obj)
    
    # Store new refresh token
    new_refresh_token = RefreshToken(
        user_id=token_obj.user_id,
        token=new_refresh_token_str,
        expires_at=new_refresh_expires_at
    )
    db.add(new_refresh_token)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token_str
    }


@router.post("/logout", response_model=dict)
async def logout(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Invalidate refresh token"""
    # Get refresh token from database
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == request.refresh_token)
    )
    token_obj = result.scalar_one_or_none()
    
    if token_obj:
        await db.delete(token_obj)
        await db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send password reset email"""
    # Always return same response to prevent email enumeration
    response_message = "If an account exists with this email, you'll receive password reset instructions"
    
    # Get user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user:
        # Create password reset token
        reset_token_str, reset_expires_at = create_password_reset_token()
        
        # Store reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=reset_token_str,
            expires_at=reset_expires_at
        )
        db.add(reset_token)
        await db.commit()
        
        # TODO: Send email with reset token
        # For MVP, log the token
        logger.info(f"Password reset token for {user.email}: {reset_token_str}")
    
    return {"message": response_message}


@router.post("/reset-password", response_model=dict)
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password with token from email"""
    # Get reset token from database
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token,
            PasswordResetToken.used == 0
        )
    )
    token_obj = result.scalar_one_or_none()
    
    # Validate token
    if not token_obj or is_token_expired(token_obj.expires_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired reset token"}
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired reset token"}
        )
    
    # Update password
    user.password_hash = get_password_hash(request.newPassword)
    
    # Mark token as used
    token_obj.used = 1
    
    await db.commit()
    
    return {"message": "Password updated successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at
    )