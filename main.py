from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from database.mongodb import connect_to_mongo, close_mongo_connection
from api.routes import lost_items

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting My Lost API...")
    await connect_to_mongo()
    logger.info("My Lost API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down My Lost API...")
    await close_mongo_connection()
    logger.info("My Lost API shut down successfully")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
