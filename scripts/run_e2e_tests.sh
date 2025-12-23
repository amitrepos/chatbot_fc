#!/bin/bash
# E2E Browser Test Runner Script
# Runs browser-based end-to-end tests

set -e

cd /var/www/chatbot_FC
source venv/bin/activate

echo "=========================================="
echo "Running FlexCube AI Assistant E2E Tests"
echo "=========================================="
echo ""

# Check if application is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Application doesn't seem to be running on http://localhost:8000"
    echo "   Please start the application first:"
    echo "   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if Chrome/Chromium is installed
if ! command -v chromium &> /dev/null && ! command -v google-chrome &> /dev/null; then
    echo "⚠️  Warning: Chrome/Chromium not found"
    echo "   Install with: sudo dnf install chromium -y"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if selenium is installed
if ! python -c "import selenium" 2>/dev/null; then
    echo "Installing selenium..."
    pip install selenium webdriver-manager
fi

echo "Running E2E tests..."
echo ""

# Run E2E tests
python -m pytest src/tests/e2e/test_browser_e2e.py -v --tb=short

echo ""
echo "=========================================="
echo "✅ E2E tests completed!"
echo "=========================================="




