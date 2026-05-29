"""Command-line interface for the FAIR catalog.

Subcommands:
    emit   Build a FAIR catalog from the dataset registry and print/write JSON.
    dcat   Emit the catalog as DCAT JSON-LD.
    score  Print a table of dataset_id -> FAIRness overall + sub-scores.

Run as ``python -m socrata_toolkit.fair.cli <subcommand>``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .registry_bridge import from_registry_yaml

_DEFAULT_REGISTRY = "config/datasets.yaml"


def _build_parser() -> argparse.ArgumentParser:
    # Shared --registry option, accepted either before or after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--registry", default=_DEFAULT_REGISTRY,
        help=f"Path to the dataset registry YAML (default: {_DEFAULT_REGISTRY}).",
    )

    parser = argparse.ArgumentParser(
        prog="socrata-fair",
        description="FAIR catalog tooling for NYC Open Data.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_emit = sub.add_parser("emit", parents=[common], help="Emit the FAIR catalog as JSON.")
    p_emit.add_argument("--output", "-o", help="Write JSON to this file instead of stdout.")

    p_dcat = sub.add_parser("dcat", parents=[common], help="Emit the catalog as DCAT JSON-LD.")
    p_dcat.add_argument("--output", "-o", help="Write JSON-LD to this file instead of stdout.")

    sub.add_parser("score", parents=[common], help="Print a FAIRness score table.")
    return parser


def _cmd_emit(args: argparse.Namespace) -> int:
    catalog = from_registry_yaml(args.registry)
    text = catalog.to_json()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote catalog JSON to {args.output}")
    else:
        print(text)
    return 0


def _cmd_dcat(args: argparse.Namespace) -> int:
    catalog = from_registry_yaml(args.registry)
    text = json.dumps(catalog.to_dcat_jsonld(), indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote DCAT JSON-LD to {args.output}")
    else:
        print(text)
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    catalog = from_registry_yaml(args.registry)
    scores = catalog.score_all()
    header = f"{'dataset_id':<28} {'overall':>8} {'F':>6} {'A':>6} {'I':>6} {'R':>6}"
    print(header)
    print("-" * len(header))
    for ds_id, s in scores.items():
        print(
            f"{ds_id:<28} {s.overall:>8.1f} {s.findable:>6.1f} "
            f"{s.accessible:>6.1f} {s.interoperable:>6.1f} {s.reusable:>6.1f}"
        )
    return 0


_DISPATCH = {"emit": _cmd_emit, "dcat": _cmd_dcat, "score": _cmd_score}


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    return _DISPATCH[args.command](args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
