import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.settings import settings
from src.modules.invoices.api import invoice_router

logger = logging.getLogger("api")
logging.basicConfig(level=settings.log_level)


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

# Include routers
app.include_router(invoice_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.app_env}

