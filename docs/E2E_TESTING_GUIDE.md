# End-to-End Browser Testing Guide

## Overview

This guide explains how to run browser-based end-to-end (E2E) tests for the FlexCube AI Assistant application. These tests verify the complete user experience through a real browser.

## Prerequisites

### 1. Install Dependencies

```bash
cd /var/www/chatbot_FC
source venv/bin/activate
pip install selenium webdriver-manager
```

### 2. Install Chrome/Chromium Browser

**On Rocky Linux / RHEL:**

```bash
# Install Chromium
sudo dnf install chromium -y

# Or install Google Chrome
sudo dnf install google-chrome-stable -y
```

**Verify installation:**
```bash
chromium --version
# or
google-chrome --version
```

### 3. Install ChromeDriver (if not using webdriver-manager)

The tests use `webdriver-manager` which automatically downloads ChromeDriver, but you can also install it manually:

```bash
# Option 1: Use webdriver-manager (automatic - recommended)
# Already handled by the test code

# Option 2: Manual installation
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
CHROME_VERSION=$(cat LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

## Test Configuration

### Environment Variables

You can configure test parameters using environment variables:

```bash
export TEST_BASE_URL="http://localhost:8000"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="Admin123!"
export TEST_USERNAME="test_user"
export TEST_PASSWORD="User123!"
```

### Default Values

- **Base URL:** `http://localhost:8000`
- **Admin Username:** `admin`
- **Admin Password:** `Admin123!`
- **Test Username:** `test_user`
- **Test Password:** `User123!`

## Running Tests

### Run All E2E Tests

```bash
cd /var/www/chatbot_FC
source venv/bin/activate
python -m pytest src/tests/e2e/test_browser_e2e.py -v
```

### Run Specific Test Classes

```bash
# Test authentication only
pytest src/tests/e2e/test_browser_e2e.py::TestAuthentication -v

# Test admin access only
pytest src/tests/e2e/test_browser_e2e.py::TestAdminAccess -v

# Test conversation history
pytest src/tests/e2e/test_browser_e2e.py::TestConversationHistory -v
```

### Run Specific Test Cases

```bash
# Test login page loads
pytest src/tests/e2e/test_browser_e2e.py::TestAuthentication::test_login_page_loads -v

# Test admin dashboard access
pytest src/tests/e2e/test_browser_e2e.py::TestAdminAccess::test_admin_dashboard_accessible -v
```

### Run with Screenshots (Non-Headless Mode)

To see the browser in action, modify the test file to remove `--headless` option:

```python
# In test_browser_e2e.py, comment out:
# chrome_options.add_argument("--headless")
```

Then run tests normally.

## Test Coverage

### ✅ Authentication Tests
- Login page loads correctly
- Successful login with valid credentials
- Failed login with invalid credentials
- Logout functionality

### ✅ Main Page Tests
- Main page loads after login
- User profile displayed
- Admin link visible for admin users
- Admin link NOT visible for regular users

### ✅ Conversation History Tests
- Conversation history section exists
- User-specific history (each user sees only their own)

### ✅ Admin Access Tests
- Admin dashboard accessible to admins
- Admin dashboard requires authentication
- Admin link navigation works
- Admin users page accessible

### ✅ Query Functionality Tests
- Query input field exists
- Query submission works

## Test Execution Time

- **Fast tests:** 1-5 seconds each (UI checks, navigation)
- **Medium tests:** 5-15 seconds (login, page loads)
- **Slow tests:** 20-120 seconds (query submission - depends on RAG pipeline)

**Total estimated time:** 5-10 minutes for full test suite

## Troubleshooting

### Chrome/Chromium Not Found

**Error:** `selenium.common.exceptions.WebDriverException: Message: 'chromedriver' executable needs to be in PATH`

**Solution:**
```bash
# Install Chrome/Chromium
sudo dnf install chromium -y

# Or use webdriver-manager (automatic)
pip install webdriver-manager
```

### Permission Denied

**Error:** `Permission denied: '/tmp/.org.chromium.Chromium.*'`

**Solution:**
```bash
# Run with proper permissions or use --no-sandbox flag (already in test code)
```

### Connection Refused

**Error:** `selenium.common.exceptions.WebDriverException: Message: unknown error: net::ERR_CONNECTION_REFUSED`

**Solution:**
1. Ensure the application is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Start the application if needed:
   ```bash
   cd /var/www/chatbot_FC
   source venv/bin/activate
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

### Test Users Don't Exist

**Error:** Login fails for test users

**Solution:**
1. Create test users:
   ```bash
   # Admin user should already exist (from seed script)
   python scripts/seed_admin_user.py
   
   # Create test user if needed
   # (Use admin UI or API to create test_user)
   ```

### Headless Mode Issues

If tests fail in headless mode, try running without headless:

1. Edit `src/tests/e2e/test_browser_e2e.py`
2. Comment out: `chrome_options.add_argument("--headless")`
3. Run tests again

## Continuous Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install selenium webdriver-manager
      - name: Install Chrome
        run: |
          sudo apt-get update
          sudo apt-get install -y chromium-browser
      - name: Run E2E tests
        run: |
          pytest src/tests/e2e/test_browser_e2e.py -v
```

## Best Practices

1. **Run tests in order:** Authentication → Main Page → Features
2. **Clean state:** Each test should be independent
3. **Wait for elements:** Use WebDriverWait instead of time.sleep()
4. **Verify assertions:** Check both positive and negative cases
5. **Handle timeouts:** Some operations (like RAG queries) take time

## Adding New Tests

To add new E2E tests:

1. Add test methods to appropriate test class
2. Use fixtures (`logged_in_admin`, `logged_in_user`) for authenticated tests
3. Follow naming convention: `test_<feature>_<scenario>`
4. Add assertions to verify expected behavior
5. Update this guide with new test coverage

## Test Results

After running tests, you'll see output like:

```
src/tests/e2e/test_browser_e2e.py::TestAuthentication::test_login_page_loads PASSED
src/tests/e2e/test_browser_e2e.py::TestAuthentication::test_login_with_valid_credentials PASSED
src/tests/e2e/test_browser_e2e.py::TestMainPage::test_main_page_loads_after_login PASSED
...
```

## Next Steps

1. **Run the tests:** Follow the instructions above
2. **Review failures:** Check error messages and fix issues
3. **Add more tests:** Cover additional user flows
4. **Integrate CI/CD:** Add to your deployment pipeline

