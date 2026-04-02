#!/usr/bin/env bash
# Full desktop build pipeline for ZeroDB Local.
#
# Steps:
#   1. Build the Python API into a PyInstaller binary
#   2. Copy binary to src-tauri/binaries/
#   3. npm install in desktop/
#   4. Next.js static export (npm run build)
#   5. cargo tauri build  ->  platform installers
#
# Usage:
#   ./zerodb-local/scripts/build-desktop.sh [--skip-pyinstaller] [--skip-npm]
#
# Outputs:
#   zerodb-local/desktop/src-tauri/target/release/bundle/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ZERODB_LOCAL="${REPO_ROOT}/zerodb-local"
DESKTOP_DIR="${ZERODB_LOCAL}/desktop"

SKIP_PYINSTALLER=false
SKIP_NPM=false

for arg in "$@"; do
    case "$arg" in
        --skip-pyinstaller) SKIP_PYINSTALLER=true ;;
        --skip-npm)         SKIP_NPM=true ;;
    esac
done

log() { echo "[build-desktop] $*"; }

# ---------------------------------------------------------------------------
# Validate toolchain
# ---------------------------------------------------------------------------
log "Checking toolchain..."

command -v cargo  >/dev/null 2>&1 || { log "ERROR: cargo not found"; exit 1; }
command -v node   >/dev/null 2>&1 || { log "ERROR: node not found";  exit 1; }
command -v npm    >/dev/null 2>&1 || { log "ERROR: npm not found";   exit 1; }

RUST_VERSION=$(rustc --version | awk '{print $2}')
NODE_VERSION=$(node --version)
log "Rust ${RUST_VERSION} | Node ${NODE_VERSION}"

# ---------------------------------------------------------------------------
# Step 1: PyInstaller binary
# ---------------------------------------------------------------------------
if [[ "${SKIP_PYINSTALLER}" == "true" ]]; then
    log "Skipping PyInstaller build (--skip-pyinstaller)."
else
    log "=== Step 1/5: Building Python API binary ==="
    bash "${SCRIPT_DIR}/build-pyinstaller.sh"
fi

# Verify binary exists before proceeding.
BINARY="${DESKTOP_DIR}/src-tauri/binaries/zerodb-server"
if [[ ! -f "${BINARY}" ]]; then
    log "WARNING: Binary not found at ${BINARY}. Tauri will fall back to dev mode."
fi

# ---------------------------------------------------------------------------
# Step 2: (already handled by build-pyinstaller.sh — binary is in place)
# ---------------------------------------------------------------------------
log "=== Step 2/5: Binary placement verified ==="

# ---------------------------------------------------------------------------
# Step 3: npm install
# ---------------------------------------------------------------------------
if [[ "${SKIP_NPM}" == "true" ]]; then
    log "Skipping npm install (--skip-npm)."
else
    log "=== Step 3/5: Installing npm dependencies ==="
    (cd "${DESKTOP_DIR}" && npm install --prefer-offline)
fi

# ---------------------------------------------------------------------------
# Step 4: Next.js static export
# ---------------------------------------------------------------------------
log "=== Step 4/5: Building Next.js static export ==="
(cd "${DESKTOP_DIR}" && npm run build)

OUT_DIR="${DESKTOP_DIR}/out"
if [[ ! -d "${OUT_DIR}" ]]; then
    log "ERROR: Next.js static export directory '${OUT_DIR}' not found after build."
    exit 1
fi
log "Static export written to: ${OUT_DIR}"

# ---------------------------------------------------------------------------
# Step 5: Tauri build
# ---------------------------------------------------------------------------
log "=== Step 5/5: Building Tauri application ==="
(cd "${DESKTOP_DIR}" && cargo tauri build)

BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/release/bundle"
log ""
log "Build complete. Platform installers:"
find "${BUNDLE_DIR}" -type f \( \
    -name "*.dmg" -o \
    -name "*.app" -o \
    -name "*.msi" -o \
    -name "*.exe" -o \
    -name "*.AppImage" -o \
    -name "*.deb" \
\) 2>/dev/null | while read -r f; do
    SIZE=$(du -sh "$f" | awk '{print $1}')
    echo "  ${SIZE}  ${f}"
done
