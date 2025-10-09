from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session

DATABASE_URL = "postgresql://ammadjahangir:090078601@localhost/hotel-listing"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ✅ Dependency for FastAPI routes
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()