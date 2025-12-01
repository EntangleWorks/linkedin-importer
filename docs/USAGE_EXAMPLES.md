# Usage Examples

This document provides comprehensive usage examples for the LinkedIn Profile Importer.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Import Scenarios](#basic-import-scenarios)
- [Database Configuration Examples](#database-configuration-examples)
- [API Credential Examples](#api-credential-examples)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)
- [Production Deployment](#production-deployment)
- [CI/CD Integration](#cicd-integration)

## Quick Start

### 1. Set Up Environment

```bash
# Navigate to the linkedin-importer directory
cd linkedin-importer

# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### 2. Configure Credentials

Edit your `.env` file:

```bash
# LinkedIn API (get from https://www.linkedin.com/developers/apps)
LINKEDIN_API_KEY=your-api-key
LINKEDIN_API_SECRET=your-api-secret

# Database (your portfolio backend database)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=portfolio
DB_USER=postgres
DB_PASSWORD=your-password
```

### 3. Run the Import

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe
```

## Basic Import Scenarios

### Import Using Full Profile URL

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe
```

### Import Using Just the Username

```bash
uv run linkedin-importer johndoe
```

### Import with Verbose Logging

See detailed progress and debugging information:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

Or using the short flag:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe -v
```

## Database Configuration Examples

### Using a Connection URL

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-url "postgresql://postgres:mypassword@localhost:5432/portfolio"
```

### Using Individual Parameters

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host localhost \
  --db-port 5432 \
  --db-name portfolio \
  --db-user postgres \
  --db-password mypassword
```

### Connecting to a Remote Database

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host db.example.com \
  --db-port 5432 \
  --db-name portfolio_prod \
  --db-user app_user \
  --db-password secretpassword
```

### Using Docker PostgreSQL

If you're running PostgreSQL in Docker:

```bash
# Start PostgreSQL container
docker run -d \
  --name portfolio-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=portfolio \
  -p 5432:5432 \
  postgres:15

# Run the importer
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host localhost \
  --db-port 5432 \
  --db-name portfolio \
  --db-user postgres \
  --db-password postgres
```

### Using Environment Variables for Sensitive Data

For security, use environment variables for passwords:

```bash
export DB_PASSWORD="mysecretpassword"
export LINKEDIN_API_KEY="your-api-key"
export LINKEDIN_API_SECRET="your-api-secret"

uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host localhost \
  --db-name portfolio \
  --db-user postgres
```

## API Credential Examples

### Override API Credentials via CLI

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --linkedin-api-key "your-api-key" \
  --linkedin-api-secret "your-api-secret"
```

### Using a Pre-obtained Access Token

Set the token in your `.env` file:

```bash
LINKEDIN_ACCESS_TOKEN=your-oauth-access-token
```

Then run normally:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe
```

## Debugging and Troubleshooting

### Enable Maximum Verbosity

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

This will show:
- Configuration loading steps
- API authentication progress
- Each API request being made
- Profile data being fetched
- Database operations
- Full error stack traces

### Test Database Connection First

Before running the full import, verify your database is accessible:

```bash
# Using psql
psql "postgresql://postgres:password@localhost:5432/portfolio" -c "SELECT 1;"

# Or using the backend's test endpoint if running
curl http://localhost:3001/health
```

### Check API Credentials

Verify your LinkedIn API credentials are valid by checking the Developer Portal:
https://www.linkedin.com/developers/apps

### Dry Run (Not Yet Implemented)

Currently, there's no dry-run mode. For testing, use a separate test database:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-name portfolio_test \
  --verbose
```

## Production Deployment

### Using a Production Environment File

Create a production `.env.production` file:

```bash
LINKEDIN_API_KEY=production-api-key
LINKEDIN_API_SECRET=production-api-secret
DATABASE_URL=postgresql://app_user:securepassword@db.production.com:5432/portfolio_prod
```

Run with the production config:

```bash
# Load production environment
export $(cat .env.production | xargs)

# Run the importer
uv run linkedin-importer https://www.linkedin.com/in/ceo
```

### Running as a Scheduled Job

Example cron job to update profiles weekly:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 cd /path/to/linkedin-importer && /path/to/uv run linkedin-importer https://www.linkedin.com/in/johndoe >> /var/log/linkedin-import.log 2>&1
```

### Using with Systemd

Create a systemd service file `/etc/systemd/system/linkedin-import.service`:

```ini
[Unit]
Description=LinkedIn Profile Importer
After=network.target

[Service]
Type=oneshot
User=app
WorkingDirectory=/opt/linkedin-importer
EnvironmentFile=/opt/linkedin-importer/.env.production
ExecStart=/usr/local/bin/uv run linkedin-importer https://www.linkedin.com/in/johndoe
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create a timer `/etc/systemd/system/linkedin-import.timer`:

```ini
[Unit]
Description=Run LinkedIn Profile Importer weekly

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable linkedin-import.timer
sudo systemctl start linkedin-import.timer
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Update LinkedIn Profile

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays
  workflow_dispatch:  # Allow manual trigger

jobs:
  update-profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        working-directory: linkedin-importer
        run: uv sync

      - name: Run LinkedIn Importer
        working-directory: linkedin-importer
        env:
          LINKEDIN_API_KEY: ${{ secrets.LINKEDIN_API_KEY }}
          LINKEDIN_API_SECRET: ${{ secrets.LINKEDIN_API_SECRET }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

### GitLab CI Example

```yaml
update-linkedin-profile:
  stage: deploy
  image: python:3.11
  script:
    - pip install uv
    - cd linkedin-importer
    - uv sync
    - uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
  variables:
    LINKEDIN_API_KEY: $LINKEDIN_API_KEY
    LINKEDIN_API_SECRET: $LINKEDIN_API_SECRET
    DATABASE_URL: $DATABASE_URL
  only:
    - schedules
```

## Expected Output

### Successful Import

```
INFO     LinkedIn Profile Importer v0.1.0
INFO     Profile URL: https://www.linkedin.com/in/johndoe
INFO     Initializing LinkedIn API client
INFO     Authenticating with LinkedIn API
INFO     Fetching profile data from https://www.linkedin.com/in/johndoe
INFO     Successfully fetched profile for John Doe
INFO     Mapping profile data to database models
INFO     Mapped 5 projects for user john.doe@email.com
INFO     Connecting to database
INFO     Database connection established
INFO     Executing database import
INFO     Import completed successfully
INFO     ============================================================
INFO     Import completed successfully!
INFO       User ID: 123e4567-e89b-12d3-a456-426614174000
INFO       Projects imported: 5
INFO       Technologies linked: 12
INFO     ============================================================
```

### Failed Import

```
ERROR    ============================================================
ERROR    Import failed!
ERROR      Error: LinkedIn authentication failed: Invalid API credentials
ERROR    ============================================================
```

## Tips and Best Practices

1. **Always use environment variables for sensitive data** - Never commit API keys or passwords to version control.

2. **Use a test database first** - Run imports against a test database before production.

3. **Enable verbose mode for debugging** - The `-v` flag provides valuable debugging information.

4. **Set up monitoring for scheduled imports** - Log output and set up alerts for failures.

5. **Respect rate limits** - The importer handles rate limiting automatically, but avoid running it too frequently.

6. **Keep your LinkedIn profile up to date** - The importer only imports what's on your profile.

7. **Review imported data** - After import, review the database to ensure data was mapped correctly.