"""
Database configuration for SQLModel with AsyncSession.
Production-ready configuration using Neon PostgreSQL.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel, select
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL_NEON")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set. Please configure it in .env")

# Convert PostgreSQL URL to async PostgreSQL URL
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Strip sslmode from URL (asyncpg handles SSL differently via connect_args)
parsed = urlparse(ASYNC_DATABASE_URL)
query_params = parse_qs(parsed.query)
query_params.pop("sslmode", None)  # Remove sslmode if present

# Rebuild URL without sslmode
new_query = urlencode(query_params, doseq=True) if query_params else ""
ASYNC_DATABASE_URL = urlunparse((
    parsed.scheme,
    parsed.netloc,
    parsed.path,
    parsed.params,
    new_query,
    parsed.fragment
))

logger.info(f"Connecting to database: {ASYNC_DATABASE_URL[:50]}...")

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    future=True,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    connect_args={
        "timeout": 30,
        "command_timeout": 30,
        "ssl": True,  # asyncpg uses ssl parameter instead of sslmode
    }
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncSession:
    """
    Dependency for FastAPI to get async database session.
    Usage in endpoints:
        @app.post("/path")
        async def endpoint(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session() as session:
        yield session


async def init_db():
    """
    Initialize database tables.
    Call this once on application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")


# Database health check
async def check_db_connection():
    """Check if database is accessible."""
    try:
        async with async_session() as session:
            await session.execute(select(1))
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False
