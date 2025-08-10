# database/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, GEOSPHERE, TEXT
import logging
import asyncio
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global connection - created once, reused across requests
_client: Optional[AsyncIOMotorClient] = None
_database = None
_connection_lock = asyncio.Lock()

def get_client():
    """Get or create MongoDB client (singleton pattern)"""
    global _client
    
    if _client is None:
        mongodb_url = os.getenv("MONGODB_URL")
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is required")
        
        # Create client with connection pooling optimized for serverless
        _client = AsyncIOMotorClient(
            mongodb_url,
            # Connection timeouts
            serverSelectionTimeoutMS=5000,   # Fast timeout for serverless
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            
            # Connection pool settings for serverless
            maxPoolSize=5,        # Small pool for serverless
            minPoolSize=0,        # Allow empty pool
            maxIdleTimeMS=30000,  # Close idle connections quickly
            
            # Reliability
            retryWrites=True,
            retryReads=True,
            
            # Disable monitoring for serverless (reduces overhead)
            heartbeatFrequencyMS=60000,  # Less frequent heartbeats
        )
        
        logger.info("MongoDB client created")
    
    return _client

async def get_database():
    """Get database instance with automatic connection handling"""
    global _database
    
    # If we already have a database reference, return it
    if _database is not None:
        return _database
    
    # Thread-safe database initialization
    async with _connection_lock:
        # Double-check after acquiring lock
        if _database is not None:
            return _database
        
        database_name = os.getenv("DATABASE_NAME")
        if not database_name:
            raise ValueError("DATABASE_NAME environment variable is required")
        
        client = get_client()
        _database = client[database_name]
        
        # Test connection (optional - the driver will handle this automatically)
        try:
            await _database.command('ping')
            logger.info(f"Connected to MongoDB database: {database_name}")
        except Exception as e:
            logger.warning(f"Initial ping failed (non-critical): {e}")
        
        # Create indexes in background (non-blocking)
        asyncio.create_task(create_indexes())
    
    return _database

async def close_mongo_connection():
    """Close database connection"""
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes (runs in background)"""
    try:
        database = await get_database()
        collection_name = os.getenv("COLLECTION_NAME", "items")
        rate_limit_collection_name = os.getenv("RATE_LIMIT_COLLECTION", "rate_limits")
        
        collection = database[collection_name]
        rate_limit_collection = database[rate_limit_collection_name]
        
        # Create indexes (with error handling for each)
        try:
            await collection.create_index([("location", GEOSPHERE)])
        except Exception as e:
            logger.warning(f"Failed to create geosphere index: {e}")
        
        try:
            await collection.create_index([
                ("description", TEXT),
                ("notes", TEXT),
                ("found_at_address", TEXT)
            ])
        except Exception as e:
            logger.warning(f"Failed to create text index: {e}")
        
        try:
            await collection.create_index("category")
            await collection.create_index("created_at")
        except Exception as e:
            logger.warning(f"Failed to create basic indexes: {e}")
        
        # Rate limiting indexes
        try:
            await rate_limit_collection.create_index("user_id")
            await rate_limit_collection.create_index("created_at", expireAfterSeconds=86400)
        except Exception as e:
            logger.warning(f"Failed to create rate limit indexes: {e}")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Index creation failed (non-critical): {e}")

# FastAPI dependency
async def get_db():
    """FastAPI dependency to get database connection"""
    return await get_database()

# Health check function
async def check_connection():
    """Check if database is accessible"""
    try:
        database = await get_database()
        await database.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False