# database/mongodb.py
from pymongo import AsyncMongoClient
from pymongo import IndexModel, GEOSPHERE, TEXT
import logging
import asyncio
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Connection configuration
_connection_config = None

def get_connection_config():
    """Get MongoDB connection configuration"""
    global _connection_config
    
    if _connection_config is None:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is required")
        if not database_name:
            raise ValueError("DATABASE_NAME environment variable is required")
        
        _connection_config = {
            "url": mongodb_url,
            "database_name": database_name,
            "options": {
                # Connection timeouts optimized for serverless
                "serverSelectionTimeoutMS": 5000,
                "connectTimeoutMS": 5000,
                "socketTimeoutMS": 5000,
                
                # Connection pool settings
                "maxPoolSize": 5,
                "minPoolSize": 0,
                "maxIdleTimeMS": 30000,
                
                # Reliability
                "retryWrites": True,
                "retryReads": True,
            }
        }
        
        logger.info("MongoDB connection configuration loaded")
    
    return _connection_config

async def get_database():
    """Get database instance - creates new client per event loop"""
    try:
        config = get_connection_config()
        
        # Create a new client for this event loop
        client = AsyncMongoClient(config["url"], **config["options"])
        database = client[config["database_name"]]
        
        # Test connection
        await database.command('ping')
        
        return database, client  # Return both so we can close the client later
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise ConnectionError(f"Database connection failed: {str(e)}")

async def close_mongo_connection():
    """Close database connection - no-op since we create per-request clients"""
    logger.info("MongoDB connection cleanup (per-request clients)")

async def create_indexes():
    """Create database indexes"""
    try:
        database, client = await get_database()
        
        try:
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
            
        finally:
            # Always close the client
            await client.close()
        
    except Exception as e:
        logger.warning(f"Index creation failed (non-critical): {e}")

# Context manager for database operations
class DatabaseManager:
    def __init__(self):
        self.database = None
        self.client = None
    
    async def __aenter__(self):
        self.database, self.client = await get_database()
        return self.database
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()

# FastAPI dependency
async def get_db():
    """FastAPI dependency to get database connection"""
    database, client = await get_database()
    try:
        yield database
    finally:
        await client.close()

# Health check function
async def check_connection():
    """Check if database is accessible"""
    try:
        database, client = await get_database()
        try:
            result = await database.command('ping')
            return result.get('ok') == 1
        finally:
            await client.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False