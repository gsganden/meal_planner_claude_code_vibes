from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list[datetime]] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every minute
        self._cleanup_task = None
    
    async def start_cleanup(self):
        """Start the cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup(self):
        """Stop the cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Periodically clean up old request entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")
    
    async def _cleanup_old_entries(self):
        """Remove request entries older than 1 minute"""
        cutoff_time = datetime.now() - timedelta(minutes=1)
        
        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > cutoff_time
            ]
            
            # Remove empty entries
            if not self.requests[key]:
                del self.requests[key]
    
    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client"""
        # Use IP address or user ID if authenticated
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # If user is authenticated, use user ID instead
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        return f"ip:{client_ip}"
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, int]:
        """
        Check if request is within rate limit
        Returns: (is_allowed, retry_after_seconds)
        """
        client_key = self._get_client_key(request)
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Get requests in the last minute
        self.requests[client_key] = [
            req_time for req_time in self.requests[client_key]
            if req_time > minute_ago
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_key]) >= self.requests_per_minute:
            # Calculate when the oldest request will expire
            oldest_request = min(self.requests[client_key])
            retry_after = int((oldest_request + timedelta(minutes=1) - now).total_seconds())
            return False, max(1, retry_after)
        
        # Add current request
        self.requests[client_key].append(now)
        return True, 0


# Global rate limiter instances
auth_limiter = RateLimiter(requests_per_minute=10)  # Auth endpoints (general)
api_limiter = RateLimiter(requests_per_minute=300)  # Global API limit per IP
websocket_limiter = RateLimiter(requests_per_minute=30)  # WebSocket messages
recipe_creation_limiter = RateLimiter(requests_per_minute=20)  # Recipe creation per user
password_reset_limiter = RateLimiter(requests_per_minute=1)  # Password reset emails (spec: 5/hour, using 1/min as approximation)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting in test environment unless explicitly testing rate limits
    import os
    if os.environ.get("TESTING") == "true" and os.environ.get("TEST_RATE_LIMITING") != "true":
        return await call_next(request)
    
    # Extract user ID from JWT token if present
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from src.auth.security import decode_access_token
            payload = decode_access_token(token)
            if payload and "sub" in payload:
                request.state.user_id = payload["sub"]
        except Exception:
            pass  # Ignore invalid tokens for rate limiting purposes
    
    # Determine which limiter to use based on path and method
    path = request.url.path
    method = request.method
    
    # Specific endpoint limits
    if path == "/v1/auth/forgot-password" and method == "POST":
        limiter = password_reset_limiter
    elif path == "/v1/recipes" and method == "POST":
        limiter = recipe_creation_limiter
    elif path.startswith("/v1/auth/"):
        limiter = auth_limiter
    elif path.startswith("/v1/chat/"):
        limiter = websocket_limiter
    elif path.startswith("/v1/"):
        limiter = api_limiter
    else:
        # No rate limiting for other paths (health, docs, etc.)
        return await call_next(request)
    
    # Check rate limit
    is_allowed, retry_after = await limiter.check_rate_limit(request)
    
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please wait before trying again.",
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((datetime.now() + timedelta(seconds=retry_after)).timestamp()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = limiter.requests_per_minute - len(limiter.requests[limiter._get_client_key(request)])
    response.headers["X-RateLimit-Limit"] = str(limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
    
    return response