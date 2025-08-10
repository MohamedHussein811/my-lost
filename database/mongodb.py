from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, GEOSPHERE, TEXT
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None
    _is_connected = False

mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        if not settings.mongodb_url:
            logger.error("MONGODB_URL environment variable is not set")
            raise ValueError("MONGODB_URL is required")
        
        if not settings.database_name:
            logger.error("DATABASE_NAME environment variable is not set")
            raise ValueError("DATABASE_NAME is required")
        
        logger.info(f"Attempting to connect to MongoDB...")
        logger.info(f"Database name: {settings.database_name}")
        logger.info(f"MongoDB URL (masked): {settings.mongodb_url[:20]}...")
        
        mongodb.client = AsyncIOMotorClient(settings.mongodb_url)
        mongodb.database = mongodb.client[settings.database_name]
        
        # Test connection with timeout
        logger.info("Testing MongoDB connection...")
        await mongodb.client.admin.command('ping')
        mongodb._is_connected = True
        logger.info("Connected to MongoDB successfully")
        
        # Create indexes
        logger.info("Creating database indexes...")
        await create_indexes()
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        mongodb._is_connected = False
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        # Log more details for common MongoDB connection issues
        if "authentication" in str(e).lower():
            logger.error("This appears to be an authentication issue. Check your MongoDB username/password.")
        elif "timeout" in str(e).lower():
            logger.error("This appears to be a network timeout. Check your MongoDB URL and network connectivity.")
        elif "dns" in str(e).lower():
            logger.error("This appears to be a DNS resolution issue. Check your MongoDB URL format.")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        mongodb._is_connected = False
        logger.info("Disconnected from MongoDB")

def is_connected() -> bool:
    """Check if database is connected"""
    return mongodb._is_connected and mongodb.database is not None

def get_database():
    """Get database instance with connection check"""
    if not is_connected():
        raise ConnectionError("Database is not connected. Please ensure MongoDB connection is established.")
    return mongodb.database

async def create_indexes():
    """Create database indexes for better performance"""
    collection = mongodb.database[settings.collection_name]
    rate_limit_collection = mongodb.database[settings.rate_limit_collection]
    
    # Geospatial index for location queries
    await collection.create_index([("location", GEOSPHERE)])
    
    # Text index for search functionality
    await collection.create_index([
        ("description", TEXT),
        ("notes", TEXT),
        ("found_at_address", TEXT)
    ])
    
    # Category index
    await collection.create_index("category")
    
    # Created at index for sorting
    await collection.create_index("created_at")
    
    # Rate limiting indexes
    await rate_limit_collection.create_index("user_id")
    await rate_limit_collection.create_index("created_at", expireAfterSeconds=86400)  # 24 hours TTL
