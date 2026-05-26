"""311 Complaint Auto-Ingestion for DOT Sidewalk Toolkit.

Automated pipeline for pulling sidewalk-related 311 complaints from
NYC Open Data, triaging via NLP, and creating task board items.

NYC 311 Service Requests dataset: ``erm2-nwe9`` on data.cityofnewyork.us

Example::

    from socrata_toolkit.pipeline.complaints import ingest_311_complaints

    result = ingest_311_complaints(max_rows=500)
    print(f"Ingested {result.total}, {result.critical_count} critical")
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

NYC_311_DOMAIN = "data.cityofnewyork.us"
NYC_311_FOURFOUR = "erm2-nwe9"

SIDEWALK_COMPLAINT_TYPES = [
    "Sidewalk Condition",
    "Broken Sidewalk",
    "Damaged Tree",
    "Curb Condition",
    "Street Condition",  # sometimes sidewalk-related
]


@dataclass
class IngestionResult:
    """Result from a 311 complaint ingestion run."""
    total: int
    sidewalk_related: int
    critical_count: int
    high_count: int
    boroughs: dict[str, int]
    task_board_items_created: int
    data: pd.DataFrame | None = field(default=None, repr=False)


def fetch_311_complaints(
    max_rows: int = 1000,
    complaint_types: list[str] | None = None,
    since: str | None = None,
    borough: str | None = None,
) -> pd.DataFrame:
    """Fetch 311 complaints from NYC Open Data.

    Args:
        max_rows: Maximum rows to fetch.
        complaint_types: Filter by complaint type. Defaults to sidewalk-related.
        since: ISO date string for incremental fetch (created_date > since).
        borough: Filter by borough name.
    """
    from ..core.client import SocrataClient

    types = complaint_types or SIDEWALK_COMPLAINT_TYPES
    where_parts = []
    type_filter = " OR ".join(f"complaint_type='{t}'" for t in types)
    where_parts.append(f"({type_filter})")

    if since:
        where_parts.append(f"created_date > '{since}'")
    if borough:
        where_parts.append(f"upper(borough) = '{borough.upper()}'")

    where = " AND ".join(where_parts)
    client = SocrataClient()
    return client.fetch_dataframe(NYC_311_DOMAIN, NYC_311_FOURFOUR, where=where, max_rows=max_rows)


def ingest_311_complaints(
    max_rows: int = 1000,
    since: str | None = None,
    borough: str | None = None,
    create_tasks: bool = False,
    board_path: str | None = None,
) -> IngestionResult:
    """Full ingestion pipeline: fetch, triage, and optionally create board tasks.

    Args:
        max_rows: Maximum complaints to fetch.
        since: Incremental fetch cutoff date.
        borough: Filter by borough.
        create_tasks: If True, create task board items for critical/high.
        board_path: Path to task board JSON (loads existing or creates new).
    """
    from ..nlp.integration import triage_complaints

    df = fetch_311_complaints(max_rows=max_rows, since=since, borough=borough)

    if df.empty:
        return IngestionResult(total=0, sidewalk_related=0, critical_count=0,
                                high_count=0, boroughs={}, task_board_items_created=0)

    # Map 311 columns to our standard
    text_col = "descriptor" if "descriptor" in df.columns else "complaint_type"
    df = triage_complaints(df, text_col=text_col)

    borough_col = "borough" if "borough" in df.columns else None
    boroughs = df[borough_col].value_counts().to_dict() if borough_col and borough_col in df.columns else {}

    critical = int((df.get("_triage_priority") == "critical").sum()) if "_triage_priority" in df.columns else 0
    high = int((df.get("_triage_priority") == "high").sum()) if "_triage_priority" in df.columns else 0

    tasks_created = 0
    if create_tasks and (critical > 0 or high > 0):
        tasks_created = _create_board_tasks(df, board_path)

    return IngestionResult(
        total=len(df),
        sidewalk_related=len(df),
        critical_count=critical,
        high_count=high,
        boroughs=boroughs,
        task_board_items_created=tasks_created,
        data=df,
    )


def _create_board_tasks(df: pd.DataFrame, board_path: str | None) -> int:
    from pathlib import Path

    from ..tools.tasks import Task, TaskBoard

    bp = board_path or "outputs/board.json"
    if Path(bp).exists():
        board = TaskBoard.load(bp)
    else:
        board = TaskBoard("311 Complaints")

    priority_rows = df[df.get("_triage_priority", pd.Series()).isin(["critical", "high"])]
    count = 0
    for _, row in priority_rows.iterrows():
        address = str(row.get("incident_address", row.get("address", "Unknown")))
        borough = str(row.get("borough", ""))
        priority = "critical" if row.get("_triage_priority") == "critical" else "high"
        desc = str(row.get("descriptor", row.get("complaint_type", "")))

        board.add_task(Task(
            title=f"311: {address}",
            description=desc,
            priority=priority,
            category="inspection",
            borough=borough,
            status="todo",
        ), actor="311_auto_ingest")
        count += 1

    board.save(bp)
    return count
