from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_database, is_connected
from models.lost_item import LostItemCreate, LostItemResponse, LostItemFilters
from services.cache_service import cache_service
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class LostItemService:
    def __init__(self):
        self.collection_name = settings.collection_name
    
    async def create_lost_item(self, item: LostItemCreate) -> str:
        """Create a new lost item"""
        try:
            if not is_connected():
                raise ConnectionError("Database connection not available")
                
            database = get_database()
            collection = database[self.collection_name]
            
            # Prepare document
            document = item.model_dump()
            document["created_at"] = datetime.now()
            document["location"] = {
                "type": "Point",
                "coordinates": [item.longitude, item.latitude]
            }
            
            # Insert document
            result = await collection.insert_one(document)
            
            # Invalidate relevant cache entries
            cache_service.invalidate_pattern("lost_items")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create lost item: {e}")
            raise
    
    async def get_lost_items(self, filters: LostItemFilters) -> List[LostItemResponse]:
        """Get lost items with optional filters"""
        try:
            if not is_connected():
                raise ConnectionError("Database connection not available")
            
            # Check cache first
            cache_key_params = filters.model_dump()
            cached_result = cache_service.get("lost_items", **cache_key_params)
            if cached_result:
                return [LostItemResponse(**item) for item in cached_result]
            
            database = get_database()
            collection = database[self.collection_name]
            
            # Build query
            query = {}
            
            # Category filter
            if filters.category:
                query["category"] = filters.category
            
            # Region bounds filter (geospatial query)
            if filters.region_bounds:
                bounds = filters.region_bounds
                query["location"] = {
                    "$geoWithin": {
                        "$box": [
                            [bounds["min_lng"], bounds["min_lat"]],
                            [bounds["max_lng"], bounds["max_lat"]]
                        ]
                    }
                }
            
            # Text search
            if filters.search_text:
                query["$text"] = {"$search": filters.search_text}
            
            # Execute query with pagination
            cursor = collection.find(query).skip(filters.skip).limit(filters.limit).sort("created_at", -1)
            
            # Convert to list
            items = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                items.append(LostItemResponse(**doc))
            
            # Cache the result
            cache_service.set("lost_items", [item.model_dump() for item in items], **cache_key_params)
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get lost items: {e}")
            raise
    
    async def get_lost_item_by_id(self, item_id: str) -> Optional[LostItemResponse]:
        """Get a specific lost item by ID"""
        try:
            if not is_connected():
                raise ConnectionError("Database connection not available")
            
            # Check cache first
            cached_result = cache_service.get("lost_item", id=item_id)
            if cached_result:
                return LostItemResponse(**cached_result)
            
            database = get_database()
            collection = database[self.collection_name]
            
            # Validate ObjectId
            if not ObjectId.is_valid(item_id):
                return None
            
            # Find document
            doc = await collection.find_one({"_id": ObjectId(item_id)})
            
            if not doc:
                return None
            
            doc["_id"] = str(doc["_id"])
            item = LostItemResponse(**doc)
            
            # Cache the result
            cache_service.set("lost_item", item.model_dump(), id=item_id)
            
            return item
            
        except Exception as e:
            logger.error(f"Failed to get lost item by ID: {e}")
            raise
    
    async def get_items_near_location(self, longitude: float, latitude: float, radius_km: float = 10) -> List[LostItemResponse]:
        """Get items near a specific location"""
        try:
            if not is_connected():
                raise ConnectionError("Database connection not available")
            
            # Check cache first
            cache_key_params = {"lng": longitude, "lat": latitude, "radius": radius_km}
            cached_result = cache_service.get("nearby_items", **cache_key_params)
            if cached_result:
                return [LostItemResponse(**item) for item in cached_result]
            
            database = get_database()
            collection = database[self.collection_name]
            
            # Geospatial query for nearby items
            query = {
                "location": {
                    "$nearSphere": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [longitude, latitude]
                        },
                        "$maxDistance": radius_km * 1000  # Convert km to meters
                    }
                }
            }
            
            cursor = collection.find(query).limit(50)
            
            items = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                items.append(LostItemResponse(**doc))
            
            # Cache the result
            cache_service.set("nearby_items", [item.model_dump() for item in items], **cache_key_params)
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get nearby items: {e}")
            raise

lost_item_service = LostItemService()