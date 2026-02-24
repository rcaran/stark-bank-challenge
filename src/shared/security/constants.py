"""
Security constants for the application.

This module contains security-related constants including:
- Security headers
- Timeout configurations
- Rate limits
"""

# Security Headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}

# API Key Header
API_KEY_HEADER_NAME = "X-API-Key"

# Webhook Signature Header (Stark Bank)
WEBHOOK_SIGNATURE_HEADER = "Digital-Signature"

# Request Timeouts (in seconds)
REQUEST_TIMEOUT_DEFAULT = 30
REQUEST_TIMEOUT_LONG = 60

# Rate Limits (requests per minute)
RATE_LIMIT_DEFAULT = 60
RATE_LIMIT_WEBHOOK = 100  # Webhooks may have higher rate

# Constant-time comparison threshold (to prevent timing attacks)
CONSTANT_TIME_COMPARE_LENGTH = 64  # Max API key length in bytes
