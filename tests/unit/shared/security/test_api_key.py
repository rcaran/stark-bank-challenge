"""
Unit tests for API Key authentication module.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.shared.security.api_key import (
    APIKeyHeader,
    InvalidAPIKeyError,
    get_api_key_dependency,
    get_api_key_header,
    verify_api_key,
)
from src.shared.utils.errors import AuthenticationError


class TestVerifyAPIKey:
    """Tests for the verify_api_key function."""

    def test_verify_api_key_valid(self):
        """Test that a valid API key is accepted."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            result = verify_api_key("valid-test-key")

            assert result is True

    def test_verify_api_key_invalid(self):
        """Test that an invalid API key is rejected."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            result = verify_api_key("invalid-test-key")

            assert result is False

    def test_verify_api_key_empty_string(self):
        """Test that an empty API key is rejected."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            result = verify_api_key("")

            assert result is False

    def test_verify_api_key_none(self):
        """Test that None API key is rejected."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            result = verify_api_key(None)

            assert result is False

    def test_verify_api_key_no_configured_key(self):
        """Test behavior when ADMIN_API_KEY is not configured."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = None

            result = verify_api_key("any-key")

            assert result is False

    def test_verify_api_key_constant_time_comparison(self):
        """Test that constant-time comparison is used (secrets.compare_digest)."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            with patch(
                "src.shared.security.api_key.secrets.compare_digest"
            ) as mock_compare:
                mock_compare.return_value = True

                result = verify_api_key("valid-test-key")

                assert result is True
                mock_compare.assert_called_once_with("valid-test-key", "valid-test-key")

    def test_verify_api_key_exception_handling(self):
        """Test that exceptions during verification are handled gracefully."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            with patch(
                "src.shared.security.api_key.secrets.compare_digest"
            ) as mock_compare:
                mock_compare.side_effect = Exception("Unexpected error")

                result = verify_api_key("valid-test-key")

                assert result is False

    def test_verify_api_key_logging_success(self, caplog):
        """Test that successful verification is logged."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            verify_api_key("valid-test-key")

            # Check that success was logged
            assert any(
                "successful" in record.message.lower() for record in caplog.records
            )

    def test_verify_api_key_logging_failure(self, caplog):
        """Test that failed verification is logged."""
        with patch("src.shared.security.api_key.settings") as mock_settings:
            mock_settings.admin_api_key = "valid-test-key"

            verify_api_key("invalid-test-key")

            # Check that failure was logged
            assert any(
                "failed" in record.message.lower()
                or "mismatch" in record.message.lower()
                for record in caplog.records
            )


class TestGetAPIKeyHeader:
    """Tests for the get_api_key_header FastAPI dependency."""

    def test_get_api_key_header_valid(self):
        """Test that valid API key from header is accepted."""
        with patch("src.shared.security.api_key.verify_api_key") as mock_verify:
            mock_verify.return_value = True

            result = get_api_key_header("valid-test-key")

            assert result == "valid-test-key"
            mock_verify.assert_called_once_with("valid-test-key")

    def test_get_api_key_header_invalid(self):
        """Test that invalid API key from header raises HTTPException."""
        with patch("src.shared.security.api_key.verify_api_key") as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                get_api_key_header("invalid-test-key")

            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail

    def test_get_api_key_header_missing(self):
        """Test that missing API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            get_api_key_header(None)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    def test_get_api_key_header_empty_string(self):
        """Test that empty API key string raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            get_api_key_header("")

        assert exc_info.value.status_code == 401

    def test_get_api_key_dependency_alias(self):
        """Test that get_api_key_dependency is an alias for get_api_key_header."""
        assert get_api_key_dependency is get_api_key_header


class TestAPIKeyHeader:
    """Tests for the APIKeyHeader callable class."""

    def test_api_key_header_callable_valid(self):
        """Test that APIKeyHeader instance is callable and validates correctly."""
        with patch("src.shared.security.api_key.verify_api_key") as mock_verify:
            mock_verify.return_value = True

            api_key_header = APIKeyHeader()
            result = api_key_header("valid-test-key")

            assert result == "valid-test-key"

    def test_api_key_header_callable_invalid(self):
        """Test that APIKeyHeader raises HTTPException for invalid key."""
        with patch("src.shared.security.api_key.verify_api_key") as mock_verify:
            mock_verify.return_value = False

            api_key_header = APIKeyHeader()

            with pytest.raises(HTTPException) as exc_info:
                api_key_header("invalid-test-key")

            assert exc_info.value.status_code == 401


class TestInvalidAPIKeyError:
    """Tests for the InvalidAPIKeyError exception."""

    def test_invalid_api_key_error_inheritance(self):
        """Test that InvalidAPIKeyError inherits from AuthenticationError."""
        error = InvalidAPIKeyError()

        assert isinstance(error, AuthenticationError)
        assert isinstance(error, Exception)

    def test_invalid_api_key_error_default_message(self):
        """Test default error message."""
        error = InvalidAPIKeyError()

        assert "Invalid API key" in str(error)

    def test_invalid_api_key_error_custom_message(self):
        """Test custom error message."""
        error = InvalidAPIKeyError("Custom error message")

        assert "Custom error message" in str(error)
