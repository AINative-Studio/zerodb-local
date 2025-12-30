#!/bin/bash

# Daily Development Workflow - ZeroDB Local
# This script demonstrates a typical daily workflow for development
# Updated: 2025-12-29

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Function to wait for user
wait_for_user() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

echo "========================================"
echo "ZeroDB Local - Daily Development Workflow"
echo "========================================"
echo ""
echo "This script simulates a typical day of development with ZeroDB Local:"
echo "  - Morning: Start services and check health"
echo "  - Midday: Pull updates from cloud"
echo "  - Afternoon: Push local changes to cloud"
echo "  - Evening: Create backup and stop services"
echo ""

wait_for_user

# ============================================================
# MORNING ROUTINE
# ============================================================

print_section "☀️  MORNING ROUTINE (9:00 AM)"

echo "Step 1: Start ZeroDB Local services..."
zerodb local up

echo ""
echo "Waiting 30 seconds for services to initialize..."
sleep 30

echo ""
echo "Step 2: Check system health..."
zerodb inspect health

echo ""
echo "Step 3: View your projects..."
zerodb inspect projects

echo ""
echo -e "${GREEN}✓ Morning setup complete!${NC}"
echo "Services are running and ready for development."

wait_for_user

# ============================================================
# MIDDAY SYNC
# ============================================================

print_section "🕐 MIDDAY SYNC (12:00 PM)"

echo "Step 4: Pull latest changes from cloud..."
echo ""

# Check if cloud is configured
if grep -q "CLOUD_API_KEY" .env.local && ! grep -q "CLOUD_API_KEY=$" .env.local; then
    echo "Planning pull from cloud..."
    zerodb sync plan --direction pull

    echo ""
    echo -e "${YELLOW}Would you like to apply these changes? [y/N]${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        zerodb sync apply --auto-approve
        echo ""
        echo -e "${GREEN}✓ Pull completed successfully!${NC}"
    else
        echo "Pull skipped."
    fi
else
    echo -e "${YELLOW}! Cloud sync not configured${NC}"
    echo "To enable cloud sync:"
    echo "  1. Get API key from https://www.ainative.studio/dashboard/api-keys"
    echo "  2. Add to .env.local: CLOUD_API_KEY=your-key-here"
    echo "  3. Restart API: zerodb local restart --service zerodb-api"
fi

echo ""
echo "Step 5: Check sync status..."
zerodb inspect sync

echo ""
echo -e "${GREEN}✓ Midday sync complete!${NC}"
echo "You're now up to date with cloud changes."

wait_for_user

# ============================================================
# DEVELOPMENT WORK
# ============================================================

print_section "💻 DEVELOPMENT WORK (2:00 PM)"

echo "Simulating development work..."
echo ""
echo "In a real workflow, you would be:"
echo "  - Building AI agents with memory"
echo "  - Creating semantic search features"
echo "  - Storing and querying vectors"
echo "  - Managing NoSQL tables"
echo "  - Uploading and retrieving files"
echo ""
echo "All changes are automatically tracked for sync."
echo ""

# Simulate some development time
echo "Working..."
for i in {1..5}; do
    echo -n "."
    sleep 1
done
echo ""

echo ""
echo -e "${GREEN}✓ Development session complete!${NC}"

wait_for_user

# ============================================================
# AFTERNOON SYNC
# ============================================================

print_section "🕓 AFTERNOON SYNC (5:00 PM)"

echo "Step 6: Push local changes to cloud..."
echo ""

if grep -q "CLOUD_API_KEY" .env.local && ! grep -q "CLOUD_API_KEY=$" .env.local; then
    echo "Planning push to cloud..."
    zerodb sync plan --direction push

    echo ""
    echo -e "${YELLOW}Would you like to push these changes? [y/N]${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        zerodb sync apply --direction push --auto-approve
        echo ""
        echo -e "${GREEN}✓ Push completed successfully!${NC}"
    else
        echo "Push skipped."
    fi
else
    echo -e "${YELLOW}! Cloud sync not configured${NC}"
    echo "Your local changes are preserved and can be synced later."
fi

echo ""
echo "Step 7: Verify sync status..."
zerodb inspect sync

echo ""
echo -e "${GREEN}✓ Afternoon sync complete!${NC}"
echo "Your progress is backed up to the cloud."

wait_for_user

# ============================================================
# EVENING ROUTINE
# ============================================================

print_section "🌙 EVENING ROUTINE (6:00 PM)"

echo "Step 8: Create local backup..."
if [ -f "./scripts/backup-local.sh" ]; then
    ./scripts/backup-local.sh
    echo -e "${GREEN}✓ Backup created${NC}"
else
    echo -e "${YELLOW}! Backup script not found${NC}"
    echo "Manual backup command:"
    echo "  docker exec zerodb-postgres pg_dump -U zerodb zerodb_local > backup_\$(date +%Y%m%d).sql"
fi

echo ""
echo "Step 9: View final project status..."
zerodb inspect projects --details

echo ""
echo "Step 10: Stop services (preserves data)..."
echo -e "${YELLOW}Stopping services...${NC}"
zerodb local down

echo ""
echo -e "${GREEN}✓ Evening routine complete!${NC}"
echo "Services stopped, data preserved, backup created."

# ============================================================
# SUMMARY
# ============================================================

print_section "📊 DAILY WORKFLOW SUMMARY"

echo "Today you:"
echo "  ✓ Started services and verified health"
echo "  ✓ Pulled latest changes from cloud"
echo "  ✓ Performed development work"
echo "  ✓ Pushed changes back to cloud"
echo "  ✓ Created a local backup"
echo "  ✓ Stopped services cleanly"
echo ""
echo "Total time: ~15 minutes of sync/management"
echo "Development time: As needed"
echo ""
echo "Key benefits:"
echo "  - Local-first: Fast development without API latency"
echo "  - Cloud backup: Your work is always safe"
echo "  - Conflict resolution: Automatic handling of concurrent changes"
echo "  - Privacy: Sensitive data stays local until you sync"
echo ""
echo "Tomorrow morning, just run:"
echo "  zerodb local up"
echo ""
echo "Or automate the entire workflow with cron:"
echo "  0 9 * * * cd /path/to/zerodb-local && zerodb local up"
echo "  0 18 * * * cd /path/to/zerodb-local && zerodb sync apply --auto-approve && zerodb local down"
echo ""

echo "========================================"
echo "Daily Workflow Complete!"
echo "========================================"
echo ""
