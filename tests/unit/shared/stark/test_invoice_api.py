from datetime import date
from unittest.mock import MagicMock

import pytest

from src.shared.stark.invoice_api import StarkInvoiceAPI
from src.shared.utils.errors import ValidationError


@pytest.fixture
def mock_stark_invoice_create(mocker):
    return mocker.patch("starkbank.invoice.create")

@pytest.fixture
def mock_stark_invoice_get(mocker):
    return mocker.patch("starkbank.invoice.get")

@pytest.fixture
def mock_stark_invoice_query(mocker):
    return mocker.patch("starkbank.invoice.query")

@pytest.fixture
def api(mocker):
    # Mock settings and check_user
    mocker.patch("src.shared.stark.client.settings")
    # Also mock _initialize_sdk to avoid real init
    mocker.patch("src.shared.stark.client.StarkBankClient._initialize_sdk")
    return StarkInvoiceAPI()

def test_create_invoice_success(api, mock_stark_invoice_create):
    mock_invoice = MagicMock(
        id="inv-123",
        amount=1000,
        tax_id="12345678901",
        name="John Doe",
        due=date.today(),
        status="created",
        fine=0,
        interest=0,
        tags=[],
        descriptions=[]
    )
    mock_stark_invoice_create.return_value = [mock_invoice]

    response = api.create_invoice(
        amount=1000,
        tax_id="12345678901",
        name="John Doe",
        due_date=date.today()
    )

    assert response.id == "inv-123"
    assert response.amount == 1000
    mock_stark_invoice_create.assert_called_once()

def test_create_invoice_validation_error(api, mocker):
    mock_sleep = mocker.patch("src.shared.stark.retry.time.sleep")

    with pytest.raises(ValidationError):
        # Passing wrong type to fail internally
        # before stark call if I had validation there?
        # Or mock stark raising InputErrors.
        # But wait, my code checks 'isinstance(amount, int)'.
        api.create_invoice(
            amount="1000", tax_id="123",
            name="John", due_date=date.today(),
        )

    assert mock_sleep.call_count == 0  # Should NOT retry


def test_get_invoice_success(api, mock_stark_invoice_get):
    mock_invoice = MagicMock(
        id="inv-123", amount=1000, due=date.today(),
        status="paid", fine=0, interest=0,
        tags=[], descriptions=[],
    )
    mock_stark_invoice_get.return_value = mock_invoice

    response = api.get_invoice("inv-123")
    assert response.id == "inv-123"
    assert response.status == "paid"

def test_list_invoices_success(api, mock_stark_invoice_query):
    mock_invoice = MagicMock(
        id="inv-123", amount=1000, due=date.today(),
        status="created", fine=0, interest=0,
        tags=[], descriptions=[],
    )
    mock_stark_invoice_query.return_value = [mock_invoice]

    invoices = api.list_invoices()
    assert len(invoices) == 1
    assert invoices[0].id == "inv-123"
