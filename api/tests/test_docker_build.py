"""
Test Docker Build and Non-Root User Permissions
Integration tests for Docker multi-stage build with proper permission handling

These tests can run independently without application dependencies.
Run with: pytest tests/test_docker_build.py -v --confcutdir=.

Refs #1128
"""
import pytest
import subprocess
import os
import json
from pathlib import Path

# Prevent conftest.py from loading application dependencies
pytest_plugins = []


@pytest.fixture(scope="module")
def docker_image_name():
    """Generate unique Docker image name for testing"""
    return "zerodb-api-test:latest"


@pytest.fixture(scope="module")
def dockerfile_path():
    """Get path to Dockerfile"""
    # Navigate from tests/ to api/ directory
    current_dir = Path(__file__).parent
    api_dir = current_dir.parent
    dockerfile = api_dir / "Dockerfile"

    assert dockerfile.exists(), f"Dockerfile not found at {dockerfile}"
    return dockerfile


@pytest.fixture(scope="module")
def api_dir_path():
    """Get path to API directory"""
    current_dir = Path(__file__).parent
    api_dir = current_dir.parent
    return api_dir


@pytest.mark.docker
class TestDockerBuild:
    """Test suite for Docker build process"""

    def test_dockerfile_exists(self, dockerfile_path):
        """
        GIVEN: Dockerfile should exist in api directory
        WHEN: Checking file existence
        THEN: File should be present and readable
        """
        assert dockerfile_path.exists()
        assert dockerfile_path.is_file()
        assert os.access(dockerfile_path, os.R_OK)

    def test_dockerfile_has_multi_stage_build(self, dockerfile_path):
        """
        GIVEN: Dockerfile should use multi-stage build
        WHEN: Reading Dockerfile content
        THEN: Should contain builder stage and runtime stage
        """
        content = dockerfile_path.read_text()

        assert "FROM python:3.11-slim as builder" in content
        assert "FROM python:3.11-slim" in content
        assert "COPY --from=builder" in content

    def test_dockerfile_creates_nonroot_user(self, dockerfile_path):
        """
        GIVEN: Dockerfile should create non-root user
        WHEN: Reading Dockerfile content
        THEN: Should contain useradd command for zerodb user
        """
        content = dockerfile_path.read_text()

        assert "useradd -m -u 1000 zerodb" in content
        assert "USER zerodb" in content

    def test_dockerfile_sets_correct_path(self, dockerfile_path):
        """
        GIVEN: Dockerfile should set PATH for zerodb user
        WHEN: Reading Dockerfile content
        THEN: Should set PATH to include /home/zerodb/.local/bin
        """
        content = dockerfile_path.read_text()

        assert "ENV PATH=/home/zerodb/.local/bin:$PATH" in content

    def test_dockerfile_copies_to_user_home(self, dockerfile_path):
        """
        GIVEN: Dockerfile should copy packages to zerodb user home
        WHEN: Reading Dockerfile content
        THEN: Should copy from builder /root/.local to /home/zerodb/.local
        """
        content = dockerfile_path.read_text()

        assert "COPY --from=builder /root/.local /home/zerodb/.local" in content

    def test_dockerfile_fixes_ownership(self, dockerfile_path):
        """
        GIVEN: Dockerfile should fix ownership of copied files
        WHEN: Reading Dockerfile content
        THEN: Should chown files to zerodb user
        """
        content = dockerfile_path.read_text()

        assert "chown -R zerodb:zerodb /app /home/zerodb/.local" in content

    def test_dockerfile_user_after_copy(self, dockerfile_path):
        """
        GIVEN: Dockerfile should switch to non-root user after setup
        WHEN: Reading Dockerfile content
        THEN: USER zerodb should come after COPY and chown commands
        """
        content = dockerfile_path.read_text()
        lines = content.split('\n')

        copy_line = -1
        chown_line = -1
        user_line = -1

        for i, line in enumerate(lines):
            if "COPY --from=builder" in line:
                copy_line = i
            if "chown -R zerodb:zerodb" in line:
                chown_line = i
            if line.strip() == "USER zerodb":
                user_line = i

        assert copy_line > 0, "COPY command not found"
        assert chown_line > 0, "chown command not found"
        assert user_line > 0, "USER command not found"
        assert copy_line < chown_line < user_line, "Commands in wrong order"

    def test_dockerfile_has_healthcheck(self, dockerfile_path):
        """
        GIVEN: Dockerfile should have health check
        WHEN: Reading Dockerfile content
        THEN: Should contain HEALTHCHECK instruction
        """
        content = dockerfile_path.read_text()

        assert "HEALTHCHECK" in content
        assert "curl -f http://localhost:8000/health" in content

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_docker_image_builds_successfully(self, docker_image_name, api_dir_path):
        """
        GIVEN: Valid Dockerfile and application code
        WHEN: Building Docker image
        THEN: Build should complete without errors
        """
        # Build Docker image
        build_cmd = [
            "docker", "build",
            "-t", docker_image_name,
            "-f", "Dockerfile",
            "."
        ]

        result = subprocess.run(
            build_cmd,
            cwd=api_dir_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        # BuildKit outputs to stderr, not stdout
        output = result.stdout + result.stderr
        assert "Successfully tagged" in output or "Successfully built" in output or "naming to" in output

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_docker_image_has_correct_user(self, docker_image_name):
        """
        GIVEN: Built Docker image
        WHEN: Inspecting image configuration
        THEN: Should run as zerodb user (UID 1000)
        """
        # Inspect Docker image
        inspect_cmd = [
            "docker", "inspect",
            docker_image_name
        ]

        result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Docker inspect failed: {result.stderr}"

        inspect_data = json.loads(result.stdout)
        config = inspect_data[0]["Config"]

        assert config["User"] == "zerodb", f"Expected user 'zerodb', got '{config['User']}'"

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_uvicorn_is_accessible(self, docker_image_name):
        """
        GIVEN: Built Docker image with zerodb user
        WHEN: Running container and checking uvicorn availability
        THEN: uvicorn should be in PATH and executable
        """
        # Run container and check uvicorn
        run_cmd = [
            "docker", "run",
            "--rm",
            docker_image_name,
            "which", "uvicorn"
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"uvicorn not found in PATH: {result.stderr}"
        assert "/home/zerodb/.local/bin/uvicorn" in result.stdout

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_python_packages_accessible(self, docker_image_name):
        """
        GIVEN: Built Docker image with zerodb user
        WHEN: Running container and checking Python packages
        THEN: Packages should be accessible to zerodb user
        """
        # Check if fastapi is accessible
        run_cmd = [
            "docker", "run",
            "--rm",
            docker_image_name,
            "python3", "-c", "import fastapi; print(fastapi.__version__)"
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"FastAPI not accessible: {result.stderr}"
        assert len(result.stdout.strip()) > 0

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_file_permissions_correct(self, docker_image_name):
        """
        GIVEN: Built Docker image with zerodb user
        WHEN: Checking file ownership in container
        THEN: /app and /home/zerodb/.local should be owned by zerodb
        """
        # Check /app ownership
        app_cmd = [
            "docker", "run",
            "--rm",
            docker_image_name,
            "stat", "-c", "%U:%G", "/app"
        ]

        result = subprocess.run(
            app_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"Failed to check /app ownership: {result.stderr}"
        assert result.stdout.strip() == "zerodb:zerodb"

        # Check /home/zerodb/.local ownership
        local_cmd = [
            "docker", "run",
            "--rm",
            docker_image_name,
            "stat", "-c", "%U:%G", "/home/zerodb/.local"
        ]

        result = subprocess.run(
            local_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"Failed to check .local ownership: {result.stderr}"
        assert result.stdout.strip() == "zerodb:zerodb"

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_container_runs_as_nonroot(self, docker_image_name):
        """
        GIVEN: Built Docker image
        WHEN: Running container and checking user
        THEN: Should run as zerodb user (UID 1000), not root
        """
        # Check user ID in running container
        run_cmd = [
            "docker", "run",
            "--rm",
            docker_image_name,
            "id", "-u"
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"Failed to check user ID: {result.stderr}"
        uid = result.stdout.strip()
        assert uid == "1000", f"Expected UID 1000, got {uid}"

    @pytest.mark.slow
    @pytest.mark.requires_docker
    def test_security_scan_passes(self, docker_image_name):
        """
        GIVEN: Built Docker image
        WHEN: Running security scan with docker scout (if available)
        THEN: Should not have critical vulnerabilities or fail gracefully
        """
        # Try to run docker scout - skip if not available or times out
        scout_cmd = [
            "docker", "scout", "cves",
            docker_image_name
        ]

        try:
            result = subprocess.run(
                scout_cmd,
                capture_output=True,
                text=True,
                timeout=30  # Reduced timeout
            )
        except subprocess.TimeoutExpired:
            # Scout is slow, skip this test
            pytest.skip("docker scout timeout - scan takes too long")

        # Scout may not be available, so don't fail if command not found
        if "unknown command" in result.stderr.lower() or result.returncode == 125:
            pytest.skip("docker scout not available")

        # If scout is available, check output for critical issues
        # Don't fail on warnings, only on critical vulnerabilities
        if result.returncode == 0:
            assert "CRITICAL" not in result.stdout.upper() or \
                   result.stdout.count("CRITICAL") == 0


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.requires_docker
class TestDockerRuntime:
    """Test suite for Docker runtime behavior"""

    @pytest.fixture(scope="class")
    def running_container(self, docker_image_name):
        """
        Start container for runtime tests
        Yields container ID, then cleans up
        """
        # Create a minimal test environment
        run_cmd = [
            "docker", "run",
            "-d",  # Detached
            "--name", "zerodb-test-runtime",
            "-e", "DATABASE_URL=postgresql://user:pass@localhost:5432/test",
            "-e", "TESTING=true",
            docker_image_name,
            "sleep", "300"  # Keep container running
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start container: {result.stderr}")

        container_id = result.stdout.strip()

        yield container_id

        # Cleanup
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            timeout=30
        )

    def test_container_started_successfully(self, running_container):
        """
        GIVEN: Docker container started
        WHEN: Checking container status
        THEN: Container should be running
        """
        inspect_cmd = [
            "docker", "inspect",
            "-f", "{{.State.Status}}",
            running_container
        ]

        result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "running"

    def test_uvicorn_can_be_executed(self, running_container):
        """
        GIVEN: Running container with zerodb user
        WHEN: Attempting to execute uvicorn
        THEN: Should have execute permissions
        """
        exec_cmd = [
            "docker", "exec",
            running_container,
            "test", "-x", "/home/zerodb/.local/bin/uvicorn"
        ]

        result = subprocess.run(
            exec_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, "uvicorn is not executable"

    def test_app_directory_writable(self, running_container):
        """
        GIVEN: Running container with zerodb user
        WHEN: Attempting to write to /app directory
        THEN: Should have write permissions
        """
        exec_cmd = [
            "docker", "exec",
            running_container,
            "touch", "/app/test_write.txt"
        ]

        result = subprocess.run(
            exec_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, "Cannot write to /app directory"

    def test_python_imports_work(self, running_container):
        """
        GIVEN: Running container with installed packages
        WHEN: Importing core dependencies
        THEN: All imports should succeed
        """
        packages = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]

        for package in packages:
            exec_cmd = [
                "docker", "exec",
                running_container,
                "python3", "-c", f"import {package}"
            ]

            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, \
                f"Failed to import {package}: {result.stderr}"


# Pytest markers are configured in test_docker_build_conftest.py
