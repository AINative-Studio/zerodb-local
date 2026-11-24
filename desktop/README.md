# ZeroDB Desktop

A Tauri 2 wrapper around the ZeroDB Local API server — system tray, auto-start, health
monitoring, and a dashboard window. See the root [`README.md`](../README.md) for what
ZeroDB Local itself does; this covers the desktop shell specifically.

## Building the sidecar binary

The desktop app bundles a standalone build of the API server (`desktop/zerodb-server.spec`)
so end users don't need Python installed. Build it from the repo root:

```bash
pip install -e ".[lite]" pyinstaller
pyinstaller desktop/zerodb-server.spec --distpath desktop/src-tauri/binaries
```

This produces `desktop/src-tauri/binaries/zerodb-server` — a single executable that serves
`/health` on `127.0.0.1:8000` with zero dependency on the source checkout. Verify it works
standalone before bundling:

```bash
cd /tmp && ZERODB_DATA_DIR=/tmp/zerodb-test-data desktop/src-tauri/binaries/zerodb-server &
curl http://127.0.0.1:8000/health
```

Rename the output to match Tauri's target-triple convention for `externalBin`
(e.g. `zerodb-server-aarch64-apple-darwin`) before `tauri build`.

## Running in dev mode

```bash
cd desktop
npm install
npm run tauri:dev
```

In dev mode the app falls back to running the API via `python3 -m uvicorn` directly
(see `src-tauri/src/sidecar.rs`'s `start_dev_fallback`) rather than the bundled binary.

## Building the app

```bash
cd desktop
npm run tauri:build
```
