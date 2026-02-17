from datetime import date
from unittest.mock import MagicMock

import pytest

from src.shared.stark.transfer_api import StarkTransferAPI


@pytest.fixture
def mock_stark_transfer_create(mocker):
    return mocker.patch("starkbank.transfer.create")


@pytest.fixture
def mock_stark_transfer_get(mocker):
    return mocker.patch("starkbank.transfer.get")


@pytest.fixture
def mock_stark_transfer_query(mocker):
    return mocker.patch("starkbank.transfer.query")


@pytest.fixture
def api(mocker):
    # Mock settings and check_user
    mocker.patch("src.shared.stark.client.settings")
    # Also mock _initialize_sdk to avoid real init
    mocker.patch("src.shared.stark.client.StarkBankClient._initialize_sdk")
    return StarkTransferAPI()


def test_create_transfer_success(api, mock_stark_transfer_create):
    mock_transfer = MagicMock(
        id="trans-123",
        amount=5000,
        tax_id="12345678901",
        name="John Doe",
        bank_code="123",
        branch_code="0001",
        account_number="12345-6",
        external_id="ext-123",
        status="created",
        tags=[],
        fee=0,
        created=date.today(),
    )
    mock_stark_transfer_create.return_value = [mock_transfer]

    response = api.create_transfer(
        amount=5000,
        name="John Doe",
        tax_id="12345678901",
        bank_code="123",
        branch_code="0001",
        account_number="12345-6",
        external_id="ext-123",
    )

    assert response.id == "trans-123"
    assert response.external_id == "ext-123"
    mock_stark_transfer_create.assert_called_once()


def test_get_transfer_success(api, mock_stark_transfer_get):
    mock_transfer = MagicMock(
        id="trans-123",
        amount=5000,
        status="processing",
        tax_id="123",
        name="John",
        bank_code="001",
        branch_code="0001",
        account_number="123",
        external_id=None,
        tags=[],
        fee=0,
    )
    mock_stark_transfer_get.return_value = mock_transfer

    response = api.get_transfer("trans-123")
    assert response.id == "trans-123"
    assert response.status == "processing"


def test_list_transfers_success(api, mock_stark_transfer_query):
    mock_transfer = MagicMock(
        id="trans-123",
        amount=5000,
        status="processing",
        tax_id="123",
        name="John",
        bank_code="001",
        branch_code="0001",
        account_number="123",
        external_id=None,
        tags=[],
        fee=0,
    )
    # query returns generator or list, mock usually returns list which is iterable
    mock_stark_transfer_query.return_value = [mock_transfer]

    transfers = api.list_transfers()
    assert len(transfers) == 1
    assert transfers[0].id == "trans-123"
