"""
Error Handler Middleware
Global exception handler for consistent error responses
"""
import logging
import traceback
import uuid
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from errors import (
    ZeroDBError,
    ErrorResponse,
    ErrorDetail,
    InternalError,
    map_db_error_to_conflict
)


# Configure logging
logger = logging.getLogger(__name__)


async def zerodb_exception_handler(
    request: Request,
    exc: Union[Exception, ZeroDBError, StarletteHTTPException, RequestValidationError]
) -> JSONResponse:
    """
    Global exception handler for all requests

    Catches all exceptions and returns standardized error responses
    matching ZeroDB Cloud API format.

    Args:
        request: FastAPI request object
        exc: Exception to handle

    Returns:
        JSONResponse with error details
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())

    # Add request ID to response headers
    headers = {"X-Request-ID": request_id}

    # Handle ZeroDB custom errors
    if isinstance(exc, ZeroDBError):
        logger.warning(
            f"ZeroDB error: {exc.error_type} - {exc.message}",
            extra={
                "request_id": request_id,
                "path": str(request.url),
                "error_type": exc.error_type
            }
        )

        error_response = ErrorResponse(
            error=exc.error_type,
            message=exc.message,
            details=exc.details if exc.details else None,
            request_id=request_id
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle FastAPI RequestValidationError (Pydantic validation errors)
    if isinstance(exc, RequestValidationError):
        # Extract validation error details
        details = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
            details.append(
                ErrorDetail(
                    field=field if field else None,
                    message=error["msg"],
                    code=error["type"]
                )
            )

        logger.warning(
            f"Validation error: {len(details)} field(s)",
            extra={
                "request_id": request_id,
                "path": str(request.url),
                "fields": [d.field for d in details]
            }
        )

        error_response = ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details=details,
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle Pydantic validation errors
    if isinstance(exc, PydanticValidationError):
        details = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            details.append(
                ErrorDetail(
                    field=field,
                    message=error["msg"],
                    code=error["type"]
                )
            )

        error_response = ErrorResponse(
            error="validation_error",
            message="Data validation failed",
            details=details,
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle Starlette HTTP exceptions (raised by FastAPI)
    if isinstance(exc, StarletteHTTPException):
        # Map HTTP status codes to error types
        error_type_map = {
            400: "bad_request",
            401: "authentication_error",
            403: "authorization_error",
            404: "not_found_error",
            405: "method_not_allowed",
            409: "conflict_error",
            422: "validation_error",
            429: "rate_limit_error",
            500: "internal_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout"
        }

        error_type = error_type_map.get(exc.status_code, "http_error")

        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "request_id": request_id,
                "path": str(request.url),
                "status_code": exc.status_code
            }
        )

        error_response = ErrorResponse(
            error=error_type,
            message=str(exc.detail),
            request_id=request_id
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle database integrity errors (constraints, duplicates)
    if isinstance(exc, IntegrityError):
        logger.warning(
            f"Database integrity error: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": str(request.url)
            }
        )

        # Map to ConflictError
        conflict_error = map_db_error_to_conflict(exc)

        error_response = ErrorResponse(
            error=conflict_error.error_type,
            message=conflict_error.message,
            details=conflict_error.details if conflict_error.details else None,
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle database operational errors
    if isinstance(exc, OperationalError):
        logger.error(
            f"Database operational error: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": str(request.url)
            }
        )

        error_response = ErrorResponse(
            error="service_unavailable",
            message="Database service is temporarily unavailable",
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle ValueError (often from service layer)
    if isinstance(exc, ValueError):
        logger.warning(
            f"Value error: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": str(request.url)
            }
        )

        error_response = ErrorResponse(
            error="validation_error",
            message=str(exc),
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )

    # Handle all other exceptions as internal errors
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": str(request.url),
            "exception_type": type(exc).__name__
        },
        exc_info=True  # Include stack trace
    )

    # Log full stack trace for debugging
    logger.error(
        f"Stack trace for request {request_id}:\n{traceback.format_exc()}"
    )

    error_response = ErrorResponse(
        error="internal_error",
        message="An unexpected error occurred. Please try again or contact support.",
        request_id=request_id
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict(exclude_none=True),
        headers=headers
    )


def setup_error_handlers(app):
    """
    Register exception handlers with FastAPI app

    Args:
        app: FastAPI application instance
    """
    # Register handler for all exceptions
    app.add_exception_handler(Exception, zerodb_exception_handler)
    app.add_exception_handler(ZeroDBError, zerodb_exception_handler)
    app.add_exception_handler(StarletteHTTPException, zerodb_exception_handler)
    app.add_exception_handler(RequestValidationError, zerodb_exception_handler)
    app.add_exception_handler(PydanticValidationError, zerodb_exception_handler)
    app.add_exception_handler(IntegrityError, zerodb_exception_handler)
    app.add_exception_handler(OperationalError, zerodb_exception_handler)
    app.add_exception_handler(ValueError, zerodb_exception_handler)

    logger.info("Global error handlers registered")
