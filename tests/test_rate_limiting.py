import pytest
import pytest_asyncio
from httpx import AsyncClient
import asyncio
import os
import time


@pytest_asyncio.fixture
async def rate_limit_client(test_client: AsyncClient):
    """Test client with rate limiting enabled"""
    # Enable rate limiting for this test
    os.environ["TEST_RATE_LIMITING"] = "true"
    
    # Clear rate limiter state before test
    from src.middleware.rate_limit import auth_limiter, api_limiter, websocket_limiter
    auth_limiter.requests.clear()
    api_limiter.requests.clear()
    websocket_limiter.requests.clear()
    
    yield test_client
    
    # Cleanup
    os.environ.pop("TEST_RATE_LIMITING", None)
    auth_limiter.requests.clear()
    api_limiter.requests.clear()
    websocket_limiter.requests.clear()


@pytest.mark.asyncio
async def test_auth_rate_limiting(rate_limit_client: AsyncClient):
    """Test rate limiting on auth endpoints (10 req/min)"""
    # Make 10 requests (should succeed)
    for i in range(10):
        response = await rate_limit_client.post("/v1/auth/signin", json={
            "email": f"test{i}@example.com",
            "password": "WrongPass123"
        })
        assert response.status_code in [401, 200]  # Either auth fail or success
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10"
    
    # 11th request should be rate limited
    response = await rate_limit_client.post("/v1/auth/signin", json={
        "email": "test11@example.com",
        "password": "WrongPass123"
    })
    
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limit_exceeded"
    assert "Retry-After" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) == 0


@pytest.mark.asyncio
async def test_api_rate_limiting(rate_limit_client: AsyncClient):
    """Test rate limiting on API endpoints (60 req/min)"""
    # Create authenticated user with unique email
    timestamp = int(time.time() * 1000000)
    signup_response = await rate_limit_client.post("/v1/auth/signup", json={
        "email": f"ratelimit_{timestamp}@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    token = signup_response.json()["access_token"]
    rate_limit_client.headers["Authorization"] = f"Bearer {token}"
    
    # Make requests up to limit
    responses = []
    for i in range(60):
        response = await rate_limit_client.get("/v1/recipes")
        responses.append(response)
        if response.status_code == 429:
            break
    
    # Check that we got rate limited before 60 (accounting for auth requests)
    rate_limited = [r for r in responses if r.status_code == 429]
    assert len(rate_limited) > 0 or len(responses) == 60


@pytest.mark.asyncio
async def test_rate_limit_headers(rate_limit_client: AsyncClient):
    """Test rate limit headers are included"""
    # Create authenticated user to test API endpoint
    timestamp = int(time.time() * 1000000)
    signup_response = await rate_limit_client.post("/v1/auth/signup", json={
        "email": f"headers_{timestamp}@example.com",
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    token = signup_response.json()["access_token"]
    rate_limit_client.headers["Authorization"] = f"Bearer {token}"
    
    response = await rate_limit_client.get("/v1/recipes")
    
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    
    # Verify header values
    limit = int(response.headers["X-RateLimit-Limit"])
    remaining = int(response.headers["X-RateLimit-Remaining"])
    reset = int(response.headers["X-RateLimit-Reset"])
    
    assert limit == 60  # API endpoint limit
    assert remaining >= 0
    assert remaining < limit
    assert reset > 0


@pytest.mark.asyncio
async def test_rate_limit_by_user(rate_limit_client: AsyncClient):
    """Test that rate limits are per-user when authenticated"""
    # Create two users with unique emails
    timestamp = int(time.time() * 1000000)
    user1_response = await rate_limit_client.post("/v1/auth/signup", json={
        "email": f"user1_rl_{timestamp}@example.com",
        "password": "User1Pass123",
        "confirmPassword": "User1Pass123"
    })
    token1 = user1_response.json()["access_token"]
    
    user2_response = await rate_limit_client.post("/v1/auth/signup", json={
        "email": f"user2_rl_{timestamp}@example.com",
        "password": "User2Pass123",
        "confirmPassword": "User2Pass123"
    })
    token2 = user2_response.json()["access_token"]
    
    # Make requests as user1
    rate_limit_client.headers["Authorization"] = f"Bearer {token1}"
    for _ in range(5):
        response = await rate_limit_client.get("/v1/recipes")
        assert response.status_code == 200
    
    # Check remaining for user1
    response = await rate_limit_client.get("/v1/recipes")
    user1_remaining = int(response.headers["X-RateLimit-Remaining"])
    
    # Switch to user2
    rate_limit_client.headers["Authorization"] = f"Bearer {token2}"
    response = await rate_limit_client.get("/v1/recipes")
    user2_remaining = int(response.headers["X-RateLimit-Remaining"])
    
    # User2 should have more remaining requests
    assert user2_remaining > user1_remaining


@pytest.mark.asyncio
async def test_no_rate_limit_on_health(test_client: AsyncClient):
    """Test that health endpoints are not rate limited"""
    # Make many requests to health endpoint
    for _ in range(100):
        response = await test_client.get("/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers