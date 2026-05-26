from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Classification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


@dataclass
class Resource:
    path: str
    resource_type: str
    classification: Classification


@dataclass
class DelegatedPermission:
    grantor_id: str
    grantee_id: str
    permission: str
    resource_pattern: str
    granted_at: datetime


@dataclass
class Decision:
    allowed: bool
    principal_id: str
    resource: str
    action: str
    reason: str = ""
    roles_checked: list[str] = field(default_factory=list)


class RBACEnforcer:
    def __init__(self):
        self.resources: dict[str, Resource] = {}
        self.delegations: list[DelegatedPermission] = []

    def register_resource(self, resource: Resource):
        self.resources[resource.path] = resource

    def add_delegated_permission(self, delegation: DelegatedPermission):
        self.delegations.append(delegation)

    def check_permission(self, principal_id: str, resource: str, action: str, roles: list[str], permissions: set[str]) -> Decision:
        if "admin" in roles or ("data_consumer" in roles and action == "read"):
            return Decision(allowed=True, principal_id=principal_id, resource=resource, action=action, roles_checked=roles)
        
        for d in self.delegations:
            if d.grantee_id == principal_id and d.permission == f"datasets:{action}" and d.resource_pattern == resource:
                return Decision(allowed=True, principal_id=principal_id, resource=resource, action=action)

        if f"datasets:{action}" in permissions or "datasets:*" in permissions:
            return Decision(allowed=True, principal_id=principal_id, resource=resource, action=action)

        return Decision(allowed=False, principal_id=principal_id, resource=resource, action=action, reason="No matching permission")

    def get_accessible_resources(self, principal_id: str, resource_type: str, roles: list[str], permissions: set[str]) -> list[str]:
        return [path for path, res in self.resources.items() if res.resource_type == resource_type]
