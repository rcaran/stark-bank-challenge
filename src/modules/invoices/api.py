"""
Invoice API Endpoints.

This module provides FastAPI endpoints for invoice operations,
protected by API key authentication.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.modules.invoices.models import InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.invoices.service import InvoiceService
from src.shared.events.bus import EventBus
from src.shared.security.api_key import get_api_key_header
from src.shared.stark.invoice_api import StarkInvoiceAPI
from src.shared.utils.errors import StarkBankError, ValidationError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.invoices.api")

# Create FastAPI router
invoice_router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
)

# Initialize service (singleton pattern for production)
_service: InvoiceService | None = None


def get_invoice_service() -> InvoiceService:
    """Get or create invoice service instance."""
    global _service
    if _service is None:
        _service = InvoiceService(
            repository=InvoiceRepository(),
            stark_api=StarkInvoiceAPI(),
            event_bus=EventBus(),
        )
    return _service


# --- Pydantic Models for Request/Response ---


class CreateInvoiceRequest(BaseModel):
    """Request model for creating an invoice."""
    amount: int = Field(..., gt=0, description="Amount in cents")
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_tax_id: str = Field(..., min_length=11, max_length=18)
    customer_email: str = Field(..., min_length=5, max_length=100)
    due_date: datetime | None = Field(None, description="Due date for the invoice")


class InvoiceResponse(BaseModel):
    """Response model for invoice data."""
    id: str
    stark_invoice_id: str | None = None
    amount: float
    customer_name: str
    customer_tax_id: str
    customer_email: str
    status: str
    created_at: str
    due_date: str | None = None
    paid_at: str | None = None
    fee: float | None = None
    net_amount: float | None = None
    retry_count: int = 0
    error_message: str | None = None


class InvoiceListResponse(BaseModel):
    """Response model for invoice list."""
    invoices: list[InvoiceResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Response model for errors."""
    detail: str
    error_code: str | None = None


# --- Endpoints ---


@invoice_router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Create Invoice",
    description="Create a new invoice in Stark Bank and persist it locally.",
)
async def create_invoice(
    request: CreateInvoiceRequest,
    api_key: str = Depends(get_api_key_header),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    """
    Create a new invoice.

    This endpoint:
    1. Validates the input data
    2. Creates the invoice in Stark Bank
    3. Persists it to the local database
    4. Returns the created invoice

    Requires API key authentication via X-API-Key header.
    """
    logger.info(
        "Create invoice request received",
        amount=request.amount,
        customer_tax_id=request.customer_tax_id[:3] + "***",  # Mask for security
    )

    try:
        invoice_data = {
            "amount": request.amount,
            "customer_name": request.customer_name,
            "customer_tax_id": request.customer_tax_id,
            "customer_email": request.customer_email,
            "due_date": request.due_date,
        }

        invoice = service.create_invoice(invoice_data)
        return _invoice_to_response(invoice)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except StarkBankError as e:
        logger.error(f"Stark Bank error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invoice: {e}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@invoice_router.get(
    "",
    response_model=InvoiceListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="List Invoices",
    description="List invoices with optional filtering and pagination.",
)
async def list_invoices(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    api_key: str = Depends(get_api_key_header),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceListResponse:
    """
    List invoices with optional filtering.

    Supports pagination via limit and offset parameters.
    Can filter by status (pending, created, paid, failed, etc.).

    Requires API key authentication via X-API-Key header.
    """
    logger.debug(
        f"List invoices request: status={status_filter}, "
        f"limit={limit}, offset={offset}"
    )

    # Validate status if provided
    if status_filter:
        try:
            InvoiceStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status: {status_filter}. "
                    f"Valid values: {[s.value for s in InvoiceStatus]}"
                ),
            ) from None

    invoices = service.list_invoices(status=status_filter, limit=limit, offset=offset)
    total = service.count_invoices(status=status_filter)

    return InvoiceListResponse(
        invoices=[_invoice_to_response(inv) for inv in invoices],
        total=total,
        limit=limit,
        offset=offset,
    )


@invoice_router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Invoice not found"},
    },
    summary="Get Invoice",
    description="Get a single invoice by ID.",
)
async def get_invoice(
    invoice_id: str,
    api_key: str = Depends(get_api_key_header),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    """
    Get an invoice by its internal ID.

    Returns the full invoice details including status and payment information.

    Requires API key authentication via X-API-Key header.
    """
    logger.debug(f"Get invoice request: {invoice_id}")

    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )

    return _invoice_to_response(invoice)


# --- Helper Functions ---


def _invoice_to_response(invoice) -> InvoiceResponse:
    """Convert InvoiceModel to InvoiceResponse."""
    data = invoice.to_dict()
    return InvoiceResponse(
        id=data["id"],
        stark_invoice_id=data.get("stark_invoice_id"),
        amount=data["amount"],
        customer_name=data["customer_name"],
        customer_tax_id=data["customer_tax_id"],
        customer_email=data["customer_email"],
        status=data["status"],
        created_at=data["created_at"] or "",
        due_date=data.get("due_date"),
        paid_at=data.get("paid_at"),
        fee=data.get("fee"),
        net_amount=data.get("net_amount"),
        retry_count=data.get("retry_count", 0),
        error_message=data.get("error_message"),
    )
