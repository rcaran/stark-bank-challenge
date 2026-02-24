# API Documentation

## Overview

This document provides comprehensive documentation for the Stark Bank Challenge API endpoints. The API provides functionality for managing invoices, transfers, and processing webhooks from Stark Bank.

**Base URL (Local):** `http://localhost:8000`  
**Base URL (Production):** `https://<your-app>.railway.app`

**API Version:** 1.0.0

---

## Table of Contents

- [Authentication](#authentication)
- [Status Codes](#status-codes)
- [Error Responses](#error-responses)
- [Rate Limits](#rate-limits)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Invoices](#invoices)
  - [Transfers](#transfers)
  - [Events Log](#events-log)
  - [Webhooks](#webhooks)

---

## Authentication

### API Key Authentication

Most endpoints (except webhooks and health check) require API key authentication via the `X-API-Key` header.

**Header Format:**
```
X-API-Key: your-api-key-here
```

**How to get an API key:**
- For development: Set `API_KEY` in your `.env` file (e.g., `dev-key-12345`)
- For production: Generate a secure random key and configure it in Railway environment variables

**Example Request:**
```bash
curl -X GET http://localhost:8000/invoices \
  -H "X-API-Key: dev-key-12345"
```

### Webhook Authentication

Webhook endpoints use digital signature validation instead of API keys. Stark Bank sends a `Digital-Signature` header with each webhook request, which is validated using your configured private key.

**Header Format:**
```
Digital-Signature: base64-encoded-signature
```

---

## Status Codes

The API uses standard HTTP status codes:

| Code | Description |
|------|-------------|
| `200` | **OK** - Request succeeded |
| `201` | **Created** - Resource created successfully |
| `400` | **Bad Request** - Invalid request data or parameters |
| `401` | **Unauthorized** - Missing or invalid API key / signature |
| `404` | **Not Found** - Resource not found |
| `422` | **Unprocessable Entity** - Request validation failed |
| `500` | **Internal Server Error** - Server-side error occurred |
| `502` | **Bad Gateway** - Error communicating with Stark Bank API |

---

## Error Responses

All error responses follow a consistent format:

### Error Response Format

```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "details": []  // Optional: additional error details
}
```

### Common Error Examples

**401 Unauthorized - Invalid API Key:**
```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```

**400 Bad Request - Invalid Status Filter:**
```json
{
  "error": "Bad Request",
  "message": "Invalid status: invalid_status. Valid values: ['pending', 'created', 'paid', 'failed', 'canceled']"
}
```

**404 Not Found:**
```json
{
  "error": "Not Found",
  "message": "Invoice not found: 12345-67890"
}
```

**422 Validation Error:**
```json
{
  "error": "Validation Error",
  "message": "Invalid request data",
  "details": [
    {
      "loc": ["body", "amount"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

**502 Bad Gateway - Stark Bank API Error:**
```json
{
  "error": "External API Error",
  "message": "Error communicating with Stark Bank API"
}
```

---

## Rate Limits

**Current Status:** No rate limits are enforced in the current version.

**Future Implementation:** Rate limiting may be added in future versions to prevent abuse. Recommended limits:
- **Authenticated endpoints:** 100 requests per minute per API key
- **Webhook endpoints:** 1000 requests per minute (global)

When rate limits are implemented, you will receive a `429 Too Many Requests` response with retry information in headers.

---

## Endpoints

### Health Check

#### `GET /health`

Check the health status of the API and its dependencies.

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "timestamp": "2026-02-16T10:30:00.123456Z",
  "checks": {
    "database": "ok",
    "event_bus": "ok"
  },
  "version": "1.0.0",
  "uptime_seconds": 3600.45,
  "environment": "development"
}
```

**Response Fields:**
- `status`: Overall health status (`healthy` or `unhealthy`)
- `timestamp`: Current server timestamp (ISO 8601 format)
- `checks`: Status of individual components
- `version`: API version
- `uptime_seconds`: Time in seconds since application started
- `environment`: Current environment (development, production, test)

**Example:**
```bash
curl http://localhost:8000/health
```

---

## Invoices

### `POST /invoices`

Create a new invoice in Stark Bank and persist it locally.

**Authentication:** Required (API Key)

**Request Body:**

```json
{
  "amount": 10000,
  "customer_name": "João Silva",
  "customer_tax_id": "12345678900",
  "customer_email": "joao.silva@example.com",
  "due_date": "2026-02-20T23:59:59Z"
}
```

**Request Fields:**
- `amount` (integer, required): Amount in cents (e.g., 10000 = R$ 100.00)
- `customer_name` (string, required): Customer's full name (1-200 characters)
- `customer_tax_id` (string, required): Customer's CPF or CNPJ (11-18 characters)
- `customer_email` (string, required): Customer's email address (5-100 characters)
- `due_date` (string, optional): Invoice due date in ISO 8601 format

**Response:** `201 Created`

```json
{
  "id": "01JCXA2B3C4D5E6F7G8H9J0K1",
  "stark_invoice_id": "5123456789123456",
  "amount": 10000.0,
  "customer_name": "João Silva",
  "customer_tax_id": "12345678900",
  "customer_email": "joao.silva@example.com",
  "status": "created",
  "created_at": "2026-02-16T10:30:00.123456Z",
  "due_date": "2026-02-20T23:59:59Z",
  "paid_at": null,
  "fee": null,
  "net_amount": null,
  "retry_count": 0,
  "error_message": null
}
```

**Response Fields:**
- `id`: Internal invoice ID (ULID format)
- `stark_invoice_id`: Stark Bank invoice ID
- `amount`: Invoice amount (in cents as float)
- `customer_name`: Customer's name
- `customer_tax_id`: Customer's CPF/CNPJ
- `customer_email`: Customer's email
- `status`: Invoice status (see [Invoice Status Values](#invoice-status-values))
- `created_at`: Creation timestamp (ISO 8601)
- `due_date`: Due date (ISO 8601)
- `paid_at`: Payment timestamp (ISO 8601, null if not paid)
- `fee`: Stark Bank fee amount (null until paid)
- `net_amount`: Net amount after fees (null until paid)
- `retry_count`: Number of retry attempts
- `error_message`: Error message if creation failed

**Example:**
```bash
curl -X POST http://localhost:8000/invoices \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000,
    "customer_name": "João Silva",
    "customer_tax_id": "12345678900",
    "customer_email": "joao.silva@example.com"
  }'
```

**Possible Errors:**
- `400 Bad Request`: Invalid request data (e.g., negative amount, invalid email)
- `401 Unauthorized`: Missing or invalid API key
- `500 Internal Server Error`: Failed to create invoice
- `502 Bad Gateway`: Error communicating with Stark Bank API

---

### `GET /invoices`

List invoices with optional filtering and pagination.

**Authentication:** Required (API Key)

**Query Parameters:**
- `status` (string, optional): Filter by invoice status (see [Invoice Status Values](#invoice-status-values))
- `limit` (integer, optional): Maximum number of results (1-1000, default: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response:** `200 OK`

```json
{
  "invoices": [
    {
      "id": "01JCXA2B3C4D5E6F7G8H9J0K1",
      "stark_invoice_id": "5123456789123456",
      "amount": 10000.0,
      "customer_name": "João Silva",
      "customer_tax_id": "12345678900",
      "customer_email": "joao.silva@example.com",
      "status": "paid",
      "created_at": "2026-02-16T10:30:00.123456Z",
      "due_date": "2026-02-20T23:59:59Z",
      "paid_at": "2026-02-16T11:00:00.123456Z",
      "fee": 50.0,
      "net_amount": 9950.0,
      "retry_count": 0,
      "error_message": null
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Response Fields:**
- `invoices`: Array of invoice objects (see [POST /invoices](#post-invoices) for field descriptions)
- `total`: Total number of invoices matching the filter
- `limit`: Maximum results per page
- `offset`: Current pagination offset

**Example:**
```bash
# List all invoices
curl -X GET http://localhost:8000/invoices \
  -H "X-API-Key: dev-key-12345"

# List paid invoices with pagination
curl -X GET "http://localhost:8000/invoices?status=paid&limit=50&offset=0" \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `400 Bad Request`: Invalid status filter
- `401 Unauthorized`: Missing or invalid API key

---

### `GET /invoices/{invoice_id}`

Get a single invoice by its internal ID.

**Authentication:** Required (API Key)

**Path Parameters:**
- `invoice_id` (string, required): The internal invoice ID (ULID format)

**Response:** `200 OK`

```json
{
  "id": "01JCXA2B3C4D5E6F7G8H9J0K1",
  "stark_invoice_id": "5123456789123456",
  "amount": 10000.0,
  "customer_name": "João Silva",
  "customer_tax_id": "12345678900",
  "customer_email": "joao.silva@example.com",
  "status": "created",
  "created_at": "2026-02-16T10:30:00.123456Z",
  "due_date": "2026-02-20T23:59:59Z",
  "paid_at": null,
  "fee": null,
  "net_amount": null,
  "retry_count": 0,
  "error_message": null
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/invoices/01JCXA2B3C4D5E6F7G8H9J0K1 \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Invoice not found

---

### Invoice Status Values

| Status | Description |
|--------|-------------|
| `pending` | Invoice is pending creation in Stark Bank |
| `created` | Invoice created successfully, awaiting payment |
| `paid` | Invoice has been paid by customer |
| `failed` | Invoice creation or processing failed |
| `canceled` | Invoice was canceled |

---

## Transfers

### `GET /transfers`

List transfers with optional filtering and pagination.

**Authentication:** Required (API Key)

**Query Parameters:**
- `status` (string, optional): Filter by transfer status (see [Transfer Status Values](#transfer-status-values))
- `limit` (integer, optional): Maximum number of results (1-1000, default: 100)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response:** `200 OK`

```json
{
  "transfers": [
    {
      "id": "01JCXB2C3D4E5F6G7H8J9K0L1",
      "invoice_id": "01JCXA2B3C4D5E6F7G8H9J0K1",
      "stark_transfer_id": "6234567890123456",
      "external_id": "invoice-01JCXA2B3C4D5E6F7G8H9J0K1",
      "amount": 9950.0,
      "status": "success",
      "created_at": "2026-02-16T11:01:00.123456Z",
      "updated_at": "2026-02-16T11:05:00.123456Z",
      "completed_at": "2026-02-16T11:05:00.123456Z",
      "retry_count": 0,
      "error_message": null
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Response Fields:**
- `transfers`: Array of transfer objects
  - `id`: Internal transfer ID (ULID format)
  - `invoice_id`: Related invoice ID
  - `stark_transfer_id`: Stark Bank transfer ID
  - `external_id`: External reference ID for idempotency
  - `amount`: Transfer amount (net amount after fees)
  - `status`: Transfer status (see [Transfer Status Values](#transfer-status-values))
  - `created_at`: Creation timestamp (ISO 8601)
  - `updated_at`: Last update timestamp (ISO 8601)
  - `completed_at`: Completion timestamp (ISO 8601, null if not completed)
  - `retry_count`: Number of retry attempts
  - `error_message`: Error message if transfer failed
- `total`: Total number of transfers matching the filter
- `limit`: Maximum results per page
- `offset`: Current pagination offset

**Example:**
```bash
# List all transfers
curl -X GET http://localhost:8000/transfers \
  -H "X-API-Key: dev-key-12345"

# List successful transfers
curl -X GET "http://localhost:8000/transfers?status=success&limit=50" \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `400 Bad Request`: Invalid status filter
- `401 Unauthorized`: Missing or invalid API key

---

### `GET /transfers/{transfer_id}`

Get a single transfer by its internal ID.

**Authentication:** Required (API Key)

**Path Parameters:**
- `transfer_id` (string, required): The internal transfer ID (ULID format)

**Response:** `200 OK`

```json
{
  "id": "01JCXB2C3D4E5F6G7H8J9K0L1",
  "invoice_id": "01JCXA2B3C4D5E6F7G8H9J0K1",
  "stark_transfer_id": "6234567890123456",
  "external_id": "invoice-01JCXA2B3C4D5E6F7G8H9J0K1",
  "amount": 9950.0,
  "status": "success",
  "created_at": "2026-02-16T11:01:00.123456Z",
  "updated_at": "2026-02-16T11:05:00.123456Z",
  "completed_at": "2026-02-16T11:05:00.123456Z",
  "retry_count": 0,
  "error_message": null
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/transfers/01JCXB2C3D4E5F6G7H8J9K0L1 \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Transfer not found

---

### `GET /transfers/invoice/{invoice_id}`

Get a transfer by its associated invoice ID.

**Authentication:** Required (API Key)

**Path Parameters:**
- `invoice_id` (string, required): The invoice ID (ULID format)

**Response:** `200 OK`

```json
{
  "id": "01JCXB2C3D4E5F6G7H8J9K0L1",
  "invoice_id": "01JCXA2B3C4D5E6F7G8H9J0K1",
  "stark_transfer_id": "6234567890123456",
  "external_id": "invoice-01JCXA2B3C4D5E6F7G8H9J0K1",
  "amount": 9950.0,
  "status": "success",
  "created_at": "2026-02-16T11:01:00.123456Z",
  "updated_at": "2026-02-16T11:05:00.123456Z",
  "completed_at": "2026-02-16T11:05:00.123456Z",
  "retry_count": 0,
  "error_message": null
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/transfers/invoice/01JCXA2B3C4D5E6F7G8H9J0K1 \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Transfer not found for the specified invoice

---

### Transfer Status Values

| Status | Description |
|--------|-------------|
| `pending` | Transfer is pending creation in Stark Bank |
| `created` | Transfer created in Stark Bank, awaiting processing |
| `processing` | Transfer is being processed by Stark Bank |
| `success` | Transfer completed successfully |
| `failed` | Transfer failed (error message in `error_message` field) |

---

## Events Log

### `GET /events-log`

List all internal events recorded in the audit log, with optional filters and pagination.

**Authentication:** Required (API Key)

**Query Parameters:**
- `event_type` (string, optional): Filter by event type (see [Event Type Values](#event-type-values))
- `start_date` (string, optional): Include only events on or after this datetime (ISO 8601 UTC)
- `end_date` (string, optional): Include only events on or before this datetime (ISO 8601 UTC)
- `limit` (integer, optional): Maximum number of results (1-500, default: 50)
- `offset` (integer, optional): Pagination offset (default: 0)

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "event_id": "b3d2c1a0-1234-5678-abcd-ef0123456789",
      "event_type": "invoice.paid",
      "payload": {
        "invoice_id": "01JCXA2B3C4D5E6F7G8H9J0K1",
        "amount": 10000,
        "fee": 50
      },
      "metadata": null,
      "timestamp": "2026-02-16T11:00:00.123456",
      "processed": true
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Response Fields:**
- `items`: Array of event log objects
  - `id`: Auto-incremented row ID
  - `event_id`: Unique UUID for the event
  - `event_type`: Event type string (see [Event Type Values](#event-type-values))
  - `payload`: Event payload as a JSON object
  - `metadata`: Optional metadata as a JSON object (may be null)
  - `timestamp`: Event timestamp (ISO 8601, UTC)
  - `processed`: Whether the event was successfully processed by all handlers
- `total`: Total number of events matching the filter
- `limit`: Maximum results per page
- `offset`: Current pagination offset

**Example:**
```bash
# List all events
curl -X GET http://localhost:8000/events-log \
  -H "X-API-Key: dev-key-12345"

# Filter by event type
curl -X GET "http://localhost:8000/events-log?event_type=invoice.paid&limit=20" \
  -H "X-API-Key: dev-key-12345"

# Filter by date range
curl -X GET "http://localhost:8000/events-log?start_date=2026-02-16T00:00:00Z&end_date=2026-02-16T23:59:59Z" \
  -H "X-API-Key: dev-key-12345"
```

**Possible Errors:**
- `401 Unauthorized`: Missing or invalid API key
- `422 Unprocessable Entity`: Invalid query parameter format

---

### Event Type Values

| Event Type | Description |
|------------|-------------|
| `invoice.created` | Invoice successfully created in Stark Bank |
| `invoice.creation_failed` | Invoice creation failed |
| `invoice.paid` | Invoice payment confirmed via webhook |
| `transfer.created` | Transfer successfully created in Stark Bank |
| `transfer.processing` | Stark Bank is processing the transfer |
| `transfer.completed` | Transfer completed successfully |
| `transfer.failed` | Transfer failed |
| `webhook.received` | Webhook received from Stark Bank |
| `webhook.validation_failed` | Webhook signature validation failed |
| `scheduler.tick` | Scheduler cycle executed |
| `system.error` | Unhandled system error |

---

## Webhooks

### `POST /webhooks/invoice`

Receive and process invoice payment webhooks from Stark Bank.

**Authentication:** Digital Signature validation (not API Key)

**Headers:**
- `Digital-Signature` (required): Base64-encoded signature from Stark Bank
- `Content-Type`: `application/json`

**Request Body:**

Stark Bank invoice webhook payload (structure defined by Stark Bank):

```json
{
  "event": {
    "log": {
      "id": "5123456789123456",
      "created": "2026-02-16T11:00:00.123456+00:00",
      "type": "credited",
      "invoice": {
        "id": "5123456789123456",
        "amount": 10000,
        "fee": 50,
        "status": "paid",
        "taxId": "12345678900",
        "tags": ["internal-id:01JCXA2B3C4D5E6F7G8H9J0K1"]
      }
    }
  }
}
```

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

**Important Notes:**
- This endpoint **always returns 200 OK** for valid signatures, even if internal processing fails
- This prevents Stark Bank from retrying webhooks unnecessarily
- If signature validation fails, returns `401 Unauthorized`
- The webhook updates the invoice status to `paid` and triggers automatic transfer creation

**Example:**
```bash
curl -X POST http://localhost:8000/webhooks/invoice \
  -H "Digital-Signature: base64-encoded-signature" \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "log": {
        "id": "5123456789123456",
        "created": "2026-02-16T11:00:00.123456+00:00",
        "type": "credited",
        "invoice": {
          "id": "5123456789123456",
          "amount": 10000,
          "fee": 50,
          "status": "paid",
          "taxId": "12345678900",
          "tags": ["internal-id:01JCXA2B3C4D5E6F7G8H9J0K1"]
        }
      }
    }
  }'
```

**Possible Errors:**
- `401 Unauthorized`: Invalid Digital-Signature

---

### `POST /webhooks/transfer`

Receive and process transfer status webhooks from Stark Bank.

**Authentication:** Digital Signature validation (not API Key)

**Headers:**
- `Digital-Signature` (required): Base64-encoded signature from Stark Bank
- `Content-Type`: `application/json`

**Request Body:**

Stark Bank transfer webhook payload (structure defined by Stark Bank):

```json
{
  "event": {
    "log": {
      "id": "6234567890123456",
      "created": "2026-02-16T11:05:00.123456+00:00",
      "type": "success",
      "transfer": {
        "id": "6234567890123456",
        "amount": 9950,
        "status": "success",
        "externalId": "invoice-01JCXA2B3C4D5E6F7G8H9J0K1"
      }
    }
  }
}
```

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

**Important Notes:**
- This endpoint **always returns 200 OK** for valid signatures, even if internal processing fails
- This prevents Stark Bank from retrying webhooks unnecessarily
- If signature validation fails, returns `401 Unauthorized`
- The webhook updates the transfer status based on the event type

**Example:**
```bash
curl -X POST http://localhost:8000/webhooks/transfer \
  -H "Digital-Signature: base64-encoded-signature" \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "log": {
        "id": "6234567890123456",
        "created": "2026-02-16T11:05:00.123456+00:00",
        "type": "success",
        "transfer": {
          "id": "6234567890123456",
          "amount": 9950,
          "status": "success",
          "externalId": "invoice-01JCXA2B3C4D5E6F7G8H9J0K1"
        }
      }
    }
  }'
```

**Possible Errors:**
- `401 Unauthorized`: Invalid Digital-Signature

---

### `GET /webhooks/health`

Simple health check endpoint for the webhook service.

**Authentication:** Not required

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "webhooks"
}
```

**Example:**
```bash
curl http://localhost:8000/webhooks/health
```

---

## Additional Resources

### Interactive API Documentation

The API provides interactive documentation using Swagger UI and ReDoc:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Spec:** `http://localhost:8000/openapi.json`

### Testing

For testing with Postman or similar tools, you can import the OpenAPI specification from `/openapi.json`.

### Support

For issues or questions, please refer to:
- GitHub Repository: [Link to your repository]
- Documentation: [docs/ folder in repository]
- Stark Bank API Docs: https://starkbank.com/docs/api

---

## Changelog

### Version 1.1.0 (2026-02-24)
- Added `GET /events-log` endpoint for querying the internal event audit log
- Added event type filter, date range filter, and pagination support to events log

### Version 1.0.0 (2026-02-16)
- Initial API release
- Invoice management endpoints
- Transfer management endpoints
- Webhook processing endpoints
- Health check endpoint
