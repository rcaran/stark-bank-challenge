# Gradual Implementation Plan
# Stark Bank Challenge

**Version:** 1.0  
**Date:** February 2026  
**Based on:** [architecture.md](architecture.md)

## Overview

This document describes the gradual implementation plan for the system, organized in incremental phases that enable:
- ✅ Continuous validation through tests
- ✅ Progressive feature deployment
- ✅ Fast feedback at each step
- ✅ Risk minimization

## Implementation Strategy

### Principles

1. **Bottom-Up:** Start with the base components (shared) and build domain modules on top of them
2. **Incremental:** Each phase delivers testable and potentially deployable functionality
3. **Test-First:** Tests accompany the implementation at each phase
4. **Integration Early:** Integrate components as early as possible to detect problems

### Phase Completion Criteria

Each phase is only considered complete when:
- ✅ Code implemented according to architecture
- ✅ Unit tests with coverage > 80%
- ✅ Integration tests passing
- ✅ Documentation updated
- ✅ Code review completed
- ✅ Successful deployment in dev environment

---

## PHASE 0: Setup and Foundation

**Estimated Duration:** 1 day  
**Objective:** Prepare the development environment and base project structure

### Tasks

#### 0.1. Project Structure
- [X] Create complete directory structure as per [architecture.md](architecture.md#31-estrutura-de-diretórios)
- [X] Initialize dependency manager (Rye/Poetry)
- [X] Configure `.gitignore`
- [X] Create `__init__.py` files in all modules

#### 0.2. Dependencies
- [X] Create `pyproject.toml` with all dependencies
  ```toml
  [project]
  name = "stark-bank-challenge"
  version = "1.0.0"
  requires-python = ">=3.14"
  dependencies = [
      "fastapi>=0.115.0",
      "uvicorn[standard]>=0.30.0",
      "httpx>=0.28.0",
      "starkbank>=2.14.0",
      "apscheduler>=3.10.0",
      "validate-docbr>=1.10.0",
      "faker>=33.0.0",
      "python-dotenv>=1.0.0"
  ]
  
  [project.optional-dependencies]
  dev = [
      "pytest>=8.3.0",
      "pytest-asyncio>=0.24.0",
      "pytest-cov>=5.0.0",
      "pytest-mock>=3.14.0",
      "ruff>=0.8.0",
      "mypy>=1.11.0"
  ]
  ```
- [X] Install dependencies: `rye sync` or `poetry install`

#### 0.3. Configuration
- [X] Create `.env.example` with all required variables
- [X] Create `src/config/settings.py` - Settings dataclass
- [X] Create `src/config/constants.py` - Business constants
- [X] Document environment variables in README

#### 0.4. Testing Setup
- [X] Configure `pytest.ini` or `pyproject.toml` with pytest settings
- [X] Create `tests/conftest.py` with base fixtures
- [X] Configure test coverage (pytest-cov)
- [x] Create test directory structure

#### 0.5. Linting & Formatting
- [X] Configure Ruff in `pyproject.toml`
- [X] Create lint script: `ruff check src/`
- [X] Create format script: `ruff format src/`
- [X] Configure pre-commit hooks (optional)

#### 0.6. Base Documentation
- [X] Create README.md with setup instructions
- [X] Document project structure
- [X] Create CONTRIBUTING.md with development workflow

### Phase 0 Deliverables
- ✅ Project structured and configured
- ✅ Dependencies installed
- ✅ Test environment configured
- ✅ Basic documentation created

### Validation
```bash
# Check structure
tree src/

# Check dependencies
rye list  # or poetry show

# Check tests
pytest --collect-only

# Check linting
ruff check src/
```

---

## PHASE 1: Shared Components - Foundation

**Estimated Duration:** 2-3 days  
**Objective:** Implement shared components to be used by all modules

### 1.1. Logger

**Files:**
- `src/shared/utils/logger.py`

**Implementation:**
- [X] `StructuredLogger` class with JSON format
- [X] Support for levels: DEBUG, INFO, WARNING, ERROR
- [X] Context injection (correlation_id, module, event)
- [X] Output to console and file with rotation
- [X] Helper function `get_logger(module_name)`

**Tests:**
- [X] `tests/unit/shared/utils/test_logger.py`
- [X] Validate JSON format
- [X] Validate log levels
- [X] Validate context injection
- [X] Validate file rotation

**Usage example:**
```python
logger = get_logger("invoices.service")
logger.info("Invoice created", data={"invoice_id": "123", "amount": 500.00})
```

### 1.2. Custom Exceptions

**Files:**
- `src/shared/utils/errors.py`

**Implementation:**
- [X] `StarkBankError` - Base exception
- [X] `RetriableError` - Errors that allow retry
- [X] `NonRetriableError` - Errors that do not allow retry
- [X] `ValidationError` - Validation errors
- [X] `AuthenticationError` - Authentication errors
- [X] `NotFoundError` - Resource not found
- [X] `TimeoutError` - Operation timeout
- [X] `RateLimitError` - Rate limit exceeded

**Tests:**
- [X] `tests/unit/shared/utils/test_errors.py`
- [X] Validate exception hierarchy
- [X] Validate error messages

### 1.3. Validators

**Files:**
- `src/shared/utils/validators.py`

**Implementation:**
- [X] `validate_cpf(cpf: str) -> bool` - using validate-docbr
- [X] `validate_cnpj(cnpj: str) -> bool` - using validate-docbr
- [X] `validate_tax_id(tax_id: str) -> bool` - detects and validates CPF or CNPJ
- [X] `format_cpf(cpf: str) -> str` - formats with dots and dashes
- [X] `format_cnpj(cnpj: str) -> str` - formats with dots and dashes
- [X] `clean_tax_id(tax_id: str) -> str` - removes formatting

**Tests:**
- [X] `tests/unit/shared/utils/test_validators.py`
- [X] Tests with valid and invalid CPFs
- [X] Tests with valid and invalid CNPJs
- [X] Formatting tests
- [X] Edge cases (None, empty, special characters)

### 1.4. Data Generator

**Files:**
- `src/shared/utils/data_generator.py`

**Implementation:**
- [X] `DataGenerator` class wrapping Faker
- [X] `generate_valid_cpf() -> str` - valid CPF
- [X] `generate_valid_cnpj() -> str` - valid CNPJ
- [X] `generate_person_data() -> dict` - name, CPF, email
- [X] `generate_company_data() -> dict` - name, CNPJ, email
- [X] `generate_customer_data(prefer_cpf: bool = True) -> dict` - 70% CPF, 30% CNPJ
- [X] pt_BR locale configuration

**Tests:**
- [X] `tests/unit/shared/utils/test_data_generator.py`
- [X] Validate generated CPFs
- [X] Validate generated CNPJs
- [X] Validate CPF/CNPJ distribution (statistical)
- [X] Validate email format

### 1.5. Database Layer

**Files:**
- `src/shared/database/connection.py`
- `src/shared/database/migrations.py`
- `src/shared/database/base_repository.py`
- `migrations/001_initial_schema.sql`

**Implementation:**

**connection.py:**
- [X] `DatabaseConnection` - Singleton pattern
- [X] Connection pool with SQLite
- [X] WAL mode enabled
- [X] Configurable timeout
- [X] Context manager for transactions
- [X] Function `get_db() -> sqlite3.Connection`

**migrations.py:**
- [X] `MigrationRunner` - runs migrations
- [X] `schema_migrations` table for control
- [X] `run_migrations()` - applies pending migrations
- [X] `rollback_migration()` - migration rollback

**001_initial_schema.sql:**
- [X] `invoices` table - as per architecture
- [X] `transfers` table - as per architecture
- [X] `events_log` table - as per architecture
- [X] Required indexes
- [X] Constraints (FK, UNIQUE)

**base_repository.py:**
- [X] `BaseRepository` - abstract class
- [X] Base methods: `_execute()`, `_fetch_one()`, `_fetch_all()`
- [X] Context manager for transactions
- [X] Query logging
- [X] Exception handling

**Tests:**
- [X] `tests/unit/shared/database/test_connection.py`
- [X] `tests/unit/shared/database/test_migrations.py`
- [X] Validate singleton pattern
- [X] Validate WAL mode
- [X] Validate transactions
- [X] Validate migrations (apply/rollback)
- [X] Use in-memory database (`:memory:`)

### 1.6. Event Bus

**Files:**
- `src/shared/events/bus.py`
- `src/shared/events/types.py`
- `src/shared/events/logger.py`

**Implementation:**

**types.py:**
- [X] Dataclass `Event` - event_id, event_type, payload, metadata, timestamp
- [X] Enum `EventType` - all system event types
- [X] Type hints for handlers: `EventHandler = Callable[[Event], None]`

**bus.py:**
- [X] `EventBus` class - Singleton pattern
- [X] `subscribe(event_type: str, handler: EventHandler) -> None`
- [X] `unsubscribe(event_type: str, handler: EventHandler) -> None`
- [X] `publish(event_type: str, payload: dict, metadata: dict = None) -> None`
- [X] Handler registry: `Dict[str, List[EventHandler]]`
- [X] Logging of all published events
- [X] Exception handling in handlers (must not break publication)

**logger.py:**
- [X] `EventLogger` - persists events in the database
- [X] Automatic subscriber for all events
- [X] Saves to `events_log` table
- [X] `get_events(event_type: str = None, limit: int = 100) -> List[Event]`

**Tests:**
- [X] `tests/unit/shared/events/test_bus.py`
- [X] `tests/unit/shared/events/test_logger.py`
- [X] Validate subscribe/unsubscribe
- [X] Validate publish (synchronous)
- [X] Validate multiple handlers for the same event
- [X] Validate that handler failure does not break others
- [X] Validate persistence in events_log
- [X] Mock handlers

### Phase 1 Deliverables
- ✅ Structured logger working
- ✅ CPF/CNPJ validators
- ✅ Fake data generator
- ✅ Database with migrations
- ✅ Event Bus operational
- ✅ Unit tests > 80% coverage
- ✅ API documentation

### Phase 1 Validation
```bash
# Tests
pytest tests/unit/shared/ -v --cov=src/shared

# Validate database
python -c "from src.shared.database.migrations import run_migrations; run_migrations()"
sqlite3 stark_bank.db ".tables"

# Validate event bus
python -c "from src.shared.events.bus import EventBus; bus = EventBus(); print('OK')"
```

---

## PHASE 2: Stark Bank Integration Layer

**Estimated Duration:** 2-3 days  
**Objective:** Implement integration with Stark Bank API with retry logic

### 2.1. Retry Logic

**Files:**
- `src/shared/stark/retry.py`

**Implementation:**
- [X] Decorator `@retry_with_backoff` - configurable
- [X] Parameters: `max_attempts`, `delays`, `retriable_exceptions`, `non_retriable_exceptions`
- [X] Exponential backoff: [0, 60, 120, 240, 480] seconds
- [X] Logging of each attempt
- [X] retry_count persistence
- [X] Raise after max_attempts

**Tests:**
- [X] `tests/unit/shared/stark/test_retry.py`
- [X] Mock of function that fails N times
- [X] Validate number of attempts
- [X] Validate delays between attempts
- [X] Validate retriable vs non-retriable exceptions
- [X] Validate logging

### 2.2. Stark Bank Client Base

**Files:**
- `src/shared/stark/client.py`

**Implementation:**
- [X] `StarkBankClient` class - base class
- [X] Initialization of starkbank SDK
- [X] Environment configuration (sandbox/production)
- [X] project_id and private_key configuration
- [X] Logging of all calls
- [X] Exception handling and mapping to custom exceptions
- [X] Rate limit handling

**Tests:**
- [X] `tests/unit/shared/stark/test_client.py`
- [X] Mock of starkbank SDK
- [X] Validate initialization
- [X] Validate environment configuration
- [X] Validate exception handling

### 2.3. Invoice API

**Files:**
- `src/shared/stark/invoice_api.py`

**Implementation:**
- [X] `StarkInvoiceAPI(StarkBankClient)` class
- [X] `create_invoice(amount, tax_id, name, due_date, ...) -> InvoiceResponse` with retry
- [X] `get_invoice(invoice_id: str) -> InvoiceResponse`
- [X] `list_invoices(limit: int, after: str) -> List[InvoiceResponse]`
- [X] Dataclass `InvoiceResponse` for standardized response
- [X] Parameter validation
- [X] Amount conversion to cents (int)
- [X] Structured logging

**Tests:**
- [X] `tests/unit/shared/stark/test_invoice_api.py`
- [ ] `tests/integration/shared/stark/test_invoice_api_integration.py` (sandbox)
- [X] Mock of starkbank.invoice.create()
- [X] Validate retry on failures
- [X] Validate value conversion
- [X] Validate parameter validation
- [ ] **Real test:** create invoice in sandbox (integration test)

### 2.4. Transfer API

**Files:**
- `src/shared/stark/transfer_api.py`

**Implementation:**
- [X] `StarkTransferAPI(StarkBankClient)` class
- [X] `create_transfer(amount, external_id, bank_code, ...) -> TransferResponse` with retry
- [X] `get_transfer(transfer_id: str) -> TransferResponse`
- [X] `list_transfers(limit: int, after: str) -> List[TransferResponse]`
- [X] Dataclass `TransferResponse` for standardized response
- [X] Idempotency via `external_id`
- [X] Parameter validation
- [X] Amount conversion to cents (int)
- [X] Structured logging

**Tests:**
- [X] `tests/unit/shared/stark/test_transfer_api.py`
- [ ] `tests/integration/shared/stark/test_transfer_api_integration.py` (sandbox)
- [X] Mock of starkbank.transfer.create()
- [X] Validate retry on failures
- [X] Validate idempotency (same external_id)
- [X] Validate value conversion
- [ ] **Real test:** create transfer in sandbox (integration test)

### Phase 2 Deliverables
- ✅ Robust retry logic
- ✅ Stark Bank base client
- ✅ Invoice API with retry
- ✅ Transfer API with retry
- ✅ Unit tests > 80%
- ✅ Integration tests with sandbox passing
- ✅ API documentation

### Phase 2 Validation
```bash
# Unit tests
pytest tests/unit/shared/stark/ -v

# Integration tests (requires sandbox credentials)
pytest tests/integration/shared/stark/ -v

# Manual test
python -m examples.test_stark_invoice
python -m examples.test_stark_transfer
```

---

## PHASE 3: Security Layer

**Estimated Duration:** 1-2 days  
**Objective:** Implement security (API Key and webhook signature validation)

### 3.1. API Key Authentication

**Files:**
- `src/shared/security/api_key.py`

**Implementation:**
- [X] Function `verify_api_key(api_key: str) -> bool` - constant-time comparison
- [X] FastAPI Dependency `get_api_key_dependency` - for use in endpoints
- [X] `APIKeyHeader` class - extracts X-API-Key header
- [X] Exception `InvalidAPIKeyError`
- [X] Logging of authentication attempts

**Tests:**
- [X] `tests/unit/shared/security/test_api_key.py`
- [X] Validate correct API key
- [X] Validate incorrect API key
- [X] Validate constant-time comparison
- [X] Validate failure logging

### 3.2. Webhook Signature Validation

**Files:**
- `src/shared/security/signature.py`

**Implementation:**
- [X] Function `validate_webhook_signature(payload: bytes, signature: str, public_key: str) -> bool`
- [X] Use ECDSA for validation (according to Stark Bank documentation)
- [X] Load Stark Bank public key
- [X] Exception `InvalidSignatureError`
- [X] Logging of validations (success/failure)

**Tests:**
- [X] `tests/unit/shared/security/test_signature.py`
- [X] Mock of valid signature
- [X] Mock of invalid signature
- [X] Validate public key parsing
- [X] Validate ECDSA verification

### 3.3. Security Constants

**Files:**
- `src/shared/security/constants.py`

**Implementation:**
- [X] Stark Bank public key (sandbox and production)
- [X] Security headers
- [X] Request timeout
- [X] Rate limits

### Phase 3 Deliverables
- ✅ API Key authentication working
- ✅ Webhook signature validation
- ✅ Unit tests > 90% (security is critical)
- ✅ Security documentation

### Phase 3 Validation
```bash
# Tests
pytest tests/unit/shared/security/ -v --cov=src/shared/security

# Validate API Key
python -c "from src.shared.security.api_key import verify_api_key; print(verify_api_key('test-key'))"
```

---

## PHASE 4: Invoices Module

**Estimated Duration:** 3-4 days  
**Objective:** Implement the complete Invoices module (generation, persistence, API)

### 4.1. Invoice Models

**Files:**
- `src/modules/invoices/models.py`
- `src/modules/invoices/events.py`

**Implementation:**

**models.py:**
- [X] Dataclass `InvoiceModel` - represents an invoice in the system
- [X] Fields: id, stark_invoice_id, amount, customer_name, customer_tax_id, customer_email, status, created_at, paid_at, fee, net_amount, retry_count, last_retry_at, error_message
- [X] Methods: `to_dict()`, `from_dict()`, `calculate_net_amount()`
- [X] Field validation

**events.py:**
- [X] `InvoiceCreatedEvent` - created invoice payload
- [X] `InvoiceCreationFailedEvent` - failure payload
- [X] Event type constants

**Tests:**
- [X] `tests/unit/modules/invoices/test_models.py`
- [X] Validate model creation
- [X] Validate net_amount calculation
- [X] Validate to_dict/from_dict conversion
- [X] Validate field validation

### 4.2. Invoice Repository

**Files:**
- `src/modules/invoices/repository.py`

**Implementation:**
- [X] `InvoiceRepository(BaseRepository)` class
- [X] `create(invoice: InvoiceModel) -> None`
- [X] `get_by_id(invoice_id: str) -> Optional[InvoiceModel]`
- [X] `get_by_stark_id(stark_id: str) -> Optional[InvoiceModel]`
- [X] `update(invoice: InvoiceModel) -> None`
- [X] `list(status: Optional[str], limit: int, offset: int) -> List[InvoiceModel]`
- [X] `count(status: Optional[str]) -> int`
- [X] Operation logging
- [X] Exception handling

**Tests:**
- [X] `tests/unit/modules/invoices/test_repository.py`
- [X] Mock database
- [X] Validate CRUD operations
- [X] Validate queries with filters
- [X] Validate pagination

### 4.3. Invoice Generator

**Files:**
- `src/modules/invoices/generator.py`

**Implementation:**
- [X] `InvoiceGenerator` class
- [X] `generate_batch(count: int) -> List[dict]` - generates data for N invoices
- [X] `_generate_single() -> dict` - generates data for 1 invoice
- [X] Uses `DataGenerator` for fake data
- [X] Validates generated CPF/CNPJ
- [X] Configuration: min/max amount, due days, CPF/CNPJ ratio
- [X] Logging of generated invoices

**Tests:**
- [X] `tests/unit/modules/invoices/test_generator.py`
- [X] Validate batch generation (8-12 invoices)
- [X] Validate values within range
- [X] Validate valid CPF/CNPJ
- [X] Validate CPF/CNPJ distribution (70/30)

### 4.4. Invoice Service

**Files:**
- `src/modules/invoices/service.py`

**Implementation:**
- [X] `InvoiceService` class
- [X] `__init__(repository, stark_api, event_bus)`
- [X] `create_invoice(invoice_data: dict) -> InvoiceModel` - creates complete invoice
  - [X] Validate data
  - [X] Create in Stark Bank (with retry)
  - [X] Save to database
  - [X] Publish `invoice.created` event
  - [X] Exception handling + publish `invoice.creation_failed`
- [X] `get_invoice(invoice_id: str) -> Optional[InvoiceModel]`
- [X] `list_invoices(status, limit, offset) -> List[InvoiceModel]`
- [X] `update_invoice_status(invoice_id, status, **kwargs) -> None`
- [X] Structured logging

**Tests:**
- [X] `tests/unit/modules/invoices/test_service.py`
- [X] Mock repository, stark_api, event_bus
- [X] Validate complete creation flow
- [X] Validate retry on failures
- [X] Validate event publication
- [X] Validate exception handling

### 4.5. Invoice API Endpoints

**Files:**
- `src/modules/invoices/api.py`

**Implementation:**
- [X] FastAPI Router `invoice_router`
- [X] `POST /invoices` - create invoice (protected by API Key)
- [X] `GET /invoices` - list invoices (protected by API Key)
  - Query params: status, limit, offset
- [X] `GET /invoices/{invoice_id}` - fetch invoice (protected by API Key)
- [X] Response models (dict or dataclass)
- [X] Exception handling → HTTP status codes
- [X] Request logging

**Tests:**
- [X] `tests/integration/modules/invoices/test_api.py`
- [X] Use FastAPI TestClient
- [X] Mock service
- [X] Validate all endpoints
- [X] Validate authentication (with/without API Key)
- [X] Validate responses and status codes

### Phase 4 Deliverables
- ✅ Complete Invoices module
- ✅ Repository working
- ✅ Generator creating valid invoices
- ✅ Service with business logic
- ✅ Operational API endpoints
- ✅ Unit + integration tests > 85%
- ✅ API documentation

### Phase 4 Validation
```bash
# Tests
pytest tests/unit/modules/invoices/ -v
pytest tests/integration/modules/invoices/ -v

# Manual API test
uvicorn src.main:app --reload
curl -X POST http://localhost:8000/invoices -H "X-API-Key: dev-key" -d '{...}'
curl -X GET http://localhost:8000/invoices -H "X-API-Key: dev-key"
```

---

## PHASE 5: Webhooks Module

**Estimated Duration:** 3-4 days  
**Objective:** Implement reception and processing of webhooks (invoices and transfers)

### 5.1. Webhook Models

**Files:**
- `src/modules/webhooks/models.py`
- `src/modules/webhooks/events.py`

**Implementation:**

**models.py:**
- [X] Dataclass `WebhookEvent` - base webhook structure
- [X] Dataclass `InvoiceWebhookPayload` - invoice payload parser
- [X] Dataclass `TransferWebhookPayload` - transfer payload parser
- [X] Parsing and validation methods

**events.py:**
- [X] `InvoicePaidEvent` - confirmed paid invoice
- [X] `TransferProcessingEvent` - transfer being processed
- [X] `TransferCompletedEvent` - completed transfer
- [X] `TransferFailedEvent` - failed transfer
- [X] `WebhookValidationFailedEvent` - invalid signature

**Tests:**
- [X] `tests/unit/modules/webhooks/test_models.py`
- [X] Validate parsing of real payloads (Stark Bank samples)
- [X] Validate required fields
- [X] Validate type conversion

### 5.2. Webhook Validator

**Files:**
- `src/modules/webhooks/validator.py`

**Implementation:**
- [X] `WebhookValidator` class
- [X] `validate_signature(payload: bytes, signature: str) -> bool`
- [X] Wrapper over `security.signature.validate_webhook_signature`
- [X] Validation logging
- [X] Exception handling

**Tests:**
- [X] `tests/unit/modules/webhooks/test_validator.py`
- [X] Mock signature validation
- [X] Validate valid signature
- [X] Validate invalid signature
- [X] Validate logging

### 5.3. Invoice Webhook Processor

**Files:**
- `src/modules/webhooks/invoice_processor.py`

**Implementation:**
- [X] `InvoiceWebhookProcessor` class
- [X] `__init__(invoice_repository, event_bus)`
- [X] `process(webhook_payload: InvoiceWebhookPayload) -> None`
  - [X] Extract data (invoice_id, amount, fee, status)
  - [X] Fetch invoice from database via stark_invoice_id
  - [X] Update invoice status
  - [X] Calculate net_amount = amount - fee
  - [X] Update paid_at timestamp
  - [X] Publish `invoice.paid` event
- [X] Structured logging
- [X] Exception handling

**Tests:**
- [X] `tests/unit/modules/webhooks/test_invoice_processor.py`
- [X] Mock repository and event_bus
- [X] Validate payment webhook processing
- [X] Validate net_amount calculation
- [X] Validate invoice update
- [X] Validate event publication

### 5.4. Transfer Webhook Processor

**Files:**
- `src/modules/webhooks/transfer_processor.py`

**Implementation:**
- [X] `TransferWebhookProcessor` class
- [X] `__init__(transfer_repository, event_bus)`
- [X] `process(webhook_payload: TransferWebhookPayload) -> None`
  - [X] Extract data (transfer_id, status, error)
  - [X] Fetch transfer from database via stark_transfer_id
  - [X] Update transfer status
  - [X] Update updated_at timestamp
  - [X] If status="success": update completed_at, publish `transfer.completed`
  - [X] If status="failed": save error_message, publish `transfer.failed`
  - [X] If status="processing": publish `transfer.processing`
- [X] Structured logging
- [X] Exception handling

**Tests:**
- [X] `tests/unit/modules/webhooks/test_transfer_processor.py`
- [X] Mock repository and event_bus
- [X] Validate processing of "processing" status
- [X] Validate processing of "success" status
- [X] Validate processing of "failed" status
- [X] Validate transfer update
- [X] Validate event publication

### 5.5. Webhook Receiver (API)

**Files:**
- `src/modules/webhooks/receiver.py`
- `src/modules/webhooks/api.py`

**Implementation:**

**receiver.py:**
- [X] `WebhookReceiver` class
- [X] `__init__(validator, invoice_processor, transfer_processor, event_bus)`
- [X] `receive_invoice_webhook(payload: bytes, signature: str) -> dict`
  - [X] Validate signature
  - [X] Parse payload
  - [X] Process via InvoiceWebhookProcessor
  - [X] Return {"status": "ok"}
- [X] `receive_transfer_webhook(payload: bytes, signature: str) -> dict`
  - [X] Validate signature
  - [X] Parse payload
  - [X] Process via TransferWebhookProcessor
  - [X] Return {"status": "ok"}
- [X] Robust exception handling (always return 200 if possible)

**api.py:**
- [X] FastAPI Router `webhook_router`
- [X] `POST /webhooks/invoice` - receive invoice webhook (public, validated by signature)
- [X] `POST /webhooks/transfer` - receive transfer webhook (public, validated by signature)
- [X] Exception handling → always return 200 (except fatal validation)
- [X] Logging of all received webhooks

**Tests:**
- [X] `tests/unit/modules/webhooks/test_receiver.py`
- [X] `tests/integration/modules/webhooks/test_api.py`
- [X] Mock processors
- [X] Validate complete webhook flow
- [X] Validate signature validation
- [X] Validate exception handling
- [X] Validate HTTP responses

### Phase 5 Deliverables
- ✅ Invoice webhooks processed
- ✅ Transfer webhooks processed
- ✅ Signature validation working
- ✅ Operational API endpoints
- ✅ Unit + integration tests > 85%
- ✅ Webhook documentation

### Phase 5 Validation
```bash
# Tests
pytest tests/unit/modules/webhooks/ -v
pytest tests/integration/modules/webhooks/ -v

# Manual test (simulate webhook)
curl -X POST http://localhost:8000/webhooks/invoice \
  -H "Content-Type: application/json" \
  -H "Digital-Signature: <signature>" \
  -d '{"event": {"log": {...}}}'
```

---

## FASE 6: Transfers Module

**Estimated Duration:** 3-4 days  
**Objective:** Implement transfers module (automatic creation upon payment receipt)

### 6.1. Transfer Models

**Files:**
- `src/modules/transfers/models.py`
- `src/modules/transfers/events.py`

**Implementation:**

**models.py:**
- [X] Dataclass `TransferModel` - represents transfer in the system
- [X] Fields: id, invoice_id, stark_transfer_id, external_id, amount, status, created_at, updated_at, completed_at, retry_count, last_retry_at, error_message
- [X] Methods: `to_dict()`, `from_dict()`
- [X] Field validation

**events.py:**
- [X] `TransferInitiatedEvent` - transfer initiated
- [X] `TransferProcessingEvent` - transfer in processing
- [X] `TransferCompletedEvent` - transfer completed
- [X] `TransferFailedEvent` - transfer failed

**Tests:**
- [X] `tests/unit/modules/transfers/test_models.py`
- [X] Validate model creation
- [X] Validate to_dict/from_dict conversion
- [X] Validate status transitions

### 6.2. Transfer Repository

**Files:**
- `src/modules/transfers/repository.py`

**Implementation:**
- [X] Class `TransferRepository(BaseRepository)`
- [X] `create(transfer: TransferModel) -> None`
- [X] `get_by_id(transfer_id: str) -> Optional[TransferModel]`
- [X] `get_by_stark_id(stark_id: str) -> Optional[TransferModel]`
- [X] `get_by_external_id(external_id: str) -> Optional[TransferModel]` - for idempotency
- [X] `get_by_invoice_id(invoice_id: str) -> Optional[TransferModel]`
- [X] `update(transfer: TransferModel) -> None`
- [X] `list(status: Optional[str], limit: int, offset: int) -> List[TransferModel]`
- [X] `count(status: Optional[str]) -> int`
- [X] Operation logging

**Tests:**
- [X] `tests/unit/modules/transfers/test_repository.py`
- [X] Database mock
- [X] Validate CRUD operations
- [X] Validate queries with filters
- [X] Validate search by external_id (idempotency)

### 6.3. Transfer Service

**Files:**
- `src/modules/transfers/service.py`

**Implementation:**
- [X] Class `TransferService`
- [X] `__init__(repository, stark_api, event_bus, config)`
- [X] `create_transfer(invoice: InvoiceModel) -> TransferModel` - creates transfer
  - [X] Generate external_id = f"invoice-{invoice.id}"
  - [X] Check if transfer already exists (idempotency)
  - [X] Calculate amount = invoice.net_amount
  - [X] Build payload with Stark Bank destination account (constants)
  - [X] Create via StarkTransferAPI (with retry)
  - [X] Save to database with status="created"
  - [X] Publish event `transfer.initiated`
  - [X] Exception handling + publish `transfer.failed`
- [X] `get_transfer(transfer_id: str) -> Optional[TransferModel]`
- [X] `list_transfers(status, limit, offset) -> List[TransferModel]`
- [X] `update_transfer_status(transfer_id, status, **kwargs) -> None`
- [X] Structured logging

**Tests:**
- [X] `tests/unit/modules/transfers/test_service.py`
- [X] repository, stark_api, event_bus mock
- [X] Validate complete creation flow
- [X] Validate idempotency (same invoice)
- [X] Validate retry on failures
- [X] Validate event publishing
- [X] Validate destination account (Stark Bank)

### 6.4. Transfer Handler (Event Subscriber)

**Files:**
- `src/modules/transfers/handler.py`

**Implementation:**
- [X] Class `TransferHandler`
- [X] `__init__(service, invoice_repository)`
- [X] `handle_invoice_paid(event: Event) -> None` - subscriber for `invoice.paid`
  - [X] Extract invoice_id from event
  - [X] Load invoice from database
  - [X] Validate if invoice is paid
  - [X] Call TransferService.create_transfer()
  - [X] Structured logging
  - [X] Exception handling (should not break event bus)
- [X] Register handler in EventBus on initialization

**Tests:**
- [X] `tests/unit/modules/transfers/test_handler.py`
- [X] service, repository, event_bus mock
- [X] Validate event processing `invoice.paid`
- [X] Validate TransferService call
- [X] Validate exception handling

### 6.5. Transfer API Endpoints

**Files:**
- `src/modules/transfers/api.py`

**Implementation:**
- [X] FastAPI Router `transfer_router`
- [X] `GET /transfers` - list transfers (protected by API Key)
  - Query params: status, limit, offset
- [X] `GET /transfers/{transfer_id}` - get transfer (protected by API Key)
- [X] `GET /transfers/invoice/{invoice_id}` - get transfer by invoice (protected by API Key)
- [X] Response models
- [X] Exception handling → HTTP status codes
- [X] Request logging

**Tests:**
- [X] `tests/integration/modules/transfers/test_api.py`
- [X] Use FastAPI TestClient
- [X] Service mock
- [X] Validate all endpoints
- [X] Validate authentication
- [X] Validate responses and status codes

### Phase 6 Deliverables
- ✅ Complete Transfers module
- ✅ Automatic creation upon payment receipt
- ✅ Guaranteed idempotency
- ✅ Event handler working
- ✅ Operational API endpoints
- ✅ Unit + integration tests > 85%
- ✅ API documentation

### Phase 6 Validation
```bash
# Tests
pytest tests/unit/modules/transfers/ -v
pytest tests/integration/modules/transfers/ -v

# E2E Test (simulate complete flow)
# 1. Create invoice
# 2. Simulate payment webhook
# 3. Verify transfer created automatically
```

---

## FASE 7: Scheduler & Main Application

**Estimated Duration:** 2-3 days  
**Objective:** Implement invoice generation scheduler and integrate all modules

### 7.1. Scheduler

**Files:**
- `src/scheduler.py`

**Implementation:**
- [X] Function `run_scheduler()` - entry point
- [X] Configure APScheduler with IntervalTrigger
- [X] Job: `generate_invoices_job()`
  - [X] Use InvoiceGenerator to generate batch
  - [X] Use InvoiceService to create each invoice
  - [X] Execution logging
  - [X] Exception handling
- [X] Configuration: interval (3h), duration (24h = 8 cycles)
- [X] Graceful shutdown
- [X] Option to run in separate thread or process

**Tests:**
- [X] `tests/unit/test_scheduler.py`
- [X] InvoiceService mock
- [X] Validate scheduling
- [X] Validate job execution
- [X] Validate shutdown

### 7.2. FastAPI Main Application

**Files:**
- `src/main.py`

**Implementation:**
- [X] FastAPI app instance
- [X] Lifespan events:
  - [X] `startup`:
    - [X] Initialize database (run migrations)
    - [X] Initialize EventBus
    - [X] Register event handlers (TransferHandler)
    - [X] Start scheduler in thread (if configured)
    - [X] Startup logging
  - [X] `shutdown`:
    - [X] Stop scheduler
    - [X] Close database connections
    - [X] Shutdown logging
- [X] Include routers:
  - [X] `invoice_router` with prefix `/invoices`
  - [X] `transfer_router` with prefix `/transfers`
  - [X] `webhook_router` with prefix `/webhooks`
- [X] Root endpoint: `GET /` - redirect to `/docs`
- [X] Health check: `GET /health`
- [X] Global exception handlers
- [X] CORS configuration (if necessary)
- [X] Logging middleware

**Tests:**
- [X] `tests/integration/test_main.py`
- [X] Use TestClient
- [X] Validate startup/shutdown
- [X] Validate health check
- [X] Validate router integration

### 7.3. Health Check

**Files:**
- `src/health.py`

**Implementation:**
- [X] Function `check_health() -> dict`
- [X] Check:
  - [X] Database (execute simple query)
  - [X] Stark Bank API (optional - may be slow)
  - [X] EventBus
- [X] Return:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-02-14T10:30:00.123Z",
    "checks": {
      "database": "ok",
      "event_bus": "ok"
    },
    "version": "1.0.0",
    "uptime_seconds": 3600
  }
  ```

**Tests:**
- [X] `tests/unit/test_health.py`
- [X] Validate health check with everything OK
- [X] Validate health check with database failure

### 7.4. Dependency Injection Setup

**Files:**
- `src/dependencies.py`

**Implementation:**
- [X] Factory functions for FastAPI Depends():
  - [X] `get_db() -> sqlite3.Connection`
  - [X] `get_event_bus() -> EventBus`
  - [X] `get_invoice_repository() -> InvoiceRepository`
  - [X] `get_invoice_service() -> InvoiceService`
  - [X] `get_transfer_repository() -> TransferRepository`
  - [X] `get_transfer_service() -> TransferService`
  - [X] `get_webhook_validator() -> WebhookValidator`
- [X] Singletons where appropriate (EventBus, Database)

### Phase 7 Deliverables
- ✅ Scheduler generating invoices every 3h
- ✅ Complete and integrated FastAPI app
- ✅ Operational health check
- ✅ All modules integrated
- ✅ Integration tests > 80%
- ✅ System running end-to-end

### Phase 7 Validation
```bash
# Run complete application
uvicorn src.main:app --reload

