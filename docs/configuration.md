# Configuration Guide

## Overview

This document provides detailed instructions for configuring the Stark Bank Challenge application. The application uses environment variables for configuration, making it easy to deploy across different environments (development, staging, production).

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Stark Bank Credentials](#stark-bank-credentials)
- [Database Configuration](#database-configuration)
- [Security Configuration](#security-configuration)
- [Scheduler Configuration](#scheduler-configuration)
- [Environment-Specific Settings](#environment-specific-settings)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Copy Environment File

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` and fill in the required values:

```bash
# Minimum required configuration
ADMIN_API_KEY=your-secure-api-key-here
STARKBANK_PRIVATE_KEY_CONTENT=your-stark-bank-private-key
STARKBANK_PROJECT_ID=your-project-id
```

### 3. Verify Configuration

```bash
# Run the application to verify configuration
uvicorn src.main:app --reload

# Check health endpoint
curl http://localhost:8000/health
```

---

## Environment Variables

### Application Settings

#### `APP_NAME`
- **Description**: Application name used in logs and monitoring
- **Type**: String
- **Default**: `stark-bank-challenge`
- **Required**: No
- **Example**: `stark-bank-challenge`

#### `APP_ENV`
- **Description**: Application environment
- **Type**: String
- **Default**: `development`
- **Required**: No
- **Values**: `development`, `staging`, `production`
- **Example**: `production`
- **Notes**: Affects logging behavior and error handling

#### `LOG_LEVEL`
- **Description**: Logging level for the application
- **Type**: String
- **Default**: `INFO`
- **Required**: No
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example**: `INFO`
- **Recommendations**:
  - Development: `DEBUG` or `INFO`
  - Production: `INFO` or `WARNING`

#### `API_PORT`
- **Description**: Port where the FastAPI server will listen
- **Type**: Integer
- **Default**: `8000`
- **Required**: No
- **Example**: `8000`

#### `API_HOST`
- **Description**: Host interface for the API server
- **Type**: String
- **Default**: `0.0.0.0`
- **Required**: No
- **Values**: `0.0.0.0` (all interfaces), `127.0.0.1` (localhost only)
- **Example**: `0.0.0.0`

---

### Security Configuration

#### `ADMIN_API_KEY`
- **Description**: API key for protected endpoints (invoices, transfers)
- **Type**: String
- **Default**: None
- **Required**: Yes (highly recommended)
- **Example**: `sk_live_abc123xyz789...`
- **Generation**:
  ```bash
  # Generate a secure random key
  openssl rand -hex 32
  ```
- **Usage**: Include in request headers as `X-API-Key: your-api-key`
- **Security Notes**:
  - Use a strong, random key (minimum 32 characters)
  - Never commit the actual key to version control
  - Rotate keys periodically in production
  - Use different keys for different environments

---

### Stark Bank Configuration

#### `STARKBANK_PRIVATE_KEY_CONTENT`
- **Description**: ECDSA private key for Stark Bank API authentication
- **Type**: String (PEM format)
- **Default**: None
- **Required**: Yes
- **Format**:
  ```
  -----BEGIN EC PRIVATE KEY-----
  MHQCAQEEIAbc...xyz123
  -----END EC PRIVATE KEY-----
  ```
- **How to Obtain**:
  1. Access [Stark Bank Dashboard](https://web.sandbox.starkbank.com/) (Sandbox)
  2. Go to Settings → API Keys
  3. Generate a new private key
  4. Copy the entire PEM content including headers
- **Security Notes**:
  - Keep this key secret and secure
  - Never commit to version control
  - Use different keys for sandbox and production

#### `STARKBANK_PROJECT_ID`
- **Description**: Project ID from Stark Bank dashboard
- **Type**: String
- **Default**: None
- **Required**: Yes
- **Example**: `5656565656565656`
- **How to Obtain**:
  1. Access Stark Bank Dashboard
  2. Go to Settings → Project Information
  3. Copy the Project ID
- **Notes**: Use sandbox Project ID for development/testing

#### `STARKBANK_ENVIRONMENT`
- **Description**: Stark Bank environment to use
- **Type**: String
- **Default**: `sandbox`
- **Required**: No
- **Values**: `sandbox`, `production`
- **Example**: `sandbox`
- **Important**:
  - Always use `sandbox` for development and testing
  - Only use `production` when ready for real transactions
  - Production requires different credentials and approval from Stark Bank

#### Webhook Signature Public Key (automatic)
- **Description**: The ECDSA public key used to validate webhook signatures is **not configured manually**. The application fetches it automatically from the Stark Bank API at startup and caches the result in memory.
- **Sandbox endpoint**: `https://sandbox.api.starkbank.com/v2/public-key`
- **Production endpoint**: `https://api.starkbank.com/v2/public-key`
- The endpoint used is determined by `STARKBANK_ENVIRONMENT`.
- **No action required** — this happens transparently. Ensure the application has outbound internet access to reach the Stark Bank API.

---

### Database Configuration

#### `DATABASE_URL`
- **Description**: Database connection URL
- **Type**: String
- **Default**: `sqlite:///./starkbank.db`
- **Required**: No
- **Examples**:
  - SQLite (file): `sqlite:///./starkbank.db`
  - SQLite (memory): `sqlite:///:memory:`
  - PostgreSQL: `postgresql://user:password@localhost:5432/dbname`
  - PostgreSQL (Railway): `postgresql://user:password@host.railway.app:5432/railway`
- **Recommendations**:
  - **Development**: SQLite is sufficient and easy to use
  - **Production**: PostgreSQL for better concurrency and reliability
  - **Testing**: In-memory SQLite for speed

**Database Selection Guide:**

| Environment | Recommended | Reason |
|-------------|-------------|--------|
| Development | SQLite | Simple, no setup required |
| Testing | SQLite (memory) | Fast, isolated |
| Production | PostgreSQL | Concurrent access, ACID compliance |

---

### Scheduler Configuration

#### `SCHEDULER_INTERVAL_HOURS`
- **Description**: How often the scheduler generates new invoices
- **Type**: Integer
- **Default**: `3`
- **Required**: No
- **Range**: 1-24
- **Example**: `3`
- **Notes**:
  - Value of `3` means invoices are generated every 3 hours
  - 8 executions per day (24 hours / 3 hours)
  - Adjust based on business requirements

#### `INVOICE_GENERATION_MIN`
- **Description**: Minimum number of invoices to generate per execution
- **Type**: Integer
- **Default**: `8`
- **Required**: No
- **Example**: `8`
- **Notes**: Must be less than or equal to `INVOICE_GENERATION_MAX`

#### `INVOICE_GENERATION_MAX`
- **Description**: Maximum number of invoices to generate per execution
- **Type**: Integer
- **Default**: `12`
- **Required**: No
- **Example**: `12`
- **Notes**: 
  - Scheduler generates a random number between MIN and MAX
  - This variability simulates real-world scenarios

---

## Stark Bank Credentials

### Getting Sandbox Credentials

1. **Create Stark Bank Account**
   - Go to [Stark Bank Sandbox](https://web.sandbox.starkbank.com/)
   - Sign up for a free sandbox account
   - Confirm your email

2. **Generate API Keys**
   - Log in to the sandbox dashboard
   - Navigate to: Settings → API Keys → New Key
   - Click "Generate Key Pair"
   - Download or copy the **Private Key** (PEM format)
   - Save it securely

3. **Get Project ID**
   - In the dashboard, go to: Settings → Project Information
   - Copy your **Project ID**
   - It will be a numeric string (e.g., `5656565656565656`)

4. **Configure Environment**
   ```bash
   # In your .env file
   STARKBANK_PROJECT_ID=5656565656565656
   STARKBANK_PRIVATE_KEY_CONTENT=-----BEGIN EC PRIVATE KEY-----
   MHQCAQEEIAbc...xyz123
   -----END EC PRIVATE KEY-----
   STARKBANK_ENVIRONMENT=sandbox
   ```

### Production Credentials

⚠️ **Important**: Production credentials require:
- Approved business account with Stark Bank
- KYC (Know Your Customer) verification
- Legal and compliance documentation
- Different private keys and project ID

**Do not use production credentials for development/testing!**

---

## Database Configuration

### SQLite (Default)

**Pros:**
- Zero configuration
- No separate database server needed
- Perfect for development and testing
- Easy to backup (single file)

**Cons:**
- Limited concurrent writes
- Not suitable for high-traffic production

**Configuration:**
```bash
DATABASE_URL=sqlite:///./starkbank.db
```

**File Location**: Database file will be created in the project root as `starkbank.db`

### PostgreSQL (Recommended for Production)

**Pros:**
- Excellent concurrency support
- ACID compliance
- Better for production workloads
- Built-in replication and backup

**Cons:**
- Requires separate database server
- More complex setup

**Configuration:**
```bash
# Local PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/starkbank

# Railway PostgreSQL (example)
DATABASE_URL=postgresql://postgres:password@containers-us-west-123.railway.app:5432/railway
```

**Setup on Railway:**
1. Create a new PostgreSQL service
2. Copy the `DATABASE_URL` from the service
3. Set it as an environment variable in your app

---

## Security Configuration

### API Key Generation

Generate a strong API key for production:

```bash
# Method 1: Using OpenSSL
openssl rand -hex 32

# Method 2: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Method 3: Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### API Key Usage

**In Requests:**
```bash
curl -X GET http://localhost:8000/invoices \
  -H "X-API-Key: your-api-key-here"
```

**In Code:**
```python
import requests

headers = {"X-API-Key": "your-api-key-here"}
response = requests.get("http://localhost:8000/invoices", headers=headers)
```

### Security Best Practices

1. **Environment Variables**: Never hardcode credentials in code
2. **Version Control**: Never commit `.env` file (use `.gitignore`)
3. **Key Rotation**: Rotate API keys periodically
4. **Different Keys**: Use different keys for dev/staging/production
5. **HTTPS**: Always use HTTPS in production
6. **Monitoring**: Log authentication failures

---

## Scheduler Configuration

### How It Works

The scheduler runs automatically when the application starts and:
1. Generates invoices at configured intervals
2. Creates invoices between MIN and MAX count
3. Submits invoices to Stark Bank API
4. Stores invoices in the database
5. Publishes events for monitoring

### Configuration Examples

**High Frequency (Development/Testing):**
```bash
SCHEDULER_INTERVAL_HOURS=1
INVOICE_GENERATION_MIN=2
INVOICE_GENERATION_MAX=5
```
- Generates 2-5 invoices every hour
- 48-120 invoices per day

**Normal Frequency (Production):**
```bash
SCHEDULER_INTERVAL_HOURS=3
INVOICE_GENERATION_MIN=8
INVOICE_GENERATION_MAX=12
```
- Generates 8-12 invoices every 3 hours
- 64-96 invoices per day

**Low Frequency (Light Usage):**
```bash
SCHEDULER_INTERVAL_HOURS=6
INVOICE_GENERATION_MIN=5
INVOICE_GENERATION_MAX=10
```
- Generates 5-10 invoices every 6 hours
- 20-40 invoices per day

### Disabling the Scheduler

To run the application without the scheduler (e.g., for testing):

```python
# In src/main.py, comment out scheduler initialization
# or set an environment flag
SCHEDULER_ENABLED=false
```

---

## Environment-Specific Settings

### Development Environment

```bash
APP_ENV=development
LOG_LEVEL=DEBUG
API_HOST=127.0.0.1
API_PORT=8000

ADMIN_API_KEY=dev-key-123

STARKBANK_ENVIRONMENT=sandbox
STARKBANK_PROJECT_ID=your-sandbox-project-id
STARKBANK_PRIVATE_KEY_CONTENT=your-sandbox-private-key

DATABASE_URL=sqlite:///./starkbank.db

SCHEDULER_INTERVAL_HOURS=1
INVOICE_GENERATION_MIN=2
INVOICE_GENERATION_MAX=5
```

**Features:**
- Verbose logging (DEBUG)
- Localhost only
- Frequent scheduler (1 hour)
- SQLite database
- Sandbox Stark Bank

### Production Environment

```bash
APP_ENV=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

ADMIN_API_KEY=sk_prod_abc123xyz789...

STARKBANK_ENVIRONMENT=production
STARKBANK_PROJECT_ID=your-production-project-id
STARKBANK_PRIVATE_KEY_CONTENT=your-production-private-key

DATABASE_URL=postgresql://user:password@db-host:5432/starkbank

SCHEDULER_INTERVAL_HOURS=3
INVOICE_GENERATION_MIN=8
INVOICE_GENERATION_MAX=12
```

**Features:**
- Moderate logging (INFO)
- All interfaces (0.0.0.0)
- Normal scheduler (3 hours)
- PostgreSQL database
- Production Stark Bank

### Testing Environment

```bash
APP_ENV=testing
LOG_LEVEL=WARNING
DATABASE_URL=sqlite:///:memory:
SCHEDULER_ENABLED=false
```

**Features:**
- Minimal logging
- In-memory database (fast)
- Scheduler disabled

---

## Troubleshooting

### Issue: "Invalid Stark Bank Credentials"

**Symptoms:**
- API returns 401 or authentication errors
- Logs show "Invalid credentials" or "Authentication failed"

**Solutions:**
1. Verify `STARKBANK_PROJECT_ID` is correct
2. Check `STARKBANK_PRIVATE_KEY_CONTENT` includes full PEM format with headers
3. Ensure no extra spaces or newlines in the key
4. Verify you're using sandbox credentials with `STARKBANK_ENVIRONMENT=sandbox`
5. Generate new credentials if needed

### Issue: "Webhook Signature Validation Failed" (Invalid key)

**Symptoms:**
- Logs show `Failed to load public key: Invalid key` or `Signature validation failed`
- Webhooks from Stark Bank are rejected with 401/403

**Solutions:**
1. Ensure the application has outbound internet access to reach the Stark Bank public-key API
2. Verify `STARKBANK_ENVIRONMENT` is set correctly (`sandbox` or `production`)
3. If running behind a proxy or firewall, ensure `https://sandbox.api.starkbank.com` (or `https://api.starkbank.com`) is reachable
4. Restart the application to clear the in-memory key cache and force a fresh fetch
5. Manually test connectivity: `curl https://sandbox.api.starkbank.com/v2/public-key`

---

### Issue: "Database Locked" (SQLite)

**Symptoms:**
- Error: "database is locked"
- Application hangs on database operations

**Solutions:**
1. Close any other connections to the database file
2. Use PostgreSQL for better concurrency
3. Reduce scheduler frequency
4. Check for long-running transactions

### Issue: "API Key Authentication Failed"

**Symptoms:**
- 403 Forbidden on protected endpoints
- "Invalid API Key" errors

**Solutions:**
1. Verify `ADMIN_API_KEY` is set in `.env`
2. Check you're including `X-API-Key` header in requests
3. Ensure no typos in the API key
4. Restart the application after changing `.env`

### Issue: "Scheduler Not Running"

**Symptoms:**
- No invoices being generated
- No scheduler logs

**Solutions:**
1. Check `SCHEDULER_ENABLED` is not set to false
2. Verify `SCHEDULER_INTERVAL_HOURS` is set
3. Check application logs for scheduler errors
4. Ensure application startup completed successfully

### Issue: "Environment Variables Not Loading"

**Symptoms:**
- Application using default values
- Configuration changes not taking effect

**Solutions:**
1. Verify `.env` file exists in project root
2. Check file name is exactly `.env` (not `.env.txt`)
3. Restart the application after changes
4. Check for syntax errors in `.env` file
5. Ensure `python-dotenv` is installed

---

## Configuration Checklist

Before deploying, verify:

- [ ] `.env` file created from `.env.example`
- [ ] `ADMIN_API_KEY` set to a strong random value
- [ ] Stark Bank credentials configured correctly
- [ ] Database URL set appropriately for environment
- [ ] Log level appropriate for environment
- [ ] Scheduler interval configured
- [ ] `.env` added to `.gitignore`
- [ ] Documentation reviewed
- [ ] Health check endpoint working
- [ ] API authentication tested

---

## Additional Resources

- [Stark Bank API Documentation](https://starkbank.com/docs/api)
- [FastAPI Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
- [Python Dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)

---

## Support

For issues or questions:
1. Check this documentation first
2. Review application logs
3. Check [docs/api.md](api.md) for API documentation
4. Check [docs/architecture.md](architecture.md) for system design

---

**Last Updated**: February 16, 2026  
**Version**: 1.0.0
