"""
E2E Test: Query Endpoints.

Tests all query endpoints with filters, pagination, and authentication:
- List invoices with filters
- Get invoice by ID
- List transfers with filters
- Get transfer by invoice ID
"""

import time
from typing import Any

from tests.e2e.helpers import (
    assert_invoice_paid,
    assert_transfer_created,
    create_test_invoice,
    simulate_webhook,
)


class TestQueryEndpoints:
    """E2E tests for query endpoints."""

    def _create_and_pay_invoice(
        self,
        e2e_app,
        e2e_db,
        mock_stark_api,
        invoice_data: dict[str, Any],
        api_key_header: dict[str, str],
        fee: int = 100,
    ) -> dict[str, Any]:
        """
        Helper to create an invoice and simulate payment.

        Args:
            e2e_app: FastAPI test client
            e2e_db: Test database connection
            mock_stark_api: Mock Stark Bank API
            invoice_data: Invoice data to create
            api_key_header: API key header for authentication
            fee: Fee to use in payment webhook (default: 100)

        Returns:
            Dictionary with invoice and transfer data
        """
        # Step 1: Create invoice via API
        invoice_response = create_test_invoice(
            e2e_app, invoice_data, api_key_header.get("X-API-Key", "test-api-key")
        )
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]

        # Step 2: Simulate payment webhook
        webhook_payload = {
            "event": {
                "id": f"evt_{invoice_id}",
                "subscription": "invoice",
                "log": {
                    "id": f"log_{invoice_id}",
                    "created": "2026-02-17T10:00:00.000000+00:00",
                    "type": "credited",
                    "invoice": {
                        "id": stark_invoice_id,
                        "amount": invoice_data["amount"],
                        "status": "paid",
                        "fee": fee,
                    },
                },
            }
        }

        simulate_webhook(e2e_app, "invoice", webhook_payload)

        # Short wait for event bus processing
        time.sleep(0.1)

        # Step 3: Validate invoice paid
        expected_net_amount = (
            invoice_data["amount"] - fee
        ) / 100.0  # Convert to currency units
        assert_invoice_paid(e2e_db, invoice_id, expected_net_amount)

        # Step 4: Validate transfer created
        transfer = assert_transfer_created(e2e_db, invoice_id)

        return {
            "invoice_id": invoice_id,
            "invoice": invoice_response,
            "transfer_id": transfer.id,
            "transfer": transfer,
        }

    def test_list_invoices_with_filters(
        self,
        e2e_app,
        e2e_db,
        mock_stark_api,
        api_key_header,
    ):
        """
        Test list invoices endpoint with filters and pagination.

        Flow:
        1. Create 5 invoices with different amounts
        2. Pay 2 of them (status=PAID)
        3. Leave 3 with status=CREATED
        4. Test filters and pagination

        Validates:
        - List all invoices without filters
        - Filter by status (paid/created)
        - Pagination (limit/offset)
        - Authentication requirement
        - Response structure
        """
        # Step 1: Create 5 invoices with different amounts
        invoice_data_list = [
            {
                "amount": 10000,
                "customer_name": "Customer One",
                "customer_tax_id": "012.345.678-90",  # Valid CPF
                "customer_email": "customer1@example.com",
            },
            {
                "amount": 20000,
                "customer_name": "Customer Two",
                "customer_tax_id": "987.654.321-00",  # Valid CPF
                "customer_email": "customer2@example.com",
            },
            {
                "amount": 30000,
                "customer_name": "Customer Three",
                "customer_tax_id": "11.222.333/0001-81",  # Valid CNPJ
                "customer_email": "customer3@example.com",
            },
            {
                "amount": 40000,
                "customer_name": "Customer Four",
                "customer_tax_id": "123.456.789-09",  # Valid CPF
                "customer_email": "customer4@example.com",
            },
            {
                "amount": 50000,
                "customer_name": "Customer Five",
                "customer_tax_id": "111.444.777-35",  # Valid CPF
                "customer_email": "customer5@example.com",
            },
        ]

        # Create all invoices
        created_invoices = []
        for invoice_data in invoice_data_list:
            invoice_response = create_test_invoice(
                client=e2e_app,
                invoice_data=invoice_data,
                api_key=api_key_header.get("X-API-Key", "test-api-key"),
            )
            created_invoices.append(invoice_response)

        # Step 2: Pay first 2 invoices (others remain CREATED)
        for i in range(2):
            invoice = created_invoices[i]
            webhook_payload = {
                "event": {
                    "id": f"evt_pay_{invoice['id']}",
                    "subscription": "invoice",
                    "log": {
                        "id": f"log_pay_{invoice['id']}",
                        "created": "2026-02-17T10:00:00.000000+00:00",
                        "type": "credited",
                        "invoice": {
                            "id": invoice["stark_invoice_id"],
                            "amount": invoice["amount"],
                            "status": "paid",
                            "fee": 100 + (i * 50),  # Different fees
                        },
                    },
                }
            }
            simulate_webhook(e2e_app, "invoice", webhook_payload)

        # Wait for webhook processing
        time.sleep(0.1)

        # Step 3: Test queries and assertions

        # Assertion 1: GET /invoices without filter returns all 5
        response = e2e_app.get("/invoices", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        invoices_list = data.get(
            "invoices", data
        )  # Handle both list and dict responses
        if isinstance(invoices_list, dict):
            invoices_list = invoices_list.get("invoices", [])
        assert len(invoices_list) == 5

        # Assertion 2: GET /invoices?status=paid returns only 2
        response = e2e_app.get("/invoices?status=paid", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        paid_invoices = data.get("invoices", data)
        if isinstance(paid_invoices, dict):
            paid_invoices = paid_invoices.get("invoices", [])
        assert len(paid_invoices) == 2
        for invoice in paid_invoices:
            assert invoice["status"] == "paid"

        # Assertion 3: GET /invoices?status=created returns only 3
        response = e2e_app.get("/invoices?status=created", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        created_invoices_response = data.get("invoices", data)
        if isinstance(created_invoices_response, dict):
            created_invoices_response = created_invoices_response.get("invoices", [])
        assert len(created_invoices_response) == 3
        for invoice in created_invoices_response:
            assert invoice["status"] == "created"

        # Assertion 4: GET /invoices?limit=2&offset=0 returns 2 items
        response = e2e_app.get("/invoices?limit=2&offset=0", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        invoices_list = data.get("invoices", data)
        if isinstance(invoices_list, dict):
            invoices_list = invoices_list.get("invoices", [])
        assert len(invoices_list) == 2

        # Assertion 5: GET /invoices?limit=2&offset=2 returns next 2 items
        response = e2e_app.get("/invoices?limit=2&offset=2", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        invoices_list = data.get("invoices", data)
        if isinstance(invoices_list, dict):
            invoices_list = invoices_list.get("invoices", [])
        assert len(invoices_list) == 2

        # Assertion 6: GET /invoices?limit=2&offset=4 returns 1 item (last)
        response = e2e_app.get("/invoices?limit=2&offset=4", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        invoices_list = data.get("invoices", data)
        if isinstance(invoices_list, dict):
            invoices_list = invoices_list.get("invoices", [])
        assert len(invoices_list) == 1

        # Assertion 7: GET /invoices without X-API-Key returns 401 or 403
        response = e2e_app.get("/invoices")
        assert response.status_code in [401, 403]

        # Assertion 8: Each invoice has required fields
        response = e2e_app.get("/invoices", headers=api_key_header)
        data = response.json()
        all_invoices = data.get("invoices", data)
        if isinstance(all_invoices, dict):
            all_invoices = all_invoices.get("invoices", [])
        for invoice in all_invoices:
            assert "id" in invoice
            assert "amount" in invoice
            assert "status" in invoice
            assert "customer_name" in invoice
            assert "customer_tax_id" in invoice
            # Validate types
            assert isinstance(invoice["id"], str)
            assert isinstance(invoice["amount"], (int, float))  # API may return float
            assert invoice["status"] in ["created", "paid", "failed"]
            assert isinstance(invoice["customer_name"], str)
            assert isinstance(invoice["customer_tax_id"], str)

    def test_get_invoice_by_id(
        self,
        e2e_app,
        e2e_db,
        mock_stark_api,
        api_key_header,
    ):
        """
        Test get invoice by ID endpoint.

        Flow:
        1. Create invoice via API
        2. Query by ID

        Validates:
        - GET /invoices/{id} with valid ID returns 200 and complete invoice
        - All mandatory fields are present
        - GET /invoices/non-existent-uuid returns 404
        - GET /invoices/{id} without X-API-Key returns 401 or 403
        """
        # Step 1: Create invoice via API
        invoice_data = {
            "amount": 15000,
            "customer_name": "Test Customer",
            "customer_tax_id": "012.345.678-90",  # Valid CPF
            "customer_email": "test@example.com",
        }

        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key"),
        )
        invoice_id = invoice_response["id"]

        # Step 2: Query by ID

        # Assertion 1: GET /invoices/{id} with valid ID returns 200
        response = e2e_app.get(f"/invoices/{invoice_id}", headers=api_key_header)
        assert response.status_code == 200

        # Assertion 2: Check all mandatory fields are present
        invoice = response.json()
        required_fields = [
            "id",
            "amount",
            "status",
            "customer_name",
            "customer_tax_id",
            "customer_email",
            "stark_invoice_id",
            "created_at",
        ]
        for field in required_fields:
            assert field in invoice, f"Field '{field}' is missing from invoice response"

        # Validate field values
        assert invoice["id"] == invoice_id
        # Amount is converted from centavos to currency units (divide by 100)
        assert invoice["amount"] == invoice_data["amount"] / 100.0
        assert invoice["customer_name"] == invoice_data["customer_name"]
        assert invoice["customer_tax_id"] == invoice_data["customer_tax_id"]
        assert invoice["customer_email"] == invoice_data["customer_email"]
        assert invoice["status"] in ["created", "paid", "failed"]
        assert isinstance(invoice["stark_invoice_id"], str)
        assert isinstance(invoice["created_at"], str)

        # Assertion 3: GET /invoices/non-existent-uuid returns 404
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = e2e_app.get(f"/invoices/{non_existent_id}", headers=api_key_header)
        assert response.status_code == 404

        # Assertion 4: GET /invoices/{id} without X-API-Key returns 401 or 403
        response = e2e_app.get(f"/invoices/{invoice_id}")
        assert response.status_code in [401, 403]

    def test_list_transfers_with_filters(
        self,
        e2e_app,
        e2e_db,
        mock_stark_api,
        api_key_header,
    ):
        """
        Test list transfers endpoint with filters and pagination.

        Flow:
        1. Create 3 invoices and simulate payment for all 3
        2. For transfer 1: simulate webhook success
        3. For transfer 2: simulate webhook failed
        4. Transfer 3: remains with status CREATED

        Validates:
        - GET /transfers returns 3 transfers
        - Filter by status (success/failed/created)
        - Pagination with limit
        - Each transfer has required fields
        """
        # Step 1: Create 3 invoices and simulate payment for all
        invoice_data_list = [
            {
                "amount": 10000,
                "customer_name": "Transfer Test One",
                "customer_tax_id": "012.345.678-90",
                "customer_email": "transfer1@example.com",
            },
            {
                "amount": 20000,
                "customer_name": "Transfer Test Two",
                "customer_tax_id": "987.654.321-00",
                "customer_email": "transfer2@example.com",
            },
            {
                "amount": 30000,
                "customer_name": "Transfer Test Three",
                "customer_tax_id": "11.222.333/0001-81",
                "customer_email": "transfer3@example.com",
            },
        ]

        # Create and pay all 3 invoices
        transfers_data = []
        for i, invoice_data in enumerate(invoice_data_list):
            result = self._create_and_pay_invoice(
                e2e_app=e2e_app,
                e2e_db=e2e_db,
                mock_stark_api=mock_stark_api,
                invoice_data=invoice_data,
                api_key_header=api_key_header,
                fee=100 + (i * 50),
            )
            transfers_data.append(result)

        # Wait for event bus processing
        time.sleep(0.1)

        # Step 2: For transfer 1 - simulate webhook success
        transfer_1 = transfers_data[0]["transfer"]
        webhook_success = {
            "event": {
                "id": "evt_success_001",
                "subscription": "transfer",
                "log": {
                    "id": "log_success_001",
                    "created": "2026-02-17T11:00:00.000000+00:00",
                    "type": "success",
                    "transfer": {
                        "id": transfer_1.stark_transfer_id,
                        "amount": transfer_1.amount,
                        "status": "success",
                        "externalId": transfer_1.external_id,
                    },
                },
            }
        }
        simulate_webhook(e2e_app, "transfer", webhook_success)

        # Step 3: For transfer 2 - simulate webhook failed
        transfer_2 = transfers_data[1]["transfer"]
        webhook_failed = {
            "event": {
                "id": "evt_failed_001",
                "subscription": "transfer",
                "log": {
                    "id": "log_failed_001",
                    "created": "2026-02-17T11:05:00.000000+00:00",
                    "type": "failed",
                    "transfer": {
                        "id": transfer_2.stark_transfer_id,
                        "amount": transfer_2.amount,
                        "status": "failed",
                        "externalId": transfer_2.external_id,
                        "error": "Insufficient funds",
                    },
                },
            }
        }
        simulate_webhook(e2e_app, "transfer", webhook_failed)

        # Step 4: Transfer 3 remains with status CREATED (no webhook sent)

        # Wait for webhook processing
        time.sleep(0.1)

        # Step 5: Test queries and assertions

        # Assertion 1: GET /transfers returns 3 transfers
        response = e2e_app.get("/transfers", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        transfers_list = data.get("transfers", data)
        if isinstance(transfers_list, dict):
            transfers_list = transfers_list.get("transfers", [])
        assert len(transfers_list) == 3

        # Assertion 2: GET /transfers?status=success returns 1
        response = e2e_app.get("/transfers?status=success", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        success_transfers = data.get("transfers", data)
        if isinstance(success_transfers, dict):
            success_transfers = success_transfers.get("transfers", [])
        assert len(success_transfers) == 1
        assert success_transfers[0]["status"] == "success"

        # Assertion 3: GET /transfers?status=failed returns 1
        response = e2e_app.get("/transfers?status=failed", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        failed_transfers = data.get("transfers", data)
        if isinstance(failed_transfers, dict):
            failed_transfers = failed_transfers.get("transfers", [])
        assert len(failed_transfers) == 1
        assert failed_transfers[0]["status"] == "failed"

        # Assertion 4: GET /transfers?status=created returns 1
        response = e2e_app.get("/transfers?status=created", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        created_transfers = data.get("transfers", data)
        if isinstance(created_transfers, dict):
            created_transfers = created_transfers.get("transfers", [])
        assert len(created_transfers) == 1
        assert created_transfers[0]["status"] == "created"

        # Assertion 5: Pagination - GET /transfers?limit=1 returns 1 item
        response = e2e_app.get("/transfers?limit=1", headers=api_key_header)
        assert response.status_code == 200
        data = response.json()
        transfers_list = data.get("transfers", data)
        if isinstance(transfers_list, dict):
            transfers_list = transfers_list.get("transfers", [])
        assert len(transfers_list) == 1

        # Assertion 6: Each transfer has required fields
        response = e2e_app.get("/transfers", headers=api_key_header)
        data = response.json()
        all_transfers = data.get("transfers", data)
        if isinstance(all_transfers, dict):
            all_transfers = all_transfers.get("transfers", [])

        required_fields = ["id", "invoice_id", "amount", "status", "external_id"]
        for transfer in all_transfers:
            for field in required_fields:
                assert field in transfer, (
                    f"Field '{field}' is missing from transfer response"
                )

            # Validate types and values
            assert isinstance(transfer["id"], str)
            assert isinstance(transfer["invoice_id"], str)
            assert isinstance(transfer["amount"], (int, float))
            assert transfer["status"] in [
                "created",
                "processing",
                "success",
                "failed",
                "canceled",
            ]
            assert isinstance(transfer["external_id"], str)
            assert transfer["external_id"].startswith("invoice-")

    def test_get_transfer_by_invoice_id(
        self,
        e2e_app,
        e2e_db,
        mock_stark_api,
        api_key_header,
    ):
        """
        Test get transfer by invoice ID endpoint.

        Flow:
        1. Create invoice and simulate payment
        2. Transfer is auto-created via event handler
        3. Query transfer by invoice_id

        Validates:
        - GET /transfers/invoice/{invoice_id} returns 200 and transfer
        - Transfer amount equals invoice net_amount
        - Transfer external_id equals "invoice-{invoice_id}"
        - Transfer invoice_id matches the invoice
        - GET /transfers/invoice/non-existent-uuid returns 404
        - GET /transfers/invoice/{id} without X-API-Key returns 401 or 403
        """
        # Step 1: Create invoice and simulate payment using helper
        invoice_data = {
            "amount": 25000,
            "customer_name": "Transfer Query Test",
            "customer_tax_id": "012.345.678-90",
            "customer_email": "transferquery@example.com",
        }

        fee = 250
        result = self._create_and_pay_invoice(
            e2e_app=e2e_app,
            e2e_db=e2e_db,
            mock_stark_api=mock_stark_api,
            invoice_data=invoice_data,
            api_key_header=api_key_header,
            fee=fee,
        )

        invoice_id = result["invoice_id"]
        transfer_id = result["transfer_id"]
        transfer = result["transfer"]

        # Calculate expected net_amount (in currency units)
        expected_net_amount = (invoice_data["amount"] - fee) / 100.0

        # Step 2: Query transfer by invoice_id

        # Assertion 1: GET /transfers/invoice/{invoice_id} returns 200 and transfer
        response = e2e_app.get(
            f"/transfers/invoice/{invoice_id}", headers=api_key_header
        )
        assert response.status_code == 200

        transfer_response = response.json()

        # Assertion 2: Transfer amount equals invoice net_amount
        # Transfer amount is stored in centavos, API returns in currency units
        assert transfer_response["amount"] == expected_net_amount, (
            f"Transfer amount {transfer_response['amount']} "
            f"does not match expected net_amount {expected_net_amount}"
        )

        # Assertion 3: Transfer external_id equals "invoice-{invoice_id}"
        expected_external_id = f"invoice-{invoice_id}"
        assert transfer_response["external_id"] == expected_external_id, (
            f"Transfer external_id {transfer_response['external_id']} "
            f"does not match expected {expected_external_id}"
        )

        # Assertion 4: Transfer invoice_id matches the invoice
        assert transfer_response["invoice_id"] == invoice_id, (
            f"Transfer invoice_id {transfer_response['invoice_id']} "
            f"does not match expected {invoice_id}"
        )

        # Validate other required fields are present
        assert "id" in transfer_response
        assert "status" in transfer_response
        assert "created_at" in transfer_response
        assert transfer_response["id"] == str(transfer_id)

        # Assertion 5: GET /transfers/invoice/non-existent-uuid returns 404
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = e2e_app.get(
            f"/transfers/invoice/{non_existent_id}", headers=api_key_header
        )
        assert response.status_code == 404

        # Assertion 6: GET /transfers/invoice/{id} without X-API-Key returns 401 or 403
        response = e2e_app.get(f"/transfers/invoice/{invoice_id}")
        assert response.status_code in [401, 403]
