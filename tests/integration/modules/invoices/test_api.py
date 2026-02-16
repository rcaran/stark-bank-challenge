"""Integration tests for Invoice API endpoints."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.invoices.api import get_invoice_service, invoice_router
from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.service import InvoiceService
from src.shared.security.api_key import get_api_key_header

# Test app setup
app = FastAPI()
app.include_router(invoice_router)


@pytest.fixture
def mock_service():
    """Create mock invoice service."""
    return Mock(spec=InvoiceService)


@pytest.fixture
def mock_api_key():
    """Mock API key authentication that always returns a valid key."""
    def override():
        return "test-api-key-12345"
    return override


@pytest.fixture
def client(mock_service, mock_api_key):
    """Create test client with mocked service and auth."""
    app.dependency_overrides[get_invoice_service] = lambda: mock_service
    app.dependency_overrides[get_api_key_header] = mock_api_key
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(mock_service):
    """Create test client without auth override (for auth tests)."""
    app.dependency_overrides[get_invoice_service] = lambda: mock_service
    # Don't override auth - let it fail naturally
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def sample_invoice():
    """Create a sample invoice."""
    return InvoiceModel(
        id="test-invoice-id",
        stark_invoice_id="stark-123",
        amount=10000,
        customer_name="Test User",
        customer_tax_id="529.982.247-25",
        customer_email="test@example.com",
        status=InvoiceStatus.CREATED,
    )


class TestCreateInvoiceEndpoint:
    """Tests for POST /invoices endpoint."""

    def test_create_invoice_success(
        self, client, mock_service, sample_invoice, valid_api_key
    ):
        """Test successful invoice creation."""
        mock_service.create_invoice.return_value = sample_invoice

        response = client.post(
            "/invoices",
            json={
                "amount": 10000,
                "customer_name": "Test User",
                "customer_tax_id": "529.982.247-25",
                "customer_email": "test@example.com",
            },
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-invoice-id"
        assert data["stark_invoice_id"] == "stark-123"
        assert data["amount"] == 10000
        assert data["status"] == "created"

    def test_create_invoice_missing_field(
        self, client, valid_api_key
    ):
        """Test creating invoice with missing required field."""
        response = client.post(
            "/invoices",
            json={
                "amount": 10000,
                "customer_name": "Test User",
                # missing customer_tax_id
                "customer_email": "test@example.com",
            },
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 422  # Validation error

    def test_create_invoice_invalid_amount(
        self, client, valid_api_key
    ):
        """Test creating invoice with invalid amount."""
        response = client.post(
            "/invoices",
            json={
                "amount": 0,  # Invalid
                "customer_name": "Test User",
                "customer_tax_id": "529.982.247-25",
                "customer_email": "test@example.com",
            },
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 422

    def test_create_invoice_without_api_key(self, client_no_auth):
        """Test creating invoice without API key."""
        response = client_no_auth.post(
            "/invoices",
            json={
                "amount": 10000,
                "customer_name": "Test User",
                "customer_tax_id": "529.982.247-25",
                "customer_email": "test@example.com",
            },
        )

        assert response.status_code == 401


class TestListInvoicesEndpoint:
    """Tests for GET /invoices endpoint."""

    def test_list_invoices_success(
        self, client, mock_service, sample_invoice, valid_api_key
    ):
        """Test successful invoice listing."""
        mock_service.list_invoices.return_value = [sample_invoice]
        mock_service.count_invoices.return_value = 1

        response = client.get(
            "/invoices",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["id"] == "test-invoice-id"

    def test_list_invoices_with_status_filter(
        self, client, mock_service, sample_invoice, valid_api_key
    ):
        """Test listing invoices with status filter."""
        mock_service.list_invoices.return_value = [sample_invoice]
        mock_service.count_invoices.return_value = 1

        response = client.get(
            "/invoices?status=created",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        mock_service.list_invoices.assert_called_once_with(
            status="created", limit=100, offset=0
        )

    def test_list_invoices_with_pagination(
        self, client, mock_service, valid_api_key
    ):
        """Test listing invoices with pagination."""
        mock_service.list_invoices.return_value = []
        mock_service.count_invoices.return_value = 0

        response = client.get(
            "/invoices?limit=50&offset=10",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 10

    def test_list_invoices_invalid_status(
        self, client, mock_service, valid_api_key
    ):
        """Test listing invoices with invalid status."""
        response = client.get(
            "/invoices?status=invalid_status",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_invoices_without_api_key(self, client_no_auth):
        """Test listing invoices without API key."""
        response = client_no_auth.get("/invoices")
        assert response.status_code == 401


class TestGetInvoiceEndpoint:
    """Tests for GET /invoices/{invoice_id} endpoint."""

    def test_get_invoice_success(
        self, client, mock_service, sample_invoice, valid_api_key
    ):
        """Test getting invoice by ID."""
        mock_service.get_invoice.return_value = sample_invoice

        response = client.get(
            "/invoices/test-invoice-id",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-invoice-id"
        assert data["amount"] == 10000

    def test_get_invoice_not_found(
        self, client, mock_service, valid_api_key
    ):
        """Test getting non-existent invoice."""
        mock_service.get_invoice.return_value = None

        response = client.get(
            "/invoices/nonexistent",
            headers={"X-API-Key": valid_api_key},
        )

        assert response.status_code == 404
        assert "Invoice not found" in response.json()["detail"]

    def test_get_invoice_without_api_key(self, client_no_auth):
        """Test getting invoice without API key."""
        response = client_no_auth.get("/invoices/test-id")
        assert response.status_code == 401


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_all_endpoints_require_auth(self, client_no_auth):
        """Test that all endpoints require authentication."""
        endpoints = [
            ("POST", "/invoices"),
            ("GET", "/invoices"),
            ("GET", "/invoices/test-id"),
        ]

        for method, path in endpoints:
            if method == "POST":
                response = client_no_auth.post(path, json={})
            else:
                response = client_no_auth.get(path)

            assert response.status_code == 401, f"{method} {path} should require auth"
