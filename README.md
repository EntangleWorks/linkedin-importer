# LinkedIn Profile Importer

A standalone CLI tool that fetches professional profile data from LinkedIn and populates a PostgreSQL database for your portfolio website.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [CLI Arguments](#cli-arguments)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Advanced Examples](#advanced-examples)
- [Database Schema Mapping](#database-schema-mapping)
- [Error Handling](#error-handling)
- [Development](#development)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

The LinkedIn Profile Importer is a Python CLI tool that automates the process of importing your LinkedIn profile data into a PostgreSQL database. It's designed to work with the portfolio backend service, mapping LinkedIn profile sections to the appropriate database tables.

## Features

- **Complete Profile Import**: Fetches all profile sections including work experience, education, skills, certifications, publications, and volunteer work
- **Automatic Mapping**: Intelligently maps LinkedIn data to your portfolio database schema
- **Transaction Safety**: All database operations are wrapped in transactions with automatic rollback on failure
- **Rate Limit Handling**: Respects LinkedIn API rate limits with automatic retry and exponential backoff
- **Flexible Configuration**: Supports both environment variables and CLI arguments
- **Verbose Logging**: Optional detailed logging for debugging and monitoring

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL database (for the portfolio backend)
- LinkedIn API credentials (API key and secret)

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

## Configuration

The importer can be configured through environment variables, a `.env` file, or CLI arguments. CLI arguments take precedence over environment variables.

### Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LINKEDIN_API_KEY` | Your LinkedIn API application key | `86a5xyz123...` |
| `LINKEDIN_API_SECRET` | Your LinkedIn API application secret | `AbCdEf123...` |

#### Database Configuration

You can configure the database using either a connection URL or individual parameters:

**Option 1: Connection URL**

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/portfolio` |

**Option 2: Individual Parameters**

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DB_HOST` | Database host | `localhost` | `db.example.com` |
| `DB_PORT` | Database port | `5432` | `5432` |
| `DB_NAME` | Database name | (required) | `portfolio` |
| `DB_USER` | Database username | (required) | `postgres` |
| `DB_PASSWORD` | Database password | (required) | `mysecretpassword` |

#### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LINKEDIN_ACCESS_TOKEN` | Pre-obtained OAuth access token | (none) |

### CLI Arguments

All configuration can also be provided via CLI arguments:

| Argument | Description | Environment Fallback |
|----------|-------------|---------------------|
| `PROFILE_URL` | LinkedIn profile URL or username (required) | - |
| `--db-url` | Database connection URL | `DATABASE_URL` |
| `--db-host` | Database host | `DB_HOST` |
| `--db-port` | Database port | `DB_PORT` |
| `--db-name` | Database name | `DB_NAME` |
| `--db-user` | Database user | `DB_USER` |
| `--db-password` | Database password | `DB_PASSWORD` |
| `--linkedin-api-key` | LinkedIn API key | `LINKEDIN_API_KEY` |
| `--linkedin-api-secret` | LinkedIn API secret | `LINKEDIN_API_SECRET` |
| `--verbose`, `-v` | Enable verbose logging | `false` |

## Usage

### Basic Usage

```bash
# Import a LinkedIn profile using environment variables for credentials
uv run linkedin-importer https://www.linkedin.com/in/johndoe

# With verbose logging
uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

### Advanced Examples

#### Override Database Credentials

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host localhost \
  --db-port 5432 \
  --db-name portfolio \
  --db-user postgres \
  --db-password mypassword
```

#### Use Database URL

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-url "postgresql://postgres:mypassword@localhost:5432/portfolio"
```

#### Override LinkedIn API Credentials

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --linkedin-api-key "your-api-key" \
  --linkedin-api-secret "your-api-secret"
```

#### Full Configuration via CLI

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe \
  --db-host db.example.com \
  --db-port 5432 \
  --db-name portfolio_prod \
  --db-user app_user \
  --db-password secretpassword \
  --linkedin-api-key "your-api-key" \
  --linkedin-api-secret "your-api-secret" \
  --verbose
```

#### Using a Username Instead of Full URL

```bash
# Both formats are supported
uv run linkedin-importer johndoe
uv run linkedin-importer https://www.linkedin.com/in/johndoe
```

## Database Schema Mapping

The importer maps LinkedIn profile data to the portfolio database schema as follows:

### Users Table

LinkedIn basic profile information is mapped to the `users` table:

| LinkedIn Field | Database Column | Description |
|----------------|-----------------|-------------|
| `firstName` + `lastName` | `name` | Full name |
| `emailAddress` | `email` | Email address |
| `profilePicture` | `avatar_url` | Profile picture URL |
| Composite | `bio` | See Bio Composition below |

#### Bio Composition

The `bio` field is composed from multiple LinkedIn sections:

1. **Headline** - Professional headline
2. **Summary** - About section
3. **Location & Industry** - Metadata
4. **Education** - Formatted education history
5. **Languages** - Language proficiencies
6. **Honors & Awards** - Achievements and recognitions

### Projects Table

Multiple LinkedIn sections are mapped to the `projects` table:

#### Work Experience → Projects

| LinkedIn Field | Database Column | Notes |
|----------------|-----------------|-------|
| `title` + `companyName` | `title` | Format: "Title at Company" |
| Generated | `slug` | URL-friendly slug from title |
| `description` | `description` | Short description |
| `location`, `employmentType`, `responsibilities` | `long_description` | Detailed description |
| `companyLogoUrl` | `image_url` | Company logo |
| `companyUrl` | `live_url` | Company website |
| - | `github_url` | Always null for LinkedIn imports |
| `startDate` | `created_at` | Position start date |
| `endDate` or now | `updated_at` | Position end date |

#### Certifications → Projects

| LinkedIn Field | Database Column | Notes |
|----------------|-----------------|-------|
| `name` | `title` | Prefixed with "Certification: " |
| `authority` | `description` | Issuing organization |
| `licenseNumber` | `long_description` | License details |
| `url` | `live_url` | Certification URL |

#### Publications → Projects

| LinkedIn Field | Database Column | Notes |
|----------------|-----------------|-------|
| `name` | `title` | Prefixed with "Publication: " |
| `publisher` | `description` | Publisher name |
| `description` | `long_description` | Publication description |
| `url` | `live_url` | Publication URL |

#### Volunteer Experience → Projects

| LinkedIn Field | Database Column | Notes |
|----------------|-----------------|-------|
| `role` + `organization` | `title` | Format: "Volunteer: Role at Organization" |
| `description` | `description` | Role description |
| `cause`, `description` | `long_description` | Detailed description |

### Project Technologies Table

LinkedIn skills are linked to the most recent projects:

| LinkedIn Field | Database Column | Notes |
|----------------|-----------------|-------|
| `name` | `technology` | Skill/technology name |
| - | `project_id` | Links to recent projects |

Skills are:
- Sorted by endorsement count (highest first)
- Linked to the 3 most recent projects
- Deduplicated and normalized

## Error Handling

The importer provides descriptive error messages for common issues:

| Error Type | Description | Resolution |
|------------|-------------|------------|
| `ConfigError` | Missing or invalid configuration | Check environment variables or CLI arguments |
| `AuthError` | LinkedIn authentication failed | Verify API credentials |
| `APIError` | LinkedIn API request failed | Check network, rate limits, or profile URL |
| `ValidationError` | Profile data validation failed | Ensure profile has required fields |
| `DatabaseError` | Database operation failed | Check database connection and permissions |

### Retry Behavior

- Network failures are retried up to 3 times with exponential backoff (1s, 2s, 4s)
- Rate limit responses (429) trigger automatic waiting per `Retry-After` header
- All database operations are transactional - failures trigger automatic rollback

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=linkedin_importer

# Run specific test file
uv run pytest tests/test_config_properties.py

# Run tests matching a pattern
uv run pytest -k "test_config"
```

### Test Categories

- **Property-based tests**: Using Hypothesis for comprehensive input testing
- **Unit tests**: Testing individual components in isolation
- **Integration tests**: Testing component interactions

### Code Quality

```bash
# Type checking (if mypy is installed)
uv run mypy src/

# Linting (if ruff is installed)
uv run ruff check src/
```

## Project Structure

```
linkedin-importer/
├── src/
│   └── linkedin_importer/        # Main package
│       ├── __init__.py           # Package initialization
│       ├── cli.py                # CLI entry point (Click)
│       ├── config.py             # Configuration models (Pydantic)
│       ├── db_models.py          # Database models
│       ├── errors.py             # Custom error classes
│       ├── linkedin_client.py    # LinkedIn API client
│       ├── logging_config.py     # Logging configuration
│       ├── mapper.py             # LinkedIn → Database mapper
│       ├── models.py             # LinkedIn data models
│       ├── orchestrator.py       # Import pipeline orchestration
│       ├── repository.py         # Database repository
│       └── validation.py         # Data validation utilities
├── tests/                        # Test suite
│   ├── test_config_*.py          # Configuration tests
│   ├── test_linkedin_client_*.py # API client tests
│   ├── test_mapper_*.py          # Mapper tests
│   ├── test_repository_*.py      # Repository tests
│   └── test_validation_*.py      # Validation tests
├── .env.example                  # Example environment variables
├── pyproject.toml                # Project configuration
├── uv.lock                       # Lock file
└── README.md                     # This file
```

## Troubleshooting

### Common Issues

#### "Configuration error: Either database URL or all of (name, user, password) must be provided"

Ensure you have either:
- Set `DATABASE_URL` environment variable, OR
- Set all of `DB_NAME`, `DB_USER`, and `DB_PASSWORD`

#### "LinkedIn authentication failed"

1. Verify your API credentials are correct
2. Check that your LinkedIn API application is active
3. Ensure you have the required API permissions

#### "Rate limit exceeded"

The importer will automatically wait and retry. If the issue persists:
- Wait a few minutes before retrying
- Check your API quota in the LinkedIn Developer Portal

#### "Profile not found" (404)

- Verify the LinkedIn profile URL is correct
- Ensure the profile is public or you have access permissions

#### Database connection errors

1. Verify the database is running and accessible
2. Check firewall rules if connecting to a remote database
3. Verify credentials are correct
4. Ensure the database and required tables exist

### Debug Mode

Enable verbose logging to get detailed information:

```bash
uv run linkedin-importer https://www.linkedin.com/in/johndoe --verbose
```

This will show:
- Configuration loading details
- API request/response information
- Database operations progress
- Detailed error stack traces

## License

MIT