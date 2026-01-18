# LinkedIn Profile Importer

A CLI tool that imports your LinkedIn profile data into a PostgreSQL database using browser automation. This tool is designed to work with the portfolio backend service, mapping LinkedIn profile sections to the appropriate database tables.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Authentication](#authentication)
  - [Cookie Authentication (Recommended)](#cookie-authentication-recommended)
  - [Email/Password Authentication](#emailpassword-authentication)
  - [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [CLI Options](#cli-options)
- [Usage](#usage)
  - [Quick Start](#quick-start)
  - [Examples](#examples)
- [Database Schema Mapping](#database-schema-mapping)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Project Structure](#project-structure)
- [Migration from API](#migration-from-api)
- [License](#license)

## Overview

The LinkedIn Profile Importer uses Selenium WebDriver to scrape your LinkedIn profile data and imports it into a PostgreSQL database. It supports two authentication methods: cookie injection (recommended) and email/password login.

> **Note:** This tool replaces the previous API-based approach, which is no longer functional due to LinkedIn API restrictions. See [Migration from API](#migration-from-api) for details.

## Features

- **Browser-Based Scraping**: Uses Selenium WebDriver with Chrome for reliable data extraction
- **Cookie Authentication**: Bypass 2FA and CAPTCHA by using your existing LinkedIn session cookie
- **Email/Password Fallback**: Traditional login with support for manual 2FA intervention
- **Complete Profile Import**: Fetches work experience, education, skills, and more
- **Automatic Mapping**: Intelligently maps LinkedIn data to your portfolio database schema
- **Transaction Safety**: All database operations are wrapped in transactions with automatic rollback
- **Headless Mode**: Run in headless mode for server/CI environments
- **Anti-Detection**: Configurable delays and human-like behavior to avoid detection
- **Screenshot on Error**: Optional screenshot capture for debugging failed scrapes

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Google Chrome browser (latest version recommended)
- PostgreSQL database (for the portfolio backend)
- A LinkedIn account

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install the LinkedIn Importer

```bash
# Clone the repository
git clone https://github.com/yourusername/nextjs-portfolio-template.git
cd nextjs-portfolio-template/linkedin-importer

# Install dependencies
uv sync

# Install with development dependencies (for testing)
uv sync --all-groups
```

### ChromeDriver

ChromeDriver is managed automatically via `webdriver-manager`. You can override the browser or driver it uses via environment variables:

```bash
# Use a specific Chrome/Chromium binary (helpful for snap/flatpak or custom installs)
export CHROME_BINARY=/snap/bin/chromium

# Pin a driver version to match your Chrome/Chromium build
# e.g. Chromium 143.0.7499.169 snap => export CHROMEDRIVER_VERSION=$(chromium --version | awk '{print $2}')
export CHROMEDRIVER_VERSION=114.0.5735.90

# Or point directly at a downloaded chromedriver
export CHROMEDRIVER_PATH=/path/to/chromedriver
```

If Chrome fails to start with `DevToolsActivePort` errors (common with snap Chromium), set `CHROME_BINARY` to your Chromium binary and pin `CHROMEDRIVER_VERSION` to that browser version.

## Authentication

LinkedIn requires authentication to access profile data. Two methods are supported:

### Cookie Authentication (Recommended)

Cookie authentication uses your existing LinkedIn session cookie (`li_at`) to authenticate. This method:

- ✅ **Bypasses 2FA completely**
- ✅ **Avoids CAPTCHA challenges**
- ✅ **Is faster and more reliable**
- ✅ **Works in headless mode**

#### How to Obtain the `li_at` Cookie

1. **Open Chrome** and navigate to [linkedin.com](https://www.linkedin.com)
2. **Log in** to your LinkedIn account (complete any 2FA if prompted)
3. **Open Developer Tools** (press F12 or right-click → Inspect)
4. **Navigate to Application tab** → Storage → Cookies → `www.linkedin.com`
5. **Find the `li_at` cookie** and copy its value

![Cookie Location](docs/images/cookie-location.png) *(if you have this image)*

The cookie value looks like: `AQEDAQNv...` (a long alphanumeric string)

#### Set the Cookie

```bash
# Via environment variable (recommended for security)
export LINKEDIN_COOKIE="AQEDAQNv..."

# Or in your .env file
LINKEDIN_COOKIE=AQEDAQNv...
```

> **Security Note:** Never commit your `li_at` cookie to version control. Add `.env` to your `.gitignore`.

#### Cookie Validity

- The `li_at` cookie typically lasts for **1 year**
- LinkedIn may invalidate it earlier if unusual activity is detected
- If authentication fails, obtain a fresh cookie

### Email/Password Authentication

If you prefer not to use cookie authentication, you can provide your LinkedIn credentials:

```bash
export LINKEDIN_EMAIL="your.email@example.com"
export LINKEDIN_PASSWORD="your-password"
```

**Important considerations:**

- ⚠️ May trigger 2FA or CAPTCHA challenges
- ⚠️ Requires visible browser mode for manual intervention
- ⚠️ Less reliable than cookie authentication
- ⚠️ Not recommended for headless/server environments

### Two-Factor Authentication (2FA)

When using email/password authentication with 2FA enabled:

1. **Run in visible browser mode** (don't use `--headless`)
2. The browser will show the 2FA challenge
3. **Enter your verification code** manually
4. The script will detect successful login and continue

```bash
# Run with visible browser for 2FA
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --no-headless
```

The script waits up to 120 seconds for 2FA completion.

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

#### Authentication (Required)

| Variable | Description | Required |
|----------|-------------|----------|
| `LINKEDIN_COOKIE` | LinkedIn `li_at` session cookie (preferred) | One of these |
| `LINKEDIN_EMAIL` | LinkedIn email address (fallback) | pairs is |
| `LINKEDIN_PASSWORD` | LinkedIn password (fallback) | required |

#### Profile (Required for Scraping)

| Variable | Description | Required |
|----------|-------------|----------|
| `PROFILE_EMAIL` | Email to associate with imported profile | Yes |

> **Note:** LinkedIn does not expose email addresses in profiles, so you must specify the email for the imported user record.

#### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/portfolio` |

Or use individual parameters:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | (required) |
| `DB_USER` | Database username | (required) |
| `DB_PASSWORD` | Database password | (required) |

#### Browser Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `HEADLESS` | Run browser in headless mode | `false` |
| `CHROME_BINARY` | Path to Chrome/Chromium binary (useful for snap/flatpak) | (system default) |
| `CHROMEDRIVER_VERSION` | Pin a specific chromedriver version to match your browser | `latest` |
| `CHROMEDRIVER_PATH` | Path to ChromeDriver (skip auto-download) | (auto-download) |
| `ACTION_DELAY` | Delay between actions (seconds) | `1.0` |
| `SCROLL_DELAY` | Delay between scrolls (seconds) | `0.5` |
| `PAGE_LOAD_TIMEOUT` | Page load timeout (seconds) | `30` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `SCREENSHOT_ON_ERROR` | Capture screenshots on error | `false` |

### CLI Options

```bash
uv run linkedin-importer --help
```

| Option | Description |
|--------|-------------|
| `--linkedin-cookie` | LinkedIn li_at session cookie |
| `--linkedin-email` | LinkedIn email (fallback auth) |
| `--linkedin-password` | LinkedIn password (fallback auth) |
| `--profile-email` | Email for imported profile (required) |
| `--headless` / `--no-headless` | Browser visibility |
| `--action-delay` | Delay between actions (seconds) |
| `--scroll-delay` | Delay between scrolls (seconds) |
| `--page-load-timeout` | Page load timeout (seconds) |
| `--max-retries` | Maximum retry attempts |
| `--screenshot-on-error` | Capture screenshot on error |
| `--chromedriver-path` | Path to ChromeDriver |
| `--db-url` | Database connection URL |
| `--db-host`, `--db-port`, etc. | Individual database params |
| `--verbose`, `-v` | Enable verbose logging |

## Usage

### Quick Start

1. **Set up your environment:**
   ```bash
   cd linkedin-importer
   cp .env.example .env
   # Edit .env with your cookie and database settings
   ```

2. **Run the importer:**
   ```bash
   uv run linkedin-importer https://linkedin.com/in/johndoe \
       --profile-email john@example.com
   ```

### Examples

#### Cookie Authentication (Recommended)

```bash
# Set cookie and run
export LINKEDIN_COOKIE="AQEDAQNv..."
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --headless
```

#### Email/Password with 2FA

```bash
# Visible browser for manual 2FA intervention
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --linkedin-email user@example.com \
    --linkedin-password mypassword \
    --profile-email john@example.com \
    --no-headless
```

#### With Custom Delays (Safer)

```bash
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --action-delay 2.0 \
    --scroll-delay 1.0 \
    --headless
```

#### Debug Mode with Screenshots

```bash
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --screenshot-on-error \
    --verbose \
    --no-headless
```

#### Using Docker PostgreSQL

```bash
# Start the database
docker compose up -d postgres

# Run import
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --db-url "postgresql://portfolio_user:portfolio_pass@localhost:5432/portfolio"
```

## Database Schema Mapping

The importer maps LinkedIn profile data to the portfolio database schema:

### Users Table

| LinkedIn Field | Database Column |
|----------------|-----------------|
| First + Last Name | `name` |
| `profile_email` (CLI arg) | `email` |
| Profile Picture | `avatar_url` |
| Headline + Summary | `bio` |

### Projects Table (from Work Experience)

| LinkedIn Field | Database Column |
|----------------|-----------------|
| Title + Company | `title` |
| Description | `description` |
| Full Description | `long_description` |
| Company Logo | `image_url` |
| Company URL | `live_url` |
| Start Date | `created_at` |
| End Date | `updated_at` |

### Project Technologies (from Skills)

Skills are linked to the most recent projects as technologies.

## Error Handling

| Error | Description | Resolution |
|-------|-------------|------------|
| `CookieExpired` | The li_at cookie is no longer valid | Obtain a fresh cookie from LinkedIn |
| `AuthError` | Authentication failed | Check credentials or cookie |
| `TwoFactorRequired` | 2FA challenge presented | Use `--no-headless` and complete 2FA manually |
| `ProfileNotFound` | Profile URL is invalid or private | Verify the URL and profile visibility |
| `ScrapingBlocked` | LinkedIn detected automation | Wait and retry with higher delays |
| `BrowserError` | ChromeDriver or browser issue | Check Chrome and ChromeDriver versions |

### Retry Behavior

- Failed operations are retried up to 3 times with exponential backoff
- Page loads timeout after 30 seconds (configurable)
- All database operations are transactional

## Troubleshooting

### "Cookie expired" or "Invalid cookie"

1. Log out and back into LinkedIn in your browser
2. Obtain a fresh `li_at` cookie
3. Update your environment variable or `.env` file

### "ChromeDriver not found"

The importer uses `webdriver-manager` to auto-download ChromeDriver. If this fails:

1. **Install Chrome** if not already installed
2. **Manually download ChromeDriver** matching your Chrome version from [chromedriver.chromium.org](https://chromedriver.chromium.org/)
3. **Set the path:** `export CHROMEDRIVER_PATH=/path/to/chromedriver`

### "Profile not found" (404)

- Verify the LinkedIn profile URL is correct
- Ensure the profile is public or you have access
- Check for typos in the username

### 2FA timeout

If the 2FA timeout is too short:
1. Run with `--no-headless` to see the browser
2. Complete 2FA within 120 seconds
3. Consider using cookie authentication to bypass 2FA entirely

### LinkedIn blocking/rate limiting

If LinkedIn detects automation:
1. **Increase delays:** `--action-delay 3.0 --scroll-delay 2.0`
2. **Wait before retrying:** Wait at least 1 hour
3. **Use a fresh cookie:** Obtain a new `li_at` cookie
4. **Avoid frequent imports:** Limit to once per day

### Database connection errors

1. Verify PostgreSQL is running: `docker compose up -d postgres`
2. Check connection parameters in `.env`
3. Ensure database and tables exist (run migrations)

### Debug mode

Enable verbose logging for detailed diagnostics:

```bash
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --verbose \
    --screenshot-on-error \
    --no-headless
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_scraper_adapter.py

# Run with coverage
uv run pytest --cov=linkedin_importer
```

### Code Quality

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

### Manual Testing

See [docs/manual_testing_checklist.md](docs/manual_testing_checklist.md) for comprehensive manual testing procedures.

## Project Structure

```
linkedin-importer/
├── src/
│   └── linkedin_importer/
│       ├── __init__.py           # Package initialization
│       ├── cli.py                # CLI entry point (Click)
│       ├── config.py             # Configuration models (Pydantic)
│       ├── db_models.py          # Database models
│       ├── errors.py             # Custom error classes
│       ├── scraper_client.py     # LinkedIn scraper client (Selenium)
│       ├── scraper_adapter.py    # Data adapter (Person → LinkedInProfile)
│       ├── scraper_errors.py     # Scraper-specific error classes
│       ├── logging_config.py     # Logging configuration
│       ├── mapper.py             # LinkedIn → Database mapper
│       ├── models.py             # LinkedIn data models
│       ├── orchestrator.py       # Import pipeline orchestration
│       ├── repository.py         # Database repository
│       └── validation.py         # Data validation utilities
├── tests/                        # Test suite
├── docs/                         # Documentation
├── .env.example                  # Example environment variables
├── pyproject.toml                # Project configuration
└── README.md                     # This file
```

## Migration from API

The previous version of this tool used LinkedIn's API, which no longer supports fetching arbitrary public profiles. The new scraper-based approach:

### What Changed

| Aspect | Old (API) | New (Scraper) |
|--------|-----------|---------------|
| Authentication | API Key + Secret | Cookie or Email/Password |
| Data Source | LinkedIn API | Browser automation |
| Rate Limits | API quotas | Detection-based |
| 2FA | N/A | Manual intervention supported |
| Headless | N/A | Supported |

### Deprecated Options

The following options are deprecated and will be removed in a future version:

- `--linkedin-api-key`
- `--linkedin-api-secret`
- `LINKEDIN_API_KEY` environment variable
- `LINKEDIN_API_SECRET` environment variable
- `LINKEDIN_ACCESS_TOKEN` environment variable

### Migration Steps

1. **Obtain your `li_at` cookie** (see [Cookie Authentication](#cookie-authentication-recommended))
2. **Update your `.env` file:**
   ```bash
   # Remove these (deprecated)
   # LINKEDIN_API_KEY=...
   # LINKEDIN_API_SECRET=...
   
   # Add these (new)
   LINKEDIN_COOKIE=your_li_at_cookie
   PROFILE_EMAIL=your@email.com
   ```
3. **Run the importer** as before - the CLI interface is compatible

For more details, see [docs/MIGRATION.md](docs/MIGRATION.md).

## License

MIT