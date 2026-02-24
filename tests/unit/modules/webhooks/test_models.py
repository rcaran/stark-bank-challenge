"""Unit tests for Webhook Models."""

from datetime import UTC, datetime

import pytest

from src.modules.webhooks.models import (
    InvoiceWebhookPayload,
    TransferWebhookPayload,
    WebhookEvent,
    WebhookEventType,
)


class TestWebhookEvent:
    """Tests for WebhookEvent dataclass."""

    def test_parse_valid_webhook_event(self):
        """Test parsing a valid webhook event."""
        payload = {
            "event": {
                "id": "5678234567890123",
                "subscription": "invoice",
                "log": {
                    "id": "1234567890123456",
                    "type": "credited",
                    "created": "2026-02-15T10:30:00.000000+00:00",
                    "invoice": {
                        "id": "9876543210987654",
                        "amount": 10000,
                        "status": "paid",
                    },
                },
            }
        }

        event = WebhookEvent.from_dict(payload)

        assert event.subscription == "invoice"
        assert event.event_id == "5678234567890123"
        assert event.event_type == "credited"
        assert event.log_id == "1234567890123456"
        assert event.raw_payload == payload

    def test_parse_webhook_missing_event_field(self):
        """Test parsing fails when 'event' field is missing."""
        payload = {"data": {"something": "else"}}

        with pytest.raises(ValueError, match="Missing 'event' field"):
            WebhookEvent.from_dict(payload)

    def test_parse_webhook_missing_log_field(self):
        """Test parsing fails when 'log' field is missing."""
        payload = {"event": {"id": "123", "subscription": "invoice"}}

        with pytest.raises(ValueError, match="Missing 'log' field"):
            WebhookEvent.from_dict(payload)

    def test_webhook_event_to_dict(self):
        """Test converting webhook event to dictionary."""
        now = datetime.now(UTC)
        event = WebhookEvent(
            subscription="transfer",
            event_id="12345",
            event_type="success",
            log_id="67890",
            log_created=now,
            received_at=now,
        )

        result = event.to_dict()

        assert result["subscription"] == "transfer"
        assert result["event_id"] == "12345"
        assert result["event_type"] == "success"
        assert result["log_id"] == "67890"

    def test_parse_webhook_with_z_timezone(self):
        """Test parsing timestamp with Z timezone suffix."""
        payload = {
            "event": {
                "id": "123",
                "subscription": "invoice",
                "log": {
                    "id": "456",
                    "type": "credited",
                    "created": "2026-02-15T10:30:00Z",
                    "invoice": {"id": "789", "amount": 1000},
                },
            }
        }

        event = WebhookEvent.from_dict(payload)

        assert event.log_created is not None
        assert event.log_created.tzinfo is not None


