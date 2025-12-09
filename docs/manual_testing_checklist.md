# Manual Testing Checklist for LinkedIn Scraper

This document provides a comprehensive checklist for manually testing the LinkedIn scraper functionality. These tests require real browser interaction and a valid LinkedIn account.

## Prerequisites

Before running manual tests, ensure you have:

- [ ] Python 3.11+ installed
- [ ] Chrome browser installed (latest version recommended)
- [ ] ChromeDriver installed and accessible (or let `webdriver-manager` auto-download)
- [ ] A valid LinkedIn account for testing
- [ ] PostgreSQL database running (for full import tests)

## Environment Setup

1. Copy `.env.example` to `.env`
2. Configure the following environment variables:
   ```bash
   # For cookie authentication (recommended)
   LINKEDIN_COOKIE=your_li_at_cookie_value
   
   # OR for email/password authentication
   LINKEDIN_EMAIL=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   
   # Profile to import
   PROFILE_URL=https://www.linkedin.com/in/your-profile
   PROFILE_EMAIL=your_email@example.com
   
   # Database configuration
   DATABASE_URL=postgresql://user:pass@localhost:5432/portfolio
   ```

---

## Test 1: Cookie Authentication

**Objective:** Verify that cookie authentication works correctly and bypasses 2FA.

### Steps:

