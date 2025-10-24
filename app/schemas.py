from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import date


class AvailabilityBase(BaseModel):
    start_date: date
    end_date: date
    price: float
    duration:int

    class Config:
        orm_mode = True


class PropertyBase(BaseModel):
    house_code: str
    name: str
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[str] = None
    detail_type: Optional[str] = None
    type_name: Optional[str] = None
    detail_type_name: Optional[str] = None
    max_persons: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    toilets: Optional[int] = None
    pets_allowed: Optional[bool] = False
    amenities: Optional[List[str]] = None
    attributes: Optional[Any] = None  # JSON data
    images: Optional[List[str]] = None

    # Ratings
    stars: Optional[float] = None
    location_rating: Optional[float] = None
    outdoor_area_rating: Optional[float] = None
    interior_rating: Optional[float] = None
    tranquility_rating: Optional[float] = None
    kitchen_rating: Optional[float] = None
    access_road_rating: Optional[float] = None

    # Descriptions
    inside_description: Optional[str] = None
    outside_description: Optional[str] = None

    # Metadata
    brand: Optional[str] = None
    domestic_currency: Optional[str] = None
    source: Optional[str] = "Interhome"

    class Config:
        orm_mode = True


class PropertyResponse(PropertyBase):
    id: int
    availabilities: Optional[List[AvailabilityBase]] = None

    class Config:
        orm_mode = True