# Check health
curl http://localhost:8000/health

# Check scheduler logs (should create invoices every 3h)
tail -f logs/app.log

# Check docs
open http://localhost:8000/docs
```

---

## FASE 8: End-to-End Tests

**Estimated Duration:** 2-3 days  
**Objective:** Implement E2E tests that validate complete flows

**Detailed plan:** [e2e-tests.md](e2e-tests.md)

### Summary

| Section | Description | Status |
|-------|-----------|--------|
| 8.1 E2E Test Infrastructure | Fixtures, helpers, mocks | ✅ Implemented |
| 8.2 E2E Test: Invoice Creation Flow | 4 tests for creation flow | ✅ Implemented |
| 8.3 E2E Test: Payment to Transfer Flow | 4 tests for payment → transfer flow | 🔧 Code exists |
| 8.4 E2E Test: Transfer Status Updates | Transfer status lifecycle | ⬜ Not implemented |
| 8.5 E2E Test: Query Endpoints | Query endpoints with filters | ⬜ Not implemented |
| 8.6 E2E Test: Error Scenarios | Error and resilience scenarios | ⬜ Not implemented |

**Files:**
- `tests/e2e/conftest.py`
- `tests/e2e/helpers.py`

**Implementation:**
- [X] E2E Fixtures:
  - [X] `e2e_app` - FastAPI TestClient with real/in-memory database
  - [X] `e2e_db` - Isolated database for each test
  - [X] `mock_stark_api` - Stark Bank API mock for E2E
  - [X] `sample_invoices` - Sample invoices
- [X] Helpers:
  - [X] `create_test_invoice()` - creates invoice via API
  - [X] `simulate_webhook()` - simulates webhook with signature
  - [X] `wait_for_event()` - waits for event to be published
  - [X] `assert_transfer_created()` - validates created transfer

### 8.2. E2E Test: Invoice Creation Flow

**Files:**
- `tests/e2e/test_invoice_creation_flow.py`

**Tests:**
- [X] `test_invoice_creation_success`
  - [X] Scheduler triggers generation
  - [X] Invoices created in Stark Bank (mock)
  - [X] Invoices saved in database
  - [X] Events `invoice.created` published
  - [X] Validate all invoices with status="created"

### 8.3. E2E Test: Payment to Transfer Flow

**Files:**
- `tests/e2e/test_payment_to_transfer_flow.py`

**Tests:**
- [X] `test_complete_payment_flow`
  - [X] Create invoice via API
  - [X] Simulate payment webhook
  - [X] Validate invoice with status="paid"
  - [X] Validate transfer created automatically
  - [X] Validate transfer with correct external_id
  - [X] Validate published events
  - [X] Validate logs
- [X] `test_idempotency_multiple_webhooks`
  - [X] Create invoice
  - [X] Simulate payment webhook 3 times
  - [X] Validate only 1 transfer created
- [X] `test_payment_flow_with_retry`
  - [X] Create invoice
  - [X] Simulate temporary failure in Stark Bank API
  - [X] Simulate payment webhook
  - [X] Validate automatic retry
  - [X] Validate transfer created after retry

### 8.4. E2E Test: Transfer Status Updates

**Files:**
- `tests/e2e/test_transfer_status_flow.py`

**Tests:**
- [X] `test_transfer_processing_to_success`
  - [X] Create invoice and simulate payment
  - [X] Transfer created with status="created"
  - [X] Simulate webhook transfer status="processing"
  - [X] Validate updated status
  - [X] Simulate webhook transfer status="success"
  - [X] Validate status="success" and completed_at filled
- [X] `test_transfer_failed`
  - [X] Create invoice and simulate payment
  - [X] Transfer created
  - [X] Simulate webhook transfer status="failed"
  - [X] Validate error_message saved
  - [X] Validate event `transfer.failed` published

### 8.5. E2E Test: Query Endpoints

**Files:**
- `tests/e2e/test_query_endpoints.py`

**Tests:**
- [X] `test_list_invoices_with_filters`
  - [X] Create multiple invoices
  - [X] Test GET /invoices with filters
  - [X] Validate pagination
  - [X] Validate authentication
- [X] `test_get_invoice_by_id`
- [X] `test_list_transfers_with_filters`
- [X] `test_get_transfer_by_invoice_id`

### 8.6. E2E Test: Error Scenarios

**Files:**
- `tests/e2e/test_error_scenarios.py`

**Tests:**
- [X] `test_invalid_webhook_signature`
  - [X] Simulate webhook with invalid signature
  - [X] Validate rejection
  - [X] Validate event `webhook.validation_failed`
- [X] `test_stark_api_timeout`
  - [X] Simulate timeout in Stark Bank API
  - [X] Validate automatic retry
  - [X] Validate failure after max attempts
- [X] `test_database_error_recovery`
  - [X] Simulate database error
  - [X] Validate exception handling
  - [X] Validate error logging

### Phase 8 Deliverables
- ✅ E2E tests covering main flows
- ✅ Idempotency validation
- ✅ Retry logic validation
- ✅ Error handling validation
- ✅ E2E coverage > 70%
- ✅ Scenario documentation

### Phase 8 Validation
```bash
# Run all E2E tests
pytest tests/e2e/ -v --tb=short

