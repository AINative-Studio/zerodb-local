#!/bin/bash
# Inspect all database state
# Comprehensive inspection of ZeroDB Local system

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

echo "========================================"
echo "ZeroDB Local - System Inspection"
echo "========================================"
echo ""
echo "This script performs a comprehensive inspection of your"
echo "ZeroDB Local instance, including:"
echo "  - System health check"
echo "  - Projects and databases"
echo "  - Sync status with cloud"
echo "  - Vector statistics"
echo "  - NoSQL tables"
echo "  - File storage"
echo "  - Event stream"
echo ""

# Check if services are running
if ! docker ps | grep -q "zerodb-api"; then
    echo -e "${YELLOW}! Warning: ZeroDB services are not running${NC}"
    echo ""
    echo "Start services first with:"
    echo "  zerodb local up"
    echo ""
    exit 1
fi

# ============================================================
# SYSTEM HEALTH
# ============================================================

print_section "🏥 System Health"

zerodb inspect health

# ============================================================
# PROJECTS
# ============================================================

print_section "📂 Projects"

zerodb inspect projects

echo ""
echo "For detailed project information:"
echo "  zerodb inspect projects --details"

# ============================================================
# SYNC STATE
# ============================================================

print_section "🔄 Sync State"

zerodb inspect sync

echo ""
echo "To plan a sync operation:"
echo "  zerodb sync plan"

# ============================================================
# VECTOR STATISTICS
# ============================================================

print_section "🧮 Vector Statistics"

zerodb inspect vectors

echo ""
echo "For namespace-specific stats:"
echo "  zerodb inspect vectors --namespace <name>"

# ============================================================
# NOSQL TABLES
# ============================================================

print_section "📊 NoSQL Tables"

zerodb inspect tables

echo ""
echo "For table schemas and row counts:"
echo "  zerodb inspect tables --schemas --counts"

# ============================================================
# FILE STORAGE
# ============================================================

print_section "📁 File Storage"

if command -v zerodb inspect files &> /dev/null; then
    zerodb inspect files
else
    echo -e "${YELLOW}! File inspection command not yet implemented${NC}"
    echo ""
    echo "You can view files in MinIO Console:"
    echo "  http://localhost:9001"
fi

# ============================================================
# EVENT STREAM
# ============================================================

print_section "📨 Event Stream"

if command -v zerodb inspect events &> /dev/null; then
    zerodb inspect events
else
    echo -e "${YELLOW}! Event stream inspection not yet implemented${NC}"
    echo ""
    echo "You can query events via the API:"
    echo "  http://localhost:8000/docs#/events"
fi

# ============================================================
# DOCKER SERVICES
# ============================================================

print_section "🐳 Docker Services"

echo "Service Status:"
docker ps --filter "name=zerodb-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "For detailed logs:"
echo "  zerodb local logs <service-name>"

# ============================================================
# STORAGE USAGE
# ============================================================

print_section "💾 Storage Usage"

echo "Docker Volume Usage:"
docker system df -v | grep zerodb || echo "No ZeroDB volumes found"

echo ""
echo "For detailed volume inspection:"
echo "  docker volume ls | grep zerodb"
echo "  docker volume inspect zerodb_<volume-name>"

# ============================================================
# SUMMARY
# ============================================================

print_section "📋 Inspection Summary"

echo "Inspection complete!"
echo ""
echo "Quick access URLs:"
echo "  - API Docs:       http://localhost:8000/docs"
echo "  - Dashboard:      http://localhost:3000"
echo "  - Qdrant:         http://localhost:6333/dashboard"
echo "  - MinIO Console:  http://localhost:9001"
echo ""
echo "Next steps:"
echo "  - To view logs:           zerodb local logs"
echo "  - To restart a service:   zerodb local restart --service <name>"
echo "  - To sync with cloud:     zerodb sync plan"
echo "  - To stop services:       zerodb local down"
echo ""

echo "========================================"
echo "Inspection Complete!"
echo "========================================"
echo ""
