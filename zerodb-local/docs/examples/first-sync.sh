#!/bin/bash

# First Sync Example - ZeroDB Local
# This script demonstrates the first synchronization workflow with ZeroDB Cloud
# Updated: 2025-12-29

set -e  # Exit on error

echo "=================================="
echo "ZeroDB Local - First Sync Example"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if CLI is installed
echo "Step 1: Checking CLI installation..."
if ! command -v zerodb &> /dev/null; then
    echo -e "${RED}✗ ZeroDB CLI not found${NC}"
    echo "Please install CLI first:"
    echo "  cd cli && pip install -e ."
    exit 1
fi
echo -e "${GREEN}✓ CLI installed${NC}"
echo ""

# Step 2: Check if services are running
echo "Step 2: Checking if services are running..."
if ! docker ps | grep -q "zerodb-api"; then
    echo -e "${YELLOW}! Services not running, starting them...${NC}"
    zerodb local up
    echo "Waiting 30 seconds for services to be ready..."
    sleep 30
else
    echo -e "${GREEN}✓ Services running${NC}"
fi
echo ""

# Step 3: Check system health
echo "Step 3: Checking system health..."
if zerodb inspect health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ All services healthy${NC}"
else
    echo -e "${RED}✗ Some services unhealthy${NC}"
    echo "Run 'zerodb inspect health' for details"
    exit 1
fi
echo ""

# Step 4: Check cloud API key
echo "Step 4: Checking cloud configuration..."
if ! grep -q "CLOUD_API_KEY" .env.local || grep -q "CLOUD_API_KEY=$" .env.local; then
    echo -e "${YELLOW}! Cloud API key not configured${NC}"
    echo ""
    echo "To sync with ZeroDB Cloud, you need an API key:"
    echo "1. Visit: https://www.ainative.studio/dashboard/api-keys"
    echo "2. Create a new API key"
    echo "3. Add to .env.local: CLOUD_API_KEY=your-key-here"
    echo "4. Restart API: zerodb local restart --service zerodb-api"
    echo ""
    echo "For now, this example will show the sync commands only."
    CLOUD_ENABLED=false
else
    echo -e "${GREEN}✓ Cloud API key configured${NC}"
    CLOUD_ENABLED=true
fi
echo ""

# Step 5: Show current projects
echo "Step 5: Listing local projects..."
zerodb inspect projects
echo ""

# Step 6: Plan sync from cloud (preview)
echo "Step 6: Planning sync from cloud (pull)..."
echo -e "${YELLOW}This shows what would be downloaded from cloud${NC}"
echo ""

if [ "$CLOUD_ENABLED" = true ]; then
    zerodb sync plan --direction pull
else
    echo "Example output:"
    echo "┌─────────────────────────────────────────────────┐"
    echo "│           Sync Plan Summary                     │"
    echo "├─────────────────────────────────────────────────┤"
    echo "│ Direction: cloud → local (pull)                 │"
    echo "│ Mode: Preview (no changes will be made)         │"
    echo "├─────────────────────────────────────────────────┤"
    echo "│ Changes to apply:                               │"
    echo "│  - CREATE: 5 vectors                            │"
    echo "│  - UPDATE: 2 vectors                            │"
    echo "│  - CREATE: 1 table                              │"
    echo "└─────────────────────────────────────────────────┘"
fi
echo ""

# Step 7: Execute sync (with confirmation)
echo "Step 7: Executing sync..."
echo -e "${YELLOW}In a real scenario, you would run:${NC}"
echo "  zerodb sync apply"
echo ""
echo "This will:"
echo "  1. Show you the sync plan again"
echo "  2. Ask for confirmation (y/N)"
echo "  3. Execute the sync operations"
echo "  4. Show progress for each item"
echo "  5. Report final results"
echo ""

if [ "$CLOUD_ENABLED" = true ]; then
    echo -e "${YELLOW}Would you like to execute the sync now? [y/N]${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        zerodb sync apply
        echo ""
        echo -e "${GREEN}✓ Sync completed!${NC}"
    else
        echo "Sync skipped."
    fi
fi
echo ""

# Step 8: Verify sync
echo "Step 8: Verifying sync status..."
if [ "$CLOUD_ENABLED" = true ]; then
    zerodb inspect sync
else
    echo "Example output:"
    echo "┌─────────────────────────────────────────────────┐"
    echo "│            Sync Status                          │"
    echo "├─────────────────────────────────────────────────┤"
    echo "│ Cloud Connection: Connected                     │"
    echo "│ Last Sync: 2025-12-29T12:00:00Z (just now)      │"
    echo "│ Direction: bidirectional                        │"
    echo "├─────────────────────────────────────────────────┤"
    echo "│ Local Changes (pending push): 0                 │"
    echo "│ Cloud Changes (pending pull): 0                 │"
    echo "│ Conflicts: 0                                    │"
    echo "└─────────────────────────────────────────────────┘"
fi
echo ""

# Step 9: View updated projects
echo "Step 9: Viewing updated projects..."
zerodb inspect projects --details
echo ""

echo "=================================="
echo "First Sync Example Complete!"
echo "=================================="
echo ""
echo "Key Takeaways:"
echo "  1. Always plan before applying sync"
echo "  2. Review conflicts and changes carefully"
echo "  3. Use --auto-approve for scripted workflows"
echo "  4. Verify sync status after completion"
echo ""
echo "Next steps:"
echo "  - Try pushing local changes: zerodb sync plan --direction push"
echo "  - Set up automated syncs: docs/examples/daily-workflow.sh"
echo "  - Create backups: docs/examples/backup-restore.sh"
echo ""
