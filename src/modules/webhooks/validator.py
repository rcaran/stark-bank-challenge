"""
Webhook signature validator module.

Provides a wrapper class for validating Stark Bank webhook signatures,
with structured logging and exception handling.
"""

from src.shared.security.signature import (
    InvalidSignatureError,
    compute_payload_hash,
    validate_webhook_signature,
)
from src.shared.utils.logger import get_logger


class WebhookValidator:
    """
    Validator for Stark Bank webhook signatures.

    This class wraps the core signature validation functionality,
    providing structured logging and consistent exception handling.

    Example:
        >>> validator = WebhookValidator()
        >>> is_valid = validator.validate_signature(payload, signature)
        >>> if not is_valid:
        ...     print("Invalid signature")
    """

    def __init__(self, public_key_pem: str | None = None):
        """
        Initialize the webhook validator.

        Args:
            public_key_pem: Optional custom public key PEM. If not provided,
                            uses the environment-based Stark Bank public key.
        """
        self._logger = get_logger("webhooks.validator")
        self._public_key_pem = public_key_pem

    def validate_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Validate a webhook signature.

        Args:
            payload: The raw webhook payload (bytes)
            signature: The base64-encoded signature from the Digital-Signature header

        Returns:
            True if signature is valid, False otherwise

        Example:
            >>> validator = WebhookValidator()
            >>> payload = b'{"event": {"log": {...}}}'
            >>> signature = "MEUCIQDaP..."
            >>> validator.validate_signature(payload, signature)
            True
        """
        payload_hash = compute_payload_hash(payload) if payload else "empty"

        self._logger.info(
            "Validating webhook signature",
            payload_hash=payload_hash,
            payload_size=len(payload) if payload else 0,
            has_signature=bool(signature),
        )

        try:
            is_valid = validate_webhook_signature(
                payload=payload,
                signature=signature,
                public_key_pem=self._public_key_pem,
            )

            if is_valid:
                self._logger.info(
                    "Webhook signature validation successful",
                    payload_hash=payload_hash,
                )
            else:
                self._logger.warning(
                    "Webhook signature validation failed",
                    payload_hash=payload_hash,
                )

            return is_valid

        except Exception as e:
            self._logger.error(
                "Webhook signature validation error",
                error=str(e),
                error_type=type(e).__name__,
                payload_hash=payload_hash,
            )
            return False

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> None:
        """
        Verify a webhook signature, raising an exception if invalid.

        Args:
            payload: The raw webhook payload (bytes)
            signature: The base64-encoded signature from the Digital-Signature header

        Raises:
            InvalidSignatureError: If the signature is invalid

        Example:
            >>> validator = WebhookValidator()
            >>> try:
            ...     validator.verify_signature(payload, signature)
            ...     print("Signature is valid")
            ... except InvalidSignatureError:
            ...     print("Invalid signature")
        """
        is_valid = self.validate_signature(payload, signature)

        if not is_valid:
            self._logger.warning(
                "Webhook signature verification failed - raising exception",
                payload_hash=compute_payload_hash(payload) if payload else "empty",
            )
            raise InvalidSignatureError("Webhook signature verification failed")
