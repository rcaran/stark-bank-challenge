"""Unit tests for InvoiceGenerator."""

from datetime import UTC, datetime

import pytest

from src.modules.invoices.generator import InvoiceGenerator
from src.shared.utils.validators import validate_cnpj, validate_cpf


class TestInvoiceGenerator:
    """Tests for InvoiceGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a standard invoice generator."""
        return InvoiceGenerator()

    @pytest.fixture
    def custom_generator(self):
        """Create a custom configured generator."""
        return InvoiceGenerator(
            min_amount=500,
            max_amount=50000,
            due_days_min=5,
            due_days_max=15,
            cpf_ratio=0.5,
        )

    def test_generator_initialization_defaults(self, generator):
        """Test generator initialization with defaults."""
        assert generator.min_amount == 100.0
        assert generator.max_amount == 100000.0
        assert generator.due_days_min == 1
        assert generator.due_days_max == 30
        assert generator.cpf_ratio == 0.7

    def test_generator_initialization_custom(self, custom_generator):
        """Test generator initialization with custom values."""
        assert custom_generator.min_amount == 500
        assert custom_generator.max_amount == 50000
        assert custom_generator.due_days_min == 5
        assert custom_generator.due_days_max == 15
        assert custom_generator.cpf_ratio == 0.5

    def test_generate_single(self, generator):
        """Test generating a single invoice."""
        invoice_data = generator._generate_single()

        assert "amount" in invoice_data
        assert "customer_name" in invoice_data
        assert "customer_tax_id" in invoice_data
        assert "customer_email" in invoice_data
        assert "due_date" in invoice_data

        # Validate amount is within range
        assert generator.min_amount <= invoice_data["amount"] <= generator.max_amount

        # Validate amount is integer
        assert isinstance(invoice_data["amount"], int)

        # Validate tax ID is valid
        tax_id = invoice_data["customer_tax_id"]
        clean_id = tax_id.replace(".", "").replace("-", "").replace("/", "")

        if len(clean_id) == 11:
            assert validate_cpf(tax_id), f"Invalid CPF: {tax_id}"
        else:
            assert validate_cnpj(tax_id), f"Invalid CNPJ: {tax_id}"

    def test_generate_batch_default_count(self, generator):
        """Test generating batch with default count (8-12)."""
        invoices = generator.generate_batch()

        assert len(invoices) >= 8
        assert len(invoices) <= 12

    def test_generate_batch_specific_count(self, generator):
        """Test generating batch with specific count."""
        invoices = generator.generate_batch(count=5)

        assert len(invoices) == 5

    def test_generate_batch_large_count(self, generator):
        """Test generating large batch."""
        invoices = generator.generate_batch(count=20)

        assert len(invoices) == 20
        # All should have valid data
        for inv in invoices:
            assert inv["amount"] > 0
            assert len(inv["customer_name"]) > 0

    def test_batch_amounts_within_range(self, generator):
        """Test that all batch amounts are within configured range."""
        invoices = generator.generate_batch(count=10)

        for inv in invoices:
            assert generator.min_amount <= inv["amount"] <= generator.max_amount

    def test_batch_due_dates_in_future(self, generator):
        """Test that all due dates are in the future."""
        now = datetime.now(UTC)
        invoices = generator.generate_batch(count=10)

        for inv in invoices:
            assert inv["due_date"] > now

    def test_batch_valid_tax_ids(self, generator):
        """Test that all generated tax IDs are valid."""
        invoices = generator.generate_batch(count=20)

        for inv in invoices:
            tax_id = inv["customer_tax_id"]
            clean_id = tax_id.replace(".", "").replace("-", "").replace("/", "")

            if len(clean_id) == 11:
                assert validate_cpf(tax_id), f"Invalid CPF: {tax_id}"
            else:
                assert validate_cnpj(tax_id), f"Invalid CNPJ: {tax_id}"

    def test_batch_valid_emails(self, generator):
        """Test that all emails contain @."""
        invoices = generator.generate_batch(count=10)

        for inv in invoices:
            assert "@" in inv["customer_email"]

    def test_cpf_cnpj_distribution(self, generator):
        """Test approximate CPF/CNPJ distribution (70/30)."""
        # Generate enough to get statistical significance
        invoices = generator.generate_batch(count=100)

        cpf_count = 0
        cnpj_count = 0

        for inv in invoices:
            tax_id = inv["customer_tax_id"]
            clean_id = tax_id.replace(".", "").replace("-", "").replace("/", "")

            if len(clean_id) == 11:
                cpf_count += 1
            else:
                cnpj_count += 1

        # With 70% CPF ratio, expect roughly 60-80% CPFs
        cpf_ratio = cpf_count / 100
        assert 0.50 <= cpf_ratio <= 0.90, (
            f"CPF ratio {cpf_ratio} outside expected range"
        )

    def test_generate_for_testing_cpf(self, generator):
        """Test generating invoice for testing with CPF."""
        invoice_data = generator.generate_invoice_for_testing(
            amount=5000,
            use_cpf=True,
        )

        assert invoice_data["amount"] == 5000

        tax_id = invoice_data["customer_tax_id"]
        clean_id = tax_id.replace(".", "").replace("-", "")
        assert len(clean_id) == 11
        assert validate_cpf(tax_id)

    def test_generate_for_testing_cnpj(self, generator):
        """Test generating invoice for testing with CNPJ."""
        invoice_data = generator.generate_invoice_for_testing(
            amount=10000,
            use_cpf=False,
        )

        assert invoice_data["amount"] == 10000

        tax_id = invoice_data["customer_tax_id"]
        clean_id = tax_id.replace(".", "").replace("-", "").replace("/", "")
        assert len(clean_id) == 14
        assert validate_cnpj(tax_id)

    def test_generate_for_testing_random_amount(self, generator):
        """Test generating invoice for testing with random amount."""
        invoice_data = generator.generate_invoice_for_testing()

        assert generator.min_amount <= invoice_data["amount"] <= generator.max_amount


class TestInvoiceGeneratorCustomConfig:
    """Tests for InvoiceGenerator with custom configuration."""

    def test_custom_amount_range(self):
        """Test custom amount range."""
        generator = InvoiceGenerator(min_amount=1000, max_amount=2000)
        invoices = generator.generate_batch(count=10)

        for inv in invoices:
            assert 1000 <= inv["amount"] <= 2000

    def test_custom_due_days_range(self):
        """Test custom due days range."""
        generator = InvoiceGenerator(due_days_min=10, due_days_max=20)
        now = datetime.now(UTC)

        invoices = generator.generate_batch(count=10)

        for inv in invoices:
            delta = (inv["due_date"] - now).days
            assert 10 <= delta <= 20

    def test_high_cpf_ratio(self):
        """Test high CPF ratio (90%)."""
        generator = InvoiceGenerator(cpf_ratio=0.9)
        invoices = generator.generate_batch(count=50)

        cpf_count = sum(
            1 for inv in invoices
            if len(
                inv["customer_tax_id"]
                .replace(".", "")
                .replace("-", "")
                .replace("/", "")
            ) == 11
        )

        assert cpf_count / 50 >= 0.75  # Expect at least 75% CPF with 90% ratio

    def test_zero_cpf_ratio(self):
        """Test zero CPF ratio (all CNPJ)."""
        generator = InvoiceGenerator(cpf_ratio=0.0)
        invoices = generator.generate_batch(count=20)

        for inv in invoices:
            tax_id = inv["customer_tax_id"]
            clean_id = tax_id.replace(".", "").replace("-", "").replace("/", "")
            assert len(clean_id) == 14, f"Expected CNPJ but got: {tax_id}"
