"""
Stark Bank Challenge - Main Application.

This module implements the FastAPI application with all modules integrated,
including lifespan management, routers, middleware, and exception handlers.
"""

import sys
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from src.config.settings import settings
from src.dependencies import cleanup, initialize_event_handlers
from src.health import check_health
from src.modules.invoices.api import invoice_router
from src.modules.transfers.api import transfer_router
from src.modules.webhooks.api import webhook_router
from src.scheduler import run_scheduler, stop_scheduler
from src.shared.database.migrations import run_migrations
from src.shared.security.api_key import InvalidAPIKeyError
from src.shared.security.signature import InvalidSignatureError
from src.shared.utils.errors import StarkBankError
from src.shared.utils.logger import get_logger

logger = get_logger("api")

# Global scheduler thread reference
_scheduler_thread: Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, event bus, event handlers, and scheduler
    - Shutdown: Stop scheduler and cleanup resources
    """
    global _scheduler_thread

    # Startup
    logger.info(
        f"Starting {settings.app_name} v1.0.0",
        environment=settings.app_env,
        log_level=settings.log_level
    )

    try:
        # 1. Run database migrations
        logger.info("Running database migrations")
        run_migrations()
        logger.info("Database migrations completed")

        # 2. Initialize EventBus and register event handlers
        logger.info("Initializing EventBus and event handlers")
        initialize_event_handlers()
        logger.info("EventBus and event handlers initialized")

        # 3. Start scheduler in background thread (if enabled)
        if settings.app_env != "test":
            logger.info("Starting invoice generation scheduler")
            _scheduler_thread = Thread(
                target=run_scheduler,
                daemon=True,
                name="SchedulerThread"
            )
            _scheduler_thread.start()
            logger.info("Scheduler started in background thread")
        else:
            logger.info("Scheduler disabled in test environment")

        logger.info(f"{settings.app_name} started successfully")

    except Exception as e:
        logger.error(f"Failed to start application: {e!s}", exc_info=True)
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down application")

    try:
        # 1. Stop scheduler
        if _scheduler_thread and _scheduler_thread.is_alive():
            logger.info("Stopping scheduler")
            stop_scheduler()
            _scheduler_thread.join(timeout=5)
            logger.info("Scheduler stopped")

        # 2. Cleanup resources
        logger.info("Cleaning up resources")
        cleanup()
        logger.info("Resources cleaned up")

    except Exception as e:
        logger.error(f"Error during shutdown: {e!s}", exc_info=True)

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Automated invoice generation and transfer system using Stark Bank API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers

@app.exception_handler(InvalidAPIKeyError)
async def invalid_api_key_handler(request: Request, exc: InvalidAPIKeyError):
    """Handle invalid API key errors."""
    logger.warning(
        "Invalid API key attempt",
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "message": "Invalid API key"
        }
    )


@app.exception_handler(InvalidSignatureError)
async def invalid_signature_handler(request: Request, exc: InvalidSignatureError):
    """Handle invalid webhook signature errors."""
    logger.warning(
        "Invalid webhook signature",
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "message": "Invalid signature"
        }
    )


@app.exception_handler(StarkBankError)
async def stark_bank_api_error_handler(request: Request, exc: StarkBankError):
    """Handle Stark Bank API errors."""
    logger.error(
        "Stark Bank API error",
        path=request.url.path,
        error=str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "External API Error",
            "message": "Error communicating with Stark Bank API"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(
        "Request validation error",
        path=request.url.path,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "message": str(exc.detail)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other unexpected exceptions."""
    logger.error(
        "Unexpected error",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


# Middleware

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(
        f"{request.method} {request.url.path}",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )

    response = await call_next(request)

    logger.info(
        f"Response {response.status_code}",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code
    )

    return response


# Include routers (routers already define their own prefix)
app.include_router(invoice_router)
app.include_router(transfer_router)
app.include_router(webhook_router)


# Root endpoints

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns the health status of all system components including:
    - Database connectivity
    - EventBus status
    - Application uptime
    - Environment information

    Returns:
        Dict with health status and component checks
    """
    return check_health(include_stark=False)

