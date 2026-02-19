# Stark Bank Challenge - Business Requirements

**Version:** 1.0  
**Date:** February 2026  
**Author:** Stark Bank Selection Process Candidate

## 1. Context

This document describes the business requirements for the Stark Bank technical challenge. The goal is to develop an application that automates invoice issuance, processes payments via webhooks, and performs automatic transfers of received amounts.

### 1.1. Environment

- Platform: Stark Bank Sandbox
- Python 3.14
- FastAPI

## 2. Objectives

### 2.1. Main Objective
Develop an automated integration with Stark Bank services that demonstrates:

- Ability to integrate with external APIs
- Event-driven architecture
- Robust error handling and retry
- Security and logging best practices
- Modular monolith

### 2.2. Specific Objectives

- Automate periodic invoice issuance
- Process payment notifications via webhooks
- Execute automatic transfers of received amounts
- Ensure complete traceability of operations
- Implement resilience and fault tolerance mechanisms

## 3. Functional Requirements

### RF001: Automatic Invoice Generation
**Description:** The system must automatically issue invoices every 3 hours for 24 hours.

**Acceptance Criteria:**

- Issue between 8 and 12 invoices per cycle (random quantity)
- Generate random payer data (name, CPF/CNPJ, email)
- Validate CPF/CNPJ before creating an invoice
- Execute 8 complete cycles (24 hours / 3 hours)
- Persist all created invoices in the database
- Publish an InvoiceCreated event for each generated invoice
- Continue execution even if some invoices fail

**Business Rules:**

- Invoice amount: between R$ 100.00 and R$ 1,000.00 (random)
- Due date: 3 days after creation
- CPF must have 11 digits and be valid
- CNPJ must have 14 digits and be valid

### RF002: Payment Webhook Processing
**Description:** The system must receive and process payment notifications sent by Stark Bank.

**Acceptance Criteria:**

- Public endpoint `POST /webhooks/invoice`
- Validate webhook digital signature (security)
- Extract payment data (invoice_id, amount, fee)
- Update invoice status in the database
- Calculate net amount (amount - fee)
- Publish InvoicePaid event after processing
- Return HTTP 200 on success
- Return HTTP 401 if signature is invalid
- Return HTTP 400 if payload is malformed

**Business Rules:**

- Only invoices with "paid" status should trigger a transfer
- Net amount = gross amount - Stark Bank fees
- Webhook must be idempotent (process duplicates without error)

### RF003: Automatic Transfers
**Description:** The system must automatically transfer received amounts (net) to the Stark Bank account.

**Acceptance Criteria:**

- Transfer net amount (amount - fee)
- Use the specified destination account details
- Ensure idempotency via external_id
- Persist transfer in the database
- Publish TransferCompleted event after success
- Do not duplicate transfers for the same invoice

**Destination Account Details:**

- Bank: 20018183
- Branch: 0001
- Account: 6341320293482496
- Name: Stark Bank S.A.
- CNPJ: 20.018.183/0001-80
- Type: payment

**Business Rules:**

- `external_id = invoice-{invoice_id}` (ensures idempotency)
- Transfer must only be created after payment confirmation
- In case of failure, the system must perform automatic retry

### RF004: Transfer Webhook Processing
**Description:** The system must receive and process transfer status notifications sent by Stark Bank.

**Acceptance Criteria:**

- Public endpoint `POST /webhooks/transfer`
- Validate webhook digital signature (security)
- Extract transfer data (transfer_id, status, amount)
- Update transfer status in the database
- Publish TransferStatusUpdated event after processing
- Return HTTP 200 on success
- Return HTTP 401 if signature is invalid
- Return HTTP 400 if payload is malformed

**Business Rules:**

- Process status updates: processing, success, failed
- Status "success" indicates transfer completed successfully
- Status "failed" indicates definitive failure (requires manual review)
- Webhook must be idempotent (process duplicates without error)
- Record all updates in audit log

### RF005: Invoice Query
**Description:** The system must expose endpoints for querying created invoices.

**Acceptance Criteria:**

