"""Task Board and Collaboration Module for DOT Sidewalk Toolkit.

Provides a lightweight, file-backed task management system with:
- Kanban-style boards with customizable columns
- Color-coded task cards (priority, status, category)
- Task assignment, due dates, and dependency tracking
- Sprint/milestone grouping
- Activity log for team collaboration
- Board persistence (JSON) and export (CSV, Markdown)

This module is designed to work standalone or power the Streamlit dashboard.
No external services required -- all data stored locally as JSON.

Example::

    from socrata_toolkit.task_board import TaskBoard, Task

    board = TaskBoard("Sidewalk Q1 2025")
    board.add_task(Task(title="Build Manhattan construction list", assignee="analyst1",
                        priority="high", category="construction", due_date="2025-02-15"))
    board.add_task(Task(title="Budget review Q1", assignee="pm", priority="medium",
                        category="budget", due_date="2025-01-30"))
    board.move_task(0, "in_progress")
    board.save("boards/q1_2025.json")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Color Coding
# ---------------------------------------------------------------------------

#: Color mapping for priority levels (CSS hex colors).
PRIORITY_COLORS: dict[str, str] = {
    "critical": "#DC3545",  # red
    "high": "#FD7E14",      # orange
    "medium": "#FFC107",    # yellow
    "low": "#28A745",       # green
    "none": "#6C757D",      # gray
}

#: Color mapping for task categories.
CATEGORY_COLORS: dict[str, str] = {
    "construction": "#0D6EFD",    # blue
    "budget": "#198754",          # green
    "inspection": "#6610F2",      # purple
    "compliance": "#D63384",      # pink
    "reporting": "#0DCAF0",       # cyan
    "planning": "#FFC107",        # yellow
    "conflict": "#DC3545",        # red
    "general": "#6C757D",         # gray
}

#: Default board columns (Kanban stages).
DEFAULT_COLUMNS = ["backlog", "todo", "in_progress", "review", "done"]

#: Status display labels.
STATUS_LABELS: dict[str, str] = {
    "backlog": "Backlog",
    "todo": "To Do",
    "in_progress": "In Progress",
    "review": "In Review",
    "done": "Done",
    "blocked": "Blocked",
}

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single task on the board."""
    title: str
    description: str = ""
    assignee: str = ""
    priority: str = "medium"  # critical, high, medium, low, none
    category: str = "general"
    status: str = "todo"
    due_date: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    dependencies: list[int] = field(default_factory=list)  # task IDs this depends on
    attachments: list[str] = field(default_factory=list)
    borough: str = ""
    contract_id: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    notes: str = ""

    @property
    def priority_color(self) -> str:
        return PRIORITY_COLORS.get(self.priority, PRIORITY_COLORS["none"])

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.category, CATEGORY_COLORS["general"])

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status == "done":
            return False
        try:
            due = pd.to_datetime(self.due_date)
            return pd.Timestamp.now() > due
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "priority": self.priority,
            "category": self.category,
            "status": self.status,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "attachments": self.attachments,
            "borough": self.borough,
            "contract_id": self.contract_id,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Task:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

@dataclass
class ActivityEntry:
    """An entry in the activity log."""
    timestamp: str
    actor: str
    action: str
    task_id: int | None
    details: str

@dataclass
class Milestone:
    """A milestone grouping tasks."""
    name: str
    due_date: str | None = None
    description: str = ""
    task_ids: list[int] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return False  # Evaluated by board context

# ---------------------------------------------------------------------------
# Task Board
# ---------------------------------------------------------------------------

