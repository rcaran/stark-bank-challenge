"""
Unit tests for webhook signature validation module.
"""

import base64
from unittest.mock import patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from src.shared.security.constants import (
    STARKBANK_PUBLIC_KEY_PRODUCTION,
    STARKBANK_PUBLIC_KEY_SANDBOX,
)
from src.shared.security.signature import (
    InvalidSignatureError,
    _get_public_key_pem,
    _load_public_key,
    compute_payload_hash,
    validate_webhook_signature,
    verify_webhook_signature,
)
from src.shared.utils.errors import ValidationError


# Generate test key pair for testing
def generate_test_keypair():
    """Generate a test ECDSA key pair for testing."""
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    return private_key, public_pem


def sign_payload(private_key, payload: bytes) -> str:
    """Sign a payload and return base64-encoded signature."""
    signature = private_key.sign(
        payload,
        ec.ECDSA(hashes.SHA256())
    )
    return base64.b64encode(signature).decode("utf-8")


class TestGetPublicKeyPem:
    """Tests for _get_public_key_pem function."""

    def test_get_public_key_sandbox(self):
        """Test that sandbox public key is returned for sandbox environment."""
        with patch("src.shared.security.signature.settings") as mock_settings:
            mock_settings.starkbank_environment = "sandbox"

            result = _get_public_key_pem()

            assert result == STARKBANK_PUBLIC_KEY_SANDBOX

    def test_get_public_key_production(self):
        """Test that production public key is returned for production environment."""
        with patch("src.shared.security.signature.settings") as mock_settings:
            mock_settings.starkbank_environment = "production"

            result = _get_public_key_pem()

            assert result == STARKBANK_PUBLIC_KEY_PRODUCTION


class TestLoadPublicKey:
    """Tests for _load_public_key function."""

    def test_load_valid_public_key(self):
        """Test loading a valid PEM-encoded public key."""
        _, public_pem = generate_test_keypair()

        public_key = _load_public_key(public_pem)

        assert public_key is not None
        assert isinstance(public_key, ec.EllipticCurvePublicKey)

    def test_load_invalid_public_key(self):
        """Test that loading an invalid key raises ValueError."""
        invalid_pem = "-----BEGIN PUBLIC KEY-----\nINVALID\n-----END PUBLIC KEY-----"

        with pytest.raises(ValueError) as exc_info:
            _load_public_key(invalid_pem)

        assert "Invalid public key format" in str(exc_info.value)