- `GET /invoices` - lists all invoices
- `GET /invoices/{id}` - queries a specific invoice
- Support filtering by status (created, paid, failed)
- Support pagination (limit, offset)
- Return complete invoice data
- Requires API Key authentication

### RF006: Transfer Query
**Description:** The system must expose endpoints for querying performed transfers.

**Acceptance Criteria:**

- `GET /transfers` - lists all transfers
- `GET /transfers/{id}` - queries a specific transfer
- Support filtering by status (processing, success, failed)
- Support pagination (limit, offset)
- Return complete transfer data
- Requires API Key authentication

### RF007: Health Check
**Description:** The system must expose an endpoint for checking application health.

**Acceptance Criteria:**

- `GET /health` - checks application status
- Verify database connectivity
- Return check timestamp
- Public endpoint (no authentication)

## 4. Non-Functional Requirements

### NFR001: Reliability and Resilience
**Description:** The system must be resilient to temporary failures of the Stark Bank API.

**Acceptance Criteria:**

- Implement automatic retry in all integrations
- Retry strategy: 5 attempts with exponential backoff

  - Attempt 1: immediate
  - Attempt 2: after 1 minute (60s)
  - Attempt 3: after 2 minutes (120s)
  - Attempt 4: after 4 minutes (240s)
  - Attempt 5: after 8 minutes (480s)

- Retry only on retriable errors (timeout, 5xx, 429)
- Do NOT retry on validation errors (4xx except 429)
- Log all attempts
- Persist retry counters in the database

**Retriable Errors:**

- Connection timeout
- 5xx errors (server error)
- 429 error (rate limit)
- Network errors (ConnectionError)

**Non-Retriable Errors:**

- 400, 401, 403, 404, 422 errors (client error)
- Data validation errors
- Authentication errors

### NFR002: Traceability and Audit
**Description:** The system must maintain a complete record of all operations.

**Acceptance Criteria:**

- Structured logging (JSON format) for all operations
- Persist all events in the `events_log` table
- Logs must include: timestamp, event_type, payload, metadata
- Appropriate log levels (INFO, WARNING, ERROR)
- Do not expose sensitive data in logs (keys, passwords)
- Correlate operations via unique event_id
- Store logs in file and console

**Audited Events:**

- invoice.created - Invoice created
- invoice.paid - Invoice paid (via webhook)
- transfer.initiated - Transfer initiated
- transfer.processing - Transfer in processing (via webhook)
- transfer.completed - Transfer completed (via webhook)
- transfer.failed - Transfer failed (via webhook)
- operation.failed - Operation failed after all retries
- error.occurred - Error captured

### NFR003: Security
**Description:** The system must implement appropriate security controls.

**Acceptance Criteria:**

- Validate digital signature of all webhooks
- API Key authentication for sensitive endpoints
- Credentials in environment variables (never in code)
- Secure API Key comparison (protection against timing attacks)
- HTTPS mandatory in production
- Do not expose stack traces in error responses
- Rate limiting on public endpoints (future)

**Public Endpoints:**

- `GET /health` - No authentication
- `POST /webhooks/invoice` - Validated by digital signature
- `POST /webhooks/transfer` - Validated by digital signature

**Protected Endpoints (require API Key via X-API-Key header):**

- `GET /invoices`
- `GET /invoices/{id}`
- `GET /transfers`
- `GET /transfers/{id}`
- `GET /docs` (Swagger)
- `GET /openapi.json`

### NFR004: Performance
**Acceptance Criteria:**

- Create invoice: < 5 seconds (without retry)
- Process webhook: < 2 seconds
- Create transfer: < 5 seconds (without retry)
- Query invoices/transfers: < 1 second
- Scheduler must execute punctually every 3 hours

### NFR005: Scalability

- Support creation of 96 invoices in 24 hours (8 cycles × 12 max)
- Process webhooks concurrently (if multiple arrive)
- Database must support data growth
- Modular architecture allows future extraction of microservices

### NFR006: Maintainability

