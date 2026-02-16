"""
Webhook Receiver.

This module provides the WebhookReceiver class that orchestrates the
reception and processing of webhooks from Stark Bank, including signature
validation and routing to appropriate processors.
"""

import json

from src.modules.webhooks.events import WEBHOOK_VALIDATION_FAILED
from src.modules.webhooks.invoice_processor import InvoiceWebhookProcessor
from src.modules.webhooks.models import (
    InvoiceWebhookPayload,
    TransferWebhookPayload,
    WebhookEvent,
)
from src.modules.webhooks.transfer_processor import TransferWebhookProcessor
from src.modules.webhooks.validator import WebhookValidator
from src.shared.events.bus import EventBus
from src.shared.security.signature import InvalidSignatureError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.webhooks.receiver")


class WebhookReceiver:
    """
    Orchestrates webhook reception and processing.

    This class handles the full webhook flow:
    1. Signature validation
    2. Payload parsing
    3. Routing to appropriate processor (invoice or transfer)
    4. Error handling and logging

    It's designed to always return a successful response to Stark Bank
    (except for invalid signatures) to prevent webhook retries for
    application errors that won't be resolved by retrying.
    """

    def __init__(
        self,
        validator: WebhookValidator,
        invoice_processor: InvoiceWebhookProcessor,
        transfer_processor: TransferWebhookProcessor,
        event_bus: EventBus,
    ):
        """
        Initialize WebhookReceiver.

        Args:
            validator: Webhook signature validator
            invoice_processor: Processor for invoice webhooks
            transfer_processor: Processor for transfer webhooks
            event_bus: Event bus for publishing domain events
        """
        self._validator = validator
        self._invoice_processor = invoice_processor
        self._transfer_processor = transfer_processor
        self._event_bus = event_bus
        logger.debug("WebhookReceiver initialized")

    def receive_invoice_webhook(
        self, payload: bytes, signature: str
    ) -> dict[str, str]:
        """
        Receive and process an invoice webhook.

        This method:
        1. Validates the webhook signature
        2. Parses the payload into InvoiceWebhookPayload
        3. Processes the webhook via InvoiceWebhookProcessor
        4. Returns success response

        Args:
            payload: Raw webhook payload bytes
            signature: Digital signature from Stark Bank

        Returns:
            Dictionary with status indicating success

        Raises:
            InvalidSignatureError: If signature validation fails (this should
                                   result in a 401 response to prevent replay attacks)
        """
        logger.info(
            "Receiving invoice webhook",
            payload_size=len(payload),
            has_signature=bool(signature),
        )

        # Validate signature - raises InvalidSignatureError if invalid
        try:
            self._validator.verify_signature(payload, signature)
        except InvalidSignatureError as e:
            logger.warning("Invoice webhook signature validation failed")
            self._publish_validation_failed_event(
                webhook_type="invoice", payload=payload, error=str(e)
            )
            raise  # Re-raise to return 401

        # Parse and process payload
        try:
            payload_dict = json.loads(payload.decode("utf-8"))
            webhook_event = WebhookEvent.from_dict(payload_dict)
            invoice_payload = InvoiceWebhookPayload.from_webhook_event(webhook_event)

            logger.info(
                "Invoice webhook parsed successfully",
                invoice_id=invoice_payload.invoice_id,
                status=invoice_payload.status,
            )

            # Process the webhook
            self._invoice_processor.process(invoice_payload)

            logger.info(
                "Invoice webhook processed successfully",
                invoice_id=invoice_payload.invoice_id,
            )

            return {"status": "ok"}

        except Exception as e:
            logger.error(
                "Error processing invoice webhook",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return success anyway to prevent Stark Bank retries
            # The error is logged and can be monitored/alerted
            return {"status": "ok", "error": "processing_error"}

    def receive_transfer_webhook(
        self, payload: bytes, signature: str
    ) -> dict[str, str]:
        """
        Receive and process a transfer webhook.

        This method:
        1. Validates the webhook signature
        2. Parses the payload into TransferWebhookPayload
        3. Processes the webhook via TransferWebhookProcessor
        4. Returns success response

        Args:
            payload: Raw webhook payload bytes
            signature: Digital signature from Stark Bank

        Returns:
            Dictionary with status indicating success

        Raises:
            InvalidSignatureError: If signature validation fails (this should
                                   result in a 401 response to prevent replay attacks)
        """
        logger.info(
            "Receiving transfer webhook",
            payload_size=len(payload),
            has_signature=bool(signature),
        )

        # Validate signature - raises InvalidSignatureError if invalid
        try:
            self._validator.verify_signature(payload, signature)
        except InvalidSignatureError as e:
            logger.warning("Transfer webhook signature validation failed")
            self._publish_validation_failed_event(
                webhook_type="transfer", payload=payload, error=str(e)
            )
            raise  # Re-raise to return 401

        # Parse and process payload
        try:
            payload_dict = json.loads(payload.decode("utf-8"))
            webhook_event = WebhookEvent.from_dict(payload_dict)
            transfer_payload = TransferWebhookPayload.from_webhook_event(webhook_event)

            logger.info(
                "Transfer webhook parsed successfully",
                transfer_id=transfer_payload.transfer_id,
                status=transfer_payload.status,
            )

            # Process the webhook
            self._transfer_processor.process(transfer_payload)

            logger.info(
                "Transfer webhook processed successfully",
                transfer_id=transfer_payload.transfer_id,
            )

            return {"status": "ok"}

        except Exception as e:
            logger.error(
                "Error processing transfer webhook",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return success anyway to prevent Stark Bank retries
            # The error is logged and can be monitored/alerted
            return {"status": "ok", "error": "processing_error"}

    def _publish_validation_failed_event(
        self, webhook_type: str, payload: bytes, error: str
    ) -> None:
        """
        Publish a webhook validation failed event.

        Args:
            webhook_type: Type of webhook (invoice or transfer)
            payload: Raw webhook payload
            error: Error message
        """
        try:
            self._event_bus.publish(
                event_type=WEBHOOK_VALIDATION_FAILED,
                payload={
                    "webhook_type": webhook_type,
                    "payload_size": len(payload),
                    "error": error,
                },
                metadata={
                    "module": "webhooks.receiver",
                    "webhook_type": webhook_type,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to publish validation failed event",
                error=str(e),
                error_type=type(e).__name__,
            )
