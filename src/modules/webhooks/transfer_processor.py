"""
Transfer Webhook Processor.

This module processes transfer webhooks from Stark Bank,
updating transfer status and publishing relevant events.
"""

from datetime import UTC, datetime
from typing import Any, Protocol

from src.modules.webhooks.events import (
    TRANSFER_COMPLETED,
    TRANSFER_FAILED,
    TRANSFER_PROCESSING,
    TransferCompletedEventPayload,
    TransferFailedEventPayload,
    TransferProcessingEventPayload,
)
from src.modules.webhooks.models import TransferWebhookPayload
from src.shared.events.bus import EventBus
from src.shared.events.types import Event
from src.shared.utils.errors import NotFoundError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.webhooks.transfer_processor")


class TransferRepositoryProtocol(Protocol):
    """Protocol defining the interface for transfer repository."""

    def get_by_stark_id(self, stark_id: str) -> Any | None:
        """Get transfer by Stark Bank transfer ID."""
        ...

    def update(self, transfer: Any) -> None:
        """Update transfer in database."""
        ...


class TransferWebhookProcessor:
    """
    Processes transfer webhooks from Stark Bank.

    This processor handles webhook events for transfers, updating the local
    database with status changes and publishing events for downstream
    processing and monitoring.
    """

    def __init__(
        self,
        transfer_repository: TransferRepositoryProtocol,
        event_bus: EventBus,
    ):
        """
        Initialize TransferWebhookProcessor.

        Args:
            transfer_repository: Repository for transfer database operations
            event_bus: Event bus for publishing domain events
        """
        self._repository = transfer_repository
        self._event_bus = event_bus
        logger.debug("TransferWebhookProcessor initialized")

    def process(self, webhook_payload: TransferWebhookPayload) -> None:
        """
        Process a transfer webhook payload.

        This method:
        1. Extracts transfer data from the webhook payload (transfer_id, status, error)
        2. Looks up the transfer in the database by stark_transfer_id
        3. Updates the transfer status
        4. Updates the updated_at timestamp
        5. For success: updates completed_at and publishes transfer.completed
        6. For failed: saves error_message and publishes transfer.failed
        7. For processing: publishes transfer.processing

        Args:
            webhook_payload: Parsed transfer webhook payload from Stark Bank

        Raises:
            NotFoundError: If the transfer is not found in the database
        """
        stark_transfer_id = webhook_payload.transfer_id
        status = webhook_payload.status

        logger.info(
            f"Processing transfer webhook: "
            f"stark_id={stark_transfer_id}, status={status}"
        )

        # Lookup transfer by stark_transfer_id
        transfer = self._repository.get_by_stark_id(stark_transfer_id)
        if not transfer:
            logger.warning(f"Transfer not found for stark_id: {stark_transfer_id}")
            raise NotFoundError(f"Transfer not found: {stark_transfer_id}")

        # Update transfer status based on webhook status
        if webhook_payload.is_successful:
            self._process_success(transfer, webhook_payload)
        elif webhook_payload.is_failed:
            self._process_failed(transfer, webhook_payload)
        elif webhook_payload.is_processing:
            self._process_processing(transfer, webhook_payload)
        else:
            logger.warning(
                f"Unknown transfer status: {status} for stark_id={stark_transfer_id}"
            )
            return

        logger.info(
            f"Transfer webhook processed successfully: "
            f"transfer_id={transfer.id}, status={status}"
        )

    def _process_success(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Process successful transfer webhook.

        Args:
            transfer: The transfer model to update
            webhook_payload: The webhook payload with transfer details
        """
        logger.debug(f"Processing transfer success: {transfer.id}")

        # Update transfer status
        transfer.status = "success"

        # Set completed_at timestamp
        transfer.completed_at = webhook_payload.updated or datetime.now(UTC)

        # Update updated_at timestamp
        transfer.updated_at = datetime.now(UTC)

        # Set fee if available
        if webhook_payload.fee is not None:
            transfer.fee = webhook_payload.fee_decimal

        # Persist changes
        self._repository.update(transfer)

        # Publish transfer completed event
        self._publish_completed_event(transfer, webhook_payload)

        logger.info(
            f"Transfer success processed: transfer_id={transfer.id}, "
            f"completed_at={transfer.completed_at}"
        )

    def _process_failed(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Process failed transfer webhook.

        Args:
            transfer: The transfer model to update
            webhook_payload: The webhook payload with error details
        """
        logger.debug(f"Processing transfer failure: {transfer.id}")

        # Update transfer status
        transfer.status = "failed"

        # Update updated_at timestamp
        transfer.updated_at = datetime.now(UTC)

        # Save error information
        transfer.error_message = webhook_payload.error_message
        if hasattr(transfer, "error_code"):
            transfer.error_code = webhook_payload.error_code

        # Persist changes
        self._repository.update(transfer)

        # Publish transfer failed event
        self._publish_failed_event(transfer, webhook_payload)

        logger.warning(
            f"Transfer failed: transfer_id={transfer.id}, "
            f"error={webhook_payload.error_message}"
        )

    def _process_processing(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Process transfer in processing state webhook.

        Args:
            transfer: The transfer model to update
            webhook_payload: The webhook payload with transfer details
        """
        logger.debug(f"Processing transfer in progress: {transfer.id}")

        # Update transfer status
        transfer.status = "processing"

        # Update updated_at timestamp
        transfer.updated_at = datetime.now(UTC)

        # Persist changes
        self._repository.update(transfer)

        # Publish transfer processing event
        self._publish_processing_event(transfer, webhook_payload)

        logger.info(f"Transfer processing update: transfer_id={transfer.id}")

    def _publish_completed_event(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Publish transfer completed event to the event bus.

        Args:
            transfer: The updated transfer model
            webhook_payload: The original webhook payload
        """
        logger.debug(f"Publishing transfer completed event: {transfer.id}")

        # Get invoice_id if available
        invoice_id = getattr(transfer, "invoice_id", None)

        # Create event payload
        event_payload = TransferCompletedEventPayload(
            transfer_id=transfer.id,
            stark_transfer_id=str(webhook_payload.transfer_id),
            invoice_id=invoice_id,
            amount=webhook_payload.amount_decimal,
            fee=webhook_payload.fee_decimal,
            external_id=webhook_payload.external_id or "",
            completed_at=transfer.completed_at or datetime.now(UTC),
        )

        # Create and publish event
        event = Event(
            event_type=TRANSFER_COMPLETED,
            payload=event_payload.to_dict(),
            metadata={
                "source": "webhook",
                "webhook_transfer_id": webhook_payload.transfer_id,
            },
        )

        self._event_bus.publish(event)

        logger.info(f"Transfer completed event published: {transfer.id}")

    def _publish_failed_event(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Publish transfer failed event to the event bus.

        Args:
            transfer: The updated transfer model
            webhook_payload: The original webhook payload
        """
        logger.debug(f"Publishing transfer failed event: {transfer.id}")

        # Get invoice_id if available
        invoice_id = getattr(transfer, "invoice_id", None)

        # Create event payload
        event_payload = TransferFailedEventPayload(
            transfer_id=transfer.id,
            stark_transfer_id=str(webhook_payload.transfer_id),
            invoice_id=invoice_id,
            amount=webhook_payload.amount_decimal,
            external_id=webhook_payload.external_id or "",
            error_code=webhook_payload.error_code,
            error_message=webhook_payload.error_message,
            failed_at=datetime.now(UTC),
        )

        # Create and publish event
        event = Event(
            event_type=TRANSFER_FAILED,
            payload=event_payload.to_dict(),
            metadata={
                "source": "webhook",
                "webhook_transfer_id": webhook_payload.transfer_id,
                "error_code": webhook_payload.error_code,
            },
        )

        self._event_bus.publish(event)

        logger.info(f"Transfer failed event published: {transfer.id}")

    def _publish_processing_event(
        self,
        transfer: Any,
        webhook_payload: TransferWebhookPayload,
    ) -> None:
        """
        Publish transfer processing event to the event bus.

        Args:
            transfer: The updated transfer model
            webhook_payload: The original webhook payload
        """
        logger.debug(f"Publishing transfer processing event: {transfer.id}")

        # Get invoice_id if available
        invoice_id = getattr(transfer, "invoice_id", None)

        # Create event payload
        event_payload = TransferProcessingEventPayload(
            transfer_id=transfer.id,
            stark_transfer_id=str(webhook_payload.transfer_id),
            invoice_id=invoice_id,
            amount=webhook_payload.amount_decimal,
            external_id=webhook_payload.external_id or "",
            timestamp=datetime.now(UTC),
        )

        # Create and publish event
        event = Event(
            event_type=TRANSFER_PROCESSING,
            payload=event_payload.to_dict(),
            metadata={
                "source": "webhook",
                "webhook_transfer_id": webhook_payload.transfer_id,
            },
        )

        self._event_bus.publish(event)

        logger.info(f"Transfer processing event published: {transfer.id}")
