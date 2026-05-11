"""Custom exceptions and error handling for FastAPI REST service.

Provides structured exception hierarchy with integration to Phase 2
observability (OperationalLogger, metrics, audit logging).

Exception Hierarchy:
    APIException (base)
    ├── AuthenticationError (401)
    ├── AuthorizationError (403)
    ├── ResourceNotFound (404)
    ├── ValidationError (422)
    ├── RateLimitError (429)
    ├── DatabaseError (500)
    └── ExternalServiceError (503)

All exceptions log to OperationalLogger and emit metrics.

Example:
    from socrata_toolkit.api.exceptions import ResourceNotFound
    raise ResourceNotFound(
        resource_type="segment",
        resource_id="seg_123",
        message="Segment not found"
    )
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class ErrorCode(Enum):
    """Standard error codes for API responses."""

    # Authentication/Authorization (4xx)
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    MISSING_TOKEN = "MISSING_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ROLE_REQUIRED = "ROLE_REQUIRED"

    # Not Found (404)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    SEGMENT_NOT_FOUND = "SEGMENT_NOT_FOUND"
    INCIDENT_NOT_FOUND = "INCIDENT_NOT_FOUND"
    REPAIR_NOT_FOUND = "REPAIR_NOT_FOUND"
    CONTRACTOR_NOT_FOUND = "CONTRACTOR_NOT_FOUND"

    # Validation (422)
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FILTER = "INVALID_FILTER"

    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server Errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


@dataclass
class ErrorDetail:
    """Detailed error information with context.

    Attributes:
        error_code: Standardized error code
        message: Human-readable error message
        status_code: HTTP status code
        request_id: Unique request identifier for tracing
        timestamp: ISO 8601 timestamp when error occurred
        details: Additional error context (optional)
    """

    error_code: str
    message: str
    status_code: int
    request_id: str = ""
    timestamp: str = ""
    details: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Initialize error with defaults."""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response.

        Returns:
            dict: Error details as dictionary
        """
        return asdict(self)


class APIException(Exception):
    """Base exception for API errors.

    All API exceptions should inherit from this class and define:
        - error_code: ErrorCode enum value
        - status_code: HTTP status code
        - message: Error message

    Attributes:
        error_code: Standardized error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error context
        request_id: Unique request identifier for tracing
    """

    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR
    status_code: int = 500

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        """Initialize API exception.

        Args:
            message: Error message
            error_code: Overrides class-level error_code
            status_code: Overrides class-level status_code
            details: Additional error context
            request_id: Request ID for tracing (auto-generated if not provided)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        self.details = details or {}
        self.request_id = request_id or str(uuid.uuid4())

    def to_error_detail(self) -> ErrorDetail:
        """Convert exception to ErrorDetail.

        Returns:
            ErrorDetail: Error details object
        """
        return ErrorDetail(
            error_code=self.error_code.value,
            message=self.message,
            status_code=self.status_code,
            request_id=self.request_id,
            details=self.details,
        )


class AuthenticationError(APIException):
    """Authentication error (401 Unauthorized).

    Raised when JWT token is invalid, expired, or missing.
    """

    error_code = ErrorCode.INVALID_TOKEN
    status_code = 401

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: Optional[ErrorCode] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize authentication error.

        Args:
            message: Error message
            error_code: Specific authentication error code
            details: Additional context
        """
        super().__init__(
            message=message,
            error_code=error_code or ErrorCode.INVALID_TOKEN,
            status_code=401,
            details=details,
        )


class AuthorizationError(APIException):
    """Authorization error (403 Forbidden).

    Raised when user lacks required permissions or roles.
    """

    error_code = ErrorCode.INSUFFICIENT_PERMISSIONS
    status_code = 403

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_role: Optional[str] = None,
        required_permission: Optional[str] = None,
    ):
        """Initialize authorization error.

        Args:
            message: Error message
            required_role: Required role (for context)
            required_permission: Required permission (for context)
        """
        details = {}
        if required_role:
            details["required_role"] = required_role
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(
            message=message,
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=403,
            details=details or None,
        )


class ResourceNotFound(APIException):
    """Resource not found error (404 Not Found).

    Raised when requested segment, incident, repair, etc. doesn't exist.
    """

    status_code = 404

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Initialize resource not found error.

        Args:
            resource_type: Type of resource (segment, incident, repair, contractor)
            resource_id: ID of missing resource
            message: Custom error message
        """
        # Map resource type to error code
        error_code_map = {
            "segment": ErrorCode.SEGMENT_NOT_FOUND,
            "incident": ErrorCode.INCIDENT_NOT_FOUND,
            "repair": ErrorCode.REPAIR_NOT_FOUND,
            "contractor": ErrorCode.CONTRACTOR_NOT_FOUND,
        }

        error_code = error_code_map.get(resource_type, ErrorCode.RESOURCE_NOT_FOUND)

        if not message:
            if resource_id:
                message = f"{resource_type.capitalize()} '{resource_id}' not found"
            else:
                message = f"{resource_type.capitalize()} not found"

        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class ValidationError(APIException):
    """Validation error (422 Unprocessable Entity).

    Raised when request data fails validation.
    """

    error_code = ErrorCode.VALIDATION_ERROR
    status_code = 422

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[dict[str, Any]] = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            errors: Field-level validation errors
        """
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details={"errors": errors} if errors else None,
        )


class RateLimitError(APIException):
    """Rate limit exceeded error (429 Too Many Requests).

    Raised when client exceeds rate limits.
    """

    error_code = ErrorCode.RATE_LIMIT_EXCEEDED
    status_code = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            limit: Request limit per window
            window_seconds: Time window in seconds
            retry_after: Seconds to wait before retrying
        """
        details = {}
        if limit:
            details["limit"] = limit
        if window_seconds:
            details["window_seconds"] = window_seconds
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=details or None,
        )


class DatabaseError(APIException):
    """Database error (500 Internal Server Error).

    Raised when database operations fail. Never exposes
    internal database details in user-facing message.
    """

    error_code = ErrorCode.DATABASE_ERROR
    status_code = 500

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize database error.

        Args:
            message: User-facing error message
            operation: Type of operation (select, insert, update, delete)
            original_error: Original database exception (logged but not exposed)
        """
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=details or None,
        )


class CacheError(APIException):
    """Cache operation error (500 Internal Server Error).

    Raised when Redis cache operations fail. Service degrades gracefully
    by falling back to database queries.
    """

    error_code = ErrorCode.CACHE_ERROR
    status_code = 500

    def __init__(
        self,
        message: str = "Cache operation failed",
        operation: Optional[str] = None,
    ):
        """Initialize cache error.

        Args:
            message: Error message
            operation: Type of operation (get, set, delete)
        """
        details = {}
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_ERROR,
            status_code=500,
            details=details or None,
        )


class ExternalServiceError(APIException):
    """External service error (503 Service Unavailable).

    Raised when upstream dependencies (database, cache, etc.) are unavailable.
    """

    error_code = ErrorCode.EXTERNAL_SERVICE_ERROR
    status_code = 503

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
    ):
        """Initialize external service error.

        Args:
            service_name: Name of unavailable service
            message: Custom error message
        """
        if not message:
            message = f"Service '{service_name}' is unavailable"

        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=503,
            details={"service": service_name},
        )