- Modular architecture (modular monolith)
- Decoupling via Event Bus
- Testable code (coverage > 85%)
- Complete documentation (business + architecture + API)
- Python 3.14 with updated libraries
- Type hints throughout the code
- Automated linting and formatting (Ruff)

## 5. Business Rules

### BR001: Random Data Generation

- Use Faker library to generate realistic names
- 70% of invoices with CPF (individual)
- 30% of invoices with CNPJ (company)
- Random amounts between R$ 100.00 and R$ 1,000.00
- Random quantity between 8 and 12 invoices per cycle

### BR002: Document Validation

- CPF: 11 numeric digits, validate check digits
- CNPJ: 14 numeric digits, validate check digits
- Reject CPF/CNPJ with all identical digits (e.g. 111.111.111-11)

### BR003: Net Amount Calculation

- net_amount = gross_amount - fees
- Fees are provided by Stark Bank in the webhook
- Net amount can never be negative

### BR004: Transfer Idempotency

- Use `external_id = invoice-{invoice_id}` in all transfers
- If a transfer with the same external_id already exists, return the existing one
- Do not create duplicate transfers for the same invoice

### BR005: Invoice States

Valid states:

- `created` - Invoice created, awaiting payment
- `paid` - Invoice paid, confirmed via webhook
- `canceled` - Invoice canceled
- `expired` - Invoice expired

### BR006: Transfer States

Valid states:

- `created` - Transfer created locally
- `processing` - Transfer being processed at Stark Bank
- `success` - Transfer completed successfully
- `failed` - Transfer failed definitively

## 6. Constraints

**Technical**

- Language: Python 3.14 mandatory
- API: Stark Bank SDK v2.14.0+
- Database: SQLite (persistent)
- Deploy: Railway free tier

**Temporal**

- Execution: 24 continuous hours
- Generation interval: 3 hours (fixed)

**Functional**

- Environment: Stark Bank Sandbox only
- Destination account: Fixed, as specified
- Scheduler: Separate process from the API

## 7. Diagrams

### 7.1. General Process Flow

```mermaid
graph TB
    Start([Start - 00:00]) --> Scheduler[Scheduler Starts]
    Scheduler --> Cycle{Run<br/>Cycle?}
    
    Cycle -->|Every 3h| Generate[Generate 8-12 Invoices]
    Generate --> CreateInv[Create Invoice via<br/>Stark Bank API]
    CreateInv --> SaveInv[Save to Database]
    SaveInv --> EventInv[Publish Event<br/>InvoiceCreated]
    EventInv --> MoreInv{More<br/>Invoices?}
    
    MoreInv -->|Yes| CreateInv
    MoreInv -->|No| Wait[Wait 3 hours]
    Wait --> Check{24h<br/>complete?}
    
    Check -->|No| Cycle
    Check -->|Yes| End([End])
    
    %% Parallel flow - Invoice Webhooks
    StarkBank[(Stark Bank<br/>Sandbox)] -.Simulates<br/>Payment.-> Webhook[POST /webhooks/invoice]
    Webhook --> ValidateSig{Signature<br/>Valid?}
    ValidateSig -->|No| Reject[HTTP 401]
    ValidateSig -->|Yes| ProcessWH[Process Webhook]
    ProcessWH --> UpdateInv[Update Invoice<br/>status=paid]
    UpdateInv --> EventPaid[Publish Event<br/>InvoicePaid]
    EventPaid --> ListenTransfer[Handler Listens<br/>InvoicePaid]
    ListenTransfer --> CalcNet[Calculate Net Amount<br/>amount - fee]
    CalcNet --> CreateTransfer[Create Transfer via<br/>Stark Bank API]
    CreateTransfer --> SaveTransfer[Save to Database<br/>status=created]
    SaveTransfer --> EventTransfer[Publish Event<br/>TransferInitiated]
    EventTransfer --> Done[HTTP 200]
    
    %% Parallel flow - Transfer Webhooks
    StarkBank -.Status<br/>Update.-> WebhookTrf[POST /webhooks/transfer]
    WebhookTrf --> ValidateSigTrf{Signature<br/>Valid?}
    ValidateSigTrf -->|No| RejectTrf[HTTP 401]
    ValidateSigTrf -->|Yes| ProcessWHTrf[Process Webhook]
    ProcessWHTrf --> UpdateTrf[Update Transfer<br/>status in Database]
    UpdateTrf --> EventTrfStatus[Publish Event<br/>TransferStatus]
    EventTrfStatus --> DoneTrf[HTTP 200]
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style StarkBank fill:#87CEEB
    style Webhook fill:#FFD700
    style WebhookTrf fill:#FFD700
    style Reject fill:#FF6B6B
    style RejectTrf fill:#FF6B6B
    style Done fill:#90EE90
    style DoneTrf fill:#90EE90
```

