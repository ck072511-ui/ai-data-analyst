"""
Production Database Configuration with Connection Pooling and Monitoring
"""

import logging

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Convert postgresql:// to postgresql+asyncpg:// for async, and sqlite:// to sqlite+aiosqlite://
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("sqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=3600,  # Recycle connections every hour
    echo=settings.DATABASE_ECHO,
    echo_pool=True,
    # SSL configuration for production
    connect_args=(
        {"ssl": {"mode": "require" if settings.ENVIRONMENT == "production" else "disable"}}
        if settings.ENVIRONMENT == "production" and not DATABASE_URL.startswith("sqlite")
        else {}
    ),
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

# Base class for models
Base = declarative_base()


# Connection event listeners for monitoring
@event.listens_for(engine.sync_engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("Database connection established")


@event.listens_for(engine.sync_engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")


@event.listens_for(engine.sync_engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection checked in to pool")


import time


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if context:
        context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if context and hasattr(context, "_query_start_time"):
        total_time = time.time() - context._query_start_time
        try:
            from app.services.monitoring_service import monitoring_service

            monitoring_service.record_db_query(total_time)

            # Record slow queries exceeding 100ms threshold
            if total_time > 0.1:
                from app.services.performance_service import performance_service

                performance_service.record_slow_query(statement, total_time)
        except Exception:
            pass


# Health check function
async def check_db_health() -> bool:
    """Check if database is healthy"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


# Session dependency for FastAPI
async def get_session() -> AsyncSession:
    """Dependency for database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


from sqlalchemy import create_engine


def get_sync_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
    return create_engine(db_url)
