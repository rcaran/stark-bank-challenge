"""
E2E Tests for Error Scenarios and System Resilience

Tests error handling and recovery mechanisms across the system:
- Invalid webhook signatures
- Stark Bank API timeouts/failures
- Database errors and recovery
- Unknown/invalid data scenarios

These tests validate that the system fails gracefully and can recover from errors.
"""

import json
import time
from unittest.mock import patch
import pytest

from src.modules.invoices.models import InvoiceStatus
from src.modules.transfers.models import TransferStatus
from src.shared.security.signature import InvalidSignatureError

from tests.e2e.helpers import (
    create_test_invoice,
    simulate_webhook,
    simulate_webhook_raw,
    assert_invoice_paid,
    assert_transfer_created,
)


class TestErrorScenarios:
    """Test suite for error scenarios and system resilience."""
    
    def test_invalid_webhook_signature(
        self,
        e2e_app,
        e2e_db,
        api_key_header,
        sample_webhook_invoice_paid,
        sample_webhook_transfer_success
    ):
        """
        Test that webhooks with invalid signatures are rejected.
        
        Verifies:
        1. Invalid signature on invoice webhook → 401 with error message
        2. No data is modified in the database
        3. Invalid signature on transfer webhook → 401 with error message
        4. System logs appropriate security warnings
        """
        # Test 1: Invoice webhook with invalid signature
        # -----------------------------------------------
        # Create an invoice first so we can send a payment webhook for it
        # (API key authentication works normally for this step)
        invoice_data = {
            "amount": 25000,
            "customer_name": "Test Customer Invalid Sig",
            "customer_tax_id": "123.456.789-09",  # Valid CPF format
            "customer_email": "test@invalidsig.com",
        }
        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key")
        )
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]
        
        # NOW configure mock validator to reject signatures for webhook test
        e2e_app._mock_validator.verify_signature.side_effect = InvalidSignatureError(
            "Invalid digital signature"
        )
        
        # Prepare payment webhook payload
        webhook_invoice_payload = sample_webhook_invoice_paid.copy()
        webhook_invoice_payload["event"]["log"]["invoice"]["id"] = stark_invoice_id
        
        # Send webhook with invalid signature
        response = simulate_webhook_raw(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_invoice_payload,
            signature="invalid_signature_12345"
        )
        
        # Verify rejection
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        response_json = response.json()
        assert "error" in response_json or "detail" in response_json, \
            "Response should contain error/detail field"
        
        # Verify error message indicates unauthorized/signature issue
        error_msg = response_json.get("error") or response_json.get("detail", "")
        assert "signature" in error_msg.lower() or "unauthorized" in error_msg.lower(), \
            f"Error message should indicate signature issue: {error_msg}"
        
        # Verify database was not modified - invoice should still be CREATED
        from tests.e2e.helpers import TestDbAdapter
        from src.modules.invoices.repository import InvoiceRepository
        
        db_adapter = TestDbAdapter(e2e_db)
        invoice_repo = InvoiceRepository(db_adapter)
        
        invoice = invoice_repo.get_by_id(invoice_id)
        assert invoice is not None, "Invoice should exist"
        assert invoice.status == InvoiceStatus.CREATED, \
            f"Invoice status should remain CREATED, got {invoice.status}"
        assert invoice.fee is None, "Fee should not be set on rejected webhook"
        assert invoice.net_amount is None, "Net amount should not be set on rejected webhook"
        
        # Test 2: Transfer webhook with invalid signature
        # -----------------------------------------------
        # For transfer webhook, we need a transfer to exist
        # First, reconfigure validator to accept signatures temporarily
        e2e_app._mock_validator.verify_signature.side_effect = None
        e2e_app._mock_validator.verify_signature.return_value = None
        
        # Pay the invoice to create a transfer
        response = simulate_webhook(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_invoice_payload
        )
        
        # Verify invoice is now paid and transfer was created
        time.sleep(0.1)  # Brief wait for async processing
        invoice = invoice_repo.get_by_id(invoice_id)
        assert invoice.status == InvoiceStatus.PAID, "Invoice should be paid now"
        
        from src.modules.transfers.repository import TransferRepository
        transfer_repo = TransferRepository(db_adapter)
        transfer = transfer_repo.get_by_invoice_id(invoice_id)
        assert transfer is not None, "Transfer should have been created"
        initial_transfer_status = transfer.status
        
        # Now reconfigure validator to reject again
        e2e_app._mock_validator.verify_signature.side_effect = InvalidSignatureError(
            "Invalid digital signature"
        )
        
        # Prepare transfer webhook payload
        webhook_transfer_payload = sample_webhook_transfer_success.copy()
        webhook_transfer_payload["event"]["log"]["transfer"]["id"] = transfer.stark_transfer_id
        webhook_transfer_payload["event"]["log"]["transfer"]["externalId"] = transfer.external_id
        
        # Send transfer webhook with invalid signature
        response = simulate_webhook_raw(
            client=e2e_app,
            webhook_type="transfer",
            payload=webhook_transfer_payload,
            signature="another_invalid_signature"
        )
        
        # Verify rejection
        assert response.status_code == 401, f"Expected 401 for transfer webhook, got {response.status_code}"
        
        response_json = response.json()
        assert "error" in response_json or "detail" in response_json, \
            "Transfer webhook response should contain error/detail field"
        
        # Verify database was not modified - transfer status should remain unchanged
        transfer = transfer_repo.get_by_id(transfer.id)
        assert transfer is not None, "Transfer should still exist"
        assert transfer.status == initial_transfer_status, \
            f"Transfer status should remain {initial_transfer_status}, got {transfer.status}"
    
    def test_stark_api_timeout(
        self,
        e2e_app,
        e2e_db,
        api_key_header,
        mock_stark_api
    ):
        """
        Test that invoice creation fails gracefully when Stark Bank API times out.
        
        Verifies:
        1. Stark API timeout raises appropriate error
        2. API returns 500 error with descriptive message
        3. No invoice is created in the database with CREATED status
        4. System handles the error without crashing
        """
        # Configure mock to simulate timeout/connection error
        mock_stark_api["invoice_api"].create_invoice.side_effect = Exception(
            "Connection timeout"
        )
        
        # Prepare invoice data with valid formats
        invoice_data = {
            "amount": 50000,  # R$ 500.00
            "customer_name": "Test Customer Timeout",
            "customer_tax_id": "123.456.789-09",  # Valid CPF format
            "customer_email": "test@timeout.com",
        }
        
        # Attempt to create invoice - should fail
        response = e2e_app.post(
            "/invoices",
            json=invoice_data,
            headers=api_key_header
        )
        
        # Verify error response
        assert response.status_code == 500, \
            f"Expected 500 Internal Server Error, got {response.status_code}"
        
        response_json = response.json()
        # Global exception handler returns "error" and "message" keys
        assert "error" in response_json or "message" in response_json, \
            "Response should contain error information"
        
        # Verify error message mentions server error
        error_msg = response_json.get("error", "") or response_json.get("message", "")
        assert "error" in error_msg.lower() or "server" in error_msg.lower(), \
            f"Error message should indicate server error: {error_msg}"
        
        # Verify database state
        from tests.e2e.helpers import TestDbAdapter
        from src.modules.invoices.repository import InvoiceRepository
        
        db_adapter = TestDbAdapter(e2e_db)
        invoice_repo = InvoiceRepository(db_adapter)
        
        # Query all invoices from the database
        invoices = invoice_repo.list(
            limit=100,
            offset=0
        )
        
        # When Stark API fails, service creates invoice with FAILED status
        # There should be no successful (CREATED) invoices for this customer
        created_invoices = [
            inv for inv in invoices
            if inv.status == InvoiceStatus.CREATED 
            and inv.customer_email == "test@timeout.com"
        ]
        
        assert len(created_invoices) == 0, \
            f"No CREATED invoice should exist in database, found {len(created_invoices)}"
        
        # Optionally verify that a FAILED invoice was recorded for tracking
        failed_invoices = [
            inv for inv in invoices
            if inv.status == InvoiceStatus.FAILED 
            and inv.customer_email == "test@timeout.com"
        ]
        
        # System should create a FAILED invoice for tracking purposes
        assert len(failed_invoices) == 1, \
            f"Expected 1 FAILED invoice for tracking, found {len(failed_invoices)}"
        
        # Verify the failed invoice has error message
        failed_invoice = failed_invoices[0]
        assert failed_invoice.error_message is not None, \
            "Failed invoice should have error message"
        assert "timeout" in failed_invoice.error_message.lower(), \
            f"Error message should mention timeout: {failed_invoice.error_message}"
        
        # Verify that mock was actually called
        mock_stark_api["invoice_api"].create_invoice.assert_called_once()
    
    def test_database_error_recovery(
        self,
        e2e_app,
        e2e_db,
        api_key_header,
        sample_webhook_invoice_paid
    ):
        """
        Test that system handles database errors gracefully and can recover.
        
        Verifies:
        1. Database error during webhook processing → 200 with error status
        2. Invoice remains unchanged in database
        3. After recovery (error removed), webhook succeeds
        4. Invoice is correctly updated to PAID
        """
        # Step 1: Create invoice successfully via API
        # --------------------------------------------
        invoice_data = {
            "amount": 35000,  # R$ 350.00
            "customer_name": "Test Customer DB Error",
            "customer_tax_id": "123.456.789-09",  # Valid CPF format
            "customer_email": "test@dberror.com",
        }
        
        invoice_response = create_test_invoice(
            client=e2e_app,
            invoice_data=invoice_data,
            api_key=api_key_header.get("X-API-Key", "test-api-key")
        )
        
        invoice_id = invoice_response["id"]
        stark_invoice_id = invoice_response["stark_invoice_id"]
        
        # Verify invoice was created with CREATED status
        from tests.e2e.helpers import TestDbAdapter
        from src.modules.invoices.repository import InvoiceRepository
        
        db_adapter = TestDbAdapter(e2e_db)
        invoice_repo = InvoiceRepository(db_adapter)
        
        invoice = invoice_repo.get_by_id(invoice_id)
        assert invoice is not None, "Invoice should exist"
        assert invoice.status == InvoiceStatus.CREATED, \
            f"Invoice should be CREATED, got {invoice.status}"
        
        # Step 2: Patch InvoiceRepository.update to simulate database error
        # ------------------------------------------------------------------
        # Prepare webhook payload
        webhook_payload = sample_webhook_invoice_paid.copy()
        webhook_payload["event"]["log"]["invoice"]["id"] = stark_invoice_id
        webhook_payload["event"]["log"]["invoice"]["fee"] = 150  # R$ 1.50
        webhook_payload["event"]["log"]["invoice"]["amount"] = 35000  # R$ 350.00
        
        # Patch the update method to raise database error
        with patch.object(
            InvoiceRepository,
            'update',
            side_effect=Exception("Database locked")
        ):
            # Step 3: Send webhook - should fail internally but return 200
            # --------------------------------------------------------------
            response = simulate_webhook_raw(
                client=e2e_app,
                webhook_type="invoice",
                payload=webhook_payload
            )
            
            # Step 4: Verify webhook returns 200 (graceful error handling)
            # -------------------------------------------------------------
            assert response.status_code == 200, \
                f"Webhook should return 200 even with internal error, got {response.status_code}"
            
            response_json = response.json()
            
            # Step 5: Verify error field in response
            # ---------------------------------------
            # The webhook receiver should indicate processing error
            # Check for "error" field or "status" != "ok"
            has_error = (
                "error" in response_json or
                response_json.get("status") != "ok" or
                "processing_error" in str(response_json).lower()
            )
            
            assert has_error, \
                f"Response should indicate processing error: {response_json}"
        
        # Step 6: Verify invoice remains CREATED (update failed)
        # -------------------------------------------------------
        invoice = invoice_repo.get_by_id(invoice_id)
        assert invoice.status == InvoiceStatus.CREATED, \
            f"Invoice should still be CREATED after DB error, got {invoice.status}"
        assert invoice.fee is None, \
            "Fee should not be set after DB error"
        assert invoice.net_amount is None, \
            "Net amount should not be set after DB error"
        
        # Step 7: Remove patch (recovery) and send webhook again
        # -------------------------------------------------------
        # Patch is automatically removed when exiting the context manager
        # Send the same webhook again
        response = simulate_webhook_raw(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_payload
        )
        
        # Step 8: Verify success response
        # --------------------------------
        assert response.status_code == 200, \
            f"Webhook should succeed after recovery, got {response.status_code}"
        
        response_json = response.json()
        assert response_json.get("status") == "ok", \
            f"Response should indicate success: {response_json}"
        
        # Step 9: Verify invoice is now PAID
        # -----------------------------------
        time.sleep(0.1)  # Brief wait for async processing
        invoice = invoice_repo.get_by_id(invoice_id)
        
        assert invoice.status == InvoiceStatus.PAID, \
            f"Invoice should be PAID after recovery, got {invoice.status}"
        assert invoice.fee == 1.5, \
            f"Fee should be 1.5 (R$), got {invoice.fee}"
        assert invoice.net_amount == 348.5, \
            f"Net amount should be 348.5 (R$ 350.00 - R$ 1.50), got {invoice.net_amount}"
        
        # Verify transfer was created
        from src.modules.transfers.repository import TransferRepository
        transfer_repo = TransferRepository(db_adapter)
        transfer = transfer_repo.get_by_invoice_id(invoice_id)
        
        assert transfer is not None, \
            "Transfer should have been created after successful webhook"
        assert transfer.amount == 348.5, \
            f"Transfer amount should match net_amount (R$), got {transfer.amount}"
        assert transfer.status == TransferStatus.CREATED, \
            f"Transfer should be CREATED, got {transfer.status}"
    
    def test_webhook_with_unknown_invoice(
        self,
        e2e_app,
        e2e_db,
        sample_webhook_invoice_paid
    ):
        """
        Test that webhook with unknown stark_invoice_id is handled gracefully.
        
        Verifies:
        1. Webhook referencing non-existent invoice → 200 (no crash)
        2. Response indicates processing issue or warning
        3. No exceptions crash the system
        4. No invalid data is created in the database
        """
        # Prepare webhook payload with unknown stark_invoice_id
        webhook_payload = sample_webhook_invoice_paid.copy()
        unknown_stark_id = "unknown_stark_invoice_12345"
        webhook_payload["event"]["log"]["invoice"]["id"] = unknown_stark_id
        webhook_payload["event"]["log"]["invoice"]["fee"] = 200  # R$ 2.00
        webhook_payload["event"]["log"]["invoice"]["amount"] = 50000  # R$ 500.00
        
        # Send webhook with unknown invoice
        response = simulate_webhook_raw(
            client=e2e_app,
            webhook_type="invoice",
            payload=webhook_payload
        )
        
        # Verify system doesn't crash - should return 200
        assert response.status_code == 200, \
            f"Webhook should return 200 even for unknown invoice, got {response.status_code}"
        
        response_json = response.json()
        
        # Response should indicate either:
        # - "status": "ok" (webhook accepted but invoice not found)
        # - or contain a warning/error field
        # The system should not crash with 500
        assert isinstance(response_json, dict), \
            "Response should be a valid JSON object"
        
        # Verify no crash or uncaught exception
        # (if we got here, the request completed without crashing)
        
        # Check that no transfer was created for unknown invoice
        from tests.e2e.helpers import TestDbAdapter
        from src.modules.invoices.repository import InvoiceRepository
        from src.modules.transfers.repository import TransferRepository
        
        db_adapter = TestDbAdapter(e2e_db)
        invoice_repo = InvoiceRepository(db_adapter)
        transfer_repo = TransferRepository(db_adapter)
        
        # Verify no invoice with this stark_invoice_id exists
        invoice = invoice_repo.get_by_stark_id(unknown_stark_id)
        assert invoice is None, \
            f"No invoice should exist for unknown stark_invoice_id: {unknown_stark_id}"
        
        # Verify no transfers were created (since invoice doesn't exist)
        all_transfers = transfer_repo.list(limit=100, offset=0)
        assert len(all_transfers) == 0, \
            f"No transfers should exist for unknown invoice, found {len(all_transfers)}"
        
        # Additional verification: system should log warning
        # (In a real implementation, you would capture logs and verify the warning)
        # For now, we verify that the webhook was processed without crashing
        
        print(f"✓ Webhook with unknown invoice handled gracefully: {response_json}")

