# database/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, GEOSPHERE, TEXT
import logging
import asyncio
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global variables for simple connection management
client: Optional[AsyncIOMotorClient] = None
database = None

async def connect_to_mongo():
    """Create database connection"""
    global client, database
    
    try:
        # Get connection details from environment
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is required")
        if not database_name:
            raise ValueError("DATABASE_NAME environment variable is required")
        
        logger.info("Connecting to MongoDB...")
        
        # Create new connection
        client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            maxPoolSize=10,
            retryWrites=True
        )
        
        database = client[database_name]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create basic indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def get_database():
    """Get database instance"""
    global client, database
    
    if database is None:
        await connect_to_mongo()
    
    if database is None:
        raise ConnectionError("Database connection failed")
    
    return database

async def close_mongo_connection():
    """Close database connection"""
    global client, database
    
    if client:
        client.close()
        client = None
        database = None
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes"""
    global database
    
    if database is None:
        return
    
    try:
        collection_name = os.getenv("COLLECTION_NAME", "items")
        rate_limit_collection_name = os.getenv("RATE_LIMIT_COLLECTION", "rate_limits")
        
        collection = database[collection_name]
        rate_limit_collection = database[rate_limit_collection_name]
        
        # Create basic indexes
        await collection.create_index([("location", GEOSPHERE)])
        await collection.create_index([
            ("description", TEXT),
            ("notes", TEXT),
            ("found_at_address", TEXT)
        ])
        await collection.create_index("category")
        await collection.create_index("created_at")
        
        # Rate limiting indexes
        await rate_limit_collection.create_index("user_id")
        await rate_limit_collection.create_index("created_at", expireAfterSeconds=86400)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")

# FastAPI dependency
async def get_db():
    """FastAPI dependency to get database connection"""
    return await get_database()