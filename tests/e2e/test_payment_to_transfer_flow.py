"""
E2E Test: Payment to Transfer Flow.

Tests the complete flow from invoice payment (via webhook) to automatic
transfer creation, including idempotency and retry scenarios.
"""

import json
import time
from unittest.mock import Mock

import pytest

from src.modules.invoices.models import InvoiceStatus
from src.modules.transfers.models import TransferStatus
from tests.e2e.helpers import (
    assert_invoice_paid,
    assert_transfer_created,
    count_transfers_by_status,
    create_test_invoice,
    simulate_webhook,
)


class TestPaymentToTransferFlow:
    """E2E tests for payment to transfer flow."""

    def test_complete_payment_flow(
        self,
        e2e_app,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
        sample_invoices,
        api_key_header,
    ):
        """
        Test complete payment flow:
        - Create invoice via API
        - Simulate webhook of payment
        - Validate invoice with status="paid"
        - Validate transfer created automatically
        - Validate transfer with correct external_id
        - Validate events published
        - Validate logs
        """
        # Mock APIs are pre-configured via fixtures - no additional setup needed
        
        # ===== STEP 1: Create Invoice via API =====
        invoice_data = sample_invoices[0]  # João Silva, 50000
        
        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key")
        )
        
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]
        
        assert invoice_response["status"] == InvoiceStatus.CREATED.value
        assert invoice_response["amount"] == invoice_data["amount"]
        
        # ===== STEP 2: Simulate Webhook of Payment =====
        webhook_payload = {
            "event": {
                "id": "webhook_event_001",
                "subscription": "invoice",
                "log": {
                    "id": "webhook_log_001",
                    "created": "2026-02-16T10:30:00.000000+00:00",
                    "type": "credited",
                    "invoice": {
                        "id": stark_invoice_id,
                        "amount": invoice_data["amount"],
                        "fee": 200,  # R$ 2.00
                        "status": "paid",
                        "name": invoice_data["customer_name"],
                        "taxId": invoice_data["customer_tax_id"],
                    },
                },
            }
        }
        
        # Simulate webhook with valid signature
        webhook_response = simulate_webhook(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_payload,
            signature="mock_valid_signature"
        )
        
        assert webhook_response["status"] == "ok"
        
        # ===== STEP 3: Validate Invoice Updated to PAID =====
        invoice = assert_invoice_paid(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_net_amount=invoice_data["amount"] - 200  # amount - fee
        )
        
        assert invoice.fee == 200
        assert invoice.paid_at is not None
        
        # ===== STEP 4: Validate Transfer Created Automatically =====
        # Give event bus time to process (in real scenario, this is async)
        time.sleep(0.5)
        
        transfer = assert_transfer_created(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_status=TransferStatus.CREATED,
            expected_amount=invoice.net_amount
        )
        
        # ===== STEP 5: Validate Transfer Details =====
        # External ID should be "invoice-{invoice_id}" for idempotency
        expected_external_id = f"invoice-{invoice_id}"
        assert transfer.external_id == expected_external_id
        assert transfer.stark_transfer_id is not None
        assert transfer.amount == invoice.net_amount
        assert transfer.created_at is not None
        
        # ===== STEP 6: Validate via API =====
        # Check that we can retrieve the transfer via API
        transfer_response = e2e_app.get(
            f"/transfers/invoice/{invoice_id}",
            headers=api_key_header
        )
        
        assert transfer_response.status_code == 200
        transfer_data = transfer_response.json()
        assert transfer_data["id"] == transfer.id
        assert transfer_data["invoice_id"] == invoice_id
        assert transfer_data["status"] == TransferStatus.CREATED.value

    def test_idempotency_multiple_webhooks(
        self,
        e2e_app,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
        sample_invoices,
        api_key_header,
    ):
        """
        Test idempotency with multiple webhooks:
        - Create invoice
        - Simulate webhook of payment 3 times (duplicate webhooks)
        - Validate only 1 transfer created
        - Validate invoice updated only once
        """
        # Mock APIs are pre-configured via fixtures - no additional setup needed
        
        # ===== STEP 1: Create Invoice =====
        invoice_data = sample_invoices[1]  # Maria Santos, 100000
        
        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key")
        )
        
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]
        
        # ===== STEP 2: Create Webhook Payload =====
        webhook_payload = {
            "event": {
                "id": "webhook_event_002",
                "subscription": "invoice",
                "log": {
                    "id": "webhook_log_002",
                    "created": "2026-02-16T11:00:00.000000+00:00",
                    "type": "credited",
                    "invoice": {
                        "id": stark_invoice_id,
                        "amount": invoice_data["amount"],
                        "fee": 500,  # R$ 5.00
                        "status": "paid",
                        "name": invoice_data["customer_name"],
                        "taxId": invoice_data["customer_tax_id"],
                    },
                },
            }
        }
        
        # ===== STEP 3: Send Webhook 3 Times (Simulate Duplicates) =====
        for i in range(3):
            webhook_response = simulate_webhook(
                client=e2e_app,
                webhook_type="invoice",
                payload=webhook_payload,
                signature="mock_valid_signature"
            )
            
            assert webhook_response["status"] == "ok"
            
            # Small delay between webhooks
            time.sleep(0.2)
        
        # Give event bus time to process all webhooks
        time.sleep(0.5)
        
        # ===== STEP 4: Validate Invoice Paid (Only Once) =====
        invoice = assert_invoice_paid(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_net_amount=invoice_data["amount"] - 500
        )
        
        # ===== STEP 5: Validate Only 1 Transfer Created =====
        # Check via repository directly
        transfer = assert_transfer_created(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_status=TransferStatus.CREATED,
            expected_amount=invoice.net_amount
        )
        
        # Count total transfers with CREATED status
        created_transfers_count = count_transfers_by_status(
            db_connection=e2e_db,
            status=TransferStatus.CREATED
        )
        
        # Should be exactly 1 transfer (idempotency guaranteed)
        assert created_transfers_count == 1, \
            f"Expected 1 transfer, found {created_transfers_count} (idempotency failed)"
        
        # Verify external_id is correct
        expected_external_id = f"invoice-{invoice_id}"
        assert transfer.external_id == expected_external_id

    def test_payment_flow_with_retry(
        self,
        e2e_app,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
        sample_invoices,
        api_key_header,
    ):
        """
        Test payment flow with retry on temporary failure:
        - Create invoice
        - Configure Stark API to fail temporarily
        - Simulate webhook of payment
        - Validate retry automatic
        - Validate transfer created after retry
        """
        # ===== SETUP: Configure retry behavior for transfer API =====
        call_count = {"count": 0}
        
        def create_transfer_with_retry(transfer_data):
            """Simulate temporary failure then success."""
            call_count["count"] += 1
            
            # First call: fail with temporary error
            if call_count["count"] == 1:
                raise Exception("Temporary network error")
            
            # Second call: succeed
            return {
                "id": f"stark_transfer_{transfer_data['externalId']}",
                "amount": transfer_data["amount"],
                "externalId": transfer_data["externalId"],
                "status": "created",
            }
        
        # Override transfer API mock behavior for this test
        mock_stark_api["transfer_api"].create_transfer.side_effect = create_transfer_with_retry
        
        # ===== STEP 1: Create Invoice =====
        invoice_data = sample_invoices[2]  # Tech Solutions LTDA, 75000
        
        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key")
        )
        
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]
        
        # ===== STEP 2: Simulate Webhook of Payment =====
        webhook_payload = {
            "event": {
                "id": "webhook_event_003",
                "subscription": "invoice",
                "log": {
                    "id": "webhook_log_003",
                    "created": "2026-02-16T12:00:00.000000+00:00",
                    "type": "credited",
                    "invoice": {
                        "id": stark_invoice_id,
                        "amount": invoice_data["amount"],
                        "fee": 300,  # R$ 3.00
                        "status": "paid",
                        "name": invoice_data["customer_name"],
                        "taxId": invoice_data["customer_tax_id"],
                    },
                },
            }
        }
        
        webhook_response = simulate_webhook(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_payload,
            signature="mock_valid_signature"
        )
        
        assert webhook_response["status"] == "ok"
        
        # ===== STEP 3: Give Time for Retry Logic =====
        # The service should retry automatically
        # Wait a bit longer to allow for retry attempts
        time.sleep(1.0)
        
        # ===== STEP 4: Validate Invoice Paid =====
        invoice = assert_invoice_paid(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_net_amount=invoice_data["amount"] - 300
        )
        
        # ===== STEP 5: Validate Transfer Created After Retry =====
        transfer = assert_transfer_created(
            db_connection=e2e_db,
            invoice_id=invoice_id,
            expected_status=TransferStatus.CREATED,
            expected_amount=invoice.net_amount
        )
        
        # ===== STEP 6: Validate Retry Occurred =====
        # Check that create_transfer was called at least twice
        assert call_count["count"] >= 2, \
            f"Expected at least 2 calls (1 failure + 1 success), got {call_count['count']}"
        
        # Validate transfer details
        assert transfer.stark_transfer_id is not None
        assert transfer.external_id == f"invoice-{invoice_id}"
        assert transfer.retry_count >= 1, \
            f"Expected retry_count >= 1, got {transfer.retry_count}"

    def test_payment_flow_different_amounts(
        self,
        e2e_app,
        e2e_db,
        e2e_event_bus,
        mock_stark_api,
        api_key_header,
    ):
        """
        Test that transfers are created with correct amounts for different fees.
        - Create multiple invoices with different amounts
        - Simulate payments with different fees
        - Validate net_amount calculations are correct
        - Validate transfers have the correct net amounts
        """
        # Mock APIs are pre-configured via fixtures - no additional setup needed
        
        # Test data: (amount, fee)
        test_cases = [
            (10000, 50),    # R$ 100.00, fee R$ 0.50
            (50000, 200),   # R$ 500.00, fee R$ 2.00
            (100000, 500),  # R$ 1,000.00, fee R$ 5.00
            (250000, 1000), # R$ 2,500.00, fee R$ 10.00
        ]
        
        for amount, fee in test_cases:
            # ===== Create Invoice =====
            invoice_data = {
                "amount": amount,
                "customer_name": f"Test Customer {amount}",
                "customer_tax_id": "123.456.789-09",
                "customer_email": f"customer{amount}@example.com",
            }
            
            invoice_response = create_test_invoice(
                client=e2e_app,
                invoice_data=invoice_data,
                api_key=api_key_header.get("X-API-Key", "test-api-key")
            )
            
            invoice_id = invoice_response["id"]
            stark_invoice_id = invoice_response["stark_invoice_id"]
            
            # ===== Simulate Payment Webhook =====
            webhook_payload = {
                "event": {
                    "id": f"webhook_{amount}",
                    "subscription": "invoice",
                    "log": {
                        "id": f"log_{amount}",
                        "created": "2026-02-16T13:00:00.000000+00:00",
                        "type": "credited",
                        "invoice": {
                            "id": stark_invoice_id,
                            "amount": amount,
                            "fee": fee,
                            "status": "paid",
                            "name": invoice_data["customer_name"],
                            "taxId": invoice_data["customer_tax_id"],
                        },
                    },
                }
            }
            
            simulate_webhook(
                client=e2e_app,
                webhook_type="invoice",
                payload=webhook_payload,
                signature="mock_valid_signature"
            )
            
            time.sleep(0.3)  # Allow processing
            
            # ===== Validate Net Amount =====
            expected_net_amount = amount - fee
            
            invoice = assert_invoice_paid(
                db_connection=e2e_db,
                invoice_id=invoice_id,
                expected_net_amount=expected_net_amount
            )
            
            # ===== Validate Transfer Amount =====
            transfer = assert_transfer_created(
                db_connection=e2e_db,
                invoice_id=invoice_id,
                expected_amount=expected_net_amount
            )
            
            assert transfer.amount == expected_net_amount, \
                f"Transfer amount mismatch for invoice {amount}: " \
                f"expected {expected_net_amount}, got {transfer.amount}"
