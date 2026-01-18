# Get your Chromium/Chrome version (example commands)
# chromium --version    # or
# google-chrome --version

# Set these to match your environment
export CHROME_BINARY=/snap/bin/chromium            # adjust to your actual chrome/chromium path
# Parse the version number from outputs like "Chromium 143.0.7499.169 snap"
export CHROMEDRIVER_VERSION=$(chromium --version | awk '{print $2}')
# OR use a manual driver: export CHROMEDRIVER_PATH=/path/to/chromedriver

# Use your LinkedIn cookie (keep private)
export LINKEDIN_COOKIE="AQEDASZOgfMDTaquAAABm7g_xakAAAGb3ExJqU4AU0PkPw4mDW0CakARqvLMFAIuVSqh2QkNWMizb3bIqH87_8vJSNg4MGdzzVB8XqCb54I8cDtTu7DX-2HcqBVbM3YVuzZwvLkg03FVwuugXBelQdBz"

# Run with visible browser for debugging and screenshots on error
cd nextjs-portfolio-template/linkedin-importer
uv run linkedin-importer https://linkedin.com/in/francois-van-wyk \
  --profile-email francois@example.com \
  --db-url "postgresql://portfolio_user:dev_password_change_in_production@localhost:5432/portfolio" \
  --verbose \
  --screenshot-on-error
