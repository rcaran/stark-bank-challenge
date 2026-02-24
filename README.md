# Stark Bank Challenge

Automated invoice and transfer management system integrated with the Stark Bank API. The system generates invoices periodically (every 3 hours), processes payment webhooks, and automatically executes transfers upon receiving payments.

Developed as part of the Stark Bank selection process, demonstrating the ability to integrate with external APIs, event-driven architecture, security, and robust error handling.

## 🚀 Implemented Features

- ✅ **Automatic Invoice Generation**: Scheduler that creates 8-12 invoices every 3 hours for 24h
- ✅ **Data Validation**: Generation of valid CPF/CNPJ with 70/30 distribution
- ✅ **Webhook Processing**: Secure reception and processing of Stark Bank webhooks
- ✅ **Digital Signature Validation**: ECDSA verification of webhooks using the public key fetched dynamically from the Stark Bank API
- ✅ **Automatic Transfers**: Automatic transfer creation upon receiving invoice payments
- ✅ **Retry Logic**: Exponential retry system for Stark Bank API calls
- ✅ **Idempotency**: Guarantee of no transfer duplication
- ✅ **Event Bus**: Event-driven architecture for module decoupling
- ✅ **RESTful API**: API Key-protected endpoints for querying invoices and transfers
- ✅ **Structured Logging**: Detailed logs in JSON format for monitoring
- ✅ **Health Check**: Application health verification endpoint
- ✅ **Persistence**: SQLite database with automatic migrations
- ✅ **Comprehensive Tests**: Coverage > 85% (unit, integration, and E2E)

## 🛠️ Technology Stack

- **Python 3.14+**: Primary language
- **FastAPI**: Asynchronous web framework for APIs
- **Stark Bank SDK**: Official Stark Bank integration
- **SQLite**: Database (easy migration to PostgreSQL)
- **APScheduler**: Periodic task scheduling
- **pytest**: Testing framework
- **Ruff**: Linting and code formatting
- **Uvicorn**: High-performance ASGI server

## 📂 Project Structure

The project follows a modular event-driven architecture:

```
stark-bank-challenge/
├── src/
│   ├── modules/           # Domain modules
│   │   ├── invoices/      # Invoice generation and management
│   │   ├── webhooks/      # Webhook processing
│   │   └── transfers/     # Transfer execution
│   │
│   ├── shared/            # Shared components
│   │   ├── database/      # Data layer
│   │   ├── events/        # Event Bus
│   │   ├── stark/         # Stark Bank integration
│   │   ├── security/      # Security and validation
│   │   └── utils/         # Utilities
│   │
│   ├── config/            # Global configurations
│   ├── main.py            # API entry point (FastAPI)
│   └── scheduler.py       # Invoice scheduler
│
├── tests/                 # Automated tests
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
│
├── docs/                  # Detailed documentation
└── migrations/            # Database migrations
```

## 📋 Requirements

