from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine and session factory
engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection and create tables"""
    global engine, async_session_maker
    
    # Close existing connections if any
    if engine:
        await engine.dispose()
    
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")


async def close_db():
    """Close database connection"""
    global engine, async_session_maker
    if engine:
        await engine.dispose()
        engine = None
        async_session_maker = None
        logger.info("Database connection closed")


async def get_db():
    """Dependency to get database session"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()