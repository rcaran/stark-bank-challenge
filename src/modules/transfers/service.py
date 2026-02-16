"""
Transfer Service.

This module provides business logic for transfer operations,
including creating transfers to Stark Bank when invoices are paid.
"""

from datetime import UTC, datetime

from src.config.constants import (
    STARKBANK_DESTINATION_ACCOUNT_NUMBER,
    STARKBANK_DESTINATION_ACCOUNT_TYPE,
    STARKBANK_DESTINATION_BANK_CODE,
    STARKBANK_DESTINATION_BRANCH_CODE,
    STARKBANK_DESTINATION_NAME,
    STARKBANK_DESTINATION_TAX_ID,
)
from src.modules.invoices.models import InvoiceModel
from src.modules.transfers.events import (
    TRANSFER_FAILED,
    TRANSFER_INITIATED,
    TransferFailedEventPayload,
    TransferInitiatedEventPayload,
)
from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.repository import TransferRepository
from src.shared.events.bus import EventBus
from src.shared.events.types import Event
from src.shared.stark.transfer_api import StarkTransferAPI
from src.shared.utils.errors import NotFoundError, RetriableError, ValidationError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.transfers.service")


class TransferService:
    """
    Service for transfer business logic.

    This service handles the creation of transfers to Stark Bank
    when invoices are paid, including idempotency checks and
    event publishing.
    """

    def __init__(
        self,
        repository: TransferRepository,
        stark_api: StarkTransferAPI,
        event_bus: EventBus,
    ):
        """
        Initialize TransferService.

        Args:
            repository: Transfer repository for database operations
            stark_api: Stark Bank Transfer API client
            event_bus: Event bus for publishing events
        """
        self.repository = repository
        self.stark_api = stark_api
        self.event_bus = event_bus
        logger.info("TransferService initialized")

    def create_transfer(self, invoice: InvoiceModel) -> TransferModel:
        """
        Create a transfer for a paid invoice.

        This method creates a transfer to the Stark Bank account
        with the net amount from the invoice. It ensures idempotency
        by checking if a transfer already exists for the invoice.

        Args:
            invoice: The paid invoice to transfer funds for

        Returns:
            TransferModel: The created or existing transfer

        Raises:
            ValidationError: If invoice data is invalid
            RetriableError: If transfer creation temporarily fails
            Exception: For other unexpected errors
        """
        logger.info(f"Creating transfer for invoice: {invoice.id}")

        # Validate invoice
        if not invoice.net_amount or invoice.net_amount <= 0:
            error_msg = (
                f"Invalid net_amount for invoice {invoice.id}: "
                f"{invoice.net_amount}"
            )
            logger.error(error_msg)
            raise ValidationError(error_msg)

        # Generate external_id for idempotency
        external_id = f"invoice-{invoice.id}"

        # Check if transfer already exists (idempotency)
        existing_transfer = self.repository.get_by_external_id(external_id)
        if existing_transfer:
            logger.info(
                f"Transfer already exists for invoice {invoice.id}: "
                f"{existing_transfer.id}"
            )
            return existing_transfer

        # Create transfer model
        transfer = TransferModel(
            invoice_id=invoice.id,
            amount=invoice.net_amount,
            external_id=external_id,
            status=TransferStatus.PENDING,
        )

        try:
            # Convert amount to cents (int) for Stark Bank API
            amount_cents = int(invoice.net_amount * 100)

            # Create transfer via Stark Bank API
            logger.info(
                f"Creating transfer via Stark Bank API: invoice_id={invoice.id}, "
                f"amount={invoice.net_amount} (R$), external_id={external_id}"
            )

            stark_response = self.stark_api.create_transfer(
                amount=amount_cents,
                name=STARKBANK_DESTINATION_NAME,
                tax_id=STARKBANK_DESTINATION_TAX_ID,
                bank_code=STARKBANK_DESTINATION_BANK_CODE,
                branch_code=STARKBANK_DESTINATION_BRANCH_CODE,
                account_number=STARKBANK_DESTINATION_ACCOUNT_NUMBER,
                external_id=external_id,
                tags=["invoice-payment", f"invoice:{invoice.id}"],
                account_type=STARKBANK_DESTINATION_ACCOUNT_TYPE,
            )

            # Update transfer with Stark Bank ID and status
            transfer.stark_transfer_id = stark_response.id
            transfer.status = TransferStatus.CREATED
            transfer.updated_at = datetime.now(UTC)

            # Save transfer to database
            self.repository.create(transfer)
            logger.info(
                f"Transfer created successfully: id={transfer.id}, "
                f"stark_id={stark_response.id}"
            )

            # Publish transfer initiated event
            event_payload = TransferInitiatedEventPayload(
                transfer_id=transfer.id,
                invoice_id=invoice.id,
                stark_transfer_id=stark_response.id,
                external_id=external_id,
                amount=invoice.net_amount,
                created_at=transfer.created_at,
            )
            event = Event(
                event_type=TRANSFER_INITIATED,
                payload=event_payload.to_dict(),
                metadata={
                    "invoice_id": invoice.id,
                    "transfer_id": transfer.id,
                    "stark_transfer_id": stark_response.id,
                    "source": "transfer_service",
                },
            )
            self.event_bus.publish(event)

            return transfer

        except (RetriableError, ConnectionError) as e:
            # Retriable errors - will be retried by the retry decorator
            error_msg = (
                f"Retriable error creating transfer for invoice "
                f"{invoice.id}: {e!s}"
            )
            logger.warning(error_msg)

            # Update transfer with error information
            transfer.error_message = str(e)
            transfer.retry_count += 1
            transfer.last_retry_at = datetime.now(UTC)
            transfer.status = TransferStatus.FAILED

            # Save failed transfer to database
            try:
                self.repository.create(transfer)
            except Exception as db_error:
                logger.error(
                    f"Failed to save failed transfer to database: {db_error}"
                )

            # Publish transfer failed event
            self._publish_transfer_failed_event(transfer, invoice, str(e))

            # Re-raise to trigger retry
            raise

        except Exception as e:
            # Non-retriable errors
            error_msg = (
                f"Non-retriable error creating transfer for invoice "
                f"{invoice.id}: {e!s}"
            )
            logger.error(error_msg, exc_info=True)

            # Update transfer with error information
            transfer.error_message = str(e)
            transfer.status = TransferStatus.FAILED

            # Save failed transfer to database
            try:
                self.repository.create(transfer)
            except Exception as db_error:
                logger.error(
                    f"Failed to save failed transfer to database: {db_error}"
                )

            # Publish transfer failed event
            self._publish_transfer_failed_event(transfer, invoice, str(e))

            # Re-raise
            raise

    def get_transfer(self, transfer_id: str) -> TransferModel | None:
        """
        Get a transfer by its ID.

        Args:
            transfer_id: The transfer ID

        Returns:
            TransferModel or None if not found
        """
        logger.debug(f"Getting transfer: {transfer_id}")
        return self.repository.get_by_id(transfer_id)

    def get_transfer_by_invoice(self, invoice_id: str) -> TransferModel | None:
        """
        Get a transfer by its invoice ID.

        Args:
            invoice_id: The invoice ID

        Returns:
            TransferModel or None if not found
        """
        logger.debug(f"Getting transfer by invoice: {invoice_id}")
        return self.repository.get_by_invoice_id(invoice_id)

    def list_transfers(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TransferModel]:
        """
        List transfers with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of TransferModel instances
        """
        logger.debug(
            f"Listing transfers: status={status}, limit={limit}, offset={offset}"
        )
        return self.repository.list(status=status, limit=limit, offset=offset)

    def count_transfers(self, status: str | None = None) -> int:
        """
        Count transfers with optional filtering.

        Args:
            status: Optional status filter

        Returns:
            Number of transfers matching the criteria
        """
        logger.debug(f"Counting transfers: status={status}")
        return self.repository.count(status=status)

    def update_transfer_status(
        self,
        transfer_id: str,
        status: str,
        **kwargs,
    ) -> None:
        """
        Update the status of a transfer.

        Args:
            transfer_id: The transfer ID
            status: The new status
            **kwargs: Additional fields to update (e.g., completed_at, error_message)

        Raises:
            NotFoundError: If transfer not found
        """
        logger.info(f"Updating transfer status: {transfer_id} -> {status}")

        transfer = self.repository.get_by_id(transfer_id)
        if not transfer:
            raise NotFoundError(f"Transfer not found: {transfer_id}")

        # Update status
        transfer.status = TransferStatus(status)
        transfer.updated_at = datetime.now(UTC)

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(transfer, key):
                setattr(transfer, key, value)

        # Save to database
        self.repository.update(transfer)
        logger.info(f"Transfer status updated: {transfer_id} -> {status}")

    def _publish_transfer_failed_event(
        self,
        transfer: TransferModel,
        invoice: InvoiceModel,
        error_message: str,
    ) -> None:
        """
        Publish a transfer failed event.

        Args:
            transfer: The failed transfer
            invoice: The related invoice
            error_message: The error message
        """
        try:
            event_payload = TransferFailedEventPayload(
                transfer_id=transfer.id,
                invoice_id=invoice.id,
                stark_transfer_id=transfer.stark_transfer_id,
                amount=transfer.amount,
                error_message=error_message,
                retry_count=transfer.retry_count,
                failed_at=datetime.now(UTC),
            )
            event = Event(
                event_type=TRANSFER_FAILED,
                payload=event_payload.to_dict(),
                metadata={
                    "invoice_id": invoice.id,
                    "transfer_id": transfer.id,
                    "error": error_message,
                    "source": "transfer_service",
                },
            )
            self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish transfer failed event: {e}")
