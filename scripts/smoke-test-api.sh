#!/bin/bash
#
# ZeroLocal API Smoke Test Script
#
# This script performs quick verification that the ZeroLocal API
# can start successfully by checking all critical modules.
#
# Usage:
#   cd zerodb-local
#   ./scripts/smoke-test-api.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
# Refs: #1182

set -e

echo "============================================================"
echo "ZeroLocal API Smoke Test"
echo "============================================================"

cd api

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at api/.venv"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "✅ Virtual environment found"

# Activate virtual environment
source .venv/bin/activate

# Test 1: Check if all dependencies are installed
echo ""
echo "Test 1: Checking dependencies..."
python3 -c "
import sys
try:
    import qdrant_client
    import minio
    import kafka
    import fastapi
    import sqlalchemy
    print('✅ All critical dependencies installed')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
"

# Test 2: Check if database module loads
echo ""
echo "Test 2: Testing database module..."
python3 -c "
import sys
try:
    import database
    assert hasattr(database, 'get_db')
    assert hasattr(database, 'Base')
    print('✅ database module loads correctly')
except Exception as e:
    print(f'❌ database module error: {e}')
    sys.exit(1)
"

# Test 3: Check if auth module loads
echo ""
echo "Test 3: Testing auth module..."
python3 -c "
import sys
try:
    import auth
    assert hasattr(auth, 'get_current_user')
    assert hasattr(auth, 'User')
    print('✅ auth module loads correctly')
except Exception as e:
    print(f'❌ auth module error: {e}')
    sys.exit(1)
"

# Test 4: Check if FastAPI app loads
echo ""
echo "Test 4: Testing FastAPI app..."
python3 -c "
import sys
try:
    from main import app
    route_count = len(app.routes)
    assert route_count >= 80, f'Expected 80+ routes, got {route_count}'
    print(f'✅ FastAPI app loads successfully with {route_count} routes')
except Exception as e:
    print(f'❌ FastAPI app error: {e}')
    sys.exit(1)
"

# Deactivate venv
deactivate

echo ""
echo "============================================================"
echo "✅ All smoke tests passed!"
echo "============================================================"
echo ""
echo "Ready to start API with:"
echo "  cd api && source .venv/bin/activate && uvicorn main:app --reload"
echo "  OR"
echo "  docker-compose up -d"
echo ""

exit 0
