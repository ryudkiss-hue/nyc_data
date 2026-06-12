"""Export helpers for the Export Center.

Provides byte-buffer builders for CSV, Excel, JSON, and a multi-dataset ZIP
bundle. All functions are pure (no Streamlit dependency) so they're testable.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """UTF-8 CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")

def to_json_bytes(df: pd.DataFrame, *, orient: str = "records") -> bytes:
    """Pretty JSON bytes."""
    return df.to_json(orient=orient, indent=2, date_format="iso").encode("utf-8")

def to_excel_bytes(frames: dict[str, pd.DataFrame]) -> bytes | None:
    """Multi-sheet Excel workbook. Returns None if no engine is available."""
    buffer = io.BytesIO()
    engine = None
    for candidate in ("xlsxwriter", "openpyxl"):
        try:
            __import__(candidate)
            engine = candidate
            break
        except ImportError:
            continue
    if engine is None:
        return None
    with pd.ExcelWriter(buffer, engine=engine) as writer:
        for name, df in frames.items():
            # Excel sheet names: max 31 chars, no special chars
            sheet = "".join(c for c in name if c.isalnum() or c in " _-")[:31] or "Sheet"
            df.to_excel(writer, sheet_name=sheet, index=False)
    buffer.seek(0)
    return buffer.getvalue()

def to_zip_bundle(frames: dict[str, pd.DataFrame], *, fmt: str = "csv") -> bytes:
    """ZIP archive of multiple datasets, one file each (csv or json)."""
    buffer = io.BytesIO()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, df in frames.items():
            if fmt == "json":
                zf.writestr(f"{name}_{ts}.json", to_json_bytes(df))
            else:
                zf.writestr(f"{name}_{ts}.csv", to_csv_bytes(df))
        # manifest
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": fmt,
            "datasets": {name: {"rows": len(df), "cols": len(df.columns)} for name, df in frames.items()},
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    buffer.seek(0)
    return buffer.getvalue()

def summary_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One-row-per-dataset summary for the export picker."""
    rows = []
    for name, df in frames.items():
        rows.append(
            {
                "Dataset": name,
                "Rows": len(df),
                "Columns": len(df.columns),
                "Memory (KB)": round(df.memory_usage(deep=True).sum() / 1024, 1),
            }
        )
    return pd.DataFrame(rows)
