from cachetools import TTLCache
from typing import Optional, List, Any
import json
import hashlib
from config.settings import settings

class CacheService:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl)
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        """Get cached data"""
        key = self._generate_key(prefix, **kwargs)
        print(f"Cache key: {key}")
        return self.cache.get(key)
    
    def set(self, prefix: str, value: Any, **kwargs) -> None:
        """Set cached data"""
        key = self._generate_key(prefix, **kwargs)
        self.cache[key] = value
    
    def invalidate_pattern(self, prefix: str) -> None:
        """Invalidate cache entries with specific prefix"""
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(prefix)]
        for key in keys_to_remove:
            del self.cache[key]

cache_service = CacheService()