### 7.2. Sequence Diagram - Complete Flow

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant IG as Invoice Generator
    participant SB as Stark Bank API
    participant DB as Database
    participant EB as Event Bus
    participant WH as Webhook Endpoint
    participant TH as Transfer Handler
    
    Note over S: Every 3 hours (8x in 24h)
    
    S->>IG: Execute generation
    loop 8 to 12 times
        IG->>IG: Generate random data (Faker)
        IG->>IG: Validate CPF/CNPJ
        IG->>SB: POST /invoices (with retry)
        alt Success
            SB-->>IG: Invoice created (ID, status)
            IG->>DB: Save invoice
            IG->>EB: Publish InvoiceCreated
        else Failure after retries
            SB-->>IG: Error
            IG->>DB: Save with status=failed
            IG->>EB: Publish OperationFailed
        end
    end
    
    Note over SB: Sandbox simulates payment
    
    SB->>WH: POST /webhooks/invoice + Digital-Signature
    WH->>WH: Validate digital signature
    alt Invalid signature
        WH-->>SB: HTTP 401 Unauthorized
    else Valid signature
        WH->>WH: Parse payload
        WH->>DB: Update invoice (status=paid, fee, net_amount)
        WH->>EB: Publish InvoicePaid
        WH-->>SB: HTTP 200 OK
        
        EB->>TH: Notify InvoicePaid
        TH->>TH: Calculate net amount
        TH->>DB: Check existing transfer
        alt Transfer already exists
            TH->>TH: Idempotency - ignore
        else Transfer does not exist
            TH->>SB: POST /transfers (with retry, external_id)
            alt Success
                SB-->>TH: Transfer created
                TH->>DB: Save transfer (status=created)
                TH->>EB: Publish TransferInitiated
            else Failure after retries
                SB-->>TH: Error
                TH->>DB: Save transfer (status=failed)
                TH->>EB: Publish OperationFailed
            end
        end
    end
    
    Note over SB: Sandbox processes transfer
    
    SB->>WH: POST /webhooks/transfer + Digital-Signature
    WH->>WH: Validate digital signature
    alt Invalid signature
        WH-->>SB: HTTP 401 Unauthorized
    else Valid signature
        WH->>WH: Parse payload
        WH->>DB: Update transfer (status=processing/success/failed)
        WH->>EB: Publish TransferStatusUpdated
        WH-->>SB: HTTP 200 OK
    end
    
    Note over DB: All operations audited in events_log
```

### 7.3. State Diagram - Invoice

```mermaid
stateDiagram-v2
    [*] --> Created: Invoice created via API
    
    Created --> Paid: Webhook received\n(status=paid)
    Created --> Canceled: Canceled manually\n(not implemented)
    Created --> Expired: Due date expired\n(not implemented)
    Created --> Failed: Creation error\n(after retries)
    
    Paid --> [*]: Transfer created
    Canceled --> [*]
    Expired --> [*]
    Failed --> [*]
    
    note right of Created
        Initial state
        Awaiting payment
    end note
    
    note right of Paid
        Payment confirmed
        Triggers transfer creation
    end note
