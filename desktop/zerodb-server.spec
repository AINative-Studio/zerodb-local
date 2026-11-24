# PyInstaller spec for the zerodb-server sidecar bundled into ZeroDB
# Desktop (desktop/src-tauri). Refs #140 (desktop ship plan, EPIC-A).
#
# Packages api/main.py (the FastAPI app `api/` is already structured to
# run as, per its own bare `from health import ...`-style imports and the
# "main:app" uvicorn target in api/main.py's __main__ block) plus the
# `lite` extra's runtime deps (faiss-cpu, sentence-transformers) into one
# onefile executable with no Python/pip/git dependency on the target
# machine.
#
# Build from the repo root:
#   pip install -e ".[lite]" pyinstaller
#   pyinstaller desktop/zerodb-server.spec --distpath desktop/dist
#
# Output: desktop/dist/zerodb-server (one file, no console window hidden
# -- this *is* the console/server process, Tauri's sidecar.rs manages its
# lifecycle and output separately).
#
# NOTE on ZERODB_PORT: sidecar.rs always launches this binary with
# `ZERODB_PORT=8000` (see desktop/src-tauri/src/main.rs's
# `start_sidecar(&data_dir, 8000)`), but api/main.py's own __main__ block
# hardcodes `port=8000` rather than reading that env var -- harmless
# today since both sides agree on 8000, but worth knowing this isn't
# live wiring. Not fixed here: out of scope for "package the binary",
# tracked as a note for whoever next touches api/main.py's __main__.

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# api/ is the real sys.path root this app expects (bare `from health
# import ...`, `from routers import ...` etc. throughout api/main.py and
# its sibling modules) -- not the repo root, and not desktop/.
REPO_ROOT = Path(SPECPATH).parent
API_ROOT = REPO_ROOT / "api"

a = Analysis(
    [str(API_ROOT / "main.py")],
    pathex=[str(API_ROOT)],
    binaries=[],
    # Refs #141 (desktop ship plan): PyInstaller only bundles Python modules
    # by default -- non-.py data files read via a runtime os.path.join are
    # invisible to its static analysis and silently absent from the onefile
    # build. Confirmed directly in CI: lite/services/database_service_lite.py
    # reads lite/db/schema_lite.sql relative to its own __file__ at startup,
    # and the first real smoke-test run failed with
    # "FileNotFoundError: ... lite/db/schema_lite.sql" the moment the server
    # tried to initialize its SQLite schema. Bundled at the same relative
    # path (lite/db/schema_lite.sql) it's read from, matching the real repo
    # layout lite/services/database_service_lite.py's __file__-relative
    # resolution expects.
    datas=[
        (str(REPO_ROOT / "lite" / "db" / "schema_lite.sql"), "lite/db"),
    ],
    hiddenimports=[
        # FastAPI/uvicorn/starlette pull in a long tail of modules via
        # dynamic import that PyInstaller's static analysis misses --
        # collect_submodules widens the net instead of hand-listing them.
        *collect_submodules("uvicorn"),
        *collect_submodules("fastapi"),
        *collect_submodules("sentence_transformers"),
        *collect_submodules("faiss"),
        *collect_submodules("routers"),
        *collect_submodules("services"),
        *collect_submodules("schemas"),
        *collect_submodules("models"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # full-mode-only deps declared in pyproject.toml's [full] extra --
        # excluded here because this spec only installs/bundles [lite],
        # keeping the onefile binary smaller and avoiding import errors
        # for optional deps that were never installed in the build env.
        "psycopg2",
        "qdrant_client",
        "minio",
        "kafka",
        "asyncpg",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="zerodb-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
