"""
E2E Test Infrastructure - Helper Functions.

This module provides helper functions for end-to-end testing:
- Creating test data via API
- Simulating webhooks with signatures
- Waiting for events
- Assertions for complex scenarios
"""

import json
import time
from contextlib import contextmanager
from typing import Any, Optional
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.repository import TransferRepository
from src.shared.events.bus import EventBus
from src.shared.events.types import Event
from src.shared.utils.logger import get_logger

logger = get_logger("tests.e2e.helpers")


class TestDbAdapter:
    """Adapter to make db_connection work with repository."""
    
    def __init__(self, test_db_conn):
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


def create_test_invoice(
    client: TestClient,
    invoice_data: dict,
    api_key: str = "test-api-key"
) -> dict:
    """
    Create an invoice via API for E2E testing.
    
    Args:
        client: FastAPI TestClient
        invoice_data: Invoice data dictionary
        api_key: API key for authentication
    
    Returns:
        dict: Created invoice response
    
    Raises:
        AssertionError: If invoice creation fails
    """
    logger.info(f"Creating test invoice for {invoice_data.get('customer_name')}")
    
    response = client.post(
        "/invoices",
        json=invoice_data,
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 201, f"Failed to create invoice: {response.text}"
    
    invoice = response.json()
    logger.info(f"Created test invoice: {invoice.get('id')}")
    
    return invoice


def simulate_webhook(
    client: TestClient,
    webhook_type: str,
    payload: dict,
    signature: str = "mock_valid_signature"
) -> dict:
    """
    Simulate a webhook request with proper signature.
    
    Args:
        client: FastAPI TestClient
        webhook_type: Type of webhook ('invoice' or 'transfer')
        payload: Webhook payload dictionary
        signature: Digital signature (defaults to mock signature)
    
    Returns:
        dict: Webhook response
    
    Raises:
        AssertionError: If webhook processing fails
    """
    logger.info(f"Simulating {webhook_type} webhook")
    
    # Determine endpoint
    endpoint = f"/webhooks/{webhook_type}"
    
    # Prepare request
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Make request
    response = client.post(
        endpoint,
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Digital-Signature": signature
        }
    )
    
    assert response.status_code == 200, f"Webhook failed: {response.text}"
    
    result = response.json()
    logger.info(f"Webhook processed successfully: {result}")
    
    return result


def simulate_webhook_raw(
    client: TestClient,
    webhook_type: str,
    payload: dict,
    signature: str = "mock_valid_signature"
):
    """
    Simulate a webhook request and return raw Response (without status assertion).
    
    This variant of simulate_webhook returns the complete Response object
    without asserting status 200. Useful for testing error scenarios where
    we expect status codes like 401, 403, 500, etc.
    
    Args:
        client: FastAPI TestClient
        webhook_type: Type of webhook ('invoice' or 'transfer')
        payload: Webhook payload dictionary
        signature: Digital signature (defaults to mock signature)
    
    Returns:
        Response: Complete Response object with status_code, text, json(), etc.
    """
    logger.info(f"Simulating {webhook_type} webhook (raw response)")
    
    # Determine endpoint
    endpoint = f"/webhooks/{webhook_type}"
    
    # Prepare request
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Make request and return raw response
    response = client.post(
        endpoint,
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Digital-Signature": signature
        }
    )
    
    logger.info(f"Webhook response status: {response.status_code}")
    
    return response


def wait_for_event(
    event_bus: EventBus,
    event_type: str,
    timeout: float = 5.0,
    poll_interval: float = 0.1
) -> Optional[Event]:
    """
    Wait for an event to be published on the event bus.
    
    This is useful for E2E tests that need to verify asynchronous
    event processing.
    
    Args:
        event_bus: EventBus instance to monitor
        event_type: Type of event to wait for
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
    
    Returns:
        Event if found, None if timeout
    """
    logger.info(f"Waiting for event: {event_type}")
    
    # Store captured events
    captured_events = []
    
    # Create event capture handler
    def capture_handler(event: Event):
        captured_events.append(event)
    
    # Subscribe to event
    event_bus.subscribe(event_type, capture_handler)
    
    # Wait for event with timeout
    elapsed = 0.0
    while elapsed < timeout:
        if captured_events:
            event = captured_events[0]
            logger.info(f"Event received: {event_type} ({event.event_id})")
            event_bus.unsubscribe(event_type, capture_handler)
            return event
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    # Cleanup
    event_bus.unsubscribe(event_type, capture_handler)
    
    logger.warning(f"Timeout waiting for event: {event_type}")
    return None


