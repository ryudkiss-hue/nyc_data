"""Analyst Autopilot workflow orchestration."""



from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..engineering.construction_list import (
    ConflictCheckResult,
    detect_construction_conflicts,
    export_construction_list,
    prioritize_construction_list,
)
from ..engineering.contract_analytics import (
    analyze_contract_progress,
    budget_analysis,
    productivity_metrics,
)
from ..program_metrics import compute_program_dashboard
from ..reporting import generate_contract_report
from .budget import load_budget_rules, validate_budget_codes
from .config import AnalystProfile, load_profile
from .conflicts_queue import build_conflicts_review
from .diff import diff_construction_lists, find_previous_pack_dir
from .executive import build_executive_summary
from .inquiries import render_inquiry_drafts
from .pack import AnalystPackResult, assemble_pack
from .publish import publish_pack
from .roles import (
    build_role_task_status_md,
    compute_role_kpis,
    evaluate_task_checklist,
    load_role_profile,
    merge_program_and_role_kpis,
    resolve_role_profile_path,
    write_role_artifacts,
)
from .sources import build_source


def _normalize_frames(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:

    """Apply light normalization for common analyst column names."""

    aliases = {

        "boro": "borough",

        "boro_name": "borough",

        "contract": "contract_id",

        "loc_id": "location_id",

        "severity_rating": "severity",

    }

    out: dict[str, pd.DataFrame] = {}

    for name, df in frames.items():

        if df.empty:

            out[name] = df

            continue

        mapping = {c: aliases[c] for c in df.columns if c in aliases}

        out[name] = df.rename(columns=mapping)

    return out





def _load_sources(

    profile: AnalystProfile,

) -> tuple[dict[str, pd.DataFrame], dict[str, Any], list[dict[str, str]], list[str]]:

    """Load all sources; continue on failure (fail loud, partial OK)."""

    frames: dict[str, pd.DataFrame] = {}

    source_stats: dict[str, Any] = {}

    partial_failures: list[dict[str, str]] = []

    warnings: list[str] = []



    for name, src_cfg in profile.sources.items():

        if profile.offline and src_cfg.type.lower() == "socrata":

            warnings.append(f"{name}: skipped (offline mode)")

            frames[name] = pd.DataFrame()

            source_stats[name] = {"rows": 0, "status": "skipped_offline"}

            continue

        try:

            df = build_source(src_cfg).load()

            frames[name] = df

            source_stats[name] = {

                "rows": len(df),

                "status": "ok",

                "type": src_cfg.type,

            }

        except Exception as exc:

            partial_failures.append({"source": name, "error": str(exc)})

            frames[name] = pd.DataFrame()

            source_stats[name] = {"rows": 0, "status": "failed", "error": str(exc)}

            warnings.append(f"{name}: FAILED — {exc}")



    return frames, source_stats, partial_failures, warnings





def _stage_duckdb(profile: AnalystProfile, frames: dict[str, pd.DataFrame]) -> None:

    try:

        from ..core import DuckDBManager



        mgr = DuckDBManager(profile.duckdb_path)

        for name, df in frames.items():

            if df.empty:

                continue

            # Sanitize name: only allow alphanumeric and underscores as identifier
            import re
            safe_name = re.sub(r'[^\w]', '_', name)
            view_name = f"analyst_{safe_name}"
            mgr.conn.register(view_name, df)

            mgr.conn.execute(
                f'CREATE OR REPLACE TABLE "{view_name}" AS SELECT * FROM "{view_name}"'
            )

        mgr.close()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"DuckDB Staging Failed: {exc}")





def _run_dry_run_pack(
    profile: AnalystProfile, started_at: str
) -> AnalystPackResult:
    """Probe sources without writing outputs; return a manifest-only result."""
    warnings: list[str] = []
    source_stats: dict[str, Any] = {}
    for name, src_cfg in profile.sources.items():
        if profile.offline and src_cfg.type.lower() == "socrata":
            warnings.append(f"{name}: skipped (offline)")
            source_stats[name] = {"status": "skipped_offline"}
            continue
        try:
            df = build_source(src_cfg).load()
            warnings.append(f"{name}: {len(df)} rows")
            source_stats[name] = {"rows": len(df), "status": "ok"}
        except Exception as exc:
            warnings.append(f"{name}: ERROR {exc}")
            source_stats[name] = {"status": "failed", "error": str(exc)}
    result = assemble_pack(profile, dry_run=True, sources=source_stats, warnings=warnings)
    result.started_at = started_at
    result.write_manifest()
    return result


