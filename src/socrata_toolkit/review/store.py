from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import duckdb
import pandas as pd

from ..core.profiles import ProfilePaths, profile_paths

DecisionKind = Literal["conflict", "approval"]
ConflictStatus = Literal["resolved", "defer", "needs_coordination"]
ApprovalStatus = Literal["approved", "hold"]


@dataclass(frozen=True)
class ReviewDecision:
    pack_date: str
    kind: DecisionKind
    key_type: str
    key_value: str
    status: str
    assigned_to: str
    notes: str
    reason: str
    updated_at: str


class ReviewStore:
    """Lightweight local decisions store (DuckDB)."""

    def __init__(
        self,
        *,
        profile: str | None = None,
        db_path: str | None = None,
        root: Path | None = None,
        state_root: Path | None = None,
    ) -> None:
        # Avoid writing to repo in tests by allowing state_root override.
        self.profile_paths: ProfilePaths = profile_paths(profile, root=root, state_root=state_root)
        self.profile_paths.dir.mkdir(parents=True, exist_ok=True)
        self.profile_paths.publish_presets_dir.mkdir(parents=True, exist_ok=True)
        self.profile_paths.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else (self.profile_paths.state_dir / "decisions.duckdb")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.db_path))
        self._ensure_schema()

    def close(self) -> None:
        """Close the underlying DuckDB connection, suppressing errors."""
        try:
            self.con.close()
        except Exception:
            pass

    def __enter__(self) -> ReviewStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_schema(self) -> None:
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS review_decisions (
              pack_date TEXT NOT NULL,
              kind TEXT NOT NULL,                -- conflict|approval
              key_type TEXT NOT NULL,            -- location_id|contract_id|...
              key_value TEXT NOT NULL,
              status TEXT NOT NULL,
              assigned_to TEXT,
              notes TEXT,
              reason TEXT,
              meta_json TEXT,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (pack_date, kind, key_type, key_value)
            )
            """
        )
        self.con.execute(
            "CREATE INDEX IF NOT EXISTS idx_review_kind_status ON review_decisions(kind, status)"
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def set_conflict(
        self,
        *,
        pack_date: str,
        key_type: str,
        key_value: str,
        status: ConflictStatus,
        assigned_to: str = "",
        notes: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Record or update a conflict decision for the given key in the store."""
        self._upsert(
            pack_date=pack_date,
            kind="conflict",
            key_type=key_type,
            key_value=key_value,
            status=status,
            assigned_to=assigned_to,
            notes=notes,
            reason="",
            meta=meta or {},
        )

    def set_approval(
        self,
        *,
        pack_date: str,
        key_type: str,
        key_value: str,
        status: ApprovalStatus,
        reason: str = "",
        assigned_to: str = "",
        notes: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Record or update an approval decision for the given key in the store."""
        self._upsert(
            pack_date=pack_date,
            kind="approval",
            key_type=key_type,
            key_value=key_value,
            status=status,
            assigned_to=assigned_to,
            notes=notes,
            reason=reason,
            meta=meta or {},
        )

    def _upsert(
        self,
        *,
        pack_date: str,
        kind: DecisionKind,
        key_type: str,
        key_value: str,
        status: str,
        assigned_to: str,
        notes: str,
        reason: str,
        meta: dict[str, Any],
    ) -> None:
        updated_at = self._now_iso()
        self.con.execute(
            """
            INSERT INTO review_decisions
              (pack_date, kind, key_type, key_value, status, assigned_to, notes, reason, meta_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (pack_date, kind, key_type, key_value) DO UPDATE SET
              status=excluded.status,
              assigned_to=excluded.assigned_to,
              notes=excluded.notes,
              reason=excluded.reason,
              meta_json=excluded.meta_json,
              updated_at=excluded.updated_at
            """,
            [
                str(pack_date),
                str(kind),
                str(key_type),
                str(key_value),
                str(status),
                str(assigned_to or ""),
                str(notes or ""),
                str(reason or ""),
                json.dumps(meta or {}),
                updated_at,
            ],
        )

    def list(
        self,
        *,
        pack_date: str | None = None,
        kind: DecisionKind | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 2000,
    ) -> pd.DataFrame:
        """Query review decisions with optional filters and return a DataFrame."""
        clauses: list[str] = []
        params: list[Any] = []
        if pack_date:
            clauses.append("pack_date = ?")
            params.append(str(pack_date))
        if kind:
            clauses.append("kind = ?")
            params.append(str(kind))
        if status:
            clauses.append("status = ?")
            params.append(str(status))
        if q:
            clauses.append("(key_value ILIKE ? OR notes ILIKE ? OR assigned_to ILIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        df = self.con.execute(
            f"""
            SELECT pack_date, kind, key_type, key_value, status,
                   COALESCE(assigned_to,'') AS assigned_to,
                   COALESCE(notes,'') AS notes,
                   COALESCE(reason,'') AS reason,
                   COALESCE(updated_at,'') AS updated_at
            FROM review_decisions
            {where}
            ORDER BY updated_at DESC
            LIMIT {int(limit)}
            """,
            params,
        ).df()
        return df

    def completion_pct(self, *, pack_date: str, kind: DecisionKind, total_items: int) -> float:
        """Return the percentage of total_items that have a recorded decision."""
        if total_items <= 0:
            return 0.0
        decided = int(
            self.con.execute(
                "SELECT COUNT(*) FROM review_decisions WHERE pack_date=? AND kind=?",
                [str(pack_date), str(kind)],
            ).fetchone()[0]
        )
        return min(100.0, (decided / total_items) * 100.0)

    def export_for_pack(self, *, pack_dir: Path, pack_date: str) -> dict[str, str]:
        """Write decisions_export.xlsx and decisions_summary.md into pack_dir."""
        pack_dir.mkdir(parents=True, exist_ok=True)
        df = self.list(pack_date=pack_date, limit=50000)
        if df.empty:
            return {}
        xlsx = pack_dir / "decisions_export.xlsx"
        md = pack_dir / "decisions_summary.md"
        df.to_excel(xlsx, index=False, engine="openpyxl")

        # Simple summary by kind/status for quick review.
        summary = (
            df.groupby(["kind", "status"])
            .size()
            .reset_index(name="count")
            .sort_values(["kind", "status"])
        )
        lines = ["# Decisions Summary", "", f"- Pack date: {pack_date}", f"- Total decisions: {len(df)}", ""]
        lines.append("## Breakdown")
        for _, row in summary.iterrows():
            lines.append(f"- {row['kind']} / {row['status']}: {int(row['count'])}")
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"decisions_export": str(xlsx), "decisions_summary": str(md)}


def default_review_store(*, profile: str | None = None) -> ReviewStore:
    """Return a ReviewStore initialised from the given profile (or the default profile)."""
    return ReviewStore(profile=profile)

