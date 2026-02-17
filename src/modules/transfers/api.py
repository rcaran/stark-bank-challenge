"""
Transfer API Endpoints.

This module provides FastAPI endpoints for transfer operations,
protected by API key authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.modules.transfers.models import TransferStatus
from src.modules.transfers.repository import TransferRepository
from src.modules.transfers.service import TransferService
from src.shared.events.bus import EventBus
from src.shared.security.api_key import get_api_key_header
from src.shared.stark.transfer_api import StarkTransferAPI
from src.shared.utils.logger import get_logger

logger = get_logger("modules.transfers.api")

# Create FastAPI router
transfer_router = APIRouter(
    prefix="/transfers",
    tags=["transfers"],
)

# Initialize service (singleton pattern for production)
_service: TransferService | None = None


def get_transfer_service() -> TransferService:
    """Get or create transfer service instance."""
    global _service
    if _service is None:
        _service = TransferService(
            repository=TransferRepository(),
            stark_api=StarkTransferAPI(),
            event_bus=EventBus(),
        )
    return _service


# --- Pydantic Models for Request/Response ---


class TransferResponse(BaseModel):
    """Response model for transfer data."""

    id: str
    invoice_id: str
    stark_transfer_id: str | None = None
    external_id: str
    amount: float
    status: str
    created_at: str
    updated_at: str
    completed_at: str | None = None
    retry_count: int = 0
    error_message: str | None = None


class TransferListResponse(BaseModel):
    """Response model for transfer list."""

    transfers: list[TransferResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Response model for errors."""

    detail: str
    error_code: str | None = None


# --- Endpoints ---


@transfer_router.get(
    "",
    response_model=TransferListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="List Transfers",
    description="List transfers with optional filtering and pagination.",
)
async def list_transfers(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _api_key: str = Depends(get_api_key_header),
    service: TransferService = Depends(get_transfer_service),
) -> TransferListResponse:
    """
    List transfers with optional filtering.

    Supports pagination via limit and offset parameters.
    Can filter by status (pending, created, processing, success, failed).

    Requires API key authentication via X-API-Key header.
    """
    logger.debug(
        f"List transfers request: status={status_filter}, "
        f"limit={limit}, offset={offset}"
    )

    # Validate status if provided
    if status_filter:
        try:
            TransferStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status: {status_filter}. "
                    f"Valid values: {[s.value for s in TransferStatus]}"
                ),
            ) from None

    transfers = service.list_transfers(status=status_filter, limit=limit, offset=offset)
    total = service.count_transfers(status=status_filter)

    return TransferListResponse(
        transfers=[_transfer_to_response(t) for t in transfers],
        total=total,
        limit=limit,
        offset=offset,
    )


@transfer_router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Transfer not found"},
    },
    summary="Get Transfer",
    description="Get a single transfer by ID.",
)
async def get_transfer(
    transfer_id: str,
    _api_key: str = Depends(get_api_key_header),
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """
    Get a transfer by its internal ID.

    Returns the full transfer details including status and completion information.

    Requires API key authentication via X-API-Key header.
    """
    logger.debug(f"Get transfer request: {transfer_id}")

    transfer = service.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer not found: {transfer_id}",
        )

    return _transfer_to_response(transfer)


@transfer_router.get(
    "/invoice/{invoice_id}",
    response_model=TransferResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Transfer not found"},
    },
    summary="Get Transfer by Invoice",
    description="Get a transfer by its invoice ID.",
)
async def get_transfer_by_invoice(
    invoice_id: str,
    _api_key: str = Depends(get_api_key_header),
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """
    Get a transfer by its invoice ID.

    Returns the full transfer details for the given invoice.

    Requires API key authentication via X-API-Key header.
    """
    logger.debug(f"Get transfer by invoice request: {invoice_id}")

    transfer = service.get_transfer_by_invoice(invoice_id)
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer not found for invoice: {invoice_id}",
        )

    return _transfer_to_response(transfer)


# --- Helper Functions ---


def _transfer_to_response(transfer) -> TransferResponse:
    """Convert TransferModel to TransferResponse."""
    data = transfer.to_dict()
    return TransferResponse(
        id=data["id"],
        invoice_id=data["invoice_id"],
        stark_transfer_id=data.get("stark_transfer_id"),
        external_id=data["external_id"],
        amount=data["amount"],
        status=data["status"],
        created_at=data["created_at"] or "",
        updated_at=data["updated_at"] or "",
        completed_at=data.get("completed_at"),
        retry_count=data.get("retry_count", 0),
        error_message=data.get("error_message"),
    )
