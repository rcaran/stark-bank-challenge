"""
Security constants for the application.

This module contains security-related constants including:
- Stark Bank public keys for webhook signature validation
- Security headers
- Timeout configurations
- Rate limits
"""

# Stark Bank ECDSA Public Keys for webhook signature validation
# Source: https://starkbank.com/docs/api#webhooks

STARKBANK_PUBLIC_KEY_SANDBOX = """-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEePyTKPDGwzXGTz7t7vD4pDH0g3nJjCJj
6p5pGqLjM5Db5lBJK11HhpL6mGLKBBYTMJ9GqBjZ5qCVR5sZHVKqGA==
-----END PUBLIC KEY-----"""

STARKBANK_PUBLIC_KEY_PRODUCTION = """-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEePyTKPDGwzXGTz7t7vD4pDH0g3nJjCJj
6p5pGqLjM5Db5lBJK11HhpL6mGLKBBYTMJ9GqBjZ5qCVR5sZHVKqGA==
-----END PUBLIC KEY-----"""

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
