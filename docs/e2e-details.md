# Implementation Details: E2E Tests
# Stark Bank Challenge

**Version:** 1.0  
**Date:** February 2026  
**Based on:** [e2e-tests.md](e2e-tests.md) — PHASE 8 Implementation Plan

---

## Table of Contents

- [Overview](#overview)
- [Test Infrastructure Architecture](#test-infrastructure-architecture)
  - [Per-Test Isolated Database](#per-test-isolated-database)
  - [Dedicated EventBus](#dedicated-eventbus)
  - [Stark Bank API Mocks](#stark-bank-api-mocks)
  - [Main Fixture: `e2e_app`](#main-fixture-e2e_app)
  - [Helpers and Utility Functions](#helpers-and-utility-functions)
- [Test Suites](#test-suites)
  - [8.2 — Invoice Creation Flow](#82--invoice-creation-flow)
  - [8.3 — Payment to Transfer Flow](#83--payment-to-transfer-flow)
  - [8.4 — Transfer Status Updates](#84--transfer-status-updates)
  - [8.5 — Query Endpoints](#85--query-endpoints)
  - [8.6 — Error Scenarios](#86--error-scenarios)
- [Results and Coverage](#results-and-coverage)

---

## Overview

The E2E (End-to-End) tests for the Stark Bank Challenge validate complete system flows, traversing multiple real layers — HTTP API → Service → Repository → Database → EventBus. Unlike unit tests (which isolate a single unit) and integration tests (which test individual modules), E2E tests exercise the system behavior as a whole, as an external client would.

**19 tests** are implemented across 5 files, covering the main use cases and error scenarios.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Full isolation** | Each test receives a temporary SQLite database + fresh EventBus via `scope="function"` fixtures |
| **No external calls** | Stark Bank APIs are replaced by configurable mocks |
| **Real flow** | All layers (HTTP, service, repository, DB) are exercised with real code |
| **Idempotency** | Tests verify that duplicate operations do not produce inconsistent data |
| **Graceful failure** | Internal errors must not return 500 for webhooks — the system absorbs and logs them |

---

## Test Infrastructure Architecture

The infrastructure files are `tests/e2e/conftest.py` and `tests/e2e/helpers.py`.

### Per-Test Isolated Database

**File:** [tests/e2e/conftest.py](../tests/e2e/conftest.py)

Each test receives a SQLite database in a temporary file that is created, migrated, and destroyed automatically:

```python
@pytest.fixture(scope="function")
def e2e_db():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        conn = sqlite3.connect(f.name, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        migrate_database(conn)  # Runs real migrations
        yield TestDatabaseConnection(conn)
    # automatic cleanup on fixture exit
```

The `TestDatabaseConnection` class wraps the raw SQLite connection with an interface compatible with the production `DatabaseConnection`, including the `get_db()` context manager that handles transactions (commit/rollback).

The `TestDatabaseConnectionAdapter` adapts `TestDatabaseConnection` to the interface expected by repositories (which call `self._db.get_db()`), completing the Adapter pattern without modifying production code.

### Dedicated EventBus

```python
@pytest.fixture(scope="function")
def e2e_event_bus():
    bus = object.__new__(EventBus)         # Bypasses __init__ with singleton
    bus._subscribers = defaultdict(list)   # Own state, no sharing
    return bus
```

The `EventBus` is implemented as a singleton in production. For tests, `object.__new__` is used to create a new instance without activating the singleton mechanism, ensuring each test has its own event bus without interference.

**Why this matters:** The EventBus is synchronous — when `publish()` is called, all registered handlers execute inline before returning. This eliminates the need for `asyncio.sleep()` or polling to wait for event processing.

### Stark Bank API Mocks

Two independent mocks are created as `scope="function"` fixtures:

**`mock_stark_invoice_api`** — simulates invoice creation:
```python
# Generates deterministic stark_invoice_id based on tax_id + amount
response.id = f"stark_{tax_id}_{amount}"
```

**`mock_stark_transfer_api`** — simulates transfer creation:
```python
# Generates stark_transfer_id based on the transfer's external_id
response.id = f"stark_transfer_{external_id}"
response.status = "created"
```

The mocks return `Mock()` objects with attributes (not dictionaries), mirroring the real behavior of the Stark Bank SDK. This allows testing attribute access (`response.id`) instead of key access (`response["id"]`).

### Main Fixture: `e2e_app`

The `e2e_app` fixture is the heart of the E2E infrastructure. It:

1. **Creates the full dependency graph** with test versions:
   - `InvoiceRepository(db_adapter)` — uses isolated database
   - `TransferRepository(db_adapter)` — uses isolated database
   - `InvoiceService(repo, mock_invoice_api, event_bus)`
   - `TransferService(repo, mock_transfer_api, event_bus)`

2. **Registers the `TransferHandler` in the EventBus** — this step is critical and was the main issue fixed in Step 0:
   ```python
   transfer_handler = TransferHandler(
       service=transfer_service,
       invoice_repository=invoice_repository,
   )
   e2e_event_bus.subscribe("invoice.paid", transfer_handler.handle_invoice_paid)
   ```
   Without this registration, the `invoice.paid` event emitted by the webhook processor would not trigger automatic transfer creation.

3. **Configures the `WebhookValidator` as a mock** that accepts all signatures by default:
   ```python
   mock_validator = Mock(spec=WebhookValidator)
   mock_validator.verify_signature.return_value = None  # Accepts
   ```
   The mock is exposed via `client._mock_validator` so that security tests can reconfigure it to reject signatures.

4. **Overrides service singletons** in the API modules so that HTTP routes use the test instances:
   ```python
   invoices_api_module._service = invoice_service
   transfers_api_module._service = transfer_service
   webhooks_api_module._get_webhook_receiver = lambda: webhook_receiver
   ```

5. **Applies `dependency_overrides` in FastAPI** for dependency injection (database, event bus, Stark APIs).

6. **Restores everything after the test** — the `finally` block in the fixture undoes all substitutions.

### Helpers and Utility Functions

**File:** [tests/e2e/helpers.py](../tests/e2e/helpers.py)

The `helpers.py` module provides reusable functions for the tests:

#### Data Creation via API

```python
def create_test_invoice(client, invoice_data, api_key) -> dict:
    """POST /invoices with authentication, asserting 201."""
```

#### Webhook Simulation

```python
def simulate_webhook(client, webhook_type, payload, signature) -> dict:
    """POST /webhooks/{type} with Digital-Signature header, asserting 200."""

def simulate_webhook_raw(client, webhook_type, payload, signature) -> Response:
    """Variant that returns the full Response without asserting status.
    Needed for error tests where we expect 401 or 500."""
```

The `_raw` variant was introduced specifically for error scenario tests, where the expected return is not 200.

#### Database Assertions

All assertion functions receive `db_connection` and internally use `TestDbAdapter` to instantiate repositories with the test database:

| Function | Assertion |
|----------|-----------|
| `assert_invoice_exists(db, id, status)` | Invoice exists with expected status |
| `assert_invoice_paid(db, id, net_amount)` | Invoice is PAID, with `fee`, `net_amount` and `paid_at` populated |
| `assert_transfer_created(db, invoice_id, status, amount)` | Transfer exists for the invoice, with correct status and amount |
| `assert_transfer_not_exists(db, invoice_id)` | No transfer exists for the invoice |
| `assert_transfer_completed(db, transfer_id)` | Transfer with SUCCESS status and `completed_at` populated |
| `assert_transfer_failed(db, transfer_id)` | Transfer with FAILED status and `error_message` populated |

#### Count and List Functions

```python
count_invoices_by_status(db, status) -> int
count_transfers_by_status(db, status) -> int
list_all_invoices(db) -> list[InvoiceModel]
list_all_transfers(db) -> list[TransferModel]
```

Used primarily to validate idempotency (correct number of records created) and query filters.

---

## Test Suites

### 8.2 — Invoice Creation Flow

**File:** [tests/e2e/test_invoice_creation_flow.py](../tests/e2e/test_invoice_creation_flow.py)  
**Class:** `TestInvoiceCreationFlow`  
**Tests:** 4

These tests verify the invoice creation flow triggered by the scheduler (`generate_invoices_job`). Since the scheduler instantiates its own dependencies internally, the tests use `@patch` from `unittest.mock` to replace the `InvoiceService` and `InvoiceGenerator` classes and inject versions that connect to the test database.

#### `test_invoice_creation_success`

**What it tests:** Complete batch generation flow via scheduler.

**Flow:**
1. Configures `InvoiceGenerator` mock to return 5 sample invoices with valid CPFs/CNPJs
2. Configures `InvoiceService` mock to return a real instance connected to the test database
3. Executes `generate_invoices_job()`
4. Verifies the Stark Bank API was called once for each invoice
5. Verifies all 5 invoices are in the database with `created` status
6. Verifies 5 `invoice.created` events were published to the EventBus with the correct structure (`invoice_id`, `amount`, `customer_name`)
7. Verifies the invoice IDs in the events match the IDs in the database

**Why it was implemented this way:** The scheduler is owned by `src/scheduler.py` and uses direct instantiation injection (not FastAPI `Depends`). `@patch` allows intercepting object creation without modifying production code.

#### `test_invoice_creation_with_batch_size_validation`

**What it tests:** That the generated batch size is within the expected range (8–12 invoices).

**Flow:**
1. Configures generator to return 10 invoices (within the 8–12 range)
2. Executes the job
3. Verifies `8 <= len(batch) <= 12`
4. Verifies all 10 invoices were persisted

#### `test_invoice_creation_with_valid_cpf_cnpj_formats`

**What it tests:** That invoices with CPF and CNPJ in different formats are accepted by the system.

**Validations:** Formatted CPF (xxx.xxx.xxx-xx), formatted CNPJ (xx.xxx.xxx/xxxx-xx), amounts in cents correctly converted to reais in the database.

#### `test_invoice_amounts_in_reais`

**What it tests:** The conversion from cents (API input) to reais (internal storage).

**Logic:** The input `amount: 50000` (cents) should be stored as `500.00` (reais) in the database. The test creates invoices with known amounts and verifies the conversion.

---

### 8.3 — Payment to Transfer Flow

**File:** [tests/e2e/test_payment_to_transfer_flow.py](../tests/e2e/test_payment_to_transfer_flow.py)  
**Class:** `TestPaymentToTransferFlow`  
**Tests:** 4

This is the core system flow: paying an invoice automatically triggers the creation of a transfer to the Stark Bank account. The complete chain is:

```
POST /invoices → [invoice created with CREATED status]
  ↓
POST /webhooks/invoice (type: "credited")
  → InvoiceWebhookProcessor.process()
  → InvoiceRepository.update() [status = PAID, fee, net_amount populated]
  → EventBus.publish("invoice.paid", {...})
  → TransferHandler.handle_invoice_paid()  ← registered in e2e_app fixture
  → TransferService.create_from_invoice()
  → StarkTransferAPI.create_transfer() [mock]
  → TransferRepository.create() [transfer saved with CREATED status]
```

#### `test_complete_payment_flow`

**What it tests:** The complete payment flow through to transfer creation.

**Step-by-step sequence:**
1. `POST /invoices` with customer "João Silva" data (R$ 500.00)
2. Extracts `invoice_id` and `stark_invoice_id` from the response
3. Builds webhook payload with `type: "credited"`, `fee: 200` (R$ 2.00)
4. `POST /webhooks/invoice` with `Digital-Signature: mock_valid_signature` header
5. Validates `webhook_response["status"] == "ok"`
6. Calls `assert_invoice_paid(db, invoice_id, expected_net_amount=499.00)`  
   → verifies status=PAID, fee=2.0, net_amount=499.00, paid_at≠None
7. Calls `assert_transfer_created(db, invoice_id, status=CREATED, amount=499.00)`
8. Verifies `transfer.external_id == f"invoice-{invoice_id}"` (idempotency pattern)
9. `GET /transfers/invoice/{invoice_id}` → verifies 200 with correct data

**Critical points verified:**
- `external_id = "invoice-{invoice_id}"` guarantees idempotency in Stark Bank
- `stark_transfer_id` is not None (mock was called and returned an ID)
- Transfer accessible via API (not only directly in the database)

#### `test_idempotency_multiple_webhooks`

**What it tests:** That receiving the same payment webhook 3 times creates only 1 transfer.

**Idempotency mechanism:** The `InvoiceWebhookProcessor` checks the current invoice status before processing it. If the invoice is already `PAID`, the processing is skipped (the `invoice.paid` event is not published again). Consequently, the `TransferHandler` is not triggered on duplicate calls.

**Verification:**
```python
created_transfers_count = count_transfers_by_status(db, TransferStatus.CREATED)
assert created_transfers_count == 1  # Exactly 1, not 3
```

#### `test_payment_flow_with_retry`

**What it tests:** The behavior when the Stark Bank transfer API fails.

**Setup:**
```python
def create_transfer_failing(**kwargs):
    raise RetriableError("Network timeout - service unavailable")

mock_stark_api["transfer_api"].create_transfer.side_effect = create_transfer_failing
```

**Verifications:**
- Invoice is marked as PAID (the payment occurred regardless of the transfer error)
- Transfer is created with FAILED status in the database (the system records the failure)
- `error_message` is populated with the error message

#### `test_payment_flow_different_amounts`

**What it tests:** That the `net_amount = amount - fee` calculation is correct for different values.

**Test cases:**
| amount (cents) | fee (cents) | expected net_amount (reais) |
|----------------|-------------|------------------------------|
| 10,000 | 50 | 99.50 |
| 50,000 | 200 | 498.00 |
| 100,000 | 500 | 995.00 |
| 250,000 | 1,000 | 2,490.00 |

---

### 8.4 — Transfer Status Updates

**File:** [tests/e2e/test_transfer_status_flow.py](../tests/e2e/test_transfer_status_flow.py)  
**Class:** `TestTransferStatusFlow`  
**Tests:** 3

These tests cover the transfer lifecycle after creation. Stark Bank sends status update webhooks to the `/webhooks/transfer` endpoints, which are processed by the `TransferWebhookProcessor`.

#### `test_transfer_processing_to_success`

**What it tests:** The complete lifecycle `CREATED → PROCESSING → SUCCESS`.

**Important technical detail:** The transfer webhook payload uses the real `stark_transfer_id` of the newly created transfer (not a fixed ID). This is obtained via `assert_transfer_created()`:
```python
transfer = assert_transfer_created(db, invoice_id, status=TransferStatus.CREATED)
stark_transfer_id = transfer.stark_transfer_id  # e.g.: "stark_transfer_invoice-abc123"
external_id = transfer.external_id              # e.g.: "invoice-abc123"
```

**Webhook sequence:**
1. `POST /webhooks/transfer` with `type: "processing"`, `id: stark_transfer_id`
2. Verifies database: `transfer.status == PROCESSING`, `updated_at` populated
3. `POST /webhooks/transfer` with `type: "success"`, `id: stark_transfer_id`
4. Verifies database: `transfer.status == SUCCESS`, `completed_at` populated
5. `GET /transfers/{transfer_id}` → verifies "success" status via API

**Field validations:**
- `completed_at` is only populated when `status = SUCCESS` (not in PROCESSING)
- `updated_at` is updated on each status transition

#### `test_transfer_failed`

**What it tests:** The `CREATED → FAILED` cycle with error capture.

**Failure payload:**
```json
{
  "log": {
    "type": "failed",
    "errors": [{"code": "insufficientFunds", "message": "Insufficient funds..."}],
    "transfer": {"id": "...", "status": "failed"}
  }
}
```

**Captured event:** The test subscribes directly to the `EventBus` to capture the `transfer.failed` event:
```python
captured_events = []
e2e_event_bus.subscribe("transfer.failed", lambda event: captured_events.append(event))
# ... processes webhook ...
assert len(captured_events) == 1
assert captured_events[0].payload["transfer_id"] == transfer_id
assert "error_message" in captured_events[0].payload
```

**Field validations:**
- `error_message` contains the Stark Bank error message
- `completed_at` is not populated for FAILED status
- `updated_at` is updated

#### `test_transfer_direct_to_success`

**What it tests:** That the system accepts transfers that go directly from `CREATED` to `SUCCESS`, without passing through `PROCESSING`. This is valid behavior in the Stark Bank API (the processing step can be omitted in immediate settlement cases).

**Verification:** After a direct `type: "success"` webhook, `transfer.status == SUCCESS` and `completed_at` is populated normally.

---

### 8.5 — Query Endpoints

**File:** [tests/e2e/test_query_endpoints.py](../tests/e2e/test_query_endpoints.py)  
**Class:** `TestQueryEndpoints`  
**Tests:** 4

These tests validate all query endpoints, including filters, pagination, and authentication requirements.

#### Internal helper `_create_and_pay_invoice`

To avoid repetition, the class defines a helper method that encapsulates invoice creation + payment:
```python
def _create_and_pay_invoice(self, e2e_app, e2e_db, mock_stark_api,
                             invoice_data, api_key_header, fee=100) -> dict:
    """Creates invoice and simulates payment. Returns dict with invoice_id and transfer_id."""
```

#### `test_list_invoices_with_filters`

**Setup:** 5 invoices created (amounts 100–500), 2 paid (the first 2).

**Cases covered:**
| Request | Expected result |
|---------|-----------------|
| `GET /invoices` | 5 invoices |
| `GET /invoices?status=paid` | 2 invoices, all with `status="paid"` |
| `GET /invoices?status=created` | 3 invoices, all with `status="created"` |
| `GET /invoices?limit=2&offset=0` | 2 invoices (page 1) |
| `GET /invoices?limit=2&offset=2` | 2 invoices (page 2) |
| `GET /invoices?limit=2&offset=4` | 1 invoice (last page) |
| `GET /invoices` without `X-API-Key` | 401 or 403 |

**Validated response structure:** Each invoice must have the fields `id`, `amount`, `status`, `customer_name`, `customer_tax_id` with correct types.

**Implementation note:** The API response can be `{"invoices": [...]}` or directly `[...]`. The test handles both formats using:
```python
invoices_list = data.get("invoices", data)
if isinstance(invoices_list, dict):
    invoices_list = invoices_list.get("invoices", [])
```

#### `test_get_invoice_by_id`

**Cases covered:**
- `GET /invoices/{id}` with valid ID → 200 with complete invoice
- Required fields verified: `id`, `amount`, `status`, `customer_name`, `customer_tax_id`, `customer_email`, `stark_invoice_id`, `created_at`
- `GET /invoices/00000000-0000-0000-0000-000000000000` → 404
- `GET /invoices/{id}` without `X-API-Key` → 401 or 403

#### `test_list_transfers_with_filters`

**Setup:**
- 3 invoices created and paid → 3 transfers with CREATED status
- Transfer 1: `success` webhook → SUCCESS status
- Transfer 2: `failed` webhook → FAILED status  
- Transfer 3: remains CREATED

**Cases covered:**
| Request | Result |
|---------|--------|
| `GET /transfers` | 3 transfers |
| `GET /transfers?status=success` | 1 transfer |
| `GET /transfers?status=failed` | 1 transfer |
| `GET /transfers?status=created` | 1 transfer |
| `GET /transfers?limit=1` | 1 transfer (pagination) |

**Validated structure:** Each transfer must have `id`, `invoice_id`, `amount`, `status`, `external_id`.

#### `test_get_transfer_by_invoice_id`

**The `GET /transfers/invoice/{invoice_id}` endpoint is a shortcut** that prevents the client from needing the `transfer_id` directly — knowing the `invoice_id` is sufficient.

**Cases covered:**
- `GET /transfers/invoice/{invoice_id}` → 200 with correct transfer
- `transfer.amount == invoice.net_amount` (value after fee)
- `transfer.external_id == f"invoice-{invoice_id}"` (idempotency pattern)
- `transfer.invoice_id == invoice_id`
- `GET /transfers/invoice/00000000-...` → 404
- Without `X-API-Key` → 401 or 403

---

### 8.6 — Error Scenarios

**File:** [tests/e2e/test_error_scenarios.py](../tests/e2e/test_error_scenarios.py)  
**Class:** `TestErrorScenarios`  
**Tests:** 4

These tests validate that the system is resilient to failures and does not break under adverse conditions.

#### `test_invalid_webhook_signature`

**What it tests:** Rejection of webhooks with invalid signatures.

**Technique:** The `mock_validator` created in `e2e_app` is exposed via `client._mock_validator`. The test reconfigures the mock to raise `InvalidSignatureError`:

```python
e2e_app._mock_validator.verify_signature.side_effect = InvalidSignatureError(
    "Invalid digital signature"
)
```

**Sequence:**
1. Creates invoice successfully (validator still accepts — it's the API, not webhook)
2. Configures mock to reject signatures
3. Sends invoice webhook with `simulate_webhook_raw` (does not assert 200)
4. Verifies: `response.status_code == 401`
5. Verifies: error message contains "signature" or "unauthorized"
6. Verifies: invoice still has CREATED status in the database
7. Re-enables validator (to pay the invoice)
8. Pays real invoice → transfer created
9. Rejects again → sends transfer webhook with invalid signature
10. Verifies: `response.status_code == 401`
11. Verifies: transfer status did not change

**Mock restoration:** The test uses `.side_effect = None` + `.return_value = None` to "undo" the rejection configuration before performing the legitimate payment mid-test.

#### `test_stark_api_timeout`

**What it tests:** Behavior when the Stark Bank API fails while creating an invoice.

**Setup:**
```python
mock_stark_api["invoice_api"].create_invoice.side_effect = Exception("Connection timeout")
```

**Verifications:**
- `POST /invoices` returns status 500
- Response body contains a descriptive error field
- No invoice with CREATED status for the test email
- An invoice with FAILED status is created for tracking, with `error_message` containing "timeout"
- The mock was called exactly once (no silent retry)

**System logic:** `InvoiceService.create_invoice()` persists the invoice with FAILED status before re-raising the exception. This enables subsequent auditing of failed attempts.

#### `test_database_error_recovery`

**What it tests:** That the system handles database errors during webhook processing without losing idempotency.

**Technique — `unittest.mock.patch.object` as context manager:**
```python
with patch.object(InvoiceRepository, "update", side_effect=Exception("Database locked")):
    # Webhook is sent but the update fails
    response = simulate_webhook_raw(client=e2e_app, webhook_type="invoice", payload=...)
    # Outside the with block: patch removed automatically
```

**Sequence:**
1. Creates invoice → CREATED status
2. Inside `patch.object`: sends payment webhook
3. Verifies: `response.status_code == 200` (webhook does not return 500 — graceful failure)
4. Verifies: response indicates processing error
5. Verifies: invoice is still CREATED (update did not occur)
6. Outside `patch.object`: sends the same webhook again
7. Verifies: `response.status_code == 200` with `status: "ok"`
8. Verifies: invoice is now PAID with correct values
9. Verifies: transfer was created with `amount = net_amount`

**Principle tested:** Webhooks are idempotent from the emitter's perspective — Stark Bank may resend the same event if it does not receive 200. The system must be able to reprocess it successfully once the transient error is resolved.

#### `test_webhook_with_unknown_invoice`

**What it tests:** That the system does not break when receiving a webhook referencing an invoice that does not exist locally.

**Scenario:** Stark Bank sends a payment webhook for `stark_invoice_id = "unknown_stark_invoice_12345"` that is not in the database.

**Verifications:**
- `response.status_code == 200` (no crash)
- Response is valid JSON (not a 500 error)
- No invoice with that `stark_invoice_id` is created in the database
- No transfer is created (no invoice to associate)

**System logic:** The `InvoiceWebhookProcessor` looks up by `stark_invoice_id`. If not found, it logs a warning and returns without processing, without raising an unhandled exception.

---

## Results and Coverage

### Test Count by File

| File | Class | Tests |
|------|-------|-------|
| [test_invoice_creation_flow.py](../tests/e2e/test_invoice_creation_flow.py) | `TestInvoiceCreationFlow` | 4 |
| [test_payment_to_transfer_flow.py](../tests/e2e/test_payment_to_transfer_flow.py) | `TestPaymentToTransferFlow` | 4 |
| [test_transfer_status_flow.py](../tests/e2e/test_transfer_status_flow.py) | `TestTransferStatusFlow` | 3 |
| [test_query_endpoints.py](../tests/e2e/test_query_endpoints.py) | `TestQueryEndpoints` | 4 |
| [test_error_scenarios.py](../tests/e2e/test_error_scenarios.py) | `TestErrorScenarios` | 4 |
| **Total** | | **19** |

### Modules Covered

| Module | E2E Coverage |
|--------|--------------|
| `src/modules/invoices/` | ~90% |
| `src/modules/transfers/` | ~92% |
| `src/modules/webhooks/` | ~91% |
| `src/shared/events/` | ~97% |

### How to Run

```bash
# All E2E tests
pytest tests/e2e/ -v --tb=short

# By module
pytest tests/e2e/test_invoice_creation_flow.py -v
pytest tests/e2e/test_payment_to_transfer_flow.py -v
pytest tests/e2e/test_transfer_status_flow.py -v
pytest tests/e2e/test_query_endpoints.py -v
pytest tests/e2e/test_error_scenarios.py -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing

# In random order (validates absence of inter-test dependencies)
pytest tests/e2e/ -v --randomly-seed=last
```

---

**Document generated in February 2026 — based on the PHASE 8 implementation of the Stark Bank Challenge**
