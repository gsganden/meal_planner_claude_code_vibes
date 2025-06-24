import pytest
from httpx import AsyncClient
from src.db.models import User, RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest.mark.asyncio
async def test_signup_success(test_client: AsyncClient):
    """Test successful user signup"""
    response = await test_client.post("/v1/auth/signup", json={
        "email": "newuser@example.com",
        "password": "SecurePass123",
        "confirmPassword": "SecurePass123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["id"] is not None


@pytest.mark.asyncio
async def test_signup_password_validation(test_client: AsyncClient):
    """Test password validation during signup"""
    # Password too short
    response = await test_client.post("/v1/auth/signup", json={
        "email": "user@example.com",
        "password": "short",
        "confirmPassword": "short"
    })
    assert response.status_code == 422
    
    # Password without letter
    response = await test_client.post("/v1/auth/signup", json={
        "email": "user@example.com",
        "password": "12345678",
        "confirmPassword": "12345678"
    })
    assert response.status_code == 422
    
    # Password without number
    response = await test_client.post("/v1/auth/signup", json={
        "email": "user@example.com",
        "password": "abcdefgh",
        "confirmPassword": "abcdefgh"
    })
    assert response.status_code == 422
    
    # Passwords don't match
    response = await test_client.post("/v1/auth/signup", json={
        "email": "user@example.com",
        "password": "ValidPass123",
        "confirmPassword": "DifferentPass123"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_duplicate_email(test_client: AsyncClient):
    """Test signup with existing email"""
    # First signup
    await test_client.post("/v1/auth/signup", json={
        "email": "duplicate@example.com",
        "password": "ValidPass123",
        "confirmPassword": "ValidPass123"
    })
    
    # Second signup with same email
    response = await test_client.post("/v1/auth/signup", json={
        "email": "duplicate@example.com",
        "password": "AnotherPass123",
        "confirmPassword": "AnotherPass123"
    })
    
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "email_exists"


@pytest.mark.asyncio
async def test_signin_success(test_client: AsyncClient):
    """Test successful signin"""
    # First create a user
    await test_client.post("/v1/auth/signup", json={
        "email": "signin@example.com",
        "password": "ValidPass123",
        "confirmPassword": "ValidPass123"
    })
    
    # Then signin
    response = await test_client.post("/v1/auth/signin", json={
        "email": "signin@example.com",
        "password": "ValidPass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "signin@example.com"


@pytest.mark.asyncio
async def test_signin_invalid_credentials(test_client: AsyncClient):
    """Test signin with invalid credentials"""
    # Create a user
    await test_client.post("/v1/auth/signup", json={
        "email": "valid@example.com",
        "password": "ValidPass123",
        "confirmPassword": "ValidPass123"
    })
    
    # Wrong password
    response = await test_client.post("/v1/auth/signin", json={
        "email": "valid@example.com",
        "password": "WrongPass123"
    })
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"
    
    # Non-existent email
    response = await test_client.post("/v1/auth/signin", json={
        "email": "nonexistent@example.com",
        "password": "SomePass123"
    })
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_refresh_token(test_client: AsyncClient):
    """Test refreshing access token"""
    # Create user and get tokens
    signup_response = await test_client.post("/v1/auth/signup", json={
        "email": "refresh@example.com",
        "password": "ValidPass123",
        "confirmPassword": "ValidPass123"
    })
    
    refresh_token = signup_response.json()["refresh_token"]
    
    # Refresh token
    response = await test_client.post("/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # New token should be different


@pytest.mark.asyncio
async def test_logout(test_client: AsyncClient):
    """Test logout"""
    # Create user and get tokens
    signup_response = await test_client.post("/v1/auth/signup", json={
        "email": "logout@example.com",
        "password": "ValidPass123",
        "confirmPassword": "ValidPass123"
    })
    
    refresh_token = signup_response.json()["refresh_token"]
    
    # Logout
    response = await test_client.post("/v1/auth/logout", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    
    # Try to use refresh token again
    response = await test_client.post("/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password(test_client: AsyncClient):
    """Test password reset request"""
    # Create user
    await test_client.post("/v1/auth/signup", json={
        "email": "reset_test@example.com",
        "password": "OldPass123",
        "confirmPassword": "OldPass123"
    })
    
    # Request password reset
    response = await test_client.post("/v1/auth/forgot-password", json={
        "email": "reset_test@example.com"
    })
    
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    
    # Test with non-existent email (should return same message)
    response = await test_client.post("/v1/auth/forgot-password", json={
        "email": "nonexistent@example.com"
    })
    
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]


@pytest.mark.asyncio
async def test_reset_password(test_client: AsyncClient):
    """Test password reset with token"""
    import time
    from src.auth.security import create_password_reset_token
    from src.db.models import PasswordResetToken, User
    from sqlalchemy import select
    
    # Create user with unique email using timestamp
    email = f"reset_complete_{int(time.time() * 1000000)}@example.com"
    await test_client.post("/v1/auth/signup", json={
        "email": email,
        "password": "OldPass123",
        "confirmPassword": "OldPass123"
    })
    
    # Mock getting a reset token (in real app, this comes from email)
    # Request password reset first to get a token
    reset_response = await test_client.post("/v1/auth/forgot-password", json={
        "email": email
    })
    assert reset_response.status_code == 200
    
    # For testing, we need to get the token that was created
    # In a real app, this would come from the email
    # We'll use a direct database query to simulate getting the token from email
    from src.db.database import get_db
    from src.main import app
    
    reset_token_str = None
    async for db in app.dependency_overrides[get_db]():
        result = await db.execute(
            select(PasswordResetToken)
            .join(User)
            .where(User.email == email)
            .order_by(PasswordResetToken.created_at.desc())
        )
        reset_token = result.scalar_one_or_none()
        if reset_token:
            reset_token_str = reset_token.token
        break
    
    # Reset password with token
    response = await test_client.post("/v1/auth/reset-password", json={
        "token": reset_token_str,
        "newPassword": "NewPass123"
    })
    
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]
    
    # Try to sign in with new password
    response = await test_client.post("/v1/auth/signin", json={
        "email": email,
        "password": "NewPass123"
    })
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # Old password should not work
    response = await test_client.post("/v1/auth/signin", json={
        "email": email,
        "password": "OldPass123"
    })
    
    assert response.status_code == 401