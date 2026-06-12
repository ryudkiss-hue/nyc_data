"""Inquiry template library — keyword and contract-type matching."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..reporting import generate_inquiry_response


def load_template_library(templates_dir: str | Path) -> list[tuple[str, list[str], str]]:
    """Load templates as (name, keywords, body) from ``*.md`` files."""
    root = Path(templates_dir)
    if not root.exists():
        return []
    out: list[tuple[str, list[str], str]] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        keywords: list[str] = []
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                meta, body = parts[1], parts[2]
                for line in meta.strip().splitlines():
                    if line.lower().startswith("keywords:"):
                        keywords = [
                            k.strip().lower()
                            for k in line.split(":", 1)[1].split(",")
                            if k.strip()
                        ]
        if not keywords:
            keywords = [path.stem.replace("_", " ").lower()]
        out.append((path.stem, keywords, body.strip()))
    return out

def match_templates(
    contracts: pd.DataFrame,
    templates: list[tuple[str, list[str], str]],
    *,
    contract_col: str = "contract_id",
    status_col: str = "status",
) -> list[tuple[str, str, str]]:
    """Return (contract_id, template_name, rendered_path_hint) matches."""
    if contracts.empty or not templates:
        return []

    matches: list[tuple[str, str, str]] = []
    for _, row in contracts.iterrows():
        cid = str(row.get(contract_col, "unknown"))
        status = str(row.get(status_col, "")).lower()
        contract_type = str(row.get("contract_type", row.get("type", ""))).lower()
        haystack = f"{cid} {status} {contract_type}".lower()

        for name, keywords, _body in templates:
            if any(kw in haystack for kw in keywords):
                matches.append((cid, name, name))
                break
    return matches

def render_inquiry_drafts(
    contracts: pd.DataFrame,
    templates_dir: str | Path,
    out_dir: Path,
    *,
    contract_ids: list[str] | None = None,
    contract_col: str = "contract_id",
) -> list[Path]:
    """Write inquiry drafts to ``out_dir`` using templates and reporting helpers."""
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = load_template_library(templates_dir)
    written: list[Path] = []

    ids = contract_ids or []
    if not ids and contract_col in contracts.columns:
        ids = [str(x) for x in contracts[contract_col].dropna().unique()[:10]]

    matched = {m[0]: m[1] for m in match_templates(contracts, templates)}

    for cid in ids:
        subset = contracts[contracts[contract_col] == cid] if contract_col in contracts.columns else contracts
        template_name = matched.get(cid, "contract_status")
        tpl_body = ""
        for name, _kw, body in templates:
            if name == template_name:
                tpl_body = body
                break

        if tpl_body:
            path = out_dir / f"inquiry_{cid}_{template_name}.md"
            filled = tpl_body.replace("{{contract_id}}", cid)
            path.write_text(filled, encoding="utf-8")
        else:
            draft = generate_inquiry_response("contract_status", subset, contract_id=cid)
            path = out_dir / f"inquiry_{cid}.md"
            draft.save(str(path))
        written.append(path)

    return written
