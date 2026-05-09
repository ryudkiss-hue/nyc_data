"""Centralized Workflow Automation Engine for DOT Sidewalk Toolkit.

Provides a lightweight, file-backed workflow orchestration system:
- Define multi-step pipelines as reusable workflow templates
- Schedule workflows on cron-like intervals (daily, weekly, custom)
- Trigger workflows from data events (new records, threshold breaches)
- Chain toolkit operations (fetch -> analyze -> report -> notify)
- Execution history and status tracking

No external scheduler required -- can run as a single Python process
or be triggered by cron/systemd/Task Scheduler.

Example::

    from socrata_toolkit.workflow_engine import (
        WorkflowEngine,
        Workflow,
        Step,
        Schedule,
    )

    engine = WorkflowEngine()
    wf = Workflow("nightly_ingest", schedule=Schedule(cron="0 2 * * *"))
    wf.add_step(Step("fetch", action="fetch_dataset", params={"domain": "data.cityofnewyork.us", "fourfour": "h9gi-nx95"}))
    wf.add_step(Step("analyze", action="profile_data", depends_on=["fetch"]))
    wf.add_step(Step("report", action="generate_report", depends_on=["analyze"]))
    wf.add_step(Step("notify", action="send_notification", depends_on=["report"]))
    engine.register(wf)
    engine.run("nightly_ingest")
"""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Schedule:
    """Workflow execution schedule."""
    cron: str = ""  # cron expression (for documentation / external schedulers)
    interval_hours: float = 0  # simple interval in hours
    description: str = ""

    @property
    def is_scheduled(self) -> bool:
        return bool(self.cron or self.interval_hours > 0)


@dataclass
class Step:
    """A single step in a workflow pipeline."""
    name: str
    action: str  # key in the action registry
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    on_failure: str = "stop"  # "stop", "skip", "retry"


@dataclass
class StepResult:
    """Result from executing a single step."""
    step_name: str
    status: str  # "success", "failed", "skipped"
    started_at: str
    finished_at: str
    duration_seconds: float
    output: Any = None
    error: Optional[str] = None


@dataclass
class WorkflowRun:
    """Record of a single workflow execution."""
    workflow_name: str
    run_id: str
    status: str  # "running", "completed", "failed", "partial"
    started_at: str
    finished_at: Optional[str] = None
    step_results: List[StepResult] = field(default_factory=list)
    trigger: str = "manual"  # "manual", "scheduled", "event"

    @property
    def duration_seconds(self) -> float:
        if not self.finished_at:
            return 0
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.finished_at)
        return (end - start).total_seconds()


@dataclass
class Workflow:
    """A reusable workflow template."""
    name: str
    description: str = ""
    schedule: Optional[Schedule] = None
    steps: List[Step] = field(default_factory=list)
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def add_step(self, step: Step) -> None:
        self.steps.append(step)


@dataclass
class EventTrigger:
    """A trigger that fires a workflow based on data conditions."""
    name: str
    workflow_name: str
    condition: str  # "threshold", "new_records", "schedule"
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Built-in Actions
# ---------------------------------------------------------------------------

