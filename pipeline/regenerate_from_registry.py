#!/usr/bin/env python3
"""
REGENERATE-FROM-REGISTRY — propagate registry changes to all derived files.

The authoritative NYC Open Data registry (pipeline/data/nyc_open_data_registry.json)
is the single source of truth. Whenever it changes (new datasets, updated
metadata, changed columns), this script regenerates every dependent project
artifact so nothing drifts out of sync:

  1. pipeline/config/socrata_datasets.json   — refresh each dataset's metadata
     (ll251_name, last_updated, row_count, column_count) from the registry;
     flag any configured socrata_id that no longer exists in the registry.
  2. pipeline/sql/02_staging_schema.sql        — regenerate from LIVE column
     introspection (dedup on real keys; geometry/keyless tables promoted as-is).
  3. pipeline/data/DATA_CATALOG.md             — human-readable catalog of every
     configured dataset, generated from the registry.

Run standalone:   python pipeline/regenerate_from_registry.py
Run daily:        invoked automatically at the end of sync_socrata_config.py
                  (registry refresh -> regenerate derived files).

DB-dependent steps (staging SQL) are best-effort: if MotherDuck is unreachable,
the config + catalog still regenerate and a warning is logged.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FILE = ROOT / "pipeline" / "data" / "nyc_open_data_registry.json"
CONFIG_FILE = ROOT / "pipeline" / "config" / "socrata_datasets.json"
STAGING_SQL = ROOT / "pipeline" / "sql" / "02_staging_schema.sql"
CATALOG_MD = ROOT / "pipeline" / "data" / "DATA_CATALOG.md"


def load_registry():
    return json.load(open(REGISTRY_FILE))["datasets"]


def load_config():
    return json.load(open(CONFIG_FILE))


# --- 1. Refresh config metadata from the registry ---------------------------
def refresh_config_metadata(config, registry):
    missing = []
    refreshed = 0
    for d in config.get("socrata_remaining", []):
        sid = d.get("socrata_id")
        reg = registry.get(sid)
        if not reg:
            missing.append((d.get("name"), sid))
            d["registry_status"] = "MISSING_FROM_REGISTRY"
            continue
        d["ll251_name"] = reg.get("name", d.get("ll251_name"))
        d["last_updated"] = reg.get("last_updated", "")
        d["registry_row_count"] = reg.get("row_count", 0)
        d["column_count"] = len(reg.get("columns", []))
        d["registry_status"] = "OK"
        refreshed += 1
    config.setdefault("metadata", {})["last_regenerated"] = "registry-driven"
    config["metadata"]["total_datasets"] = len(config.get("socrata_remaining", []))
    json.dump(config, open(CONFIG_FILE, "w"), indent=2)
    return refreshed, missing


# --- 2. Regenerate staging SQL from LIVE columns ----------------------------
def _pick_key(cols):
    priority = ("inspectionid", "violationid", "reinspectionid", "atdid", "rampid",
                "bblid", "objectid", "sr", "swv_number", "cornerid",
                "workscheduleprojectlocationid", "unique_key", "segmentid")
    low = {c.lower(): c for c in cols}
    for p in priority:
        if p in low:
            return low[p]
    for c in cols:
        if c.lower().endswith("id") and not c.startswith(":@"):
            return c
    return None


def generate_staging_sql(con, config):
    names = [d["name"] for d in config.get("socrata_remaining", [])]
    lines = [
        "-- Staging Schema - AUTO-GENERATED from live columns by regenerate_from_registry.py",
        "-- Do not edit by hand; rerun the regenerator after any registry/data change.",
        "-- Dedup on real natural keys; geometry/keyless tables promoted as-is.",
        "",
        "CREATE SCHEMA IF NOT EXISTS staging;",
        "",
    ]
    generated = 0
    for name in names:
        try:
            cols = [c[0] for c in con.execute(
                f'SELECT * FROM nyc_dot_analytics.raw."{name}" LIMIT 0').description]
        except Exception:
            lines.append(f'-- {name}: not present in raw schema yet -> skipped')
            lines.append("")
            continue
        has_geom = "the_geom" in cols
        key = _pick_key(cols)
        if key and not has_geom:
            lines.append(f'CREATE OR REPLACE TABLE staging."{name}" AS')
            lines.append(f'SELECT * FROM raw."{name}"')
            lines.append(f'QUALIFY ROW_NUMBER() OVER (PARTITION BY "{key}" ORDER BY 1 DESC) = 1;')
        else:
            reason = "geometry table" if has_geom else "no natural key"
            lines.append(f'-- {name}: {reason} -> promote as-is')
            lines.append(f'CREATE OR REPLACE TABLE staging."{name}" AS SELECT * FROM raw."{name}";')
        lines.append("")
        generated += 1
    STAGING_SQL.write_text("\n".join(lines))
    return generated


# --- 3. Regenerate data catalog ---------------------------------------------
def generate_data_catalog(config, registry):
    rows = config.get("socrata_remaining", [])
    out = [
        "# NYC DOT SIM — Data Catalog",
        "",
        "> AUTO-GENERATED from the authoritative registry by "
        "`pipeline/regenerate_from_registry.py`. Do not edit by hand.",
        "",
        f"**Datasets:** {len(rows)}  |  **Source of truth:** Local Law 251 registry "
        "(`pipeline/data/nyc_open_data_registry.json`)",
        "",
        "| Table | Socrata ID | LL251 Name | Last Updated | Cols | Domain |",
        "|---|---|---|---|---|---|",
    ]
    for d in sorted(rows, key=lambda x: x["name"]):
        reg = registry.get(d["socrata_id"], {})
        out.append(
            f"| `{d['name']}` | {d['socrata_id']} | {reg.get('name','?')[:48]} | "
            f"{(reg.get('last_updated') or '')[:10]} | {len(reg.get('columns',[]))} | "
            f"{d.get('domain_schema','')} |"
        )
    CATALOG_MD.write_text("\n".join(out) + "\n")
    return len(rows)


def main():
    print("=" * 72)
    print("REGENERATE FROM REGISTRY — propagating source-of-truth changes")
    print("=" * 72)
    registry = load_registry()
    config = load_config()
    print(f"Registry datasets: {len(registry)}  |  Configured: {len(config.get('socrata_remaining', []))}")

    refreshed, missing = refresh_config_metadata(config, registry)
    print(f"[config]   refreshed metadata for {refreshed} datasets")
    if missing:
        print(f"[config]   WARNING: {len(missing)} configured IDs not in registry:")
        for nm, sid in missing:
            print(f"             - {nm} ({sid})")

    catalog_n = generate_data_catalog(config, registry)
    print(f"[catalog]  wrote {CATALOG_MD.name} ({catalog_n} datasets)")

    # Staging SQL needs live DB; best-effort.
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        import duckdb
        tok = None if os.getenv("NYC_FORCE_LOCAL") == "1" else os.getenv("MOTHERDUCK_TOKEN", "")
        if tok:
            con = duckdb.connect(f"md:nyc_dot_analytics?token={tok}")
        else:
            local = ROOT / "nyc_dot_analytics.duckdb"
            if not local.exists():
                raise RuntimeError("no DB (MOTHERDUCK_TOKEN unset and no local file)")
            con = duckdb.connect(str(local))
        n = generate_staging_sql(con, config)
        con.close()
        print(f"[staging]  regenerated {STAGING_SQL.name} from live columns ({n} tables)")
    except Exception as e:
        print(f"[staging]  SKIPPED (no DB): {e}")

    print("Regeneration complete. Derived files reflect the current registry.")


if __name__ == "__main__":
    main()
