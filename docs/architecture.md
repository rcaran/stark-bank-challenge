# Stark Bank Challenge - Architecture Document

**Version:** 1.0  
**Date:** February 2026  
**Author:** Stark Bank Selection Process Candidate

## 1. Overview

### 1.1. System Objective

The system implements an automated integration with the Stark Bank platform to:

- **Automatically generate invoices** every 3 hours for 24 hours
- **Process payment notifications** via webhooks
- **Execute automatic transfers** of received amounts

### 1.2. Architectural Principles

#### Modular Monolith
- Single application with well-defined and decoupled modules
- Prepared for future evolution into microservices
- Inter-module communication via Event Bus

#### Event-Driven Architecture
- Decoupling via event publish/subscribe
- Complete operation traceability
- Facilitates auditing and debugging

#### Resilience by Design
- Automatic retry with exponential backoff
- Explicit failure handling
- Graceful degradation

#### Security First
- Digital signature validation
- API Key authentication
- Principle of least privilege

### 1.3. Technology Stack

| Component | Technology | Version | Justification |
|------------|-----------|---------|---------------|
| Language | Python | 3.14 | Project requirement |
| Web Framework | FastAPI | 0.115+ | Performance, async, native OpenAPI |
| Database | SQLite | 3.x | Simplicity, portability, no setup |
| HTTP Client | httpx | 0.28+ | Native async, built-in retry |
| Scheduler | APScheduler | 3.10+ | In-process cron jobs |
| Stark Bank SDK | starkbank | 2.14+ | Official SDK |
| Validation | validate-docbr | 1.10+ | CPF/CNPJ validation |
| Faker | Faker | 33+ | Fake data generation |
| Linting | Ruff | 0.8+ | Fast linting and formatting |
| Testing | pytest | 8.3+ | Standard test framework |

**Note:** Pydantic is not used (alignment with Stark Bank stack).

## 2. High-Level Architecture

### 2.1. Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     STARK BANK CHALLENGE                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐              ┌──────────────┐              │
│  │   FastAPI   │◄────────────►│  Scheduler   │              │
│  │  Web Server │              │ (APScheduler)│              │
│  └──────┬──────┘              └──────┬───────┘              │
│         │                             │                       │
│         │         ┌──────────────────┘                       │
│         │         │                                           │
│         ▼         ▼                                           │
│  ┌─────────────────────────────────────────┐                │
│  │          DOMAIN MODULES                  │                │
│  ├──────────────┬──────────────┬───────────┤                │
│  │   Invoices   │  Webhooks    │ Transfers │                │
│  │   Module     │   Module     │  Module   │                │
│  └──────┬───────┴──────┬───────┴─────┬─────┘                │
│         │              │             │                       │
│         └──────────────┼─────────────┘                       │
│                        ▼                                      │
│         ┌─────────────────────────────┐                      │
│         │    SHARED COMPONENTS         │                      │
│         ├────────────┬────────────────┤                      │
│         │ Event Bus  │ Stark Bank API │                      │
│         │  Logger    │   Security     │                      │
│         │ Database   │   Retry Logic  │                      │
│         └────────────┴────────────────┘                      │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         ▼
              ┌──────────────────┐
              │  Stark Bank API   │
              │    (Sandbox)      │
              └──────────────────┘