class TestValidateWebhookSignature:
    """Tests for validate_webhook_signature function."""

    def test_validate_valid_signature(self):
        """Test that a valid signature is accepted."""
        # Generate test keypair
        private_key, public_pem = generate_test_keypair()

        # Create payload and signature
        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        # Validate
        result = validate_webhook_signature(payload, signature, public_pem)

        assert result is True

    def test_validate_invalid_signature(self):
        """Test that an invalid signature is rejected."""
        # Generate test keypair
        private_key, public_pem = generate_test_keypair()

        # Create payload and signature
        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        # Modify payload (signature will be invalid)
        modified_payload = b'{"event": {"log": {"id": "456"}}}'

        # Validate
        result = validate_webhook_signature(modified_payload, signature, public_pem)

        assert result is False

    def test_validate_empty_payload(self):
        """Test that empty payload is rejected."""
        _, public_pem = generate_test_keypair()

        result = validate_webhook_signature(b"", "signature", public_pem)

        assert result is False

    def test_validate_empty_signature(self):
        """Test that empty signature is rejected."""
        _, public_pem = generate_test_keypair()

        result = validate_webhook_signature(b"payload", "", public_pem)

        assert result is False

    def test_validate_invalid_base64_signature(self):
        """Test that invalid base64 signature is rejected."""
        _, public_pem = generate_test_keypair()

        payload = b'{"event": {"log": {"id": "123"}}}'
        invalid_signature = "not-valid-base64!@#$"

        result = validate_webhook_signature(payload, invalid_signature, public_pem)

        assert result is False

    def test_validate_with_default_public_key(self):
        """Test validation using default public key from settings."""
        with patch("src.shared.security.signature._get_public_key_pem") as mock_get_key:
            private_key, public_pem = generate_test_keypair()
            mock_get_key.return_value = public_pem

            payload = b'{"event": {"log": {"id": "123"}}}'
            signature = sign_payload(private_key, payload)

            # Validate without providing public_key_pem (should use default)
            result = validate_webhook_signature(payload, signature)

            assert result is True
            mock_get_key.assert_called_once()

    def test_validate_exception_handling(self):
        """Test that exceptions during validation are handled gracefully."""
        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = "valid-base64-signature"

        # Use invalid public key to trigger exception
        invalid_pem = "-----BEGIN PUBLIC KEY-----\nINVALID\n-----END PUBLIC KEY-----"

        result = validate_webhook_signature(payload, signature, invalid_pem)

        assert result is False

    def test_validate_logging_success(self, caplog):
        """Test that successful validation is logged."""
        private_key, public_pem = generate_test_keypair()

        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        validate_webhook_signature(payload, signature, public_pem)

        # Check that success was logged
        assert any("successful" in record.message.lower() for record in caplog.records)

    def test_validate_logging_failure(self, caplog):
        """Test that failed validation is logged."""
        private_key, public_pem = generate_test_keypair()

        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        # Modify payload (signature will be invalid)
        modified_payload = b'{"event": {"log": {"id": "456"}}}'

        validate_webhook_signature(modified_payload, signature, public_pem)

        # Check that failure was logged
        assert any(
            "failed" in record.message.lower()
            or "does not match" in record.message.lower()
            for record in caplog.records
        )


class TestVerifyWebhookSignature:
    """Tests for verify_webhook_signature function."""

    def test_verify_valid_signature(self):
        """Test that valid signature does not raise exception."""
        private_key, public_pem = generate_test_keypair()

        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        # Should not raise
        verify_webhook_signature(payload, signature, public_pem)

    def test_verify_invalid_signature_raises(self):
        """Test that invalid signature raises InvalidSignatureError."""
        private_key, public_pem = generate_test_keypair()

        payload = b'{"event": {"log": {"id": "123"}}}'
        signature = sign_payload(private_key, payload)

        # Modify payload
        modified_payload = b'{"event": {"log": {"id": "456"}}}'

        with pytest.raises(InvalidSignatureError) as exc_info:
            verify_webhook_signature(modified_payload, signature, public_pem)

        assert "verification failed" in str(exc_info.value).lower()


class TestComputePayloadHash:
    """Tests for compute_payload_hash function."""

    def test_compute_hash_consistent(self):
        """Test that same payload produces same hash."""
        payload = b'{"event": {"log": {"id": "123"}}}'

        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)

        assert hash1 == hash2

    def test_compute_hash_different_payloads(self):
        """Test that different payloads produce different hashes."""
        payload1 = b'{"event": {"log": {"id": "123"}}}'
        payload2 = b'{"event": {"log": {"id": "456"}}}'

        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)

        assert hash1 != hash2

    def test_compute_hash_hex_format(self):
        """Test that hash is returned in hex format."""
        payload = b'{"event": {"log": {"id": "123"}}}'

        hash_result = compute_payload_hash(payload)

        # SHA-256 hex digest is 64 characters
        assert len(hash_result) == 64
        # Should only contain hex characters
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestInvalidSignatureError:
    """Tests for InvalidSignatureError exception."""

    def test_invalid_signature_error_inheritance(self):
        """Test that InvalidSignatureError inherits from ValidationError."""
        error = InvalidSignatureError()

        assert isinstance(error, ValidationError)
        assert isinstance(error, Exception)

    def test_invalid_signature_error_default_message(self):
        """Test default error message."""
        error = InvalidSignatureError()

        assert "Invalid webhook signature" in str(error)

    def test_invalid_signature_error_custom_message(self):
        """Test custom error message."""
        error = InvalidSignatureError("Custom error message")

        assert "Custom error message" in str(error)
