"""YAML profile loading for Analyst Autopilot."""



from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass

class SourceConfig:

    type: str

    path: str | None = None

    sheet: int | str = 0

    domain: str | None = None

    fourfour: str | None = None

    table: str | None = None

    dsn_env: str = "PG_DSN"

    max_rows: int | None = None

    column_map: dict[str, str] = field(default_factory=dict)





@dataclass

class AnalystProfile:

    profile_name: str

    sources: dict[str, SourceConfig]

    outputs_dir: str = "outputs/analyst_pack"

    output_formats: list[str] = field(default_factory=lambda: ["xlsx", "md", "html", "json"])

    steps: dict[str, Any] = field(default_factory=dict)

    contract_ids: list[str] = field(default_factory=list)

    duckdb_path: str = "data/local_db/nyc_mission_control.duckdb"

    offline: bool = False

    budget_codes_path: str | None = None

    inquiry_templates_dir: str = "config/inquiry_templates"

    golden_profile_path: str | None = None

    role: str | None = None

    role_profile_path: str | None = None



    @property

    def prioritize(self) -> bool:

        return bool(self.steps.get("prioritize", True))



    @property

    def contract_report(self) -> bool:

        return bool(self.steps.get("contract_report", True))



    @property

    def program_kpi(self) -> bool:

        return bool(self.steps.get("program_kpi", True))



    @property

    def inquiry_templates(self) -> bool:

        return bool(self.steps.get("inquiry_templates", True))



    @property

    def construction_diff(self) -> bool:

        return bool(self.steps.get("construction_diff", True))



    @property

    def executive_summary(self) -> bool:

        return bool(self.steps.get("executive_summary", True))

    @property
    def publish(self) -> bool:
        """Whether to run a post-pack publish step (requires publish_profile path)."""
        return bool(self.steps.get("publish", False))

    @property
    def publish_profile_path(self) -> str | None:
        v = self.steps.get("publish_profile") or self.steps.get("publish_profile_path")
        return str(v) if v else None



    @property

    def conflict_buffer_m(self) -> float:

        conflicts = self.steps.get("conflicts", {})

        if isinstance(conflicts, dict):

            return float(conflicts.get("buffer_m", 20))

        return 20.0





def _parse_source(name: str, raw: dict[str, Any]) -> SourceConfig:

    return SourceConfig(

        type=str(raw.get("type", "excel")),

        path=raw.get("path"),

        sheet=raw.get("sheet", 0),

        domain=raw.get("domain"),

        fourfour=raw.get("fourfour"),

        table=raw.get("table"),

        dsn_env=str(raw.get("dsn_env", "PG_DSN")),

        max_rows=raw.get("max_rows"),

        column_map=dict(raw.get("column_map", {})),

    )





def load_profile(config_path: str | Path) -> AnalystProfile:

    """Load analyst profile from YAML."""

    path = Path(config_path)

    if not path.exists():

        raise FileNotFoundError(f"Analyst profile not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    sources_raw = data.get("sources", {})

    sources = {k: _parse_source(k, v) for k, v in sources_raw.items()}

    outputs = data.get("outputs", {}) or {}

    return AnalystProfile(

        profile_name=str(data.get("profile_name", path.stem)),

        sources=sources,

        outputs_dir=str(outputs.get("dir", "outputs/analyst_pack")),

        output_formats=list(outputs.get("formats", ["xlsx", "md", "html", "json"])),

        steps=dict(data.get("steps", {})),

        contract_ids=[str(c) for c in data.get("contract_ids", [])],

        duckdb_path=str(data.get("duckdb_path", "data/local_db/nyc_mission_control.duckdb")),

        offline=bool(data.get("offline", False)),

        budget_codes_path=data.get("budget_codes") or data.get("budget_codes_path"),

        inquiry_templates_dir=str(

            data.get("inquiry_templates_dir", "config/inquiry_templates")

        ),

        golden_profile_path=data.get("golden_profile"),

        role=data.get("role"),

        role_profile_path=data.get("role_profile") or data.get("role_profile_path"),

    )

