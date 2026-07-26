#!/usr/bin/env python3
"""Audit live NYC Open Data against the local registries.

For every dataset in pipeline/config/socrata_datasets.json, checks against the
live Socrata API:
  - accessibility (HTTP status on /api/views)
  - freshness (days since rowsUpdatedAt)
  - row-count drift (live SoQL count vs registry_row_count)
  - schema drift (live field names vs pipeline/data/nyc_open_data_registry.json baseline)

Also classifies every configured dataset by program scope (core SIM / DOT-adjacent /
context) against the Sidewalk Program analyst duties, and scans the full registry
for in-scope DOT/sidewalk datasets not yet configured.

Usage:
    python scripts/audit_registry_drift.py [--out pipeline/logs/registry_drift_report.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "pipeline" / "config" / "socrata_datasets.json"
REGISTRY_PATH = ROOT / "pipeline" / "data" / "nyc_open_data_registry.json"
DOMAIN = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")

# Scope model for the Sidewalk Program Project Analyst role:
# core = directly serves a stated duty (sidewalk repairs, ramps, construction
# lists, GIS conflicts, contract budget/progress, program metrics).
_CORE_TERMS = re.compile(
    r"sidewalk|ramp|curb|pedestrian|inspection|violation|dismissal|reinspection"
    r"|resurfacing|capital|permit|street.?construction|protruding|tree.?damage",
    re.IGNORECASE,
)
# adjacent = DOT operational data an analyst joins against for planning.
_ADJACENT_TERMS = re.compile(
    r"street|traffic|crash|closure|centerline|planimetric|311|complaint|step.?street",
    re.IGNORECASE,
)


def classify_scope(name: str, ll251: str, agency: str, schema: str) -> str:
    text = f"{name} {ll251} {schema}"
    if _CORE_TERMS.search(text):
        return "core"
    if _ADJACENT_TERMS.search(text) or "DOT" in (agency or ""):
        return "adjacent"
    return "context"


def _headers() -> dict:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    token = os.getenv("SOCRATA_APP_TOKEN")
    return {"X-App-Token": token} if token else {}


def audit_one(entry: dict, baseline_cols: set[str] | None, headers: dict) -> dict:
    fourfour = entry["socrata_id"]
    out: dict = {
        "key": entry.get("name"),
        "fourfour": fourfour,
        "scope": entry.get("_scope"),
        "status": "ok",
        "issues": [],
    }
    try:
        resp = requests.get(
            f"https://{DOMAIN}/api/views/{fourfour}.json", headers=headers, timeout=30
        )
    except Exception as e:
        out["status"] = "error"
        out["issues"].append(f"metadata request failed: {e}")
        return out
    if not resp.ok:
        out["status"] = "error"
        out["issues"].append(f"HTTP {resp.status_code} on /api/views")
        return out

    payload = resp.json()
    updated = payload.get("rowsUpdatedAt")
    if updated:
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(updated, tz=timezone.utc)).days
        out["days_since_update"] = age
        if age > 365:
            out["issues"].append(f"stale: {age} days since last update")

    live_cols = {c.get("fieldName") for c in payload.get("columns", []) if c.get("fieldName")}
    out["live_column_count"] = len(live_cols)
    if baseline_cols:
        added = sorted(c for c in live_cols - baseline_cols if not c.startswith(":@"))
        removed = sorted(baseline_cols - live_cols)
        if added:
            out["issues"].append(f"columns added: {added}")
        if removed:
            out["issues"].append(f"columns removed: {removed}")

    try:
        cresp = requests.get(
            f"https://{DOMAIN}/resource/{fourfour}.json",
            params={"$select": "count(*) as n"},
            headers=headers,
            timeout=30,
        )
        if cresp.ok:
            live_n = int(cresp.json()[0].get("n", 0))
            out["live_row_count"] = live_n
            base_n = int(entry.get("registry_row_count") or 0)
            if live_n == 0:
                out["issues"].append("live row count is 0")
            elif base_n and live_n < base_n * 0.5:
                out["issues"].append(f"row count dropped >50%: {base_n} -> {live_n}")
        else:
            out["issues"].append(f"HTTP {cresp.status_code} on SoQL count")
    except Exception as e:
        out["issues"].append(f"count query failed: {e}")

    if out["issues"]:
        out["status"] = "drift"
    return out


def find_candidates(registry: dict, configured_ids: set[str]) -> list[dict]:
    """In-scope, fresh, populated registry datasets not yet in the pipeline config."""
    candidates = []
    for fourfour, e in registry.get("datasets", {}).items():
        if fourfour in configured_ids:
            continue
        name = e.get("name", "")
        agency = e.get("agency", "")
        # In-scope for the Sidewalk Program: sidewalk-specific by name, or a DOT
        # dataset matching core program terms. Other agencies' inspection/violation
        # datasets (DOB, DSNY, HPD, ...) are out of scope for SIM.
        sidewalk_specific = re.search(r"sidewalk|pedestrian ramp|curb cut", name, re.IGNORECASE)
        is_dot = "(DOT)" in (agency or "") or "Transportation" in (agency or "")
        if not (sidewalk_specific or (is_dot and _CORE_TERMS.search(name))):
            continue
        candidates.append(
            {
                "fourfour": fourfour,
                "name": name,
                "agency": agency,
                "last_updated": e.get("last_updated"),
                "update_frequency": e.get("update_frequency"),
                "visits": e.get("visits", 0),
                "url": e.get("url"),
            }
        )
    candidates.sort(key=lambda c: (str(c.get("last_updated") or ""), c.get("visits") or 0), reverse=True)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "pipeline" / "logs" / "registry_drift_report.json"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    headers = _headers()

    entries = [e for e in config.get("socrata_remaining", []) if e.get("socrata_id")]
    reg_datasets = registry.get("datasets", {})
    for e in entries:
        reg = reg_datasets.get(e["socrata_id"], {})
        e["_scope"] = classify_scope(
            e.get("name", ""), e.get("ll251_name", ""), reg.get("agency", ""), e.get("domain_schema", "")
        )

    baselines = {
        f: {c.get("field_name") for c in e.get("columns", []) if c.get("field_name")}
        for f, e in reg_datasets.items()
        if e.get("columns")
    }

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(audit_one, e, baselines.get(e["socrata_id"]), headers): e for e in entries
        }
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda r: (r["status"] != "error", r["status"] != "drift", r["key"] or ""))

    candidates = find_candidates(registry, {e["socrata_id"] for e in entries})

    report = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "domain": DOMAIN,
        "dataset_count": len(results),
        "summary": {
            "ok": sum(1 for r in results if r["status"] == "ok"),
            "drift": sum(1 for r in results if r["status"] == "drift"),
            "error": sum(1 for r in results if r["status"] == "error"),
        },
        "scope_counts": {
            s: sum(1 for r in results if r["scope"] == s) for s in ("core", "adjacent", "context")
        },
        "results": results,
        "candidates_not_configured": candidates[:25],
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Audited {len(results)} datasets: {report['summary']}")
    print(f"Scope: {report['scope_counts']}")
    for r in results:
        if r["status"] != "ok":
            print(f"\n[{r['status'].upper()}] {r['key']} ({r['fourfour']}, scope={r['scope']})")
            for issue in r["issues"]:
                print(f"  - {issue}")
    print(f"\nTop unconfigured in-scope candidates: {len(candidates)} found (25 saved)")
    for c in candidates[:10]:
        print(f"  {c['fourfour']}  {c['name'][:60]}  [{c['agency'][:30]}] updated {str(c['last_updated'])[:10]}")
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
