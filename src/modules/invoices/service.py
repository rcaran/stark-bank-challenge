"""
Invoice Service.

This module contains the business logic for invoice operations,
coordinating between the repository, Stark Bank API, and event bus.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.modules.invoices.events import (
    INVOICE_CREATED,
    INVOICE_CREATION_FAILED,
    InvoiceCreatedEventPayload,
    InvoiceCreationFailedEventPayload,
)
from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.shared.events.bus import EventBus
from src.shared.events.types import Event
from src.shared.stark.invoice_api import StarkInvoiceAPI
from src.shared.utils.errors import NotFoundError, StarkBankError, ValidationError
from src.shared.utils.logger import get_logger
from src.shared.utils.validators import validate_tax_id

logger = get_logger("modules.invoices.service")


class InvoiceService:
    """
    Service layer for invoice operations.

    Coordinates between:
    - InvoiceRepository: Database operations
    - StarkInvoiceAPI: Stark Bank integration
    - EventBus: Event publishing for system integration
    """

    def __init__(
        self,
        repository: InvoiceRepository = None,
        stark_api: StarkInvoiceAPI = None,
        event_bus: EventBus = None,
    ):
        """
        Initialize InvoiceService with dependencies.

        Args:
            repository: InvoiceRepository instance (creates new if not provided)
            stark_api: StarkInvoiceAPI instance (creates new if not provided)
            event_bus: EventBus instance (uses singleton if not provided)
        """
        self.repository = repository or InvoiceRepository()
        self.stark_api = stark_api or StarkInvoiceAPI()
        self.event_bus = event_bus or EventBus()

        logger.info("InvoiceService initialized")

    def create_invoice(self, invoice_data: Dict[str, Any]) -> InvoiceModel:
        """
        Create a new invoice.

        This method:
        1. Validates input data
        2. Creates invoice in Stark Bank (with retry)
        3. Persists to local database
        4. Publishes invoice.created event

        Args:
            invoice_data: Dictionary with invoice fields:
                - amount: Amount in cents (int)
                - customer_name: Customer name
                - customer_tax_id: CPF or CNPJ
                - customer_email: Customer email
                - due_date: Due date (datetime)

        Returns:
            Created InvoiceModel instance

        Raises:
            ValidationError: If input data is invalid
            StarkBankError: If Stark Bank API fails after retries
        """
        logger.info("Creating new invoice", amount=invoice_data.get("amount"))

        # Validate input data
        self._validate_invoice_data(invoice_data)

        # Create local invoice model (pending status)
        invoice = InvoiceModel(
            amount=invoice_data["amount"],
            customer_name=invoice_data["customer_name"],
            customer_tax_id=invoice_data["customer_tax_id"],
            customer_email=invoice_data["customer_email"],
            due_date=invoice_data.get("due_date"),
        )

        try:
            # Create invoice in Stark Bank
            stark_response = self.stark_api.create_invoice(
                amount=int(invoice.amount),
                tax_id=invoice.customer_tax_id,
                name=invoice.customer_name,
                due_date=invoice.due_date.date() if invoice.due_date else None,
            )

            # Update invoice with Stark Bank ID and mark as created
            invoice.mark_as_created(stark_response.id)

            # Persist to database
            self.repository.create(invoice)

            # Publish success event
            self._publish_invoice_created_event(invoice)

            logger.info(
                "Invoice created successfully",
                invoice_id=invoice.id,
                stark_id=invoice.stark_invoice_id,
            )

            return invoice

        except (StarkBankError, Exception) as e:
            # Mark as failed and save
            error_message = str(e)
            invoice.mark_as_failed(error_message)

            # Try to persist failed invoice for tracking
            try:
                self.repository.create(invoice)
            except Exception as db_error:
                logger.error(
                    "Failed to persist failed invoice",
                    invoice_id=invoice.id,
                    error=str(db_error),
                )

            # Publish failure event
            self._publish_invoice_creation_failed_event(invoice, error_message)

            logger.error(
                "Invoice creation failed",
                invoice_id=invoice.id,
                error=error_message,
            )

            raise

    def get_invoice(self, invoice_id: str) -> Optional[InvoiceModel]:
        """
        Get an invoice by ID.

        Args:
            invoice_id: Internal invoice ID

        Returns:
            InvoiceModel if found, None otherwise
        """
        logger.debug(f"Getting invoice: {invoice_id}")
        return self.repository.get_by_id(invoice_id)

    def get_invoice_by_stark_id(self, stark_id: str) -> Optional[InvoiceModel]:
        """
        Get an invoice by Stark Bank ID.

        Args:
            stark_id: Stark Bank invoice ID

        Returns:
            InvoiceModel if found, None otherwise
        """
        logger.debug(f"Getting invoice by Stark ID: {stark_id}")
        return self.repository.get_by_stark_id(stark_id)

    def list_invoices(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InvoiceModel]:
        """
        List invoices with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of InvoiceModel instances
        """
        logger.debug(
            f"Listing invoices: status={status}, limit={limit}, offset={offset}"
        )
        return self.repository.list(status=status, limit=limit, offset=offset)

    def update_invoice_status(
        self,
        invoice_id: str,
        status: InvoiceStatus,
        **kwargs,
    ) -> InvoiceModel:
        """
        Update an invoice's status.

        Args:
            invoice_id: Invoice ID to update
            status: New status
            **kwargs: Additional fields to update (fee, paid_at, etc.)

        Returns:
            Updated InvoiceModel

        Raises:
            NotFoundError: If invoice doesn't exist
        """
        logger.info(f"Updating invoice status: {invoice_id} -> {status}")

        invoice = self.repository.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_id}")

        # Update status
        invoice.status = status

        # Update additional fields
        if "fee" in kwargs:
            invoice.fee = kwargs["fee"]
            invoice.calculate_net_amount()

        if "paid_at" in kwargs:
            invoice.paid_at = kwargs["paid_at"]

        if "error_message" in kwargs:
            invoice.error_message = kwargs["error_message"]

        # Persist changes
        self.repository.update(invoice)

        logger.info(f"Invoice status updated: {invoice_id} -> {status}")
        return invoice

    def mark_invoice_as_paid(
        self,
        invoice_id: str,
        fee: float,
        paid_at: datetime = None,
    ) -> InvoiceModel:
        """
        Mark an invoice as paid.

        Args:
            invoice_id: Invoice ID
            fee: Fee charged by Stark Bank
            paid_at: Payment timestamp (optional)

        Returns:
            Updated InvoiceModel

        Raises:
            NotFoundError: If invoice doesn't exist
        """
        invoice = self.repository.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {invoice_id}")

        invoice.mark_as_paid(fee=fee, paid_at=paid_at or datetime.now(timezone.utc))
        self.repository.update(invoice)

        logger.info(
            "Invoice marked as paid",
            invoice_id=invoice_id,
            fee=fee,
            net_amount=invoice.net_amount,
        )

        return invoice

    def count_invoices(self, status: Optional[str] = None) -> int:
        """
        Count invoices with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            Number of invoices
        """
        return self.repository.count(status=status)

    def _validate_invoice_data(self, data: Dict[str, Any]) -> None:
        """
        Validate invoice input data.

        Args:
            data: Invoice data dictionary

        Raises:
            ValidationError: If data is invalid
        """
        required_fields = [
            "amount", "customer_name", "customer_tax_id", "customer_email"
        ]

        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Missing required field: {field}")

        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            raise ValidationError("Amount must be a positive number")

        # Validate tax ID (CPF or CNPJ)
        if not validate_tax_id(data["customer_tax_id"]):
            raise ValidationError(f"Invalid tax ID: {data['customer_tax_id']}")

        # Validate email format (basic check)
        if "@" not in data["customer_email"]:
            raise ValidationError(f"Invalid email: {data['customer_email']}")

    def _publish_invoice_created_event(self, invoice: InvoiceModel) -> None:
        """Publish invoice.created event."""
        payload = InvoiceCreatedEventPayload(
            invoice_id=invoice.id,
            stark_invoice_id=invoice.stark_invoice_id,
            amount=invoice.amount,
            customer_name=invoice.customer_name,
            customer_tax_id=invoice.customer_tax_id,
            customer_email=invoice.customer_email,
            created_at=invoice.created_at,
        )

        event = Event(
            event_type=INVOICE_CREATED,
            payload=payload.to_dict(),
            metadata={"source": "invoice_service"},
        )

        self.event_bus.publish(event)

    def _publish_invoice_creation_failed_event(
        self,
        invoice: InvoiceModel,
        error_message: str,
    ) -> None:
        """Publish invoice.creation_failed event."""
        payload = InvoiceCreationFailedEventPayload(
            invoice_id=invoice.id,
            amount=invoice.amount,
            customer_name=invoice.customer_name,
            customer_tax_id=invoice.customer_tax_id,
            error_message=error_message,
            retry_count=invoice.retry_count,
            timestamp=datetime.now(timezone.utc),
        )

        event = Event(
            event_type=INVOICE_CREATION_FAILED,
            payload=payload.to_dict(),
            metadata={"source": "invoice_service"},
        )

        self.event_bus.publish(event)
