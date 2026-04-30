"""
Test configuration for zerodb-local tests.
Adds zerodb-local to sys.path so that lite.* imports resolve correctly.
"""
import sys
from pathlib import Path

# Add zerodb-local/ itself to sys.path so `lite.services.*` imports work
_zerodb_local_root = str(Path(__file__).resolve().parent.parent)
if _zerodb_local_root not in sys.path:
    sys.path.insert(0, _zerodb_local_root)
