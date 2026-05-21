"""Week-over-week construction list diff vs previous analyst pack."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def find_previous_pack_dir(pack_dir: Path, outputs_root: Path | None = None) -> Path | None:
    """Return the most recent pack folder strictly before ``pack_dir``."""
    root = outputs_root or pack_dir.parent
    if not root.exists():
        return None
    dated = sorted(d for d in root.iterdir() if d.is_dir() and d != pack_dir)
    prior = [d for d in dated if d.name < pack_dir.name]
    return prior[-1] if prior else (dated[-1] if dated and dated[-1] != pack_dir else None)


def diff_construction_lists(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    *,
    key_col: str = "location_id",
) -> tuple[pd.DataFrame, str]:
    """Compare construction lists; return tagged DataFrame and markdown summary."""
    if current.empty and previous.empty:
        return current, "# Construction List Diff\n\nNo data in current or previous pack.\n"

    cur_keys = set(current[key_col].astype(str)) if key_col in current.columns else set()
    prev_keys = set(previous[key_col].astype(str)) if key_col in previous.columns else set()

    added = cur_keys - prev_keys
    removed = prev_keys - cur_keys
    common = cur_keys & prev_keys

    lines = [
        "# Construction List — Week over Week",
        "",
        f"- **Current items:** {len(cur_keys)}",
        f"- **Previous items:** {len(prev_keys)}",
        f"- **Added:** {len(added)}",
        f"- **Removed:** {len(removed)}",
        f"- **Unchanged keys:** {len(common)}",
        "",
    ]
    if added:
        lines.append("## New locations")
        for loc in sorted(added)[:50]:
            lines.append(f"- {loc}")
        if len(added) > 50:
            lines.append(f"- … and {len(added) - 50} more")
        lines.append("")
    if removed:
        lines.append("## Dropped locations")
        for loc in sorted(removed)[:50]:
            lines.append(f"- {loc}")
        if len(removed) > 50:
            lines.append(f"- … and {len(removed) - 50} more")
        lines.append("")

    tagged = current.copy()
    if key_col in tagged.columns:
        tagged["_wow_change"] = tagged[key_col].astype(str).map(
            lambda k: "new" if k in added else ("removed_prev" if k in removed else "unchanged")
        )
    return tagged, "\n".join(lines)
