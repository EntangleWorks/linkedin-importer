# Usage Examples

This document provides comprehensive usage examples for the LinkedIn Profile Importer using the new scraper-based approach.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication Examples](#authentication-examples)
  - [Cookie Authentication (Recommended)](#cookie-authentication-recommended)
  - [Email/Password Authentication](#emailpassword-authentication)
  - [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
- [Browser Mode Examples](#browser-mode-examples)
  - [Headless Mode (Production)](#headless-mode-production)
  - [Visible Browser (Debugging)](#visible-browser-debugging)
- [Database Configuration Examples](#database-configuration-examples)
- [Delay and Timing Examples](#delay-and-timing-examples)
- [Error Handling Examples](#error-handling-examples)
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
# LinkedIn Authentication (cookie method - recommended)
LINKEDIN_COOKIE=AQEDAQNv...  # Your li_at cookie value

# Profile to import
PROFILE_EMAIL=john@example.com  # Email for the imported profile

# Database (your portfolio backend database)
DATABASE_URL=postgresql://postgres:password@localhost:5432/portfolio
```

### 3. Run the Import

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe --profile-email john@example.com
```

## Authentication Examples

### Cookie Authentication (Recommended)

Cookie authentication uses your existing LinkedIn session and bypasses 2FA completely.

#### Step 1: Obtain the li_at Cookie

1. Open Chrome and navigate to [linkedin.com](https://www.linkedin.com)
2. Log in to your LinkedIn account
3. Open Developer Tools (F12)
4. Go to **Application** → **Cookies** → **www.linkedin.com**
5. Find the `li_at` cookie and copy its value

#### Step 2: Set the Cookie

**Option A: Environment Variable (recommended for security)**

```bash
export LINKEDIN_COOKIE="AQEDAQNv..."
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com
```

**Option B: CLI Argument**

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --linkedin-cookie "AQEDAQNv..." \
    --profile-email john@example.com
```

**Option C: .env File**

```bash
# .env
LINKEDIN_COOKIE=AQEDAQNv...
PROFILE_EMAIL=john@example.com
DATABASE_URL=postgresql://user:pass@localhost:5432/portfolio
```

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe
```

### Email/Password Authentication

For users who prefer not to use cookie authentication.

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --linkedin-email your.email@example.com \
    --linkedin-password "your-password" \
    --profile-email john@example.com \
    --no-headless  # Visible browser for potential 2FA
```

Or using environment variables:

```bash
export LINKEDIN_EMAIL="your.email@example.com"
export LINKEDIN_PASSWORD="your-password"
export PROFILE_EMAIL="john@example.com"

uv run linkedin-importer https://www.linkedin.com/in/johndoe --no-headless
```

### Two-Factor Authentication (2FA)

When using email/password with 2FA enabled:

```bash
# IMPORTANT: Use --no-headless so you can see and interact with 2FA
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --linkedin-email your.email@example.com \
    --linkedin-password "your-password" \
    --profile-email john@example.com \
    --no-headless \
    --verbose
```

When the browser opens and presents the 2FA challenge:
1. Enter your verification code manually
2. The script will detect successful login and continue
3. You have 120 seconds to complete 2FA

**Pro tip:** To avoid 2FA, use cookie authentication instead!

## Browser Mode Examples

### Headless Mode (Production)

Run without a visible browser window - ideal for servers and automation:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --headless
```

Or set in environment:

```bash
export HEADLESS=true
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com
```

### Visible Browser (Debugging)

See what the browser is doing - useful for debugging:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --no-headless \
    --verbose
```

With screenshot capture on errors:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --no-headless \
    --screenshot-on-error \
    --verbose
```

Screenshots are saved to the current directory with timestamps.

## Database Configuration Examples

### Using a Connection URL

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-url "postgresql://postgres:mypassword@localhost:5432/portfolio"
```

### Using Individual Parameters

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-host localhost \
    --db-port 5432 \
    --db-name portfolio \
    --db-user postgres \
    --db-password mypassword
```

### Connecting to a Remote Database

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-url "postgresql://app_user:securepassword@db.production.com:5432/portfolio_prod"
```

### Using Docker PostgreSQL

```bash
# Start PostgreSQL container
docker run -d \
    --name portfolio-db \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=portfolio \
    -p 5432:5432 \
    postgres:16

# Run the importer
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-url "postgresql://postgres:postgres@localhost:5432/portfolio"
```

### Using docker-compose

```bash
# Start the full stack
docker compose up -d

# Run the importer
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-url "postgresql://portfolio_user:portfolio_pass@localhost:5432/portfolio"
```

## Delay and Timing Examples

### Safe Mode (Slower but Less Detection Risk)

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --action-delay 3.0 \
    --scroll-delay 2.0 \
    --page-load-timeout 60 \
    --headless
```

### Fast Mode (Faster but Higher Detection Risk)

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --action-delay 0.5 \
    --scroll-delay 0.3 \
    --headless
```

### Custom Retry Configuration

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --max-retries 5 \
    --page-load-timeout 45
```

### Using Environment Variables for Timing

```bash
export ACTION_DELAY=2.0
export SCROLL_DELAY=1.0
export PAGE_LOAD_TIMEOUT=45
export MAX_RETRIES=5

uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com
```

## Error Handling Examples

### With Screenshot on Error

Capture the browser state when errors occur:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --screenshot-on-error \
    --verbose
```

### Using Custom ChromeDriver

If automatic ChromeDriver download fails:

```bash
# Download ChromeDriver manually and set path
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --chromedriver-path /usr/local/bin/chromedriver
```

### Handling Expired Cookies

If you get a "cookie expired" error:

```bash
# 1. Log into LinkedIn in your browser
# 2. Get a fresh li_at cookie
# 3. Update and run again
export LINKEDIN_COOKIE="new_cookie_value"
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com
```

## Production Deployment

### Using a Production Environment File

Create `.env.production`:

```bash
LINKEDIN_COOKIE=production-cookie-value
PROFILE_EMAIL=ceo@company.com
DATABASE_URL=postgresql://app_user:securepassword@db.production.com:5432/portfolio_prod
HEADLESS=true
ACTION_DELAY=2.0
SCROLL_DELAY=1.0
SCREENSHOT_ON_ERROR=true
```

Run with production config:

```bash
# Load production environment
set -a && source .env.production && set +a

# Run the importer
uv run linkedin-importer https://www.linkedin.com/in/ceo-profile
```

### Running as a Scheduled Job (Cron)

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 cd /path/to/linkedin-importer && /usr/local/bin/uv run linkedin-importer https://www.linkedin.com/in/johndoe --profile-email john@example.com --headless >> /var/log/linkedin-import.log 2>&1
```

### Using with Systemd

Create `/etc/systemd/system/linkedin-import.service`:

```ini
[Unit]
Description=LinkedIn Profile Importer
After=network.target

[Service]
Type=oneshot
User=app
WorkingDirectory=/opt/linkedin-importer
EnvironmentFile=/opt/linkedin-importer/.env.production
ExecStart=/usr/local/bin/uv run linkedin-importer https://www.linkedin.com/in/johndoe --profile-email john@example.com --headless
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create timer `/etc/systemd/system/linkedin-import.timer`:

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

      - name: Install Chrome
        uses: browser-actions/setup-chrome@latest

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        working-directory: linkedin-importer
        run: uv sync

      - name: Run LinkedIn Importer
        working-directory: linkedin-importer
        env:
          LINKEDIN_COOKIE: ${{ secrets.LINKEDIN_COOKIE }}
          PROFILE_EMAIL: ${{ secrets.PROFILE_EMAIL }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          HEADLESS: "true"
        run: |
          uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

### GitLab CI Example

```yaml
update-linkedin-profile:
  stage: deploy
  image: python:3.11
  before_script:
    - apt-get update && apt-get install -y chromium chromium-driver
    - pip install uv
  script:
    - cd linkedin-importer
    - uv sync
    - uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
  variables:
    LINKEDIN_COOKIE: $LINKEDIN_COOKIE
    PROFILE_EMAIL: $PROFILE_EMAIL
    DATABASE_URL: $DATABASE_URL
    HEADLESS: "true"
    CHROMEDRIVER_PATH: /usr/bin/chromedriver
  only:
    - schedules
```

## Expected Output

### Successful Import

```
INFO     LinkedIn Profile Importer v0.2.0
INFO     Profile URL: https://www.linkedin.com/in/johndoe
INFO     Authentication method: cookie (li_at)
INFO     Initializing browser (headless mode)
INFO     Authenticating with LinkedIn...
INFO     Authentication successful
INFO     Navigating to profile: https://www.linkedin.com/in/johndoe
INFO     Scraping profile data...
INFO     Successfully scraped profile for John Doe
INFO     Mapping profile data to database models
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
ERROR      Error: Cookie authentication failed: Cookie may be expired
ERROR    ============================================================
ERROR    
ERROR    To fix this:
ERROR      1. Log into LinkedIn in your browser
ERROR      2. Open DevTools (F12) → Application → Cookies
ERROR      3. Copy the new 'li_at' cookie value
ERROR      4. Update your LINKEDIN_COOKIE environment variable
```

## Tips and Best Practices

1. **Use cookie authentication** - It's more reliable and bypasses 2FA/CAPTCHA challenges.

2. **Run in headless mode for production** - But use visible mode when debugging issues.

3. **Use appropriate delays** - Higher delays reduce the risk of LinkedIn detecting automation.

4. **Enable screenshots on error** - They help diagnose issues when scraping fails.

5. **Keep your cookie fresh** - If you encounter authentication errors, get a new cookie.

6. **Don't run too frequently** - Limit imports to once per day maximum to avoid detection.

7. **Use environment variables for secrets** - Never hardcode cookies or passwords in scripts.

8. **Test against a test database first** - Verify the import works before running against production.

9. **Monitor your imports** - Set up logging and alerts for scheduled imports.

10. **Keep LinkedIn profile updated** - The importer only imports what's visible on your profile.