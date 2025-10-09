from fastapi import Body, FastAPI, Response, status, HTTPException, Depends

app = FastAPI()
from .routers import property
from .import models
from .database import engine, SessionLocal, get_db
app.include_router(property.router)
models.Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}