"""Work Management System Integration for DOT Sidewalk Toolkit.

Integration adapters for:
- Monday.com work management (board/item/update creation)
- Microsoft Project (XML export for task scheduling)
- Microsoft 365 (SharePoint list sync, Teams notifications, Outlook)
- Google Workspace (Sheets sync, Calendar events, Drive upload)

All integrations produce structured output files or API-ready payloads.
Actual API calls require credentials configured via environment variables.

Example::

    from socrata_toolkit.work_management import (
        MondayAdapter,
        MSProjectExporter,
        M365Adapter,
        GoogleWorkspaceAdapter,
    )

    # Monday.com: create tasks from construction list
    monday = MondayAdapter()
    payload = monday.construction_list_to_items(df)
    monday.export_items("monday_items.json", payload)

    # MS Project: export schedule
    exporter = MSProjectExporter()
    exporter.from_contracts(contracts_df)
    exporter.save("project_schedule.xml")
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Monday.com Adapter
# ---------------------------------------------------------------------------

@dataclass
class MondayItem:
    """Represents a Monday.com board item."""
    name: str
    group: str
    status: str
    priority: str
    date: Optional[str] = None
    person: Optional[str] = None
    text: str = ""
    numbers: Dict[str, float] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)


class MondayAdapter:
    """Convert toolkit data into Monday.com board items.

    Generates structured JSON payloads compatible with Monday.com's
    API or bulk import. Does not make API calls directly (to avoid
    requiring API keys in the toolkit).

    Usage::

        adapter = MondayAdapter()
        items = adapter.construction_list_to_items(df)
        adapter.export_items("monday_tasks.json", items)
    """

    def construction_list_to_items(
        self,
        df: pd.DataFrame,
        borough_col: str = "borough",
        address_col: str = "address",
        status_col: str = "status",
        priority_col: str = "_priority_score",
        scope_col: str = "_scope",
        sqft_col: str = "estimated_sqft",
    ) -> List[MondayItem]:
        """Convert a construction list DataFrame to Monday.com items."""
        items = []
        for _, row in df.iterrows():
            priority = "high" if float(row.get(priority_col, 0) or 0) >= 0.7 else (
                "medium" if float(row.get(priority_col, 0) or 0) >= 0.4 else "low"
            )
            items.append(MondayItem(
                name=str(row.get(address_col, f"Location {row.name}")),
                group=str(row.get(borough_col, "Unassigned")),
                status=str(row.get(status_col, "Pending")),
                priority=priority,
                text=str(row.get(scope_col, "")),
                numbers={"sqft": float(row.get(sqft_col, 0) or 0)},
                labels=[str(row.get(scope_col, ""))],
            ))
        return items

    def contracts_to_items(
        self,
        df: pd.DataFrame,
        contract_id_col: str = "contract_id",
        status_col: str = "status",
        start_col: str = "start_date",
        end_col: str = "end_date",
        budget_col: str = "planned_spend",
    ) -> List[MondayItem]:
        """Convert contract data to Monday.com items for project tracking."""
        items = []
        for _, row in df.iterrows():
            items.append(MondayItem(
                name=str(row.get(contract_id_col, f"Contract {row.name}")),
                group="Contracts",
                status=str(row.get(status_col, "Active")),
                priority="medium",
                date=str(row.get(start_col, "")) if start_col in row else None,
                numbers={"budget": float(row.get(budget_col, 0) or 0)},
            ))
        return items

    def export_items(self, path: str, items: List[MondayItem]) -> str:
        """Export Monday.com items as JSON for API import."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "name": item.name,
                "group": item.group,
                "column_values": {
                    "status": {"label": item.status},
                    "priority": {"label": item.priority},
                    "date": {"date": item.date} if item.date else None,
                    "person": {"personsAndTeams": [{"id": item.person}]} if item.person else None,
                    "text": item.text,
                    **{k: {"number": v} for k, v in item.numbers.items()},
                },
                "labels": item.labels,
            }
            for item in items
        ]
        p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return str(p)


# ---------------------------------------------------------------------------
# Microsoft Project Exporter
# ---------------------------------------------------------------------------

@dataclass
class ProjectTask:
    """A task in a project schedule."""
    uid: int
    name: str
    start: str
    finish: str
    duration_days: int
    pct_complete: float
    predecessors: List[int] = field(default_factory=list)
    resource: str = ""
    notes: str = ""