def _build_construction_plan(
    profile: AnalystProfile,
    inspections: pd.DataFrame,
    permits: pd.DataFrame,
) -> tuple[pd.DataFrame, ConflictCheckResult | None, str, pd.DataFrame, str]:
    """Prioritize construction list, detect conflicts, and compute diff."""
    construction = pd.DataFrame()
    conflict_result: ConflictCheckResult | None = None
    conflicts_md = ""
    conflicts_review = pd.DataFrame()
    construction_diff_md = ""

    if profile.prioritize and not inspections.empty:
        construction = prioritize_construction_list(inspections)
        if not permits.empty:
            conflict_result = detect_construction_conflicts(construction, permits)
            construction = conflict_result.clean
            conflicts_md = (
                "# Construction Conflicts Summary\n\n"
                f"- Total items: {conflict_result.total_items}\n"
                f"- Conflicts: {conflict_result.conflict_count}\n"
                f"- Conflict rate: {conflict_result.conflict_rate}%\n"
            )
            if conflict_result.summary_by_borough:
                conflicts_md += "\n## By Borough\n"
                for boro, cnt in conflict_result.summary_by_borough.items():
                    conflicts_md += f"- {boro}: {cnt}\n"
            conflicts_review = build_conflicts_review(conflict_result.conflicts)

    if profile.construction_diff and not construction.empty:
        day = datetime.now(timezone.utc).date().isoformat()
        pack_dir = Path(profile.outputs_dir) / day
        prev = find_previous_pack_dir(pack_dir, Path(profile.outputs_dir))
        prev_df = pd.DataFrame()
        if prev and (prev / "construction_list.xlsx").exists():
            prev_df = pd.read_excel(prev / "construction_list.xlsx", engine="openpyxl")
        _, construction_diff_md = diff_construction_lists(construction, prev_df)

    return construction, conflict_result, conflicts_md, conflicts_review, construction_diff_md


def _compute_kpi_payload(
    profile: AnalystProfile,
    contracts: pd.DataFrame,
    inspections: pd.DataFrame,
) -> tuple[dict[str, Any] | None, str | None]:
    """Compute program KPI dashboard and write JSON sidecar. Returns (payload, path)."""
    if not profile.program_kpi:
        return None, None
    kpi_df = contracts if not contracts.empty else inspections
    if kpi_df.empty:
        return None, None
    dashboard = compute_program_dashboard(kpi_df)
    td = Path(tempfile.mkdtemp(prefix="analyst_kpi_"))
    kpi_json = td / "program_kpi.json"
    kpi_payload: dict[str, Any] = {
        "overall_health": dashboard.overall_health,
        "metrics": [
            {"name": m.name, "value": m.value, "target": m.target, "status": m.status}
            for m in dashboard.metrics
        ],
    }
    kpi_json.write_text(json.dumps(kpi_payload, indent=2), encoding="utf-8")
    return kpi_payload, str(kpi_json)


def _apply_role_profile(
    profile: AnalystProfile,
    result: AnalystPackResult,
    inspections: pd.DataFrame,
    construction: pd.DataFrame,
    contracts: pd.DataFrame,
    conflicts_md: str,
    construction_diff_md: str,
    kpi_payload: dict[str, Any] | None,
    warnings: list[str],
) -> None:
    """Evaluate role task checklist and write role KPI artifacts into the pack."""
    role_profile_path = resolve_role_profile_path(profile.role, profile.role_profile_path)
    if not role_profile_path:
        return
    try:
        role_profile = load_role_profile(role_profile_path)
        tasks, task_pct = evaluate_task_checklist(role_profile, result.pack_dir, result.artifacts)
        task_md = build_role_task_status_md(role_profile, tasks, task_pct, result.run_date)
        role_dashboard = compute_role_kpis(
            role_profile,
            inspections=inspections,
            construction=construction,
            contracts=contracts,
            conflicts_md=conflicts_md,
            construction_diff_md=construction_diff_md,
            program_kpi=kpi_payload,
            pack_artifacts=result.artifacts,
            task_completion_pct=task_pct,
        )
        merged = merge_program_and_role_kpis(kpi_payload, role_dashboard) if kpi_payload else None
        role_arts = write_role_artifacts(result.pack_dir, role_dashboard, task_md, merged_program_kpi=merged)
        result.artifacts.update(role_arts)
        result.write_manifest()
    except Exception as exc:
        warnings.append(f"role profile: FAILED — {exc}")
        result.warnings = warnings
        result.write_manifest()


