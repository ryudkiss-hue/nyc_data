"""Load Analyst Pack tables into dataframes for Dash callbacks."""



from __future__ import annotations



import json

from functools import lru_cache

from pathlib import Path



import pandas as pd



from dash_app.data.analyst_pack import (

    latest_pack_dir,

    load_construction_list,

    load_manifest,

    load_program_kpi,

    load_role_kpi_dashboard,

)





def _pack_cache_key(pack_dir: Path | str | None) -> tuple[str, float]:

    pack = resolve_pack_dir(pack_dir)

    if not pack:

        return ("", 0.0)

    manifest = pack / "manifest.json"

    mtime = manifest.stat().st_mtime if manifest.exists() else pack.stat().st_mtime

    return (str(pack.resolve()), mtime)





def resolve_pack_dir(pack_dir: Path | str | None = None) -> Path | None:

    if pack_dir is None:

        return latest_pack_dir()

    p = Path(pack_dir)

    return p if p.exists() else None





@lru_cache(maxsize=8)

def _cached_pack_tables(key: tuple[str, float]) -> dict[str, object]:

    path_str, _ = key

    if not path_str:

        return {

            "construction": pd.DataFrame(),

            "manifest": {},

            "contract_analytics": {},

            "program_kpi": {},

            "role_kpi": {},

        }

    pack = Path(path_str)

    out: dict[str, object] = {

        "construction": load_construction_list(pack),

        "manifest": load_manifest(pack),

        "program_kpi": load_program_kpi(pack),

        "role_kpi": load_role_kpi_dashboard(pack),

        "contract_analytics": {},

    }

    ca_path = pack / "contract_analytics.json"

    if ca_path.exists():

        out["contract_analytics"] = json.loads(ca_path.read_text(encoding="utf-8"))

    return out





def load_pack_tables(pack_dir: Path | str | None = None) -> dict[str, pd.DataFrame | dict]:

    """Return staged tables from the latest (or given) pack for client-side exploration."""

    key = _pack_cache_key(pack_dir)

    raw = _cached_pack_tables(key)

    return {

        "construction": raw["construction"],

        "manifest": raw["manifest"],

        "contract_analytics": raw["contract_analytics"],

        "program_kpi": raw["program_kpi"],

        "role_kpi": raw["role_kpi"],

    }





@lru_cache(maxsize=16)

def _cached_manifest_summary(key: tuple[str, float]) -> dict:

    path_str, _ = key

    if not path_str:

        return {"run_date": "", "artifact_count": 0, "warning_count": 0, "health": "none"}

    manifest = load_manifest(Path(path_str))

    warnings = manifest.get("warnings", []) or []

    partial = manifest.get("partial_failures", []) or []

    health = "warn" if warnings or partial else "ok"

    return {

        "run_date": manifest.get("run_date", Path(path_str).name),

        "profile_name": manifest.get("profile_name", ""),

        "artifact_count": len(manifest.get("artifacts", {}) or {}),

        "warning_count": len(warnings) + len(partial),

        "health": health,

    }





def manifest_summary(pack_dir: Path | str | None = None) -> dict:

    return dict(_cached_manifest_summary(_pack_cache_key(pack_dir)))





def construction_records(pack_dir: Path | str | None = None, *, limit: int | None = None) -> list[dict]:

    df = load_pack_tables(pack_dir)["construction"]

    if isinstance(df, pd.DataFrame) and not df.empty:

        if limit is not None:

            df = df.head(limit)

        return df.to_dict("records")

    return []





def invalidate_pack_cache() -> None:

    _cached_pack_tables.cache_clear()

    _cached_manifest_summary.cache_clear()


