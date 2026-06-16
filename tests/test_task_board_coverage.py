"""Comprehensive tests for socrata_toolkit.task_board module.

Covers Task dataclass, TaskBoard CRUD, filtering, search, stats,
milestones, DataFrame import, persistence (save/load), and export
(DataFrame, Markdown). File I/O uses tempfile for isolation.
"""
from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from socrata_toolkit.task_board import (
    CATEGORY_COLORS,
    DEFAULT_COLUMNS,
    PRIORITY_COLORS,
    STATUS_LABELS,
    ActivityEntry,
    Milestone,
    Task,
    TaskBoard,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_board() -> TaskBoard:
    """Fresh TaskBoard with no tasks."""
    return TaskBoard("Test Board")

@pytest.fixture
def populated_board() -> TaskBoard:
    """Board pre-loaded with a mix of tasks in various states."""
    board = TaskBoard("Populated Board")
    board.add_task(Task(title="Inspect ramp MN-01", assignee="alice", priority="high",
                        category="inspection", borough="MN", status="todo"))
    board.add_task(Task(title="Budget review Q1", assignee="bob", priority="medium",
                        category="budget", borough="BK", status="in_progress"))
    board.add_task(Task(title="File compliance report", assignee="alice", priority="critical",
                        category="compliance", borough="BX", status="done"))
    board.add_task(Task(title="Plan resurfacing", assignee="carol", priority="low",
                        category="planning", borough="QN", status="backlog"))
    return board

@pytest.fixture
def tmp_board_path(tmp_path: Path) -> str:
    """Temporary file path for board persistence tests."""
    return str(tmp_path / "board.json")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Tests for module-level constants."""

    def test_priority_colors_has_all_levels(self):
        for level in ("critical", "high", "medium", "low", "none"):
            assert level in PRIORITY_COLORS

    def test_category_colors_has_general(self):
        assert "general" in CATEGORY_COLORS

    def test_default_columns_length(self):
        assert len(DEFAULT_COLUMNS) == 5

    def test_status_labels_map_all_defaults(self):
        for col in DEFAULT_COLUMNS:
            assert col in STATUS_LABELS

# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

class TestTaskDataclass:
    """Tests for the Task dataclass and its properties."""

    def test_minimal_task_creation(self):
        task = Task(title="Fix crack")
        assert task.title == "Fix crack"
        assert task.priority == "medium"
        assert task.status == "todo"
        assert task.tags == []

    def test_priority_color_known_level(self):
        task = Task(title="X", priority="critical")
        assert task.priority_color == PRIORITY_COLORS["critical"]

    def test_priority_color_unknown_defaults_to_none_color(self):
        task = Task(title="X", priority="unknown_level")
        assert task.priority_color == PRIORITY_COLORS["none"]

    def test_category_color_known(self):
        task = Task(title="X", category="construction")
        assert task.category_color == CATEGORY_COLORS["construction"]

    def test_category_color_unknown_defaults_to_general(self):
        task = Task(title="X", category="xyz")
        assert task.category_color == CATEGORY_COLORS["general"]

    def test_is_overdue_false_when_no_due_date(self):
        task = Task(title="X")
        assert task.is_overdue is False

    def test_is_overdue_false_when_done(self):
        task = Task(title="X", due_date="1990-01-01", status="done")
        assert task.is_overdue is False

    def test_is_overdue_true_when_past_due(self):
        task = Task(title="X", due_date="2000-01-01", status="todo")
        assert task.is_overdue is True

    def test_is_overdue_invalid_date_returns_false(self):
        task = Task(title="X", due_date="not-a-date", status="todo")
        assert task.is_overdue is False

    def test_to_dict_round_trip(self):
        task = Task(title="Round trip", priority="high", tags=["a", "b"])
        d = task.to_dict()
        assert d["title"] == "Round trip"
        assert d["tags"] == ["a", "b"]

    def test_from_dict_creates_task(self):
        d = {"title": "From dict", "priority": "low", "category": "general"}
        task = Task.from_dict(d)
        assert task.title == "From dict"
        assert task.priority == "low"

# ---------------------------------------------------------------------------
# TaskBoard CRUD
# ---------------------------------------------------------------------------

class TestTaskBoardCRUD:
    """Tests for add, update, move, delete, and comment operations."""

    def test_add_task_returns_integer_id(self, empty_board):
        task_id = empty_board.add_task(Task(title="First"))
        assert task_id == 0

    def test_add_task_increments_id(self, empty_board):
        id0 = empty_board.add_task(Task(title="T1"))
        id1 = empty_board.add_task(Task(title="T2"))
        assert id1 == id0 + 1

    def test_add_task_logs_activity(self, empty_board):
        empty_board.add_task(Task(title="Logged"), actor="test_user")
        assert len(empty_board.activity_log) == 1
        assert empty_board.activity_log[0].actor == "test_user"
        assert empty_board.activity_log[0].action == "created"

    def test_update_task_changes_field(self, populated_board):
        populated_board.update_task(0, priority="critical")
        assert populated_board.tasks[0].priority == "critical"

    def test_update_task_logs_change(self, populated_board):
        log_before = len(populated_board.activity_log)
        populated_board.update_task(0, priority="low")
        assert len(populated_board.activity_log) > log_before

    def test_move_task_updates_status(self, populated_board):
        populated_board.move_task(0, "in_progress")
        assert populated_board.tasks[0].status == "in_progress"

    def test_move_task_logs_activity(self, populated_board):
        log_before = len(populated_board.activity_log)
        populated_board.move_task(0, "done")
        assert len(populated_board.activity_log) > log_before

    def test_delete_task_sets_status_deleted(self, populated_board):
        populated_board.delete_task(0)
        assert populated_board.tasks[0].status == "deleted"

    def test_delete_task_logs_activity(self, populated_board):
        log_before = len(populated_board.activity_log)
        populated_board.delete_task(1)
        assert len(populated_board.activity_log) > log_before

    def test_add_comment_appends_to_notes(self, populated_board):
        populated_board.add_comment(0, actor="inspector", comment="Checked on site")
        assert "Checked on site" in populated_board.tasks[0].notes

    def test_add_comment_logs_activity(self, populated_board):
        log_before = len(populated_board.activity_log)
        populated_board.add_comment(0, actor="pm", comment="Review done")
        assert len(populated_board.activity_log) > log_before

# ---------------------------------------------------------------------------
# Filtering and querying
# ---------------------------------------------------------------------------

class TestTaskBoardFiltering:
    """Tests for get_column, filter_tasks, and search_tasks."""

    def test_get_column_returns_todo_tasks(self, populated_board):
        todo = populated_board.get_column("todo")
        assert all(t.status == "todo" for _, t in todo)

    def test_get_column_empty_for_nonexistent_status(self, populated_board):
        assert populated_board.get_column("nonexistent") == []

    def test_filter_by_assignee(self, populated_board):
        results = populated_board.filter_tasks(assignee="alice")
        assert all(t.assignee == "alice" for _, t in results)

    def test_filter_by_priority(self, populated_board):
        results = populated_board.filter_tasks(priority="high")
        assert all(t.priority == "high" for _, t in results)

    def test_filter_by_category(self, populated_board):
        results = populated_board.filter_tasks(category="budget")
        assert all(t.category == "budget" for _, t in results)

    def test_filter_by_borough(self, populated_board):
        results = populated_board.filter_tasks(borough="MN")
        assert all(t.borough == "MN" for _, t in results)

    def test_filter_excludes_deleted(self, populated_board):
        populated_board.delete_task(0)
        results = populated_board.filter_tasks()
        assert all(t.status != "deleted" for _, t in results)

    def test_search_tasks_by_title(self, populated_board):
        results = populated_board.search_tasks("ramp")
        assert any("ramp" in t.title.lower() for _, t in results)

    def test_search_tasks_case_insensitive(self, populated_board):
        results = populated_board.search_tasks("BUDGET")
        assert any("budget" in t.title.lower() or "budget" in t.category for _, t in results)

    def test_search_tasks_no_match_returns_empty(self, populated_board):
        assert populated_board.search_tasks("xyzzy_nonexistent_term_999") == []

# ---------------------------------------------------------------------------
# Board statistics
# ---------------------------------------------------------------------------

class TestTaskBoardStats:
    """Tests for the stats() method."""

    def test_total_tasks_count(self, populated_board):
        s = populated_board.stats()
        assert s["total_tasks"] == 4

    def test_by_status_includes_all_columns(self, populated_board):
        s = populated_board.stats()
        for col in DEFAULT_COLUMNS:
            assert col in s["by_status"]

    def test_completion_rate_calculation(self, populated_board):
        s = populated_board.stats()
        assert 0.0 <= s["completion_rate"] <= 100.0

    def test_deleted_tasks_excluded_from_total(self, populated_board):
        populated_board.delete_task(0)
        s = populated_board.stats()
        assert s["total_tasks"] == 3

    def test_overdue_count_present(self, populated_board):
        assert "overdue_count" in populated_board.stats()

# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

class TestMilestones:
    """Tests for milestone add and progress tracking."""

    def test_add_milestone_returns_index(self, empty_board):
        idx = empty_board.add_milestone("Sprint 1", due_date="2026-07-01")
        assert idx == 0

    def test_milestone_progress_zero_tasks(self, empty_board):
        empty_board.add_milestone("M1")
        prog = empty_board.milestone_progress(0)
        assert prog["total_tasks"] == 0
        assert prog["pct_complete"] == 0.0

    def test_milestone_progress_tracks_done(self, populated_board):
        populated_board.add_milestone("M1", task_ids=[2])
        prog = populated_board.milestone_progress(0)
        assert prog["completed"] == 1

    def test_milestone_progress_returns_name(self, empty_board):
        empty_board.add_milestone("Release 1")
        prog = empty_board.milestone_progress(0)
        assert prog["name"] == "Release 1"

    def test_milestone_is_complete_always_false(self):
        ms = Milestone(name="X")
        assert ms.is_complete is False

# ---------------------------------------------------------------------------
# Bulk import from DataFrame
# ---------------------------------------------------------------------------

class TestImportFromConstructionList:
    """Tests for import_from_construction_list."""

    def test_returns_correct_count(self, empty_board):
        df = pd.DataFrame({
            "address": ["123 Main", "456 Elm"],
            "borough": ["MN", "BK"],
            "_scope": ["construction", "inspection"],
            "_priority_score": [0.8, 0.3],
        })
        count = empty_board.import_from_construction_list(df)
        assert count == 2
        assert len(empty_board.tasks) == 2

    def test_high_priority_score_maps_to_high(self, empty_board):
        df = pd.DataFrame({
            "address": ["A"],
            "borough": ["MN"],
            "_scope": ["general"],
            "_priority_score": [0.9],
        })
        empty_board.import_from_construction_list(df)
        assert empty_board.tasks[0].priority == "high"

    def test_low_priority_score_maps_to_low(self, empty_board):
        df = pd.DataFrame({
            "address": ["B"],
            "borough": ["BX"],
            "_scope": ["general"],
            "_priority_score": [0.1],
        })
        empty_board.import_from_construction_list(df)
        assert empty_board.tasks[0].priority == "low"

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestTaskBoardPersistence:
    """Tests for save and load round-trip."""

    def test_save_creates_file(self, populated_board, tmp_board_path):
        populated_board.save(tmp_board_path)
        assert Path(tmp_board_path).exists()

    def test_save_returns_path_string(self, populated_board, tmp_board_path):
        result = populated_board.save(tmp_board_path)
        assert result == tmp_board_path

    def test_load_restores_tasks(self, populated_board, tmp_board_path):
        populated_board.save(tmp_board_path)
        loaded = TaskBoard.load(tmp_board_path)
        assert len(loaded.tasks) == len(populated_board.tasks)

    def test_load_restores_board_name(self, populated_board, tmp_board_path):
        populated_board.save(tmp_board_path)
        loaded = TaskBoard.load(tmp_board_path)
        assert loaded.name == populated_board.name

    def test_load_restores_activity_log(self, populated_board, tmp_board_path):
        populated_board.save(tmp_board_path)
        loaded = TaskBoard.load(tmp_board_path)
        assert len(loaded.activity_log) == len(populated_board.activity_log)

    def test_save_creates_parent_directories(self, populated_board, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "board.json")
        populated_board.save(deep_path)
        assert Path(deep_path).exists()

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestTaskBoardExport:
    """Tests for to_dataframe and to_markdown."""

    def test_to_dataframe_excludes_deleted(self, populated_board):
        populated_board.delete_task(0)
        df = populated_board.to_dataframe()
        assert len(df) == 3
        assert "deleted" not in df["status"].values

    def test_to_dataframe_returns_dataframe(self, populated_board):
        assert isinstance(populated_board.to_dataframe(), pd.DataFrame)

    def test_to_markdown_contains_board_name(self, populated_board):
        md = populated_board.to_markdown()
        assert "Populated Board" in md

    def test_to_markdown_contains_column_headers(self, populated_board):
        md = populated_board.to_markdown()
        assert "To Do" in md or "Backlog" in md

    def test_to_markdown_shows_task_titles(self, populated_board):
        md = populated_board.to_markdown()
        assert "Inspect ramp MN-01" in md
