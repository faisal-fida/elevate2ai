"""
Database configuration and session management for the application.
Uses SQLAlchemy with SQLite for data persistence.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import URL

from app.config import settings

# Create async database engine
# Uses aiosqlite for async SQLite access
engine = create_async_engine(
    URL.create(drivername="sqlite+aiosqlite", database=settings.DATABASE_PATH),
    echo=settings.SQL_ECHO,  # Log SQL queries if enabled
    future=True,
)

# Create async session factory
# - expire_on_commit=False: Keep objects usable after session is committed
# - autocommit=False: Transactions must be explicitly committed
# - autoflush=False: Changes not automatically flushed before queries
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all SQLAlchemy models
Base = declarative_base()


async def get_db():
    """
    Dependency provider for FastAPI to get database sessions.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            users = await db_operations.get_all_users(db)
            return users

    Yields:
        AsyncSession: Database session for executing queries
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Auto-commit if no exceptions
        except Exception:
            await session.rollback()  # Rollback on error
            raise
