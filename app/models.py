from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Date, Text
from .database import Base
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import relationship


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    house_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

    # Location details
    region = Column(String, nullable=True)  # region name
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Type & Classification
    type = Column(String, nullable=True)  # e.g., "H"
    detail_type = Column(String, nullable=True)  # e.g., "V"
    type_name = Column(String, nullable=True)  # e.g., "House"
    detail_type_name = Column(String, nullable=True)  # e.g., "Villa"

    # Capacity and structure
    max_persons = Column(Integer, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    toilets = Column(Integer, nullable=True)
    pets_allowed = Column(Boolean, default=False)

    # Attributes / Amenities / Features
    amenities = Column(ARRAY(String), nullable=True)  # e.g., ['wifi', 'parking', 'sauna']
    attributes = Column(JSON, nullable=True)          # store raw attribute list if needed
    images = Column(ARRAY(String), nullable=True)     # image URLs

    # Ratings (Evaluation)
    stars = Column(Float, nullable=True)
    location_rating = Column(Float, nullable=True)
    outdoor_area_rating = Column(Float, nullable=True)
    interior_rating = Column(Float, nullable=True)
    tranquility_rating = Column(Float, nullable=True)
    kitchen_rating = Column(Float, nullable=True)
    access_road_rating = Column(Float, nullable=True)

    # Descriptions
    inside_description = Column(Text, nullable=True)
    outside_description = Column(Text, nullable=True)

    # Miscellaneous metadata
    brand = Column(String, nullable=True)
    domestic_currency = Column(String, nullable=True)
    source = Column(String, nullable=False, default="Interhome")

    # Relationship with Availability
    availabilities = relationship("Availability", back_populates="property", cascade="all, delete-orphan")


class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"))
    start_date = Column(Date)
    end_date = Column(Date)
    price = Column(Float)
    duration=Column(Integer)

    property = relationship("Property", back_populates="availabilities")