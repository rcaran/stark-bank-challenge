# Deployment Guide

This guide provides step-by-step instructions for deploying the Stark Bank Challenge application to Railway and other platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Railway Deployment](#railway-deployment)
3. [Environment Variables Configuration](#environment-variables-configuration)
4. [Database Persistence](#database-persistence)
5. [Monitoring Setup](#monitoring-setup)
6. [Troubleshooting](#troubleshooting)
7. [Alternative Platforms](#alternative-platforms)

---

## Prerequisites

Before deploying, ensure you have:

- **GitHub Account**: Repository must be hosted on GitHub
- **Railway Account**: Sign up at [railway.app](https://railway.app)
- **Stark Bank Account**: Sandbox credentials from [starkbank.com](https://starkbank.com)
- **API Key**: Generated secure random key (e.g., `openssl rand -hex 32`)

---

## Railway Deployment

Railway is the recommended platform for deploying this application due to its simplicity and free tier.

### 1. Initial Setup

1. **Sign up/Login to Railway**
   - Go to [railway.app](https://railway.app)
   - Sign in with your GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose the `stark-bank-challenge` repository
   - Railway will automatically detect the Python project

3. **Configure Build Settings**
   - Railway automatically detects `pyproject.toml`
   - Build command: `pip install -e .`
   - Start command: Defined in `Procfile` (see below)

### 2. Deploy Configuration Files

The repository includes the following deployment files:

#### `Procfile`
```
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

#### `railway.toml`
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### 3. First Deployment

1. Railway will automatically start building the project
2. Monitor the build logs in the Railway dashboard
3. The build process:
   - Detects Python 3.14
   - Installs dependencies from `pyproject.toml`
   - Creates the deployment image
   - Starts the application

### 4. Obtain Application URL

After successful deployment:
- Go to the "Settings" tab in Railway
- Click "Generate Domain"
- Your app will be available at: `https://<your-app>.railway.app`

---

## Environment Variables Configuration

### Setting Variables in Railway

1. Navigate to your project in Railway
2. Click on the "Variables" tab
3. Add the following environment variables:

### Required Variables

```bash
# Application Settings
APP_NAME=stark-bank-challenge
APP_ENV=production
LOG_LEVEL=INFO
API_PORT=8000
API_HOST=0.0.0.0

# Security (IMPORTANT: Change this!)
ADMIN_API_KEY=<generate-secure-random-key>

# Stark Bank Configuration
STARKBANK_PRIVATE_KEY_CONTENT=<your-stark-bank-private-key>
STARKBANK_PROJECT_ID=<your-stark-bank-project-id>
STARKBANK_ENVIRONMENT=sandbox

# Database
DATABASE_URL=sqlite:///./data/starkbank.db

# Scheduler
SCHEDULER_INTERVAL_HOURS=3
INVOICE_GENERATION_MIN=8
INVOICE_GENERATION_MAX=12
```

### Generating Secure API Key

```bash
# On Linux/Mac
openssl rand -hex 32

# On Windows (PowerShell)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Obtaining Stark Bank Credentials

1. **Sign up** at [starkbank.com](https://starkbank.com)
2. **Create Sandbox Project**:
   - Go to Dashboard → Projects
   - Create a new Sandbox project
   - Note the Project ID
3. **Generate Private Key**:
   - Use Stark Bank CLI or Dashboard
   - Download the ECDSA private key
   - Copy the entire PEM content including headers:
     ```
     -----BEGIN EC PRIVATE KEY-----
     <key content>
     -----END EC PRIVATE KEY-----
     ```

4. **Set in Railway**:
   - For multiline keys, paste the entire content
   - Or encode as base64 if needed

---

## Database Persistence

### SQLite with Volume (Recommended)

Railway provides volume mounting for file persistence:

1. **Create Volume in Railway**:
   - Go to project Settings
   - Navigate to "Volumes"
   - Click "Add Volume"
   - Mount path: `/app/data`
   - Size: 1 GB (sufficient for this project)

2. **Update DATABASE_URL**:
   ```bash
   DATABASE_URL=sqlite:////app/data/starkbank.db
   ```
   Note: Four slashes for absolute path

3. **Verify Persistence**:
   - Deploy the application
   - Create some invoices
   - Redeploy the application
   - Verify data persists

### PostgreSQL Alternative (Recommended for Production)

Railway offers free PostgreSQL databases:

1. **Add PostgreSQL Service**:
   - In Railway project, click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway automatically provisions the database

2. **Link to Application**:
   - Railway provides `DATABASE_URL` automatically
   - Update application to use PostgreSQL connection

3. **Modify Database Adapter** (if needed):
   - Update `src/shared/database/connection.py`
   - Replace SQLite-specific code with SQLAlchemy or similar
   - Add `psycopg2-binary` to dependencies

### Database Migrations

The application automatically runs migrations on startup:

```python
# src/main.py (lifespan event)
async def startup_event():
    db = DatabaseConnection()
    db.run_migrations()
    logger.info("Database migrations completed")
```

To run migrations manually:
```bash
railway run python -c "from src.shared.database.migrations import run_migrations; run_migrations()"
```

---

## Monitoring Setup

### Railway Dashboard Monitoring

Railway provides built-in monitoring:

1. **Metrics Available**:
   - CPU usage
   - Memory usage
   - Network traffic
   - Build/deployment history
   - Crash reports

2. **Viewing Logs**:
   - Click on your service
   - Go to "Deployments" tab
   - Select current deployment
   - View real-time logs

3. **Log Filtering**:
   ```bash
   # View logs locally via Railway CLI
   railway logs --tail

   # Filter specific level
   railway logs | grep ERROR
   ```

### Application Health Check

The application provides a health endpoint:

```bash
# Check application health
curl https://<your-app>.railway.app/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-17T10:30:00.123Z",
  "checks": {
    "database": "ok",
    "event_bus": "ok"
  },
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### Setting Up Alerts

Railway doesn't have built-in alerting on free tier, but you can:

1. **External Monitoring** (e.g., UptimeRobot):
   - Sign up at [uptimerobot.com](https://uptimerobot.com)
   - Add monitor for `/health` endpoint
   - Configure email/SMS alerts

2. **Custom Logging**:
   - The app logs to stdout (captured by Railway)
   - Configure external log aggregation (e.g., Logtail, Papertrail)

### Scheduler Monitoring

Monitor invoice generation:

```bash
# Check logs for scheduler activity
railway logs | grep "Scheduler"

# Expected output every 3 hours:
# [INFO] Scheduler job started
# [INFO] Generated 10 invoices
# [INFO] Scheduler job completed
```

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms**: Deployment fails or crashes immediately

**Solutions**:
```bash
# Check logs
railway logs --tail

# Common causes:
# - Missing environment variables
# - Invalid Stark Bank credentials
# - Database connection issues

# Verify environment variables
railway variables

# Test locally first
python -m src.main
```

#### 2. Database Not Persisting

**Symptoms**: Data lost after redeploy

**Solutions**:
- Verify volume is mounted: `/app/data`
- Check DATABASE_URL uses absolute path: `sqlite:////app/data/...`
- Ensure volume size is sufficient
- Check file permissions in logs

#### 3. Webhooks Not Received

**Symptoms**: Invoices created but transfers not triggered

**Solutions**:
```bash
# Verify Railway URL is public
curl https://<your-app>.railway.app/webhooks/invoice

# Check webhook registration in Stark Bank
# Dashboard → Webhooks → Verify URLs

# Test signature validation
# Check logs for "WebhookValidationFailedEvent"

# Manually trigger test webhook from Stark Bank dashboard
```

#### 4. High Memory Usage

**Symptoms**: Application crashes with OOM errors

**Solutions**:
- Railway free tier: 512 MB RAM limit
- Optimize database queries (use pagination)
- Reduce scheduler frequency if needed
- Consider upgrading Railway plan
- Monitor with: `railway logs | grep memory`

#### 5. Stark Bank API Errors

**Symptoms**: 401, 403, or 500 errors from Stark Bank

**Solutions**:
```bash
# Verify credentials
railway variables | grep STARK

# Check API key format (must include headers)
# Check Project ID is correct
# Verify sandbox environment

# Test credentials locally
python -c "from src.shared.stark.client import StarkBankClientWrapper; client = StarkBankClientWrapper(); print('OK')"
```

#### 6. Port Binding Issues

**Symptoms**: Application starts but not accessible

**Solutions**:
- Ensure `--port $PORT` is used (Railway provides PORT env var)
- Verify `--host 0.0.0.0` (not 127.0.0.1)
- Check Procfile is correct:
  ```
  web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
  ```

### Debug Mode

To enable verbose logging:

```bash
# In Railway variables
LOG_LEVEL=DEBUG

# Redeploy to apply
railway up
```

### Restart Application

```bash
# Via Railway Dashboard
# Go to project → Click restart icon

# Via Railway CLI
railway restart

# Force redeploy
railway up --force
```

### Database Reset

If you need to reset the database:

```bash
# WARNING: This deletes all data!

# Via Railway CLI (if volume exists)
railway run rm /app/data/starkbank.db

# Or delete and recreate volume in Railway dashboard
# Settings → Volumes → Delete → Create new
```

---

## Webhook Registration

After deploying, register webhooks with Stark Bank:

### 1. Get Your Railway URL

```bash
# From Railway dashboard or CLI
railway domain
# Output: https://<your-app>.railway.app
```

### 2. Register Webhooks in Stark Bank

Go to Stark Bank Dashboard → Webhooks:

1. **Invoice Webhook**:
   - URL: `https://<your-app>.railway.app/webhooks/invoice`
   - Event: `invoice.paid`
   - Method: POST

2. **Transfer Webhook**:
   - URL: `https://<your-app>.railway.app/webhooks/transfer`
   - Events: `transfer.processing`, `transfer.success`, `transfer.failed`
   - Method: POST

### 3. Verify Webhook Registration

Test with Stark Bank's webhook test tool:
```bash
# Check logs after triggering test
railway logs | grep webhook
```

---

## Production Checklist

Before going live, verify:

- [ ] All environment variables set correctly
- [ ] Secure API key generated (not "dev-api-key")
- [ ] Stark Bank credentials valid
- [ ] Database persistence configured (volume or PostgreSQL)
- [ ] Webhooks registered with correct URLs
- [ ] Health check endpoint responding
- [ ] Logs showing scheduler running every 3 hours
- [ ] Test invoice creation working
- [ ] Test webhook reception working
- [ ] Test transfer creation after payment webhook
- [ ] Monitoring/alerting configured
- [ ] Documentation reviewed

---

## Alternative Platforms

While Railway is recommended, the application can be deployed to other platforms:

### Heroku

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create stark-bank-challenge

# Add buildpack
heroku buildpacks:set heroku/python

# Set environment variables
heroku config:set APP_ENV=production
heroku config:set ADMIN_API_KEY=<your-key>
# ... (set all other variables)

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Render

1. Create account at [render.com](https://render.com)
2. New Web Service → Connect repository
3. Configure:
   - Build Command: `pip install -e .`
   - Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy

### Docker (Self-Hosted)

```dockerfile
# Dockerfile (create if needed)
FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t stark-bank-challenge .
docker run -p 8000:8000 --env-file .env stark-bank-challenge
```

### DigitalOcean App Platform

1. Create account at [digitalocean.com](https://digitalocean.com)
2. Apps → Create App → GitHub repository
3. Configure:
   - Type: Web Service
   - Run Command: `uvicorn src.main:app --host 0.0.0.0 --port 8080`
4. Add environment variables
5. Deploy

---

## Performance Optimization

### Railway Free Tier Limits

- **CPU**: Shared
- **RAM**: 512 MB
- **Disk**: 1 GB (volume)
- **Network**: 100 GB/month
- **Sleep**: No (always on)

### Optimization Tips

1. **Database Queries**:
   - Use pagination for list endpoints
   - Add indexes to frequently queried columns
   - Limit batch sizes

2. **Memory Usage**:
   - Monitor with health check
   - Avoid loading large datasets in memory
   - Use generators for batch processing

3. **API Calls**:
   - Batch Stark Bank API calls when possible
   - Implement request caching
   - Use retry with exponential backoff

4. **Scheduler**:
   - Adjust interval if needed (default: 3 hours)
   - Reduce batch size if memory issues

---

## Scaling Considerations

When scaling beyond free tier:

1. **Upgrade Railway Plan**:
   - Developer: $5/month (more resources)
   - Team: $20/month (priority support)

2. **Migrate to PostgreSQL**:
   - Better performance for large datasets
   - ACID compliance
   - Concurrent access handling

3. **Separate Services**:
   - API service (FastAPI)
   - Scheduler service (separate worker)
   - Background jobs (Celery/RQ)

4. **Load Balancing**:
   - Multiple Railway instances
   - Use Railway's built-in load balancing
   - Configure health checks for auto-restart

---

## Support

For deployment issues:

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Stark Bank Support**: [starkbank.com/support](https://starkbank.com/support)
- **Project Issues**: GitHub Issues in this repository

---

## Version History

- **v1.0.0** (2026-02-17): Initial deployment guide
