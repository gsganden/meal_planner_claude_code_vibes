"""
Shared test fixtures and configuration
"""
import pytest
import pytest_asyncio
import os
import tempfile
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.db.database import Base, get_db
from src.main import app
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator:
    """Set up test environment variables"""
    # Store original env vars
    original_env = {}
    test_vars = {
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "GOOGLE_API_KEY": "test-google-api-key",
        "GOOGLE_OPENAI_BASE_URL": "https://test.googleapis.com/v1beta/openai/",
        "DEBUG": "false",
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
        "TESTING": "true"  # Flag to disable rate limiting in tests
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest_asyncio.fixture
async def test_db_session():
    """Create a test database session with proper isolation"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Set test database URL
    database_url = f"sqlite+aiosqlite:///{db_path}"
    
    # Create engine for this test
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=None  # Disable connection pooling for tests
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session for testing
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


@pytest_asyncio.fixture
async def test_client():
    """Create test client with isolated database"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Set test database URL
    database_url = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    
    # Create engine for this test
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=None  # Disable connection pooling for tests
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Override the get_db dependency
    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()
    await engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


@pytest_asyncio.fixture
async def authenticated_client(test_client: AsyncClient):
    """Create authenticated test client"""
    # Create a test user and get token
    import time
    unique_email = f"test_{int(time.time() * 1000000)}@example.com"
    
    signup_response = await test_client.post("/v1/auth/signup", json={
        "email": unique_email,
        "password": "TestPass123",
        "confirmPassword": "TestPass123"
    })
    
    if signup_response.status_code != 201:
        raise Exception(f"Signup failed: {signup_response.json()}")
    
    token = signup_response.json()["access_token"]
    test_client.headers["Authorization"] = f"Bearer {token}"
    
    yield test_client


@pytest.fixture
def sample_recipe_data():
    """Sample recipe data for testing"""
    return {
        "title": "Test Recipe",
        "yield": "4 servings",
        "description": "A test recipe for unit tests",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "ingredients": [
            {"text": "2 cups flour", "quantity": 2, "unit": "cup"},
            {"text": "1 tsp salt", "quantity": 1, "unit": "tsp"},
            {"text": "3 eggs", "quantity": 3, "unit": ""}
        ],
        "steps": [
            {"order": 1, "text": "Mix dry ingredients"},
            {"order": 2, "text": "Add wet ingredients"},
            {"order": 3, "text": "Bake at 350°F"}
        ],
        "tags": ["baking", "easy"]
    }


@pytest.fixture
def auth_headers():
    """Generate auth headers for testing"""
    def _auth_headers(token: str):
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers