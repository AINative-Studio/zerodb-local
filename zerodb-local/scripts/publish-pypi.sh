#!/bin/bash
# Publish ZeroDB Local to PyPI
set -e

VERSION=${1:-"1.0.0"}

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
echo -e "${CYAN}║${NC}    ${BOLD}${YELLOW}PyPI Package Builder${NC}  ${BOLD}v${VERSION}${NC}                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                                ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }

# Install build tools if needed
echo "Installing build tools..."
pip install --upgrade build twine

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Build the package
echo "Building package..."
python3 -m build

# Check the package
echo "Checking package..."
twine check dist/*

echo ""
echo "✅ Package built successfully!"
echo ""
echo "Distribution files:"
ls -lh dist/
echo ""

# Ask for confirmation before uploading
read -p "Upload to PyPI? (yes/no/test): " UPLOAD

case $UPLOAD in
  yes|y|Y)
    echo "Uploading to PyPI..."
    twine upload dist/*
    echo "✅ Published to PyPI!"
    echo "Install with: pip install zerodb-local"
    ;;
  test|t|T)
    echo "Uploading to TestPyPI..."
    twine upload --repository testpypi dist/*
    echo "✅ Published to TestPyPI!"
    echo "Install with: pip install --index-url https://test.pypi.org/simple/ zerodb-local"
    ;;
  *)
    echo "Skipping upload."
    echo "To upload manually:"
    echo "  PyPI: twine upload dist/*"
    echo "  TestPyPI: twine upload --repository testpypi dist/*"
    ;;
esac

echo ""
echo "Package info:"
echo "  Name: zerodb-local"
echo "  Version: ${VERSION}"
echo "  Size: $(du -sh dist/*.tar.gz | awk '{print $1}')"
echo ""
