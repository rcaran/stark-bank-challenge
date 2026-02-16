"""
Invoice Repository.

This module provides database operations for invoices,
extending the BaseRepository with invoice-specific methods.
"""

from typing import List, Optional

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.shared.database.base_repository import BaseRepository
from src.shared.database.connection import DatabaseConnection
from src.shared.utils.errors import NotFoundError
from src.shared.utils.logger import get_logger

logger = get_logger("modules.invoices.repository")


class InvoiceRepository(BaseRepository[InvoiceModel]):
    """Repository for invoice database operations."""

    def __init__(self, db_connection: DatabaseConnection = None):
        """
        Initialize InvoiceRepository.

        Args:
            db_connection: Optional database connection (uses singleton if not provided)
        """
        super().__init__(db_connection)
        logger.debug("InvoiceRepository initialized")

    def create(self, invoice: InvoiceModel) -> None:
        """
        Create a new invoice in the database.

        Args:
            invoice: InvoiceModel instance to persist

        Raises:
            Exception: If database operation fails
        """
        logger.info(f"Creating invoice: {invoice.id}")

        query = """
            INSERT INTO invoices (
                id, stark_invoice_id, amount, customer_name, customer_tax_id,
                customer_email, status, created_at, paid_at, fee, net_amount,
                retry_count, last_retry_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            invoice.id,
            invoice.stark_invoice_id,
            invoice.amount,
            invoice.customer_name,
            invoice.customer_tax_id,
            invoice.customer_email,
            (
                invoice.status.value
                if isinstance(invoice.status, InvoiceStatus)
                else invoice.status
            ),
            invoice.created_at.isoformat() if invoice.created_at else None,
            invoice.paid_at.isoformat() if invoice.paid_at else None,
            invoice.fee,
            invoice.net_amount,
            invoice.retry_count,
            invoice.last_retry_at.isoformat() if invoice.last_retry_at else None,
            invoice.error_message,
        )

        self._execute(query, params)
        logger.info(f"Invoice created successfully: {invoice.id}")

    def get_by_id(self, invoice_id: str) -> Optional[InvoiceModel]:
        """
        Get an invoice by its internal ID.

        Args:
            invoice_id: Internal invoice ID

        Returns:
            InvoiceModel if found, None otherwise
        """
        logger.debug(f"Getting invoice by ID: {invoice_id}")

        query = """
            SELECT id, stark_invoice_id, amount, customer_name, customer_tax_id,
                   customer_email, status, created_at, paid_at, fee, net_amount,
                   retry_count, last_retry_at, error_message
            FROM invoices WHERE id = ?
        """

        row = self._fetchone(query, (invoice_id,))

        if not row:
            logger.debug(f"Invoice not found: {invoice_id}")
            return None

        return self._row_to_model(row)

    def get_by_stark_id(self, stark_id: str) -> Optional[InvoiceModel]:
        """
        Get an invoice by its Stark Bank ID.

        Args:
            stark_id: Stark Bank invoice ID

        Returns:
            InvoiceModel if found, None otherwise
        """
        logger.debug(f"Getting invoice by Stark ID: {stark_id}")

        query = """
            SELECT id, stark_invoice_id, amount, customer_name, customer_tax_id,
                   customer_email, status, created_at, paid_at, fee, net_amount,
                   retry_count, last_retry_at, error_message
            FROM invoices WHERE stark_invoice_id = ?
        """

        row = self._fetchone(query, (stark_id,))

        if not row:
            logger.debug(f"Invoice not found by Stark ID: {stark_id}")
            return None

        return self._row_to_model(row)

    def update(self, invoice: InvoiceModel) -> None:
        """
        Update an existing invoice in the database.

        Args:
            invoice: InvoiceModel instance with updated data

        Raises:
            NotFoundError: If invoice doesn't exist
        """
        logger.info(f"Updating invoice: {invoice.id}")

        # Check if exists first
        existing = self.get_by_id(invoice.id)
        if not existing:
            raise NotFoundError(f"Invoice not found: {invoice.id}")

        query = """
            UPDATE invoices SET
                stark_invoice_id = ?,
                amount = ?,
                customer_name = ?,
                customer_tax_id = ?,
                customer_email = ?,
                status = ?,
                created_at = ?,
                paid_at = ?,
                fee = ?,
                net_amount = ?,
                retry_count = ?,
                last_retry_at = ?,
                error_message = ?
            WHERE id = ?
        """

        params = (
            invoice.stark_invoice_id,
            invoice.amount,
            invoice.customer_name,
            invoice.customer_tax_id,
            invoice.customer_email,
            (
                invoice.status.value
                if isinstance(invoice.status, InvoiceStatus)
                else invoice.status
            ),
            invoice.created_at.isoformat() if invoice.created_at else None,
            invoice.paid_at.isoformat() if invoice.paid_at else None,
            invoice.fee,
            invoice.net_amount,
            invoice.retry_count,
            invoice.last_retry_at.isoformat() if invoice.last_retry_at else None,
            invoice.error_message,
            invoice.id,
        )

        self._execute(query, params)
        logger.info(f"Invoice updated successfully: {invoice.id}")

    def list(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[InvoiceModel]:
        """
        List invoices with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of InvoiceModel instances
        """
        logger.debug(
            f"Listing invoices: status={status}, limit={limit}, offset={offset}"
        )

        if status:
            query = """
                SELECT id, stark_invoice_id, amount, customer_name, customer_tax_id,
                       customer_email, status, created_at, paid_at, fee, net_amount,
                       retry_count, last_retry_at, error_message
                FROM invoices WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self._fetchall(query, (status, limit, offset))
        else:
            query = """
                SELECT id, stark_invoice_id, amount, customer_name, customer_tax_id,
                       customer_email, status, created_at, paid_at, fee, net_amount,
                       retry_count, last_retry_at, error_message
                FROM invoices
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self._fetchall(query, (limit, offset))

        invoices = [self._row_to_model(row) for row in rows]
        logger.debug(f"Found {len(invoices)} invoices")
        return invoices

    def count(self, status: Optional[str] = None) -> int:
        """
        Count invoices with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            Number of invoices matching the criteria
        """
        logger.debug(f"Counting invoices: status={status}")

        if status:
            query = "SELECT COUNT(*) FROM invoices WHERE status = ?"
            row = self._fetchone(query, (status,))
        else:
            query = "SELECT COUNT(*) FROM invoices"
            row = self._fetchone(query)

        count = row[0] if row else 0
        logger.debug(f"Invoice count: {count}")
        return count

    def list_by_status(self, status: InvoiceStatus) -> List[InvoiceModel]:
        """
        List all invoices with a specific status.

        Args:
            status: Invoice status to filter by

        Returns:
            List of InvoiceModel instances
        """
        status_value = status.value if isinstance(status, InvoiceStatus) else status
        return self.list(status=status_value, limit=10000)

    def _row_to_model(self, row) -> InvoiceModel:
        """
        Convert a database row to an InvoiceModel.

        Args:
            row: Database row tuple

        Returns:
            InvoiceModel instance
        """
        return InvoiceModel.from_dict({
            "id": row[0],
            "stark_invoice_id": row[1],
            "amount": row[2],
            "customer_name": row[3],
            "customer_tax_id": row[4],
            "customer_email": row[5],
            "status": row[6],
            "created_at": row[7],
            "paid_at": row[8],
            "fee": row[9],
            "net_amount": row[10],
            "retry_count": row[11],
            "last_retry_at": row[12],
            "error_message": row[13],
        })
