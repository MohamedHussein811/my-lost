from fastapi import APIRouter, HTTPException, Header, Query, Depends
from typing import List, Optional
from models.lost_item import LostItemCreate, LostItemResponse, LostItemFilters
from services.lost_item_service import lost_item_service
from services.rate_limit_service import rate_limit_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lost-items", tags=["Lost Items"])

def get_user_identifier(
    x_device_id: Optional[str] = Header(None),
    x_mac_address: Optional[str] = Header(None),
    x_user_agent: Optional[str] = Header(None)
) -> str:
    """Extract user identifier from headers"""
    # Priority: device_id > mac_address > user_agent hash
    if x_device_id:
        return f"device_{x_device_id}"
    elif x_mac_address:
        return f"mac_{x_mac_address}"
    elif x_user_agent:
        return f"ua_{hash(x_user_agent)}"
    else:
        raise HTTPException(status_code=400, detail="User identifier required")

@router.post("/", response_model=dict, status_code=201)
async def create_lost_item(
    item: LostItemCreate,
    user_id: str = Depends(get_user_identifier)
):
    """Create a new lost item post"""
    try:
        # Check rate limit
        can_post = await rate_limit_service.check_rate_limit(user_id)
        if not can_post:
            raise HTTPException(
                status_code=429, 
                detail="Daily post limit exceeded. You can only post 2 items per day."
            )
        
        # Create the item
        item_id = await lost_item_service.create_lost_item(item)
        
        # Record the post for rate limiting
        await rate_limit_service.record_post(user_id)
        
        return {
            "message": "Lost item created successfully",
            "item_id": item_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating lost item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[LostItemResponse])
async def get_lost_items(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_lat: Optional[float] = Query(None, description="Minimum latitude for region filter"),
    max_lat: Optional[float] = Query(None, description="Maximum latitude for region filter"),
    min_lng: Optional[float] = Query(None, description="Minimum longitude for region filter"),
    max_lng: Optional[float] = Query(None, description="Maximum longitude for region filter"),
    search: Optional[str] = Query(None, description="Search text in description, notes, or address"),
    limit: int = Query(50, le=100, description="Maximum number of items to return"),
    skip: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get lost items with optional filters"""
    try:
        # Validate region bounds
        region_bounds = None
        if any([min_lat, max_lat, min_lng, max_lng]):
            if not all([min_lat, max_lat, min_lng, max_lng]):
                raise HTTPException(
                    status_code=400,
                    detail="All region bounds parameters (min_lat, max_lat, min_lng, max_lng) must be provided"
                )
            
            region_bounds = {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lng": min_lng,
                "max_lng": max_lng
            }
        
        # Create filters
        filters = LostItemFilters(
            category=category,
            region_bounds=region_bounds,
            search_text=search,
            limit=limit,
            skip=skip
        )
        
        # Get items
        items = await lost_item_service.get_lost_items(filters)
        return items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lost items: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{item_id}", response_model=LostItemResponse)
async def get_lost_item(item_id: str):
    """Get a specific lost item by ID"""
    try:
        item = await lost_item_service.get_lost_item_by_id(item_id)
        
        if not item:
            raise HTTPException(status_code=404, detail="Lost item not found")
        
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lost item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/nearby/", response_model=List[LostItemResponse])
async def get_nearby_items(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of search center"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of search center"),
    radius: float = Query(10, ge=0.1, le=100, description="Search radius in kilometers")
):
    """Get lost items near a specific location"""
    try:
        items = await lost_item_service.get_items_near_location(longitude, latitude, radius)
        return items
        
    except Exception as e:
        logger.error(f"Error getting nearby items: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")