"""
Test configuration for zerodb-local tests.
Adds zerodb-local to sys.path so that lite.* imports resolve correctly.
"""
import sys
from pathlib import Path

import pytest

# Add zerodb-local/ itself to sys.path so `lite.services.*` imports work
_zerodb_local_root = str(Path(__file__).resolve().parent.parent)
if _zerodb_local_root not in sys.path:
    sys.path.insert(0, _zerodb_local_root)


@pytest.fixture(autouse=True, scope="module")
def _restore_sys_path_after_cli_imports():
    """
    Importing zerodb_local.cli / zerodb_local.server (exercised by
    test_packaging.py and test_integration_lite.py) transitively imports the
    source-tree cli/ package, which inserts cli/ onto sys.path[0] as a side
    effect with no cleanup (cli/zerodb_main.py and friends do this
    unconditionally at import time). Left in place, that insertion outranks
    api/'s own sys.path entry for the rest of the pytest session, so a later
    bare `import main` (api/tests/test_router_auth_coverage.py's client
    fixture) can resolve to cli/main.py's Typer app instead of api/main.py's
    FastAPI app.

    Snapshot sys.path once per test module in this directory and restore it
    at module teardown, so this directory's pollution never survives past
    tests/ into a later testpaths entry (e.g. api/tests/). Module- rather
    than function-scoped so this stays a cheap, rare guard instead of adding
    teardown cost to every single test -- including the lite_server
    subprocess fixtures in this same directory, whose startup already races
    a fixed timeout and was observed to time out when this ran per-test.
    Refs #101
    """
    path_before = list(sys.path)
    yield
    sys.path[:] = path_before
