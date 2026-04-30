#!/bin/bash
# ZeroLocal Dashboard - Development Script

set -e

echo "======================================"
echo "ZeroLocal Dashboard - Development Mode"
echo "======================================"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start development server
echo "Starting Next.js development server..."
echo "Dashboard will be available at http://localhost:3000"
echo "API endpoint: http://localhost:8000"
echo ""

npm run dev
