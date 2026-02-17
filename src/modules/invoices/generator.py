"""
Invoice Generator.

This module generates random invoice data for testing and batch creation,
using the shared DataGenerator for realistic Brazilian customer data.
"""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from src.shared.utils.data_generator import DataGenerator
from src.shared.utils.logger import get_logger
from src.shared.utils.validators import validate_cnpj, validate_cpf

logger = get_logger("modules.invoices.generator")


class InvoiceGenerator:
    """
    Generator for invoice data.

    Uses DataGenerator to create realistic customer information
    and generates random invoice amounts within configurable ranges.
    """

    # Default configuration
    DEFAULT_MIN_AMOUNT = 100.0  # R$ 1,00 in cents
    DEFAULT_MAX_AMOUNT = 100000.0  # R$ 1.000,00 in cents
    DEFAULT_DUE_DAYS_MIN = 1
    DEFAULT_DUE_DAYS_MAX = 30
    DEFAULT_CPF_RATIO = 0.7  # 70% CPF, 30% CNPJ

    def __init__(
        self,
        min_amount: float | None = None,
        max_amount: float | None = None,
        due_days_min: int | None = None,
        due_days_max: int | None = None,
        cpf_ratio: float | None = None,
    ):
        """
        Initialize InvoiceGenerator with configuration.

        Args:
            min_amount: Minimum invoice amount in cents (default: 100)
            max_amount: Maximum invoice amount in cents (default: 100000)
            due_days_min: Minimum days until due date (default: 1)
            due_days_max: Maximum days until due date (default: 30)
            cpf_ratio: Ratio of CPF vs CNPJ (default: 0.7)
        """
        self.data_generator = DataGenerator()
        self.min_amount = (
            min_amount if min_amount is not None else self.DEFAULT_MIN_AMOUNT
        )
        self.max_amount = (
            max_amount if max_amount is not None else self.DEFAULT_MAX_AMOUNT
        )
        self.due_days_min = (
            due_days_min if due_days_min is not None else self.DEFAULT_DUE_DAYS_MIN
        )
        self.due_days_max = (
            due_days_max if due_days_max is not None else self.DEFAULT_DUE_DAYS_MAX
        )
        self.cpf_ratio = cpf_ratio if cpf_ratio is not None else self.DEFAULT_CPF_RATIO

        logger.info(
            "InvoiceGenerator initialized",
            min_amount=self.min_amount,
            max_amount=self.max_amount,
            cpf_ratio=self.cpf_ratio,
        )

    def generate_batch(self, count: int | None = None) -> list[dict[str, Any]]:
        """
        Generate a batch of invoice data.

        If count is not specified, generates between 8 and 12 invoices
        as per the challenge requirements.

        Args:
            count: Number of invoices to generate (optional)

        Returns:
            List of invoice data dictionaries
        """
        if count is None:
            count = random.randint(8, 12)

        logger.info(f"Generating batch of {count} invoices")

        invoices = []
        for i in range(count):
            invoice_data = self._generate_single()
            invoices.append(invoice_data)
            tax_id_clean = (
                invoice_data["customer_tax_id"]
                .replace(".", "")
                .replace("-", "")
                .replace("/", "")
            )
            tax_id_type = "CPF" if len(tax_id_clean) == 11 else "CNPJ"
            logger.debug(
                f"Generated invoice {i + 1}/{count}",
                amount=invoice_data["amount"],
                tax_id_type=tax_id_type,
            )

        logger.info(
            "Batch generation completed",
            count=len(invoices),
            total_amount=sum(inv["amount"] for inv in invoices),
        )

        return invoices

    def _generate_single(self) -> dict[str, Any]:
        """
        Generate data for a single invoice.

        Returns:
            Dictionary with invoice data including:
            - amount: Random amount in cents (int)
            - customer_name: Random name
            - customer_tax_id: Valid CPF or CNPJ
            - customer_email: Random email
            - due_date: Random future date
        """
        # Generate customer data (70% CPF, 30% CNPJ based on cpf_ratio)
        is_person = random.random() < self.cpf_ratio
        if is_person:
            customer_data = self.data_generator.generate_person_data()
        else:
            customer_data = self.data_generator.generate_company_data()

        # Validate generated tax ID
        tax_id = customer_data["tax_id"]
        clean_tax_id = tax_id.replace(".", "").replace("-", "").replace("/", "")

        if len(clean_tax_id) == 11:
            if not validate_cpf(tax_id):
                logger.warning("Generated invalid CPF, regenerating")
                customer_data = self.data_generator.generate_person_data()
        else:
            if not validate_cnpj(tax_id):
                logger.warning("Generated invalid CNPJ, regenerating")
                customer_data = self.data_generator.generate_company_data()

        # Generate random amount (as integer cents)
        amount = random.randint(int(self.min_amount), int(self.max_amount))

        # Generate due date
        due_days = random.randint(self.due_days_min, self.due_days_max)
        due_date = datetime.now(UTC) + timedelta(days=due_days)

        return {
            "amount": amount,
            "customer_name": customer_data["name"],
            "customer_tax_id": customer_data["tax_id"],
            "customer_email": customer_data["email"],
            "due_date": due_date,
        }

    def generate_invoice_for_testing(
        self,
        amount: int | None = None,
        use_cpf: bool = True,
    ) -> dict[str, Any]:
        """
        Generate invoice data with specific parameters for testing.

        Args:
            amount: Specific amount in cents (optional)
            use_cpf: Use CPF instead of CNPJ (default: True)

        Returns:
            Dictionary with invoice data
        """
        if use_cpf:
            customer_data = self.data_generator.generate_person_data()
        else:
            customer_data = self.data_generator.generate_company_data()

        if amount is None:
            amount = random.randint(int(self.min_amount), int(self.max_amount))

        due_date = datetime.now(UTC) + timedelta(days=7)

        return {
            "amount": amount,
            "customer_name": customer_data["name"],
            "customer_tax_id": customer_data["tax_id"],
            "customer_email": customer_data["email"],
            "due_date": due_date,
        }
