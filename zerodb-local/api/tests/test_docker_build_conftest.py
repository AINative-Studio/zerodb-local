"""
Minimal pytest configuration for Docker build tests
Does not require application dependencies

Refs #1128
"""
import pytest


def pytest_configure(config):
    """
    Configure pytest markers for Docker tests
    """
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker"
    )
    config.addinivalue_line(
        "markers", "requires_docker: mark test as requiring Docker daemon"
    )
