#!/bin/bash
# Test CLI cloud login with correct endpoint

cd /Users/aideveloper/core/zerodb-local
source test_cli_venv/bin/activate

echo "Testing ZeroDB CLI Cloud Login"
echo "==============================="
echo ""
echo "Email: admin@ainative.studio"
echo "Password: REDACTED_CREDENTIAL_PURGED"
echo ""

# Use echo to pipe password to avoid interactive prompt issues
echo -e "admin@ainative.studio\nREDACTED_CREDENTIAL_PURGED" | zerodb cloud login 2>&1