```

### 7.4. State Diagram - Transfer

```mermaid
stateDiagram-v2
    [*] --> Created: Transfer created via API\nlocally
    
    Created --> Processing: Webhook received\nstatus=processing
    Processing --> Success: Webhook received\nstatus=success
    Processing --> Failed: Webhook received\nstatus=failed
    
    Created --> Failed: Creation error\n(after retries)
    
    Failed --> Created: Manual retry\n(not implemented)
    
    Success --> [*]
    Failed --> [*]
    
    note right of Created
        Transfer created locally
        Sent to Stark Bank
    end note
    
    note right of Processing
        Being processed
        Awaiting confirmation
    end note
    
    note right of Success
        Transfer confirmed
        Amount transferred successfully
    end note
    
    note right of Failed
        Permanent failure
        Requires manual intervention
    end note
```

### 7.5. Module Architecture

```mermaid
graph TB
    subgraph "Processes"
        API[Web API\nFastAPI]
        SCHED[Scheduler\nAPScheduler]
    end
    
    subgraph "Shared - Shared Components"
        EB[Event Bus\nPub/Sub]
        DB[(SQLite\nDatabase)]
        LOG[Logger\nStructured]
        SEC[Security\nAPI Key Validator]
    end
    
    subgraph "Domain Modules"
        INV[Invoices Module\n- Generator\n- Service\n- Events]
        WH[Webhooks Module\n- Receiver\n- Validator\n- Events]
        TRF[Transfers Module\n- Service\n- Handler\n- Events]
        SI[Stark Integration\n- Invoice API\n- Transfer API\n- Retry Logic]
    end
    
    subgraph "External APIs"
        SB[Stark Bank API\nSandbox]
    end
    
    SCHED --> INV
    API --> WH
    API --> SEC
    
    INV --> EB
    INV --> DB
    INV --> SI
    
    WH --> EB
    WH --> DB
    WH --> SEC
    
    TRF --> EB
    TRF --> DB
    TRF --> SI
    
    SI --> SB
    
    EB -.notifies.-> INV
    EB -.notifies.-> TRF
    EB --> DB
    
    INV --> LOG
    WH --> LOG
    TRF --> LOG
    SI --> LOG
    
    style API fill:#FFD700
    style SCHED fill:#87CEEB
    style EB fill:#90EE90
    style DB fill:#DDA0DD
    style SB fill:#FF6B6B
```

### 7.6. Event Flow (Event Bus)

```mermaid
graph LR
    subgraph "Publishers"
        IG[Invoice Generator]
        WH[Webhook Handler]
        TS[Transfer Service]
    end
    
    subgraph "Event Bus"
        EB{Event Bus\nPub/Sub}
    end
    
    subgraph "Subscribers"
        L[Logger]
        A[Auditor]
        TH[Transfer Handler]
        M[Metrics Collector]
    end
    
    subgraph "Persistence"
        DB[(events_log)]
    end
    
    IG -->|InvoiceCreated| EB
    WH -->|InvoicePaid| EB
    WH -->|TransferStatusUpdated| EB
    TS -->|TransferInitiated| EB
    TS -->|TransferCompleted| EB
    TS -->|TransferFailed| EB
    TS -->|OperationFailed| EB
    
    EB -->|all events| L
    EB -->|all events| A
    EB -->|InvoicePaid| TH
    EB -->|all events| M
    
    A --> DB
    
    style EB fill:#90EE90
    style DB fill:#DDA0DD
```

### 7.7. Retry Strategy

```mermaid
graph TB
    Start([API Operation]) --> Try1[Attempt 1\nImmediate]
    Try1 --> Check1{Success?}
    Check1 -->|Yes| Success([Return Result])
    Check1 -->|Retriable Error| Wait1[Wait 1 min]
    Check1 -->|Non-Retriable Error| Fail([Throw Exception])
    
    Wait1 --> Try2[Attempt 2]
    Try2 --> Check2{Success?}
    Check2 -->|Yes| Success
    Check2 -->|Retriable Error| Wait2[Wait 2 min]
    Check2 -->|Non-Retriable Error| Fail
    
    Wait2 --> Try3[Attempt 3]
    Try3 --> Check3{Success?}
    Check3 -->|Yes| Success
    Check3 -->|Retriable Error| Wait3[Wait 4 min]
    Check3 -->|Non-Retriable Error| Fail
    
    Wait3 --> Try4[Attempt 4]
    Try4 --> Check4{Success?}
    Check4 -->|Yes| Success
    Check4 -->|Retriable Error| Wait4[Wait 8 min]
    Check4 -->|Non-Retriable Error| Fail
    
    Wait4 --> Try5[Attempt 5\nLast]
    Try5 --> Check5{Success?}
    Check5 -->|Yes| Success
    Check5 -->|Any Error| Fail
    
    style Success fill:#90EE90
    style Fail fill:#FF6B6B
    style Try1 fill:#FFD700
    style Try2 fill:#FFD700
    style Try3 fill:#FFD700
    style Try4 fill:#FFD700
    style Try5 fill:#FFA500