def run_analyst_pack(
    config_path: str | Path,
    *,
    dry_run: bool = False,
    offline: bool | None = None,
) -> AnalystPackResult:
    """Run the full analyst workflow from a YAML profile."""
    started_at = datetime.now(timezone.utc).isoformat()
    profile = load_profile(config_path)
    if offline is not None:
        profile.offline = bool(offline)

    if dry_run:
        return _run_dry_run_pack(profile, started_at)

    frames, source_stats, partial_failures, warnings = _load_sources(profile)
    frames = _normalize_frames(frames)
    _stage_duckdb(profile, frames)

    inspections = frames.get("inspections", pd.DataFrame())
    contracts = frames.get("contracts", pd.DataFrame())
    permits = frames.get("permits", pd.DataFrame())

    if profile.budget_codes_path:
        rules = load_budget_rules(profile.budget_codes_path)
        warnings.extend(validate_budget_codes(contracts, rules))

    construction, conflict_result, conflicts_md, conflicts_review, construction_diff_md = (
        _build_construction_plan(profile, inspections, permits)
    )

    contract_report_path: str | None = None
    if profile.contract_report and not contracts.empty:
        report = generate_contract_report(contracts)
        td = Path(tempfile.mkdtemp(prefix="analyst_contract_"))
        contract_report_path = str(td / "contract_status.md")
        report.save(contract_report_path)

    kpi_payload, program_kpi_path = _compute_kpi_payload(profile, contracts, inspections)

    inquiry_dir: Path | None = None
    if profile.inquiry_templates and not contracts.empty:
        inquiry_dir = Path(tempfile.mkdtemp(prefix="analyst_inquiry_"))
        render_inquiry_drafts(
            contracts,
            profile.inquiry_templates_dir,
            inquiry_dir,
            contract_ids=profile.contract_ids or None,
        )

    executive_md = ""
    executive_html = ""
    if profile.executive_summary:
        executive_md, executive_html = build_executive_summary(
            construction=construction,
            conflict_result=conflict_result,
            contracts=contracts,
            kpi_payload=kpi_payload,
            run_date=datetime.now(timezone.utc).date().isoformat(),
            profile_name=profile.profile_name,
        )

    result = assemble_pack(
        profile,
        construction=construction,
        conflicts_md=conflicts_md,
        conflicts_review=conflicts_review,

        construction_diff_md=construction_diff_md or None,

        contract_report_path=contract_report_path,

        program_kpi_path=program_kpi_path,

        inquiry_dir=inquiry_dir,

        executive_md=executive_md or None,

        executive_html=executive_html or None,

        dry_run=False,

        sources=source_stats,

        partial_failures=partial_failures,

        warnings=warnings,

        started_at=started_at,

    )

    # Data dictionary (trust diagnostics) — written per pack for transparency
    try:
        from .data_dictionary import write_data_dictionary

        arts = write_data_dictionary(result.pack_dir, frames)
        result.artifacts.update(arts)
        result.write_manifest()
    except Exception:
        pass



    if not construction.empty:

        try:

            _cl_path = str(result.pack_dir / "construction_list.xlsx")
            export_construction_list(construction, _cl_path)
            result.artifacts["construction_list"] = _cl_path

        except Exception:

            pass



    if not contracts.empty:

        sidecar = result.pack_dir / "contract_analytics.json"

        try:

            progress = analyze_contract_progress(contracts)

            budget = budget_analysis(contracts)

            productivity = productivity_metrics(contracts)

            sidecar.write_text(

                json.dumps(

                    {

                        "progress": [p.__dict__ for p in progress],

                        "budget": budget.__dict__ if budget else {},

                        "productivity": productivity.__dict__ if productivity else {},

                    },

                    indent=2,

                    default=str,

                ),

                encoding="utf-8",

            )

            result.artifacts["contract_analytics"] = str(sidecar)

            result.write_manifest()

        except Exception:

            pass



    _apply_role_profile(
        profile, result, inspections, construction, contracts,
        conflicts_md, construction_diff_md, kpi_payload, warnings,
    )

    # Persist run state for UX ("Resume" in Dash, publish defaults, last role)
    try:
        from ..core.profiles import ensure_profile_exists
        from ..core.state import save_state

        pp = ensure_profile_exists(result.profile_name)
        payload = {
            "last_pack_dir": str(result.pack_dir),
            "last_profile_name": str(result.profile_name),
            "last_role": str(profile.role or ""),
            "last_run_date": str(result.run_date),
        }
        # New: per-profile state
        save_state(str(pp.state_dir / "last_pack.json"), payload)
        # Backward-compatible: global state remains updated
        save_state("outputs/.state/last_pack.json", payload)
    except Exception:
        pass

    # Export any saved review decisions into this pack (optional)
    try:
        from ..review.store import ReviewStore

        with ReviewStore(profile=result.profile_name) as store:
            arts = store.export_for_pack(pack_dir=result.pack_dir, pack_date=result.run_date)
            if arts:
                result.artifacts.update(arts)
                result.write_manifest()
    except Exception:
        pass

    # Optional publish step (post-pack automation)
    if profile.publish and profile.publish_profile_path:
        try:
            publish_pack(
                pack_dir=result.pack_dir,
                profile_path=profile.publish_profile_path,
                dry_run=False,
            )
        except Exception as exc:
            warnings = list(result.warnings or [])
            warnings.append(f"publish: FAILED — {exc}")
            result.warnings = warnings
            result.write_manifest()

    return result