class TaskBoard:
    """Kanban-style task board with full lifecycle management.

    Provides task CRUD, column management, activity logging, filtering,
    and persistence. Designed to power both CLI and Streamlit interfaces.
    """

    def __init__(self, name: str = "DOT Sidewalk Board", columns: list[str] | None = None) -> None:
        self.name = name
        self.columns = columns or list(DEFAULT_COLUMNS)
        self.tasks: list[Task] = []
        self.activity_log: list[ActivityEntry] = []
        self.milestones: list[Milestone] = []
        self.team_members: list[str] = []

    # -- Task CRUD -----------------------------------------------------------

    def add_task(self, task: Task, actor: str = "system") -> int:
        """Add a task and return its index (ID)."""
        task_id = len(self.tasks)
        self.tasks.append(task)
        self._log(actor, "created", task_id, f"Created: {task.title}")
        return task_id

    def update_task(self, task_id: int, actor: str = "system", **kwargs: Any) -> Task:
        """Update task fields and log the change."""
        task = self.tasks[task_id]
        changes = []
        for key, value in kwargs.items():
            if hasattr(task, key):
                old = getattr(task, key)
                setattr(task, key, value)
                changes.append(f"{key}: {old} -> {value}")
        task.updated_at = datetime.now(timezone.utc).isoformat()
        if changes:
            self._log(actor, "updated", task_id, "; ".join(changes))
        return task

    def move_task(self, task_id: int, new_status: str, actor: str = "system") -> None:
        """Move a task to a new status column."""
        task = self.tasks[task_id]
        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc).isoformat()
        self._log(actor, "moved", task_id, f"{STATUS_LABELS.get(old_status, old_status)} -> {STATUS_LABELS.get(new_status, new_status)}")

    def delete_task(self, task_id: int, actor: str = "system") -> None:
        """Mark a task as deleted (soft delete via status)."""
        task = self.tasks[task_id]
        task.status = "deleted"
        task.updated_at = datetime.now(timezone.utc).isoformat()
        self._log(actor, "deleted", task_id, f"Deleted: {task.title}")

    def add_comment(self, task_id: int, actor: str, comment: str) -> None:
        """Add a comment to a task's activity log."""
        task = self.tasks[task_id]
        task.notes += f"\n[{actor} @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {comment}"
        self._log(actor, "commented", task_id, comment[:100])

    # -- Filtering and Querying -----------------------------------------------

    def get_column(self, status: str) -> list[tuple]:
        """Return (task_id, task) pairs for a given status column."""
        return [(i, t) for i, t in enumerate(self.tasks) if t.status == status]

    def filter_tasks(
        self,
        status: str | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        borough: str | None = None,
        overdue_only: bool = False,
    ) -> list[tuple]:
        """Filter tasks by criteria. Returns (task_id, task) pairs."""
        results = []
        for i, t in enumerate(self.tasks):
            if t.status == "deleted":
                continue
            if status and t.status != status:
                continue
            if assignee and t.assignee != assignee:
                continue
            if priority and t.priority != priority:
                continue
            if category and t.category != category:
                continue
            if borough and t.borough != borough:
                continue
            if overdue_only and not t.is_overdue:
                continue
            results.append((i, t))
        return results

    def search_tasks(self, query: str) -> list[tuple]:
        """Search tasks by title and description text."""
        q = query.lower()
        return [(i, t) for i, t in enumerate(self.tasks)
                if q in t.title.lower() or q in t.description.lower() or q in t.notes.lower()]

    # -- Board Statistics -----------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Compute board-level statistics."""
        active = [t for t in self.tasks if t.status != "deleted"]
        by_status = {}
        for col in self.columns:
            by_status[col] = sum(1 for t in active if t.status == col)
        by_priority = {}
        for p in PRIORITY_COLORS:
            by_priority[p] = sum(1 for t in active if t.priority == p)
        by_category = {}
        for t in active:
            by_category[t.category] = by_category.get(t.category, 0) + 1
        by_assignee = {}
        for t in active:
            if t.assignee:
                by_assignee[t.assignee] = by_assignee.get(t.assignee, 0) + 1

        overdue = sum(1 for t in active if t.is_overdue)
        done = sum(1 for t in active if t.status == "done")
        completion_rate = round(done / max(len(active), 1) * 100, 1)

        return {
            "total_tasks": len(active),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
            "by_assignee": by_assignee,
            "overdue_count": overdue,
            "completion_rate": completion_rate,
        }

    # -- Milestones -----------------------------------------------------------

    def add_milestone(self, name: str, due_date: str | None = None, task_ids: list[int] | None = None) -> int:
        """Add a milestone. Returns its index."""
        ms = Milestone(name=name, due_date=due_date, task_ids=task_ids or [])
        self.milestones.append(ms)
        return len(self.milestones) - 1

    def milestone_progress(self, milestone_idx: int) -> dict[str, Any]:
        """Compute progress for a milestone."""
        ms = self.milestones[milestone_idx]
        tasks = [self.tasks[i] for i in ms.task_ids if i < len(self.tasks)]
        done = sum(1 for t in tasks if t.status == "done")
        total = len(tasks)
        return {
            "name": ms.name,
            "total_tasks": total,
            "completed": done,
            "pct_complete": round(done / max(total, 1) * 100, 1),
            "due_date": ms.due_date,
        }

    # -- Import from DataFrames -----------------------------------------------

    def import_from_construction_list(
        self,
        df: pd.DataFrame,
        address_col: str = "address",
        borough_col: str = "borough",
        scope_col: str = "_scope",
        priority_col: str = "_priority_score",
        status: str = "todo",
    ) -> int:
        """Bulk-import tasks from a construction list DataFrame."""
        count = 0
        for _, row in df.iterrows():
            priority = "high" if float(row.get(priority_col, 0) or 0) >= 0.7 else (
                "medium" if float(row.get(priority_col, 0) or 0) >= 0.4 else "low"
            )
            task = Task(
                title=f"Repair: {row.get(address_col, 'Unknown')}",
                category=str(row.get(scope_col, "construction")),
                priority=priority,
                status=status,
                borough=str(row.get(borough_col, "")),
            )
            self.add_task(task)
            count += 1
        return count

    # -- Persistence ----------------------------------------------------------

    def save(self, path: str) -> str:
        """Save the board to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "columns": self.columns,
            "tasks": [t.to_dict() for t in self.tasks],
            "activity_log": [
                {"timestamp": a.timestamp, "actor": a.actor, "action": a.action,
                 "task_id": a.task_id, "details": a.details}
                for a in self.activity_log
            ],
            "milestones": [
                {"name": m.name, "due_date": m.due_date, "description": m.description, "task_ids": m.task_ids}
                for m in self.milestones
            ],
            "team_members": self.team_members,
        }
        p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path: str) -> TaskBoard:
        """Load a board from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        board = cls(name=data.get("name", "Board"), columns=data.get("columns"))
        board.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        board.activity_log = [
            ActivityEntry(**a) for a in data.get("activity_log", [])
        ]
        board.milestones = [
            Milestone(**m) for m in data.get("milestones", [])
        ]
        board.team_members = data.get("team_members", [])
        return board

    # -- Export ---------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """Export all tasks as a DataFrame."""
        return pd.DataFrame([t.to_dict() for t in self.tasks if t.status != "deleted"])

    def to_markdown(self) -> str:
        """Export the board as a Markdown Kanban view."""
        lines = [f"# {self.name}", ""]
        for col in self.columns:
            tasks = self.get_column(col)
            lines.append(f"## {STATUS_LABELS.get(col, col)} ({len(tasks)})")
            lines.append("")
            for tid, task in tasks:
                overdue = " [OVERDUE]" if task.is_overdue else ""
                assignee = f" @{task.assignee}" if task.assignee else ""
                due = f" (due: {task.due_date})" if task.due_date else ""
                lines.append(f"- [{task.priority.upper()}] {task.title}{assignee}{due}{overdue}")
            lines.append("")
        return "\n".join(lines)

    # -- Internal -------------------------------------------------------------

    def _log(self, actor: str, action: str, task_id: int | None, details: str) -> None:
        self.activity_log.append(ActivityEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            task_id=task_id,
            details=details,
        ))