```

### 2.2. System Processes

#### Process 1: Web API (FastAPI)
- **Port:** 8000
- **Responsibility:** Expose REST endpoints and process webhooks
- **Endpoints:**
  - `POST /webhooks/invoice` - Receives invoice payment notifications
  - `POST /webhooks/transfer` - Receives transfer status notifications
  - `GET /invoices` - List invoices
  - `GET /invoices/{id}` - Query specific invoice
  - `GET /transfers` - List transfers
  - `GET /transfers/{id}` - Query specific transfer
  - `GET /health` - Health check
  - `GET /docs` - Swagger UI

#### Process 2: Scheduler (Background)
- **Responsibility:** Execute invoice generation periodically
- **Schedule:** Every 3 hours
- **Duration:** 24 hours (8 cycles)
- **Execution:**
  - Runs in a separate thread
  - Does not block the API
  - Can be extracted to an independent process in the future

## 3. Modular Architecture

### 3.1. Directory Structure

```
stark-bank-challenge/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── scheduler.py               # Scheduler entry point
│   │
│   ├── modules/                   # Domain Modules
│   │   ├── __init__.py
│   │   │
│   │   ├── invoices/              # Invoice Module
│   │   │   ├── __init__.py
│   │   │   ├── generator.py      # Invoice generation
│   │   │   ├── service.py        # Business logic
│   │   │   ├── repository.py     # Database access
│   │   │   ├── models.py         # Data models
│   │   │   ├── events.py         # Event definitions
│   │   │   └── api.py            # REST endpoints
│   │   │
│   │   ├── webhooks/              # Webhook Module
│   │   │   ├── __init__.py
│   │   │   ├── receiver.py       # Receives webhooks
│   │   │   ├── validator.py      # Validates signatures
│   │   │   ├── invoice_processor.py  # Processes invoice webhooks
│   │   │   ├── transfer_processor.py # Processes transfer webhooks
│   │   │   ├── events.py         # Event definitions
│   │   │   └── api.py            # REST endpoints
│   │   │
│   │   └── transfers/             # Transfer Module
│   │       ├── __init__.py
│   │       ├── service.py         # Business logic
│   │       ├── handler.py         # Event handler
│   │       ├── repository.py      # Database access
│   │       ├── models.py          # Data models
│   │       ├── events.py          # Event definitions
│   │       └── api.py             # REST endpoints
│   │
│   ├── shared/                    # Shared Components
│   │   ├── __init__.py
│   │   │
│   │   ├── database/              # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py     # Connection pool
│   │   │   ├── migrations.py     # Schema migrations
│   │   │   └── base_repository.py # Base class
│   │   │
│   │   ├── events/                # Event Bus
│   │   │   ├── __init__.py
│   │   │   ├── bus.py            # Event bus implementation
│   │   │   ├── types.py          # Event types
│   │   │   └── logger.py         # Event logger
│   │   │
│   │   ├── stark/                 # Stark Bank Integration
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # Base client
│   │   │   ├── invoice_api.py    # Invoice API
│   │   │   ├── transfer_api.py   # Transfer API
│   │   │   └── retry.py          # Retry logic
│   │   │
│   │   ├── security/              # Security
│   │   │   ├── __init__.py
│   │   │   ├── api_key.py        # API Key validator
│   │   │   ├── signature.py      # Webhook signature
│   │   │   └── constants.py      # Security constants
│   │   │
│   │   └── utils/                 # Utilities
│   │       ├── __init__.py
│   │       ├── logger.py          # Structured logger
│   │       ├── validators.py     # CPF/CNPJ validators
│   │       ├── data_generator.py # Faker wrapper
│   │       └── errors.py          # Custom exceptions
│   │
│   └── config/                    # Configuration
│       ├── __init__.py
│       ├── settings.py            # App settings
│       └── constants.py           # Business constants
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── e2e/                      # End-to-end tests
│
├── docs/                          # Documentation
│   ├── challenge.md              # Business requirements
│   ├── architecture.md           # This document
│   └── api.md                    # API specification
│
├── migrations/                    # Database migrations
│   └── 001_initial_schema.sql
│
├── .env.example                   # Environment template
├── .gitignore
├── pyproject.toml                # Dependencies (Poetry/Rye)
├── Procfile                      # Railway deployment
└── README.md                     # Setup instructions
```

### 3.2. Domain Modules

#### 3.2.1. Invoices Module

**Responsibilities:**
- Generate invoices with random data
- Validate CPF/CNPJ
- Create invoices via Stark Bank API
- Persist invoices in the database
- Publish creation events
- Expose query endpoints

**Components:**
- `InvoiceGenerator`: Generates data and creates invoices
- `InvoiceService`: Business logic
- `InvoiceRepository`: Persistence
- `InvoiceAPI`: REST endpoints

**Published Events:**
- `InvoiceCreated`: Invoice successfully created
- `InvoiceCreationFailed`: Creation failure

#### 3.2.2. Webhooks Module

**Responsibilities:**
- Receive webhooks from Stark Bank (invoices and transfers)
- Validate digital signature
- Process invoice payment payloads
- Process transfer status payloads
- Update invoice and transfer statuses
- Publish payment and transfer events

**Components:**
- `WebhookReceiver`: HTTP endpoints
- `SignatureValidator`: Signature validation
- `InvoiceWebhookProcessor`: Invoice processing
- `TransferWebhookProcessor`: Transfer processing

**Published Events:**
- `InvoicePaid`: Confirmed paid invoice
- `TransferProcessing`: Transfer in processing
- `TransferCompleted`: Transfer successfully completed
- `TransferFailed`: Transfer failed
- `WebhookValidationFailed`: Invalid signature

#### 3.2.3. Transfers Module

**Responsibilities:**
- Listen to `InvoicePaid` events
- Calculate net amount (amount - fee)
- Create transfers via Stark Bank API
- Ensure idempotency
- Persist transfers
- Expose query endpoints

**Components:**
- `TransferService`: Business logic
- `TransferHandler`: Event handler (InvoicePaid)
- `TransferRepository`: Persistence
- `TransferAPI`: REST endpoints

**Published Events:**
- `TransferCompleted`: Transfer completed
- `TransferFailed`: Transfer failure

### 3.3. Shared Components

#### 3.3.1. Event Bus

**Implementation:**
- Pattern: In-memory Pub/Sub
- Synchronous (for simplicity)
- Handlers registered at initialization

**Interface:**
```python
class EventBus:
    def publish(self, event_type: str, payload: dict) -> None:
        """Publishes event to all subscribers"""
        
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Registers handler for event type"""
        
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Removes handler"""
```

**System Events:**
- `invoice.created` - Invoice created
- `invoice.paid` - Invoice paid
- `transfer.initiated` - Transfer initiated
- `transfer.processing` - Transfer in processing
- `transfer.completed` - Transfer successfully completed
- `transfer.failed` - Transfer failed
- `operation.failed` - Operation failed

**Persistence:**
- All events are saved in `events_log` for auditing

#### 3.3.2. Database Layer

**Technology:** SQLite
- File: `stark_bank.db`
- Mode: WAL (Write-Ahead Logging) for concurrency
- Connection pool: native sqlite3

**Tables:**
```sql
-- Invoices
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    stark_invoice_id TEXT UNIQUE,
    amount REAL NOT NULL,
    customer_name TEXT NOT NULL,
    customer_tax_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    fee REAL,
    net_amount REAL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT
);