def assert_invoice_exists(
    db_connection,
    invoice_id: str,
    expected_status: Optional[InvoiceStatus] = None
) -> InvoiceModel:
    """
    Assert that an invoice exists in the database with expected status.
    
    Args:
        db_connection: Database connection
        invoice_id: Invoice ID to check
        expected_status: Expected invoice status (optional)
    
    Returns:
        InvoiceModel: The found invoice
    
    Raises:
        AssertionError: If invoice not found or status doesn't match
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = InvoiceRepository(db_adapter)
    invoice = repository.get_by_id(invoice_id)
    
    assert invoice is not None, f"Invoice not found: {invoice_id}"
    
    if expected_status is not None:
        assert invoice.status == expected_status, \
            f"Invoice {invoice_id} status mismatch: expected {expected_status}, got {invoice.status}"
    
    logger.info(f"Invoice assertion passed: {invoice_id} (status: {invoice.status})")
    
    return invoice


def assert_transfer_created(
    db_connection,
    invoice_id: str,
    expected_status: Optional[TransferStatus] = None,
    expected_amount: Optional[float] = None
) -> TransferModel:
    """
    Assert that a transfer was created for an invoice.
    
    Args:
        db_connection: Database connection
        invoice_id: Invoice ID that should have a transfer
        expected_status: Expected transfer status (optional)
        expected_amount: Expected transfer amount (optional)
    
    Returns:
        TransferModel: The found transfer
    
    Raises:
        AssertionError: If transfer not found or doesn't match expectations
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    transfer = repository.get_by_invoice_id(invoice_id)
    
    assert transfer is not None, f"Transfer not found for invoice: {invoice_id}"
    
    if expected_status is not None:
        assert transfer.status == expected_status, \
            f"Transfer status mismatch: expected {expected_status}, got {transfer.status}"
    
    if expected_amount is not None:
        assert transfer.amount == expected_amount, \
            f"Transfer amount mismatch: expected {expected_amount}, got {transfer.amount}"
    
    logger.info(
        f"Transfer assertion passed for invoice {invoice_id}: "
        f"transfer_id={transfer.id}, status={transfer.status}, amount={transfer.amount}"
    )
    
    return transfer


def assert_transfer_not_exists(
    db_connection,
    invoice_id: str
) -> None:
    """
    Assert that no transfer exists for an invoice.
    
    Args:
        db_connection: Database connection
        invoice_id: Invoice ID that should not have a transfer
    
    Raises:
        AssertionError: If transfer is found
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    transfer = repository.get_by_invoice_id(invoice_id)
    
    assert transfer is None, f"Unexpected transfer found for invoice: {invoice_id}"
    
    logger.info(f"Transfer non-existence assertion passed for invoice: {invoice_id}")


def assert_invoice_paid(
    db_connection,
    invoice_id: str,
    expected_net_amount: Optional[float] = None
) -> InvoiceModel:
    """
    Assert that an invoice is marked as paid with correct details.
    
    Args:
        db_connection: Database connection
        invoice_id: Invoice ID to check
        expected_net_amount: Expected net amount after fees (optional)
    
    Returns:
        InvoiceModel: The paid invoice
    
    Raises:
        AssertionError: If invoice not paid or net_amount doesn't match
    """
    invoice = assert_invoice_exists(db_connection, invoice_id, InvoiceStatus.PAID)
    
    assert invoice.paid_at is not None, f"Invoice {invoice_id} missing paid_at timestamp"
    assert invoice.fee is not None, f"Invoice {invoice_id} missing fee"
    assert invoice.net_amount is not None, f"Invoice {invoice_id} missing net_amount"
    
    if expected_net_amount is not None:
        assert invoice.net_amount == expected_net_amount, \
            f"Net amount mismatch: expected {expected_net_amount}, got {invoice.net_amount}"
    
    logger.info(
        f"Invoice paid assertion passed: {invoice_id} "
        f"(amount: {invoice.amount}, fee: {invoice.fee}, net: {invoice.net_amount})"
    )
    
    return invoice


def assert_transfer_completed(
    db_connection,
    transfer_id: str
) -> TransferModel:
    """
    Assert that a transfer is completed successfully.
    
    Args:
        db_connection: Database connection
        transfer_id: Transfer ID to check
    
    Returns:
        TransferModel: The completed transfer
    
    Raises:
        AssertionError: If transfer not completed
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    transfer = repository.get_by_id(transfer_id)
    
    assert transfer is not None, f"Transfer not found: {transfer_id}"
    assert transfer.status == TransferStatus.SUCCESS, \
        f"Transfer not completed: status is {transfer.status}"
    assert transfer.completed_at is not None, \
        f"Transfer {transfer_id} missing completed_at timestamp"
    
    logger.info(f"Transfer completed assertion passed: {transfer_id}")
    
    return transfer


