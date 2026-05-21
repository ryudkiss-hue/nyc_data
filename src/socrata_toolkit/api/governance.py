from dataclasses import dataclass
from enum import Enum
from typing import Any

from .authorization import Classification


class PIIType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    NONE = "none"


class MaskingStrategy(Enum):
    MASK = "mask"
    REDACT = "redact"
    NONE = "none"


@dataclass
class AccessDecision:
    allowed: bool
    reason: str = ""


class GovernanceEnforcer:
    def __init__(self):
        self.policies: dict[str, dict[str, Any]] = {}
        self.pii_fields: dict[str, dict[str, Any]] = {}

    def set_policy(self, dataset_id: str, classification: Classification = Classification.PUBLIC):
        self.policies[dataset_id] = {"classification": classification}

    def add_pii_field(self, dataset_id: str, field_name: str, pii_type: PIIType, strategy: MaskingStrategy):
        if dataset_id not in self.pii_fields:
            self.pii_fields[dataset_id] = {}
        self.pii_fields[dataset_id][field_name] = {"type": pii_type, "strategy": strategy}

    def apply_masking(self, dataset_id: str, data: dict[str, Any], role: str) -> dict[str, Any]:
        if role == "admin":
            return data
        
        result = data.copy()
        fields = self.pii_fields.get(dataset_id, {})
        for field_name, info in fields.items():
            if field_name in result:
                val = str(result[field_name])
                if info["type"] == PIIType.EMAIL:
                    result[field_name] = "****@" + val.split("@")[-1] if "@" in val else "****"
                elif info["type"] == PIIType.PHONE:
                    result[field_name] = "****" + val[-4:] if len(val) >= 4 else "****"
                elif info["type"] == PIIType.SSN:
                    result[field_name] = "****" + val[-4:] if len(val) >= 4 else "****"
        return result

    def validate_access(self, dataset_id: str, role: str) -> AccessDecision:
        policy = self.policies.get(dataset_id, {})
        classification = policy.get("classification", Classification.PUBLIC)
        if classification == Classification.RESTRICTED and role != "admin":
            return AccessDecision(allowed=False, reason="Restricted access")
        return AccessDecision(allowed=True)

    def auto_detect_pii(self, dataset_id: str, records: list[dict[str, Any]]) -> dict[str, PIIType]:
        detected = {}
        if not records: return {}
        first = records[0]
        for k in first.keys():
            if "email" in k.lower(): detected[k] = PIIType.EMAIL
            elif "phone" in k.lower(): detected[k] = PIIType.PHONE
        return detected
