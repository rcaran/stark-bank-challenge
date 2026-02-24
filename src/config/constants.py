"""
Application constants.

This module contains configuration constants that are not environment-specific.
For environment variables, see settings.py.
For event types, see shared/events/types.py.
"""

# Retry Configuration (used by stark/retry.py)
# Default delays between retry attempts in seconds
RETRY_DELAYS = [0, 60, 120, 240, 480]
RETRY_MAX_ATTEMPTS = 5

# Stark Bank Environment Values
STARKBANK_ENV_SANDBOX = "sandbox"
STARKBANK_ENV_PRODUCTION = "production"

# Stark Bank Destination Account (for transfers)
STARKBANK_DESTINATION_BANK_CODE = "20018183"
STARKBANK_DESTINATION_BRANCH_CODE = "0001"
STARKBANK_DESTINATION_ACCOUNT_NUMBER = "6341320293482496"
STARKBANK_DESTINATION_NAME = "Stark Bank S.A."
STARKBANK_DESTINATION_TAX_ID = "20018183000180"
STARKBANK_DESTINATION_ACCOUNT_TYPE = "payment"
