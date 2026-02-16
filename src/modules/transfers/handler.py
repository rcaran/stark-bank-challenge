"""
Transfer Handler.

This module provides event handlers for transfer operations,
specifically handling invoice.paid events to automatically create transfers.
"""

from src.modules.invoices.models import InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.transfers.service import TransferService
from src.shared.events.types import Event
from src.shared.utils.errors import NotFoundError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.transfers.handler")


class TransferHandler:
    """
    Handler for transfer-related events.

    This handler subscribes to invoice.paid events and automatically
    creates transfers to Stark Bank when invoices are paid.
    """

    def __init__(
        self,
        service: TransferService,
        invoice_repository: InvoiceRepository,
    ):
        """
        Initialize TransferHandler.

        Args:
            service: TransferService for creating transfers
            invoice_repository: InvoiceRepository for loading invoice data
        """
        self.service = service
        self.invoice_repository = invoice_repository
        logger.info("TransferHandler initialized")

    def handle_invoice_paid(self, event: Event) -> None:
        """
        Handle invoice.paid event by creating a transfer.

        This method is called when an invoice is paid. It loads the invoice
        from the database, validates it's paid, and creates a transfer.

        Args:
            event: The invoice.paid event containing invoice_id in payload

        Raises:
            Exception: Various exceptions (logged but not re-raised to avoid
                      breaking the event bus)
        """
        try:
            # Extract invoice_id from event payload
            invoice_id = event.payload.get("invoice_id")
            if not invoice_id:
                logger.error(
                    "Missing invoice_id in invoice.paid event payload",
                    event_id=event.event_id,
                )
                return

            logger.info(
                f"Processing invoice.paid event for invoice: {invoice_id}",
                event_id=event.event_id,
            )

            # Load invoice from database
            try:
                invoice = self.invoice_repository.get_by_id(invoice_id)
            except NotFoundError:
                logger.error(
                    f"Invoice not found: {invoice_id}",
                    event_id=event.event_id,
                )
                return

            # Validate invoice is paid
            if invoice.status != InvoiceStatus.PAID:
                logger.warning(
                    f"Invoice {invoice_id} is not paid (status: {invoice.status})",
                    event_id=event.event_id,
                )
                return

            # Validate invoice has net_amount
            if not invoice.net_amount or invoice.net_amount <= 0:
                logger.error(
                    f"Invoice {invoice_id} has invalid net_amount: "
                    f"{invoice.net_amount}",
                    event_id=event.event_id,
                )
                return

            # Create transfer
            logger.info(
                f"Creating transfer for invoice {invoice_id} "
                f"(net_amount: R$ {invoice.net_amount:.2f})"
            )
            transfer = self.service.create_transfer(invoice)

            logger.info(
                f"Transfer created successfully: transfer_id={transfer.id}, "
                f"invoice_id={invoice_id}",
                event_id=event.event_id,
            )

        except Exception as e:
            # Log error but don't re-raise to avoid breaking event bus
            logger.error(
                f"Error handling invoice.paid event: {e!s}",
                event_id=event.event_id,
                error=str(e),
                exc_info=True,
            )
