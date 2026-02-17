"""Integration tests for Transfer API endpoints."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.transfers.api import get_transfer_service, transfer_router
from src.modules.transfers.models import TransferModel, TransferStatus
from src.modules.transfers.service import TransferService
from src.shared.security.api_key import get_api_key_header

# Test app setup
app = FastAPI()
app.include_router(transfer_router)


@pytest.fixture
def mock_service():
    """Create mock transfer service."""
    return Mock(spec=TransferService)


@pytest.fixture
def mock_api_key():
    """Mock API key authentication that always returns a valid key."""

    def override():
        return "test-api-key-12345"

    return override


@pytest.fixture
def client(mock_service, mock_api_key):
    """Create test client with mocked service and auth."""
    app.dependency_overrides[get_transfer_service] = lambda: mock_service
    app.dependency_overrides[get_api_key_header] = mock_api_key
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(mock_service):
    """Create test client without auth override (for auth tests)."""
    app.dependency_overrides[get_transfer_service] = lambda: mock_service
    # Don't override auth - let it fail naturally
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def sample_transfer():
    """Create a sample transfer."""
    return TransferModel(
        id="test-transfer-id",
        invoice_id="test-invoice-id",
        stark_transfer_id="stark-transfer-123",
        external_id="invoice-test-invoice-id",
        amount=9500.00,  # Net amount after fees
        status=TransferStatus.CREATED,
    )


class TestListTransfersEndpoint:
    """Tests for GET /transfers endpoint."""

    def test_list_transfers_success(
        self, client, mock_service, sample_transfer, valid_api_key
    ):
        """Test successful transfer listing."""
        mock_service.list_transfers.return_value = [sample_transfer]
        mock_service.count_transfers.return_value = 1

        response = client.get(
            "/transfers",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["transfers"]) == 1
        assert data["transfers"][0]["id"] == "test-transfer-id"

    def test_list_transfers_with_status_filter(
        self, client, mock_service, sample_transfer, valid_api_key
    ):
        """Test listing transfers with status filter."""
        mock_service.list_transfers.return_value = [sample_transfer]
        mock_service.count_transfers.return_value = 1

        response = client.get(
            "/transfers?status=created",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        mock_service.list_transfers.assert_called_once_with(
            status="created", limit=100, offset=0
        )

    def test_list_transfers_with_pagination(self, client, mock_service, valid_api_key):
        """Test listing transfers with pagination."""
        mock_service.list_transfers.return_value = []
        mock_service.count_transfers.return_value = 0

        response = client.get(
            "/transfers?limit=50&offset=10",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 10

    def test_list_transfers_invalid_status(self, client, mock_service, valid_api_key):
        """Test listing transfers with invalid status."""
        response = client.get(
            "/transfers?status=invalid_status",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_transfers_without_api_key(self, client_no_auth):
        """Test listing transfers without API key."""
        response = client_no_auth.get("/transfers")
        assert response.status_code == 401


class TestGetTransferEndpoint:
    """Tests for GET /transfers/{transfer_id} endpoint."""

    def test_get_transfer_success(
        self, client, mock_service, sample_transfer, valid_api_key
    ):
        """Test getting transfer by ID."""
        mock_service.get_transfer.return_value = sample_transfer

        response = client.get(
            "/transfers/test-transfer-id",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-transfer-id"
        assert data["amount"] == 9500.00
        assert data["invoice_id"] == "test-invoice-id"

    def test_get_transfer_not_found(self, client, mock_service, valid_api_key):
        """Test getting non-existent transfer."""
        mock_service.get_transfer.return_value = None

        response = client.get(
            "/transfers/nonexistent",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 404
        assert "Transfer not found" in response.json()["detail"]

    def test_get_transfer_without_api_key(self, client_no_auth):
        """Test getting transfer without API key."""
        response = client_no_auth.get("/transfers/test-id")
        assert response.status_code == 401


class TestGetTransferByInvoiceEndpoint:
    """Tests for GET /transfers/invoice/{invoice_id} endpoint."""

    def test_get_transfer_by_invoice_success(
        self, client, mock_service, sample_transfer, valid_api_key
    ):
        """Test getting transfer by invoice ID."""
        mock_service.get_transfer_by_invoice.return_value = sample_transfer

        response = client.get(
            "/transfers/invoice/test-invoice-id",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-transfer-id"
        assert data["invoice_id"] == "test-invoice-id"
        assert data["amount"] == 9500.00

    def test_get_transfer_by_invoice_not_found(
        self, client, mock_service, valid_api_key
    ):
        """Test getting transfer for non-existent invoice."""
        mock_service.get_transfer_by_invoice.return_value = None

        response = client.get(
            "/transfers/invoice/nonexistent",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 404
        assert "Transfer not found for invoice" in response.json()["detail"]

    def test_get_transfer_by_invoice_without_api_key(self, client_no_auth):
        """Test getting transfer by invoice without API key."""
        response = client_no_auth.get("/transfers/invoice/test-invoice-id")
        assert response.status_code == 401


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_all_endpoints_require_auth(self, client_no_auth):
        """Test that all endpoints require authentication."""
        endpoints = [
            ("GET", "/transfers"),
            ("GET", "/transfers/test-id"),
            ("GET", "/transfers/invoice/test-invoice-id"),
        ]

        for method, path in endpoints:
            response = client_no_auth.get(path)
            assert response.status_code == 401, f"{method} {path} should require auth"