# Run with full coverage
pytest tests/ --cov=src --cov-report=html

# Check coverage
open htmlcov/index.html
```

---

## FASE 9: Documentation & Polish

**Estimated Duration:** 2 days  
**Objective:** Document complete system and prepare for production

### 9.1. API Documentation

**Files:**
- `docs/api.md`

**Content:**
- [X] List all endpoints
- [X] Request/Response examples
- [X] Authentication headers
- [X] Status codes
- [X] Error responses
- [X] Rate limits

### 9.2. README.md

**File:**
- `README.md`

**Content:**
- [X] Project description
- [X] Implemented features
- [X] Technology stack
- [X] Requirements (Python 3.14)
- [X] Setup instructions:
  - [X] Clone repo
  - [X] Install dependencies
  - [X] Configure .env
  - [X] Run migrations
  - [X] Start app
- [X] How to test
- [X] Deploy instructions (Railway)
- [X] License

### 9.3. Environment Configuration

**Files:**
- `.env.example`
- `docs/configuration.md`

**Content:**
- [X] All variables documented
- [X] Default values
- [X] How to obtain Stark Bank credentials
- [X] Configuration for development vs production

### 9.4. Deployment Guide

**Files:**
- `docs/deployment.md`
- `Procfile`
- `railway.toml` (or similar)

**Content:**
- [X] Railway setup instructions
- [X] Environment variables configuration
- [X] Database persistence
- [X] Monitoring setup
- [X] Troubleshooting

### 9.5. Code Quality

**Tasks:**
- [X] Run linting on all code: `ruff check src/`
- [X] Run linting on all code: `ruff check tests/`
- [X] Run formatting: `ruff format src/`
- [X] Run formatting: `ruff format tests/`
- [X] Run type checking: `mypy src/` (if configured)
- [X] Run type checking: `mypy tests/` (if configured)
- [X] Review TODOs and FIXMEs
- [X] Review comments
- [X] Remove dead code
- [X] Validate docstrings


### Phase 9 Deliverables
- ✅ Complete documentation
- ✅ Detailed README
- ✅ Deployment guide
- ✅ Clean and formatted code
- ✅ System ready for production

### Phase 9 Validation
```bash
# Validate documentation
# Read README and follow instructions from scratch

