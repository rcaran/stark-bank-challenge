"""
E2E Test Infrastructure - Fixtures.

This module provides fixtures for end-to-end testing including:
- Isolated test database
- FastAPI TestClient with real dependencies
- Mock Stark Bank API
- Sample test data
"""

import json
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.config.settings import settings
from src.dependencies import (
    get_db,
    get_event_bus,
    get_stark_client,
    get_stark_invoice_api,
    get_stark_transfer_api,
)
from src.main import app
from src.modules.invoices import api as invoices_api_module
from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.invoices.service import InvoiceService
from src.modules.transfers import api as transfers_api_module
from src.modules.transfers.handler import TransferHandler
from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.repository import TransferRepository
from src.modules.transfers.service import TransferService
from src.modules.webhooks import api as webhooks_api_module
from src.modules.webhooks.invoice_processor import InvoiceWebhookProcessor
from src.modules.webhooks.receiver import WebhookReceiver
from src.modules.webhooks.transfer_processor import TransferWebhookProcessor
from src.modules.webhooks.validator import WebhookValidator
from src.shared.database.connection import DatabaseConnection
from src.shared.database.migrations import migrate_database
from src.shared.events.bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger("tests.e2e")


class TestDatabaseConnection:
    """
    Wrapper for test database connection to match DatabaseConnection interface.
    """
    def __init__(self, conn):
        self._connection = conn
    
    @property
    def connection(self):
        return self._connection
    
    @contextmanager
    def get_db(self):
        """
        Context manager that yields the connection and handles transactions.
        """
        try:
            yield self._connection
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Test database transaction failed: {e!s}")
            raise


