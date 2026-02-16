"""
Webhook API Endpoints.

This module provides FastAPI endpoints for receiving webhooks from Stark Bank.
These endpoints are publicly accessible but require valid signatures.
"""

from typing import Dict

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from src.modules.invoices.repository import InvoiceRepository
from src.modules.webhooks.invoice_processor import InvoiceWebhookProcessor
from src.modules.webhooks.receiver import WebhookReceiver
from src.modules.webhooks.transfer_processor import TransferWebhookProcessor
from src.modules.webhooks.validator import WebhookValidator
from src.shared.database.connection import get_db_connection
from src.shared.events.bus import EventBus
from src.shared.security.signature import InvalidSignatureError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.webhooks.api")

# Create router
webhook_router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


def _get_webhook_receiver() -> WebhookReceiver:
    """
    Dependency factory for WebhookReceiver.

    Creates and returns a fully configured WebhookReceiver instance
    with all necessary dependencies.

    Returns:
        Configured WebhookReceiver instance
    """
    validator = WebhookValidator()
    event_bus = EventBus()

    # Initialize invoice processor
    invoice_repository = InvoiceRepository(get_db_connection())
    invoice_processor = InvoiceWebhookProcessor(
        invoice_repository=invoice_repository,
        event_bus=event_bus,
    )

    # Initialize transfer processor
    # Note: Transfer repository will be implemented in Phase 6
    # For now, we use a mock/placeholder
    try:
        from src.modules.transfers.repository import TransferRepository

        transfer_repository = TransferRepository(get_db_connection())
    except ImportError:
        # Transfer module not yet implemented - use placeholder
        transfer_repository = None

    transfer_processor = TransferWebhookProcessor(
        transfer_repository=transfer_repository,
        event_bus=event_bus,
    )

    return WebhookReceiver(
        validator=validator,
        invoice_processor=invoice_processor,
        transfer_processor=transfer_processor,
        event_bus=event_bus,
    )


@webhook_router.post(
    "/invoice",
    summary="Receive invoice webhook",
    description="Receives and processes invoice webhooks from Stark Bank. "
    "Validates signature and updates invoice status.",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Webhook processed successfully",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        },
        401: {
            "description": "Invalid signature",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid webhook signature"}
                }
            },
        },
    },
)
async def receive_invoice_webhook(
    request: Request,
    digital_signature: str = Header(..., alias="Digital-Signature"),
) -> JSONResponse:
    """
    Receive and process an invoice webhook from Stark Bank.

    This endpoint:
    1. Reads the raw request body
    2. Validates the Digital-Signature header
    3. Processes the webhook payload
    4. Always returns 200 OK (except for invalid signatures)

    Args:
        request: FastAPI request object
        digital_signature: Digital signature from Stark Bank (header)

    Returns:
        JSONResponse with status

    Note:
        This endpoint always returns 200 OK for valid signatures, even if
        processing fails internally. This prevents Stark Bank from retrying
        webhooks for application errors that won't be resolved by retrying.
    """
    logger.info(
        "Invoice webhook received",
        has_signature=bool(digital_signature),
    )

    try:
        # Read raw body
        body = await request.body()

        logger.debug(
            "Invoice webhook body received",
            body_size=len(body),
        )

        # Process webhook
        receiver = _get_webhook_receiver()
        result = receiver.receive_invoice_webhook(
            payload=body,
            signature=digital_signature,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )

    except InvalidSignatureError as e:
        logger.warning(
            "Invoice webhook rejected - invalid signature",
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid webhook signature"},
        )

    except Exception as e:
        logger.error(
            "Unexpected error processing invoice webhook",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Return 200 anyway to prevent retries
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "error": "internal_error"},
        )


@webhook_router.post(
    "/transfer",
    summary="Receive transfer webhook",
    description="Receives and processes transfer webhooks from Stark Bank. "
    "Validates signature and updates transfer status.",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Webhook processed successfully",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        },
        401: {
            "description": "Invalid signature",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid webhook signature"}
                }
            },
        },
    },
)
async def receive_transfer_webhook(
    request: Request,
    digital_signature: str = Header(..., alias="Digital-Signature"),
) -> JSONResponse:
    """
    Receive and process a transfer webhook from Stark Bank.

    This endpoint:
    1. Reads the raw request body
    2. Validates the Digital-Signature header
    3. Processes the webhook payload
    4. Always returns 200 OK (except for invalid signatures)

    Args:
        request: FastAPI request object
        digital_signature: Digital signature from Stark Bank (header)

    Returns:
        JSONResponse with status

    Note:
        This endpoint always returns 200 OK for valid signatures, even if
        processing fails internally. This prevents Stark Bank from retrying
        webhooks for application errors that won't be resolved by retrying.
    """
    logger.info(
        "Transfer webhook received",
        has_signature=bool(digital_signature),
    )

    try:
        # Read raw body
        body = await request.body()

        logger.debug(
            "Transfer webhook body received",
            body_size=len(body),
        )

        # Process webhook
        receiver = _get_webhook_receiver()
        result = receiver.receive_transfer_webhook(
            payload=body,
            signature=digital_signature,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )

    except InvalidSignatureError as e:
        logger.warning(
            "Transfer webhook rejected - invalid signature",
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid webhook signature"},
        )

    except Exception as e:
        logger.error(
            "Unexpected error processing transfer webhook",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Return 200 anyway to prevent retries
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "error": "internal_error"},
        )


@webhook_router.get(
    "/health",
    summary="Webhook service health check",
    description="Simple health check endpoint to verify webhook service is running.",
    response_model=Dict[str, str],
)
async def webhook_health() -> Dict[str, str]:
    """
    Health check endpoint for webhook service.

    Returns:
        Dictionary with status
    """
    return {"status": "healthy", "service": "webhooks"}
