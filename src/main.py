from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.config.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    # Shutdown
    logger.info("Shutting down application")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.app_env}

# Avoid circular imports or undefined logger
import logging
logger = logging.getLogger("api")
logging.basicConfig(level=settings.log_level)
