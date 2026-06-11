#!/bin/bash
# NYC DOT Toolkit - Test Verification Script
# Runs full test suite, generates coverage report, and verifies production readiness

set -e

echo "=========================================="
echo "NYC DOT Toolkit - Test Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# Step 1: Check if pytest is installed
echo "Step 1: Checking pytest installation..."
python -m pip show pytest > /dev/null 2>&1
print_status $? "pytest is installed"

# Step 2: Install test dependencies if needed
echo ""
echo "Step 2: Installing test dependencies..."
pip install -q pytest pytest-cov pytest-asyncio coverage

# Step 3: Run unit tests
echo ""
echo "Step 3: Running unit tests..."
python -m pytest tests/ -v --tb=short 2>&1 | tee test_results.txt
TEST_RESULT=${PIPESTATUS[0]}
print_status $TEST_RESULT "Unit tests completed"

# Step 4: Run tests with coverage
echo ""
echo "Step 4: Running tests with coverage..."
python -m pytest tests/ --cov=socrata_toolkit --cov-report=term-missing --cov-report=html 2>&1 | tee -a test_results.txt
COVERAGE_RESULT=${PIPESTATUS[0]}
print_status $COVERAGE_RESULT "Coverage report generated"

# Step 5: Check coverage threshold
echo ""
echo "Step 5: Checking coverage threshold (minimum 70%)..."
COVERAGE_PERCENT=$(python -m coverage report | grep "^TOTAL" | awk '{print $NF}' | sed 's/%//')
echo "Current coverage: ${COVERAGE_PERCENT}%"

if (( $(echo "$COVERAGE_PERCENT >= 70" | bc -l) )); then
    print_status 0 "Coverage threshold met (${COVERAGE_PERCENT}%)"
else
    echo -e "${YELLOW}⚠ Coverage below threshold (${COVERAGE_PERCENT}%)${NC}"
    echo "  Current: ${COVERAGE_PERCENT}%"
    echo "  Required: 70%"
    echo "  Gap: $(python -c "print(70 - int('$COVERAGE_PERCENT'))")%"
fi

# Step 6: Integration tests (optional)
if [ -f "tests/test_integration.py" ]; then
    echo ""
    echo "Step 6: Running integration tests..."
    python -m pytest tests/test_integration.py -v --tb=short || true
fi

# Step 7: Generate report
echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo ""
echo "Coverage Report:"
python -m coverage report | tail -10
echo ""
echo "Detailed HTML coverage report: htmlcov/index.html"
echo "Test results: test_results.txt"
echo ""

# Step 8: Recommendations
echo "=========================================="
echo "Recommendations"
echo "=========================================="
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Some tests failed - see details above${NC}"
fi

if (( $(echo "$COVERAGE_PERCENT >= 80" | bc -l) )); then
    echo -e "${GREEN}✓ Coverage is excellent (${COVERAGE_PERCENT}%)${NC}"
elif (( $(echo "$COVERAGE_PERCENT >= 70" | bc -l) )); then
    echo -e "${YELLOW}⚠ Coverage is acceptable but could improve${NC}"
else
    echo -e "${RED}✗ Coverage is too low${NC}"
fi

echo ""
echo "Next steps:"
echo "1. Review test_results.txt for any failures"
echo "2. Review htmlcov/index.html for coverage gaps"
echo "3. Fix failing tests before production"
echo "4. Commit results: git commit -am 'Test verification complete'"
echo ""
