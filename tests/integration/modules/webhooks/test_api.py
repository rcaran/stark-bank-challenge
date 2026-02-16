"""
Integration tests for Webhook API Endpoints.

Tests the webhook endpoints with FastAPI TestClient, validating
the full request/response flow including signature validation.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.webhooks.api import webhook_router

# Disable pytest-flask fixtures for FastAPI tests
pytest_plugins = []


@pytest.fixture
def app():
    """Create FastAPI application with webhook router."""
    app = FastAPI()
    app.include_router(webhook_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_invoice_webhook_payload():
    """Sample invoice webhook payload."""
    return {
        "event": {
            "id": "6589898251476992",
            "subscription": "invoice",
            "log": {
                "id": "5123328385236992",
                "created": "2024-01-15T10:30:00.000000+00:00",
                "type": "credited",
                "invoice": {
                    "id": "5730903989420032",
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
def sample_transfer_webhook_payload():
    """Sample transfer webhook payload."""
    return {
        "event": {
            "id": "7589898251476992",
            "subscription": "transfer",
            "log": {
                "id": "6123328385236992",
                "created": "2024-01-15T11:30:00.000000+00:00",
                "type": "success",
                "transfer": {
                    "id": "6730903989420032",
                    "amount": 49800,
                    "status": "success",
                    "externalId": "invoice-12345",
                },
            },
        }
    }


class TestInvoiceWebhookEndpoint:
    """Tests for POST /webhooks/invoice endpoint."""

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_invoice_webhook_success(
        self, mock_get_receiver, client, sample_invoice_webhook_payload
    ):
        """Test successful invoice webhook request."""
        # Arrange
        mock_receiver = Mock()
        mock_receiver.receive_invoice_webhook.return_value = {"status": "ok"}
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_invoice_webhook_payload)
        signature = "valid_signature"

        # Act
        response = client.post(
            "/webhooks/invoice",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_receiver.receive_invoice_webhook.assert_called_once()

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_invoice_webhook_missing_signature(
        self, mock_get_receiver, client, sample_invoice_webhook_payload
    ):
        """Test invoice webhook without signature header."""
        # Arrange
        payload = json.dumps(sample_invoice_webhook_payload)

        # Act
        response = client.post(
            "/webhooks/invoice",
            content=payload,
        )

        # Assert
        # Unprocessable Entity (missing required header)
        assert response.status_code == 422

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_invoice_webhook_invalid_signature_returns_401(
        self, mock_get_receiver, client, sample_invoice_webhook_payload
    ):
        """Test invoice webhook with invalid signature returns 401."""
        # Arrange
        from src.shared.security.signature import InvalidSignatureError

        mock_receiver = Mock()
        mock_receiver.receive_invoice_webhook.side_effect = InvalidSignatureError(
            "Invalid signature"
        )
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_invoice_webhook_payload)
        signature = "invalid_signature"

        # Act
        response = client.post(
            "/webhooks/invoice",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["message"]

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_invoice_webhook_processing_error_returns_200(
        self, mock_get_receiver, client, sample_invoice_webhook_payload
    ):
        """Test invoice webhook with processing error still returns 200."""
        # Arrange
        mock_receiver = Mock()
        mock_receiver.receive_invoice_webhook.side_effect = Exception("Database error")
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_invoice_webhook_payload)
        signature = "valid_signature"

        # Act
        response = client.post(
            "/webhooks/invoice",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        # Should return 200 to prevent Stark Bank retries
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "error" in data


class TestTransferWebhookEndpoint:
    """Tests for POST /webhooks/transfer endpoint."""

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_transfer_webhook_success(
        self, mock_get_receiver, client, sample_transfer_webhook_payload
    ):
        """Test successful transfer webhook request."""
        # Arrange
        mock_receiver = Mock()
        mock_receiver.receive_transfer_webhook.return_value = {"status": "ok"}
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_transfer_webhook_payload)
        signature = "valid_signature"

        # Act
        response = client.post(
            "/webhooks/transfer",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_receiver.receive_transfer_webhook.assert_called_once()

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_transfer_webhook_missing_signature(
        self, mock_get_receiver, client, sample_transfer_webhook_payload
    ):
        """Test transfer webhook without signature header."""
        # Arrange
        payload = json.dumps(sample_transfer_webhook_payload)

        # Act
        response = client.post(
            "/webhooks/transfer",
            content=payload,
        )

        # Assert
        assert response.status_code == 422  # Unprocessable Entity

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_transfer_webhook_invalid_signature_returns_401(
        self, mock_get_receiver, client, sample_transfer_webhook_payload
    ):
        """Test transfer webhook with invalid signature returns 401."""
        # Arrange
        from src.shared.security.signature import InvalidSignatureError

        mock_receiver = Mock()
        mock_receiver.receive_transfer_webhook.side_effect = InvalidSignatureError(
            "Invalid signature"
        )
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_transfer_webhook_payload)
        signature = "invalid_signature"

        # Act
        response = client.post(
            "/webhooks/transfer",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["message"]

    @patch("src.modules.webhooks.api._get_webhook_receiver")
    def test_transfer_webhook_processing_error_returns_200(
        self, mock_get_receiver, client, sample_transfer_webhook_payload
    ):
        """Test transfer webhook with processing error still returns 200."""
        # Arrange
        mock_receiver = Mock()
        mock_receiver.receive_transfer_webhook.side_effect = Exception("Database error")
        mock_get_receiver.return_value = mock_receiver

        payload = json.dumps(sample_transfer_webhook_payload)
        signature = "valid_signature"

        # Act
        response = client.post(
            "/webhooks/transfer",
            content=payload,
            headers={"Digital-Signature": signature},
        )

        # Assert
        # Should return 200 to prevent Stark Bank retries
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "error" in data


class TestWebhookHealthEndpoint:
    """Tests for GET /webhooks/health endpoint."""

    def test_webhook_health_check(self, client):
        """Test webhook health check endpoint."""
        # Act
        response = client.get("/webhooks/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhooks"


class TestWebhookAPIDocumentation:
    """Tests for API documentation."""

    def test_openapi_schema_generated(self, app):
        """Test that OpenAPI schema is generated correctly."""
        # Act
        schema = app.openapi()

        # Assert
        assert "paths" in schema
        assert "/webhooks/invoice" in schema["paths"]
        assert "/webhooks/transfer" in schema["paths"]
        assert "/webhooks/health" in schema["paths"]

    def test_webhook_endpoints_have_proper_documentation(self, app):
        """Test that webhook endpoints have proper documentation."""
        # Act
        schema = app.openapi()

        # Assert
        invoice_endpoint = schema["paths"]["/webhooks/invoice"]["post"]
        assert "summary" in invoice_endpoint
        assert "description" in invoice_endpoint
        assert "responses" in invoice_endpoint

        transfer_endpoint = schema["paths"]["/webhooks/transfer"]["post"]
        assert "summary" in transfer_endpoint
        assert "description" in transfer_endpoint
        assert "responses" in transfer_endpoint
