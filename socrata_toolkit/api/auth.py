"""JWT authentication and role-based access control (RBAC).

Provides JWT token generation/verification, user context extraction,
and role-based access control for protecting endpoints.

Key Components:
    - JWTConfig: JWT configuration and signing
    - User: User context with roles and permissions
    - create_access_token(): Generate JWT token
    - verify_token(): Validate and extract JWT
    - require_auth(): FastAPI dependency for protected endpoints
    - require_role(): Decorator to enforce role requirements

Roles:
    - VIEWER: Read-only access (GET endpoints)
    - ANALYST: Read + export (GET, POST export)
    - ADMIN: Full access (all methods)

Example:
    from socrata_toolkit.api.auth import create_access_token, require_auth
    token = create_access_token(user_id="user_123", roles=["analyst"])
    
    @app.get("/protected")
    def protected_endpoint(current_user: User = Depends(require_auth)):
        return {"user": current_user.user_id}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Set
import uuid

try:
    from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
    HAS_JWT = True
except ImportError:
    HAS_JWT = False


class Role(str, Enum):
    """User roles for RBAC."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class Permission(str, Enum):
    """Fine-grained permissions."""

    # Read operations
    READ_SEGMENTS = "read:segments"
    READ_INCIDENTS = "read:incidents"
    READ_REPAIRS = "read:repairs"
    READ_KPIS = "read:kpis"
    READ_CONTRACTORS = "read:contractors"
    READ_AUDIT_LOGS = "read:audit_logs"

    # Write operations (analyst+)
    WRITE_REPAIRS = "write:repairs"
    UPDATE_REPAIR_STATUS = "update:repair_status"
    ASSIGN_REPAIR = "assign:repair"

    # Delete operations (admin only)
    DELETE_INCIDENTS = "delete:incidents"
    DELETE_REPAIRS = "delete:repairs"

    # Export operations (analyst+)
    EXPORT_DATA = "export:data"


# Map roles to permissions
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_SEGMENTS,
        Permission.READ_INCIDENTS,
        Permission.READ_REPAIRS,
        Permission.READ_KPIS,
        Permission.READ_CONTRACTORS,
        Permission.READ_AUDIT_LOGS,
    },
    Role.ANALYST: {
        Permission.READ_SEGMENTS,
        Permission.READ_INCIDENTS,
        Permission.READ_REPAIRS,
        Permission.READ_KPIS,
        Permission.READ_CONTRACTORS,
        Permission.READ_AUDIT_LOGS,
        Permission.WRITE_REPAIRS,
        Permission.UPDATE_REPAIR_STATUS,
        Permission.ASSIGN_REPAIR,
        Permission.EXPORT_DATA,
    },
    Role.ADMIN: set(Permission),  # All permissions
}


@dataclass
class User:
    """Authenticated user context.

    Attributes:
        user_id: Unique user identifier
        email: User email address
        roles: List of role assignments
        permissions: Computed permissions based on roles
    """

    user_id: str
    email: str
    roles: List[Role] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Compute permissions from roles."""
        self.permissions = set()
        for role in self.roles:
            self.permissions.update(ROLE_PERMISSIONS.get(role, set()))

    def has_role(self, role: Role) -> bool:
        """Check if user has specific role.

        Args:
            role: Role to check

        Returns:
            bool: True if user has role
        """
        return role in self.roles

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission.

        Args:
            permission: Permission to check

        Returns:
            bool: True if user has permission
        """
        return permission in self.permissions

    def has_any_role(self, *roles: Role) -> bool:
        """Check if user has any of specified roles.

        Args:
            *roles: Roles to check

        Returns:
            bool: True if user has any role
        """
        return any(role in self.roles for role in roles)

    def to_dict(self) -> dict:
        """Convert user to dictionary (for JWT payload).

        Returns:
            dict: User data for JWT encoding
        """
        return {
            "user_id": self.user_id,
            "email": self.email,
            "roles": [role.value for role in self.roles],
        }


@dataclass
class JWTConfig:
    """JWT configuration.

    Attributes:
        secret_key: Secret key for signing (min 32 chars for HS256)
        algorithm: JWT algorithm (HS256, HS512, RS256)
        expiry_minutes: Token expiry in minutes
    """

    secret_key: str
    algorithm: str = "HS256"
    expiry_minutes: int = 24 * 60  # 24 hours

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not HAS_JWT:
            raise ImportError("PyJWT is required for JWT functionality")

        if len(self.secret_key) < 8:
            raise ValueError("Secret key must be at least 8 characters")

        if self.algorithm not in ("HS256", "HS512", "RS256"):
            raise ValueError(f"Invalid algorithm: {self.algorithm}")

        if self.expiry_minutes < 1:
            raise ValueError("Expiry must be at least 1 minute")


