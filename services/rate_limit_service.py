# services/rate_limit_service.py
from datetime import datetime, timedelta
from database.mongodb import DatabaseManager
import os
import logging

logger = logging.getLogger(__name__)

class RateLimitService:
    def __init__(self):
        self.rate_limit_collection = os.getenv("RATE_LIMIT_COLLECTION", "rate_limits")
        self.max_posts_per_day = int(os.getenv("MAX_POSTS_PER_DAY", "10"))
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded daily post limit"""
        try:
            async with DatabaseManager() as database:
                collection = database[self.rate_limit_collection]
                
                # Get today's date range
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                
                # Count posts today
                post_count = await collection.count_documents({
                    "user_id": user_id,
                    "created_at": {"$gte": today, "$lt": tomorrow}
                })
                
                return post_count < self.max_posts_per_day
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow the request to proceed if rate limiting fails
            return True
    
    async def record_post(self, user_id: str) -> None:
        """Record a post for rate limiting"""
        try:
            async with DatabaseManager() as database:
                collection = database[self.rate_limit_collection]
                
                await collection.insert_one({
                    "user_id": user_id,
                    "created_at": datetime.now()
                })
            
        except Exception as e:
            logger.error(f"Failed to record post: {e}")

rate_limit_service = RateLimitService()