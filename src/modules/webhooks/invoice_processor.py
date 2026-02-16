"""
Invoice Webhook Processor.

This module processes invoice webhooks from Stark Bank,
updating invoice status and publishing relevant events.
"""

from datetime import datetime, timezone
from typing import Optional

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.webhooks.events import INVOICE_PAID, InvoicePaidEventPayload
from src.modules.webhooks.models import InvoiceWebhookPayload, WebhookEventType
from src.shared.events.bus import EventBus
from src.shared.events.types import Event
from src.shared.utils.errors import NotFoundError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.webhooks.invoice_processor")


class InvoiceWebhookProcessor:
    """
    Processes invoice webhooks from Stark Bank.

    This processor handles webhook events for invoices, updating the local
    database with payment information and publishing events for downstream
    processing (e.g., triggering transfers).
    """

    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        event_bus: EventBus,
    ):
        """
        Initialize InvoiceWebhookProcessor.

        Args:
            invoice_repository: Repository for invoice database operations
            event_bus: Event bus for publishing domain events
        """
        self._repository = invoice_repository
        self._event_bus = event_bus
        logger.debug("InvoiceWebhookProcessor initialized")

    def process(self, webhook_payload: InvoiceWebhookPayload) -> None:
        """
        Process an invoice webhook payload.

        This method:
        1. Extracts invoice data from the webhook payload
        2. Looks up the invoice in the database by stark_invoice_id
        3. Updates the invoice status and payment details
        4. Calculates the net amount (amount - fee)
        5. Publishes an invoice.paid event

        Args:
            webhook_payload: Parsed invoice webhook payload from Stark Bank

        Raises:
            NotFoundError: If the invoice is not found in the database
        """
        stark_invoice_id = webhook_payload.invoice_id
        status = webhook_payload.status

        logger.info(
            f"Processing invoice webhook: stark_id={stark_invoice_id}, status={status}"
        )

        # Only process credited (paid) invoices
        if status != WebhookEventType.INVOICE_CREDITED.value:
            logger.debug(
                f"Ignoring non-payment webhook event: {status} for {stark_invoice_id}"
            )
            return

        # Lookup invoice by stark_invoice_id
        invoice = self._repository.get_by_stark_id(stark_invoice_id)
        if not invoice:
            logger.warning(f"Invoice not found for stark_id: {stark_invoice_id}")
            raise NotFoundError(f"Invoice not found: {stark_invoice_id}")

        # Update invoice with payment details
        self._update_invoice_payment(invoice, webhook_payload)

        # Publish invoice paid event
        self._publish_invoice_paid_event(invoice, webhook_payload)

        logger.info(
            f"Invoice webhook processed successfully: "
            f"invoice_id={invoice.id}, net_amount={invoice.net_amount}"
        )

    def _update_invoice_payment(
        self,
        invoice: InvoiceModel,
        webhook_payload: InvoiceWebhookPayload,
    ) -> None:
        """
        Update invoice with payment information.

        Args:
            invoice: The invoice model to update
            webhook_payload: The webhook payload with payment details
        """
        logger.debug(f"Updating invoice payment: {invoice.id}")

        # Update status to paid
        invoice.status = InvoiceStatus.PAID

        # Set payment timestamp
        invoice.paid_at = webhook_payload.updated or datetime.now(timezone.utc)

        # Set fee (convert from centavos to reais)
        if webhook_payload.fee is not None:
            invoice.fee = webhook_payload.fee_decimal

        # Calculate net amount (amount - fee)
        invoice.calculate_net_amount()

        # Persist changes
        self._repository.update(invoice)

        logger.info(
            f"Invoice payment updated: invoice_id={invoice.id}, "
            f"fee={invoice.fee}, net_amount={invoice.net_amount}"
        )

    def _publish_invoice_paid_event(
        self,
        invoice: InvoiceModel,
        webhook_payload: InvoiceWebhookPayload,
    ) -> None:
        """
        Publish invoice paid event to the event bus.

        Args:
            invoice: The updated invoice model
            webhook_payload: The original webhook payload
        """
        logger.debug(f"Publishing invoice paid event: {invoice.id}")

        # Create event payload
        event_payload = InvoicePaidEventPayload(
            invoice_id=invoice.id,
            stark_invoice_id=str(webhook_payload.invoice_id),
            amount=invoice.amount,
            fee=invoice.fee or 0.0,
            net_amount=invoice.net_amount or invoice.amount,
            customer_tax_id=invoice.customer_tax_id,
            paid_at=invoice.paid_at or datetime.now(timezone.utc),
        )

        # Create and publish event
        event = Event(
            event_type=INVOICE_PAID,
            payload=event_payload.to_dict(),
            metadata={
                "source": "webhook",
                "webhook_invoice_id": webhook_payload.invoice_id,
            },
        )

        self._event_bus.publish(event)

        logger.info(f"Invoice paid event published: {invoice.id}")

    def process_payment(
        self,
        stark_invoice_id: str,
        amount: int,
        fee: Optional[int],
        paid_at: Optional[datetime] = None,
    ) -> InvoiceModel:
        """
        Convenience method to process a payment directly without full webhook payload.

        This is useful for testing or manual payment processing.

        Args:
            stark_invoice_id: The Stark Bank invoice ID
            amount: Payment amount in centavos
            fee: Fee amount in centavos
            paid_at: Payment timestamp (defaults to now)

        Returns:
            Updated InvoiceModel

        Raises:
            NotFoundError: If invoice not found
        """
        logger.info(f"Processing direct payment: stark_id={stark_invoice_id}")

        invoice = self._repository.get_by_stark_id(stark_invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice not found: {stark_invoice_id}")

        # Update invoice
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = paid_at or datetime.now(timezone.utc)

        if fee is not None:
            invoice.fee = fee / 100.0  # Convert from centavos

        invoice.calculate_net_amount()
        self._repository.update(invoice)

        # Publish event
        event_payload = InvoicePaidEventPayload(
            invoice_id=invoice.id,
            stark_invoice_id=stark_invoice_id,
            amount=invoice.amount,
            fee=invoice.fee or 0.0,
            net_amount=invoice.net_amount or invoice.amount,
            customer_tax_id=invoice.customer_tax_id,
            paid_at=invoice.paid_at,
        )

        event = Event(
            event_type=INVOICE_PAID,
            payload=event_payload.to_dict(),
            metadata={"source": "direct"},
        )
        self._event_bus.publish(event)

        logger.info(f"Direct payment processed: invoice_id={invoice.id}")
        return invoice
