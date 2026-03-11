#!/bin/bash
set -e

# ZeroDB Local - Installation Script
# Automates setup with pre-flight checks and helpful feedback

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}${BLUE}███████╗███████╗██████╗  ██████╗ ██████╗ ██████╗ ${NC}              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}${BLUE}╚══███╔╝██╔════╝██╔══██╗██╔═══██╗██╔══██╗██╔══██╗${NC}             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${BOLD}${BLUE}███╔╝ █████╗  ██████╔╝██║   ██║██║  ██║██████╔╝${NC}             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}   ${BOLD}${BLUE}███╔╝  ██╔══╝  ██╔══██╗██║   ██║██║  ██║██╔══██╗${NC}             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}${BLUE}███████╗███████╗██║  ██║╚██████╔╝██████╔╝██████╔╝${NC}             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}${BLUE}╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ${NC}              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                                ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${BOLD}${GREEN}LOCAL${NC} ${BOLD}Development Environment${NC}  ${BOLD}v1.0.0${NC}                    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    Complete AINative Data Stack                               ${CYAN}║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Pre-flight checks
echo -e "${BOLD}1. Running pre-flight checks...${NC}"

# Check Docker
echo -n "   Checking Docker... "
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ NOT FOUND${NC}"
    echo ""
    echo -e "${YELLOW}Docker is required but not installed.${NC}"
    echo "Please install Docker Desktop:"
    echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  Linux: https://docs.docker.com/engine/install/"
    echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
    exit 1
fi
echo -e "${GREEN}✓${NC}"

# Check Docker is running
echo -n "   Checking Docker is running... "
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ NOT RUNNING${NC}"
    echo ""
    echo -e "${YELLOW}Docker is installed but not running.${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo -e "${GREEN}✓${NC}"

# Check Docker Compose
echo -n "   Checking Docker Compose... "
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}✗ NOT FOUND${NC}"
    echo ""
    echo -e "${YELLOW}Docker Compose is required.${NC}"
    echo "It should come with Docker Desktop. Please reinstall Docker."
    exit 1
fi
echo -e "${GREEN}✓${NC}"

# Check Python 3
echo -n "   Checking Python 3... "
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ NOT FOUND${NC}"
    echo ""
    echo -e "${YELLOW}Python 3.9+ is required for CLI installation.${NC}"
    echo "Install from: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ ($PYTHON_VERSION)${NC}"

# Check available memory
echo -n "   Checking available memory... "
if [[ "$OSTYPE" == "darwin"* ]]; then
    FREE_MEM=$(vm_stat | awk '/Pages free/ {print int($3) * 4096 / 1024 / 1024)}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    FREE_MEM=$(free -m | awk '/^Mem:/{print $7}')
else
    FREE_MEM=4096  # Assume sufficient on Windows
fi

if [ "$FREE_MEM" -lt 4096 ]; then
    echo -e "${YELLOW}⚠ ${FREE_MEM}MB (recommended: 4GB+)${NC}"
else
    echo -e "${GREEN}✓ ${FREE_MEM}MB${NC}"
fi

echo ""

# Setup environment
echo -e "${BOLD}2. Setting up environment...${NC}"

if [ ! -f .env.local ]; then
    echo "   Creating .env.local from template..."
    cp .env.local.example .env.local
    echo -e "   ${GREEN}✓ Created .env.local${NC}"
    echo -e "   ${YELLOW}Note: Edit .env.local to customize settings${NC}"
else
    echo -e "   ${YELLOW}⚠ .env.local already exists, skipping${NC}"
fi

# Create data directories
echo "   Creating data directories..."
mkdir -p data/postgres data/qdrant data/minio data/redpanda data/embeddings
echo -e "   ${GREEN}✓ Created data directories${NC}"

echo ""

# Start services
echo -e "${BOLD}3. Starting ZeroDB services...${NC}"
echo "   This may take 1-2 minutes on first run (downloading images)..."
echo ""

docker compose up -d

echo ""
echo "   Waiting for services to be healthy..."
sleep 5

# Check service health
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    HEALTHY=$(docker compose ps --format json | jq -r '.Health' | grep -c "healthy" || echo "0")
    TOTAL=$(docker compose ps --format json | jq -r '.Name' | wc -l | tr -d ' ')

    if [ "$HEALTHY" -ge 5 ]; then
        echo -e "   ${GREEN}✓ Services are healthy ($HEALTHY/$TOTAL)${NC}"
        break
    fi

    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo -e "   ${YELLOW}⚠ Services taking longer than expected${NC}"
    echo "   Check status with: docker compose ps"
fi

echo ""

# Install CLI
echo -e "${BOLD}4. Installing ZeroDB CLI...${NC}"
echo "   Creating virtual environment..."

cd cli
if [ -d "venv" ]; then
    echo -e "   ${YELLOW}⚠ venv already exists, using it${NC}"
else
    python3 -m venv venv
    echo -e "   ${GREEN}✓ Created venv${NC}"
fi

echo "   Installing CLI..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -e .

if command -v zerodb &> /dev/null; then
    echo -e "   ${GREEN}✓ CLI installed successfully${NC}"
    ZERODB_VERSION=$(zerodb version 2>/dev/null || echo "1.0.0")
    echo "   Version: $ZERODB_VERSION"
else
    echo -e "   ${RED}✗ CLI installation failed${NC}"
    exit 1
fi

cd ..

echo ""

# Success summary
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}                                                                ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${BOLD}${GREEN}✅ Installation Complete!${NC}                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                                ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Services running at:${NC}"
echo "  🌐 Dashboard:  http://localhost:3000"
echo "  📡 API:        http://localhost:8000"
echo "  📚 API Docs:   http://localhost:8000/docs"
echo "  🗄️  PostgreSQL: localhost:5432"
echo "  🔍 Qdrant:     localhost:6333"
echo "  💾 MinIO:      localhost:9001"
echo ""
echo -e "${BOLD}Quick commands:${NC}"
echo "  # Activate CLI"
echo "  source cli/venv/bin/activate"
echo ""
echo "  # Check status"
echo "  zerodb local status"
echo ""
echo "  # View logs"
echo "  docker compose logs -f"
echo ""
echo "  # Stop services"
echo "  docker compose down"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Open dashboard: http://localhost:3000"
echo "  2. Test API: curl http://localhost:8000/health"
echo "  3. Read docs: cat README.md"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