def _action_fetch_dataset(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Fetch data from Socrata."""
    from .client import SocrataClient
    client = SocrataClient()
    domain = params.get("domain", "data.cityofnewyork.us")
    fourfour = params.get("fourfour", "")
    max_rows = params.get("max_rows", 10000)
    df = client.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    context["dataframe"] = df
    return {"rows": len(df), "columns": len(df.columns)}


def _action_profile_data(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Profile the current dataframe."""
    from .analysis import profile_dataframe
    df = context.get("dataframe", pd.DataFrame())
    profile = profile_dataframe(df)
    context["profile"] = profile
    return {"row_count": profile.row_count, "column_count": profile.column_count}


def _action_quality_check(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Run quality scoring."""
    from .governance import compute_quality_score
    df = context.get("dataframe", pd.DataFrame())
    score = compute_quality_score(df, key_columns=params.get("key_columns"))
    context["quality_score"] = score
    return {"overall": score.overall, "completeness": score.completeness}


def _action_detect_outliers(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Detect outliers in numeric columns."""
    from .analysis_advanced import flag_anomalies
    df = context.get("dataframe", pd.DataFrame())
    flagged, report = flag_anomalies(df, method=params.get("method", "iqr"))
    context["dataframe"] = flagged
    context["anomaly_report"] = report
    return {"flagged_rows": report.flagged_rows, "flagged_pct": report.flagged_pct}


def _action_prioritize_list(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Prioritize construction list."""
    from .construction_list import prioritize_construction_list, classify_scope, flag_ada_locations
    df = context.get("dataframe", pd.DataFrame())
    df = prioritize_construction_list(df)
    df = classify_scope(df)
    df = flag_ada_locations(df)
    context["dataframe"] = df
    return {"total": len(df)}


def _action_generate_report(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Generate a contract report."""
    from .reporting import generate_contract_report
    df = context.get("dataframe", pd.DataFrame())
    report = generate_contract_report(df)
    path = params.get("output_path", "outputs/reports/auto_report.md")
    report.save(path)
    context["report_path"] = path
    return {"report_path": path}


def _action_nlp_enrich(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Enrich data with NLP analysis."""
    from .nlp_integration import enrich_construction_list
    df = context.get("dataframe", pd.DataFrame())
    text_col = params.get("text_column", "description")
    if text_col in df.columns:
        df = enrich_construction_list(df, text_col=text_col)
        context["dataframe"] = df
    return {"enriched_columns": [c for c in df.columns if c.startswith("_nlp_")]}


def _action_triage_complaints(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Triage complaints using NLP."""
    from .nlp_integration import triage_complaints
    df = context.get("dataframe", pd.DataFrame())
    text_col = params.get("text_column", "complaint_text")
    df = triage_complaints(df, text_col=text_col)
    context["dataframe"] = df
    critical = (df.get("_triage_priority") == "critical").sum() if "_triage_priority" in df.columns else 0
    return {"triaged": len(df), "critical_count": int(critical)}


def _action_export(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Export dataframe to file."""
    df = context.get("dataframe", pd.DataFrame())
    path = params.get("path", "outputs/export.csv")
    fmt = params.get("format", "csv")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records", indent=2)
    elif fmt == "xlsx":
        df.to_excel(path, index=False)
    return {"path": path, "rows": len(df)}


def _action_send_notification(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Send a notification (logs to activity; would integrate with Teams/email in production)."""
    message = params.get("message", "Workflow completed")
    channel = params.get("channel", "log")
    log.info("NOTIFICATION [%s]: %s", channel, message)
    return {"channel": channel, "message": message}


def _action_compute_kpis(params: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Compute program KPI dashboard."""
    from .program_metrics import compute_program_dashboard
    df = context.get("dataframe", pd.DataFrame())
    dashboard = compute_program_dashboard(df)
    context["dashboard"] = dashboard
    return {"health": dashboard.overall_health, "metrics": len(dashboard.metrics)}


# Action registry
BUILTIN_ACTIONS: Dict[str, Callable] = {
    "fetch_dataset": _action_fetch_dataset,
    "profile_data": _action_profile_data,
    "quality_check": _action_quality_check,
    "detect_outliers": _action_detect_outliers,
    "prioritize_list": _action_prioritize_list,
    "generate_report": _action_generate_report,
    "nlp_enrich": _action_nlp_enrich,
    "triage_complaints": _action_triage_complaints,
    "export": _action_export,
    "send_notification": _action_send_notification,
    "compute_kpis": _action_compute_kpis,
}


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """Centralized workflow orchestration engine.

    Manages workflow registration, execution, and history tracking.
    All state is persisted to JSON files for durability.
    """

    def __init__(self, state_dir: str = "outputs/workflows") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.workflows: Dict[str, Workflow] = {}
        self.actions: Dict[str, Callable] = dict(BUILTIN_ACTIONS)
        self.triggers: List[EventTrigger] = []
        self.history: List[WorkflowRun] = []

    def register(self, workflow: Workflow) -> None:
        """Register a workflow template."""
        self.workflows[workflow.name] = workflow

    def register_action(self, name: str, fn: Callable) -> None:
        """Register a custom action function."""
        self.actions[name] = fn

    def register_trigger(self, trigger: EventTrigger) -> None:
        """Register an event trigger."""
        self.triggers.append(trigger)

    def run(self, workflow_name: str, trigger: str = "manual", context: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        """Execute a workflow by name.

        Steps are executed in order. Dependencies are checked but
        execution is sequential (not parallel).

        Returns a WorkflowRun with step results.
        """
        if workflow_name not in self.workflows:
            raise KeyError(f"Workflow '{workflow_name}' not registered")

        wf = self.workflows[workflow_name]
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run = WorkflowRun(
            workflow_name=workflow_name,
            run_id=run_id,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            trigger=trigger,
        )

        ctx = context if context is not None else {}
        completed_steps: set = set()
        all_success = True

        for step in wf.steps:
            # Check dependencies
            missing_deps = [d for d in step.depends_on if d not in completed_steps]
            if missing_deps:
                result = StepResult(
                    step_name=step.name, status="skipped",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    duration_seconds=0,
                    error=f"Unmet dependencies: {missing_deps}",
                )
                run.step_results.append(result)
                all_success = False
                continue

            action_fn = self.actions.get(step.action)
            if not action_fn:
                result = StepResult(
                    step_name=step.name, status="failed",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    duration_seconds=0,
                    error=f"Unknown action: {step.action}",
                )
                run.step_results.append(result)
                all_success = False
                if step.on_failure == "stop":
                    break
                continue

            start = datetime.now(timezone.utc)
            try:
                output = action_fn(step.params, ctx)
                end = datetime.now(timezone.utc)
                result = StepResult(
                    step_name=step.name, status="success",
                    started_at=start.isoformat(), finished_at=end.isoformat(),
                    duration_seconds=(end - start).total_seconds(),
                    output=output,
                )
                completed_steps.add(step.name)
            except Exception as exc:
                end = datetime.now(timezone.utc)
                result = StepResult(
                    step_name=step.name, status="failed",
                    started_at=start.isoformat(), finished_at=end.isoformat(),
                    duration_seconds=(end - start).total_seconds(),
                    error=str(exc),
                )
                all_success = False
                if step.on_failure == "stop":
                    run.step_results.append(result)
                    break

            run.step_results.append(result)

        run.status = "completed" if all_success else "partial" if completed_steps else "failed"
        run.finished_at = datetime.now(timezone.utc).isoformat()
        self.history.append(run)
        self._save_run(run)
        return run

    def check_triggers(self, event_data: Dict[str, Any]) -> List[WorkflowRun]:
        """Evaluate registered triggers and run matching workflows.

        event_data should contain keys like 'type', 'value', 'threshold', etc.
        """
        runs = []
        for trigger in self.triggers:
            if not trigger.enabled:
                continue
            if self._evaluate_trigger(trigger, event_data):
                run = self.run(trigger.workflow_name, trigger="event")
                runs.append(run)
        return runs

    def get_history(self, workflow_name: Optional[str] = None, last_n: int = 20) -> List[WorkflowRun]:
        """Get execution history, optionally filtered by workflow name."""
        history = self.history
        if workflow_name:
            history = [r for r in history if r.workflow_name == workflow_name]
        return history[-last_n:]

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all registered workflows with their metadata."""
        return [
            {
                "name": wf.name,
                "description": wf.description,
                "steps": len(wf.steps),
                "enabled": wf.enabled,
                "scheduled": wf.schedule.is_scheduled if wf.schedule else False,
                "tags": wf.tags,
            }
            for wf in self.workflows.values()
        ]

    def list_actions(self) -> List[str]:
        """List all registered action names."""
        return sorted(self.actions.keys())

    def save_state(self) -> str:
        """Persist all workflows and triggers to JSON."""
        state = {
            "workflows": {
                name: {
                    "name": wf.name,
                    "description": wf.description,
                    "enabled": wf.enabled,
                    "tags": wf.tags,
                    "schedule": {"cron": wf.schedule.cron, "interval_hours": wf.schedule.interval_hours} if wf.schedule else None,
                    "steps": [
                        {"name": s.name, "action": s.action, "params": s.params,
                         "depends_on": s.depends_on, "on_failure": s.on_failure}
                        for s in wf.steps
                    ],
                }
                for name, wf in self.workflows.items()
            },
            "triggers": [
                {"name": t.name, "workflow_name": t.workflow_name,
                 "condition": t.condition, "params": t.params, "enabled": t.enabled}
                for t in self.triggers
            ],
        }
        path = str(self.state_dir / "engine_state.json")
        Path(path).write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        return path

    def load_state(self, path: Optional[str] = None) -> None:
        """Load workflows and triggers from JSON."""
        p = Path(path or str(self.state_dir / "engine_state.json"))
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        for name, wf_data in data.get("workflows", {}).items():
            schedule = None
            if wf_data.get("schedule"):
                schedule = Schedule(**wf_data["schedule"])
            wf = Workflow(
                name=wf_data["name"],
                description=wf_data.get("description", ""),
                schedule=schedule,
                enabled=wf_data.get("enabled", True),
                tags=wf_data.get("tags", []),
            )
            for s_data in wf_data.get("steps", []):
                wf.add_step(Step(**s_data))
            self.workflows[name] = wf
        for t_data in data.get("triggers", []):
            self.triggers.append(EventTrigger(**t_data))

    def _save_run(self, run: WorkflowRun) -> None:
        runs_dir = self.state_dir / "runs"
        runs_dir.mkdir(exist_ok=True)
        path = runs_dir / f"{run.workflow_name}_{run.run_id}.json"
        data = {
            "workflow_name": run.workflow_name,
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "trigger": run.trigger,
            "step_results": [
                {"step_name": r.step_name, "status": r.status, "started_at": r.started_at,
                 "finished_at": r.finished_at, "duration_seconds": r.duration_seconds,
                 "output": r.output, "error": r.error}
                for r in run.step_results
            ],
        }
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _evaluate_trigger(self, trigger: EventTrigger, event_data: Dict[str, Any]) -> bool:
        if trigger.condition == "threshold":
            field_name = trigger.params.get("field")
            threshold = trigger.params.get("threshold", 0)
            value = event_data.get(field_name, 0)
            return float(value) > float(threshold)
        if trigger.condition == "new_records":
            return event_data.get("type") == "new_records"
        return False


# ---------------------------------------------------------------------------
# Pre-built Workflow Templates
# ---------------------------------------------------------------------------

def create_nightly_ingest_workflow(domain: str, fourfour: str, report_path: str = "outputs/reports/nightly.md") -> Workflow:
    """Create a pre-configured nightly data ingest workflow."""
    wf = Workflow(
        name="nightly_ingest",
        description="Nightly fetch, analyze, quality check, and report",
        schedule=Schedule(cron="0 2 * * *", description="Daily at 2 AM"),
        tags=["automated", "nightly"],
    )
    wf.add_step(Step("fetch", action="fetch_dataset", params={"domain": domain, "fourfour": fourfour}))
    wf.add_step(Step("profile", action="profile_data", depends_on=["fetch"]))
    wf.add_step(Step("quality", action="quality_check", depends_on=["fetch"]))
    wf.add_step(Step("outliers", action="detect_outliers", depends_on=["fetch"]))
    wf.add_step(Step("report", action="generate_report", depends_on=["profile"], params={"output_path": report_path}))
    wf.add_step(Step("notify", action="send_notification", depends_on=["report"], params={"message": "Nightly ingest complete"}))
    return wf


def create_complaint_triage_workflow(domain: str, fourfour: str) -> Workflow:
    """Create a pre-configured complaint triage workflow."""
    wf = Workflow(
        name="complaint_triage",
        description="Fetch complaints, triage via NLP, export results",
        tags=["nlp", "complaints"],
    )
    wf.add_step(Step("fetch", action="fetch_dataset", params={"domain": domain, "fourfour": fourfour}))
    wf.add_step(Step("triage", action="triage_complaints", depends_on=["fetch"]))
    wf.add_step(Step("export", action="export", depends_on=["triage"], params={"path": "outputs/triaged_complaints.csv"}))
    wf.add_step(Step("notify", action="send_notification", depends_on=["export"], params={"message": "Complaint triage complete"}))
    return wf


def create_construction_list_workflow(domain: str, fourfour: str) -> Workflow:
    """Create a workflow that builds a prioritized construction list."""
    wf = Workflow(
        name="build_construction_list",
        description="Fetch inspections, prioritize, enrich with NLP, export",
        tags=["construction", "nlp"],
    )
    wf.add_step(Step("fetch", action="fetch_dataset", params={"domain": domain, "fourfour": fourfour}))
    wf.add_step(Step("prioritize", action="prioritize_list", depends_on=["fetch"]))
    wf.add_step(Step("enrich", action="nlp_enrich", depends_on=["prioritize"]))
    wf.add_step(Step("kpis", action="compute_kpis", depends_on=["fetch"], on_failure="skip"))
    wf.add_step(Step("export", action="export", depends_on=["enrich"], params={"path": "outputs/construction_list.csv"}))
    return wf
