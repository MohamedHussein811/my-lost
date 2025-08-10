from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    mongodb_url: str = os.environ["MONGODB_URL"]
    database_name: str = os.environ["DATABASE_NAME"]
    collection_name: str = "lost_items"
    rate_limit_collection: str = "user_rate_limits"
    cache_ttl: int = 300  # 5 minutes
    max_posts_per_day: int = 2
    
    class Config:
        env_file = ".env"

settings = Settings()