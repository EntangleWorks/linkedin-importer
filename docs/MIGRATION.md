# Migration Guide: API to Scraper

This guide documents the migration from the old LinkedIn API-based approach to the new scraper-based approach.

> **Note:** The deprecated API code has been completely removed. This document is kept for historical reference and to help users who may have old configurations.

## Why This Change?

The LinkedIn API no longer supports fetching arbitrary public profiles. The API is now restricted to:

- Your own profile data (with OAuth consent)
- Organization pages you manage
- Limited partner integrations

The new scraper-based approach uses browser automation (Selenium WebDriver) to extract profile data directly from LinkedIn's web interface.

## What Changed

### Authentication

| Aspect | Old (API) | New (Scraper) |
|--------|-----------|---------------|
| Method | API Key + Secret | Cookie or Email/Password |
| Environment Variables | `LINKEDIN_API_KEY`, `LINKEDIN_API_SECRET` | `LINKEDIN_COOKIE` or `LINKEDIN_EMAIL`/`LINKEDIN_PASSWORD` |
| 2FA | Not applicable | Supported via manual intervention |
| Token Refresh | Automatic | Manual cookie refresh if expired |

### Configuration

| Old Variable | New Variable | Notes |
|--------------|--------------|-------|
| `LINKEDIN_API_KEY` | (removed) | No longer needed |
| `LINKEDIN_API_SECRET` | (removed) | No longer needed |
| `LINKEDIN_ACCESS_TOKEN` | (removed) | No longer needed |
| (none) | `LINKEDIN_COOKIE` | **Preferred** auth method |
| (none) | `LINKEDIN_EMAIL` | Fallback auth method |
| (none) | `LINKEDIN_PASSWORD` | Fallback auth method |
| (none) | `PROFILE_EMAIL` | **Required** - email for imported profile |
| (none) | `HEADLESS` | Run browser without window |
| (none) | `ACTION_DELAY` | Delay between actions |
| (none) | `SCROLL_DELAY` | Delay between scrolls |
| (none) | `SCREENSHOT_ON_ERROR` | Debug screenshots |

### CLI Options

| Old Option | New Option | Notes |
|------------|------------|-------|
| `--linkedin-api-key` | (deprecated) | Will be removed |
| `--linkedin-api-secret` | (deprecated) | Will be removed |
| (none) | `--linkedin-cookie` | Preferred auth |
| (none) | `--linkedin-email` | Fallback auth |
| (none) | `--linkedin-password` | Fallback auth |
| (none) | `--profile-email` | **Required** |
| (none) | `--headless`/`--no-headless` | Browser visibility |
| (none) | `--action-delay` | Anti-detection |
| (none) | `--screenshot-on-error` | Debug mode |

### Data Differences

The scraper extracts data from LinkedIn's web interface, which may differ slightly from the API:

| Data Field | API | Scraper | Notes |
|------------|-----|---------|-------|
| Email | Available | **Not available** | Must be provided via `--profile-email` |
| Profile Picture | URL provided | URL extracted | Same result |
| Experience | Structured JSON | Parsed from HTML | Same data, different source |
| Education | Structured JSON | Parsed from HTML | Same data, different source |
| Skills | With endorsement count | Names only | Endorsement counts not visible on page |
| Certifications | Full details | Limited | Some fields may not be visible |
| Publications | Full details | Limited | Some fields may not be visible |

## Migration Steps

### Step 1: Obtain Your LinkedIn Cookie

