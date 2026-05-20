from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import pandas as pd


def _col_stats(s: pd.Series) -> dict[str, Any]:
    n = len(s)
    nulls = int(s.isna().sum()) if n else 0
    non_null = int(n - nulls)
    uniq = int(s.nunique(dropna=True)) if n else 0
    sample = [str(x) for x in s.dropna().head(5).tolist()]
    out: dict[str, Any] = {
        "dtype": str(s.dtype),
        "rows": int(n),
        "non_null": non_null,
        "nulls": nulls,
        "null_pct": float((nulls / n) * 100.0) if n else 0.0,
        "unique": uniq,
        "sample_values": sample,
    }
    # Numeric extras
    try:
        if pd.api.types.is_numeric_dtype(s):
            desc = s.dropna().astype(float).describe()
            out.update(
                {
                    "min": float(desc.get("min", 0.0)) if not desc.empty else None,
                    "max": float(desc.get("max", 0.0)) if not desc.empty else None,
                    "mean": float(desc.get("mean", 0.0)) if not desc.empty else None,
                }
            )
    except Exception:
        pass
    return out


def build_data_dictionary(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    payload: dict[str, Any] = {"sources": {}}
    for name, df in frames.items():
        if df is None or df.empty:
            payload["sources"][name] = {"rows": 0, "columns": {}}
            continue
        cols: dict[str, Any] = {}
        for c in df.columns:
            try:
                cols[str(c)] = _col_stats(df[c])
            except Exception:
                cols[str(c)] = {"dtype": "unknown"}
        payload["sources"][name] = {"rows": int(len(df)), "columns": cols}
    return payload


def render_data_dictionary_md(dd: dict[str, Any]) -> str:
    lines: list[str] = ["# Data Dictionary", ""]
    sources = dd.get("sources") or {}
    for name, s in sources.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Rows: {s.get('rows', 0)}")
        cols = s.get("columns") or {}
        if not cols:
            lines.append("- Columns: (none)")
            lines.append("")
            continue
        lines.append("")
        lines.append("| column | dtype | non_null | null_pct | unique | sample |")
        lines.append("|---|---|---:|---:|---:|---|")
        for col, meta in cols.items():
            sample = ", ".join((meta.get("sample_values") or [])[:3])
            lines.append(
                f"| `{col}` | {meta.get('dtype','')} | {meta.get('non_null','')} | {meta.get('null_pct',''):.2f} | {meta.get('unique','')} | {sample} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_data_dictionary(pack_dir: Path, frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    dd = build_data_dictionary(frames)
    pack_dir.mkdir(parents=True, exist_ok=True)
    md_path = pack_dir / "data_dictionary.md"
    json_path = pack_dir / "data_dictionary.json"
    md_path.write_text(render_data_dictionary_md(dd), encoding="utf-8")
    json_path.write_text(json.dumps(dd, indent=2, default=str), encoding="utf-8")
    return {"data_dictionary_md": str(md_path), "data_dictionary_json": str(json_path)}