# Validate code
ruff check src/
ruff format --check src/

# Validate tests
pytest tests/ --cov=src --cov-report=term

# Validate deployment (Railway)
# Follow docs/deployment.md
```

---

## FASE 10: Deployment & Monitoring - Not implemented

**Estimated Duration:** 1-2 days  
**Objective:** Deploy on Railway and configure monitoring

### 10.1. Railway Setup

**Tasks:**
- [ ] Create Railway account
- [ ] Connect GitHub repository
- [ ] Configure environment variables
- [ ] Configure Procfile
- [ ] Configure volume for database (if available)
- [ ] Make first deploy
- [ ] Validate running application

### 10.2. Environment Variables (Production)

**Configure in Railway:**
```
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=<from-stark-bank>
STARK_BANK_PRIVATE_KEY=<base64-encoded>
API_KEY=<generate-secure-random>
DATABASE_URL=sqlite:///./data/stark_bank.db
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24
```

### 10.3. Database Persistence

**Tasks:**
- [ ] Configure volume in Railway (if available)
- [ ] Or migrate to PostgreSQL (Railway offers free tier)
- [ ] Test persistence after redeploy
- [ ] Configure backups (manual or automatic)

### 10.4. Monitoring

**Tasks:**
- [ ] Configure Railway dashboard
- [ ] Monitor logs
- [ ] Monitor CPU/Memory usage
- [ ] Configure alerts (if available)
- [ ] Test health check endpoint

### 10.5. Webhook Registration

**Tasks:**
- [ ] Obtain Railway URL: `https://<app>.railway.app`
- [ ] Register webhooks in Stark Bank:
  - [ ] Invoice webhook: `https://<app>.railway.app/webhooks/invoice`
  - [ ] Transfer webhook: `https://<app>.railway.app/webhooks/transfer`
