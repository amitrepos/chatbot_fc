#!/bin/bash
# Test Runner Script
# Runs all tests with proper authentication

set -e

cd /var/www/chatbot_FC
source venv/bin/activate

echo "=========================================="
echo "Running FlexCube AI Assistant Tests"
echo "=========================================="
echo ""

echo "Step 1: Running unit tests..."
python -m pytest src/tests/unit/ -v
echo ""

echo "Step 2: Running existing query logic tests..."
python -m pytest src/tests/test_query_logic.py -v
echo ""

echo "Step 3: Running integration tests (requires postgres user)..."
sudo -u postgres /var/www/chatbot_FC/venv/bin/python -m pytest src/tests/integration/ -v
echo ""

echo "=========================================="
echo "✅ All tests completed!"
echo "=========================================="




