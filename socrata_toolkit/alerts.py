from __future__ import annotations

"""Alerting and notification utilities.

This module implements a lightweight Observer pattern for operational alerts.
It is intentionally dependency-light: `smtplib` is used for SMTP emails (standard
library), `rich` is optional for nicer CLI output, and Postgres-based persistence
is supported via a simple SQL writer (psycopg required only when used).

Usage summary:
    mgr = AlertManager()
    mgr.register(CLINotifier())
    mgr.register(EmailNotifier(smtp_config))
    mgr.emit(Alert(severity="critical", message="...", payload={...}))

The `AlertManager` supports batch delivery, configurable thresholds, and
pluggable subscribers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol
import threading
import time
import json

try:
    from rich import print as rprint
except Exception:  # pragma: no cover - optional
    rprint = print


@dataclass
class Alert:
    """Represents a single operational alert.

    Fields:
      - severity: e.g. 'info', 'warning', 'critical'
      - message: short human-readable summary
      - payload: arbitrary JSON-serializable metadata
      - created_at: epoch timestamp (auto-populated)
    """
    severity: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class Subscriber(Protocol):
    """Protocol that alert subscribers must implement."""

    def notify(self, alert: Alert) -> None:  # pragma: no cover - interface
        ...


class AlertManager:
    """Manages subscribers and dispatches alerts.

    The manager is thread-safe and supports batching. You can register many
    subscribers (CLI, Email, DB, etc.) and call `emit()` to broadcast alerts.
    """

    def __init__(self, batch_mode: bool = True, batch_interval: float = 30.0):
        self.subscribers: List[Subscriber] = []
        self.lock = threading.Lock()
        self.batch_mode = batch_mode
        self.batch_interval = batch_interval
        self._batch: List[Alert] = []
        self._stop = False
        if self.batch_mode:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def register(self, s: Subscriber) -> None:
        """Register a new subscriber to receive alerts."""
        with self.lock:
            self.subscribers.append(s)

    def unregister(self, s: Subscriber) -> None:
        with self.lock:
            try:
                self.subscribers.remove(s)
            except ValueError:
                pass

    def emit(self, alert: Alert) -> None:
        """Emit an alert immediately (or add to batch if batch_mode)."""
        if self.batch_mode:
            with self.lock:
                self._batch.append(alert)
        else:
            self._dispatch(alert)

    def _dispatch(self, alert: Alert) -> None:
        for s in list(self.subscribers):
            try:
                s.notify(alert)
            except Exception:
                # Keep running even if one subscriber fails
                pass

    def _worker(self) -> None:
        while not self._stop:
            time.sleep(self.batch_interval)
            with self.lock:
                batch = self._batch
                self._batch = []
            if not batch:
                continue
            # simple batch delivery: dispatch alerts individually to subscribers
            for alert in batch:
                self._dispatch(alert)

    def shutdown(self) -> None:
        """Stop the background thread and flush batches."""
        self._stop = True
        if self.batch_mode and getattr(self, "_thread", None):
            self._thread.join(timeout=1.0)
        # flush remaining
        with self.lock:
            batch = self._batch
            self._batch = []
        for alert in batch:
            self._dispatch(alert)


class CLINotifier:
    """Prints alerts to the console.

    Uses `rich.print` when available, otherwise falls back to `print`.
    """

    def __init__(self, show_payload: bool = True):
        self.show_payload = show_payload

    def notify(self, alert: Alert) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(alert.created_at))
        header = f"[{alert.severity.upper()}] {ts} - {alert.message}"
        try:
            rprint(header)
            if self.show_payload and alert.payload:
                rprint(json.dumps(alert.payload, indent=2, default=str))
        except Exception:
            print(header)
            if self.show_payload and alert.payload:
                print(alert.payload)


class EmailNotifier:
    """Sends alerts as email using SMTP. Minimal configuration required.

    Config is a dict with keys: `host`, `port`, `username`, `password`, `from_addr`, `recipients` (list).
    For production consider SendGrid / SES integrations.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def _send_email(self, subject: str, body: str, recipients: List[str]) -> None:
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
            s.login(self.config.get("username"), self.config.get("password", ""))
        s.send_message(msg)
        s.quit()

    def notify(self, alert: Alert) -> None:
        subject = f"[{alert.severity.upper()}] {alert.message}"
        body = json.dumps({"message": alert.message, "payload": alert.payload, "ts": alert.created_at}, indent=2, default=str)
        recipients = self.config.get("recipients", [])
        if not recipients:
            return
        try:
            self._send_email(subject, body, recipients)
        except Exception:
            # Swallow email errors to avoid crashing pipeline
            pass


class DBNotifier:
    """Persist alerts into a Postgres `alerts` table.

    The notifier lazily imports `psycopg` only when used so tests and other
    lightweight runs remain dependency-light.
    """

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
        except Exception as exc:
            raise ImportError("psycopg is required for DBNotifier: pip install '.[postgres]'") from exc
        self.psycopg = psycopg
        self.conn = psycopg.connect(dsn)
        cur = self.conn.cursor()
        cur.execute(self.ALERTS_TABLE_SQL)
        self.conn.commit()

    def notify(self, alert: Alert) -> None:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO alerts (severity, message, payload) VALUES (%s, %s, %s)", (alert.severity, alert.message, self.psycopg.types.json.Json(alert.payload)))
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
