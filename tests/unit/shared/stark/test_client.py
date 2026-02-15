import pytest
from unittest.mock import MagicMock
import starkbank
from src.shared.stark.client import StarkBankClient
from src.shared.utils.errors import AuthenticationError, ValidationError, StarkBankError

@pytest.fixture
def mock_starkbank_project(mocker):
    return mocker.patch("starkbank.Project")

@pytest.fixture
def mock_starkbank_user(mocker):
    return mocker.patch("starkbank.user")

def test_client_initialization(mock_starkbank_project, mock_starkbank_user, mocker):
    mock_settings = mocker.patch("src.shared.stark.client.settings")
    mock_settings.starkbank_project_id = "project-123"
    mock_settings.starkbank_private_key_content = "private-key"
    mock_settings.starkbank_environment = "sandbox"
    
    client = StarkBankClient()
    
    mock_starkbank_project.assert_called_once_with(
        environment="sandbox",
        id="project-123",
        private_key="private-key"
    )
    # Verify checking user (which initializes SDK)
    assert client.check_user == mock_starkbank_project.return_value

def test_handle_stark_error_input(mocker):
    client = StarkBankClient()
    
    class MockInputErrors(Exception):
        pass

    mocker.patch("src.shared.stark.client.InputErrors", MockInputErrors)
    
    mock_error = MockInputErrors()
    mock_error.errors = [MagicMock(message="Invalid field")]

    with pytest.raises(ValidationError) as excinfo:
        client.handle_stark_error(mock_error)
    
    assert "Invalid field" in str(excinfo.value.details)

def test_handle_stark_error_generic():
    client = StarkBankClient()
    error = Exception("Unknown error")
    with pytest.raises(StarkBankError):
        client.handle_stark_error(error)