@pytest.fixture(scope="function")
def e2e_db():
    """
    Create an isolated database for each E2E test.
    
    Uses a temporary file to provide persistence during the test
    while ensuring complete isolation between tests.
    
    Yields:
        TestDatabaseConnection: Test database connection wrapper
    """
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_db_path = temp_db.name
    temp_db.close()
    
    logger.info(f"Creating E2E test database: {temp_db_path}")
    
    # Create connection with check_same_thread=False for testing
    # This allows the connection to be used from different threads
    # (TestClient runs requests in a separate thread)
    conn = sqlite3.connect(temp_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    try:
        # Run migrations to set up schema
        migrate_database(conn)
        
        # Wrap in TestDatabaseConnection
        test_db_conn = TestDatabaseConnection(conn)
        
        yield test_db_conn
        
    finally:
        # Clean up
        conn.close()
        import os
        try:
            os.unlink(temp_db_path)
            logger.info(f"Cleaned up E2E test database: {temp_db_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up test database: {e}")


@pytest.fixture(scope="function")
def e2e_event_bus():
    """
    Create a fresh EventBus for each E2E test.
    
    Returns:
        EventBus: Fresh event bus instance
    """
    from collections import defaultdict
    
    # Create new event bus (bypasses singleton)
    bus = object.__new__(EventBus)
    bus._subscribers = defaultdict(list)
    
    return bus


@pytest.fixture(scope="function")
def mock_stark_invoice_api():
    """
    Create a mock Stark Bank Invoice API for E2E testing.
    
    Simulates successful invoice creation without making real API calls.
    
    Returns:
        Mock: Mock StarkInvoiceAPI instance
    """
    mock_api = Mock()
    
    # Default behavior: successful invoice creation
    def create_invoice_side_effect(**kwargs):
        amount = kwargs.get('amount')
        name = kwargs.get('name')
        tax_id = kwargs.get('tax_id')
        due_date = kwargs.get('due_date')
        
        # Create a mock response object with an id attribute
        response = Mock()
        response.id = f"stark_{tax_id}_{amount}"
        return response
    
    mock_api.create_invoice.side_effect = create_invoice_side_effect
    
    return mock_api


@pytest.fixture(scope="function")
def mock_stark_transfer_api():
    """
    Create a mock Stark Bank Transfer API for E2E testing.
    
    Simulates successful transfer creation without making real API calls.
    
    Returns:
        Mock: Mock StarkTransferAPI instance
    """
    mock_api = Mock()
    
    # Default behavior: successful transfer creation
    def create_transfer_side_effect(
        amount,
        name,
        tax_id,
        bank_code,
        branch_code,
        account_number,
        external_id,
        tags=None,
        account_type=None,
    ):
        # Create a mock response object with attributes (not a dict)
        response = Mock()
        response.id = f"stark_transfer_{external_id}"
        response.amount = amount
        response.external_id = external_id
        response.status = "created"
        response.bank_code = bank_code
        response.branch_code = branch_code
        response.account_number = account_number
        return response
    
    mock_api.create_transfer.side_effect = create_transfer_side_effect
    
    return mock_api


@pytest.fixture(scope="function")
def mock_stark_api(mock_stark_invoice_api, mock_stark_transfer_api):
    """
    Complete mock of Stark Bank APIs for E2E testing.
    
    Returns:
        dict: Dictionary with invoice_api and transfer_api mocks
    """
    return {
        "invoice_api": mock_stark_invoice_api,
        "transfer_api": mock_stark_transfer_api,
    }


class TestDatabaseConnectionAdapter:
    """
    Adapter to make TestDatabaseConnection work with repository.
    Provides get_db context manager that repositories expect.
    """
    def __init__(self, test_db_conn: TestDatabaseConnection):
        self._test_db = test_db_conn
    
    @contextmanager
    def get_db(self):
        """Context manager that yields the test connection."""
        try:
            yield self._test_db.connection
            self._test_db.connection.commit()
        except Exception as e:
            self._test_db.connection.rollback()
            raise


@pytest.fixture(scope="function")
def e2e_app(e2e_db, e2e_event_bus, mock_stark_api):
    """
    Create FastAPI application with E2E test dependencies.
    
    Overrides normal dependencies with test versions:
    - Uses isolated test database
    - Uses fresh EventBus
    - Uses mock Stark Bank APIs
    
    Args:
        e2e_db: Isolated test database
        e2e_event_bus: Fresh event bus
        mock_stark_api: Mock Stark Bank APIs
    
    Returns:
        TestClient: FastAPI test client
    """
    # Create adapter for test database
    db_adapter = TestDatabaseConnectionAdapter(e2e_db)
    
    # Create repositories with test database
    invoice_repository = InvoiceRepository(db_adapter)
    transfer_repository = TransferRepository(db_adapter)
    
    # Create services with mock APIs and test dependencies
    invoice_service = InvoiceService(
        repository=invoice_repository,
        stark_api=mock_stark_api["invoice_api"],
        event_bus=e2e_event_bus,
    )
    
    transfer_service = TransferService(
        repository=transfer_repository,
        stark_api=mock_stark_api["transfer_api"],
        event_bus=e2e_event_bus,
    )
    
    # Create and register TransferHandler to handle invoice.paid events
    transfer_handler = TransferHandler(
        service=transfer_service,
        invoice_repository=invoice_repository,
    )
    e2e_event_bus.subscribe("invoice.paid", transfer_handler.handle_invoice_paid)
    
    # Create mock webhook validator that always accepts signatures
    mock_validator = Mock(spec=WebhookValidator)
    mock_validator.validate_signature.return_value = True
    mock_validator.verify_signature.return_value = None  # verify_signature returns None on success
    
    # Create webhook receiver with test dependencies
    invoice_processor = InvoiceWebhookProcessor(
        invoice_repository=invoice_repository,
        event_bus=e2e_event_bus,
    )
    transfer_processor = TransferWebhookProcessor(
        transfer_repository=transfer_repository,
        event_bus=e2e_event_bus,
    )
    webhook_receiver = WebhookReceiver(
        validator=mock_validator,
        invoice_processor=invoice_processor,
        transfer_processor=transfer_processor,
        event_bus=e2e_event_bus,
    )
    
    # Store original factory singletons to restore later
    original_invoice_service = invoices_api_module._service
    original_transfer_service = transfers_api_module._service
    
    # Override the service singletons in API modules
    invoices_api_module._service = invoice_service
    transfers_api_module._service = transfer_service
    
    # Override the webhook receiver factory
    original_get_webhook_receiver = webhooks_api_module._get_webhook_receiver
    webhooks_api_module._get_webhook_receiver = lambda: webhook_receiver
    
    # Override FastAPI dependencies
    def override_get_db():
        yield e2e_db
    
    def override_get_event_bus():
        return e2e_event_bus
    
    def override_get_stark_invoice_api():
        return mock_stark_api["invoice_api"]
    
    def override_get_stark_transfer_api():
        return mock_stark_api["transfer_api"]
    
    # Apply dependency overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_event_bus] = override_get_event_bus
    app.dependency_overrides[get_stark_invoice_api] = override_get_stark_invoice_api
    app.dependency_overrides[get_stark_transfer_api] = override_get_stark_transfer_api
    
    # Create test client
    client = TestClient(app)
    
    # Expose mock_validator for tests that need to reconfigure it
    client._mock_validator = mock_validator
    
    yield client
    
    # Clean up: restore original singletons
    invoices_api_module._service = original_invoice_service
    transfers_api_module._service = original_transfer_service
    webhooks_api_module._get_webhook_receiver = original_get_webhook_receiver
    
    # Clear FastAPI overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_invoices():
    """
    Generate sample invoice data for E2E testing.
    
    Returns:
        list[dict]: List of sample invoice data dictionaries
    """
    return [
        {
            "amount": 50000,
            "customer_name": "João Silva",
            "customer_tax_id": "012.345.678-90",
            "customer_email": "joao.silva@example.com",
        },
        {
            "amount": 100000,
            "customer_name": "Maria Santos",
            "customer_tax_id": "987.654.321-00",
            "customer_email": "maria.santos@example.com",
        },
        {
            "amount": 75000,
            "customer_name": "Tech Solutions LTDA",
            "customer_tax_id": "11.222.333/0001-81",  # Valid CNPJ
            "customer_email": "contato@techsolutions.com",
        },
    ]


@pytest.fixture
def sample_invoice_models():
    """
    Generate sample InvoiceModel instances for E2E testing.
    
    Returns:
        list[InvoiceModel]: List of sample invoice models
    """
    return [
        InvoiceModel(
            id="invoice_001",
            amount=50000,
            customer_name="João Silva",
            customer_tax_id="012.345.678-90",
            customer_email="joao.silva@example.com",
            status=InvoiceStatus.CREATED,
            stark_invoice_id="stark_invoice_001",
        ),
        InvoiceModel(
            id="invoice_002",
            amount=100000,
            customer_name="Maria Santos",
            customer_tax_id="987.654.321-00",
            customer_email="maria.santos@example.com",
            status=InvoiceStatus.CREATED,
            stark_invoice_id="stark_invoice_002",
        ),
    ]


@pytest.fixture
def sample_webhook_invoice_paid():
    """
    Generate sample webhook payload for paid invoice.
    
    Returns:
        dict: Webhook payload for paid invoice
    """
    return {
        "event": {
            "id": "6589898251476992",
            "subscription": "invoice",
            "log": {
                "id": "5123328385236992",
                "created": "2024-01-15T10:30:00.000000+00:00",
                "type": "credited",
                "invoice": {
                    "id": "stark_invoice_001",
                    "amount": 50000,
                    "fee": 200,
                    "status": "paid",
                    "name": "João Silva",
                    "taxId": "012.345.678-90",
                },
            },
        }
    }


@pytest.fixture
def sample_webhook_transfer_success():
    """
    Generate sample webhook payload for successful transfer.
    
    Returns:
        dict: Webhook payload for successful transfer
    """
    return {
        "event": {
            "id": "7589898251476992",
            "subscription": "transfer",
            "log": {
                "id": "6123328385236992",
                "created": "2024-01-15T11:30:00.000000+00:00",
                "type": "success",
                "transfer": {
                    "id": "stark_transfer_001",
                    "amount": 49800,
                    "status": "success",
                    "externalId": "invoice-invoice_001",
                },
            },
        }
    }


@pytest.fixture
def sample_webhook_transfer_processing():
    """
    Generate sample webhook payload for transfer in processing status.
    
    Returns:
        dict: Webhook payload for transfer in processing status
    """
    return {
        "event": {
            "id": "9589898251476992",
            "subscription": "transfer",
            "log": {
                "id": "8123328385236992",
                "created": "2024-01-15T11:15:00.000000+00:00",
                "type": "processing",
                "transfer": {
                    "id": "stark_transfer_001",
                    "amount": 49800,
                    "status": "processing",
                    "externalId": "invoice-invoice_001",
                },
            },
        }
    }


@pytest.fixture
def sample_webhook_transfer_failed():
    """
    Generate sample webhook payload for failed transfer.
    
    Returns:
        dict: Webhook payload for failed transfer
    """
    return {
        "event": {
            "id": "8589898251476992",
            "subscription": "transfer",
            "log": {
                "id": "7123328385236992",
                "created": "2024-01-15T11:45:00.000000+00:00",
                "type": "failed",
                "transfer": {
                    "id": "stark_transfer_002",
                    "amount": 99800,
                    "status": "failed",
                    "externalId": "invoice-invoice_002",
                },
            },
        }
    }


@pytest.fixture
def api_key_header():
    """
    Generate API key header for authenticated requests.
    
    Returns:
        dict: Headers with API key
    """
    # Use test API key or the one from settings
    api_key = settings.admin_api_key or "test-api-key"
    return {"X-API-Key": api_key}
