from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class FinderInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)

class LostItemCreate(BaseModel):
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    image_url: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., min_length=1, max_length=50)
    found_at_address: str = Field(..., min_length=5, max_length=200)
    finder_info: FinderInfo

class LostItemResponse(BaseModel):
    id: str = Field(alias="_id")
    longitude: float
    latitude: float
    image_url: str
    description: str
    notes: Optional[str]
    category: str
    found_at_address: str
    finder_info: FinderInfo
    created_at: datetime
    
    class Config:
        populate_by_name = True

class LostItemFilters(BaseModel):
    category: Optional[str] = None
    region_bounds: Optional[dict] = None  # {"min_lat": float, "max_lat": float, "min_lng": float, "max_lng": float}
    search_text: Optional[str] = None
    limit: int = Field(default=50, le=100)
    skip: int = Field(default=0, ge=0)
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        return v.lower().strip() if v else v