def create_access_token(
    user: User,
    config: JWTConfig,
    expires_delta: Optional[timedelta] = None,
    request_id: Optional[str] = None,
) -> str:
    """Generate JWT access token for user.

    Args:
        user: User object to encode in token
        config: JWT configuration
        expires_delta: Custom expiry (uses config default if None)
        request_id: Request ID for tracing

    Returns:
        str: Encoded JWT token

    Raises:
        ValueError: If configuration is invalid

    Example:
        >>> config = JWTConfig(secret_key="very-secret-key-at-least-32-chars-long")
        >>> user = User(user_id="user_123", email="user@example.com", roles=[Role.ANALYST])
        >>> token = create_access_token(user, config)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    if not expires_delta:
        expires_delta = timedelta(minutes=config.expiry_minutes)

    expire = datetime.utcnow() + expires_delta
    request_id = request_id or str(uuid.uuid4())

    payload = {
        **user.to_dict(),
        "exp": expire,
        "iat": datetime.utcnow(),
        "request_id": request_id,
    }

    return encode(payload, config.secret_key, algorithm=config.algorithm)


def verify_token(token: str, config: JWTConfig) -> dict:
    """Verify and decode JWT token.

    Args:
        token: JWT token string
        config: JWT configuration

    Returns:
        dict: Decoded token payload

    Raises:
        ExpiredSignatureError: If token has expired
        InvalidTokenError: If token is invalid
    """
    try:
        payload = decode(token, config.secret_key, algorithms=[config.algorithm])
        return payload
    except ExpiredSignatureError:
        raise Exception("Token has expired")
    except InvalidTokenError as e:
        raise Exception(f"Invalid token: {str(e)}")


def extract_bearer_token(auth_header: Optional[str]) -> str:
    """Extract bearer token from Authorization header.

    Args:
        auth_header: Authorization header value (e.g., "Bearer eyJ...")

    Returns:
        str: Token string without "Bearer " prefix

    Raises:
        ValueError: If header format is invalid
    """
    if not auth_header:
        raise ValueError("Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid Authorization header format (expected: Bearer <token>)")

    return parts[1]


def token_from_payload(payload: dict) -> User:
    """Convert JWT payload to User object.

    Args:
        payload: Decoded JWT payload

    Returns:
        User: User object with roles and permissions

    Raises:
        ValueError: If payload is missing required fields
    """
    user_id = payload.get("user_id")
    email = payload.get("email")
    roles_str = payload.get("roles", [])

    if not user_id or not email:
        raise ValueError("Invalid token: missing user_id or email")

    roles = [Role(role) for role in roles_str]
    return User(user_id=user_id, email=email, roles=roles)


# Example function for FastAPI dependency injection
async def require_auth(
    auth_header: Optional[str] = None,
    config: Optional[JWTConfig] = None,
) -> User:
    """FastAPI dependency to require authentication.

    Usage in routes:
        from fastapi import Depends, Header
        @app.get("/protected")
        async def protected(
            current_user: User = Depends(require_auth)
        ):
            return {"user_id": current_user.user_id}

    Args:
        auth_header: Authorization header from request
        config: JWT configuration (usually from app state)

    Returns:
        User: Authenticated user object

    Raises:
        Exception: If authentication fails
    """
    from socrata_toolkit.api.exceptions import AuthenticationError

    if not config:
        raise AuthenticationError("JWT config not configured")

    try:
        token = extract_bearer_token(auth_header)
        payload = verify_token(token, config)
        user = token_from_payload(payload)
        return user
    except Exception as e:
        raise AuthenticationError(str(e))


def require_role(*required_roles: Role):
    """Decorator to require specific roles.

    Usage:
        @app.post("/repairs/{repair_id}/status")
        @require_role(Role.ANALYST, Role.ADMIN)
        async def update_repair_status(
            repair_id: str,
            current_user: User = Depends(require_auth)
        ):
            return {"status": "updated"}

    Args:
        *required_roles: Roles allowed to access endpoint

    Returns:
        function: Decorator function
    """

    def decorator(func):
        async def wrapper(*args, current_user: User = None, **kwargs):
            from socrata_toolkit.api.exceptions import AuthorizationError

            if not current_user:
                raise AuthorizationError("User context not found")

            if not current_user.has_any_role(*required_roles):
                raise AuthorizationError(
                    f"This operation requires one of: {', '.join(r.value for r in required_roles)}",
                    required_role=required_roles[0].value,
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator


def require_permission(permission: Permission):
    """Decorator to require specific permission.

    Usage:
        @app.post("/export/segments")
        @require_permission(Permission.EXPORT_DATA)
        async def export_segments(current_user: User = Depends(require_auth)):
            return {"export": "data"}

    Args:
        permission: Permission required to access endpoint

    Returns:
        function: Decorator function
    """

    def decorator(func):
        async def wrapper(*args, current_user: User = None, **kwargs):
            from socrata_toolkit.api.exceptions import AuthorizationError

            if not current_user:
                raise AuthorizationError("User context not found")

            if not current_user.has_permission(permission):
                raise AuthorizationError(
                    f"This operation requires permission: {permission.value}",
                    required_permission=permission.value,
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
