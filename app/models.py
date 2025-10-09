from sqlalchemy import Column, Integer, String, Boolean,ForeignKey, Float,Date
from .database import Base
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text



class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    house_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    max_persons = Column(Integer, nullable=False)
    pets_allowed = Column(Boolean, default=False)
    price_per_night = Column(Float, nullable=False)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Integer, nullable=False)
    amenities = Column(ARRAY(String))  # PostgreSQL array of strings
    images = Column(ARRAY(String))
    source = Column(String, nullable=False)  # e.g., "Interhome" or "Ares"
    availabilities = relationship("Availability", back_populates="property", cascade="all, delete-orphan")



class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"))
    start_date = Column(Date)
    end_date = Column(Date)
    price = Column(Float)

    property = relationship("Property", back_populates="availabilities")