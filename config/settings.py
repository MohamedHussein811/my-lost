from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    mongodb_url: str = os.environ.get("MONGODB_URL", "")
    database_name: str = os.environ.get("DATABASE_NAME", "")
    collection_name: str = "lost_items"
    rate_limit_collection: str = "user_rate_limits"
    cache_ttl: int = 300  # 5 minutes
    max_posts_per_day: int = 2
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate required settings
        if not self.mongodb_url:
            raise ValueError("MONGODB_URL environment variable is required")
        if not self.database_name:
            raise ValueError("DATABASE_NAME environment variable is required")
    
    class Config:
        env_file = ".env"

settings = Settings()