"""API Request Processing Pipeline

Orchestrates the complete request lifecycle:
1. Authenticate (validate credentials)
2. Authorize (check permissions)
3. RateLimit (check quota)
4. Validate (schema, governance)
5. Mask (apply PII masking)
6. Execute (call handler)
7. AuditLog (record request)
8. Observe (emit metrics)

Example:
    from socrata_toolkit.api.request_pipeline import APIRequestPipeline
    
    pipeline = APIRequestPipeline(
        auth_providers=[jwt_provider, api_key_provider],
        enforcer=enforcer,
        limiter=limiter,
        governance=governance,
    )
    
    response = pipeline.process_request(request, handler_func)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PipelineRequest:
    """Normalized request object."""

    path: str
    method: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class PipelineResponse:
    """Pipeline response with metadata."""

    status_code: int
    data: Any
    headers: Dict[str, str] = None
    latency_ms: float = 0.0
    request_id: str = ""
    errors: List[str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.errors is None:
            self.errors = []


class APIRequestPipeline:
    """Main request processing pipeline."""

    def __init__(
        self,
        auth_providers: List[Any],
        enforcer: Any,
        limiter: Any,
        governance: Any,
        enable_audit: bool = True,
        enable_metrics: bool = True,
    ) -> None:
        """Initialize pipeline."""
        self.auth_providers = auth_providers
        self.enforcer = enforcer
        self.limiter = limiter
        self.governance = governance
        self.enable_audit = enable_audit
        self.enable_metrics = enable_metrics

    def process_request(
        self,
        request: PipelineRequest,
        handler: Callable[[Dict[str, Any]], Any],
    ) -> PipelineResponse:
        """Process complete request lifecycle.

        Args:
            request: Normalized request
            handler: Request handler function

        Returns:
            PipelineResponse: Response with metadata
        """
        start_time = time.time()
        request_id = self._generate_request_id()
        response = None

        try:
            # 1. AUTHENTICATE
            auth_context = self._authenticate(request, request_id)
            logger.debug(f"[{request_id}] Authenticated: {auth_context.principal_id}")

            # 2. AUTHORIZE
            self._authorize(request, auth_context, request_id)
            logger.debug(f"[{request_id}] Authorized")

            # 3. RATE LIMIT
            self._check_rate_limit(auth_context.principal_id, request_id)
            logger.debug(f"[{request_id}] Rate limit passed")

            # 4. VALIDATE
            self._validate_request(request, auth_context, request_id)
            logger.debug(f"[{request_id}] Validation passed")

            # 5. MASK (PII)
            masked_body = self._apply_masking(request, auth_context, request_id)

            # 6. EXECUTE
            data = handler({"body": masked_body, "context": auth_context})
            logger.debug(f"[{request_id}] Handler executed")

            # 7. AUDIT LOG
            latency = (time.time() - start_time) * 1000
            self._log_audit(request, auth_context, "success", request_id, latency)

            # 8. OBSERVE
            self._emit_metrics(request, auth_context, "success", latency, request_id)

            # Mask response if needed
            masked_response = self._mask_response(data, auth_context, request_id)

            response = PipelineResponse(
                status_code=200,
                data=masked_response,
                latency_ms=latency,
                request_id=request_id,
            )

            # Add quota headers
            quota_headers = self.limiter.get_quota_headers(auth_context.principal_id)
            response.headers.update(quota_headers)

            return response

        except Exception as e:
            latency = (time.time() - start_time) * 1000

            # Log error
            logger.error(f"[{request_id}] Pipeline error: {str(e)}", exc_info=True)
            self._log_audit(
                request, 
                getattr(self, "_last_auth_context", None),
                "failure",
                request_id,
                latency,
                error=str(e),
            )
            self._emit_metrics(
                request,
                getattr(self, "_last_auth_context", None),
                "failure",
                latency,
                request_id,
            )

            return PipelineResponse(
                status_code=500,
                data={"error": "Internal server error"},
                latency_ms=latency,
                request_id=request_id,
                errors=[str(e)],
            )

    def _authenticate(
        self,
        request: PipelineRequest,
        request_id: str,
    ) -> Any:
        """Authenticate request using available providers."""
        # Extract credentials from request
        credentials = self._extract_credentials(request)
        if not credentials:
            raise ValueError("No authentication credentials provided")

        # Try each provider
        for provider in self.auth_providers:
            try:
                context = provider.authenticate(credentials)
                self._last_auth_context = context
                logger.debug(f"[{request_id}] Auth via {context.auth_method}")
                return context
            except Exception:
                continue

        raise ValueError("Authentication failed with all providers")

    def _authorize(
        self,
        request: PipelineRequest,
        auth_context: Any,
        request_id: str,
    ) -> None:
        """Check authorization for request."""
        # Extract resource and action from request
        resource = request.path
        action = self._get_action_from_method(request.method)

        # Check permission
        decision = self.enforcer.check_permission(
            principal_id=auth_context.principal_id,
            resource=resource,
            action=action,
            roles=auth_context.roles,
            permissions=auth_context.permissions,
        )

        if not decision.allowed:
            raise PermissionError(f"Access denied: {decision.reason}")

    def _check_rate_limit(self, user_id: str, request_id: str) -> None:
        """Check if user is within rate limits."""
        if not self.limiter.check_rate_limit(user_id):
            logger.warning(f"[{request_id}] Rate limit exceeded for {user_id}")
            raise Exception(f"Rate limit exceeded")

    def _validate_request(
        self,
        request: PipelineRequest,
        auth_context: Any,
        request_id: str,
    ) -> None:
        """Validate request data."""
        # Could validate against schema registry (W1)
        # For now, just basic validation
        if request.body is None and request.method in ("POST", "PUT", "PATCH"):
            raise ValueError("Request body required")

    def _apply_masking(
        self,
        request: PipelineRequest,
        auth_context: Any,
        request_id: str,
    ) -> Dict[str, Any]:
        """Apply PII masking to request body."""
        if not request.body:
            return {}

        # Extract dataset_id from request path
        dataset_id = self._extract_dataset_id(request.path)
        if not dataset_id:
            return request.body

        # Apply masking
        user_role = auth_context.roles[0] if auth_context.roles else "guest"
        masked = self.governance.apply_masking(dataset_id, request.body, user_role)
        return masked

    def _mask_response(
        self,
        data: Any,
        auth_context: Any,
        request_id: str,
    ) -> Any:
        """Apply masking to response data."""
        if isinstance(data, dict) and "records" in data:
            # Mask records list
            dataset_id = data.get("dataset_id")
            if dataset_id:
                user_role = auth_context.roles[0] if auth_context.roles else "guest"
                data["records"] = self.governance.mask_response(
                    dataset_id, data["records"], user_role
                )
        return data

    def _log_audit(
        self,
        request: PipelineRequest,
        auth_context: Optional[Any],
        result: str,
        request_id: str,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log to audit trail."""
        if not self.enable_audit or not auth_context:
            return

        logger.info(
            f"[{request_id}] {request.method} {request.path} - {result}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "user_id": auth_context.principal_id,
                "result": result,
                "latency_ms": latency_ms,
                "error": error,
            },
        )

    def _emit_metrics(
        self,
        request: PipelineRequest,
        auth_context: Optional[Any],
        result: str,
        latency_ms: float,
        request_id: str,
    ) -> None:
        """Emit metrics to observability system."""
        if not self.enable_metrics or not auth_context:
            return

        # Record usage
        self.limiter.record_request(
            user_id=auth_context.principal_id,
            latency_ms=latency_ms,
            success=(result == "success"),
        )

    def _extract_credentials(self, request: PipelineRequest) -> Dict[str, Any]:
        """Extract credentials from request headers."""
        credentials = {}

        # Try JWT in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            credentials["token"] = auth_header[7:]
            return credentials

        # Try API key in Authorization header
        if auth_header.startswith("ApiKey "):
            credentials["api_key"] = auth_header[7:]
            return credentials

        # Try API key in X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            credentials["api_key"] = api_key
            return credentials

        # Try Basic auth
        if auth_header.startswith("Basic "):
            import base64
            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                username, password = decoded.split(":", 1)
                credentials["username"] = username
                credentials["password"] = password
                return credentials
            except Exception:
                pass

        return credentials

    def _get_action_from_method(self, method: str) -> str:
        """Convert HTTP method to action."""
        method_to_action = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
        }
        return method_to_action.get(method, "read")

    def _extract_dataset_id(self, path: str) -> Optional[str]:
        """Extract dataset ID from request path."""
        # Example: /api/v1/datasets/xyz/records -> xyz
        parts = path.split("/")
        try:
            if "datasets" in parts:
                idx = parts.index("datasets")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except (ValueError, IndexError):
            pass
        return None

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())[:8]