-- Transfers
CREATE TABLE transfers (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    stark_transfer_id TEXT UNIQUE,
    external_id TEXT UNIQUE,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TEXT,
    error_message TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Events Log (audit)
CREATE TABLE events_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    timestamp TEXT NOT NULL,
    processed INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_stark_id ON invoices(stark_invoice_id);
CREATE INDEX idx_transfers_invoice ON transfers(invoice_id);
CREATE INDEX idx_transfers_external_id ON transfers(external_id);
CREATE INDEX idx_events_type ON events_log(event_type);
CREATE INDEX idx_events_timestamp ON events_log(timestamp);
```

#### 3.3.3. Stark Bank Integration

**Wrapper over official SDK:**
- Abstraction to facilitate testing
- Automatic retry with exponential backoff
- Structured logging of all operations

**Invoice API:**
```python
class StarkInvoiceAPI:
    def create_invoice(
        self,
        amount: int,
        tax_id: str,
        name: str,
        due_date: datetime
    ) -> InvoiceResponse:
        """Creates invoice in Stark Bank with retry"""
```

**Transfer API:**
```python
class StarkTransferAPI:
    def create_transfer(
        self,
        amount: int,
        external_id: str,
        bank_code: str,
        branch_code: str,
        account_number: str,
        account_type: str,
        tax_id: str,
        name: str
    ) -> TransferResponse:
        """Creates transfer in Stark Bank with retry"""
```

**Retry Strategy:**
```python
@retry(
    max_attempts=5,
    delays=[0, 60, 120, 240, 480],  # seconds
    retriable_exceptions=[TimeoutError, RateLimitError, ServerError],
    non_retriable_exceptions=[ValidationError, AuthError]
)
def _call_api(self, ...):
    """Executes call with automatic retry"""
```

#### 3.3.4. Security Layer

**API Key Authentication:**
```python
async def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """Validates API Key securely (constant-time comparison)"""
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=401)
```

**Webhook Signature Validation:**
```python
def validate_webhook_signature(
    payload: bytes,
    signature: str,
    public_key: str
) -> bool:
    """Validates webhook digital signature using ECDSA"""
```

**Protected Endpoints:**
- `GET /invoices*` - Requires API Key
- `GET /transfers*` - Requires API Key
- `GET /docs` - Requires API Key

**Public Endpoints:**
- `GET /health` - No authentication
- `POST /webhooks/invoice` - Validated by digital signature
- `POST /webhooks/transfer` - Validated by digital signature

#### 3.3.5. Logger

**Format:** Structured JSON
```json
{
    "timestamp": "2026-02-14T10:30:00.123Z",
    "level": "INFO",
    "module": "invoices.generator",
    "event": "invoice_created",
    "message": "Invoice created successfully",
    "data": {
        "invoice_id": "uuid-123",
        "amount": 500.00,
        "customer_tax_id": "123.456.789-00"
    },
    "correlation_id": "req-uuid-456"
}
```

**Levels:**
- `DEBUG`: Development details
- `INFO`: Normal operations
- `WARNING`: Unexpected non-critical situations
- `ERROR`: Failures requiring attention

**Outputs:**
- Console (stdout)
- File: `logs/app.log` (daily rotation)

## 4. Design Patterns

### 4.1. Repository Pattern

Abstracts database access, facilitating testing and maintenance.

```python
class InvoiceRepository:
    def create(self, invoice: InvoiceModel) -> None:
        """Inserts invoice into database"""
        
    def get_by_id(self, invoice_id: str) -> Optional[InvoiceModel]:
        """Fetches invoice by ID"""
        
    def get_by_stark_id(self, stark_id: str) -> Optional[InvoiceModel]:
        """Fetches invoice by Stark ID"""
        
    def update(self, invoice: InvoiceModel) -> None:
        """Updates invoice"""
        
    def list(self, status: Optional[str], limit: int, offset: int) -> List[InvoiceModel]:
        """Lists invoices with filters"""