class TestInvoiceWebhookPayload:
    """Tests for InvoiceWebhookPayload dataclass."""

    @pytest.fixture
    def sample_invoice_webhook(self):
        """Sample invoice webhook payload from Stark Bank."""
        return {
            "event": {
                "id": "5678234567890123",
                "subscription": "invoice",
                "log": {
                    "id": "1234567890123456",
                    "type": "credited",
                    "created": "2026-02-15T10:30:00.000000+00:00",
                    "invoice": {
                        "id": "9876543210987654",
                        "amount": 50000,  # 500.00 reais in centavos
                        "fee": 500,  # 5.00 reais fee
                        "status": "paid",
                        "name": "João Silva",
                        "taxId": "123.456.789-09",
                        "created": "2026-02-14T08:00:00.000000+00:00",
                        "updated": "2026-02-15T10:30:00.000000+00:00",
                    },
                },
            }
        }

    def test_parse_invoice_webhook_payload(self, sample_invoice_webhook):
        """Test parsing a complete invoice webhook payload."""
        payload = InvoiceWebhookPayload.from_dict(sample_invoice_webhook)

        assert payload.invoice_id == "9876543210987654"
        assert payload.status == "credited"  # Event type, not invoice status
        assert payload.amount == 50000
        assert payload.fee == 500
        assert payload.name == "João Silva"
        assert payload.tax_id == "123.456.789-09"

    def test_invoice_amount_conversion(self, sample_invoice_webhook):
        """Test amount conversion from centavos to reais."""
        payload = InvoiceWebhookPayload.from_dict(sample_invoice_webhook)

        assert payload.amount == 50000
        assert payload.amount_decimal == 500.0
        assert payload.fee == 500
        assert payload.fee_decimal == 5.0

    def test_invoice_net_amount_calculation(self, sample_invoice_webhook):
        """Test net amount calculation."""
        payload = InvoiceWebhookPayload.from_dict(sample_invoice_webhook)

        assert payload.net_amount == 49500  # 50000 - 500
        assert payload.net_amount_decimal == 495.0

    def test_invoice_net_amount_without_fee(self):
        """Test net amount when fee is not present."""
        payload = {
            "event": {
                "id": "123",
                "subscription": "invoice",
                "log": {
                    "id": "456",
                    "type": "created",
                    "created": "2026-02-15T10:30:00Z",
                    "invoice": {
                        "id": "789",
                        "amount": 10000,
                        "status": "created",
                        # No fee field
                    },
                },
            }
        }

        invoice = InvoiceWebhookPayload.from_dict(payload)

        assert invoice.fee is None
        assert invoice.fee_decimal is None
        assert invoice.net_amount is None
        assert invoice.net_amount_decimal is None

    def test_parse_invoice_webhook_missing_invoice(self):
        """Test parsing fails when invoice data is missing."""
        payload = {
            "event": {
                "id": "123",
                "subscription": "invoice",
                "log": {
                    "id": "456",
                    "type": "credited",
                    "created": "2026-02-15T10:30:00Z",
                    # No invoice field
                },
            }
        }

        with pytest.raises(ValueError, match="Missing invoice data"):
            InvoiceWebhookPayload.from_dict(payload)

    def test_invoice_payload_to_dict(self, sample_invoice_webhook):
        """Test converting invoice payload to dictionary."""
        payload = InvoiceWebhookPayload.from_dict(sample_invoice_webhook)
        result = payload.to_dict()

        assert result["invoice_id"] == "9876543210987654"
        assert result["status"] == "credited"  # Event type, not invoice status
        assert result["amount"] == 50000
        assert result["amount_decimal"] == 500.0
        assert result["fee"] == 500
        assert result["fee_decimal"] == 5.0
        assert result["net_amount"] == 49500
        assert result["net_amount_decimal"] == 495.0


