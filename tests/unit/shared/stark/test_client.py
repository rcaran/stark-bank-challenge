from unittest.mock import MagicMock

import pytest

from src.shared.stark.client import StarkBankClient
from src.shared.utils.errors import StarkBankError, ValidationError


@pytest.fixture
def mock_starkbank_project(mocker):
    return mocker.patch("starkbank.Project")


@pytest.fixture
def mock_starkbank_user(mocker):
    return mocker.patch("starkbank.user")


def test_client_initialization(mock_starkbank_project, mocker):
    mock_settings = mocker.patch("src.shared.stark.client.settings")
    mock_settings.starkbank_project_id = "project-123"
    mock_settings.starkbank_private_key_content = "private-key"
    mock_settings.starkbank_environment = "sandbox"

    # Ensure starkbank.user is None so lazy init triggers
    mocker.patch("starkbank.user", None)

    client = StarkBankClient()
    # Trigger lazy SDK initialization via check_user
    _ = client.check_user

    mock_starkbank_project.assert_called_once_with(
        environment="sandbox", id="project-123", private_key="private-key"
    )
    # Verify checking user (which initializes SDK)
    assert client.check_user == mock_starkbank_project.return_value


def test_handle_stark_error_input(mocker):
    mocker.patch("src.shared.stark.client.settings")
    mocker.patch("src.shared.stark.client.StarkBankClient._initialize_sdk")
    client = StarkBankClient()

    class MockInputError(Exception):
        pass

    mocker.patch("src.shared.stark.client.InputErrors", MockInputError)

    mock_error = MockInputError()
    mock_error.errors = [MagicMock(message="Invalid field")]

    with pytest.raises(ValidationError) as excinfo:
        client.handle_stark_error(mock_error)

    assert "Invalid field" in str(excinfo.value.details)


def test_handle_stark_error_generic():
    from unittest.mock import patch

    with (
        patch("src.shared.stark.client.settings"),
        patch("src.shared.stark.client.StarkBankClient._initialize_sdk"),
    ):
        client = StarkBankClient()
    error = Exception("Unknown error")
    with pytest.raises(StarkBankError):
        client.handle_stark_error(error)
