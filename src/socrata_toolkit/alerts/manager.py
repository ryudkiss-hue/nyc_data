"""Alerting and notification utilities.

This module implements a lightweight Observer pattern for operational alerts.
It supports CLI, Email, and Postgres-based persistence.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol

try:
    from rich import print as rprint
except ImportError:  # pragma: no cover
    rprint = print

log = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels for operational alerts."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Status of an operational alert."""

    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents a single operational alert."""

    alert_id: str
    severity: AlertSeverity
    message: str
    alert_type: str
    timestamp: str
    status: AlertStatus = AlertStatus.NEW
    payload: dict[str, Any] = field(default_factory=dict)
    dataset_name: str = ""
    check_name: str = ""
    # Legacy field — kept for backward compatibility with CLINotifier/EmailNotifier
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        severity: AlertSeverity,
        message: str,
        alert_type: str,
        payload: dict[str, Any],
        dataset_name: str = "",
        check_name: str = "",
    ) -> Alert:
        """Factory method that auto-generates alert_id and timestamp."""
        return cls(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            message=message,
            alert_type=alert_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=AlertStatus.NEW,
            payload=payload,
            dataset_name=dataset_name,
            check_name=check_name,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to a plain dict."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value
            if isinstance(self.severity, AlertSeverity)
            else self.severity,
            "message": self.message,
            "alert_type": self.alert_type,
            "timestamp": self.timestamp,
            "status": self.status.value if isinstance(self.status, AlertStatus) else self.status,
            "payload": self.payload,
            "dataset_name": self.dataset_name,
            "check_name": self.check_name,
        }


class Subscriber(Protocol):
    """Protocol that alert subscribers must implement."""

    def notify(self, alert: Alert) -> None: ...


class AlertManager:
    """Manages alert lifecycle: ingestion, acknowledgement, resolution, and persistence.

    Supports two usage modes:
    - New API (used by Monitoring): ingest_alert / acknowledge_alert / resolve_alert
    - Legacy Observer API: register / emit (for CLINotifier / EmailNotifier / DBNotifier)
    """

    def __init__(
        self,
        duckdb_conn: Any = None,
        batch_mode: bool = False,
        batch_interval: float = 30.0,
    ):
        # New API state
        self.alerts: dict[str, Alert] = {}
        self.alert_history: list[dict[str, Any]] = []
        self.notification_handlers: list[Callable[[Alert], None]] = []
        self.duckdb_conn = duckdb_conn

        # Legacy Observer state
        self.subscribers: list[Subscriber] = []
        self.lock = threading.Lock()
        self.batch_mode = batch_mode
        self.batch_interval = batch_interval
        self._batch: list[Alert] = []
        self._stop = False
        if self.batch_mode:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    # ------------------------------------------------------------------
    # New lifecycle API
    # ------------------------------------------------------------------

    def ingest_alert(self, alert: Alert) -> None:
        """Ingest an alert, record history, and notify handlers."""
        self.alerts[alert.alert_id] = alert
        self.alert_history.append(
            {
                "event": "ingested",
                "alert_id": alert.alert_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log.error("Notification handler error: %s", exc)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert by ID. Returns True on success."""
        if alert_id not in self.alerts:
            return False
        self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
        self.alert_history.append(
            {
                "event": "acknowledged",
                "alert_id": alert_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert by ID. Returns True on success."""
        if alert_id not in self.alerts:
            return False
        self.alerts[alert_id].status = AlertStatus.RESOLVED
        self.alert_history.append(
            {
                "event": "resolved",
                "alert_id": alert_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True

    def get_alerts_by_status(self, status: AlertStatus) -> list[Alert]:
        """Return all alerts with the given status."""
        return [a for a in self.alerts.values() if a.status == status]

    def get_active_alerts(self) -> list[Alert]:
        """Return all non-resolved alerts."""
        return [a for a in self.alerts.values() if a.status != AlertStatus.RESOLVED]

    def get_alert_summary(self) -> dict[str, int]:
        """Return count of active (non-resolved) alerts by severity name."""
        summary: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for alert in self.alerts.values():
            if alert.status == AlertStatus.RESOLVED:
                continue
            sev_name = (
                alert.severity.value
                if isinstance(alert.severity, AlertSeverity)
                else str(alert.severity)
            )
            if sev_name in summary:
                summary[sev_name] += 1
        return summary

    def register_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a callable that will be invoked on each ingested alert."""
        self.notification_handlers.append(handler)

    # ------------------------------------------------------------------
    # DuckDB persistence
    # ------------------------------------------------------------------

    _CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS monitoring_alerts (
        alert_id TEXT PRIMARY KEY,
        severity TEXT,
        message TEXT,
        alert_type TEXT,
        timestamp TEXT,
        status TEXT,
        payload TEXT,
        dataset_name TEXT,
        check_name TEXT
    )
    """

    def save_to_duckdb(self) -> bool:
        """Persist current alerts to DuckDB. Returns True on success."""
        if self.duckdb_conn is None:
            return False
        try:
            self.duckdb_conn.execute(self._CREATE_TABLE_SQL)
            for alert in self.alerts.values():
                d = alert.to_dict()
                self.duckdb_conn.execute(
                    """
                    INSERT OR REPLACE INTO monitoring_alerts
                        (alert_id, severity, message, alert_type, timestamp, status, payload, dataset_name, check_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d["alert_id"],
                        d["severity"],
                        d["message"],
                        d["alert_type"],
                        d["timestamp"],
                        d["status"],
                        json.dumps(d["payload"]),
                        d["dataset_name"],
                        d["check_name"],
                    ),
                )
            return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log.error("Failed to save alerts to DuckDB: %s", exc)
            return False

    def query_alerts_from_duckdb(self) -> list[dict[str, Any]]:
        """Load alerts from DuckDB. Returns list of dicts, or [] if unavailable."""
        if self.duckdb_conn is None:
            return []
        try:
            result = self.duckdb_conn.execute("SELECT * FROM monitoring_alerts").fetchall()
            return [dict(row) for row in result] if result else []
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log.error("Failed to query alerts from DuckDB: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Legacy Observer API (preserved for CLINotifier / EmailNotifier / DBNotifier)
    # ------------------------------------------------------------------

    def register(self, s: Subscriber) -> None:
        """Register a new subscriber (legacy Observer API)."""
        with self.lock:
            self.subscribers.append(s)

    def unregister(self, s: Subscriber) -> None:
        """Unregister a subscriber (legacy Observer API)."""
        with self.lock:
            try:
                self.subscribers.remove(s)
            except ValueError:
                pass

    def emit(self, alert: Alert) -> None:
        """Emit an alert (legacy Observer API)."""
        if self.batch_mode:
            with self.lock:
                self._batch.append(alert)
        else:
            self._dispatch(alert)

    def _dispatch(self, alert: Alert) -> None:
        for s in list(self.subscribers):
            try:
                s.notify(alert)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log.error("Failed to dispatch alert to subscriber %s: %s", s, exc)

    def _worker(self) -> None:
        while not self._stop:
            try:
                time.sleep(self.batch_interval)
                with self.lock:
                    batch, self._batch = self._batch, []
                if not batch:
                    continue
                for alert in batch:
                    self._dispatch(alert)
            except Exception as exc:
                log.error("AlertManager worker thread error: %s", exc)

    def shutdown(self) -> None:
        """Stop background thread and flush (legacy batch mode)."""
        try:
            self._stop = True
            if self.batch_mode and getattr(self, "_thread", None):
                self._thread.join(timeout=1.0)
            with self.lock:
                batch, self._batch = self._batch, []
            for alert in batch:
                self._dispatch(alert)
        except Exception as exc:
            log.error("Error during AlertManager shutdown: %s", exc)


class CLINotifier:
    """Prints alerts to the console."""

    def __init__(self, show_payload: bool = True):
        self.show_payload = show_payload

    def notify(self, alert: Alert) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(alert.created_at))
        sev = (
            alert.severity.value
            if isinstance(alert.severity, AlertSeverity)
            else str(alert.severity)
        )
        header = f"[{sev.upper()}] {ts} - {alert.message}"
        try:
            rprint(header)
            if self.show_payload and alert.payload:
                rprint(json.dumps(alert.payload, indent=2, default=str))
        except Exception:  # pylint: disable=broad-exception-caught
            print(header)
            if self.show_payload and alert.payload:
                print(alert.payload)


class EmailNotifier:
    """Sends alerts via SMTP."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def _send_email(self, subject: str, body: str, recipients: list[str]) -> None:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.get("from_addr")
        msg["To"] = ",".join(recipients)
        msg.set_content(body)

        s = smtplib.SMTP(self.config.get("host", "localhost"), self.config.get("port", 25))
        if self.config.get("username"):
            s.starttls()
            user_val = os.getenv("SOCRATA_USER") or str(self.config.get("username"))
            s.login(user=user_val, password=str(self.config.get("password", "")))
        s.send_message(msg)
        s.quit()

    def notify(self, alert: Alert) -> None:
        sev = (
            alert.severity.value
            if isinstance(alert.severity, AlertSeverity)
            else str(alert.severity)
        )
        subject = f"[{sev.upper()}] {alert.message}"
        body = json.dumps(
            {"message": alert.message, "payload": alert.payload, "ts": alert.created_at},
            indent=2,
            default=str,
        )
        recipients = self.config.get("recipients", [])
        if not recipients:
            return
        try:
            self._send_email(subject, body, recipients)
        except Exception:  # pylint: disable=broad-exception-caught
            pass


class DBNotifier:
    """Persist alerts into Postgres."""

    ALERTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS alerts (
      id SERIAL PRIMARY KEY,
      created_at TIMESTAMPTZ DEFAULT now(),
      severity TEXT,
      message TEXT,
      payload JSONB
    );
    """

    def __init__(self, dsn: str):
        try:
            import psycopg
            from psycopg.types.json import Json

            self.psycopg = psycopg
            self.Json = Json
        except ImportError as exc:
            raise ImportError("psycopg is required: pip install 'psycopg[binary]'") from exc

        self.dsn = dsn
        with self.psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(self.ALERTS_TABLE_SQL)

    def notify(self, alert: Alert) -> None:
        """Inserts alert into DB."""
        try:
            sev = (
                alert.severity.value
                if isinstance(alert.severity, AlertSeverity)
                else str(alert.severity)
            )
            with self.psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO alerts (severity, message, payload) VALUES (%s, %s, %s)",
                        (sev, alert.message, self.Json(alert.payload)),
                    )
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def close(self) -> None:
        """Not needed with context managers, but kept for API compatibility."""
        pass
