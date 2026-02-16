"""Unit tests for WebhookValidator."""

from unittest.mock import MagicMock, patch

import pytest

from src.modules.webhooks.validator import WebhookValidator
from src.shared.security.signature import InvalidSignatureError


class TestWebhookValidator:
    """Tests for WebhookValidator class."""

    def test_init_default_public_key(self):
        """Test validator initializes with default public key."""
        validator = WebhookValidator()

        assert validator._public_key_pem is None

    def test_init_custom_public_key(self):
        """Test validator initializes with custom public key."""
        custom_key = "-----BEGIN PUBLIC KEY-----\ncustom\n-----END PUBLIC KEY-----"
        validator = WebhookValidator(public_key_pem=custom_key)

        assert validator._public_key_pem == custom_key

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_valid(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature returns True for valid signature."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = True

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        result = validator.validate_signature(payload, signature)

        assert result is True
        mock_validate.assert_called_once_with(
            payload=payload,
            signature=signature,
            public_key_pem=None,
        )

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_invalid(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature returns False for invalid signature."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = False

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "invalid_signature"

        result = validator.validate_signature(payload, signature)

        assert result is False
        mock_validate.assert_called_once()

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_with_custom_public_key(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature uses custom public key when provided."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = True

        custom_key = "-----BEGIN PUBLIC KEY-----\ncustom\n-----END PUBLIC KEY-----"
        validator = WebhookValidator(public_key_pem=custom_key)
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        result = validator.validate_signature(payload, signature)

        assert result is True
        mock_validate.assert_called_once_with(
            payload=payload,
            signature=signature,
            public_key_pem=custom_key,
        )

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_exception_returns_false(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature returns False when exception occurs."""
        mock_hash.return_value = "abc123"
        mock_validate.side_effect = Exception("Unexpected error")

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        result = validator.validate_signature(payload, signature)

        assert result is False

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_empty_payload(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature handles empty payload."""
        mock_validate.return_value = False

        validator = WebhookValidator()
        payload = b""
        signature = "MEUCIQDaP..."

        result = validator.validate_signature(payload, signature)

        assert result is False

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_validate_signature_empty_signature(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test validate_signature handles empty signature."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = False

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = ""

        result = validator.validate_signature(payload, signature)

        assert result is False


class TestWebhookValidatorVerify:
    """Tests for WebhookValidator.verify_signature method."""

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_verify_signature_valid_does_not_raise(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test verify_signature does not raise for valid signature."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = True

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        # Should not raise any exception
        validator.verify_signature(payload, signature)

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_verify_signature_invalid_raises_exception(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test verify_signature raises InvalidSignatureError for invalid signature."""
        mock_hash.return_value = "abc123"
        mock_validate.return_value = False

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "invalid_signature"

        with pytest.raises(InvalidSignatureError):
            validator.verify_signature(payload, signature)

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    def test_verify_signature_exception_raises_invalid_signature(
        self, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test verify_signature raises InvalidSignatureError when exception occurs."""
        mock_hash.return_value = "abc123"
        mock_validate.side_effect = Exception("Unexpected error")

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        with pytest.raises(InvalidSignatureError):
            validator.verify_signature(payload, signature)


class TestWebhookValidatorLogging:
    """Tests for WebhookValidator logging behavior."""

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    @patch("src.modules.webhooks.validator.get_logger")
    def test_logs_validation_attempt(
        self, mock_get_logger: MagicMock, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test that validation attempts are logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_hash.return_value = "abc123"
        mock_validate.return_value = True

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        validator.validate_signature(payload, signature)

        # Check that info was logged (validation start)
        assert mock_logger.info.call_count >= 1

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    @patch("src.modules.webhooks.validator.get_logger")
    def test_logs_validation_success(
        self, mock_get_logger: MagicMock, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test that successful validation is logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_hash.return_value = "abc123"
        mock_validate.return_value = True

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        validator.validate_signature(payload, signature)

        # Should log success
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("successful" in str(call).lower() for call in info_calls)

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    @patch("src.modules.webhooks.validator.get_logger")
    def test_logs_validation_failure(
        self, mock_get_logger: MagicMock, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test that failed validation is logged as warning."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_hash.return_value = "abc123"
        mock_validate.return_value = False

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "invalid"

        validator.validate_signature(payload, signature)

        # Should log warning for failure
        assert mock_logger.warning.call_count >= 1

    @patch("src.modules.webhooks.validator.validate_webhook_signature")
    @patch("src.modules.webhooks.validator.compute_payload_hash")
    @patch("src.modules.webhooks.validator.get_logger")
    def test_logs_validation_error(
        self, mock_get_logger: MagicMock, mock_hash: MagicMock, mock_validate: MagicMock
    ):
        """Test that validation errors are logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_hash.return_value = "abc123"
        mock_validate.side_effect = Exception("Test error")

        validator = WebhookValidator()
        payload = b'{"event": {"log": {}}}'
        signature = "MEUCIQDaP..."

        validator.validate_signature(payload, signature)

        # Should log error
        assert mock_logger.error.call_count >= 1
