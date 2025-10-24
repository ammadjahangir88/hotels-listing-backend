from fastapi import Body, FastAPI, Response, status, HTTPException, Depends

app = FastAPI()
from .routers import property
from .import models
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, SessionLocal, get_db


from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as redis
# ✅ Allow CORS
origins = [
    "http://localhost:5173",  # React frontend
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],           
)
app.include_router(property.router)
models.Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup():
    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")