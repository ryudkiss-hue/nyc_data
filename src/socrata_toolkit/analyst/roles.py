"""Role profiles — job-duty checklists and role-specific KPIs for analyst pack."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ..program_metrics import MetricDefinition, _compute_status

ROLE_PROFILES_DIR = Path("config/role_profiles")

@dataclass
class RoleDuty:
    id: str
    text: str
    workflow_steps: list[str] = field(default_factory=list)
    pack_outputs: list[str] = field(default_factory=list)
    inquiry_templates: list[str] = field(default_factory=list)

@dataclass
class RoleKpiDef:
    name: str
    description: str
    formula: str
    direction: str
    target: float
    warning_threshold: float
    critical_threshold: float
    data_source: dict[str, Any] = field(default_factory=dict)

@dataclass
class RoleProfile:
    role_id: str
    display_name: str
    job_reference: dict[str, Any]
    unit_focus: str
    duties: list[RoleDuty]
    kpis: list[RoleKpiDef]
    path: Path | None = None

@dataclass
class RoleKpiSnapshot:
    name: str
    value: float
    target: float
    status: str
    description: str

@dataclass
class RoleKpiDashboard:
    role_id: str
    display_name: str
    job_reference: dict[str, Any]
    metrics: list[RoleKpiSnapshot]
    overall_health: str
    program_kpi_merged: bool = False

def _parse_duty(raw: dict[str, Any]) -> RoleDuty:
    return RoleDuty(
        id=str(raw.get("id", "")),
        text=str(raw.get("text", "")),
        workflow_steps=[str(s) for s in raw.get("workflow_steps", [])],
        pack_outputs=[str(p) for p in raw.get("pack_outputs", [])],
        inquiry_templates=[str(t) for t in raw.get("inquiry_templates", [])],
    )

def _parse_kpi(raw: dict[str, Any]) -> RoleKpiDef:
    return RoleKpiDef(
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        formula=str(raw.get("formula", "")),
        direction=str(raw.get("direction", "lower_is_better")),
        target=float(raw.get("target", 0)),
        warning_threshold=float(raw.get("warning_threshold", 0)),
        critical_threshold=float(raw.get("critical_threshold", 0)),
        data_source=dict(raw.get("data_source", {})),
    )

def load_role_profile(role_or_path: str | Path) -> RoleProfile:
    """Load a role YAML by role_id (filename stem) or explicit path."""
    path = Path(role_or_path)
    if not path.suffix:
        path = ROLE_PROFILES_DIR / f"{role_or_path}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Role profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return RoleProfile(
        role_id=str(data.get("role_id", path.stem)),
        display_name=str(data.get("display_name", path.stem)),
        job_reference=dict(data.get("job_reference", {})),
        unit_focus=str(data.get("unit_focus", "")),
        duties=[_parse_duty(d) for d in data.get("duties", [])],
        kpis=[_parse_kpi(k) for k in data.get("metrics", [])],
        path=path,
    )

def list_role_profiles(directory: str | Path | None = None) -> list[RoleProfile]:
    """Load all role profiles in config/role_profiles/."""
    root = Path(directory or ROLE_PROFILES_DIR)
    if not root.exists():
        return []
    profiles: list[RoleProfile] = []
    for yaml_path in sorted(root.glob("*.yaml")):
        try:
            profiles.append(load_role_profile(yaml_path))
        except Exception:
            continue
    return profiles

def resolve_role_profile_path(role: str | None, explicit: str | None = None) -> Path | None:
    """Resolve a role profile file path from a role_id or an explicit path string."""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else ROLE_PROFILES_DIR / explicit
    if role:
        p = ROLE_PROFILES_DIR / f"{role}.yaml"
        return p if p.exists() else None
    return None

def _kpi_status(value: float, defn: RoleKpiDef) -> str:
    metric = MetricDefinition(
        name=defn.name,
        description=defn.description,
        unit="",
        target=defn.target,
        warning_threshold=defn.warning_threshold,
        critical_threshold=defn.critical_threshold,
        direction=defn.direction,
    )
    return _compute_status(value, metric)

def _parse_conflict_rate(conflicts_md: str) -> float | None:
    if not conflicts_md:
        return None
    m = re.search(r"Conflict rate:\s*([\d.]+)%", conflicts_md, re.I)
    return float(m.group(1)) if m else None

def _parse_diff_added(construction_diff_md: str) -> float:
    if not construction_diff_md:
        return 0.0
    m = re.search(r"Added[:\s]+(\d+)", construction_diff_md, re.I)
    return float(m.group(1)) if m else 0.0

def _program_green_pct(program_kpi: dict[str, Any] | None) -> float | None:
    if not program_kpi:
        return None
    metrics = program_kpi.get("metrics", [])
    if not metrics:
        return None
    green = sum(1 for m in metrics if m.get("status") == "green")
    return (green / len(metrics)) * 100.0

def compute_role_kpis(
    role: RoleProfile,
    *,
    inspections: pd.DataFrame | None = None,
    construction: pd.DataFrame | None = None,
    contracts: pd.DataFrame | None = None,
    conflicts_md: str = "",
    construction_diff_md: str = "",
    program_kpi: dict[str, Any] | None = None,
    pack_artifacts: dict[str, str] | None = None,
    task_completion_pct: float | None = None,
) -> RoleKpiDashboard:
    """Compute role-specific KPI values from pack inputs."""
    inspections = inspections if inspections is not None else pd.DataFrame()
    construction = construction if construction is not None else pd.DataFrame()
    contracts = contracts if contracts is not None else pd.DataFrame()
    pack_artifacts = pack_artifacts or {}

    computed: dict[str, float] = {}

    if not inspections.empty and "severity" in inspections.columns:
        high = inspections[inspections["severity"].fillna(0) >= 4]
        on_list = set()
        if not construction.empty and "location_id" in construction.columns:
            on_list = set(construction["location_id"].astype(str))
        backlog = sum(1 for lid in high.get("location_id", []) if str(lid) not in on_list)
        computed["high_priority_backlog"] = float(backlog)

    rate = _parse_conflict_rate(conflicts_md)
    if rate is not None:
        computed["conflict_rate_pct"] = rate

    has_exec = bool(
        pack_artifacts.get("executive_summary")
        or pack_artifacts.get("executive_summary_md")
    )
    has_contract = bool(pack_artifacts.get("contract_status"))
    computed["ifa_report_ready"] = 1.0 if (has_exec and has_contract) else 0.0

    if not construction.empty:
        ada_col = "ada_flag" in construction.columns
        sev_col = "severity" in construction.columns
        mask = pd.Series(False, index=construction.index)
        if ada_col:
            mask = mask | (construction["ada_flag"].fillna(0).astype(float) >= 1)
        if sev_col:
            mask = mask | (construction["severity"].fillna(0) >= 5)
        computed["ramp_make_safe_queue"] = float(mask.sum())

    if task_completion_pct is not None:
        computed["administrative_review_coverage"] = float(task_completion_pct)

    if not contracts.empty:
        if {"actual_sqft", "planned_sqft"}.issubset(contracts.columns):
            planned = contracts["planned_sqft"].replace(0, pd.NA).astype(float)
            pct = (contracts["actual_sqft"].astype(float) / planned * 100).dropna()
            if len(pct):
                computed["contract_completion_pct"] = float(pct.mean())
        if {"actual_spend", "planned_spend"}.issubset(contracts.columns):
            planned_sum = float(contracts["planned_spend"].fillna(0).sum())
            if planned_sum > 0:
                actual_sum = float(contracts["actual_spend"].fillna(0).sum())
                computed["budget_burn_variance_pct"] = (
                    (actual_sum - planned_sum) / planned_sum
                ) * 100.0

    computed["construction_list_delta"] = _parse_diff_added(construction_diff_md)

    green_pct = _program_green_pct(program_kpi)
    if green_pct is not None:
        computed["program_health_score"] = green_pct

    snapshots: list[RoleKpiSnapshot] = []
    for kpi_def in role.kpis:
        value = computed.get(kpi_def.name)
        if value is None:
            continue
        status = _kpi_status(value, kpi_def)
        snapshots.append(
            RoleKpiSnapshot(
                name=kpi_def.name,
                value=round(value, 2),
                target=kpi_def.target,
                status=status,
                description=kpi_def.description,
            )
        )

    statuses = [s.status for s in snapshots]
    if "red" in statuses:
        health = "red"
    elif "yellow" in statuses:
        health = "yellow"
    elif snapshots:
        health = "green"
    else:
        health = "unknown"

    return RoleKpiDashboard(
        role_id=role.role_id,
        display_name=role.display_name,
        job_reference=role.job_reference,
        metrics=snapshots,
        overall_health=health,
    )

def evaluate_task_checklist(
    role: RoleProfile,
    pack_dir: Path,
    artifacts: dict[str, str],
) -> tuple[list[dict[str, Any]], float]:
    """Return per-duty status and overall completion percent."""
    rows: list[dict[str, Any]] = []
    done = 0
    def _output_present(out_pattern: str) -> bool:
        if out_pattern.endswith("/"):
            folder = pack_dir / out_pattern.strip("/").split("/")[0]
            return folder.is_dir() and any(folder.iterdir())
        stem = out_pattern.replace("/", "")
        if (pack_dir / out_pattern).exists():
            return True
        if stem in artifacts:
            return True
        for key, path in artifacts.items():
            if out_pattern in path or key == stem.replace(".xlsx", "").replace(".md", "").replace(".html", "").replace(".json", ""):
                return True
        return False

    for duty in role.duties:
        outputs_ok: list[bool] = []
        for out_pattern in duty.pack_outputs:
            outputs_ok.append(_output_present(out_pattern))
        complete = bool(outputs_ok) and all(outputs_ok)
        if complete:
            done += 1
        rows.append(
            {
                "id": duty.id,
                "duty": duty.text,
                "workflow_steps": duty.workflow_steps,
                "pack_outputs": duty.pack_outputs,
                "complete": complete,
            }
        )
    total = len(role.duties) or 1
    pct = (done / total) * 100.0
    return rows, pct

def build_role_task_status_md(
    role: RoleProfile,
    tasks: list[dict[str, Any]],
    completion_pct: float,
    run_date: str,
) -> str:
    """Render a Markdown task-status report for the role from per-duty completion data."""
    lines = [
        f"# Role task status — {role.display_name}",
        "",
        f"**Run date:** {run_date}",
        f"**Job reference:** {role.job_reference.get('business_title', role.role_id)} "
        f"(jid-{role.job_reference.get('jid', 'n/a')})",
        "",
        f"**Completion:** {completion_pct:.0f}% ({sum(1 for t in tasks if t['complete'])}/{len(tasks)} duties)",
        "",
        role.unit_focus.strip(),
        "",
        "## Checklist",
        "",
    ]
    for t in tasks:
        mark = "x" if t["complete"] else " "
        lines.append(f"- [{mark}] **{t['id']}** — {t['duty']}")
        if t.get("pack_outputs"):
            lines.append(f"  - Expected: {', '.join(t['pack_outputs'])}")
    lines.append("")
    ref = role.job_reference.get("url")
    if ref:
        lines.append(f"[City Jobs posting]({ref})")
    return "\n".join(lines)

def role_dashboard_to_dict(dashboard: RoleKpiDashboard) -> dict[str, Any]:
    """Serialize a RoleKpiDashboard to a JSON-compatible dict."""
    return {
        "role_id": dashboard.role_id,
        "display_name": dashboard.display_name,
        "job_reference": dashboard.job_reference,
        "overall_health": dashboard.overall_health,
        "program_kpi_merged": dashboard.program_kpi_merged,
        "metrics": [
            {
                "name": m.name,
                "value": m.value,
                "target": m.target,
                "status": m.status,
                "description": m.description,
            }
            for m in dashboard.metrics
        ],
    }

def merge_program_and_role_kpis(
    program_kpi: dict[str, Any] | None,
    role_dashboard: RoleKpiDashboard,
) -> dict[str, Any]:
    """Combine standard program KPIs with role-specific metrics for one JSON file."""
    base = dict(program_kpi or {})
    base["role"] = role_dashboard_to_dict(role_dashboard)
    role_dashboard.program_kpi_merged = True
    return base

def write_role_artifacts(
    pack_dir: Path,
    role_dashboard: RoleKpiDashboard,
    task_md: str,
    *,
    merged_program_kpi: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Write role KPI JSON and task status markdown; return artifact paths."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    kpi_path = pack_dir / "role_kpi_dashboard.json"
    kpi_path.write_text(
        json.dumps(role_dashboard_to_dict(role_dashboard), indent=2),
        encoding="utf-8",
    )
    artifacts["role_kpi_dashboard"] = str(kpi_path)

    task_path = pack_dir / "role_task_status.md"
    task_path.write_text(task_md, encoding="utf-8")
    artifacts["role_task_status"] = str(task_path)

    if merged_program_kpi is not None:
        prog_path = pack_dir / "program_kpi.json"
        prog_path.write_text(json.dumps(merged_program_kpi, indent=2), encoding="utf-8")
        artifacts["program_kpi"] = str(prog_path)

    return artifacts
