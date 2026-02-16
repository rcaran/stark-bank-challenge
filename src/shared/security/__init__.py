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
    "APIKeyHeader",
    "InvalidAPIKeyError",
    "InvalidSignatureError",
    "compute_payload_hash",
    "get_api_key_dependency",
    "get_api_key_header",
    # Signature
    "validate_webhook_signature",
    # API Key
    "verify_api_key",
    "verify_webhook_signature",
]
