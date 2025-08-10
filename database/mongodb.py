# database/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, GEOSPHERE, TEXT
from config.settings import settings
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self._is_connected = False
        # Do not bind an asyncio.Lock to a potentially different/closed loop at import time
        # Create the lock lazily per current running loop
        self._connection_lock = None
        self._lock_loop_id = None

    def _get_connection_lock(self) -> asyncio.Lock:
        """Return an asyncio.Lock bound to the current running loop.
        This avoids cross-event-loop issues like 'Event loop is closed'.
        """
        current_loop = asyncio.get_running_loop()
        if self._connection_lock is None or self._lock_loop_id != id(current_loop):
            self._connection_lock = asyncio.Lock()
            self._lock_loop_id = id(current_loop)
        return self._connection_lock

mongodb = MongoDB()

async def get_database():
    """Get database instance with automatic connection handling for serverless"""
    try:
        if not mongodb._is_connected or mongodb.database is None:
            async with mongodb._get_connection_lock():
                # Double-check after acquiring lock
                if not mongodb._is_connected or mongodb.database is None:
                    await connect_to_mongo()
        
        if mongodb.database is None:
            raise ConnectionError("Database connection failed - database is None")
        
        return mongodb.database
        
    except Exception as e:
        logger.error(f"get_database failed: {e}")
        raise ConnectionError(f"Database service temporarily unavailable: {str(e)}")

async def connect_to_mongo():
    """Create database connection with better error handling"""
    try:
        if not settings.mongodb_url:
            logger.error("MONGODB_URL environment variable is not set")
            raise ValueError("MONGODB_URL is required")
        
        if not settings.database_name:
            logger.error("DATABASE_NAME environment variable is not set")
            raise ValueError("DATABASE_NAME is required")
        
        # Log connection attempt (mask sensitive info)
        masked_url = settings.mongodb_url[:20] + "***" + settings.mongodb_url[-10:] if len(settings.mongodb_url) > 30 else "***"
        logger.info(f"Attempting to connect to MongoDB: {masked_url}")
        logger.info(f"Database name: {settings.database_name}")
        
        # Close existing connection if any
        if mongodb.client:
            mongodb.client.close()
        
        # Create new connection with serverless-friendly settings
        mongodb.client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=10000,  # Increased to 10 seconds
            connectTimeoutMS=10000,          # Increased to 10 seconds
            socketTimeoutMS=10000,           # Add socket timeout
            maxPoolSize=1,                   # Limit connection pool for serverless
            minPoolSize=0,                   # Allow pool to be empty
            maxIdleTimeMS=30000,            # Close connections after 30s idle
            retryWrites=True,
            retryReads=True
        )
        
        mongodb.database = mongodb.client[settings.database_name]
        
        # Test connection with increased timeout
        logger.info("Testing MongoDB connection...")
        ping_result = await asyncio.wait_for(
            mongodb.client.admin.command('ping'), 
            timeout=15.0
        )
        logger.info(f"MongoDB ping result: {ping_result}")
        
        if not ping_result or not ping_result.get('ok'):
            raise ConnectionError("MongoDB ping failed - server not responding properly")
        
        mongodb._is_connected = True
        logger.info("Connected to MongoDB successfully")
        
        # Test database access
        try:
            collections = await mongodb.database.list_collection_names()
            logger.info(f"Database accessible, collections: {len(collections)}")
        except Exception as e:
            logger.warning(f"Could not list collections (non-critical): {e}")
        
        # Create indexes (but don't fail if this fails)
        try:
            await create_indexes()
        except Exception as e:
            logger.warning(f"Failed to create indexes (non-critical): {e}")
        
    except asyncio.TimeoutError:
        mongodb._is_connected = False
        error_msg = "MongoDB connection timed out - check network connectivity and MongoDB Atlas IP whitelist"
        logger.error(error_msg)
        raise ConnectionError(error_msg)
    except Exception as e:
        mongodb._is_connected = False
        error_msg = f"Failed to connect to MongoDB: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        
        # Provide specific guidance for common errors
        if "authentication failed" in str(e).lower():
            error_msg += " - Check username/password in connection string"
        elif "network" in str(e).lower() or "timeout" in str(e).lower():
            error_msg += " - Check MongoDB Atlas IP whitelist (should include 0.0.0.0/0)"
        elif "ssl" in str(e).lower():
            error_msg += " - Check SSL/TLS configuration"
        
        raise ConnectionError(error_msg)

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        mongodb._is_connected = False
        mongodb.client = None
        mongodb.database = None
        logger.info("Disconnected from MongoDB")
        # Reset lock so a fresh one will be created for the next loop
        mongodb._connection_lock = None
        mongodb._lock_loop_id = None

def is_connected() -> bool:
    """Check if database is connected"""
    return mongodb._is_connected and mongodb.database is not None

async def create_indexes():
    """Create database indexes for better performance"""
    if mongodb.database is None:
        return
        
    collection = mongodb.database[settings.collection_name]
    rate_limit_collection = mongodb.database[settings.rate_limit_collection]
    
    try:
        # Create indexes with timeout
        await asyncio.wait_for(
            collection.create_index([("location", GEOSPHERE)]),
            timeout=10.0
        )
        
        await asyncio.wait_for(
            collection.create_index([
                ("description", TEXT),
                ("notes", TEXT),
                ("found_at_address", TEXT)
            ]),
            timeout=10.0
        )
        
        await asyncio.wait_for(
            collection.create_index("category"),
            timeout=10.0
        )
        
        await asyncio.wait_for(
            collection.create_index("created_at"),
            timeout=10.0
        )
        
        # Rate limiting indexes
        await asyncio.wait_for(
            rate_limit_collection.create_index("user_id"),
            timeout=10.0
        )
        
        await asyncio.wait_for(
            rate_limit_collection.create_index("created_at", expireAfterSeconds=86400),
            timeout=10.0
        )
        
        logger.info("Database indexes created successfully")
        
    except asyncio.TimeoutError:
        logger.warning("Index creation timed out (non-critical)")
    except Exception as e:
        logger.warning(f"Failed to create some indexes (non-critical): {e}")

# Dependency for FastAPI routes
async def get_db():
    """FastAPI dependency to get database connection"""
    try:
        db = await get_database()
        if db is None:
            raise ConnectionError("Database connection returned None")
        return db
    except Exception as e:
        logger.error(f"Database dependency failed: {e}")
        raise ConnectionError(f"Database service temporarily unavailable: {str(e)}")