# app/schemas/property.py
from pydantic import BaseModel
from typing import List, Optional

class Property(BaseModel):
    house_code: str
    name: str
    location: Optional[str]
    city: str
    country: str
    max_persons: int
    pets_allowed: bool
    price_per_night: float
    bedrooms: int
    bathrooms: int
    amenities: List[str]
    images: List[str]
    source: str  # "Interhome" or "Ares"
    availability: Optional[List[str]] = None  # e.g., ["2025-06-01", "2025-06-10"]
