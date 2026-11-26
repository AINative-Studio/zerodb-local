#!/bin/bash
# Test CLI cloud login with correct endpoint
#
# Refs #164: credentials used to be hardcoded in this file. Set them via
# env vars instead:
#   ZERODB_TEST_EMAIL=you@example.com ZERODB_TEST_PASSWORD=yourpassword ./test_cli_login.sh

cd /Users/aideveloper/core/zerodb-local
source test_cli_venv/bin/activate

if [ -z "$ZERODB_TEST_EMAIL" ] || [ -z "$ZERODB_TEST_PASSWORD" ]; then
  echo "Set ZERODB_TEST_EMAIL and ZERODB_TEST_PASSWORD before running this script." >&2
  exit 1
fi

echo "Testing ZeroDB CLI Cloud Login"
echo "==============================="
echo ""
echo "Email: $ZERODB_TEST_EMAIL"
echo ""

# Use echo to pipe password to avoid interactive prompt issues
echo -e "$ZERODB_TEST_EMAIL\n$ZERODB_TEST_PASSWORD" | zerodb cloud login 2>&1
