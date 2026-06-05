"""Dynamic analysis documentation with DuckDB-backed cache.

Generates structured markdown documentation for a Socrata dataset and caches
the result. On subsequent calls, returns the cached version unless the
underlying data has changed (content-hash strategy) or the TTL has elapsed.

Usage:
    python dynamic_doc_cache.py --key inspection
    python dynamic_doc_cache.py --key violations --invalidate
    python dynamic_doc_cache.py --list
    python dynamic_doc_cache.py --purge

Configuration: config/doc_cache_config.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import yaml

# Resolve project root (3 levels up from this script)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

CONFIG_PATH = PROJECT_ROOT / "config" / "doc_cache_config.yaml"
DATASETS_PATH = PROJECT_ROOT / "config" / "datasets.yaml"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f).get("doc_cache", {})


def _cache_db_path(cfg: dict) -> Path:
    p = Path(cfg.get("cache_path", "data/cache/doc_cache.duckdb"))
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Cache schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_cache (
    doc_id       TEXT PRIMARY KEY,
    dataset_key  TEXT NOT NULL,
    input_hash   TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    strategy     TEXT NOT NULL,
    content      TEXT NOT NULL,
    row_count    BIGINT,
    quality_score REAL
);
"""


def _get_conn(db_path: Path) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(db_path))
    conn.execute(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Cache key / hash
# ---------------------------------------------------------------------------

def _input_hash(dataset_key: str, last_modified: str | None, cfg: dict) -> str:
    """Stable hash over the inputs that would affect doc content."""
    payload = json.dumps({
        "key": dataset_key,
        "last_modified": last_modified,
        "include_quality": cfg.get("content", {}).get("include_quality_score", True),
        "include_schema": cfg.get("content", {}).get("include_schema", True),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cache read/write
# ---------------------------------------------------------------------------

def _cache_get(conn: duckdb.DuckDBPyConnection, doc_id: str, strategy: str,
               input_hash: str) -> str | None:
    """Return cached content if still valid, else None."""
    row = conn.execute(
        "SELECT content, expires_at, input_hash FROM doc_cache WHERE doc_id = ?",
        [doc_id],
    ).fetchone()
    if row is None:
        return None

    content, expires_at, cached_hash = row
    now = datetime.now(timezone.utc)

    # TTL check
    if strategy in ("ttl", "both"):
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return None

    # Content-hash check
    if strategy in ("content_hash", "both"):
        if cached_hash != input_hash:
            return None

    return content


def _cache_put(conn: duckdb.DuckDBPyConnection, doc_id: str, dataset_key: str,
               input_hash: str, content: str, ttl_hours: int, strategy: str,
               row_count: int | None, quality_score: float | None) -> None:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)
    conn.execute(
        """INSERT OR REPLACE INTO doc_cache
           (doc_id, dataset_key, input_hash, generated_at, expires_at, strategy,
            content, row_count, quality_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [doc_id, dataset_key, input_hash, now.isoformat(), expires_at.isoformat(),
         strategy, content, row_count, quality_score],
    )


def _cache_evict_lru(conn: duckdb.DuckDBPyConnection, max_entries: int) -> None:
    count = conn.execute("SELECT COUNT(*) FROM doc_cache").fetchone()[0]
    if count > max_entries:
        excess = count - max_entries
        conn.execute(
            """DELETE FROM doc_cache WHERE doc_id IN (
               SELECT doc_id FROM doc_cache ORDER BY generated_at ASC LIMIT ?)""",
            [excess],
        )


# ---------------------------------------------------------------------------
# Doc generation
# ---------------------------------------------------------------------------

def _fetch_last_modified(domain: str, fourfour: str) -> str | None:
    try:
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig
        client = SocrataClient(SocrataConfig())
        meta = client.get_metadata(domain, fourfour)
        return getattr(meta, "last_modified", None) or getattr(meta, "updated_at", None)
    except Exception:
        return None


def _generate_doc(dataset_key: str, cfg: dict) -> tuple[str, int | None, float | None]:
    """Produce the markdown documentation string for a dataset."""
    content_cfg = cfg.get("content", {})

    # Load dataset registry
    datasets: dict = {}
    if DATASETS_PATH.exists():
        with DATASETS_PATH.open() as f:
            raw = yaml.safe_load(f) or {}
        for section in raw.values():
            if isinstance(section, dict):
                datasets.update(section)

    ds = datasets.get(dataset_key, {})
    fourfour = ds.get("fourfour", "unknown")
    domain = ds.get("domain", "data.cityofnewyork.us")
    description = ds.get("description", "No description available.")

    lines = [
        f"# Dataset Documentation: `{dataset_key}`",
        f"",
        f"**Fourfour:** `{fourfour}`  ",
        f"**Domain:** {domain}  ",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"## Description",
        f"",
        description,
        f"",
    ]

    row_count: int | None = None
    quality_score: float | None = None

    try:
        from socrata_toolkit.core.client import SocrataClient, SocrataConfig
        client = SocrataClient(SocrataConfig())
        meta = client.get_metadata(domain, fourfour)

        if content_cfg.get("include_freshness", True):
            lm = getattr(meta, "last_modified", None)
            lines += ["## Freshness", "", f"**Last modified:** {lm or 'unknown'}", ""]

        if content_cfg.get("include_row_count", True):
            row_count = getattr(meta, "row_count", None)
            lines += ["## Row Count", "", f"**Rows:** {row_count:,}" if row_count else "**Rows:** unknown", ""]

        if content_cfg.get("include_schema", True):
            cols = meta.column_dict() if hasattr(meta, "column_dict") else []
            if cols:
                lines += ["## Schema", "", "| Field | Type | Description |", "|---|---|---|"]
                for col in cols[:30]:
                    lines.append(
                        f"| `{col.get('fieldName','')}` | {col.get('dataTypeName','')} | "
                        f"{col.get('description','')[:80]} |"
                    )
                lines.append("")

        if content_cfg.get("include_quality_score", True):
            max_rows = content_cfg.get("max_sample_rows", 5)
            df = client.fetch_dataframe(domain, fourfour, max_rows=max(max_rows, 100))
            if not df.empty:
                from socrata_toolkit.governance import compute_quality_score
                qs = compute_quality_score(df)
                quality_score = qs.overall
                lines += [
                    "## Quality Score",
                    "",
                    f"| Dimension | Score |",
                    f"|---|---|",
                    f"| **Overall** | {qs.overall:.1f} |",
                    f"| Completeness | {qs.completeness:.1f} |",
                    f"| Validity | {qs.validity:.1f} |",
                    f"| Consistency | {qs.consistency:.1f} |",
                    f"| Freshness | {qs.freshness:.1f} |",
                    "",
                ]

        if content_cfg.get("include_sample_queries", True):
            lines += [
                "## Sample Queries",
                "",
                f"```python",
                f"from socrata_toolkit.core.client import SocrataClient, SocrataConfig",
                f"client = SocrataClient(SocrataConfig())",
                f'df = client.fetch_dataframe("{domain}", "{fourfour}", max_rows=1000)',
                f"```",
                "",
            ]

    except Exception as exc:
        lines += ["## ⚠️ Live Data Unavailable", "", f"Could not fetch live metadata: {exc}", ""]

    return "\n".join(lines), row_count, quality_score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_generate(dataset_key: str, invalidate: bool = False) -> str:
    """Return cached doc or generate + cache a fresh one."""
    cfg = _load_config()
    if not cfg.get("enabled", True):
        doc, _, _ = _generate_doc(dataset_key, cfg)
        return doc

    strategy = cfg.get("invalidation_strategy", "both")
    ttl_hours = int(cfg.get("ttl_hours", 24))
    max_entries = int(cfg.get("max_entries", 200))
    db_path = _cache_db_path(cfg)
    doc_id = f"doc:{dataset_key}"

    datasets: dict = {}
    if DATASETS_PATH.exists():
        with DATASETS_PATH.open() as f:
            raw = yaml.safe_load(f) or {}
        for section in raw.values():
            if isinstance(section, dict):
                datasets.update(section)

    ds = datasets.get(dataset_key, {})
    domain = ds.get("domain", "data.cityofnewyork.us")
    fourfour = ds.get("fourfour", "")

    last_modified = None
    if strategy in ("content_hash", "both") and fourfour:
        last_modified = _fetch_last_modified(domain, fourfour)

    input_hash = _input_hash(dataset_key, last_modified, cfg)

    conn = _get_conn(db_path)

    if not invalidate:
        cached = _cache_get(conn, doc_id, strategy, input_hash)
        if cached is not None:
            if cfg.get("audit_log"):
                _audit("cache_hit", dataset_key)
            conn.close()
            return cached

    if cfg.get("audit_log"):
        _audit("cache_miss", dataset_key)

    doc, row_count, quality_score = _generate_doc(dataset_key, cfg)
    _cache_put(conn, doc_id, dataset_key, input_hash, doc,
               ttl_hours, strategy, row_count, quality_score)
    _cache_evict_lru(conn, max_entries)
    conn.close()
    return doc


def list_cached() -> list[dict]:
    cfg = _load_config()
    db_path = _cache_db_path(cfg)
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT dataset_key, generated_at, expires_at, row_count, quality_score "
        "FROM doc_cache ORDER BY generated_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"key": r[0], "generated_at": r[1], "expires_at": r[2],
         "row_count": r[3], "quality_score": r[4]}
        for r in rows
    ]


def purge_cache() -> int:
    cfg = _load_config()
    db_path = _cache_db_path(cfg)
    conn = _get_conn(db_path)
    count = conn.execute("SELECT COUNT(*) FROM doc_cache").fetchone()[0]
    conn.execute("DELETE FROM doc_cache")
    conn.close()
    return count


def _audit(action: str, dataset_key: str) -> None:
    try:
        from socrata_toolkit.governance import AuditLogger
        AuditLogger().log_event(
            actor="analysis-documentation",
            action=action,
            resource=dataset_key,
            details={},
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dynamic analysis documentation cache")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", help="Dataset key to document (e.g. inspection)")
    group.add_argument("--list", action="store_true", help="List all cached docs")
    group.add_argument("--purge", action="store_true", help="Clear the entire cache")
    parser.add_argument("--invalidate", action="store_true",
                        help="Force regeneration even if cache is fresh")
    args = parser.parse_args()

    if args.list:
        entries = list_cached()
        if not entries:
            print("Cache is empty.")
            return
        print(f"{'Key':<25} {'Generated':<22} {'Expires':<22} {'Rows':>10} {'Quality':>8}")
        print("-" * 90)
        for e in entries:
            print(f"{e['key']:<25} {str(e['generated_at'])[:19]:<22} "
                  f"{str(e['expires_at'])[:19]:<22} "
                  f"{str(e['row_count'] or '?'):>10} "
                  f"{f\"{e['quality_score']:.1f}\" if e['quality_score'] else '?':>8}")
        return

    if args.purge:
        n = purge_cache()
        print(f"Purged {n} cached document(s).")
        return

    doc = get_or_generate(args.key, invalidate=args.invalidate)
    print(doc)


if __name__ == "__main__":
    main()
