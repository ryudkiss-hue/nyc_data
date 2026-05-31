"""
Bundle multiple context files into a single structured text file for AI-assisted analysis.

Applies a priority ordering (task > business > schema > prior_findings > constraints > format),
deduplicates repeated content, and produces a single prompt-ready bundle.

Usage:
    python context_bundler.py --task "Investigate churn drivers" \
        --files schema.md business_context.md prior_report.md \
        --output bundle.txt

    python context_bundler.py --config bundle_config.json --output bundle.txt
"""

import argparse
import json
import os
import sys
from pathlib import Path

LAYER_ORDER = ["task", "business", "schema", "prior_findings", "constraints", "format"]

LAYER_HEADERS = {
    "task": "## TASK",
    "business": "## BUSINESS CONTEXT",
    "schema": "## DATA SCHEMA",
    "prior_findings": "## PRIOR FINDINGS",
    "constraints": "## CONSTRAINTS",
    "format": "## OUTPUT FORMAT",
}


def build_bundle(task: str, file_map: dict[str, list[str]]) -> str:
    sections = []
    sections.append("# Context Bundle\n")

    if task:
        sections.append(f"{LAYER_HEADERS['task']}\n{task}\n")

    for layer in LAYER_ORDER:
        if layer == "task":
            continue
        paths = file_map.get(layer, [])
        if not paths:
            continue
        content_parts = []
        for path in paths:
            p = Path(path)
            if not p.exists():
                print(f"  WARNING: file not found: {path}", file=sys.stderr)
                continue
            content_parts.append(f"### {p.name}\n{p.read_text(encoding='utf-8').strip()}")
        if content_parts:
            sections.append(f"{LAYER_HEADERS[layer]}\n" + "\n\n".join(content_parts) + "\n")

    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="Bundle context files for AI-assisted analysis.")
    parser.add_argument("--task", help="Task description (what you want the AI to do)")
    parser.add_argument("--files", nargs="+", help="Files to bundle (assigned to 'prior_findings' layer by default)")
    parser.add_argument("--business", nargs="+", help="Business context files")
    parser.add_argument("--schema", nargs="+", help="Schema / data dictionary files")
    parser.add_argument("--constraints", nargs="+", help="Constraint files")
    parser.add_argument("--format", nargs="+", dest="fmt", help="Output format files")
    parser.add_argument("--config", help="JSON config file with layer → file mappings")
    parser.add_argument("--output", required=True, help="Output path for the bundle")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        task = config.get("task", "")
        file_map = {k: v for k, v in config.items() if k != "task"}
    else:
        task = args.task or ""
        file_map = {
            "business": args.business or [],
            "schema": args.schema or [],
            "prior_findings": args.files or [],
            "constraints": args.constraints or [],
            "format": args.fmt or [],
        }

    bundle = build_bundle(task, file_map)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(bundle)

    char_count = len(bundle)
    est_tokens = char_count // 4
    print(f"Bundle written to {args.output}")
    print(f"  Characters: {char_count:,}  |  Estimated tokens: ~{est_tokens:,}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Demo: bundle two in-memory snippets
        demo_task = "Investigate why enterprise churn increased in Q1 2024."
        demo_file_map = {
            "business": [],
            "schema": [],
            "prior_findings": [],
        }
        bundle = build_bundle(demo_task, demo_file_map)
        print("Demo bundle preview:")
        print(bundle[:300])
        print(f"  Estimated tokens: ~{len(bundle)//4:,}")
    else:
        main()