```

**Retriable Errors:**

- Timeout (ConnectionTimeout, ReadTimeout)
- HTTP 5xx (500, 502, 503, 504)
- HTTP 429 (Rate Limit)
- ConnectionError

**Non-Retriable Errors:**

- HTTP 4xx (400, 401, 403, 404, 422)
- ValidationError
- AuthenticationError

## 8. Data Model

### 8.1. Database Structure

```mermaid
erDiagram
    INVOICES ||--o{ TRANSFERS : "generates"
    INVOICES ||--o{ EVENTS_LOG : "logs"
    TRANSFERS ||--o{ EVENTS_LOG : "logs"
    
    INVOICES {
        uuid id PK
        string stark_invoice_id UK
        decimal amount
        string customer_name
        string customer_tax_id
        string customer_email
        enum status
        timestamp created_at
        timestamp paid_at
        decimal fee
        decimal net_amount
        int retry_count
        timestamp last_retry_at
        text error_message
    }
    
    TRANSFERS {
        uuid id PK
        uuid invoice_id FK
        string stark_transfer_id UK
        string external_id UK
        decimal amount
        enum status
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
        int retry_count
        timestamp last_retry_at
        text error_message
    }
    
    EVENTS_LOG {
        int id PK
        uuid event_id UK
        string event_type
        json payload
        json metadata
        timestamp timestamp
        boolean processed
    }
```

## 9. Project Acceptance Criteria

### 9.1. Functionality

- System generates 8-12 invoices every 3 hours
- System runs for 24 hours (8 complete cycles)
- Invoice webhook processes payments correctly
- Transfer webhook processes status updates correctly
- Transfers are created automatically
- Net amount calculated correctly (amount - fee)
- Funds transferred to specified Stark Bank account
- Transfer statuses updated via webhook
- Query endpoints work correctly

### 9.2. Quality

- Test coverage > 85%
- All behaviors tested
- Retry works as specified
- Transfer idempotency validated
- CPF/CNPJ validation implemented
- API Key protects endpoints correctly

### 9.3. Documentation

- Complete architecture document
- API specification document
- README with execution instructions
- Diagrams included in documentation
- Code commented where necessary

### 9.4. Delivery

- Code in public GitHub repository
- Application deployed on Railway
- Running for 24 hours
- Logs and execution evidence
- All dependencies documented

## 10. Glossary

- Invoice: Bill/charge generated for a customer
- Transfer: Bank transfer to the destination account
- Webhook: HTTP notification sent by an external event
- Event Bus: Pub/sub messaging system for decoupling
- Retry: Automatic reattempt after failure
- Exponential Backoff: Strategy of increasing wait times between retries
- Idempotency: Property of an operation producing the same result if executed multiple times
- External ID: External identifier to ensure idempotency
- API Key: Authentication key for API access
- CPF: Individual Taxpayer Registry (11 digits)
- CNPJ: National Corporate Taxpayer Registry (14 digits)
- Sandbox: Testing environment that simulates production
- DTO: Data Transfer Object - object used for transferring data
- Net Amount: Gross amount minus fees

## 11. References

- Stark Bank API Documentation ()
- Stark Bank Python SDK
- FastAPI Documentation
- Python 3.14 Release Notes
- Railway Documentation
