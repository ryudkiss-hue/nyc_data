#!/usr/bin/env python3
"""Daily cache refresh for NYC DOT Socrata datasets.

Pipeline (runs sequentially, errors are isolated per dataset):
  1. Incremental fetch — records updated in last 24h via :updated_at
  2. NLP triage     — keyword-based priority labelling for text-rich datasets
  3. DuckDB upsert  — merge incremental rows into raw schema, stage core tables
  4. MD archive     — copy raw records older than 30d into MotherDuck
  5. Analytics views — refresh all materialized marts
  6. Health report  — size, row counts, freshness, quality scores

Usage:
  PYTHONPATH=src:. python scripts/daily_refresh.py
  PYTHONPATH=src:. python scripts/daily_refresh.py --full-reload
  PYTHONPATH=src:. python scripts/daily_refresh.py --datasets inspection violations
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import duckdb
import pandas as pd

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.core.duckdb_analytics_models import refresh_all_analytics_views
from socrata_toolkit.core.duckdb_pipeline import (
    _INSPECTION_DATE_CANDIDATES,
    _INSPECTION_KEY_CANDIDATES,
    _PERMIT_DATE_CANDIDATES,
    _PERMIT_KEY_CANDIDATES,
    _RAMP_DATE_CANDIDATES,
    _RAMP_KEY_CANDIDATES,
    SOCRATA_DATASETS,
    _stage_table,
    get_duckdb_connection,
    initialize_database,
    load_raw_from_socrata,
    stage_inspections,
    stage_permits,
    stage_ramps,
)
from socrata_toolkit.governance.core import compute_quality_score
from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.nlp.integration import triage_complaints


def _load_dataset_config_keys() -> list[str]:
    """Return the 24 active dataset keys from data/dataset_config.json."""
    cfg = ROOT / "data" / "dataset_config.json"
    if cfg.exists():
        data = json.loads(cfg.read_text())
        return [k for k in data if k != "_template"]
    # Fallback: CLAUDE.md core 57 datasets minus known-broken ones
    return [
        "inspection", "violations", "built", "lot_info", "reinspection",
        "tree_damage", "dismissals", "correspondences", "curb_metal_protruding",
        "ramp_locations", "ramp_complaints", "ramp_progress",
        "street_permits", "capital_intersections", "street_construction_inspections",
        "street_closures_block", "street_resurfacing_schedule", "street_resurfacing_inhouse",
        "step_streets", "sidewalk_planimetric", "pedestrian_demand",
        "mappluto", "complaints_311",
    ]

# ── constants ─────────────────────────────────────────────────────────────────
DOMAIN = "data.cityofnewyork.us"
DB_PATH = os.getenv("DUCKDB_PATH", str(ROOT / "data/local_db/nyc_mission_control.duckdb"))

# Datasets skipped unconditionally: empty, inaccessible, or geo-only (no flat JSON rows)
SKIP_DATASETS = {"capital_blocks", "permit_stipulations", "sidewalk_planimetric"}

# Datasets known stale but still attempted (errors captured, not fatal)
WARN_STALE = {"ramp_locations", "weekly_construction"}

# Text column names to try for NLP triage (checked in order)
NLP_TEXT_COLUMNS = ["descriptor", "description", "complaint_type", "resolution_description"]

# Archive rows older than this many days to MotherDuck
ARCHIVE_AFTER_DAYS = 30

# Default date column for incremental window
DEFAULT_DATE_COL = ":updated_at"

# dataset_config.json uses "permits"; SOCRATA_DATASETS uses "street_permits"
CONFIG_KEY_ALIASES: dict[str, str] = {"permits": "street_permits"}

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("daily_refresh")


# ── helpers ───────────────────────────────────────────────────────────────────

def _since_iso() -> str:
    """ISO 8601 timestamp 24 hours ago."""
    from datetime import timedelta
    ts = datetime.now(timezone.utc) - timedelta(hours=24)
    return ts.strftime("%Y-%m-%dT%H:%M:%S")


def _table_row_count(conn: duckdb.DuckDBPyConnection, schema: str, name: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {schema}.{name}").fetchone()[0]
    except Exception:
        return 0


def _table_exists(conn: duckdb.DuckDBPyConnection, schema: str, name: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?",
        [schema, name],
    ).fetchone()
    return bool(row and row[0])


def _find_text_column(df: pd.DataFrame) -> str | None:
    for col in NLP_TEXT_COLUMNS:
        if col in df.columns:
            return col
    return None


def _aligned_col_list(
    conn: duckdb.DuckDBPyConnection,
    schema: str,
    table: str,
    df: pd.DataFrame,
) -> str:
    """Return a quoted comma-separated list of columns present in both the table and df."""
    existing = {r[0] for r in conn.execute(f"DESCRIBE {schema}.{table}").fetchall()}
    shared = [c for c in df.columns if c in existing]
    if not shared:
        shared = list(df.columns)
    return ", ".join(f'"{c}"' for c in shared)


def _upsert_incremental(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    df: pd.DataFrame,
    key_col: str | None,
) -> int:
    """Insert or replace rows in raw.<table> using DuckDB."""
    if df.empty:
        return 0
    conn.register("_inc_df", df)
    try:
        if not _table_exists(conn, "raw", table):
            conn.execute(f"CREATE TABLE raw.{table} AS SELECT * FROM _inc_df")
            inserted = len(df)
        elif key_col and key_col in df.columns:
            conn.execute(
                f"DELETE FROM raw.{table} WHERE \"{key_col}\" IN "
                f"(SELECT \"{key_col}\" FROM _inc_df)"
            )
            cols = _aligned_col_list(conn, "raw", table, df)
            conn.execute(f"INSERT INTO raw.{table} ({cols}) SELECT {cols} FROM _inc_df")
            inserted = len(df)
        else:
            cols = _aligned_col_list(conn, "raw", table, df)
            conn.execute(f"INSERT INTO raw.{table} ({cols}) SELECT {cols} FROM _inc_df")
            inserted = len(df)
    finally:
        conn.unregister("_inc_df")
    return inserted


# ── pipeline steps ────────────────────────────────────────────────────────────

def step_fetch_incremental(
    dataset_keys: list[str],
    full_reload: bool,
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, dict]:
    """Step 1: Fetch incremental (or full) data from Socrata into raw schema."""
    client = SocrataClient(SocrataConfig())
    since = _since_iso()
    results: dict[str, dict] = {}

    for key in dataset_keys:
        if key in SKIP_DATASETS:
            results[key] = {"status": "skipped", "reason": "known-broken dataset"}
            continue

        socrata_key = CONFIG_KEY_ALIASES.get(key, key)
        fourfour = SOCRATA_DATASETS.get(socrata_key)
        if not fourfour:
            results[key] = {"status": "skipped", "reason": "not in SOCRATA_DATASETS"}
            continue

        if key in WARN_STALE:
            log.warning("[%s] dataset is known stale — attempting anyway", key)

        t0 = time.monotonic()
        try:
            raw_table = socrata_key  # raw schema uses SOCRATA_DATASETS key
            # Cap initial full-reload to 100K rows to avoid hanging on huge datasets
            # (street_permits=3.6M, complaints_311=21M). Use --full-reload for uncapped load.
            FULL_RELOAD_CAP = None if full_reload else 100_000
            if full_reload or not _table_exists(conn, "raw", raw_table):
                log.info("[%s] full reload (fourfour=%s, cap=%s)", key, fourfour, FULL_RELOAD_CAP)
                result = load_raw_from_socrata(socrata_key, max_rows=FULL_RELOAD_CAP)
                if result.get("status") == "error":
                    raise RuntimeError(result.get("error", "unknown error"))
                row_count = result.get("row_count", 0)
                mode = "full"
            else:
                log.info("[%s] incremental since %s", key, since)
                pages = list(client.fetch_since(
                    DOMAIN, fourfour,
                    updated_col=DEFAULT_DATE_COL,
                    since=since,
                    max_rows=50_000,
                ))
                if pages:
                    df = pd.DataFrame([row for page in pages for row in page])
                    key_col = next(
                        (c for c in ["objectid", "id", "permit_number", "ramp_id"] if c in df.columns),
                        None,
                    )
                    row_count = _upsert_incremental(conn, raw_table, df, key_col)
                else:
                    row_count = 0
                mode = "incremental"

            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {
                "status": "success",
                "mode": mode,
                "rows_fetched": row_count,
                "elapsed_s": elapsed,
            }
            log.info("[%s] %s — %d rows in %.1fs", key, mode, row_count, elapsed)

        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {"status": "error", "error": str(exc), "elapsed_s": elapsed}
            log.error("[%s] fetch failed: %s", key, exc)

    return results


def step_nlp_triage(
    dataset_keys: list[str],
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, dict]:
    """Step 2: Keyword-based NLP triage on text-rich raw tables."""
    NLP_TARGETS = {"complaints_311", "tree_damage", "dismissals", "curb_metal_protruding"}
    results: dict[str, dict] = {}

    for key in dataset_keys:
        if key not in NLP_TARGETS:
            continue
        if not _table_exists(conn, "raw", key):
            results[key] = {"status": "skipped", "reason": "raw table missing"}
            continue

        t0 = time.monotonic()
        try:
            df = conn.execute(f"SELECT * FROM raw.{key} LIMIT 10000").df()
            text_col = _find_text_column(df)
            if text_col is None:
                results[key] = {"status": "skipped", "reason": "no text column found"}
                continue

            df_triaged = triage_complaints(df, text_col=text_col)
            priority_counts = df_triaged["_triage_priority"].value_counts().to_dict()

            conn.register("_triaged_df", df_triaged)
            try:
                conn.execute(f"DROP TABLE IF EXISTS raw.{key}_triaged")
                conn.execute(f"CREATE TABLE raw.{key}_triaged AS SELECT * FROM _triaged_df")
            finally:
                conn.unregister("_triaged_df")

            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {
                "status": "success",
                "rows": len(df_triaged),
                "priorities": priority_counts,
                "elapsed_s": elapsed,
            }
            log.info("[%s] NLP triage: %s in %.1fs", key, priority_counts, elapsed)

        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {"status": "error", "error": str(exc), "elapsed_s": elapsed}
            log.error("[%s] NLP triage failed: %s", key, exc)

    return results


def step_stage_upsert(conn: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """Step 3: Deduplicate and stage core tables (inspections, permits, ramps)."""
    results: dict[str, dict] = {}
    stages = {
        "inspections": (stage_inspections, "raw.inspection"),
        "permits": (stage_permits, "raw.street_permits"),
        "ramps": (stage_ramps, "raw.ramp_progress"),
    }

    for name, (fn, raw_table) in stages.items():
        schema, tbl = raw_table.split(".")
        if not _table_exists(conn, schema, tbl):
            results[name] = {"status": "skipped", "reason": f"{raw_table} not loaded"}
            continue
        t0 = time.monotonic()
        try:
            result = fn()
            elapsed = round(time.monotonic() - t0, 1)
            results[name] = {**result, "elapsed_s": elapsed}
            if result.get("status") == "success":
                log.info("[staging.%s] %d rows in %.1fs", name, result.get("row_count_staged", 0), elapsed)
        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 1)
            results[name] = {"status": "error", "error": str(exc), "elapsed_s": elapsed}
            log.error("[staging.%s] failed: %s", name, exc)

    # Generic staging for remaining datasets that have raw tables
    GENERIC_STAGE_TARGETS = [
        ("violations", ["objectid", "id"], [":updated_at", "created_date"]),
        ("built", ["objectid", "id"], [":updated_at", "created_date"]),
        ("reinspection", ["objectid", "id"], [":updated_at", "created_date"]),
        ("dismissals", ["objectid", "id"], [":updated_at", "created_date"]),
    ]
    for key, key_cands, date_cands in GENERIC_STAGE_TARGETS:
        if not _table_exists(conn, "raw", key):
            continue
        t0 = time.monotonic()
        try:
            result = _stage_table(f"raw.{key}", f"staging.{key}", key_cands, date_cands, conn)
            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {**result, "elapsed_s": elapsed}
            if result.get("status") == "success":
                log.info("[staging.%s] %d rows in %.1fs", key, result.get("row_count_staged", 0), elapsed)
        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 1)
            results[key] = {"status": "error", "error": str(exc), "elapsed_s": elapsed}
            log.error("[staging.%s] failed: %s", key, exc)

    return results


def step_archive_to_motherduck(conn: duckdb.DuckDBPyConnection) -> dict:
    """Step 4: Archive raw records older than ARCHIVE_AFTER_DAYS to MotherDuck."""
    md_token = os.getenv("MOTHERDUCK_TOKEN")
    if not md_token:
        return {"status": "skipped", "reason": "MOTHERDUCK_TOKEN not set"}

    t0 = time.monotonic()
    archived_total = 0
    errors: list[str] = []

    md = MotherDuckConnection(token=md_token)
    if not md.is_motherduck:
        return {"status": "skipped", "reason": "MotherDuck connection unavailable (falling back to local)"}

    cutoff = datetime.now(timezone.utc).replace(microsecond=0)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    ARCHIVE_TARGETS = [
        ("inspection", ":updated_at"),
        ("violations", ":updated_at"),
        ("street_permits", ":updated_at"),
        ("dismissals", ":updated_at"),
        ("ramp_progress", ":updated_at"),
    ]

    for key, date_col in ARCHIVE_TARGETS:
        if not _table_exists(conn, "raw", key):
            continue
        try:
            # Check column exists
            cols = {r[0] for r in conn.execute(f"DESCRIBE raw.{key}").fetchall()}
            if date_col not in cols and ":updated_at" not in cols:
                continue
            col = date_col if date_col in cols else ":updated_at"

            df_old = conn.execute(
                f"SELECT * FROM raw.{key} "
                f"WHERE \"{col}\" < '{cutoff_str}'::TIMESTAMP - INTERVAL '{ARCHIVE_AFTER_DAYS} days'"
            ).df()

            if df_old.empty:
                continue

            # Upsert into MotherDuck archive schema
            archive_table = f"raw_archive.{key}"
            md.create_schema("raw_archive")
            md.execute(f"CREATE TABLE IF NOT EXISTS {archive_table} AS SELECT * FROM df_old LIMIT 0")
            md.execute(f"INSERT INTO {archive_table} SELECT * FROM df_old")
            archived_total += len(df_old)
            log.info("[archive] %s → MotherDuck %s: %d rows", key, archive_table, len(df_old))
        except Exception as exc:
            errors.append(f"{key}: {exc}")
            log.warning("[archive] %s failed: %s", key, exc)

    elapsed = round(time.monotonic() - t0, 1)
    return {
        "status": "success" if not errors else "partial",
        "archived_rows": archived_total,
        "errors": errors,
        "elapsed_s": elapsed,
    }


def step_refresh_analytics(conn: duckdb.DuckDBPyConnection) -> dict:
    """Step 5: Rebuild all analytics materialized views."""
    t0 = time.monotonic()
    try:
        results = refresh_all_analytics_views(conn)
        elapsed = round(time.monotonic() - t0, 1)
        success = sum(1 for r in results.values() if r.get("status") == "success")
        log.info("Analytics: %d/%d marts refreshed in %.1fs", success, len(results), elapsed)
        return {"status": "success", "marts": results, "elapsed_s": elapsed}
    except Exception as exc:
        elapsed = round(time.monotonic() - t0, 1)
        log.error("Analytics refresh failed: %s", exc)
        return {"status": "error", "error": str(exc), "elapsed_s": elapsed}


def step_cache_health(
    dataset_keys: list[str],
    conn: duckdb.DuckDBPyConnection,
) -> dict:
    """Step 6: Report DuckDB cache size, row counts, and quality snapshot."""
    db_size_mb = 0.0
    db_file = Path(DB_PATH)
    if db_file.exists():
        db_size_mb = round(db_file.stat().st_size / 1_048_576, 2)

    sla_cfg_path = ROOT / "data" / "sla_config.json"
    sla_thresholds = {"HIGH": 14, "MEDIUM": 30, "LOW": 60}
    if sla_cfg_path.exists():
        sla_raw = json.loads(sla_cfg_path.read_text())
        for tier, val in sla_raw.get("sla_thresholds", {}).items():
            sla_thresholds[tier] = val.get("days", sla_thresholds.get(tier))

    table_health: dict[str, dict] = {}
    quality_samples: dict[str, float] = {}

    QUALITY_TARGETS = ["inspection", "violations", "street_permits", "ramp_progress"]

    for key in dataset_keys:
        if not _table_exists(conn, "raw", key):
            continue
        row_count = _table_row_count(conn, "raw", key)
        table_health[key] = {"raw_rows": row_count}

        if _table_exists(conn, "staging", key):
            table_health[key]["staged_rows"] = _table_row_count(conn, "staging", key)

        # Quick quality sample for core datasets
        if key in QUALITY_TARGETS and row_count > 0:
            try:
                sample = conn.execute(f"SELECT * FROM raw.{key} USING SAMPLE 500").df()
                score = compute_quality_score(
                    sample,
                    key_columns=["objectid"],
                    date_column=next((c for c in [":updated_at", "created_date"] if c in sample.columns), None),
                )
                quality_samples[key] = round(score.overall, 1)
                table_health[key]["quality_score"] = quality_samples[key]
            except Exception:
                pass

    return {
        "db_size_mb": db_size_mb,
        "db_path": str(DB_PATH),
        "tables": table_health,
        "quality_samples": quality_samples,
        "sla_thresholds_days": sla_thresholds,
    }


# ── report ────────────────────────────────────────────────────────────────────

def _print_report(report: dict) -> None:
    sep = "─" * 68

    print(f"\n{'═'*68}")
    print(" NYC DOT Daily Cache Refresh — Report")
    print(f" Run at: {report['run_at']}")
    print(f"{'═'*68}")

    # Fetch summary
    fetch = report.get("fetch", {})
    ok  = [k for k, v in fetch.items() if v.get("status") == "success"]
    err = [k for k, v in fetch.items() if v.get("status") == "error"]
    skp = [k for k, v in fetch.items() if v.get("status") == "skipped"]
    total_rows = sum(v.get("rows_fetched", 0) for v in fetch.values())
    print(f"\n{'Step 1: Fetch':─<68}")
    print(f"  {'success':8s}: {len(ok)} datasets  ({total_rows:,} rows total)")
    print(f"  {'error':8s}: {len(err)} datasets  {err or ''}")
    print(f"  {'skipped':8s}: {len(skp)} datasets")
    for k, v in sorted(fetch.items()):
        if v.get("status") == "success":
            print(f"    ✓ {k:<35} {v.get('rows_fetched',0):>7,} rows  [{v.get('mode','')}]")
    if err:
        print("\n  ERRORS:")
        for k in err:
            print(f"    ✗ {k}: {fetch[k].get('error','')}")

    # NLP
    nlp = report.get("nlp", {})
    print(f"\n{'Step 2: NLP Triage':─<68}")
    for k, v in sorted(nlp.items()):
        if v.get("status") == "success":
            prio = v.get("priorities", {})
            print(f"  ✓ {k}: {v.get('rows',0):,} rows → {prio}")
        else:
            print(f"  - {k}: {v.get('status')} ({v.get('reason',v.get('error',''))})")

    # Staging
    staging = report.get("staging", {})
    print(f"\n{'Step 3: Staging':─<68}")
    for k, v in sorted(staging.items()):
        if v.get("status") == "success":
            print(f"  ✓ {k:<18} raw={v.get('row_count_raw',0):>7,}  staged={v.get('row_count_staged',0):>7,}  dedup={v.get('dedup_loss_pct',0):.1f}%")
        else:
            print(f"  - {k}: {v.get('status')} ({v.get('error',v.get('reason',''))})")

    # Archive
    archive = report.get("archive", {})
    print(f"\n{'Step 4: MotherDuck Archive':─<68}")
    st = archive.get("status", "?")
    print(f"  status: {st}  |  rows archived: {archive.get('archived_rows', 0):,}")
    if archive.get("reason"):
        print(f"  note: {archive['reason']}")
    if archive.get("errors"):
        for e in archive["errors"]:
            print(f"  ✗ {e}")

    # Analytics
    analytics = report.get("analytics", {})
    print(f"\n{'Step 5: Analytics Views':─<68}")
    marts = analytics.get("marts", {})
    for m, v in sorted(marts.items()):
        mark = "✓" if v.get("status") == "success" else "✗"
        print(f"  {mark} {m:<40} {v.get('row_count',0):>7,} rows")
    if analytics.get("status") == "error":
        print(f"  ERROR: {analytics.get('error','')}")

    # Cache health
    health = report.get("health", {})
    print(f"\n{'Step 6: Cache Health':─<68}")
    print(f"  DuckDB: {health.get('db_path','?')}  ({health.get('db_size_mb',0):.1f} MB)")
    tables = health.get("tables", {})
    if tables:
        print(f"  {'Dataset':<35} {'Raw':>8}  {'Staged':>8}  {'Quality':>8}")
        print(f"  {'─'*35} {'─'*8}  {'─'*8}  {'─'*8}")
        for k, t in sorted(tables.items()):
            q = f"{t.get('quality_score','—'):>6}" if 'quality_score' in t else "      —"
            print(f"  {k:<35} {t.get('raw_rows',0):>8,}  {t.get('staged_rows',''):>8}  {q}")

    print(f"\n{'═'*68}")
    elapsed = report.get("total_elapsed_s", 0)
    status = "SUCCESS" if not err else f"PARTIAL ({len(err)} fetch errors)"
    print(f" Total: {elapsed:.1f}s  |  Status: {status}")
    print(f"{'═'*68}\n")


# ── entrypoint ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily Socrata cache refresh")
    parser.add_argument("--full-reload", action="store_true",
                        help="Drop and reload all tables (ignore incremental window)")
    parser.add_argument("--datasets", nargs="*",
                        help="Limit to specific dataset keys (default: all active)")
    parser.add_argument("--skip-archive", action="store_true",
                        help="Skip MotherDuck archive step")
    parser.add_argument("--skip-analytics", action="store_true",
                        help="Skip analytics view refresh")
    parser.add_argument("--json-out", metavar="FILE",
                        help="Write full report JSON to FILE")
    args = parser.parse_args(argv)

    t_start = time.monotonic()
    run_at = datetime.now(timezone.utc).isoformat()

    # Dataset list — default to dataset_config.json (24 active datasets)
    config_keys = _load_dataset_config_keys()
    all_keys = [k for k in config_keys if k not in SKIP_DATASETS]
    dataset_keys = args.datasets if args.datasets else all_keys
    log.info("Refreshing %d datasets (full_reload=%s)", len(dataset_keys), args.full_reload)

    # Init DuckDB
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_duckdb_connection(DB_PATH)
    initialize_database()

    report: dict = {"run_at": run_at, "db_path": DB_PATH}

    # Step 1: Fetch
    log.info("── Step 1/6: Incremental fetch ──────────────────────────────────")
    report["fetch"] = step_fetch_incremental(dataset_keys, args.full_reload, conn)

    # Step 2: NLP
    log.info("── Step 2/6: NLP triage ─────────────────────────────────────────")
    report["nlp"] = step_nlp_triage(dataset_keys, conn)

    # Step 3: Staging
    log.info("── Step 3/6: Staging / upsert ───────────────────────────────────")
    report["staging"] = step_stage_upsert(conn)

    # Step 4: Archive
    log.info("── Step 4/6: MotherDuck archive ─────────────────────────────────")
    if args.skip_archive:
        report["archive"] = {"status": "skipped", "reason": "--skip-archive flag"}
    else:
        report["archive"] = step_archive_to_motherduck(conn)

    # Step 5: Analytics views
    log.info("── Step 5/6: Analytics materialization ──────────────────────────")
    if args.skip_analytics:
        report["analytics"] = {"status": "skipped", "reason": "--skip-analytics flag"}
    else:
        report["analytics"] = step_refresh_analytics(conn)

    # Step 6: Health
    log.info("── Step 6/6: Cache health report ────────────────────────────────")
    report["health"] = step_cache_health(dataset_keys, conn)

    report["total_elapsed_s"] = round(time.monotonic() - t_start, 1)

    # Output
    _print_report(report)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, default=str))
        log.info("Report written to %s", args.json_out)

    fetch_errors = [k for k, v in report["fetch"].items() if v.get("status") == "error"]
    return 1 if fetch_errors else 0


if __name__ == "__main__":
    sys.exit(main())