class TestTransferWebhookPayload:
    """Tests for TransferWebhookPayload dataclass."""

    @pytest.fixture
    def sample_transfer_success_webhook(self):
        """Sample successful transfer webhook payload."""
        return {
            "event": {
                "id": "1234567890123456",
                "subscription": "transfer",
                "log": {
                    "id": "5678901234567890",
                    "type": "success",
                    "created": "2026-02-15T14:00:00.000000+00:00",
                    "transfer": {
                        "id": "9876543210987654",
                        "amount": 49500,  # 495.00 reais
                        "status": "success",
                        "externalId": "invoice-abc123",
                        "bankCode": "20018183",
                        "branchCode": "0001",
                        "accountNumber": "6341320293482496",
                        "accountType": "payment",
                        "name": "Stark Bank S.A.",
                        "taxId": "20.018.183/0001-80",
                        "fee": 0,
                        "created": "2026-02-15T12:00:00.000000+00:00",
                        "updated": "2026-02-15T14:00:00.000000+00:00",
                    },
                },
            }
        }

    @pytest.fixture
    def sample_transfer_failed_webhook(self):
        """Sample failed transfer webhook payload."""
        return {
            "event": {
                "id": "1234567890123456",
                "subscription": "transfer",
                "log": {
                    "id": "5678901234567890",
                    "type": "failed",
                    "created": "2026-02-15T14:00:00.000000+00:00",
                    "errors": [
                        {
                            "code": "invalidAccountNumber",
                            "message": "Account number is invalid",
                        }
                    ],
                    "transfer": {
                        "id": "9876543210987654",
                        "amount": 49500,
                        "status": "failed",
                        "externalId": "invoice-abc123",
                        "bankCode": "20018183",
                        "branchCode": "0001",
                        "accountNumber": "invalid",
                        "accountType": "payment",
                        "name": "Stark Bank S.A.",
                        "taxId": "20.018.183/0001-80",
                        "created": "2026-02-15T12:00:00.000000+00:00",
                        "updated": "2026-02-15T14:00:00.000000+00:00",
                    },
                },
            }
        }

    def test_parse_transfer_success_webhook(self, sample_transfer_success_webhook):
        """Test parsing a successful transfer webhook."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_success_webhook)

        assert payload.transfer_id == "9876543210987654"
        assert payload.status == "success"
        assert payload.amount == 49500
        assert payload.external_id == "invoice-abc123"
        assert payload.bank_code == "20018183"
        assert payload.branch_code == "0001"
        assert payload.account_number == "6341320293482496"
        assert payload.account_type == "payment"
        assert payload.name == "Stark Bank S.A."
        assert payload.tax_id == "20.018.183/0001-80"

    def test_transfer_amount_conversion(self, sample_transfer_success_webhook):
        """Test amount conversion from centavos to reais."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_success_webhook)

        assert payload.amount == 49500
        assert payload.amount_decimal == 495.0

    def test_transfer_status_helpers_success(self, sample_transfer_success_webhook):
        """Test status helper properties for successful transfer."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_success_webhook)

        assert payload.is_successful is True
        assert payload.is_failed is False
        assert payload.is_processing is False

    def test_transfer_status_helpers_failed(self, sample_transfer_failed_webhook):
        """Test status helper properties for failed transfer."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_failed_webhook)

        assert payload.is_successful is False
        assert payload.is_failed is True
        assert payload.is_processing is False

    def test_transfer_status_helpers_processing(self):
        """Test status helper properties for processing transfer."""
        payload = {
            "event": {
                "id": "123",
                "subscription": "transfer",
                "log": {
                    "id": "456",
                    "type": "processing",
                    "created": "2026-02-15T10:30:00Z",
                    "transfer": {
                        "id": "789",
                        "amount": 10000,
                        "status": "processing",
                        "externalId": "test-123",
                    },
                },
            }
        }

        transfer = TransferWebhookPayload.from_dict(payload)

        assert transfer.is_successful is False
        assert transfer.is_failed is False
        assert transfer.is_processing is True

    def test_parse_transfer_error_info(self, sample_transfer_failed_webhook):
        """Test parsing error information from failed transfer."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_failed_webhook)

        assert payload.error_code == "invalidAccountNumber"
        assert payload.error_message == "Account number is invalid"

    def test_parse_transfer_no_errors(self, sample_transfer_success_webhook):
        """Test parsing transfer without error information."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_success_webhook)

        assert payload.error_code is None
        assert payload.error_message is None

    def test_parse_transfer_webhook_missing_transfer(self):
        """Test parsing fails when transfer data is missing."""
        payload = {
            "event": {
                "id": "123",
                "subscription": "transfer",
                "log": {
                    "id": "456",
                    "type": "success",
                    "created": "2026-02-15T10:30:00Z",
                    # No transfer field
                },
            }
        }

        with pytest.raises(ValueError, match="Missing transfer data"):
            TransferWebhookPayload.from_dict(payload)

    def test_transfer_payload_to_dict(self, sample_transfer_success_webhook):
        """Test converting transfer payload to dictionary."""
        payload = TransferWebhookPayload.from_dict(sample_transfer_success_webhook)
        result = payload.to_dict()

        assert result["transfer_id"] == "9876543210987654"
        assert result["status"] == "success"
        assert result["amount"] == 49500
        assert result["amount_decimal"] == 495.0
        assert result["external_id"] == "invoice-abc123"
        assert result["is_successful"] is True
        assert result["is_failed"] is False
        assert result["is_processing"] is False


class TestWebhookEventType:
    """Tests for WebhookEventType enum."""

    def test_invoice_event_types(self):
        """Test invoice-related event types exist."""
        assert WebhookEventType.INVOICE_CREATED == "created"
        assert WebhookEventType.INVOICE_CREDITED == "credited"
        assert WebhookEventType.INVOICE_CANCELED == "canceled"
        assert WebhookEventType.INVOICE_EXPIRED == "expired"

    def test_transfer_event_types(self):
        """Test transfer-related event types exist."""
        # TRANSFER_CREATED == "created" is intentional: Stark Bank sends "created"
        # for both invoice and transfer creations. Routing is done via 'subscription'.
        assert WebhookEventType.TRANSFER_CREATED == "created"
        assert WebhookEventType.TRANSFER_PROCESSING == "processing"
        assert WebhookEventType.TRANSFER_SUCCESS == "success"
        assert WebhookEventType.TRANSFER_FAILED == "failed"
