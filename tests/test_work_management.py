import json

import pandas as pd
import pytest

from socrata_toolkit.tools.work import (
    GoogleWorkspaceAdapter,
    M365Adapter,
    MSProjectExporter,
    MondayAdapter,
)


def _construction_list():
    return pd.DataFrame({
        "borough": ["MANHATTAN", "BROOKLYN"],
        "address": ["123 Main St", "456 Oak Ave"],
        "status": ["Pending Repair", "Complete"],
        "_priority_score": [0.8, 0.3],
        "_scope": ["sidewalk_repair", "pedestrian_ramp"],
        "estimated_sqft": [200, 50],
    })


def _contracts():
    return pd.DataFrame({
        "contract_id": ["C1", "C2"],
        "status": ["Active", "Complete"],
        "start_date": ["2024-01-01", "2024-06-01"],
        "end_date": ["2025-06-30", "2025-01-31"],
        "planned_spend": [100000, 50000],
        "pct_complete": [45.0, 100.0],
    })


# -- Monday.com ---------------------------------------------------------------

def test_monday_construction_list_to_items():
    adapter = MondayAdapter()
    items = adapter.construction_list_to_items(_construction_list())
    assert len(items) == 2
    assert items[0].priority == "high"  # score >= 0.7
    assert items[1].priority == "low"   # score < 0.4


def test_monday_contracts_to_items():
    adapter = MondayAdapter()
    items = adapter.contracts_to_items(_contracts())
    assert len(items) == 2
    assert items[0].name == "C1"


def test_monday_export_items(tmp_path):
    adapter = MondayAdapter()
    items = adapter.construction_list_to_items(_construction_list())
    path = str(tmp_path / "monday.json")
    adapter.export_items(path, items)
    data = json.loads(open(path).read())
    assert len(data) == 2
    assert data[0]["name"] == "123 Main St"


# -- MS Project ---------------------------------------------------------------

def test_ms_project_from_contracts():
    exporter = MSProjectExporter()
    tasks = exporter.from_contracts(_contracts())
    assert len(tasks) == 2
    assert tasks[0].name == "C1"
    assert tasks[0].duration_days > 0


def test_ms_project_save(tmp_path):
    exporter = MSProjectExporter()
    exporter.from_contracts(_contracts())
    path = str(tmp_path / "schedule.xml")
    exporter.save(path)
    content = open(path).read()
    assert "<Project" in content
    assert "<Task>" in content
    assert "C1" in content


# -- Microsoft 365 ------------------------------------------------------------

def test_m365_sharepoint_list_items():
    df = _construction_list()
    items = M365Adapter.sharepoint_list_items(df, key_columns=["borough", "address", "status"])
    assert len(items) == 2
    assert "fields" in items[0]
    assert items[0]["fields"]["borough"] == "MANHATTAN"


def test_m365_teams_notification():
    msg = M365Adapter.teams_notification(
        "Alert: 5 new conflicts",
        "Construction conflicts detected",
        facts={"Borough": "Manhattan", "Count": 5},
    )
    assert msg["@type"] == "MessageCard"
    assert len(msg["sections"][0]["facts"]) == 2


def test_m365_outlook_event():
    event = M365Adapter.outlook_event(
        "Contract Review Meeting",
        "2025-03-15T09:00:00",
        "2025-03-15T10:00:00",
        attendees=["user@dot.nyc.gov"],
    )
    assert event["subject"] == "Contract Review Meeting"
    assert len(event["attendees"]) == 1


def test_m365_export_payloads(tmp_path):
    path = str(tmp_path / "payload.json")
    M365Adapter().export_payloads(path, {"test": True})
    data = json.loads(open(path).read())
    assert data["test"] is True


# -- Google Workspace ----------------------------------------------------------

def test_google_sheets_values():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    payload = GoogleWorkspaceAdapter.sheets_values(df)
    assert payload["majorDimension"] == "ROWS"
    assert len(payload["values"]) == 3  # header + 2 rows
    assert payload["values"][0] == ["a", "b"]


def test_google_calendar_event():
    event = GoogleWorkspaceAdapter.calendar_event(
        "Site Inspection",
        "2025-03-15T09:00:00",
        "2025-03-15T12:00:00",
        location="123 Main St, Manhattan",
    )
    assert event["summary"] == "Site Inspection"
    assert event["location"] == "123 Main St, Manhattan"


def test_google_export_for_sheets(tmp_path):
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    path = str(tmp_path / "sheets.json")
    GoogleWorkspaceAdapter().export_for_sheets(df, path)
    data = json.loads(open(path).read())
    assert len(data["values"]) == 3
