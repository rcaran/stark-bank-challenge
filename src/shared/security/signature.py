"""
Webhook signature validation module.

Provides ECDSA signature validation for Stark Bank webhooks
to ensure authenticity and integrity of webhook payloads.
"""

import base64
import hashlib

from cryptography.exceptions import (
    InvalidSignature as CryptoInvalidSignature,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from src.config.constants import STARKBANK_ENV_SANDBOX
from src.config.settings import settings
from src.shared.security.constants import (
    STARKBANK_PUBLIC_KEY_PRODUCTION,
    STARKBANK_PUBLIC_KEY_SANDBOX,
)
from src.shared.utils.errors import ValidationError
from src.shared.utils.logger import get_logger

logger = get_logger("security.signature")


class InvalidSignatureError(ValidationError):
    """Raised when webhook signature validation fails."""
    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message)


def _get_public_key_pem() -> str:
    """
    Get the appropriate Stark Bank public key based on environment.

    Returns:
        The PEM-encoded public key string
    """
    if settings.starkbank_environment == STARKBANK_ENV_SANDBOX:
        return STARKBANK_PUBLIC_KEY_SANDBOX
    return STARKBANK_PUBLIC_KEY_PRODUCTION


def _load_public_key(public_key_pem: str) -> ec.EllipticCurvePublicKey:
    """
    Load an ECDSA public key from PEM format.

    Args:
        public_key_pem: The PEM-encoded public key

    Returns:
        The loaded public key object

    Raises:
        ValueError: If the key cannot be loaded
    """
    try:
        return serialization.load_pem_public_key(
            public_key_pem.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Failed to load public key: {e}")
        raise ValueError(f"Invalid public key format: {e}") from e


def validate_webhook_signature(
    payload: bytes,
    signature: str,
    public_key_pem: str | None = None
) -> bool:
    """
    Validate a webhook signature using ECDSA.

    Stark Bank signs webhook payloads using ECDSA with SHA-256.
    The signature is base64-encoded and sent in the Digital-Signature header.

    Args:
        payload: The raw webhook payload (bytes)
        signature: The base64-encoded signature from the header
        public_key_pem: Optional custom public key (defaults to
            environment-based key)

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> payload = b'{"event": {"log": {...}}}'
        >>> signature = "MEUCIQDaP..."
        >>> validate_webhook_signature(payload, signature)
        True
    """
    if not payload:
        logger.warning("Signature validation failed: empty payload")
        return False

    if not signature:
        logger.warning("Signature validation failed: empty signature")
        return False

    try:
        # Get the public key
        if public_key_pem is None:
            public_key_pem = _get_public_key_pem()

        public_key = _load_public_key(public_key_pem)

        # Decode the base64 signature
        try:
            signature_bytes = base64.b64decode(signature)
        except Exception as e:
            logger.warning(
                f"Signature validation failed: invalid base64 encoding: {e}"
            )
            return False

        # Verify the signature
        # Stark Bank uses ECDSA with SHA-256
        try:
            public_key.verify(
                signature_bytes,
                payload,
                ec.ECDSA(hashes.SHA256())
            )
            logger.info("Webhook signature validation successful")
            return True

        except CryptoInvalidSignature:
            logger.warning(
                "Signature validation failed: signature does not match payload"
            )
            return False

    except Exception as e:
        logger.error(f"Signature validation failed with exception: {e}")
        return False


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    public_key_pem: str | None = None
) -> None:
    """
    Verify webhook signature and raise exception if invalid.

    Similar to validate_webhook_signature but raises an exception
    instead of returning a boolean.

    Args:
        payload: The raw webhook payload (bytes)
        signature: The base64-encoded signature from the header
        public_key_pem: Optional custom public key

    Raises:
        InvalidSignatureError: If the signature is invalid

    Example:
        >>> try:
        ...     verify_webhook_signature(payload, signature)
        ... except InvalidSignatureError:
        ...     print("Invalid signature")
    """
    is_valid = validate_webhook_signature(payload, signature, public_key_pem)

    if not is_valid:
        raise InvalidSignatureError("Webhook signature verification failed")


def compute_payload_hash(payload: bytes) -> str:
    """
    Compute SHA-256 hash of payload for logging/debugging.

    Args:
        payload: The raw payload bytes

    Returns:
        Hex-encoded SHA-256 hash

    Example:
        >>> compute_payload_hash(b'{"event": {...}}')
        'a3c4e5f...'
    """
    return hashlib.sha256(payload).hexdigest()
