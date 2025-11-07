#!/bin/bash
# Test runner script for AIrsenal Ops Console backend

set -e

echo "=========================================="
echo "AIrsenal Ops Console - Backend Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if MongoDB is running
echo "Checking MongoDB connection..."
if ! nc -z localhost 27017 2>/dev/null; then
    echo -e "${RED}Error: MongoDB is not running on localhost:27017${NC}"
    echo "Please start MongoDB before running tests"
    exit 1
fi
echo -e "${GREEN}✓ MongoDB is running${NC}"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Consider activating a virtual environment before running tests"
    echo ""
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Run tests with coverage
echo "Running tests..."
echo "-------------------------------------------"
pytest "$@"
TEST_EXIT_CODE=$?
echo "-------------------------------------------"
echo ""

# Print coverage summary
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
    echo "Run 'open htmlcov/index.html' to view detailed coverage report"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit $TEST_EXIT_CODE
fi

echo ""
echo "=========================================="
echo "Test run complete"
echo "=========================================="
