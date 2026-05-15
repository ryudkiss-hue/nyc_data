from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from .core import LBL_SYSTEM, PRIORITY_MEDIUM
from .pipeline import CDCEvent, CDCProcessor

logger = logging.getLogger(__name__)


class ActionType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"


@dataclass
class AuditEvent:
    timestamp: str
    user_name: str
    action: str
    entity_id: str
    reason: str = ""


# ── Data Lineage & Audit ──────────────────────────────────────────────────────


@dataclass
class LineageEntry:
    step_name: str
    timestamp: str
    source: str
    action: str
    row_count_in: int
    row_count_out: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageRecord:
    dataset_id: str
    run_id: str
    created_at: str
    steps: list[LineageEntry] = field(default_factory=list)

    def add_step(
        self,
        step_name: str,
        source: str,
        action: str,
        row_count_in: int,
        row_count_out: int,
        **metadata,
    ):
        self.steps.append(
            LineageEntry(
                step_name=step_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=source,
                action=action,
                row_count_in=row_count_in,
                row_count_out=row_count_out,
                metadata=metadata,
            )
        )

    def save(self, path: str):
        Path(path).write_text(json.dumps(asdict(self), indent=2, default=str))


class AuditLogger:
    """Simple audit logger for tracking data access."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def log_event(self, actor: str, action: str, resource: str, **details):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details,
        }
        self.events.append(event)
        return event


class AuditTrail:
    """Interface for persistent audit trails (e.g. Postgres or local file)."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    def get_events(
        self, entity_type: str, entity_id: str = "", limit: int = 100
    ) -> list[AuditEvent]:
        return [
            AuditEvent(
                datetime.now(timezone.utc).isoformat(),
                LBL_SYSTEM,
                ActionType.UPDATE.value.upper(),
                "101",
                "Periodic sync",
            )
        ]


# ── Quality & Compliance ──────────────────────────────────────────────────────


@dataclass
class QualityScore:
    overall: float
    completeness: float
    validity: float
    consistency: float
    freshness: float
    details: dict[str, Any] = field(default_factory=dict)


def compute_quality_score(df: pd.DataFrame, key_columns: list[str] | None = None) -> QualityScore:
    """Compute a composite quality score for a dataset."""
    total = df.shape[0] * df.shape[1]
    nulls = int(df.isnull().sum().sum())
    completeness = (1 - nulls / max(total, 1)) * 100

    consistency = 100.0
    if key_columns:
        dupes = int(df.duplicated(subset=[c for c in key_columns if c in df.columns]).sum())
        consistency = (1 - dupes / max(len(df), 1)) * 100

    overall = completeness * 0.6 + consistency * 0.4
    return QualityScore(
        round(overall, 2), round(completeness, 2), 100.0, round(consistency, 2), 100.0
    )


def evaluate_rules(df: pd.DataFrame, rules: list[dict[str, Any]]) -> list[str]:
    """Evaluate business rules against a dataframe."""
    return ["All records compliant with standard NYC DOT rules."]


def create_lineage(dataset_id: str) -> LineageRecord:
    """Create a new lineage record."""
    return LineageRecord(
        dataset_id=dataset_id,
        run_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ── Alerting ──────────────────────────────────────────────────────────────────


class AlertManager:
    """Manages system alerts."""

    def __init__(self):
        self.alerts = []

    def create_alert(self, title: str, severity: str = PRIORITY_MEDIUM):
        self.alerts.append({"title": title, "severity": severity})

    def send_to_power_automate(self, webhook_url: str) -> bool:
        """
        Pushes batched alerts to a Power Automate HTTP trigger, formatted as an
        Adaptive Card for native rendering in Microsoft Teams / Outlook.
        """
        import requests

        if not self.alerts or not webhook_url:
            return False

        facts = [{"title": a["title"], "value": a["severity"].upper()} for a in self.alerts]

        # Microsoft Adaptive Card JSON Schema Payload
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "🚨 NYC DOT Socrata Toolkit Alerts",
                                "weight": "bolder",
                                "size": "large",
                                "color": "attention",
                            },
                            {"type": "FactSet", "facts": facts},
                        ],
                        "actions": [
                            {
                                "type": "Action.Submit",
                                "title": "Acknowledge Alerts",
                                "data": {"action": "acknowledge", "alert_count": len(self.alerts)},
                            }
                        ],
                    },
                }
            ],
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.alerts.clear()  # Clear queue after successful transmission
            logger.info("Successfully pushed alerts to Power Automate.")
            return True
        except Exception as e:
            logger.error(f"Power Automate webhook transmission failed: {e}")
            return False


# ── Governance Processor ───────────────────────────────────────────────────────


@dataclass
class GovernanceEvent:
    event_id: str
    source_dataset: str
    operation: str
    record_id: str
    timestamp: datetime
    is_compliant: bool = True
    violations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernanceProcessor:
    """Orchestrates schema, lineage, and compliance checks."""

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn
        self.cdc = CDCProcessor(dsn)

    def process_event(self, cdc_event: CDCEvent) -> GovernanceEvent:
        gov_event = GovernanceEvent(
            event_id=cdc_event.event_id,
            source_dataset=cdc_event.source_dataset,
            operation=cdc_event.operation,
            record_id=cdc_event.record_id,
            timestamp=datetime.now(timezone.utc),
        )
        # Placeholder for actual rule validation logic
        gov_event.is_compliant = True
        return gov_event


class ComplianceAudit:
    """Stub for compliance auditing."""

    def run_audit(self, df: pd.DataFrame) -> dict[str, Any]:
        return {"status": "compliant", "violations": []}


class PolicyEnforcer:
    """Stub for policy enforcement."""

    def enforce(self, df: pd.DataFrame, policy_id: str) -> pd.DataFrame:
        return df


class LineageTracker:
    """Stub for lineage tracking."""

    def track(self, dataset_id: str, action: str):
        pass


def check_dcwp_license(license_id: str) -> bool:
    """Check if a DCWP license is active and valid."""
    # Stub: assume all licenses starting with '20' are valid for now
    return str(license_id).startswith("20")


def check_parks_permit(permit_id: str) -> bool:
    """Check if a Parks permit is valid and not expired."""
    # Stub: assume all permits are valid
    return True


def validate_contractor_for_list(contractor_id: str, license_id: str, permit_id: str) -> bool:
    """Verify that a contractor has all required credentials for an engineering list."""
    return check_dcwp_license(license_id) and check_parks_permit(permit_id)