class MSProjectExporter:
    """Export project schedules in Microsoft Project XML format.

    Generates XML compatible with MS Project, ProjectLibre, and
    other project management tools that support MS Project XML import.
    """

    def __init__(self) -> None:
        self.tasks: List[ProjectTask] = []

    def add_task(self, task: ProjectTask) -> None:
        self.tasks.append(task)

    def from_contracts(
        self,
        df: pd.DataFrame,
        contract_id_col: str = "contract_id",
        start_col: str = "start_date",
        end_col: str = "end_date",
        pct_col: str = "pct_complete",
    ) -> List[ProjectTask]:
        """Generate project tasks from a contracts DataFrame."""
        self.tasks = []
        for i, (_, row) in enumerate(df.iterrows()):
            start = str(row.get(start_col, "2025-01-01"))
            end = str(row.get(end_col, "2025-12-31"))
            try:
                duration = (pd.to_datetime(end) - pd.to_datetime(start)).days
            except Exception:
                duration = 90

            task = ProjectTask(
                uid=i + 1,
                name=str(row.get(contract_id_col, f"Task {i+1}")),
                start=start,
                finish=end,
                duration_days=max(duration, 1),
                pct_complete=float(row.get(pct_col, 0) or 0),
            )
            self.tasks.append(task)
        return self.tasks

    def save(self, path: str) -> str:
        """Export as MS Project XML."""
        root = ET.Element("Project")
        root.set("xmlns", "http://schemas.microsoft.com/project")

        ET.SubElement(root, "Name").text = "DOT Sidewalk Program"
        ET.SubElement(root, "StartDate").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT08:00:00")

        tasks_elem = ET.SubElement(root, "Tasks")
        for task in self.tasks:
            t = ET.SubElement(tasks_elem, "Task")
            ET.SubElement(t, "UID").text = str(task.uid)
            ET.SubElement(t, "Name").text = task.name
            ET.SubElement(t, "Start").text = f"{task.start}T08:00:00"
            ET.SubElement(t, "Finish").text = f"{task.finish}T17:00:00"
            ET.SubElement(t, "Duration").text = f"PT{task.duration_days * 8}H0M0S"
            ET.SubElement(t, "PercentComplete").text = str(int(task.pct_complete))
            if task.notes:
                ET.SubElement(t, "Notes").text = task.notes

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(root)
        tree.write(str(p), encoding="unicode", xml_declaration=True)
        return str(p)


# ---------------------------------------------------------------------------
# Microsoft 365 Adapter
# ---------------------------------------------------------------------------

class M365Adapter:
    """Generate payloads for Microsoft 365 integration.

    Creates structured data for:
    - SharePoint list items
    - Teams channel notifications
    - Outlook calendar events

    Output is JSON payloads compatible with the Microsoft Graph API.
    Actual API calls require authentication configured separately.
    """

    @staticmethod
    def sharepoint_list_items(
        df: pd.DataFrame,
        list_name: str = "Construction List",
        key_columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert a DataFrame to SharePoint list item payloads."""
        cols = key_columns or list(df.columns)
        items = []
        for _, row in df.iterrows():
            fields = {col: _serialize(row.get(col)) for col in cols if col in row.index}
            items.append({"fields": fields})
        return items

    @staticmethod
    def teams_notification(
        title: str,
        body: str,
        facts: Optional[Dict[str, Any]] = None,
        theme_color: str = "003366",
    ) -> Dict[str, Any]:
        """Build a Teams Incoming Webhook message card payload."""
        sections = [{"activityTitle": title, "text": body}]
        if facts:
            sections[0]["facts"] = [{"name": k, "value": str(v)} for k, v in facts.items()]
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": title,
            "sections": sections,
        }

    @staticmethod
    def outlook_event(
        subject: str,
        start: str,
        end: str,
        body: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build an Outlook calendar event payload (Graph API format)."""
        event = {
            "subject": subject,
            "start": {"dateTime": start, "timeZone": "Eastern Standard Time"},
            "end": {"dateTime": end, "timeZone": "Eastern Standard Time"},
            "body": {"contentType": "HTML", "content": body},
        }
        if attendees:
            event["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in attendees
            ]
        return event

    def export_payloads(self, path: str, payloads: Any) -> str:
        """Write any payload(s) to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payloads, indent=2, default=str), encoding="utf-8")
        return str(p)


# ---------------------------------------------------------------------------
# Google Workspace Adapter
# ---------------------------------------------------------------------------

class GoogleWorkspaceAdapter:
    """Generate payloads for Google Workspace integration.

    Creates structured data for:
    - Google Sheets (row-oriented data for Sheets API)
    - Google Calendar events
    - Google Drive file metadata

    Output is JSON payloads compatible with Google Workspace APIs.
    """

    @staticmethod
    def sheets_values(
        df: pd.DataFrame,
        sheet_name: str = "Sheet1",
        include_header: bool = True,
    ) -> Dict[str, Any]:
        """Convert DataFrame to Google Sheets API values payload.

        Compatible with ``spreadsheets.values.update`` API endpoint.
        """
        values = []
        if include_header:
            values.append(list(df.columns))
        for _, row in df.iterrows():
            values.append([_serialize(v) for v in row.values])
        return {
            "range": f"{sheet_name}!A1",
            "majorDimension": "ROWS",
            "values": values,
        }

    @staticmethod
    def calendar_event(
        summary: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build a Google Calendar event payload."""
        event = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "America/New_York"},
            "end": {"dateTime": end, "timeZone": "America/New_York"},
            "description": description,
            "location": location,
        }
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]
        return event

    def export_for_sheets(self, df: pd.DataFrame, path: str, sheet_name: str = "Sheet1") -> str:
        """Export DataFrame as a Google Sheets-compatible JSON file."""
        payload = self.sheets_values(df, sheet_name=sheet_name)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return str(p)


def _serialize(value: Any) -> Any:
    """Serialize a value for JSON export."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
