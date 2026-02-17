"""
Unit tests for WebhookReceiver.

Tests the webhook receiver orchestration, including signature validation,
payload parsing, and routing to appropriate processors.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.modules.webhooks.receiver import WebhookReceiver
from src.shared.security.signature import InvalidSignatureError


@pytest.fixture
def mock_validator():
    """Mock webhook validator."""
    validator = Mock()
    validator.verify_signature = Mock()
    return validator


@pytest.fixture
def mock_invoice_processor():
    """Mock invoice webhook processor."""
    processor = Mock()
    processor.process = Mock()
    return processor


@pytest.fixture
def mock_transfer_processor():
    """Mock transfer webhook processor."""
    processor = Mock()
    processor.process = Mock()
    return processor


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = Mock()
    bus.publish = Mock()
    return bus


@pytest.fixture
def webhook_receiver(
    mock_validator, mock_invoice_processor, mock_transfer_processor, mock_event_bus
):
    """Create WebhookReceiver instance with mocked dependencies."""
    return WebhookReceiver(
        validator=mock_validator,
        invoice_processor=mock_invoice_processor,
        transfer_processor=mock_transfer_processor,
        event_bus=mock_event_bus,
    )


@pytest.fixture
def sample_invoice_webhook_payload():
    """Sample invoice webhook payload."""
    return {
        "event": {
            "id": "6589898251476992",
            "subscription": "invoice",
            "log": {
                "id": "5123328385236992",
                "created": "2024-01-15T10:30:00.000000+00:00",
                "type": "credited",
                "invoice": {
                    "id": "5730903989420032",
                    "amount": 50000,
                    "fee": 200,
                    "status": "paid",
                    "name": "João Silva",
                    "taxId": "012.345.678-90",
                },
            },
        }
    }


@pytest.fixture
def sample_transfer_webhook_payload():
    """Sample transfer webhook payload."""
    return {
        "event": {
            "id": "7589898251476992",
            "subscription": "transfer",
            "log": {
                "id": "6123328385236992",
                "created": "2024-01-15T11:30:00.000000+00:00",
                "type": "success",
                "transfer": {
                    "id": "6730903989420032",
                    "amount": 49800,
                    "status": "success",
                    "externalId": "invoice-12345",
                },
            },
        }
    }


class TestReceiveInvoiceWebhook:
    """Tests for receive_invoice_webhook method."""

    def test_receive_invoice_webhook_success(
        self,
        webhook_receiver,
        mock_validator,
        mock_invoice_processor,
        sample_invoice_webhook_payload,
    ):
        """Test successful invoice webhook reception and processing."""
        # Arrange
        payload = json.dumps(sample_invoice_webhook_payload).encode("utf-8")
        signature = "valid_signature"

        # Validator should succeed (no exception)
        mock_validator.verify_signature.return_value = None

        # Act
        result = webhook_receiver.receive_invoice_webhook(payload, signature)

        # Assert
        assert result == {"status": "ok"}
        mock_validator.verify_signature.assert_called_once_with(payload, signature)
        mock_invoice_processor.process.assert_called_once()

    def test_receive_invoice_webhook_invalid_signature(
        self, webhook_receiver, mock_validator, mock_invoice_processor, mock_event_bus
    ):
        """Test invoice webhook with invalid signature raises exception."""
        # Arrange
        payload = b'{"event": {"log": {}}}'
        signature = "invalid_signature"

        # Validator should raise InvalidSignatureError
        mock_validator.verify_signature.side_effect = InvalidSignatureError(
            "Invalid signature"
        )

        # Act & Assert
        with pytest.raises(InvalidSignatureError):
            webhook_receiver.receive_invoice_webhook(payload, signature)

        # Processor should not be called
        mock_invoice_processor.process.assert_not_called()

        # Validation failed event should be published
        mock_event_bus.publish.assert_called_once()

    def test_receive_invoice_webhook_processing_error(
        self,
        webhook_receiver,
        mock_validator,
        mock_invoice_processor,
        sample_invoice_webhook_payload,
    ):
        """Test invoice webhook returns success even when processing fails."""
        # Arrange
        payload = json.dumps(sample_invoice_webhook_payload).encode("utf-8")
        signature = "valid_signature"

        # Validator succeeds
        mock_validator.verify_signature.return_value = None

        # Processor raises exception
        mock_invoice_processor.process.side_effect = Exception("Database error")

        # Act
        result = webhook_receiver.receive_invoice_webhook(payload, signature)

        # Assert - should return success despite processing error
        assert result["status"] == "ok"
        assert "error" in result
        mock_validator.verify_signature.assert_called_once()
        mock_invoice_processor.process.assert_called_once()

    def test_receive_invoice_webhook_invalid_payload(
        self, webhook_receiver, mock_validator, mock_invoice_processor
    ):
        """Test invoice webhook with invalid JSON payload."""
        # Arrange
        payload = b"invalid json"
        signature = "valid_signature"

        # Validator succeeds
        mock_validator.verify_signature.return_value = None

        # Act
        result = webhook_receiver.receive_invoice_webhook(payload, signature)

        # Assert - should return success with error flag
        assert result["status"] == "ok"
        assert "error" in result
        mock_validator.verify_signature.assert_called_once()
        mock_invoice_processor.process.assert_not_called()


class TestReceiveTransferWebhook:
    """Tests for receive_transfer_webhook method."""

    def test_receive_transfer_webhook_success(
        self,
        webhook_receiver,
        mock_validator,
        mock_transfer_processor,
        sample_transfer_webhook_payload,
    ):
        """Test successful transfer webhook reception and processing."""
        # Arrange
        payload = json.dumps(sample_transfer_webhook_payload).encode("utf-8")
        signature = "valid_signature"

        # Validator should succeed (no exception)
        mock_validator.verify_signature.return_value = None

        # Act
        result = webhook_receiver.receive_transfer_webhook(payload, signature)

        # Assert
        assert result == {"status": "ok"}
        mock_validator.verify_signature.assert_called_once_with(payload, signature)
        mock_transfer_processor.process.assert_called_once()

    def test_receive_transfer_webhook_invalid_signature(
        self, webhook_receiver, mock_validator, mock_transfer_processor, mock_event_bus
    ):
        """Test transfer webhook with invalid signature raises exception."""
        # Arrange
        payload = b'{"event": {"log": {}}}'
        signature = "invalid_signature"

        # Validator should raise InvalidSignatureError
        mock_validator.verify_signature.side_effect = InvalidSignatureError(
            "Invalid signature"
        )

        # Act & Assert
        with pytest.raises(InvalidSignatureError):
            webhook_receiver.receive_transfer_webhook(payload, signature)

        # Processor should not be called
        mock_transfer_processor.process.assert_not_called()

        # Validation failed event should be published
        mock_event_bus.publish.assert_called_once()

    def test_receive_transfer_webhook_processing_error(
        self,
        webhook_receiver,
        mock_validator,
        mock_transfer_processor,
        sample_transfer_webhook_payload,
    ):
        """Test transfer webhook returns success even when processing fails."""
        # Arrange
        payload = json.dumps(sample_transfer_webhook_payload).encode("utf-8")
        signature = "valid_signature"

        # Validator succeeds
        mock_validator.verify_signature.return_value = None

        # Processor raises exception
        mock_transfer_processor.process.side_effect = Exception("Database error")

        # Act
        result = webhook_receiver.receive_transfer_webhook(payload, signature)

        # Assert - should return success despite processing error
        assert result["status"] == "ok"
        assert "error" in result
        mock_validator.verify_signature.assert_called_once()
        mock_transfer_processor.process.assert_called_once()

    def test_receive_transfer_webhook_invalid_payload(
        self, webhook_receiver, mock_validator, mock_transfer_processor
    ):
        """Test transfer webhook with invalid JSON payload."""
        # Arrange
        payload = b"invalid json"
        signature = "valid_signature"

        # Validator succeeds
        mock_validator.verify_signature.return_value = None

        # Act
        result = webhook_receiver.receive_transfer_webhook(payload, signature)

        # Assert - should return success with error flag
        assert result["status"] == "ok"
        assert "error" in result
        mock_validator.verify_signature.assert_called_once()
        mock_transfer_processor.process.assert_not_called()


class TestWebhookReceiverLogging:
    """Tests for logging behavior."""

    @patch("src.modules.webhooks.receiver.logger")
    def test_logs_invoice_webhook_reception(
        self,
        mock_logger,
        webhook_receiver,
        mock_validator,
        sample_invoice_webhook_payload,
    ):
        """Test that invoice webhook reception is logged."""
        # Arrange
        payload = json.dumps(sample_invoice_webhook_payload).encode("utf-8")
        signature = "valid_signature"
        mock_validator.verify_signature.return_value = None

        # Act
        webhook_receiver.receive_invoice_webhook(payload, signature)

        # Assert
        assert mock_logger.info.called

    @patch("src.modules.webhooks.receiver.logger")
    def test_logs_transfer_webhook_reception(
        self,
        mock_logger,
        webhook_receiver,
        mock_validator,
        sample_transfer_webhook_payload,
    ):
        """Test that transfer webhook reception is logged."""
        # Arrange
        payload = json.dumps(sample_transfer_webhook_payload).encode("utf-8")
        signature = "valid_signature"
        mock_validator.verify_signature.return_value = None

        # Act
        webhook_receiver.receive_transfer_webhook(payload, signature)

        # Assert
        assert mock_logger.info.called

    @patch("src.modules.webhooks.receiver.logger")
    def test_logs_validation_failure(
        self, mock_logger, webhook_receiver, mock_validator
    ):
        """Test that validation failures are logged."""
        # Arrange
        payload = b'{"event": {}}'
        signature = "invalid_signature"
        mock_validator.verify_signature.side_effect = InvalidSignatureError(
            "Invalid signature"
        )

        # Act & Assert
        with pytest.raises(InvalidSignatureError):
            webhook_receiver.receive_invoice_webhook(payload, signature)

        # Should log warning
        assert mock_logger.warning.called
