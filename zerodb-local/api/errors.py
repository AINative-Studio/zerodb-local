"""
Custom Error Classes
Defines error structures matching ZeroDB Cloud API format
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Single error detail"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response format matching cloud API"""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


class ZeroDBError(Exception):
    """Base exception for ZeroDB Local errors"""
    def __init__(
        self,
        message: str,
        error_type: str = "internal_error",
        details: Optional[List[ErrorDetail]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_type = error_type
        self.details = details or []
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(ZeroDBError):
    """Validation error (400)"""
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            error_type="validation_error",
            details=details,
            status_code=400
        )


class AuthenticationError(ZeroDBError):
    """Authentication error (401)"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_type="authentication_error",
            status_code=401
        )


class AuthorizationError(ZeroDBError):
    """Authorization error (403)"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_type="authorization_error",
            status_code=403
        )


class NotFoundError(ZeroDBError):
    """Resource not found error (404)"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            error_type="not_found_error",
            status_code=404
        )


class ConflictError(ZeroDBError):
    """Resource conflict error (409)"""
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            error_type="conflict_error",
            details=details,
            status_code=409
        )


class RateLimitError(ZeroDBError):
    """Rate limit exceeded error (429)"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_type="rate_limit_error",
            status_code=429
        )


class InternalError(ZeroDBError):
    """Internal server error (500)"""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            message=message,
            error_type="internal_error",
            status_code=500
        )


class ServiceUnavailableError(ZeroDBError):
    """Service unavailable error (503)"""
    def __init__(self, service: str):
        super().__init__(
            message=f"Service '{service}' is unavailable",
            error_type="service_unavailable_error",
            status_code=503
        )


# Cloud API specific errors
class CloudAPIAuthenticationError(ZeroDBError):
    """Cloud API authentication error (401)"""
    def __init__(self, message: str = "Cloud API authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_type="cloud_auth_error",
            status_code=401
        )
        self.api_details = details


class CloudAPIConnectionError(ZeroDBError):
    """Cloud API connection error"""
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(
            message=message,
            error_type="cloud_connection_error",
            status_code=503
        )
        self.url = url


class CloudAPINotFoundError(ZeroDBError):
    """Cloud API resource not found error (404)"""
    def __init__(self, message: str = "Resource not found in cloud", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_type="cloud_not_found_error",
            status_code=404
        )
        self.api_details = details


class CloudAPIServerError(ZeroDBError):
    """Cloud API server error (500+)"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_type="cloud_server_error",
            status_code=status_code
        )
        self.api_details = details


class CloudAPITimeoutError(ZeroDBError):
    """Cloud API timeout error"""
    def __init__(self, message: str, timeout: Optional[int] = None):
        super().__init__(
            message=message,
            error_type="cloud_timeout_error",
            status_code=504
        )
        self.timeout = timeout


class ImportError(ZeroDBError):
    """Import operation error"""
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            error_type="import_error",
            details=details,
            status_code=500
        )


# Error code mappings for database constraints
DATABASE_ERROR_CODES = {
    "23505": "duplicate_key",  # Unique violation
    "23503": "foreign_key_violation",
    "23502": "not_null_violation",
    "23514": "check_violation",
    "22001": "string_too_long",
}


def map_db_error_to_conflict(error: Exception) -> ConflictError:
    """
    Map database constraint errors to ConflictError

    Args:
        error: Database exception

    Returns:
        ConflictError with appropriate message
    """
    error_str = str(error)

    # Try to extract constraint name
    if "duplicate key" in error_str.lower():
        # Extract field name if possible
        if "DETAIL:" in error_str:
            detail_part = error_str.split("DETAIL:")[1].split("\n")[0].strip()
            return ConflictError(
                message="Resource already exists",
                details=[ErrorDetail(message=detail_part, code="duplicate_key")]
            )
        return ConflictError(message="Resource already exists")

    elif "foreign key" in error_str.lower():
        return ConflictError(
            message="Referenced resource does not exist",
            details=[ErrorDetail(message=error_str, code="foreign_key_violation")]
        )

    elif "not-null" in error_str.lower() or "null value" in error_str.lower():
        return ConflictError(
            message="Required field is missing",
            details=[ErrorDetail(message=error_str, code="not_null_violation")]
        )

    elif "check constraint" in error_str.lower():
        return ConflictError(
            message="Value does not meet constraints",
            details=[ErrorDetail(message=error_str, code="check_violation")]
        )

    # Generic conflict
    return ConflictError(message="Database constraint violation")
