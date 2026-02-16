"""
Main FastAPI application for meal planning system.
Entry point for running the server and validating Neon database connection.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from api_endpoints import setup_meal_planning_routes
from config import init_db, close_db, check_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage FastAPI application lifespan.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting Meal Planning API...")
    
    # Check environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("⚠️  DATABASE_URL not set - running without database")
    else:
        logger.info(f"✓ Database URL configured (pooler: {db_url[:30]}...)")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✓ Database tables initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
    
    # Check connection
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("✓ Neon PostgreSQL connection validated")
    else:
        logger.warning("⚠️  Database connection check failed - check DATABASE_URL")
    
    logger.info("✅ Meal Planning API ready to accept requests")
    
    # Yield control back to FastAPI for request handling
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Meal Planning API...")
    try:
        await close_db()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"✗ Shutdown error: {e}")
    
    logger.info("✅ Meal Planning API shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Meal Planning System API",
    description="AI-powered meal planning and shopping integration for QuickMarket",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register meal planning routes
setup_meal_planning_routes(app)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "Meal Planning API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/api/v1")
async def api_root():
    """API v1 root endpoint."""
    return {
        "version": "1.0.0",
        "endpoints": {
            "meal_planning": "/api/v1/meal-planning",
            "docs": "/docs"
        }
    }


# if __name__ == "__main__":
#     # Run development server
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=10000,
#         reload=True,
#         log_level="info"
#     )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="info"
    )

# uvicorn main:app --reload
