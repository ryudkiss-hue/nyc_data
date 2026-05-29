from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PipelineRequest:
    path: str
    method: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    ip_address: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIRequestPipeline:
    def __init__(self, auth_providers: list[Any], enforcer: Any, limiter: Any, governance: Any):
        self.auth_providers = auth_providers
        self.enforcer = enforcer
        self.limiter = limiter
        self.governance = governance

    def _extract_credentials(self, request: PipelineRequest) -> dict[str, str]:
        creds = {}
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            creds["token"] = auth[7:]

        key = request.headers.get("X-API-Key")
        if key:
            creds["api_key"] = key
        return creds

    def _get_action_from_method(self, method: str) -> str:
        mapping = {"GET": "read", "POST": "write", "DELETE": "delete", "PUT": "write"}
        return mapping.get(method.upper(), "read")