```

### 4.2. Service Layer

Encapsulates business logic, orchestrating repositories and external APIs.

```python
class InvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        stark_api: StarkInvoiceAPI,
        event_bus: EventBus
    ):
        self.repository = repository
        self.stark_api = stark_api
        self.event_bus = event_bus
        
    def create_invoice(self, data: dict) -> InvoiceModel:
        """Creates invoice with full business logic"""
        # 1. Validate data
        # 2. Create in Stark Bank
        # 3. Save to database
        # 4. Publish event
        # 5. Return model
```

### 4.3. Event-Driven Pattern

Decoupling between modules via events.

```python
# Publisher (Invoice Generator)
invoice = service.create_invoice(data)
event_bus.publish("invoice.created", {
    "invoice_id": invoice.id,
    "amount": invoice.amount,
    "created_at": invoice.created_at
})

# Subscriber (Transfer Handler)
event_bus.subscribe("invoice.paid", transfer_handler.handle_invoice_paid)
```

### 4.4. Dependency Injection

Facilitates testing and flexibility.

```python
# DI container (simplified)
def get_invoice_service() -> InvoiceService:
    """Factory function for InvoiceService"""
    db = get_database()
    repository = InvoiceRepository(db)
    stark_api = StarkInvoiceAPI()
    event_bus = get_event_bus()
    return InvoiceService(repository, stark_api, event_bus)

# Usage
@router.post("/invoices")
def create_invoice(
    data: dict,
    service: InvoiceService = Depends(get_invoice_service)
):
    return service.create_invoice(data)
