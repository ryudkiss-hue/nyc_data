import pandas as pd
import pytest

from socrata_toolkit.tools.tasks import TaskBoard, Task, PRIORITY_COLORS, CATEGORY_COLORS


def test_task_creation():
    t = Task(title="Fix sidewalk", priority="high", category="construction")
    assert t.priority_color == PRIORITY_COLORS["high"]
    assert t.category_color == CATEGORY_COLORS["construction"]


def test_task_overdue():
    t = Task(title="Overdue task", due_date="2020-01-01", status="todo")
    assert t.is_overdue is True

    t2 = Task(title="Future task", due_date="2099-01-01", status="todo")
    assert t2.is_overdue is False

    t3 = Task(title="Done task", due_date="2020-01-01", status="done")
    assert t3.is_overdue is False


def test_board_add_and_get():
    board = TaskBoard("Test Board")
    tid = board.add_task(Task(title="Task A", status="todo"))
    assert tid == 0
    tasks = board.get_column("todo")
    assert len(tasks) == 1
    assert tasks[0][1].title == "Task A"


def test_board_move_task():
    board = TaskBoard()
    board.add_task(Task(title="Task A", status="todo"))
    board.move_task(0, "in_progress", actor="tester")
    assert board.tasks[0].status == "in_progress"
    assert any("moved" in a.action for a in board.activity_log)


def test_board_update_task():
    board = TaskBoard()
    board.add_task(Task(title="Original", priority="low"))
    board.update_task(0, priority="critical", assignee="analyst1")
    assert board.tasks[0].priority == "critical"
    assert board.tasks[0].assignee == "analyst1"


def test_board_delete_task():
    board = TaskBoard()
    board.add_task(Task(title="Delete me"))
    board.delete_task(0)
    assert board.tasks[0].status == "deleted"


def test_board_add_comment():
    board = TaskBoard()
    board.add_task(Task(title="Task A"))
    board.add_comment(0, "pm", "Needs review by Friday")
    assert "Needs review" in board.tasks[0].notes


def test_board_filter_tasks():
    board = TaskBoard()
    board.add_task(Task(title="A", priority="high", assignee="user1", category="construction"))
    board.add_task(Task(title="B", priority="low", assignee="user2", category="budget"))
    board.add_task(Task(title="C", priority="high", assignee="user1", category="budget"))

    high = board.filter_tasks(priority="high")
    assert len(high) == 2

    user1 = board.filter_tasks(assignee="user1")
    assert len(user1) == 2

    budget = board.filter_tasks(category="budget")
    assert len(budget) == 2


def test_board_search_tasks():
    board = TaskBoard()
    board.add_task(Task(title="Fix Manhattan sidewalk"))
    board.add_task(Task(title="Brooklyn ramp repair"))
    results = board.search_tasks("manhattan")
    assert len(results) == 1


def test_board_stats():
    board = TaskBoard()
    board.add_task(Task(title="A", status="todo", priority="high"))
    board.add_task(Task(title="B", status="done", priority="low"))
    board.add_task(Task(title="C", status="todo", priority="high"))
    stats = board.stats()
    assert stats["total_tasks"] == 3
    assert stats["by_status"]["todo"] == 2
    assert stats["by_status"]["done"] == 1
    assert stats["by_priority"]["high"] == 2
    assert stats["completion_rate"] == pytest.approx(33.3, abs=0.1)


def test_board_milestones():
    board = TaskBoard()
    t1 = board.add_task(Task(title="A", status="done"))
    t2 = board.add_task(Task(title="B", status="todo"))
    ms_id = board.add_milestone("Sprint 1", task_ids=[t1, t2])
    progress = board.milestone_progress(ms_id)
    assert progress["total_tasks"] == 2
    assert progress["completed"] == 1
    assert progress["pct_complete"] == 50.0


def test_board_import_from_construction_list():
    df = pd.DataFrame({
        "address": ["123 Main St", "456 Oak Ave"],
        "borough": ["MANHATTAN", "BROOKLYN"],
        "_scope": ["sidewalk_repair", "pedestrian_ramp"],
        "_priority_score": [0.8, 0.3],
    })
    board = TaskBoard()
    count = board.import_from_construction_list(df)
    assert count == 2
    assert board.tasks[0].priority == "high"
    assert board.tasks[1].priority == "low"


def test_board_save_and_load(tmp_path):
    path = str(tmp_path / "board.json")
    board = TaskBoard("Test")
    board.add_task(Task(title="A", priority="high"))
    board.add_task(Task(title="B", status="done"))
    board.add_milestone("MS1", task_ids=[0, 1])
    board.team_members = ["alice", "bob"]
    board.save(path)

    loaded = TaskBoard.load(path)
    assert loaded.name == "Test"
    assert len(loaded.tasks) == 2
    assert len(loaded.milestones) == 1
    assert loaded.team_members == ["alice", "bob"]


def test_board_to_dataframe():
    board = TaskBoard()
    board.add_task(Task(title="A"))
    board.add_task(Task(title="B"))
    df = board.to_dataframe()
    assert len(df) == 2
    assert "title" in df.columns


def test_board_to_markdown():
    board = TaskBoard("My Board")
    board.add_task(Task(title="Task A", status="todo", priority="high", assignee="pm"))
    board.add_task(Task(title="Task B", status="done", priority="low"))
    md = board.to_markdown()
    assert "# My Board" in md
    assert "Task A" in md
    assert "@pm" in md