- [ ] Validate webhook reception

### 10.6. Production Testing

**Tasks:**
- [ ] Wait for scheduler to create invoices (3h)
- [ ] Monitor creation logs
- [ ] Simulate invoice payment (Stark Bank sandbox)
- [ ] Validate received webhook
- [ ] Validate created transfer
- [ ] Validate complete flow logs

### Phase 10 Deliverables
- ✅ Application deployed on Railway
- ✅ Database persisting data
- ✅ Webhooks registered and working
- ✅ Monitoring configured
- ✅ System running in production for 24h

### Phase 10 Validation
```bash
# Check deployment
curl https://<app>.railway.app/health

# Check docs
open https://<app>.railway.app/docs

# Monitor logs
railway logs --tail

# Check scheduler
# Wait 3h and check invoice creation logs

# Test webhook (use Stark Bank tool)
```

---

## FASE 11: Final Review & Documentation

**Estimated Duration:** 1 day  
**Objective:** Review complete system and prepare delivery

### 11.1. Code Review

**Tasks:**
- [ ] Review code of each module
- [ ] Validate architecture compliance
- [ ] Validate error handling
- [ ] Validate logging
- [ ] Validate tests
- [ ] Validate documentation

### 11.2. Test Coverage Review

**Tasks:**
- [ ] Run full coverage
- [ ] Validate > 85% total coverage
- [ ] Identify critical gaps
- [ ] Add missing tests

