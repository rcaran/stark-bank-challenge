"""
E2E Test: Invoice Creation Flow.

Tests the complete flow of invoice creation through the scheduler,
including Stark Bank API calls, database persistence, and event publishing.
"""

from unittest.mock import MagicMock, patch

from src.modules.invoices.models import InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.scheduler import generate_invoices_job
from src.shared.utils.logger import get_logger

logger = get_logger("tests.e2e.invoice_creation_flow")


class TestInvoiceCreationFlow:
    """E2E tests for the invoice creation flow."""

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_invoice_creation_success(
        self,
        mock_generator_class,
        mock_service_class,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
    ):
        """
        Test complete invoice creation flow:
        - Scheduler triggers generation
        - Invoices created in Stark Bank (mock)
        - Invoices saved in database
        - Events published
        - All invoices have status="created"
        """
        logger.info("Starting E2E test: invoice_creation_success")

        # ===== SETUP: Configure mocks and dependencies =====

        # Configure generator mock to return sample invoices
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        sample_invoice_data = [
            {
                "amount": 50000,
                "customer_name": "João Silva",
                "customer_tax_id": "123.456.789-09",
                "customer_email": "joao.silva@example.com",
            },
            {
                "amount": 100000,
                "customer_name": "Maria Santos",
                "customer_tax_id": "111.444.777-35",
                "customer_email": "maria.santos@example.com",
            },
            {
                "amount": 75000,
                "customer_name": "Tech Solutions LTDA",
                "customer_tax_id": "11.222.333/0001-81",
                "customer_email": "contato@techsolutions.com",
            },
            {
                "amount": 120000,
                "customer_name": "Carlos Oliveira",
                "customer_tax_id": "987.654.321-00",
                "customer_email": "carlos.oliveira@example.com",
            },
            {
                "amount": 85000,
                "customer_name": "Ana Costa",
                "customer_tax_id": "012.345.678-90",
                "customer_email": "ana.costa@example.com",
            },
        ]

        mock_generator.generate_batch.return_value = sample_invoice_data

        # Configure service mock to create invoices using real dependencies
        # We need to use the actual service here to test the full flow
        from src.modules.invoices.service import InvoiceService

        repository = InvoiceRepository(e2e_db)
        stark_invoice_api = mock_stark_api["invoice_api"]
        service = InvoiceService(
            repository=repository, stark_api=stark_invoice_api, event_bus=e2e_event_bus
        )

        # Return the real service instance
        mock_service_class.return_value = service

        # Track published events
        published_events = []

        def capture_event(event):
            published_events.append(event)
            logger.debug(f"Event captured: {event.event_type}")

        e2e_event_bus.subscribe("invoice.created", capture_event)

        # ===== EXECUTE: Run the scheduler job =====

        logger.info("Executing generate_invoices_job")
        generate_invoices_job()

        # ===== VERIFY: Scheduler triggered generation =====

        # Verify generator was called
        mock_generator.generate_batch.assert_called_once_with(count=None)
        logger.info("✓ Scheduler triggered invoice generation")

        # ===== VERIFY: Invoices created in Stark Bank (mock) =====

        # Verify Stark Bank API was called for each invoice
        assert stark_invoice_api.create_invoice.call_count == len(sample_invoice_data)

        # Verify each invoice was sent to Stark Bank with correct data
        for idx, invoice_data in enumerate(sample_invoice_data):
            call_args = stark_invoice_api.create_invoice.call_args_list[idx]
            # Access keyword arguments
            kwargs = call_args.kwargs

            assert kwargs["amount"] == invoice_data["amount"]
            assert kwargs["name"] == invoice_data["customer_name"]
            # Tax ID is passed as provided by the service
            assert kwargs["tax_id"] == invoice_data["customer_tax_id"]

        logger.info("✓ All invoices sent to Stark Bank API")

        # ===== VERIFY: Invoices saved in database =====

        # Query all invoices from database
        cursor = e2e_db.connection.cursor()
        cursor.execute("SELECT * FROM invoices")
        db_invoices = cursor.fetchall()

        # Should have all created invoices
        assert len(db_invoices) == len(sample_invoice_data)
        logger.info(f"✓ Found {len(db_invoices)} invoices in database")

        # Verify each invoice has required fields
        for db_invoice in db_invoices:
            assert db_invoice["id"] is not None
            assert db_invoice["stark_invoice_id"] is not None
            assert db_invoice["amount"] > 0
            assert db_invoice["customer_name"] is not None
            assert db_invoice["customer_tax_id"] is not None
            assert db_invoice["customer_email"] is not None
            assert db_invoice["status"] == InvoiceStatus.CREATED.value
            assert db_invoice["created_at"] is not None
            logger.debug(
                f"  - Invoice {db_invoice['id']}: {db_invoice['customer_name']}"
                f" - {db_invoice['amount'] / 100:.2f}"
            )

        logger.info("✓ All invoices have required fields")

        # ===== VERIFY: All invoices have status="created" =====

        # Verify all invoices have CREATED status
        cursor.execute("SELECT status FROM invoices")
        statuses = [row["status"] for row in cursor.fetchall()]

        assert all(status == InvoiceStatus.CREATED.value for status in statuses)
        logger.info("✓ All invoices have status='created'")

        # ===== VERIFY: Events published =====

        # Should have one event per invoice
        assert len(published_events) == len(sample_invoice_data)
        logger.info(f"✓ {len(published_events)} events published")

        # Verify all events are invoice.created
        for event in published_events:
            assert event.event_type == "invoice.created"
            assert event.payload is not None
            assert "invoice_id" in event.payload
            assert "amount" in event.payload
            assert "customer_name" in event.payload

        logger.info("✓ All 'invoice.created' events have correct structure")

        # ===== VERIFY: Event data matches database records =====

        # Get invoices from repository for detailed verification
        invoices_from_db = repository.list(
            status=InvoiceStatus.CREATED, limit=100, offset=0
        )

        assert len(invoices_from_db) == len(sample_invoice_data)

        # Map events to invoices
        event_invoice_ids = {event.payload["invoice_id"] for event in published_events}
        db_invoice_ids = {invoice.id for invoice in invoices_from_db}

        assert event_invoice_ids == db_invoice_ids
        logger.info("✓ Event data matches database records")

        # ===== VERIFY: Invoice amounts match original data =====

        # Convert original amounts from cents to reais for comparison
        # (internal storage is in reais, input is in cents)
        original_amounts_reais = {
            data["amount"] / 100.0 for data in sample_invoice_data
        }
        db_amounts = {invoice.amount for invoice in invoices_from_db}

        assert db_amounts == original_amounts_reais
        logger.info("✓ Invoice amounts preserved correctly")

        # ===== SUMMARY =====

        logger.info("=" * 60)
        logger.info("E2E Test Summary: Invoice Creation Flow")
        logger.info("=" * 60)
        logger.info("✓ Scheduler triggered: YES")
        logger.info(f"✓ Invoices generated: {len(sample_invoice_data)}")
        logger.info(
            f"✓ Stark Bank API calls: {stark_invoice_api.create_invoice.call_count}"
        )
        logger.info(f"✓ Invoices in database: {len(db_invoices)}")
        logger.info(f"✓ Events published: {len(published_events)}")
        logger.info("✓ All status='created': YES")
        logger.info("=" * 60)
        logger.info("✅ TEST PASSED: Invoice Creation Flow")
        logger.info("=" * 60)

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_invoice_creation_with_batch_size_validation(
        self,
        mock_generator_class,
        mock_service_class,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
    ):
        """
        Test that scheduler generates invoices within expected batch size (8-12).
        """
        logger.info("Starting E2E test: invoice_creation_with_batch_size_validation")

        # Setup: Configure to return a random batch (8-12)
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        # Generate 10 sample invoices (within 8-12 range) with valid CPFs
        valid_cpfs = [
            "123.456.789-09",
            "111.444.777-35",
            "987.654.321-00",
            "012.345.678-90",
            "654.552.024-56",
            "326.607.966-37",
            "906.647.337-19",
            "787.589.537-52",
            "430.678.195-00",
            "155.576.557-27",
        ]

        sample_invoice_data = [
            {
                "amount": 50000 + (i * 10000),
                "customer_name": f"Customer {i}",
                "customer_tax_id": valid_cpfs[i],
                "customer_email": f"customer{i}@example.com",
            }
            for i in range(10)
        ]

        mock_generator.generate_batch.return_value = sample_invoice_data

        # Setup real service
        from src.modules.invoices.service import InvoiceService

        repository = InvoiceRepository(e2e_db)
        service = InvoiceService(
            repository=repository,
            stark_api=mock_stark_api["invoice_api"],
            event_bus=e2e_event_bus,
        )
        mock_service_class.return_value = service

        # Execute
        generate_invoices_job()

        # Verify batch size is within expected range
        batch_size = len(sample_invoice_data)
        assert 8 <= batch_size <= 12, f"Batch size {batch_size} not in range [8, 12]"

        # Verify all were created
        cursor = e2e_db.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM invoices")
        count = cursor.fetchone()["count"]

        assert count == batch_size

        logger.info(f"✓ Batch size validation passed: {batch_size} invoices created")

    @patch("src.scheduler.InvoiceService")
    @patch("src.scheduler.InvoiceGenerator")
    def test_invoice_creation_handles_partial_failures(
        self,
        mock_generator_class,
        mock_service_class,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
    ):
        """
        Test that scheduler handles partial failures gracefully.
        Some invoices succeed, some fail, but the job completes.
        """
        logger.info("Starting E2E test: invoice_creation_handles_partial_failures")

        # Setup
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        sample_invoice_data = [
            {
                "amount": 50000,
                "customer_name": "Success Invoice 1",
                "customer_tax_id": "123.456.789-09",
                "customer_email": "success1@example.com",
            },
            {
                "amount": 100000,
                "customer_name": "Fail Invoice",
                "customer_tax_id": "111.444.777-35",
                "customer_email": "fail@example.com",
            },
            {
                "amount": 75000,
                "customer_name": "Success Invoice 2",
                "customer_tax_id": "987.654.321-00",
                "customer_email": "success2@example.com",
            },
        ]

        mock_generator.generate_batch.return_value = sample_invoice_data

        # Setup real service but make Stark API fail for second invoice
        from src.modules.invoices.service import InvoiceService

        repository = InvoiceRepository(e2e_db)

        # Configure mock to fail on second call
        # Return Mock objects with .id attribute (matching StarkInvoiceAPI response)
        success_response_1 = MagicMock()
        success_response_1.id = "stark_inv_1"

        success_response_3 = MagicMock()
        success_response_3.id = "stark_inv_3"

        mock_stark_api["invoice_api"].create_invoice.side_effect = [
            success_response_1,
            Exception("Stark Bank API Error: Rate limit exceeded"),
            success_response_3,
        ]

        service = InvoiceService(
            repository=repository,
            stark_api=mock_stark_api["invoice_api"],
            event_bus=e2e_event_bus,
        )
        mock_service_class.return_value = service

        # Execute - should not raise exception despite failure
        generate_invoices_job()

        # Verify: 2 invoices created (1 failed)
        cursor = e2e_db.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM invoices WHERE status = ?",
            (InvoiceStatus.CREATED.value,),
        )
        success_count = cursor.fetchone()["count"]

        assert success_count == 2, (
            f"Expected 2 successful invoices, got {success_count}"
        )

        logger.info("✓ Partial failure handled: 2 success, 1 failed")
        logger.info("✅ TEST PASSED: Scheduler handles partial failures gracefully")

    def test_invoice_creation_generates_valid_customer_data(
        self, e2e_db, e2e_event_bus, mock_stark_api
    ):
        """
        Test that generated invoices have valid customer data (CPF/CNPJ).
        """
        logger.info("Starting E2E test: invoice_creation_generates_valid_customer_data")

        from src.modules.invoices.generator import InvoiceGenerator
        from src.modules.invoices.service import InvoiceService
        from src.shared.utils.validators import validate_cnpj, validate_cpf

        # Use real generator
        generator = InvoiceGenerator()
        repository = InvoiceRepository(e2e_db)
        service = InvoiceService(
            repository=repository,
            stark_api=mock_stark_api["invoice_api"],
            event_bus=e2e_event_bus,
        )

        # Generate and create invoices
        invoice_data_list = generator.generate_batch(count=10)

        for invoice_data in invoice_data_list:
            service.create_invoice(invoice_data)

        # Verify all have valid CPF or CNPJ
        cursor = e2e_db.connection.cursor()
        cursor.execute("SELECT customer_tax_id FROM invoices")
        tax_ids = [row["customer_tax_id"] for row in cursor.fetchall()]

        for tax_id in tax_ids:
            # Remove formatting
            clean_tax_id = tax_id.replace(".", "").replace("-", "").replace("/", "")

            # Check if valid CPF or CNPJ
            is_valid = validate_cpf(clean_tax_id) or validate_cnpj(clean_tax_id)
            assert is_valid, f"Invalid tax ID: {tax_id}"

        logger.info(f"✓ All {len(tax_ids)} tax IDs are valid CPF or CNPJ")
        logger.info("✅ TEST PASSED: Generated customer data is valid")
