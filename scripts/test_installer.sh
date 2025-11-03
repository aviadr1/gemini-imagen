#!/bin/bash
# Test script for the standalone installer
#
# This script tests the complete installation process end-to-end,
# verifying that the installer works correctly.

# Don't use set -e because we want to run all tests even if some fail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create temporary test home
TEST_HOME="/tmp/test-install-$$"
mkdir -p "$TEST_HOME"

cleanup() {
    if [ -d "$TEST_HOME" ]; then
        rm -rf "$TEST_HOME"
    fi
}

trap cleanup EXIT

echo "========================================"
echo "Testing gemini-imagen Standalone Installer"
echo "========================================"
echo ""
echo "Test Home: $TEST_HOME"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Test 1: Run installer
log_test "Running installer..."
if HOME="$TEST_HOME" bash -c "echo -e 'y\nn' | python3 '$SCRIPT_DIR/install.py'" > /dev/null 2>&1; then
    log_pass "Installer completed successfully"
else
    log_fail "Installer failed to run"
    # Don't exit, continue with other tests
fi

# Test 2: Check venv was created
log_test "Checking virtual environment..."
VENV_PATH="$TEST_HOME/.local/share/gemini-imagen"
if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/python" ]; then
    log_pass "Virtual environment created at $VENV_PATH"
else
    log_fail "Virtual environment not found"
fi

# Test 3: Check wrapper script exists
log_test "Checking wrapper script..."
WRAPPER_PATH="$TEST_HOME/.local/bin/imagen"
if [ -f "$WRAPPER_PATH" ] || [ -L "$WRAPPER_PATH" ]; then
    log_pass "Wrapper script exists at $WRAPPER_PATH"
else
    log_fail "Wrapper script not found"
fi

# Test 4: Check install receipt
log_test "Checking install receipt..."
RECEIPT_PATH="$TEST_HOME/.config/imagen/install_receipt.json"
if [ -f "$RECEIPT_PATH" ]; then
    log_pass "Install receipt created at $RECEIPT_PATH"

    # Validate receipt content
    if command -v jq >/dev/null 2>&1; then
        VERSION=$(jq -r '.version' "$RECEIPT_PATH")
        INSTALL_METHOD=$(jq -r '.install_method' "$RECEIPT_PATH")

        if [ "$INSTALL_METHOD" = "standalone" ]; then
            log_pass "Install receipt has correct install_method: $INSTALL_METHOD"
        else
            log_fail "Install receipt has wrong install_method: $INSTALL_METHOD"
        fi

        log_pass "Installed version: $VERSION"
    fi
else
    log_fail "Install receipt not found"
fi

# Test 5: Test imagen command exists
log_test "Testing imagen command exists..."
export PATH="$TEST_HOME/.local/bin:$PATH"
if command -v imagen >/dev/null 2>&1; then
    log_pass "imagen command found in PATH"
else
    log_fail "imagen command not found in PATH"
fi

# Test 6: Test imagen --version
log_test "Testing 'imagen --version'..."
if VERSION_OUTPUT=$(imagen --version 2>&1); then
    log_pass "imagen --version works: $VERSION_OUTPUT"

    # Check version format
    if echo "$VERSION_OUTPUT" | grep -q "imagen, version"; then
        log_pass "Version output has correct format"
    else
        log_fail "Version output format unexpected: $VERSION_OUTPUT"
    fi
else
    log_fail "imagen --version failed"
fi

# Test 7: Test imagen --help
log_test "Testing 'imagen --help'..."
if imagen --help > /dev/null 2>&1; then
    log_pass "imagen --help works"
else
    log_fail "imagen --help failed"
fi

# Test 8: Test imagen commands exist
log_test "Testing imagen commands are available..."
HELP_OUTPUT=$(imagen --help)

declare -a COMMANDS=("generate" "analyze" "edit" "config" "keys" "models")
for cmd in "${COMMANDS[@]}"; do
    if echo "$HELP_OUTPUT" | grep -q "$cmd"; then
        log_pass "Command '$cmd' is available"
    else
        log_fail "Command '$cmd' not found in help"
    fi
done

# Check for self-update separately (it might not be in published version yet)
if echo "$HELP_OUTPUT" | grep -q "self-update"; then
    log_pass "Command 'self-update' is available"
else
    log_warning "Command 'self-update' not found (expected if testing published version before PR merge)"
fi

# Test 9: Check that gemini-imagen package is importable
log_test "Testing Python package import..."
if "$VENV_PATH/bin/python" -c "import gemini_imagen; print(gemini_imagen.__version__)" > /dev/null 2>&1; then
    PYTHON_VERSION=$("$VENV_PATH/bin/python" -c "import gemini_imagen; print(gemini_imagen.__version__)")
    log_pass "gemini_imagen package importable, version: $PYTHON_VERSION"
else
    log_fail "gemini_imagen package not importable"
fi

# Test 10: Check S3 extras are installed
log_test "Testing S3 extras installation..."
if "$VENV_PATH/bin/python" -c "import boto3" > /dev/null 2>&1; then
    log_pass "S3 extras (boto3) installed correctly"
else
    log_fail "S3 extras (boto3) not installed"
fi

# Test 11: Test self-update --check (should work for standalone install)
log_test "Testing 'imagen self-update --check'..."
if imagen self-update --check > /dev/null 2>&1; then
    log_pass "imagen self-update --check works"
else
    # This might fail if command doesn't exist yet or due to network issues
    log_warning "imagen self-update --check failed (expected if testing published version before PR merge, or network issue)"
fi

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
