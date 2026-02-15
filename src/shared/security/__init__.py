"""
Security module for API authentication and webhook validation.
"""

from src.shared.security.api_key import (
    APIKeyHeader,
    InvalidAPIKeyError,
    get_api_key_dependency,
    get_api_key_header,
    verify_api_key,
)
from src.shared.security.signature import (
    InvalidSignatureError,
    compute_payload_hash,
    validate_webhook_signature,
    verify_webhook_signature,
)

__all__ = [
    # API Key
    "verify_api_key",
    "get_api_key_header",
    "get_api_key_dependency",
    "APIKeyHeader",
    "InvalidAPIKeyError",
    # Signature
    "validate_webhook_signature",
    "verify_webhook_signature",
    "compute_payload_hash",
    "InvalidSignatureError",
]
