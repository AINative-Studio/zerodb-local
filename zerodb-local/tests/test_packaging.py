"""
Tests for zerodb-local PyPI packaging.

Validates that the package structure, metadata, CLI entry point,
and dependency declarations are correctly configured.

Refs #1713
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest


# ---- Package import tests ----


class TestPackageImports:
    """Verify the zerodb_local package is importable and well-formed."""

    def test_import_zerodb_local(self):
        """Package root must be importable."""
        import zerodb_local

        assert zerodb_local is not None

    def test_version_is_set(self):
        """Package must expose a __version__ string."""
        from zerodb_local import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Version must follow semver (major.minor.patch)."""
        from zerodb_local import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2, f"Expected semver, got {__version__}"
        for part in parts:
            assert part.isdigit(), f"Non-numeric version component: {part}"

    def test_version_matches_pyproject(self):
        """Package __version__ must match pyproject.toml version."""
        from zerodb_local import __version__

        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found (running outside source tree)")

        content = pyproject_path.read_text()
        # Parse version = "x.y.z" from pyproject.toml
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                pyproject_version = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                assert __version__ == pyproject_version, (
                    f"__init__.py has {__version__}, pyproject.toml has {pyproject_version}"
                )
                return

        pytest.fail("Could not find version in pyproject.toml")

    def test_import_cli_module(self):
        """The cli module must be importable."""
        from zerodb_local import cli

        assert cli is not None

    def test_cli_app_is_typer(self):
        """The cli.app must be a Typer instance."""
        import typer
        from zerodb_local.cli import app

        assert isinstance(app, typer.Typer)

    def test_import_server_module(self):
        """The server module must be importable."""
        from zerodb_local import server

        assert server is not None

    def test_server_create_app_callable(self):
        """server.create_app must be a callable factory."""
        from zerodb_local.server import create_app

        assert callable(create_app)


# ---- CLI entry point tests ----


class TestCLIEntryPoint:
    """Verify the `zerodb` console script is accessible."""

    def test_cli_help_flag(self):
        """Running `python -m zerodb_local.cli --help` must succeed."""
        result = subprocess.run(
            [sys.executable, "-c", "from zerodb_local.cli import app; app(['--help'])"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Typer exits with code 0 on --help
        assert result.returncode == 0, f"CLI --help failed: {result.stderr}"
        assert "zerodb" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_cli_version_command(self):
        """The `version` command must be registered."""
        result = subprocess.run(
            [sys.executable, "-c", "from zerodb_local.cli import app; app(['version'])"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, f"version command failed: {result.stderr}"
        # Full CLI shows "v1.0.0", standalone shows "0.2.0" — both are valid
        assert "version" in result.stdout.lower() or "0.2.0" in result.stdout or "1.0.0" in result.stdout


# ---- Dependency declaration tests ----


class TestDependencies:
    """Verify that key dependencies are declared in pyproject.toml."""

    @pytest.fixture(scope="class")
    def pyproject_content(self):
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")
        return pyproject_path.read_text()

    @pytest.mark.parametrize(
        "dep",
        [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "typer",
            "httpx",
            "pydantic",
            "python-multipart",
        ],
    )
    def test_core_dependency_declared(self, pyproject_content, dep):
        """Core dependencies must be listed in pyproject.toml."""
        assert dep in pyproject_content, f"Missing core dependency: {dep}"

    @pytest.mark.parametrize("dep", ["faiss-cpu", "sentence-transformers"])
    def test_lite_extra_declared(self, pyproject_content, dep):
        """Lite extra dependencies must be declared."""
        assert dep in pyproject_content, f"Missing lite extra: {dep}"

    @pytest.mark.parametrize(
        "dep", ["psycopg2-binary", "qdrant-client", "minio", "kafka-python", "asyncpg"]
    )
    def test_full_extra_declared(self, pyproject_content, dep):
        """Full extra dependencies must be declared."""
        assert dep in pyproject_content, f"Missing full extra: {dep}"

    @pytest.mark.parametrize("dep", ["pytest", "pytest-asyncio", "pytest-cov"])
    def test_dev_extra_declared(self, pyproject_content, dep):
        """Dev extra dependencies must be declared."""
        assert dep in pyproject_content, f"Missing dev extra: {dep}"


# ---- pyproject.toml structure tests ----


class TestPyprojectStructure:
    """Validate pyproject.toml has required sections."""

    @pytest.fixture(scope="class")
    def pyproject_content(self):
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")
        return pyproject_path.read_text()

    def test_build_system_defined(self, pyproject_content):
        """Build system must use hatchling."""
        assert "[build-system]" in pyproject_content
        assert "hatchling" in pyproject_content

    def test_project_name(self, pyproject_content):
        """Project name must be zerodb-local."""
        assert 'name = "zerodb-local"' in pyproject_content

    def test_console_script_defined(self, pyproject_content):
        """Console script entry point must map zerodb to zerodb_local.cli:app."""
        assert "[project.scripts]" in pyproject_content
        assert "zerodb_local.cli:app" in pyproject_content

    def test_python_requires(self, pyproject_content):
        """Must require Python >= 3.10."""
        assert ">=3.10" in pyproject_content

    def test_wheel_packages(self, pyproject_content):
        """Wheel must include zerodb_local package."""
        assert "zerodb_local" in pyproject_content
        assert "[tool.hatch.build.targets.wheel]" in pyproject_content

    def test_no_conflict_with_zerodb_cli(self, pyproject_content):
        """Package name must NOT be zerodb-cli (already published)."""
        # The name field must be zerodb-local, not zerodb-cli
        lines = pyproject_content.splitlines()
        for line in lines:
            if line.strip().startswith("name") and "=" in line:
                assert "zerodb-cli" not in line, "Package name conflicts with existing zerodb-cli on PyPI"
                break