### 11.3. Final Documentation

**Tasks:**
- [ ] Update [architecture.md](architecture.md) if necessary
- [ ] Update README.md
- [ ] Create CHANGELOG.md
- [ ] Document important technical decisions
- [ ] Document trade-offs and limitations
- [ ] Document next steps (future improvements)


### 11.4. Submission Checklist

**Validate:**
- [ ] ✅ Code on GitHub with complete README
- [ ] ✅ Application deployed and accessible
- [ ] ✅ Webhooks working
- [ ] ✅ Scheduler generating invoices
- [ ] ✅ Tests with > 85% coverage
- [ ] ✅ Complete documentation
- [ ] ✅ Structured logs
- [ ] ✅ Security implemented
- [ ] ✅ Robust error handling
- [ ] ✅ Guaranteed idempotency

### Phase 11 Deliverables
- ✅ Complete system reviewed
- ✅ Documentation finalized
- ✅ Ready for delivery

---

### Critical Path

```
Phase 0 → Phase 1 → Phase 2 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 10
         ↓
       Phase 3 (parallel with Phase 2)
```


## Risks and Mitigations

### Risk 1: Stark Bank API Integration

**Risk:** Unstable sandbox API or incomplete documentation  
**Mitigation:**
- Implement robust retry from the beginning
- Extensive mocking in tests
- Contact Stark Bank support if necessary

