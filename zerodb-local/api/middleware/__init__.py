"""
Middleware Package
Exports middleware components for the ZeroDB Local API
"""
from .error_handler import setup_error_handlers, zerodb_exception_handler

__all__ = [
    "setup_error_handlers",
    "zerodb_exception_handler"
]
