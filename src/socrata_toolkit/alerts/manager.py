"""Alerting and notification utilities.

This module implements a lightweight Observer pattern for operational alerts.
It supports CLI, Email, and Postgres-based persistence.
"""
from __future__ import annotations

import os
import threading
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

# Fix: Import os specifically to avoid 'os is not defined' in _send_email
# Fix: Removed the problematic 'from streamlit import login, user' as it conflicted with SMTP logic

try:
    from rich import print as rprint
except ImportError:  # pragma: no cover
    rprint = print

log = logging.getLogger(__name__)

@dataclass
class Alert:
    """Represents a single operational alert."""
    severity: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

class Subscriber(Protocol):
    """Protocol that alert subscribers must implement."""
    def notify(self, alert: Alert) -> None:
        ...

class AlertManager:
    """Manages subscribers and dispatches alerts."""
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
        """Register a new subscriber."""
        with self.lock:
            self.subscribers.append(s)

    def unregister(self, s: Subscriber) -> None:
        """Unregister a subscriber."""
        with self.lock:
            try:
                self.subscribers.remove(s)
            except ValueError:
                pass

    def emit(self, alert: Alert) -> None:
        """Emit an alert."""
        if self.batch_mode:
            with self.lock:
                self._batch.append(alert)
        else:
            self._dispatch(alert)

    def _dispatch(self, alert: Alert) -> None:
        for s in list(self.subscribers):
            try:
                s.notify(alert)
            except Exception: # pylint: disable=broad-exception-caught
                pass

    def _worker(self) -> None:
        while not self._stop:
            time.sleep(self.batch_interval)
            with self.lock:
                batch, self._batch = self._batch, []
            if not batch:
                continue
            for alert in batch:
                self._dispatch(alert)

    def shutdown(self) -> None:
        """Stop background thread and flush."""
        self._stop = True
        if self.batch_mode and getattr(self, "_thread", None):
            self._thread.join(timeout=1.0)
        with self.lock:
            batch, self._batch = self._batch, []
        for alert in batch:
            self._dispatch(alert)

class CLINotifier:
    """Prints alerts to the console."""
    def __init__(self, show_payload: bool = True):
        self.show_payload = show_payload

    def notify(self, alert: Alert) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(alert.created_at))
        header = f"[{alert.severity.upper()}] {ts} - {alert.message}"
        try:
            rprint(header)
            if self.show_payload and alert.payload:
                rprint(json.dumps(alert.payload, indent=2, default=str))
        except Exception: # pylint: disable=broad-exception-caught
            print(header)
            if self.show_payload and alert.payload:
                print(alert.payload)

class EmailNotifier:
    """Sends alerts via SMTP."""
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
            # Fix: Ensure user is a string to satisfy Pylance
            user_val = os.getenv("SOCRATA_USER") or str(self.config.get("username"))
            s.login(user=user_val, password=str(self.config.get("password", "")))
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
        except Exception: # pylint: disable=broad-exception-caught
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
        # Fix: Use context manager to satisfy Pylint 'no-member' check
        with self.psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(self.ALERTS_TABLE_SQL)

    def notify(self, alert: Alert) -> None:
        """Inserts alert into DB."""
        try:
            with self.psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Fix: Use the imported Json type for the payload
                    cur.execute(
                        "INSERT INTO alerts (severity, message, payload) VALUES (%s, %s, %s)",
                        (alert.severity, alert.message, self.Json(alert.payload))
                    )
        except Exception: # pylint: disable=broad-exception-caught
            pass

    def close(self) -> None:
        """Not needed with context managers, but kept for API compatibility."""
        pass
