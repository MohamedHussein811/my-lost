from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, GEOSPHERE, TEXT
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        mongodb.client = AsyncIOMotorClient(settings.mongodb_url)
        mongodb.database = mongodb.client[settings.database_name]
        
        # Test connection
        await mongodb.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB")

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
