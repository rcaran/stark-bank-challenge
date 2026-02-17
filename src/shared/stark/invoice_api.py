"""Stark Bank Invoice API wrapper with retry logic."""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import starkbank
from starkbank import Invoice

from src.shared.stark.client import StarkBankClient
from src.shared.stark.retry import retry_with_backoff
from src.shared.utils.errors import (
    AuthenticationError,
    RetriableError,
    StarkBankError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class InvoiceResponse:
    id: str
    amount: int
    tax_id: str
    name: str
    due_date: datetime
    status: str
    pdf: str | None = None
    fine: float = 0
    interest: float = 0
    tags: list[str] | None = None
    descriptions: list[dict[str, Any]] | None = None

    @classmethod
    def from_stark_invoice(cls, invoice: Invoice) -> InvoiceResponse:
        # starkbank.Invoice object has attributes.
        return cls(
            id=invoice.id,
            amount=invoice.amount,
            tax_id=invoice.tax_id,
            name=invoice.name,
            due_date=invoice.due,  # 'due' in starkbank object
            status=invoice.status,
            pdf=invoice.pdf if hasattr(invoice, "pdf") else None,
            fine=invoice.fine,
            interest=invoice.interest,
            tags=invoice.tags,
            descriptions=invoice.descriptions,
        )


class StarkInvoiceAPI(StarkBankClient):
    @retry_with_backoff(
        retriable_exceptions=(StarkBankError, RetriableError, ConnectionError),
        non_retriable_exceptions=(ValidationError, AuthenticationError),
    )
    def create_invoice(
        self,
        amount: int,
        tax_id: str,
        name: str,
        due_date: date,
        fine: float = 0,
        interest: float = 0,
        tags: list[str] | None = None,
        descriptions: list[dict] | None = None,
    ) -> InvoiceResponse:
        """
        Creates an invoice in Stark Bank.
        params:
            amount: in cents
        """
        _ = self.check_user  # Ensure initialized

        logger.info(f"Creating invoice: amount={amount}, tax_id={tax_id}, name={name}")

        # Validate amount is int
        if not isinstance(amount, int):
            raise ValidationError("Amount must be integer (cents)")

        try:
            invoices = starkbank.invoice.create(
                [
                    Invoice(
                        amount=amount,
                        tax_id=tax_id,
                        name=name,
                        due=due_date,
                        fine=fine,
                        interest=interest,
                        tags=tags,
                        descriptions=descriptions,
                    )
                ]
            )

            created_invoice = invoices[0]
            logger.info(f"Invoice created: {created_invoice.id}")
            return InvoiceResponse.from_stark_invoice(created_invoice)

        except Exception as e:
            self.handle_stark_error(e)

    def get_invoice(self, invoice_id: str) -> InvoiceResponse:
        _ = self.check_user  # Ensure initialized
        try:
            invoice = starkbank.invoice.get(invoice_id)
            return InvoiceResponse.from_stark_invoice(invoice)
        except Exception as e:
            self.handle_stark_error(e)

    def list_invoices(
        self, limit: int = 100, after: date | None = None, status: str | None = None
    ) -> list[InvoiceResponse]:
        _ = self.check_user  # Ensure initialized
        try:
            # starkbank.invoice.query returns generator
            invoices_gen = starkbank.invoice.query(
                limit=limit, after=after, status=status
            )
            return [InvoiceResponse.from_stark_invoice(inv) for inv in invoices_gen]
        except Exception as e:
            self.handle_stark_error(e)
