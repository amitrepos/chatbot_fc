# How to Test the FlexCube AI Assistant Application

## Quick Start Guide

This guide provides step-by-step instructions for testing the application end-to-end.

## Prerequisites

1. **Application is running:**
   ```bash
   cd /var/www/chatbot_FC
   source venv/bin/activate
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Test users exist:**
   - Admin user: `admin` / `Admin123!`
   - Test user: `test_user` / `User123!` (create if needed)

## Method 1: Manual Browser Testing (Recommended for Quick Checks)

### Step 1: Access the Application

Open your browser and navigate to:
- **Local:** `http://localhost:8000`
- **Remote:** `http://65.109.226.36:8000`

### Step 2: Test Login

1. You should be redirected to `/login` if not authenticated
2. Enter admin credentials:
   - Username: `admin`
   - Password: `Admin123!`
3. Click "Login"
4. You should be redirected to the main page

### Step 3: Test Admin Access

1. After logging in as admin, look for the "👑 Admin" button in the top right
2. Click the "👑 Admin" button
3. You should be taken to `/admin/dashboard`
4. Verify you can see:
   - Admin Dashboard with statistics
   - Navigation links (Users, Analytics, etc.)

### Step 4: Test Conversation History

1. On the main page, scroll down to "Conversation History" section
2. If you've asked questions before, you should see your history
3. Ask a new question:
   - Type: "What is FlexCube?"
   - Click "Ask Question"
   - Wait for answer (20-90 seconds)
4. Scroll down - your new question should appear in history
5. **Important:** Log out and log in as a different user
6. Verify that user only sees their own history (not the admin's)

### Step 5: Test User-Specific History

1. Create or log in as a different user (e.g., `test_user`)
2. Ask a question as that user
3. Log out and log back in as admin
4. Verify admin only sees admin's questions, not the other user's
5. Log back in as the other user
6. Verify that user only sees their own questions

### Step 6: Test Admin Features

1. Log in as admin
2. Navigate to `/admin/users`
3. Verify you can see the user list
4. Try creating a new user
5. Try editing a user
6. Navigate to `/admin/analytics`
7. Verify analytics page loads

### Step 7: Test Regular User Restrictions

1. Log in as a regular user (not admin)
2. Verify the "👑 Admin" button does NOT appear
3. Try accessing `/admin/dashboard` directly
4. You should be redirected to login or see an error

## Method 2: Automated Browser Tests (E2E)

### Install Chrome/Chromium

```bash
# On Rocky Linux
sudo dnf install chromium -y

# Verify installation
chromium --version
```

### Run E2E Tests

```bash
cd /var/www/chatbot_FC
source venv/bin/activate

# Run all E2E tests
./scripts/run_e2e_tests.sh

# Or run with pytest directly
pytest src/tests/e2e/test_browser_e2e.py -v
```

### Run Specific Test Categories

```bash
# Test authentication only
pytest src/tests/e2e/test_browser_e2e.py::TestAuthentication -v

# Test admin access
pytest src/tests/e2e/test_browser_e2e.py::TestAdminAccess -v

# Test conversation history
pytest src/tests/e2e/test_browser_e2e.py::TestConversationHistory -v
```

## Method 3: API Testing (Using curl or Postman)

### Test Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### Test Admin Dashboard (with token)

```bash
# First get token from login response
TOKEN="your_token_here"

curl http://localhost:8000/api/admin/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

### Test Conversation History

```bash
TOKEN="your_token_here"

curl http://localhost:8000/api/conversations/history \
  -H "Authorization: Bearer $TOKEN"
```

## Test Checklist

### ✅ Authentication
- [ ] Login page loads
- [ ] Login with valid credentials works
- [ ] Login with invalid credentials fails
- [ ] Logout works
- [ ] Redirects to login when not authenticated

### ✅ User Interface
- [ ] Main page loads after login
- [ ] User profile shows in header
- [ ] Admin link visible for admin users
- [ ] Admin link NOT visible for regular users

### ✅ Conversation History
- [ ] History section exists
- [ ] History loads from database (not localStorage)
- [ ] Each user sees only their own history
- [ ] New questions appear in history

### ✅ Admin Features
- [ ] Admin dashboard accessible
- [ ] Admin dashboard requires authentication
- [ ] Admin link navigation works
- [ ] Admin users page accessible
- [ ] Admin can manage users

### ✅ Query Functionality
- [ ] Query input field exists
- [ ] Can submit questions
- [ ] Answers are displayed
- [ ] Sources are shown

## Troubleshooting

### Application Not Running

```bash
# Check if running
curl http://localhost:8000/health

# Start if not running
cd /var/www/chatbot_FC
source venv/bin/activate
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Chrome Not Found (for E2E tests)

```bash
# Install Chrome
sudo dnf install chromium -y

# Or use headless Firefox (modify test file)
```

### Test Users Don't Exist

```bash
# Create admin user
python scripts/seed_admin_user.py

# Create test user via admin UI or API
```

### Tests Fail

1. Check application logs: `tail -f /tmp/api.log`
2. Check browser console (if running non-headless)
3. Verify test users exist
4. Verify application is running
5. Check network connectivity

## Expected Test Results

### Manual Testing
- All checklist items should pass
- No errors in browser console
- Smooth user experience

### Automated E2E Tests
- All tests should pass (PASSED status)
- No timeouts or errors
- Tests complete in 5-10 minutes

## Next Steps

1. **Run manual tests** to verify basic functionality
2. **Run automated E2E tests** for comprehensive coverage
3. **Review test results** and fix any failures
4. **Add more tests** as needed for new features

For detailed E2E testing documentation, see `docs/E2E_TESTING_GUIDE.md`