1. Open Chrome and go to [linkedin.com](https://www.linkedin.com)
2. Log in to your account (complete 2FA if prompted)
3. Open Developer Tools (F12)
4. Navigate to **Application** → **Storage** → **Cookies** → **www.linkedin.com**
5. Find the `li_at` cookie and copy its value

### Step 2: Update Environment Variables

**Before (.env - old API approach):**

```bash
# LinkedIn API Configuration (DEPRECATED)
LINKEDIN_API_KEY=your-api-key
LINKEDIN_API_SECRET=your-api-secret
LINKEDIN_ACCESS_TOKEN=your-access-token

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/portfolio
```

**After (.env - new scraper approach):**

```bash
# LinkedIn Scraper Configuration
LINKEDIN_COOKIE=AQEDAQNv...your-li_at-cookie-value

# Email for the imported profile (LinkedIn doesn't expose emails)
PROFILE_EMAIL=john@example.com

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/portfolio

# Optional: Browser settings
HEADLESS=true
ACTION_DELAY=1.0
SCROLL_DELAY=0.5
SCREENSHOT_ON_ERROR=false
```

### Step 3: Update CLI Commands

**Before (old API approach):**

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --linkedin-api-key "your-key" \
    --linkedin-api-secret "your-secret"
```

**After (new scraper approach):**

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
    --profile-email john@example.com \
    --headless
```

### Step 4: Update CI/CD Pipelines

**Before (GitHub Actions):**

```yaml
env:
  LINKEDIN_API_KEY: ${{ secrets.LINKEDIN_API_KEY }}
  LINKEDIN_API_SECRET: ${{ secrets.LINKEDIN_API_SECRET }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

**After (GitHub Actions):**

```yaml
- name: Install Chrome
  uses: browser-actions/setup-chrome@latest

# ... install uv and dependencies ...

env:
  LINKEDIN_COOKIE: ${{ secrets.LINKEDIN_COOKIE }}
  PROFILE_EMAIL: ${{ secrets.PROFILE_EMAIL }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  HEADLESS: "true"
```

### Step 5: Update Secrets

1. Remove old secrets:
   - `LINKEDIN_API_KEY`
   - `LINKEDIN_API_SECRET`
   - `LINKEDIN_ACCESS_TOKEN`

2. Add new secrets:
   - `LINKEDIN_COOKIE` - Your li_at cookie value
   - `PROFILE_EMAIL` - Email for the imported profile

## Removed Features

The following features have been removed:

### CLI Options (Removed)

```bash
# These options no longer exist
--linkedin-api-key     # Removed - use --linkedin-cookie instead
--linkedin-api-secret  # Removed
```

### Environment Variables (Removed)

```bash
# These environment variables are no longer recognized
LINKEDIN_API_KEY       # Removed - use LINKEDIN_COOKIE instead
LINKEDIN_API_SECRET    # Removed
LINKEDIN_ACCESS_TOKEN  # Removed
```

### Code (Removed)

The following classes and files have been removed:

- `LinkedInConfig` class - replaced by `AuthConfig`
- `linkedin_client.py` module - replaced by `scraper_client.py`
- `LinkedInClient` class - replaced by `LinkedInScraperClient`

## Troubleshooting Migration Issues

### "Authentication requires either LINKEDIN_COOKIE or both LINKEDIN_EMAIL and LINKEDIN_PASSWORD"

You're missing the new authentication configuration. Set one of:

```bash
# Option 1: Cookie (recommended)
export LINKEDIN_COOKIE="your-li_at-cookie"

# Option 2: Email/Password
export LINKEDIN_EMAIL="your@email.com"
export LINKEDIN_PASSWORD="your-password"
```

### "profile_email is required when using the scraper"

LinkedIn doesn't expose email addresses. You must provide the email:

```bash
uv run linkedin-importer https://linkedin.com/in/johndoe \
    --profile-email john@example.com
```

### "ChromeDriver not found"

The scraper needs Chrome and ChromeDriver:

1. Install Chrome browser
2. Let `webdriver-manager` auto-download ChromeDriver, or
3. Set `CHROMEDRIVER_PATH=/path/to/chromedriver`

### "Cookie expired" after migration

Cookies expire periodically. Get a fresh cookie:

1. Log into LinkedIn in your browser
2. Get a new `li_at` cookie from DevTools
3. Update your `LINKEDIN_COOKIE` environment variable

### Import completes but some data is missing

The scraper extracts what's visible on the profile page:

- **Collapsed sections**: The scraper scrolls to load content, but some sections may be collapsed
- **Limited visibility**: Some profile sections are only visible to connections
- **Privacy settings**: The profile owner may have hidden certain sections

## Getting Help

If you encounter issues:

1. **Check the README**: [README.md](../README.md) has detailed setup instructions
2. **Review examples**: [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) has common use cases
3. **Manual testing**: [manual_testing_checklist.md](manual_testing_checklist.md) can help debug issues
4. **Open an issue**: Report bugs or request help on GitHub