def assert_transfer_failed(
    db_connection,
    transfer_id: str,
    expect_error_message: bool = True
) -> TransferModel:
    """
    Assert that a transfer failed.
    
    Args:
        db_connection: Database connection
        transfer_id: Transfer ID to check
        expect_error_message: Whether to expect an error message
    
    Returns:
        TransferModel: The failed transfer
    
    Raises:
        AssertionError: If transfer not failed or missing error message
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    transfer = repository.get_by_id(transfer_id)
    
    assert transfer is not None, f"Transfer not found: {transfer_id}"
    assert transfer.status == TransferStatus.FAILED, \
        f"Transfer not failed: status is {transfer.status}"
    
    if expect_error_message:
        assert transfer.error_message is not None, \
            f"Transfer {transfer_id} missing error_message"
    
    logger.info(
        f"Transfer failed assertion passed: {transfer_id} "
        f"(error: {transfer.error_message})"
    )
    
    return transfer


def get_invoice_by_stark_id(
    db_connection,
    stark_invoice_id: str
) -> Optional[InvoiceModel]:
    """
    Get invoice by Stark Bank invoice ID.
    
    Args:
        db_connection: Database connection
        stark_invoice_id: Stark Bank invoice ID
    
    Returns:
        InvoiceModel if found, None otherwise
    """
    repository = InvoiceRepository()
    return repository.get_by_stark_id(stark_invoice_id, db_connection)


def get_transfer_by_stark_id(
    db_connection,
    stark_transfer_id: str
) -> Optional[TransferModel]:
    """
    Get transfer by Stark Bank transfer ID.
    
    Args:
        db_connection: Database connection
        stark_transfer_id: Stark Bank transfer ID
    
    Returns:
        TransferModel if found, None otherwise
    """
    repository = TransferRepository()
    return repository.get_by_stark_id(stark_transfer_id, db_connection)


def count_invoices_by_status(
    db_connection,
    status: InvoiceStatus
) -> int:
    """
    Count invoices with a specific status.
    
    Args:
        db_connection: Database connection
        status: Invoice status to count
    
    Returns:
        int: Number of invoices with the status
    """
    repository = InvoiceRepository()
    return repository.count(status=status.value, conn=db_connection)


def count_transfers_by_status(
    db_connection,
    status: TransferStatus
) -> int:
    """
    Count transfers with a specific status.
    
    Args:
        db_connection: Database connection
        status: Transfer status to count
    
    Returns:
        int: Number of transfers with the status
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    return repository.count(status=status.value)


def list_all_invoices(db_connection) -> list[InvoiceModel]:
    """
    List all invoices in the database.
    
    Args:
        db_connection: Database connection
    
    Returns:
        list[InvoiceModel]: All invoices
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = InvoiceRepository(db_adapter)
    return repository.list(limit=1000, offset=0)


def list_all_transfers(db_connection) -> list[TransferModel]:
    """
    List all transfers in the database.
    
    Args:
        db_connection: Database connection
    
    Returns:
        list[TransferModel]: All transfers
    """
    db_adapter = TestDbAdapter(db_connection)
    repository = TransferRepository(db_adapter)
    return repository.list(limit=1000, offset=0)
