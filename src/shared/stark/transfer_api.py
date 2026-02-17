"""Stark Bank Transfer API wrapper with retry logic."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

import starkbank
from starkbank import Transfer

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
class TransferResponse:
    id: str
    amount: int
    tax_id: str
    name: str
    bank_code: str
    branch_code: str
    account_number: str
    external_id: str | None
    status: str
    tags: list[str] | None = None
    fee: int = 0
    created: datetime | None = None

    @classmethod
    def from_stark_transfer(cls, transfer: Transfer) -> TransferResponse:
        return cls(
            id=transfer.id,
            amount=transfer.amount,
            tax_id=transfer.tax_id,
            name=transfer.name,
            bank_code=transfer.bank_code,
            branch_code=transfer.branch_code,
            account_number=transfer.account_number,
            external_id=transfer.external_id,
            status=transfer.status,
            tags=transfer.tags,
            fee=transfer.fee,
            created=transfer.created if hasattr(transfer, "created") else None,
        )


class StarkTransferAPI(StarkBankClient):
    @retry_with_backoff(
        retriable_exceptions=(StarkBankError, RetriableError, ConnectionError),
        non_retriable_exceptions=(ValidationError, AuthenticationError),
    )
    def create_transfer(
        self,
        amount: int,
        name: str,
        tax_id: str,
        bank_code: str,
        branch_code: str,
        account_number: str,
        external_id: str | None = None,
        tags: list[str] | None = None,
        account_type: str = "checking",
    ) -> TransferResponse:
        """
        Creates a transfer in Stark Bank.
        params:
            amount: in cents
        """
        _ = self.check_user  # Ensure initialized

        logger.info(
            f"Creating transfer: amount={amount}, name={name}, "
            f"external_id={external_id}"
        )

        if not isinstance(amount, int):
            raise ValidationError("Amount must be integer (cents)")

        try:
            transfers = starkbank.transfer.create(
                [
                    Transfer(
                        amount=amount,
                        name=name,
                        tax_id=tax_id,
                        bank_code=bank_code,
                        branch_code=branch_code,
                        account_number=account_number,
                        external_id=external_id,
                        tags=tags,
                        account_type=account_type,
                    )
                ]
            )

            created_transfer = transfers[0]
            logger.info(f"Transfer created: {created_transfer.id}")
            return TransferResponse.from_stark_transfer(created_transfer)
        except Exception as e:
            self.handle_stark_error(e)

    def get_transfer(self, transfer_id: str) -> TransferResponse:
        _ = self.check_user  # Ensure initialized
        try:
            transfer = starkbank.transfer.get(transfer_id)
            return TransferResponse.from_stark_transfer(transfer)
        except Exception as e:
            self.handle_stark_error(e)

    def list_transfers(
        self,
        limit: int = 100,
        after: date | None = None,
        status: str | None = None,
        transaction_ids: list[str] | None = None,
    ) -> list[TransferResponse]:
        _ = self.check_user  # Ensure initialized
        try:
            transfers_gen = starkbank.transfer.query(
                limit=limit, after=after, status=status, transaction_ids=transaction_ids
            )
            return [TransferResponse.from_stark_transfer(t) for t in transfers_gen]
        except Exception as e:
            self.handle_stark_error(e)
