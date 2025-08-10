# database/mongodb.py
from pymongo import AsyncMongoClient
from pymongo import IndexModel, GEOSPHERE, TEXT
import logging
import asyncio
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global async client - modern PyMongo Async API (replaces Motor)
_async_client: Optional[AsyncMongoClient] = None
_database = None
_connection_lock = asyncio.Lock()

def get_async_client():
    """Get or create PyMongo Async client (singleton pattern)"""
    global _async_client
    
    if _async_client is None:
        mongodb_url = os.getenv("MONGODB_URL")
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is required")
        
        # Create async client with PyMongo Async API (replaces Motor)
        _async_client = AsyncMongoClient(
            mongodb_url,
            # Connection timeouts optimized for serverless
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            
            # Connection pool settings
            maxPoolSize=5,
            minPoolSize=0,
            maxIdleTimeMS=30000,
            
            # Reliability
            retryWrites=True,
            retryReads=True,
        )
        
        logger.info("PyMongo Async client created")
    
    return _async_client

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
        
        client = get_async_client()
        _database = client[database_name]
        
        # Test connection
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
    global _async_client, _database
    
    if _async_client:
        await _async_client.close()
        _async_client = None
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
        
        # Create indexes with individual error handling
        try:
            await collection.create_index([("location", GEOSPHERE)])
            logger.info("Created geosphere index")
        except Exception as e:
            logger.warning(f"Failed to create geosphere index: {e}")
        
        try:
            await collection.create_index([
                ("description", TEXT),
                ("notes", TEXT),
                ("found_at_address", TEXT)
            ])
            logger.info("Created text search index")
        except Exception as e:
            logger.warning(f"Failed to create text index: {e}")
        
        try:
            await collection.create_index("category")
            await collection.create_index("created_at")
            logger.info("Created basic indexes")
        except Exception as e:
            logger.warning(f"Failed to create basic indexes: {e}")
        
        # Rate limiting indexes
        try:
            await rate_limit_collection.create_index("user_id")
            await rate_limit_collection.create_index("created_at", expireAfterSeconds=86400)
            logger.info("Created rate limit indexes")
        except Exception as e:
            logger.warning(f"Failed to create rate limit indexes: {e}")
        
        logger.info("Database index creation completed")
        
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
        result = await database.command('ping')
        return result.get('ok') == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False