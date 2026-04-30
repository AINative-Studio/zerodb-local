"""
Prerequisites checking utility for ZeroDB Local setup

Checks Docker installation, Python version, port availability, and disk space
before allowing setup to proceed.

Refs #1132
"""
import sys
import subprocess
import socket
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


def check_docker_installed() -> bool:
    """
    Check if Docker is installed and accessible

    Returns:
        bool: True if Docker is installed and running, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_docker_desktop_running() -> bool:
    """
    Check if Docker Desktop is running (not just Docker daemon)

    Returns:
        bool: True if Docker Desktop is running
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_python_version() -> Dict[str, any]:
    """
    Check if Python version meets minimum requirements (3.9+)

    Returns:
        dict: {
            'supported': bool,
            'version': str,
            'message': str (optional)
        }
    """
    version_info = sys.version_info
    version_str = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"

    supported = version_info >= (3, 9, 0)

    result = {
        'supported': supported,
        'version': version_str
    }

    if not supported:
        result['message'] = f"Python 3.9+ required, found {version_str}"

    return result


def check_port_available(port: int, host: str = 'localhost') -> bool:
    """
    Check if a port is available for binding

    Args:
        port: Port number to check
        host: Host address (default: localhost)

    Returns:
        bool: True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex((host, port))
            return result != 0  # 0 means port is in use
    except Exception:
        return False


def check_all_ports(ports: List[int]) -> Dict[str, any]:
    """
    Check availability of multiple ports

    Args:
        ports: List of port numbers to check

    Returns:
        dict: {
            'all_available': bool,
            'available': List[int],
            'in_use': List[int]
        }
    """
    available = []
    in_use = []

    for port in ports:
        if check_port_available(port):
            available.append(port)
        else:
            in_use.append(port)

    return {
        'all_available': len(in_use) == 0,
        'available': available,
        'in_use': in_use
    }


def check_disk_space(path: str = None, min_gb: int = 10) -> Dict[str, any]:
    """
    Check available disk space

    Args:
        path: Path to check (default: current directory)
        min_gb: Minimum required space in GB

    Returns:
        dict: {
            'sufficient': bool,
            'free_gb': float,
            'required_gb': int
        }
    """
    if path is None:
        path = Path.cwd()

    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)  # Convert bytes to GB

    return {
        'sufficient': free_gb >= min_gb,
        'free_gb': round(free_gb, 2),
        'required_gb': min_gb
    }


def check_prerequisites(project_root: Path = None) -> Dict[str, any]:
    """
    Check all prerequisites for ZeroDB Local setup

    Args:
        project_root: Project root directory

    Returns:
        dict: {
            'all_passed': bool,
            'docker': bool,
            'docker_running': bool,
            'python': dict,
            'ports': dict,
            'disk_space': dict,
            'errors': List[str],
            'warnings': List[str]
        }
    """
    errors = []
    warnings = []

    # Check Docker installation
    docker_installed = check_docker_installed()
    if not docker_installed:
        errors.append("Docker is not installed. Please install Docker Desktop from https://www.docker.com/products/docker-desktop")

    # Check Docker running
    docker_running = check_docker_desktop_running() if docker_installed else False
    if docker_installed and not docker_running:
        errors.append("Docker Desktop is not running. Please start Docker Desktop and try again.")

    # Check Python version
    python_check = check_python_version()
    if not python_check['supported']:
        errors.append(f"Python 3.9+ is required. Found {python_check['version']}")

    # Check required ports
    required_ports = [8000, 3000, 5432, 6333, 9000, 9001, 9092, 8082, 8001]
    ports_check = check_all_ports(required_ports)
    if not ports_check['all_available']:
        port_list = ', '.join(map(str, ports_check['in_use']))
        errors.append(f"Required ports are in use: {port_list}. Please stop services using these ports.")

    # Check disk space
    disk_check = check_disk_space(project_root, min_gb=10)
    if not disk_check['sufficient']:
        warnings.append(f"Low disk space: {disk_check['free_gb']}GB free. Recommended: {disk_check['required_gb']}GB or more.")

    all_passed = len(errors) == 0

    return {
        'all_passed': all_passed,
        'docker': docker_installed,
        'docker_running': docker_running,
        'python': python_check,
        'ports': ports_check,
        'disk_space': disk_check,
        'errors': errors,
        'warnings': warnings
    }