1. **Obtain fresh li_at cookie:**
   - [ ] Open Chrome and navigate to [linkedin.com](https://www.linkedin.com)
   - [ ] Log in to your LinkedIn account
   - [ ] Open Developer Tools (F12)
   - [ ] Go to Application > Cookies > www.linkedin.com
   - [ ] Find the `li_at` cookie and copy its value

2. **Set the cookie:**
   - [ ] Set `LINKEDIN_COOKIE` in your `.env` file
   - [ ] Ensure `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` are not set (or comment them out)

3. **Run the importer:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --verbose
   ```

4. **Verify results:**
   - [ ] No 2FA prompt appears
   - [ ] Profile data is scraped successfully
   - [ ] Console shows "Using cookie-based authentication (preferred)"

### Expected Results:
- Authentication completes without user interaction
- Profile data is retrieved and displayed
- No 2FA or CAPTCHA challenges

### Notes:
_Record any observations here:_

---

## Test 2: Full Import Pipeline

**Objective:** Verify the complete import from LinkedIn to database.

### Steps:

1. **Ensure database is running:**
   ```bash
   docker compose up -d postgres
   ```

2. **Run full import:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --verbose
   ```

3. **Verify database entries:**
   ```bash
   docker compose exec postgres psql -U portfolio_user -d portfolio -c "SELECT * FROM users WHERE email = 'your-email@example.com';"
   docker compose exec postgres psql -U portfolio_user -d portfolio -c "SELECT * FROM projects ORDER BY created_at DESC LIMIT 5;"
   ```

4. **Check data accuracy:**
   - [ ] User name matches LinkedIn profile
   - [ ] User bio contains profile headline and summary
   - [ ] Projects match LinkedIn work experiences
   - [ ] Technologies are linked to recent projects

### Expected Results:
- User record created/updated in database
- Projects created for each work experience
- Technologies linked to projects based on skills

### Notes:
_Record any observations here:_

---

## Test 3: Headless Mode

**Objective:** Verify that headless mode works correctly for server environments.

### Steps:

1. **Run with headless flag (default):**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --headless \
       --verbose
   ```

2. **Verify:**
   - [ ] No browser window appears
   - [ ] Scraping completes successfully
   - [ ] Profile data is retrieved

3. **Run with visible browser:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --no-headless \
       --verbose
   ```

4. **Verify:**
   - [ ] Browser window appears
   - [ ] Can observe login and navigation
   - [ ] Browser closes after completion

### Expected Results:
- Both modes complete successfully
- Headless mode has no visible browser
- Visible mode shows browser activity

### Notes:
_Record any observations here:_

---

## Test 4: 2FA Flow (Email/Password Authentication)

**Objective:** Verify that 2FA manual intervention works correctly.

### Prerequisites:
- LinkedIn account with 2FA enabled
- Email/password authentication (not cookie)

### Steps:

1. **Clear cookie and set credentials:**
   ```bash
   # In .env
   # LINKEDIN_COOKIE=  # Comment out or remove
   LINKEDIN_EMAIL=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   ```

2. **Run importer in visible mode:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --no-headless \
       --verbose
   ```

3. **Complete 2FA challenge:**
   - [ ] Observe the browser presenting 2FA challenge
   - [ ] Enter verification code when prompted
   - [ ] Wait for the script to detect successful login

4. **Verify results:**
   - [ ] Script continues after 2FA completion
   - [ ] Profile is scraped successfully
   - [ ] Appropriate log messages appear

### Expected Results:
- 2FA challenge is presented in browser
- User can complete verification manually
- Script detects successful login and continues

### Notes:
_Record any observations here:_

---

## Test 5: Error Handling

### Test 5.1: Expired Cookie

**Steps:**
1. [ ] Set an obviously invalid cookie: `LINKEDIN_COOKIE=invalid_cookie_value`
2. [ ] Run the importer
3. [ ] Verify error message mentions "expired" or "invalid" cookie

### Test 5.2: Non-existent Profile

**Steps:**
1. [ ] Use a non-existent profile URL: `https://www.linkedin.com/in/this-profile-does-not-exist-12345`
2. [ ] Run the importer
3. [ ] Verify error message mentions "not found"

### Test 5.3: Missing Credentials

**Steps:**
1. [ ] Clear all authentication settings (no cookie, no email/password)
2. [ ] Run the importer
3. [ ] Verify error message mentions authentication requirements

### Expected Results:
- Clear, actionable error messages for each scenario
- No stack traces (unless --verbose is used)
- Suggestions for remediation included in errors

### Notes:
_Record any observations here:_

---

## Test 6: Rate Limiting Behavior

**Objective:** Verify that the scraper handles rate limiting gracefully.

### Steps:

1. **Configure delays:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/your-profile \
       --profile-email your-email@example.com \
       --action-delay 2.0 \
       --scroll-delay 1.0 \
       --verbose
   ```

2. **Observe timing:**
   - [ ] Actions are delayed appropriately
   - [ ] No rapid-fire requests
   - [ ] Scroll actions are smooth

3. **Test retry behavior:**
   - [ ] If a temporary error occurs, verify retry with exponential backoff
   - [ ] Check logs for retry messages

### Expected Results:
- Actions are properly delayed
- Human-like scrolling behavior
- Retry logic works as expected

### Notes:
_Record any observations here:_

---

## Test 7: Different Profile Types

### Test 7.1: Profile with Minimal Data

**Steps:**
1. [ ] Find or create a LinkedIn profile with minimal information (just name)
2. [ ] Run the importer
3. [ ] Verify partial data is imported without errors

### Test 7.2: Profile with All Sections

**Steps:**
1. [ ] Use a comprehensive profile (experiences, education, skills, certifications, etc.)
2. [ ] Run the importer
3. [ ] Verify all sections are extracted

### Test 7.3: Profile with Special Characters

**Steps:**
1. [ ] Use a profile with non-ASCII characters (e.g., José García, 日本語 name)
2. [ ] Run the importer
3. [ ] Verify characters are preserved correctly in database

### Expected Results:
- All profile types are handled gracefully
- Partial data doesn't cause failures
- Unicode characters are preserved

### Notes:
_Record any observations here:_

---

## Test 8: Screenshot on Error

**Objective:** Verify that screenshots are captured when errors occur.

### Steps:

1. **Enable screenshot capture:**
   ```bash
   uv run linkedin-importer https://www.linkedin.com/in/non-existent-profile \
       --profile-email test@example.com \
       --screenshot-on-error \
       --no-headless \
       --verbose
   ```

2. **Check for screenshot:**
   - [ ] Look for screenshot files in the working directory
   - [ ] Verify screenshot shows the error state
   - [ ] File naming includes timestamp and error type

### Expected Results:
- Screenshot is captured on error
- Screenshot file is saved locally
- Image shows the browser state at error time

### Notes:
_Record any observations here:_

---

## Results Summary

| Test | Status | Notes |
|------|--------|-------|
| 1. Cookie Authentication | ☐ Pass ☐ Fail | |
| 2. Full Import Pipeline | ☐ Pass ☐ Fail | |
| 3. Headless Mode | ☐ Pass ☐ Fail | |
| 4. 2FA Flow | ☐ Pass ☐ Fail | |
| 5.1 Expired Cookie | ☐ Pass ☐ Fail | |
| 5.2 Non-existent Profile | ☐ Pass ☐ Fail | |
| 5.3 Missing Credentials | ☐ Pass ☐ Fail | |
| 6. Rate Limiting | ☐ Pass ☐ Fail | |
| 7.1 Minimal Profile | ☐ Pass ☐ Fail | |
| 7.2 Full Profile | ☐ Pass ☐ Fail | |
| 7.3 Special Characters | ☐ Pass ☐ Fail | |
| 8. Screenshot on Error | ☐ Pass ☐ Fail | |

---

## Tester Information

- **Tester Name:** ________________
- **Date:** ________________
- **Environment:**
  - OS: ________________
  - Python Version: ________________
  - Chrome Version: ________________
  - ChromeDriver Version: ________________

## Additional Observations

_Record any additional observations, bugs found, or improvement suggestions:_

---

## Known Issues / Limitations

1. **LinkedIn page structure changes:** LinkedIn frequently updates their page layout, which may break selectors. If parsing fails, check for LinkedIn UI updates.

2. **Rate limiting:** Aggressive scraping may trigger LinkedIn's anti-automation measures. Use reasonable delays.

3. **Cookie expiration:** The `li_at` cookie typically expires after 1 year but may be invalidated earlier if LinkedIn detects unusual activity.

4. **2FA timeout:** The default 2FA timeout is 120 seconds. If more time is needed, the user must complete the challenge faster or the script will timeout.