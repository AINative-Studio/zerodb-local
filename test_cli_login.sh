#!/bin/bash
# Test CLI cloud login with correct endpoint

cd /Users/aideveloper/core/zerodb-local
source test_cli_venv/bin/activate

echo "Testing ZeroDB CLI Cloud Login"
echo "==============================="
echo ""
echo "Email: admin@ainative.studio"
echo "Password: Admin2025!Secure"
echo ""

# Use echo to pipe password to avoid interactive prompt issues
echo -e "admin@ainative.studio\nAdmin2025!Secure" | zerodb cloud login 2>&1
