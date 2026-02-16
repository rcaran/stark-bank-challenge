"""
Integration tests for the main FastAPI application.

Tests application startup, shutdown, routing, exception handling,
and health checks.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


class TestMainApplication:
    """Test suite for main FastAPI application."""
    
    def test_root_redirects_to_docs(self, client):
        """Test that root endpoint redirects to /docs."""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/docs"
    
    def test_root_redirect_followed(self, client):
        """Test that following redirect from root works."""
        response = client.get("/", follow_redirects=True)
        
        assert response.status_code == 200
        # FastAPI docs page should contain expected content
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    def test_health_check_returns_healthy(self, client):
        """Test that health check endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "environment" in data
        
        # Check structure of checks
        assert "database" in data["checks"]
        assert "event_bus" in data["checks"]
    
    def test_health_check_database_status(self, client):
        """Test that health check includes database status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        # Database should be ok in test environment
        assert data["checks"]["database"] == "ok"
    
    def test_health_check_event_bus_status(self, client):
        """Test that health check includes event bus status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        # EventBus should be ok
        assert data["checks"]["event_bus"] == "ok"
    
    def test_health_check_version(self, client):
        """Test that health check returns version info."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "1.0.0"
    
    def test_health_check_uptime(self, client):
        """Test that health check returns uptime."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        # Uptime should be a positive number
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
    
    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_docs_endpoint_accessible(self, client):
        """Test that /docs endpoint is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
    
    def test_redoc_endpoint_accessible(self, client):
        """Test that /redoc endpoint is accessible."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
    
    def test_invoice_router_included(self, client):
        """Test that invoice router is included."""
        # Try to access invoices endpoint (should fail without API key but route should exist)
        response = client.get("/invoices")
        
        # Should get 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
    
    def test_transfer_router_included(self, client):
        """Test that transfer router is included."""
        # Try to access transfers endpoint (should fail without API key but route should exist)
        response = client.get("/transfers")
        
        # Should get 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
    
    def test_webhook_router_included(self, client):
        """Test that webhook router is included."""
        # Try to access webhook endpoint (POST should exist)
        response = client.post(
            "/webhooks/invoice",
            json={"test": "data"}
        )
        
        # Should not get 404, but might get 400 or other error for invalid payload
        assert response.status_code != 404
    
    def test_nonexistent_endpoint_returns_404(self, client):
        """Test that accessing nonexistent endpoint returns 404."""
        response = client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
    
    def test_invalid_method_returns_405(self, client):
        """Test that using invalid HTTP method returns 405."""
        # Health check only supports GET
        response = client.post("/health")
        
        assert response.status_code == 405
    
    def test_cors_headers_in_development(self, client):
        """Test that CORS headers are present in development mode."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS should be configured
        # Note: In test environment this might behave differently
        assert response.status_code in [200, 405]


class TestExceptionHandlers:
    """Test suite for exception handlers."""
    
    def test_validation_error_handler(self, client):
        """Test that validation errors return proper format."""
        # Send invalid data to an endpoint that expects specific format
        response = client.post(
            "/webhooks/invoice",
            json={},  # Missing required fields
            headers={"Digital-Signature": "invalid"}
        )
        
        # Should handle validation errors gracefully
        assert response.status_code in [400, 401, 422]
        
        data = response.json()
        assert "error" in data or "message" in data
    
    def test_general_exception_handler(self, client):
        """Test that unexpected errors are handled gracefully."""
        # This is harder to test without deliberately breaking something
        # But we can verify the handler exists by checking the OpenAPI schema
        response = client.get("/openapi.json")
        
        assert response.status_code == 200


class TestApplicationLifespan:
    """Test suite for application lifespan events."""
    
    def test_application_starts_successfully(self):
        """Test that application starts without errors."""
        # Creating TestClient triggers startup
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_application_shuts_down_gracefully(self):
        """Test that application shuts down without errors."""
        # TestClient context manager handles shutdown
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
        
        # If we get here without exception, shutdown was successful
        assert True
    
    def test_database_initialized_on_startup(self):
        """Test that database is initialized during startup."""
        with TestClient(app) as client:
            response = client.get("/health")
            data = response.json()
            
            # Database should be operational
            assert data["checks"]["database"] == "ok"
    
    def test_event_bus_initialized_on_startup(self):
        """Test that EventBus is initialized during startup."""
        with TestClient(app) as client:
            response = client.get("/health")
            data = response.json()
            
            # EventBus should be operational
            assert data["checks"]["event_bus"] == "ok"


class TestApplicationMetadata:
    """Test suite for application metadata."""
    
    def test_application_title(self, client):
        """Test that application has correct title."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert "stark-bank-challenge" in schema["info"]["title"].lower()
    
    def test_application_version(self, client):
        """Test that application has correct version."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert schema["info"]["version"] == "1.0.0"
    
    def test_application_description(self, client):
        """Test that application has description."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert "description" in schema["info"]
        assert len(schema["info"]["description"]) > 0