```

### 4.5. Retry Pattern

Automatic resilience with exponential backoff.

```python
def retry_with_backoff(
    func: Callable,
    max_attempts: int = 5,
    delays: List[int] = [0, 60, 120, 240, 480]
) -> Any:
    """
    Executes function with automatic retry
    
    Args:
        func: Function to execute
        max_attempts: Maximum number of attempts
        delays: List of delays in seconds between attempts
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except RetriableError as e:
            if attempt == max_attempts:
                raise
            delay = delays[attempt - 1]
            logger.warning(f"Attempt {attempt} failed, retrying in {delay}s")
            time.sleep(delay)
        except NonRetriableError:
            raise  # Does not retry
```

### 4.6. Factory Pattern

Creation of complex objects.

```python
class InvoiceFactory:
    @staticmethod
    def create_random_invoice() -> dict:
        """Creates random invoice data"""
        faker = Faker('pt_BR')
        
        # 30% CPF, 70% CNPJ
        is_cpf = random.random() < 0.7
        
        if is_cpf:
            tax_id = generate_valid_cpf()
            name = faker.name()
        else:
            tax_id = generate_valid_cnpj()
            name = faker.company()
            
        return {
            "amount": random.randint(10000, 100000),  # cents
            "tax_id": tax_id,
            "name": name,
            "email": faker.email(),
            "due_date": datetime.now() + timedelta(days=3)
        }
```

## 5. Data Flows

### 5.1. Invoice Creation Flow

```
1. Scheduler triggers InvoiceGenerator (every 3h)
2. InvoiceGenerator:
   a. Generates random data (8-12 invoices)
   b. Validates CPF/CNPJ
3. InvoiceService:
   a. Creates invoice via StarkInvoiceAPI (with retry)
   b. Saves to database via InvoiceRepository
   c. Publishes "invoice.created" event
4. EventBus notifies subscribers:
   a. Logger: records in events_log
   b. Metrics: increments counter
```

### 5.2. Webhook Processing Flow

```
1. Stark Bank sends POST /webhooks/invoice
2. WebhookReceiver:
   a. Validates digital signature
   b. Parses JSON payload
3. WebhookProcessor:
   a. Extracts data (invoice_id, amount, fee)
   b. Calculates net_amount = amount - fee
   c. Updates invoice via InvoiceRepository
   d. Publishes "invoice.paid" event
4. TransferHandler (subscriber of "invoice.paid"):
   a. Listens to event
   b. Triggers TransferService
5. TransferService:
   a. Checks if transfer already exists (idempotency)
   b. Creates transfer via StarkTransferAPI (with retry)
   c. Saves to database via TransferRepository
   d. Publishes "transfer.completed" event
6. WebhookReceiver returns HTTP 200
```

### 5.3. Transfer Flow

```
1. TransferHandler receives "invoice.paid" event
2. TransferHandler:
   a. Extracts invoice_id from event
   b. Loads invoice from database
   c. Calculates net_amount
3. TransferService:
   a. Checks existing transfer via external_id
   b. If exists: returns existing (idempotency)
   c. If not exists:
      i. Builds transfer payload
      ii. Creates via StarkTransferAPI (with retry)
      iii. Saves to database with status="created"
      iv. Publishes "transfer.initiated" event
```

### 5.4. Transfer Webhook Processing Flow

```
1. Stark Bank sends POST /webhooks/transfer
2. WebhookReceiver:
   a. Validates digital signature
   b. Parses JSON payload
3. TransferWebhookProcessor:
   a. Extracts data (transfer_id, status)
   b. Fetches transfer from database via stark_transfer_id
   c. Updates transfer status
   d. Saves updated_at timestamp
   e. Decides which event to publish:
      - status="processing" → publishes "transfer.processing"
      - status="success" → publishes "transfer.completed" + updates completed_at
      - status="failed" → publishes "transfer.failed" + saves error_message
4. EventBus notifies subscribers:
   a. Logger: records in events_log
   b. Metrics: updates counters
   c. Alerts: notifies on failure
5. WebhookReceiver returns HTTP 200
```

**Transfer States from Stark Bank:**
- `created` - Transfer created (initial local status)
- `processing` - Being processed at Stark Bank
- `success` - Transfer successfully completed
- `failed` - Transfer failed (banking error, insufficient balance, etc.)

### 5.5. Retry Flow

```
1. Operation fails with retriable error
2. RetryLogic:
   a. Checks error type
   b. If retriable error and attempts < 5:
      i. Increments retry_count
      ii. Records last_retry_at
      iii. Waits for delay (exponential backoff)
      iv. Executes again
   c. If non-retriable error or attempts = 5:
      i. Saves error_message
      ii. Updates status to "failed"
      iii. Publishes "operation.failed" event
      iv. Raises exception
```

## 6. Resilience Strategies

### 6.1. Retry with Exponential Backoff

**Configuration:**
- Max attempts: 5
- Delays: [0s, 60s, 120s, 240s, 480s]
- Total max time: ~15 minutes

**Retriable Errors:**
- `TimeoutError`: Connection/read timeout
- `RateLimitError`: HTTP 429 (Too Many Requests)
- `ServerError`: HTTP 5xx (500, 502, 503, 504)
- `ConnectionError`: Network failure

**Non-Retriable Errors:**
- `ValidationError`: HTTP 422 (Unprocessable Entity)
- `AuthenticationError`: HTTP 401 (Unauthorized)
- `PermissionError`: HTTP 403 (Forbidden)
- `NotFoundError`: HTTP 404 (Not Found)
- `BadRequestError`: HTTP 400 (Bad Request)

### 6.2. Idempotency

**Transfers:**
- Use `external_id = invoice-{invoice_id}`
- Stark Bank guarantees: same external_id = same transfer
- Before creating: check if already exists in local database

**Webhooks:**
- May be sent multiple times
- Always process, but do not duplicate transfer
- Invoice status ensures idempotency

### 6.3. State Persistence

**Retry Records:**
```python
invoice.retry_count = 0
invoice.last_retry_at = None
invoice.error_message = None

# On each retry
invoice.retry_count += 1
invoice.last_retry_at = datetime.now()

# If definitively failed
invoice.status = "failed"
invoice.error_message = str(error)
```

**Complete Audit:**
- All events saved in `events_log`
- Allows manual replay if needed
- Facilitates debugging

### 6.4. Circuit Breaker (Future)

**Not implemented in v1.0, but prepared for:**
- Detecting consecutive failures
- Temporarily "opening the circuit"
- Automatically recovering when service comes back

## 7. Security

### 7.1. Authentication

**API Key (for query endpoints):**
```
Header: X-API-Key: <secret-key>
```
- Secure comparison (constant-time)
- Generated and stored as environment variable

**Digital Signature (for webhooks):**
```
Header: Digital-Signature: <ecdsa-signature>
```
- Validation using Stark Bank public key
- Prevents forged webhooks

### 7.2. Authorization

**Simple model:**
- API Key: full read access
- Webhooks: no authentication, but signature validation
- Health check: public

**Future:**
- Implement roles (admin, readonly)
- Rate limiting per API Key
- OAuth2 for external integrations

### 7.3. Data Protection

**Logs:**
- Do not log API Keys or passwords
- Partially mask CPF/CNPJ
- Never log complete webhook payloads (sensitive data)

**Database:**
- SQLite file with restricted permissions (0600)
- Encrypted backup (future)

**Environment Variables:**
```
STARK_BANK_PRIVATE_KEY=<base64-encoded-key>
STARK_BANK_PROJECT_ID=<project-id>
API_KEY=<random-secret-key>
DATABASE_URL=sqlite:///./stark_bank.db
```

### 7.4. HTTPS

**Production (Railway):**
- HTTPS mandatory
- Automatically managed certificate
- HTTP to HTTPS redirect

**Development:**
- HTTP allowed (localhost)

## 8. Observability

### 8.1. Logging

**Structure:**
- Format: JSON
- Levels: DEBUG, INFO, WARNING, ERROR
- Context: correlation_id, module, event

**Outputs:**
- Console (stdout) - for Railway
- File: `logs/app.log` - daily rotation

**Exemplo:**
```json
{
    "timestamp": "2026-02-14T10:30:00.123Z",
    "level": "INFO",
    "correlation_id": "req-abc123",
    "module": "invoices.service",
    "event": "invoice_created",
    "message": "Invoice created successfully",
    "data": {
        "invoice_id": "uuid-123",
        "stark_invoice_id": "5678",
        "amount": 500.00,
        "retry_count": 0
    }
}
```

### 8.2. Metrics (Future)

**Counters:**
- `invoices_created_total` - Total invoices created
- `invoices_failed_total` - Total failures
- `webhooks_invoice_received_total` - Total invoice webhooks received
- `webhooks_transfer_received_total` - Total transfer webhooks received
- `transfers_initiated_total` - Total transfers initiated
- `transfers_completed_total` - Total transfers completed
- `transfers_failed_total` - Total failed transfers

**Histograms:**
- `invoice_creation_duration_seconds` - Creation time
- `webhook_invoice_processing_duration_seconds` - Invoice webhook processing time
- `webhook_transfer_processing_duration_seconds` - Transfer webhook processing time
- `transfer_creation_duration_seconds` - Transfer time

**Gauges:**
- `active_invoices` - Invoices with status=created
- `processing_transfers` - Transfers with status=processing

### 8.3. Tracing (Future)

**OpenTelemetry:**
- Full trace of each operation
- Correlation between invoice → payment → transfer
- Visualization in Jaeger/Zipkin

### 8.4. Health Check

**Endpoint: GET /health**

```json
{
    "status": "healthy",
    "timestamp": "2026-02-14T10:30:00.123Z",
    "checks": {
        "database": "ok",
        "stark_api": "ok"
    },
    "version": "1.0.0",
    "uptime_seconds": 3600
}
```

## 9. Testing Strategy

### 9.1. Testing Pyramid

```
        ▲
       ╱ ╲
      ╱ E2E╲         (~10% - 5 tests)
     ╱─────╲
    ╱  Int  ╲        (~30% - 15 tests)
   ╱─────────╲
  ╱   Unit    ╲      (~60% - 30 tests)
 ╱─────────────╲
```

**Target:** 85%+ coverage

### 9.2. Unit Tests

**Scope:** Isolated functions and methods

**Tools:**
- pytest
- pytest-mock
- pytest-cov (coverage)

**Examples:**
- CPF/CNPJ validation
- net_amount calculation
- Webhook parsing
- Payload formatting
- Retry logic

**Mocking:**
- Stark Bank API (mock responses)
- Database (in-memory or mock)
- Faker (fixed seed for predictability)

### 9.3. Integration Tests

**Scope:** Integration between components

**Examples:**
- InvoiceService + InvoiceRepository + EventBus
- WebhookProcessor + InvoiceRepository
- TransferService + StarkAPI (mocked)
- Event flow: invoice.created → handlers

**Database:**
- SQLite in-memory (`:memory:`)
- Schema created in setup

### 9.4. E2E Tests

**Scope:** Full flow

**Tools:**
- FastAPI TestClient
- pytest-asyncio

**Examples:**
1. **Invoice Creation Flow:**
   - Scheduler starts
   - Invoices created
   - Saved to database
   - Events published

2. **Invoice Webhook Flow:**
   - POST /webhooks/invoice
   - Signature validated
   - Invoice updated
   - Transfer created

3. **Transfer Webhook Flow:**
   - POST /webhooks/transfer
   - Signature validated
   - Transfer updated
   - Status correctly processed

4. **Query Flow:**
   - GET /invoices with filters
   - GET /invoices/{id}
   - GET /transfers with filters
   - GET /transfers/{id}
   - Authentication via API Key

**Stark Bank API:**
- Mocked for E2E (does not hit sandbox)

### 9.5. Fixtures

```python
# conftest.py

@pytest.fixture
def db_connection():
    """In-memory SQLite database"""
    conn = sqlite3.connect(":memory:")
    # Run migrations
    conn.execute(CREATE_INVOICES_TABLE)
    conn.execute(CREATE_TRANSFERS_TABLE)
    conn.execute(CREATE_EVENTS_LOG_TABLE)
    yield conn
    conn.close()

@pytest.fixture
def mock_stark_api():
    """Mock Stark Bank API"""
    api = Mock(spec=StarkInvoiceAPI)
    api.create_invoice.return_value = InvoiceResponse(
        id="stark-123",
        status="created",
        ...
    )
    return api

@pytest.fixture
def event_bus():
    """Real EventBus instance"""
    return EventBus()
```

### 9.6. Test Coverage

**Per Module:**
- `invoices/` - 90%+ (critical logic)
- `webhooks/` - 90%+ (critical security)
- `transfers/` - 90%+ (money involved)
- `shared/` - 80%+
- `main.py` - 70%+ (integration)

**Run:**
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

## 10. Configuration Management

### 10.1. Environment Variables

```bash
# .env (development)

# Stark Bank
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=5656565656565656
STARK_BANK_PRIVATE_KEY=<base64-encoded-pem>

# API
API_KEY=dev-secret-key-12345
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./stark_bank.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24
```

### 10.2. Settings Module

```python
# src/config/settings.py

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    # Stark Bank
    stark_environment: str
    stark_project_id: str
    stark_private_key: str
    
    # API
    api_key: str
    api_host: str
    api_port: int
    
    # Database
    database_url: str
    
    # Logging
    log_level: str
    log_file: str
    
    # Scheduler
    scheduler_enabled: bool
    scheduler_interval_hours: int
    scheduler_duration_hours: int
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        return cls(
            stark_environment=os.getenv("STARK_BANK_ENVIRONMENT", "sandbox"),
            stark_project_id=os.getenv("STARK_BANK_PROJECT_ID"),
            stark_private_key=os.getenv("STARK_BANK_PRIVATE_KEY"),
            api_key=os.getenv("API_KEY"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./stark_bank.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/app.log"),
            scheduler_enabled=os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
            scheduler_interval_hours=int(os.getenv("SCHEDULER_INTERVAL_HOURS", "3")),
            scheduler_duration_hours=int(os.getenv("SCHEDULER_DURATION_HOURS", "24")),
        )

# Singleton
settings = Settings.from_env()
```

### 10.3. Constants

```python
# src/config/constants.py

# Stark Bank Transfer Destination
STARK_BANK_ACCOUNT = {
    "bank_code": "20018183",
    "branch_code": "0001",
    "account_number": "6341320293482496",
    "account_type": "payment",
    "tax_id": "20.018.183/0001-80",
    "name": "Stark Bank S.A."
}

# Invoice Configuration
INVOICE_MIN_AMOUNT = 10000  # R$ 100.00 (cents)
INVOICE_MAX_AMOUNT = 100000  # R$ 1,000.00 (cents)
INVOICE_DUE_DAYS = 3
INVOICE_MIN_BATCH_SIZE = 8
INVOICE_MAX_BATCH_SIZE = 12

# CPF/CNPJ
CPF_WEIGHT = 0.7  # 70% CPF, 30% CNPJ

# Retry Configuration
RETRY_MAX_ATTEMPTS = 5
RETRY_DELAYS = [0, 60, 120, 240, 480]  # seconds

# Status
INVOICE_STATUS_CREATED = "created"
INVOICE_STATUS_PAID = "paid"
INVOICE_STATUS_FAILED = "failed"
INVOICE_STATUS_CANCELED = "canceled"
INVOICE_STATUS_EXPIRED = "expired"

TRANSFER_STATUS_CREATED = "created"
TRANSFER_STATUS_PROCESSING = "processing"
TRANSFER_STATUS_SUCCESS = "success"
TRANSFER_STATUS_FAILED = "failed"

# Events
EVENT_INVOICE_CREATED = "invoice.created"
EVENT_INVOICE_PAID = "invoice.paid"
EVENT_TRANSFER_INITIATED = "transfer.initiated"
EVENT_TRANSFER_PROCESSING = "transfer.processing"
EVENT_TRANSFER_COMPLETED = "transfer.completed"
EVENT_TRANSFER_FAILED = "transfer.failed"
EVENT_OPERATION_FAILED = "operation.failed"
```

## 11. Deployment

### 11.1. Railway

**Platform:** Railway (free tier)

**Advantages:**
- Automatic deployment via Git
- Native HTTPS
- Centralized logs
- Environment variables
- Free domain

**Configuration:**

```toml
# Procfile (Railway)
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
scheduler: python src/scheduler.py
```

**Note:** Railway free tier allows 1 process. Solution:
- Option 1: Run scheduler in a thread inside the API
- Option 2: Use Railway Pro (2 processes)
- **Chosen: Option 1** (thread inside the API)

### 11.2. Environment Variables (Railway)

```
STARK_BANK_ENVIRONMENT=sandbox
STARK_BANK_PROJECT_ID=<from-stark-bank>
STARK_BANK_PRIVATE_KEY=<base64-encoded>
API_KEY=<generate-random-secure>
DATABASE_URL=sqlite:///./data/stark_bank.db
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
```

### 11.3. Database Persistence

**Problem:** Railway free tier does not persist files

**Solution:**
- Use mounted volume (Railway supports)
- Configure volume: `/app/data`
- Database path: `/app/data/stark_bank.db`

**Alternative (if volume unavailable):**
- Railway's free PostgreSQL
- Migrate from SQLite to PostgreSQL

### 11.4. Build & Startup

```yaml
# railway.toml (example)
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

**Build steps:**
1. Detect Python 3.14
2. Install dependencies (pyproject.toml)
3. Run migrations (startup script)
4. Start API + Scheduler

### 11.5. Monitoring

**Railway Dashboard:**
- CPU/Memory usage
- Request logs
- Error logs
- Uptime

**Custom Health Check:**
```bash
# Railway health check endpoint
curl https://stark-bank-challenge.railway.app/health
```

## 12. Development Workflow

### 12.1. Local Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd stark-bank-challenge

# 2. Install dependencies (example with rye)
rye sync

# 3. Setup environment
cp .env.example .env
# Edit .env with your Stark Bank credentials

# 4. Run migrations
python -m src.database.migrations

# 5. Run application
# Terminal 1 - API
uvicorn src.main:app --reload

# Terminal 2 - Scheduler (or use thread mode)
python src/scheduler.py
```

### 12.2. Linting & Formatting

```bash
# Ruff (linting + formatting)
ruff check src/
ruff format src/

# Type checking
mypy src/
```

### 12.3. Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/unit/invoices/

# Watch mode
pytest-watch
```

### 12.4. Git Workflow

**Branches:**
- `main` - Production (Railway auto-deploy)
- `develop` - Development
- `feature/<name>` - Features
- `fix/<name>` - Bugfixes

**Commits:**
- feat: New feature
- fix: Bug fix
- refactor: Refactoring
- docs: Documentation
- test: Tests
- chore: Maintenance

**Exemplo:**
```
feat(invoices): add invoice generation with retry logic

- Implement InvoiceGenerator class
- Add retry decorator with exponential backoff
- Add unit tests for retry behavior
```

## 13. Troubleshooting

### 13.1. Common Issues

#### Error: "Invalid Private Key"
**Cause:** Stark Bank private key is incorrect or malformatted

**Solution:**
```bash
# Check format (should be base64)
echo $STARK_BANK_PRIVATE_KEY | base64 -d

# Generate new key in Stark Bank dashboard
```

#### Error: "Database is Locked"
**Cause:** SQLite concurrency issue

**Solution:**
```python
# Enable WAL mode
conn.execute("PRAGMA journal_mode=WAL")

# Larger timeout
conn = sqlite3.connect("db.sqlite", timeout=30)
```

#### Error: "Webhook Signature Invalid"
**Cause:** Incorrect public key or modified payload

**Solution:**
```python
# Check public key
logger.debug(f"Public key: {public_key[:20]}...")

# Log raw payload
logger.debug(f"Raw payload: {request.body}")
```

#### Scheduler Not Running
**Cause:** Thread not started or silent exception

**Solution:**
```python
# Add logs
logger.info("Scheduler started")
logger.info(f"Next run: {scheduler.get_jobs()}")

# Check exceptions
try:
    scheduler.start()
except Exception as e:
    logger.error(f"Scheduler failed: {e}")
```

### 13.2. Debugging

**FastAPI Debug Mode:**
```bash
uvicorn src.main:app --reload --log-level debug
```

**Detailed Logs:**
```python
# Temporary debug logging
logger.setLevel(logging.DEBUG)
```

**Database Inspection:**
```bash
sqlite3 stark_bank.db

.tables
.schema invoices
SELECT * FROM invoices LIMIT 5;
SELECT * FROM events_log ORDER BY timestamp DESC LIMIT 10;
```

## 14. Future Improvements

### 14.1. Short Term (v1.1)

- [ ] PostgreSQL as database option
- [ ] Circuit breaker pattern
- [ ] Rate limiting on endpoints
- [ ] Metrics with Prometheus
- [ ] Monitoring dashboard
- [ ] Manual retry of failed operations

## 15. Conclusion

### 15.1. Architecture Highlights

1. **Modular:** Easy to understand, test, and evolve
2. **Resilient:** Automatic retry and failure handling
3. **Traceable:** Structured logging and complete auditing
4. **Secure:** Signature and API Key validation
5. **Testable:** Coverage > 85% with clear tests
6. **Documented:** Architecture and API fully documented

### 15.2. Alignment with Requirements

✅ Modular monolith  
✅ Event-driven architecture  
✅ Retry with exponential backoff  
✅ CPF/CNPJ validation  
✅ Transfer idempotency  
✅ Structured logging  
✅ Security (API Key + Signature)  
✅ Python 3.14 without Pydantic  
✅ FastAPI + SQLite  
✅ Tests > 85% coverage  

### 15.3. Trade-offs

**Choices:**
- SQLite (simplicity) vs PostgreSQL (performance)
- In-memory Event Bus (simplicity) vs RabbitMQ (scalability)
- Monolith (simple deployment) vs Microservices (scalability)
- Thread scheduler (single process) vs Process (Railway free tier)

**Justification:**
- MVP focused on demonstrating technical capabilities
- Trade-offs documented for future evolution
- Architecture allows gradual migration

### 15.4. Learnings

- Integration with banking APIs requires extreme resilience
- Event-driven facilitates auditing and debugging
- Idempotency is critical for financial operations
- Tests are an investment, not a cost
- Documentation is part of the product

---

**Status:** Living document, updated as implementation progresses