### Risk 2: Railway Persistence

**Risk:** Railway free tier does not persist files (SQLite)  
**Mitigation:**
- Option 1: Use mounted volume
- Option 2: Migrate to PostgreSQL (Railway offers free tier)
- Prepare code to be database-agnostic

### Risk 3: Scheduler on Free Tier

**Risk:** Railway free tier allows only 1 process  
**Mitigation:**
- Run scheduler in thread within the FastAPI process
- Code prepared to extract to a separate process in the future

### Risk 4: Test Coverage

**Risk:** Difficulty in achieving 85% coverage  
**Mitigation:**
- Start tests from phase 1
- Test-driven development where possible
- Focus on critical code (webhooks, transfers)

### Risk 5: Deadline

**Risk:** Not completing all phases on time  
**Mitigation:**
- Prioritize MVP: Phases 0-7 and 10 are critical
- Phases 8, 9, 11 can be reduced if necessary
- Continuously communicate progress

---

## Success Criteria

### Functional

- ✅ Generates invoices automatically every 3h for 24h
- ✅ Processes payment webhooks correctly
- ✅ Creates automatic transfers upon payment receipt
- ✅ Transfers are idempotent
- ✅ Processes transfer status webhooks
- ✅ Query APIs working

### Non-Functional

- ✅ Tests with > 85% coverage
- ✅ Structured logging in JSON
- ✅ Automatic retry with exponential backoff
- ✅ Digital signature validation
- ✅ Robust error handling
- ✅ Complete documentation
- ✅ Clean and well-structured code

### Technical

- ✅ Modular architecture as per specification
- ✅ Event-driven architecture implemented
- ✅ Python 3.14 without Pydantic
- ✅ FastAPI + SQLite
- ✅ Deploy working on Railway
- ✅ Webhooks registered and receiving events

---

## Next Steps after v1.0

### Short Term (v1.1)

- Circuit breaker pattern
- PostgreSQL as database option
- Metrics with Prometheus
- Rate limiting on endpoints
- Monitoring dashboard
- Manual retry of failed operations

### Medium Term (v2.0)

- Microservices (separate modules)
- Message queue (RabbitMQ/SQS)
- Distributed tracing
- OAuth2 authentication
- Multi-tenant support
- API versioning

### Long Term (v3.0)

- Kubernetes deployment
- Auto-scaling
- Multi-region
- Real-time dashboard
- Analytics and BI
- Machine learning for fraud detection

---

## Conclusion

This gradual implementation plan ensures:

1. **Incremental Progress:** Each phase delivers value and can be validated
2. **Risk Reduction:** Problems are detected early
3. **Quality:** Tests accompany implementation
4. **Flexibility:** Phases can be adjusted as needed
5. **Documentation:** System always documented

---

**Living document - update as implementation progresses**