- **Python 3.14+**
- Account on [Stark Bank](https://starkbank.com) (sandbox environment)
- Git

## 🔧 Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/stark-bank-challenge.git
cd stark-bank-challenge
```

### 2. Install Dependencies

**Using pip (standard):**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -e .[dev]
```

**Using Rye (recommended):**
```bash
rye sync
```

**Using Poetry:**
```bash
poetry install
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file with your credentials:

```env
# Application
APP_ENV=development
LOG_LEVEL=INFO

# Stark Bank Credentials
STARK_BANK_PROJECT_ID=your-project-id-here
STARK_BANK_PRIVATE_KEY=-----BEGIN EC PRIVATE KEY-----\nYour\nPrivate\nKey\nHere\n-----END EC PRIVATE KEY-----
STARK_BANK_ENVIRONMENT=sandbox

# API Security
API_KEY=dev-key-insecure-change-in-production

# Database
DATABASE_PATH=./data/stark_bank.db

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_DURATION_HOURS=24

# Invoice Generation
INVOICE_MIN_COUNT=8
INVOICE_MAX_COUNT=12
INVOICE_MIN_AMOUNT=100
INVOICE_MAX_AMOUNT=10000
INVOICE_DUE_DAYS_MIN=1
INVOICE_DUE_DAYS_MAX=7
```

**How to obtain Stark Bank credentials:**
1. Access [Stark Bank Sandbox](https://web.sandbox.starkbank.com)
2. Create a developer account
3. Generate an ECDSA (Elliptic Curve) key pair
4. Register the public key in the Stark Bank dashboard
5. Copy the Project ID and private key to the `.env` file

### 4. Run Database Migrations

Migrations run automatically on application startup, but you can run them manually:

```bash
python -c "from src.shared.database.migrations import run_migrations; run_migrations()"
```

### 5. Start the Application

**Development mode (with auto-reload):**
```bash
uvicorn src.main:app --reload --port 8000
```

**Production mode:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at: `http://localhost:8000`

- **API Docs (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

### 6. Configure Webhooks in Stark Bank

To receive payment notifications:

1. Access the Stark Bank dashboard
2. Configure the following webhooks:
   - **Invoice:** `https://your-url.railway.app/webhooks/invoice`
   - **Transfer:** `https://your-url.railway.app/webhooks/transfer`

## 🧪 How to Test

### Run All Tests

```bash
pytest
```

### Tests by Category

```bash
# Unit tests only
pytest tests/unit -v

# Integration tests only
pytest tests/integration -v

# E2E tests only
pytest tests/e2e -v
```

### Tests with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View HTML report
# Open: htmlcov/index.html in browser
```

### Specific Tests

```bash
# Test specific module
pytest tests/unit/modules/invoices/ -v

# Test specific file
pytest tests/unit/modules/invoices/test_service.py -v

# Test specific function
pytest tests/unit/modules/invoices/test_service.py::test_create_invoice_success -v
```

### Test Full Flow (Manual)

1. **Create Invoice:**
```bash
curl -X POST http://localhost:8000/invoices \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "tax_id": "012.345.678-90",
    "name": "John Smith",
    "due": "2026-02-20"
  }'
```

2. **List Invoices:**
```bash
curl -X GET "http://localhost:8000/invoices?status=created&limit=10" \
  -H "X-API-Key: dev-key"
```

3. **Simulate Payment Webhook** (use Stark Bank tools or Postman)

4. **Check Created Transfer:**
```bash
curl -X GET http://localhost:8000/transfers \
  -H "X-API-Key: dev-key"
```

## 🚀 Deploy (Railway)

> 📖 **For detailed deployment instructions**, see the [Deployment Guide](docs/deployment.md), which includes:
> - Step-by-step Railway configuration
> - Environment variable setup
> - Database persistence
> - Monitoring and troubleshooting
> - Alternative deployments (Heroku, Render, Docker, DigitalOcean)

### Prerequisites

- Account on [Railway](https://railway.app)
- Project connected to GitHub

### Deployment Steps

1. **Create a new project on Railway:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose the `stark-bank-challenge` repository

2. **Configure Environment Variables:**

   In Railway, go to "Variables" and add:
   ```
   APP_ENV=production
   LOG_LEVEL=INFO
   STARK_BANK_PROJECT_ID=<your-project-id>
   STARK_BANK_PRIVATE_KEY=<your-private-key>
   STARK_BANK_ENVIRONMENT=sandbox
   API_KEY=<generate-a-strong-key>
   DATABASE_PATH=/app/data/stark_bank.db
   SCHEDULER_ENABLED=true
   SCHEDULER_INTERVAL_HOURS=3
   SCHEDULER_DURATION_HOURS=24
   ```

3. **Configure the Start Command:**

   In Railway, under "Settings" > "Deploy", configure:
   ```
   uvicorn src.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Configure Volume for Persistence (Optional):**
   - Railway offers persistent volumes
   - Mount at `/app/data` to keep the SQLite database
   - Or migrate to PostgreSQL (Railway offers free PostgreSQL)

5. **Deploy:**
   - Commit to GitHub
   - Railway will deploy automatically

6. **Configure Webhooks:**
   - After deployment, copy the Railway URL: `https://your-app.railway.app`
   - Configure in Stark Bank:
     - Invoice: `https://your-app.railway.app/webhooks/invoice`
     - Transfer: `https://your-app.railway.app/webhooks/transfer`

7. **Monitor:**
   - Use Railway Logs to monitor
   - Check Health Check: `https://your-app.railway.app/health`

### Alternative: Deploy with Docker

```bash
# Dockerfile already configured in the project
docker build -t stark-bank-challenge .
docker run -p 8000:8000 --env-file .env stark-bank-challenge
```

## 💻 Development

### Linting and Formatting
The project uses `ruff` for linting and formatting.

```bash
# Check linting
ruff check src/

# Auto-fix linting
ruff check src/ --fix

# Format code
ruff format src/
```

### Available Scripts (Windows)

```bash
# Format code
.\scripts\format.bat

# Run linter
.\scripts\lint.bat

# Run tests
.\scripts\test.bat
```

## 📚 Additional Documentation

- [Architecture](docs/architecture.md) - Architectural decisions and patterns used
- [API](docs/api.md) - Complete REST API documentation
- [Implementation Plan](docs/implementation-plan.md) - Detailed development plan
- [E2E Details](docs/e2e-details.md) - End-To-End test details
- [Original Challenge](docs/challenge.md) - Challenge specification

## 📊 Architecture

The system uses **event-driven architecture** with the following main components:

- **Event Bus**: Decouples modules via publish/subscribe
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic
- **API Layer**: REST endpoints with FastAPI

### Main Flow

1. **Scheduler** generates invoices every 3h
2. Invoices are created in the **Stark Bank API**
3. When paid, a **webhook** notifies the system
4. System fetches Stark Bank public key from the API and validates the ECDSA signature
5. **Event Bus** publishes `invoice.paid` event
6. **Transfer Handler** listens to the event and creates a transfer
7. Transfer is executed in Stark Bank
8. Webhooks notify transfer status

## 🔒 Security

- ECDSA digital signature validation on all webhooks (public key fetched dynamically from `https://sandbox.api.starkbank.com/v2/public-key` and cached)
- API Key authentication for private endpoints
- Input data validation with Pydantic
- Logging of all sensitive operations
- Secrets via environment variables

## 🧰 Technologies and Patterns

- **Clean Architecture**: Layer separation
- **SOLID Principles**: Maintainable and testable code
- **Dependency Injection**: Dependency decoupling
- **Repository Pattern**: Persistence abstraction
- **Event-Driven Architecture**: Asynchronous communication between modules
- **Retry Pattern**: Resilience in external calls
- **Idempotency**: Duplication prevention

## 🤝 Contributing

1. Fork the project
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## 👤 Author

Developed as part of the Stark Bank selection process.

---

**Note**: This project uses the Stark Bank **sandbox** environment. For production use, adjust the configurations appropriately.
