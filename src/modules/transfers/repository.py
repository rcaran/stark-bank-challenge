"""
Transfer Repository.

This module provides database operations for transfers,
extending the BaseRepository with transfer-specific methods.
"""

from typing import List, Optional

from src.modules.transfers.models import TransferModel, TransferStatus
from src.shared.database.base_repository import BaseRepository
from src.shared.database.connection import DatabaseConnection
from src.shared.utils.errors import NotFoundError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.transfers.repository")


class TransferRepository(BaseRepository[TransferModel]):
    """Repository for transfer database operations."""

    def __init__(self, db_connection: DatabaseConnection = None):
        """
        Initialize TransferRepository.

        Args:
            db_connection: Optional database connection (uses singleton if not provided)
        """
        super().__init__(db_connection)
        logger.debug("TransferRepository initialized")

    def create(self, transfer: TransferModel) -> None:
        """
        Create a new transfer in the database.

        Args:
            transfer: TransferModel instance to persist

        Raises:
            Exception: If database operation fails
        """
        logger.info(f"Creating transfer: {transfer.id}")

        query = """
            INSERT INTO transfers (
                id, invoice_id, stark_transfer_id, external_id, amount,
                status, created_at, updated_at, completed_at,
                retry_count, last_retry_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            transfer.id,
            transfer.invoice_id,
            transfer.stark_transfer_id,
            transfer.external_id,
            transfer.amount,
            (
                transfer.status.value
                if isinstance(transfer.status, TransferStatus)
                else transfer.status
            ),
            transfer.created_at.isoformat() if transfer.created_at else None,
            transfer.updated_at.isoformat() if transfer.updated_at else None,
            transfer.completed_at.isoformat() if transfer.completed_at else None,
            transfer.retry_count,
            transfer.last_retry_at.isoformat() if transfer.last_retry_at else None,
            transfer.error_message,
        )

        self._execute(query, params)
        logger.info(f"Transfer created successfully: {transfer.id}")

    def get_by_id(self, transfer_id: str) -> Optional[TransferModel]:
        """
        Get a transfer by its internal ID.

        Args:
            transfer_id: Internal transfer ID

        Returns:
            TransferModel if found, None otherwise
        """
        logger.debug(f"Getting transfer by ID: {transfer_id}")

        query = """
            SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                   status, created_at, updated_at, completed_at,
                   retry_count, last_retry_at, error_message
            FROM transfers WHERE id = ?
        """

        row = self._fetchone(query, (transfer_id,))

        if not row:
            logger.debug(f"Transfer not found: {transfer_id}")
            return None

        return self._row_to_model(row)

    def get_by_stark_id(self, stark_id: str) -> Optional[TransferModel]:
        """
        Get a transfer by its Stark Bank ID.

        Args:
            stark_id: Stark Bank transfer ID

        Returns:
            TransferModel if found, None otherwise
        """
        logger.debug(f"Getting transfer by Stark ID: {stark_id}")

        query = """
            SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                   status, created_at, updated_at, completed_at,
                   retry_count, last_retry_at, error_message
            FROM transfers WHERE stark_transfer_id = ?
        """

        row = self._fetchone(query, (stark_id,))

        if not row:
            logger.debug(f"Transfer not found by Stark ID: {stark_id}")
            return None

        return self._row_to_model(row)

    def get_by_external_id(self, external_id: str) -> Optional[TransferModel]:
        """
        Get a transfer by its external ID (for idempotency).

        Args:
            external_id: External transfer ID used for idempotency

        Returns:
            TransferModel if found, None otherwise
        """
        logger.debug(f"Getting transfer by external ID: {external_id}")

        query = """
            SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                   status, created_at, updated_at, completed_at,
                   retry_count, last_retry_at, error_message
            FROM transfers WHERE external_id = ?
        """

        row = self._fetchone(query, (external_id,))

        if not row:
            logger.debug(f"Transfer not found by external ID: {external_id}")
            return None

        return self._row_to_model(row)

    def get_by_invoice_id(self, invoice_id: str) -> Optional[TransferModel]:
        """
        Get a transfer by its associated invoice ID.

        Args:
            invoice_id: Invoice ID

        Returns:
            TransferModel if found, None otherwise
        """
        logger.debug(f"Getting transfer by invoice ID: {invoice_id}")

        query = """
            SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                   status, created_at, updated_at, completed_at,
                   retry_count, last_retry_at, error_message
            FROM transfers WHERE invoice_id = ?
        """

        row = self._fetchone(query, (invoice_id,))

        if not row:
            logger.debug(f"Transfer not found by invoice ID: {invoice_id}")
            return None

        return self._row_to_model(row)

    def update(self, transfer: TransferModel) -> None:
        """
        Update an existing transfer in the database.

        Args:
            transfer: TransferModel instance with updated data

        Raises:
            NotFoundError: If transfer doesn't exist
        """
        logger.info(f"Updating transfer: {transfer.id}")

        # Check if exists first
        existing = self.get_by_id(transfer.id)
        if not existing:
            raise NotFoundError(f"Transfer not found: {transfer.id}")

        query = """
            UPDATE transfers SET
                invoice_id = ?,
                stark_transfer_id = ?,
                external_id = ?,
                amount = ?,
                status = ?,
                created_at = ?,
                updated_at = ?,
                completed_at = ?,
                retry_count = ?,
                last_retry_at = ?,
                error_message = ?
            WHERE id = ?
        """

        params = (
            transfer.invoice_id,
            transfer.stark_transfer_id,
            transfer.external_id,
            transfer.amount,
            (
                transfer.status.value
                if isinstance(transfer.status, TransferStatus)
                else transfer.status
            ),
            transfer.created_at.isoformat() if transfer.created_at else None,
            transfer.updated_at.isoformat() if transfer.updated_at else None,
            transfer.completed_at.isoformat() if transfer.completed_at else None,
            transfer.retry_count,
            transfer.last_retry_at.isoformat() if transfer.last_retry_at else None,
            transfer.error_message,
            transfer.id,
        )

        self._execute(query, params)
        logger.info(f"Transfer updated successfully: {transfer.id}")

    def list(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TransferModel]:
        """
        List transfers with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of TransferModel instances
        """
        logger.debug(
            f"Listing transfers: status={status}, limit={limit}, offset={offset}"
        )

        if status:
            query = """
                SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                       status, created_at, updated_at, completed_at,
                       retry_count, last_retry_at, error_message
                FROM transfers WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self._fetchall(query, (status, limit, offset))
        else:
            query = """
                SELECT id, invoice_id, stark_transfer_id, external_id, amount,
                       status, created_at, updated_at, completed_at,
                       retry_count, last_retry_at, error_message
                FROM transfers
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self._fetchall(query, (limit, offset))

        transfers = [self._row_to_model(row) for row in rows]
        logger.debug(f"Found {len(transfers)} transfers")
        return transfers

    def count(self, status: Optional[str] = None) -> int:
        """
        Count transfers with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            Number of transfers matching the criteria
        """
        logger.debug(f"Counting transfers: status={status}")

        if status:
            query = "SELECT COUNT(*) FROM transfers WHERE status = ?"
            row = self._fetchone(query, (status,))
        else:
            query = "SELECT COUNT(*) FROM transfers"
            row = self._fetchone(query)

        count = row[0] if row else 0
        logger.debug(f"Transfer count: {count}")
        return count

    def list_by_status(self, status: TransferStatus) -> List[TransferModel]:
        """
        List all transfers with a specific status.

        Args:
            status: Transfer status to filter by

        Returns:
            List of TransferModel instances
        """
        status_value = status.value if isinstance(status, TransferStatus) else status
        return self.list(status=status_value, limit=10000)

    def _row_to_model(self, row) -> TransferModel:
        """
        Convert a database row to a TransferModel.

        Args:
            row: Database row tuple

        Returns:
            TransferModel instance
        """
        return TransferModel.from_dict({
            "id": row[0],
            "invoice_id": row[1],
            "stark_transfer_id": row[2],
            "external_id": row[3],
            "amount": row[4],
            "status": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "completed_at": row[8],
            "retry_count": row[9],
            "last_retry_at": row[10],
            "error_message": row[11],
        })
