# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from database.mongodb import connect_to_mongo, close_mongo_connection, is_connected
from api.routes import lost_items

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - simplified for serverless"""
    # Startup
    logger.info("Starting My Lost API...")
    
    # Don't try to connect here in serverless - connect on-demand instead
    logger.info("My Lost API started (serverless mode)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down My Lost API...")
    try:
        await close_mongo_connection()
        logger.info("My Lost API shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="My Lost API",
    description="API for reporting and finding lost items",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lost_items.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to My Lost API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with better error handling"""
    try:
        from database.mongodb import get_database
        from config.settings import settings
        
        # Check environment variables
        mongodb_url_configured = bool(os.environ.get("MONGODB_URL"))
        database_name_configured = bool(os.environ.get("DATABASE_NAME"))
        
        result = {
            "status": "healthy",
            "mongodb_url_configured": mongodb_url_configured,
            "database_name_configured": database_name_configured,
            "mongodb_url_length": len(os.environ.get("MONGODB_URL", "")),
            "database_name": os.environ.get("DATABASE_NAME", "NOT_SET"),
            "environment": os.environ.get("VERCEL_ENV", "local")
        }
        
        # Test database connection
        try:
            db = await get_database()
            if db is None:
                result["database"] = "disconnected"
                result["connection_error"] = "get_database returned None"
            else:
                await db.command('ping')
                result["database"] = "connected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            result["database"] = "disconnected"
            result["connection_error"] = str(e)[:200]  # Truncate long error messages
        
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )