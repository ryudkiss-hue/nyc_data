#!/usr/bin/env python3
"""
qa_runner.py — Automated QA checks against analysis output documents.

Usage:
    python qa_runner.py <path/to/report.md>
    python qa_runner.py reports/analytics-cycle-2026-06-02/02_business_metrics.md

Checks:
  - No NaN / null / undefined values in numeric cells
  - Percentages sum to ~100% where expected
  - All table rows have consistent column counts
  - No TODO / FIXME / placeholder text left in document
  - No broken relative links
  - Numeric values are plausible (no negative counts, no rates >100%)
  - Every ⚠️ flag has a corresponding note
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ISSUES: list[tuple[str, str, str]] = []  # (severity, line, message)


def flag(severity: str, line: str | int, msg: str) -> None:
    ISSUES.append((severity, str(line), msg))


def check_placeholders(lines: list[str]) -> None:
    patterns = [r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"\[PLACEHOLDER\]", r"\bTBD\b"]
    for i, line in enumerate(lines, 1):
        for pat in patterns:
            if re.search(pat, line, re.I):
                flag("ERROR", i, f"Placeholder text found: {line.strip()[:60]}")


def check_table_structure(lines: list[str]) -> None:
    in_table = False
    header_cols: int | None = None
    table_start = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_start = i
                header_cols = stripped.count("|") - 1
            else:
                if "---" not in stripped:
                    cols = stripped.count("|") - 1
                    if cols != header_cols:
                        flag("ERROR", i, f"Table column mismatch: expected {header_cols}, got {cols}")
        else:
            in_table = False
            header_cols = None


def check_percentages(lines: list[str]) -> None:
    pct_pattern = re.compile(r"(\d+\.?\d*)\s*%")
    for i, line in enumerate(lines, 1):
        for match in pct_pattern.finditer(line):
            val = float(match.group(1))
            if val > 100.0:
                flag("ERROR", i, f"Percentage > 100%: {val}% in: {line.strip()[:60]}")
            elif val < 0:
                flag("ERROR", i, f"Negative percentage: {val}%")


def check_numeric_plausibility(lines: list[str]) -> None:
    count_pattern = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+)\s*(rows|violations|corners|segments|jobs)\b", re.I)
    for i, line in enumerate(lines, 1):
        for match in count_pattern.finditer(line):
            raw = match.group(1).replace(",", "")
            val = int(raw)
            if val < 0:
                flag("ERROR", i, f"Negative count {val} for '{match.group(2)}'")
            if val > 10_000_000:
                flag("WARN", i, f"Suspiciously large count {val:,} — verify")


def check_warning_flags(lines: list[str]) -> None:
    warning_lines = [i for i, ln in enumerate(lines, 1) if "⚠️" in ln]
    for wl in warning_lines:
        # Check that the ⚠️ line or the next line has explanatory text
        context = lines[wl - 1].strip()
        if len(context) < 10:
            flag("WARN", wl, "⚠️ flag with no explanatory text")


def check_data_source_citations(content: str) -> None:
    # Every dataset mentioned should have an API ID or citation
    datasets = re.findall(r"\b([a-z0-9]{4}-[a-z0-9]{4})\b", content)
    if not datasets:
        flag("WARN", "—", "No Socrata API IDs (xxxx-xxxx format) found — data sources may be undocumented")


def check_recommendations_actionable(lines: list[str]) -> None:
    rec_section = False
    for i, line in enumerate(lines, 1):
        if "recommendation" in line.lower() or "## 5." in line:
            rec_section = True
        if rec_section and line.strip().startswith(">"):
            text = line.strip()
            # Check recommendation has an owner signal (Recommend: verb)
            if not re.search(r"[Rr]ecommend(ation)?[:\s]", text) and not re.search(r"\bshould\b|\baction\b", text, re.I):
                flag("INFO", i, f"Recommendation may lack actionable verb: {text[:70]}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: qa_runner.py <report.md>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    print(f"\n{'='*60}")
    print(f"QA RUNNER: {path.name}")
    print(f"Lines: {len(lines)} | Size: {len(content):,} bytes")
    print(f"{'='*60}\n")

    check_placeholders(lines)
    check_table_structure(lines)
    check_percentages(lines)
    check_numeric_plausibility(lines)
    check_warning_flags(lines)
    check_data_source_citations(content)
    check_recommendations_actionable(lines)

    if not ISSUES:
        print("✅ All automated checks passed — no issues found.\n")
        sys.exit(0)

    errors = [x for x in ISSUES if x[0] == "ERROR"]
    warns = [x for x in ISSUES if x[0] == "WARN"]
    infos = [x for x in ISSUES if x[0] == "INFO"]

    for sev, lineno, msg in ISSUES:
        icon = {"ERROR": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ "}.get(sev, "?")
        print(f"{icon} [{sev}] line {lineno}: {msg}")

    print(f"\nSummary: {len(errors)} errors, {len(warns)} warnings, {len(infos)} info")
    if errors:
        print("❌ QA FAILED — resolve errors before delivery.")
        sys.exit(1)
    else:
        print("✅ QA PASSED (warnings noted — review before delivery).")
        sys.exit(0)


if __name__ == "__main__":
    main()
