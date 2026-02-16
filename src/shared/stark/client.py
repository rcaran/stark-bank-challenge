import logging

import starkbank
from starkbank.error import InputErrors, InternalServerError

from src.config.settings import settings
from src.shared.utils.errors import (
    AuthenticationError,
    StarkBankError,
    ValidationError,
)

logger = logging.getLogger(__name__)

class StarkBankClient:
    _instance: StarkBankClient | None = None
    _user: starkbank.Project | None = None

    def __init__(self):
        self.project_id = settings.starkbank_project_id
        self.private_key_content = settings.starkbank_private_key_content
        self.environment = settings.starkbank_environment

        if not self.project_id or not self.private_key_content:
            logger.warning("Stark Bank credentials not fully configured.")

    def _initialize_sdk(self):
        """Initializes the Stark Bank SDK with the Project user."""
        try:
            if self._user is None and self.project_id and self.private_key_content:
                self._user = starkbank.Project(
                    environment=self.environment,
                    id=self.project_id,
                    private_key=self.private_key_content
                )
                starkbank.user = self._user  # Set default user for the SDK
                logger.info(
                    f"Stark Bank SDK initialized for project {self.project_id} "
                    f"in {self.environment}"
                )
        except Exception as e:
            logger.error(f"Failed to initialize Stark Bank SDK: {e}")
            raise AuthenticationError(
                f"Failed to initialize Stark Bank SDK: {e!s}"
            ) from e

    @property
    def check_user(self):
         if not starkbank.user:
             self._initialize_sdk()
         return starkbank.user

    def handle_stark_error(self, e: Exception) -> None:
        """
        Maps Stark Bank exceptions to domain exceptions.
        """
        logger.error(f"Stark Bank API Error: {e}")

        if isinstance(e, InputErrors):
            # InputErrors contains list of errors.
            details = {"errors": [err.message for err in e.errors]}
            raise ValidationError(
                f"Stark Bank Validation Error: {e}", details=details
            ) from e

        if isinstance(e, InternalServerError):
            # This might be retriable
             raise StarkBankError(f"Stark Bank Internal Error: {e}") from e

        # General fallback
        raise StarkBankError(f"Stark Bank Error: {e}") from e


_client: StarkBankClient | None = None


def get_client() -> StarkBankClient:
    """Lazy singleton accessor for StarkBankClient."""
    global _client
    if _client is None:
        _client = StarkBankClient()
    return _client
