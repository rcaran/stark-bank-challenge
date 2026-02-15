"""
Application constants.

This module contains configuration constants that are not environment-specific.
For environment variables, see settings.py.
For security constants, see shared/security/constants.py.
For event types, see shared/events/types.py.
"""

# Retry Configuration (used by stark/retry.py)
# Default delays between retry attempts in seconds
RETRY_DELAYS = [0, 60, 120, 240, 480]
RETRY_MAX_ATTEMPTS = 5

# Stark Bank Environment Values
STARKBANK_ENV_SANDBOX = "sandbox"
STARKBANK_ENV_PRODUCTION = "production"
