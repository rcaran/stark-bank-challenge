"""
API Key authentication module.

Provides secure API key validation using constant-time comparison
to prevent timing attacks, along with FastAPI dependencies for
easy integration with endpoints.
"""

import secrets

from fastapi import Header, HTTPException, status

from src.config.settings import settings
from src.shared.security.constants import API_KEY_HEADER_NAME
from src.shared.utils.errors import AuthenticationError
from src.shared.utils.logger import get_logger

logger = get_logger("security.api_key")


class InvalidAPIKeyError(AuthenticationError):
    """Raised when an invalid API key is provided."""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message)


def verify_api_key(api_key: str) -> bool:
    """
    Verify if the provided API key is valid.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        api_key: The API key to verify

    Returns:
        True if the API key is valid, False otherwise

    Example:
        >>> verify_api_key("valid-key")
        True
        >>> verify_api_key("invalid-key")
        False
    """
    if not api_key:
        logger.warning("API key verification failed: empty key provided")
        return False

    # Get the valid API key from settings
    valid_api_key = settings.admin_api_key

    if not valid_api_key:
        logger.error(
            "API key verification failed: "
            "ADMIN_API_KEY not configured in settings"
        )
        return False

    # Use secrets.compare_digest for constant-time comparison
    # This prevents timing attacks
    try:
        is_valid = secrets.compare_digest(api_key, valid_api_key)

        if is_valid:
            logger.info("API key verification successful")
        else:
            logger.warning("API key verification failed: key mismatch")

        return is_valid
    except Exception as e:
        logger.error(f"API key verification failed with exception: {e}")
        return False


def get_api_key_header(
    x_api_key: str | None = Header(None, alias=API_KEY_HEADER_NAME)
) -> str:
    """
    FastAPI dependency to extract and validate API key from request header.

    Args:
        x_api_key: The API key from the X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid (401 Unauthorized)

    Example:
        @app.get("/protected", dependencies=[Depends(get_api_key_header)])
        def protected_route():
            return {"message": "Access granted"}
    """
    if not x_api_key:
        logger.warning("API key missing in request header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not verify_api_key(x_api_key):
        logger.warning("Invalid API key attempt from header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# Alias for backward compatibility and cleaner imports
get_api_key_dependency = get_api_key_header


class APIKeyHeader:
    """
    Callable class for extracting API key from headers.

    Can be used as a dependency in FastAPI routes.

    Example:
        api_key_header = APIKeyHeader()

        @app.get("/protected")
        def protected_route(api_key: str = Depends(api_key_header)):
            return {"message": "Access granted"}
    """

    def __call__(
        self,
        x_api_key: str | None = Header(None, alias=API_KEY_HEADER_NAME)
    ) -> str:
        """
        Extract and validate API key from request header.

        Args:
            x_api_key: The API key from the X-API-Key header

        Returns:
            The validated API key

        Raises:
            HTTPException: If API key is missing or invalid
        """
        return get_api_key_header(x_api_key)
