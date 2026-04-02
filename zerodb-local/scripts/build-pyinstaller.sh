#!/usr/bin/env bash
# Build the ZeroDB API server into a self-contained PyInstaller binary and
# copy it to the Tauri sidecar binaries directory.
#
# Usage:
#   ./zerodb-local/scripts/build-pyinstaller.sh [--clean]
#
# Outputs:
#   zerodb-local/desktop/src-tauri/binaries/zerodb-server   (macOS/Linux)
#   zerodb-local/desktop/src-tauri/binaries/zerodb-server.exe  (Windows)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
API_DIR="${REPO_ROOT}/zerodb-local/api"
DESKTOP_DIR="${REPO_ROOT}/zerodb-local/desktop"
BINARIES_DIR="${DESKTOP_DIR}/src-tauri/binaries"
DIST_DIR="${REPO_ROOT}/zerodb-local/build/pyinstaller"

log() { echo "[build-pyinstaller] $*"; }

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
if [[ ! -f "${API_DIR}/main.py" ]]; then
    log "ERROR: ${API_DIR}/main.py not found. Run from repo root."
    exit 1
fi

# ---------------------------------------------------------------------------
# Optional clean
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--clean" ]]; then
    log "Cleaning previous build artifacts..."
    rm -rf "${DIST_DIR}" "${REPO_ROOT}/zerodb-local/build/pyinstaller-work"
fi

# ---------------------------------------------------------------------------
# Install PyInstaller
# ---------------------------------------------------------------------------
log "Installing / upgrading PyInstaller..."
pip install --quiet --upgrade pyinstaller

# ---------------------------------------------------------------------------
# Install API dependencies
# ---------------------------------------------------------------------------
if [[ -f "${API_DIR}/requirements.txt" ]]; then
    log "Installing API requirements..."
    pip install --quiet -r "${API_DIR}/requirements.txt"
fi

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
mkdir -p "${DIST_DIR}"

log "Running PyInstaller..."
pyinstaller \
    --onefile \
    --name zerodb-server \
    --distpath "${DIST_DIR}" \
    --workpath "${REPO_ROOT}/zerodb-local/build/pyinstaller-work" \
    --specpath "${REPO_ROOT}/zerodb-local/build" \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import uvicorn.lifespan.off \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.logging \
    --collect-all fastapi \
    --collect-all sqlalchemy \
    "${API_DIR}/main.py"

# ---------------------------------------------------------------------------
# Copy to Tauri binaries directory
# ---------------------------------------------------------------------------
mkdir -p "${BINARIES_DIR}"

if [[ "$(uname -s)" == "MINGW"* ]] || [[ "$(uname -s)" == "CYGWIN"* ]]; then
    BINARY_NAME="zerodb-server.exe"
else
    BINARY_NAME="zerodb-server"
fi

cp "${DIST_DIR}/${BINARY_NAME}" "${BINARIES_DIR}/${BINARY_NAME}"
chmod +x "${BINARIES_DIR}/${BINARY_NAME}"

log "Binary copied to: ${BINARIES_DIR}/${BINARY_NAME}"
log "Build complete."
