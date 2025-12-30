#!/bin/bash
# First-time ZeroDB Local setup
# This script performs a complete first-time installation and verification

set -e

echo "=========================================="
echo "  ZeroDB Local - First-Time Setup"
echo "=========================================="
echo ""

# Step 1: Initialize environment
echo "[1/5] Initializing ZeroDB Local..."
zerodb local init

echo ""

# Step 2: Start all services
echo "[2/5] Starting all services..."
zerodb local up

echo ""

# Step 3: Wait for services to start
echo "[3/5] Waiting for services to start (30 seconds)..."
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Step 4: Check health
echo "[4/5] Checking system health..."
zerodb inspect health

echo ""

# Step 5: Display access information
echo "[5/5] Setup complete!"
echo ""
echo "=========================================="
echo "  Access Your Services"
echo "=========================================="
echo ""
echo "  API Documentation:  http://localhost:8000/docs"
echo "  Dashboard:          http://localhost:3000"
echo "  Qdrant Dashboard:   http://localhost:6333/dashboard"
echo "  MinIO Console:      http://localhost:9001"
echo ""
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo ""
echo "  1. Open the API docs and explore endpoints"
echo "  2. Create your first project via the API"
echo "  3. Run 'zerodb inspect projects' to see your projects"
echo "  4. Read the Quick Start guide: docs/QUICK_START.md"
echo ""
echo "=========================================="
echo ""

# Display quick command reference
echo "Quick Command Reference:"
echo ""
echo "  View logs:         zerodb local logs"
echo "  Stop services:     zerodb local down"
echo "  Restart services:  zerodb local restart"
echo "  Check health:      zerodb inspect health"
echo "  Sync to cloud:     zerodb sync plan"
echo ""
echo "For more help, run: zerodb --help"
echo ""
