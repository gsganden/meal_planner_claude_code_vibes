from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.db.database import init_db, close_db
from src.middleware.rate_limit import rate_limit_middleware, auth_limiter, api_limiter, websocket_limiter
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip database initialization in test environment
    # Tests will handle their own database setup
    import os
    if os.environ.get("TESTING") != "true":
        # Startup
        logger.info("Starting up Recipe Chat Assistant...")
        await init_db()
        
        # Start rate limiter cleanup tasks
        await auth_limiter.start_cleanup()
        await api_limiter.start_cleanup()
        await websocket_limiter.start_cleanup()
    
    yield
    
    if os.environ.get("TESTING") != "true":
        # Shutdown
        logger.info("Shutting down Recipe Chat Assistant...")
        
        # Stop rate limiter cleanup tasks
        await auth_limiter.stop_cleanup()
        await api_limiter.stop_cleanup()
        await websocket_limiter.stop_cleanup()
        
        await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
@app.middleware("http")
async def add_rate_limiting(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.3f}s"
    )
    
    # Add process time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependency status"""
    from src.db.database import engine
    from src.llm.client import get_llm_client
    
    health_status = {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "checks": {}
    }
    
    # Check database
    try:
        if engine:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            health_status["checks"]["database"] = {"status": "healthy"}
        else:
            health_status["checks"]["database"] = {"status": "unhealthy", "error": "No engine"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check LLM client configuration
    try:
        client = get_llm_client()
        if client and settings.google_api_key:
            health_status["checks"]["llm"] = {"status": "healthy", "model": "gemini-2.5-flash"}
        else:
            health_status["checks"]["llm"] = {"status": "unhealthy", "error": "Missing configuration"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["llm"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check rate limiters
    health_status["checks"]["rate_limiting"] = {
        "status": "healthy",
        "limits": {
            "auth": f"{auth_limiter.requests_per_minute}/min",
            "api": f"{api_limiter.requests_per_minute}/min",
            "websocket": f"{websocket_limiter.requests_per_minute}/min"
        }
    }
    
    return health_status


# Register routers
from src.api import auth, recipes, chat
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(recipes.router, prefix="/v1/recipes", tags=["recipes"])
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])