import pytest

from socrata_toolkit.ops.workflow import (
    EventTrigger,
    Schedule,
    Step,
    Workflow,
    WorkflowEngine,
    create_complaint_triage_workflow,
    create_construction_list_workflow,
    create_nightly_ingest_workflow,
)


def test_workflow_creation():
    wf = Workflow("test", description="Test workflow")
    wf.add_step(Step("s1", action="profile_data"))
    wf.add_step(Step("s2", action="export", depends_on=["s1"]))
    assert len(wf.steps) == 2


def test_schedule():
    s = Schedule(cron="0 2 * * *")
    assert s.is_scheduled is True
    s2 = Schedule()
    assert s2.is_scheduled is False


def test_engine_register_and_list():
    engine = WorkflowEngine()
    wf = Workflow("test_wf")
    wf.add_step(Step("s1", action="profile_data"))
    engine.register(wf)
    listing = engine.list_workflows()
    assert len(listing) == 1
    assert listing[0]["name"] == "test_wf"


def test_engine_list_actions():
    engine = WorkflowEngine()
    actions = engine.list_actions()
    assert "fetch_dataset" in actions
    assert "profile_data" in actions
    assert "export" in actions
    assert "send_notification" in actions


def test_engine_run_simple(tmp_path):
    import pandas as pd
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))

    # Register a workflow that works with pre-loaded context
    wf = Workflow("test")
    wf.add_step(Step("profile", action="profile_data"))
    wf.add_step(Step("export", action="export", depends_on=["profile"],
                      params={"path": str(tmp_path / "out.csv")}))
    engine.register(wf)

    # Run with pre-loaded dataframe
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    run = engine.run("test", context={"dataframe": df})
    assert run.status == "completed"
    assert len(run.step_results) == 2
    assert run.step_results[0].status == "success"
    assert run.step_results[1].status == "success"


def test_engine_run_missing_dependency(tmp_path):
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))
    wf = Workflow("test")
    # s2 depends on s1 which doesn't exist
    wf.add_step(Step("s2", action="export", depends_on=["s1"]))
    engine.register(wf)
    run = engine.run("test")
    assert run.step_results[0].status == "skipped"


def test_engine_run_unknown_action(tmp_path):
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))
    wf = Workflow("test")
    wf.add_step(Step("bad", action="nonexistent_action"))
    engine.register(wf)
    run = engine.run("test")
    assert run.step_results[0].status == "failed"
    assert "Unknown action" in run.step_results[0].error


def test_engine_custom_action(tmp_path):
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))

    def my_action(params, context):
        context["custom"] = True
        return {"done": True}

    engine.register_action("my_action", my_action)
    wf = Workflow("test")
    wf.add_step(Step("custom", action="my_action"))
    engine.register(wf)
    ctx = {}
    run = engine.run("test", context=ctx)
    assert run.status == "completed"
    assert ctx.get("custom") is True


def test_engine_triggers(tmp_path):
    import pandas as pd
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))

    wf = Workflow("alert_wf")
    wf.add_step(Step("notify", action="send_notification", params={"message": "threshold breached"}))
    engine.register(wf)

    trigger = EventTrigger(name="high_severity", workflow_name="alert_wf",
                            condition="threshold", params={"field": "severity", "threshold": 8})
    engine.register_trigger(trigger)

    # Should trigger
    runs = engine.check_triggers({"severity": 9.5})
    assert len(runs) == 1

    # Should not trigger
    runs = engine.check_triggers({"severity": 5})
    assert len(runs) == 0


def test_engine_save_and_load_state(tmp_path):
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))
    wf = Workflow("persist_test", description="Test persistence", tags=["test"])
    wf.add_step(Step("s1", action="profile_data"))
    engine.register(wf)
    engine.register_trigger(EventTrigger("t1", "persist_test", "threshold", {"field": "v", "threshold": 5}))
    path = engine.save_state()

    engine2 = WorkflowEngine(state_dir=str(tmp_path / "wf"))
    engine2.load_state(path)
    assert "persist_test" in engine2.workflows
    assert len(engine2.triggers) == 1


def test_engine_history(tmp_path):
    import pandas as pd
    engine = WorkflowEngine(state_dir=str(tmp_path / "wf"))
    wf = Workflow("hist")
    wf.add_step(Step("s1", action="profile_data"))
    engine.register(wf)
    engine.run("hist", context={"dataframe": pd.DataFrame({"x": [1]})})
    engine.run("hist", context={"dataframe": pd.DataFrame({"x": [2]})})
    history = engine.get_history("hist")
    assert len(history) == 2


def test_prebuilt_nightly_workflow():
    wf = create_nightly_ingest_workflow("data.cityofnewyork.us", "h9gi-nx95")
    assert wf.name == "nightly_ingest"
    assert len(wf.steps) == 6
    assert wf.schedule.cron == "0 2 * * *"


def test_prebuilt_complaint_triage():
    wf = create_complaint_triage_workflow("data.cityofnewyork.us", "abcd-1234")
    assert len(wf.steps) == 4


def test_prebuilt_construction_list():
    wf = create_construction_list_workflow("data.cityofnewyork.us", "h9gi-nx95")
    assert len(wf.steps) == 5
