"""Assemble Analyst Pack output folder."""



from __future__ import annotations



import json

from dataclasses import dataclass, field

from datetime import datetime, timezone

from pathlib import Path

from typing import Any



import pandas as pd



from .. import __version__

from .config import AnalystProfile





@dataclass

class AnalystPackResult:

    """Paths and metadata for a completed analyst pack run."""



    pack_dir: Path

    profile_name: str

    run_date: str

    artifacts: dict[str, str] = field(default_factory=dict)

    dry_run: bool = False

    warnings: list[str] = field(default_factory=list)

    sources: dict[str, Any] = field(default_factory=dict)

    partial_failures: list[dict[str, str]] = field(default_factory=list)

    started_at: str = ""

    finished_at: str = ""



    def manifest_path(self) -> Path:

        return self.pack_dir / "manifest.json"



    def write_manifest(self) -> None:

        payload = {

            "profile_name": self.profile_name,

            "run_date": self.run_date,

            "toolkit_version": __version__,

            "dry_run": self.dry_run,

            "started_at": self.started_at,

            "finished_at": self.finished_at or datetime.now(timezone.utc).isoformat(),

            "sources": self.sources,

            "artifacts": self.artifacts,

            "warnings": self.warnings,

            "partial_failures": self.partial_failures,

        }

        self.pack_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")





def assemble_pack(

    profile: AnalystProfile,

    *,

    construction: pd.DataFrame | None = None,

    conflicts_md: str | None = None,

    contract_report_path: str | None = None,

    program_kpi_path: str | None = None,

    inquiry_dir: Path | None = None,

    construction_diff_md: str | None = None,

    conflicts_review: pd.DataFrame | None = None,

    executive_md: str | None = None,

    executive_html: str | None = None,

    dry_run: bool = False,

    run_date: str | None = None,

    sources: dict[str, Any] | None = None,

    partial_failures: list[dict[str, str]] | None = None,

    warnings: list[str] | None = None,

    started_at: str = "",

) -> AnalystPackResult:

    """Write all artifacts under outputs/analyst_pack/{date}/."""

    day = run_date or datetime.now(timezone.utc).date().isoformat()

    pack_dir = Path(profile.outputs_dir) / day

    if not dry_run:

        pack_dir.mkdir(parents=True, exist_ok=True)



    result = AnalystPackResult(

        pack_dir=pack_dir,

        profile_name=profile.profile_name,

        run_date=day,

        dry_run=dry_run,

        sources=sources or {},

        partial_failures=partial_failures or [],

        warnings=list(warnings or []),

        started_at=started_at,

    )



    if dry_run:

        result.warnings.append("Dry run — no files written")

        return result



    if construction is not None and not construction.empty:

        xlsx = pack_dir / "construction_list.xlsx"

        construction.to_excel(xlsx, index=False, engine="openpyxl")

        result.artifacts["construction_list"] = str(xlsx)



    if conflicts_md:

        path = pack_dir / "conflicts_summary.md"

        path.write_text(conflicts_md, encoding="utf-8")

        result.artifacts["conflicts_summary"] = str(path)



    if construction_diff_md:

        path = pack_dir / "construction_list_diff.md"

        path.write_text(construction_diff_md, encoding="utf-8")

        result.artifacts["construction_list_diff"] = str(path)



    if conflicts_review is not None and not conflicts_review.empty:

        xlsx = pack_dir / "conflicts_review.xlsx"

        conflicts_review.to_excel(xlsx, index=False, engine="openpyxl")

        result.artifacts["conflicts_review"] = str(xlsx)



    if executive_md:

        md_path = pack_dir / "executive_summary.md"

        md_path.write_text(executive_md, encoding="utf-8")

        result.artifacts["executive_summary_md"] = str(md_path)

    if executive_html:

        html_path = pack_dir / "executive_summary.html"

        html_path.write_text(executive_html, encoding="utf-8")

        result.artifacts["executive_summary"] = str(html_path)



    if contract_report_path and Path(contract_report_path).exists():

        dest = pack_dir / "contract_status.md"

        dest.write_text(Path(contract_report_path).read_text(encoding="utf-8"), encoding="utf-8")

        result.artifacts["contract_status"] = str(dest)



    if program_kpi_path and Path(program_kpi_path).exists():

        dest = pack_dir / "program_kpi.json"

        dest.write_text(Path(program_kpi_path).read_text(encoding="utf-8"), encoding="utf-8")

        result.artifacts["program_kpi"] = str(dest)



    if inquiry_dir and inquiry_dir.exists():

        out_inq = pack_dir / "inquiry_drafts"

        out_inq.mkdir(exist_ok=True)

        for f in inquiry_dir.glob("*"):

            if f.is_file():

                (out_inq / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

        result.artifacts["inquiry_drafts"] = str(out_inq)



    result.finished_at = datetime.now(timezone.utc).isoformat()

    result.write_manifest()

    return result

