import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from .cli_nlquery import run_nl_query
from .observability.duckdb_store import DuckDBObservabilityStore


def load_kpi_registry(registry_path: str = "config/kpi_registry.json") -> dict:
    """Load KPI registry from JSON file"""
    path = Path(registry_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_research_questions(questions_path: str = "config/research_questions.json") -> list:
    """Load research questions from JSON file"""
    path = Path(questions_path)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def load_embeddings_cache(cache_path: str = "cache/kpi_embeddings.json") -> dict:
    """Load embeddings cache from JSON file"""
    path = Path(cache_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def execute_nlquery(args):
    """Execute natural language query"""
    kpi_registry = load_kpi_registry(args.registry)
    research_questions = load_research_questions()
    embeddings_cache = load_embeddings_cache()

    decision_id = str(uuid.uuid4())
    result = run_nl_query(
        question=args.question,
        kpi_registry=kpi_registry,
        research_questions=research_questions,
        embeddings_cache=embeddings_cache,
        expand=args.expand,
        mark_helpful=args.helpful,
        mark_wrong=args.wrong,
        corrected_kpi_id=args.corrected_kpi
    )

    store = DuckDBObservabilityStore(args.db)
    try:
        store.record_routing_decision(
            decision_id=decision_id,
            question=args.question,
            matched_kpi_id=result.get('matched_kpi'),
            confidence=result.get('confidence', 0.0),
            ensemble_status="success" if result.get('matched_kpi') else "no_match",
            latency_ms=0,
            router_source=result.get('routing_source', 'unknown')
        )

        if args.helpful or args.wrong:
            store.record_feedback(
                feedback_id=str(uuid.uuid4()),
                routing_decision_id=decision_id,
                helpful=args.helpful,
                corrected_kpi_id=args.corrected_kpi,
                feedback_text=args.question
            )
    finally:
        store.close()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get('matched_kpi'):
            print(f"\nMatched: {result.get('kpi_name')}")
            print(f"Confidence: {result.get('confidence'):.2%}")
        else:
            print("\nNo match found")


def execute_evaluate(args):
    """Execute evaluation subcommand"""
    sys.path.insert(0, 'src')
    from socrata_toolkit.training.evaluate_router import evaluate_router

    with open(args.registry) as f:
        registry = json.load(f)

    variants = []
    with open(args.variants) as f:
        for line in f:
            variants.append(json.loads(line))

    result = evaluate_router(registry, variants)
    print(f"Router Accuracy: {result['accuracy']:.2%}")
    print(f"Correct: {result['correct']}/{result['total']}")
    print(json.dumps(result['confusion_matrix'], indent=2))


def execute_train(args):
    """Execute training subcommand"""
    sys.path.insert(0, 'src')
    from socrata_toolkit.training.train_router_weights import train_router_weights

    store = DuckDBObservabilityStore(args.db)
    feedback = store.get_recent_feedback(limit=1000)
    store.close()

    result = train_router_weights(feedback, iterations=args.iterations)
    print(f"Training complete - {args.iterations} iterations")
    print(f"Final Accuracy: {result['accuracy']:.2%}")
    print(f"Updated Weights: {json.dumps(result['updated_weights'], indent=2)}")


def execute_demo(args):
    """Execute demo subcommand"""
    sys.path.insert(0, 'src')
    from training.demo_workflow import run_demo
    run_demo()


def execute_readiness(args):
    """Print the deployment readiness report (automated checks)."""
    from socrata_toolkit.core.readiness import run_readiness_checks

    report = run_readiness_checks(run_pytest=getattr(args, "pytest", False))
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        print(f"Readiness: {report['overall_score']}/100  ({report['grade']})")
        for axis, score in report["axis_scores"].items():
            print(f"  {axis:<16} {score:>5}/100")
        print(report["note"])


_FOURFOUR_RE = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")
_DEFAULT_DOMAIN = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")


def _resolve_fourfour(
    key_or_fourfour: str,
    config_path: str = "pipeline/config/socrata_datasets.json",
) -> tuple[str, str]:
    """Return (key, fourfour). Accepts a raw 4x4 id or a dataset key from the pipeline config."""
    if _FOURFOUR_RE.match(key_or_fourfour):
        return key_or_fourfour, key_or_fourfour
    path = Path(config_path)
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
        entries = list(cfg.get("socrata_remaining", [])) + list(cfg.get("cached_datasets", []))
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == key_or_fourfour and entry.get("socrata_id"):
                return key_or_fourfour, entry["socrata_id"]
    raise SystemExit(
        f"Unknown dataset '{key_or_fourfour}': not a 4x4 id and no matching key in {config_path}"
    )


def execute_health(args):
    """Classify a dataset's health from live Socrata metadata."""
    from datetime import datetime, timezone

    import requests

    from socrata_toolkit.analysis.dataset_health import (
        DatasetHealthClassifier,
        DatasetHealthMetrics,
    )

    key, fourfour = _resolve_fourfour(args.dataset)
    headers = {}
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    try:
        resp = requests.get(
            f"https://{args.domain}/api/views/{fourfour}.json", headers=headers, timeout=30
        )
        accessible = resp.ok
        payload = resp.json() if resp.ok else {}
        error_message = None if resp.ok else f"HTTP {resp.status_code}"
    except Exception as e:
        accessible, payload, error_message = False, {}, str(e)

    updated = payload.get("rowsUpdatedAt")
    schema = {
        c.get("fieldName") or c.get("name", ""): c.get("dataTypeName", "")
        for c in payload.get("columns", [])
    }
    # /api/views has no reliable row count (viewCount is page views) — ask SoQL for one.
    row_count = payload.get("rowsCount")
    if accessible and row_count is None:
        try:
            cresp = requests.get(
                f"https://{args.domain}/resource/{fourfour}.json",
                params={"$select": "count(*) as n"}, headers=headers, timeout=30,
            )
            if cresp.ok:
                row_count = int(cresp.json()[0].get("n", 0))
        except Exception:
            row_count = None
    metrics = DatasetHealthMetrics(
        key=key,
        fourfour=fourfour,
        row_count=row_count,
        last_modified=datetime.fromtimestamp(updated, tz=timezone.utc) if updated else None,
        schema_snapshot=schema or None,
        schema_baseline=schema or None,
        is_accessible=accessible,
        error_message=error_message,
    )
    report = DatasetHealthClassifier().classify(metrics)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
        return
    print(f"{key} ({fourfour}) - {payload.get('name', 'inaccessible')}")
    print(f"  Status:    {report.status.value}  (severity {report.severity}/100, {report.severity_level.value})")
    print(f"  Rows:      {report.row_count if report.row_count is not None else 'unknown'}")
    print(f"  Freshness: {report.freshness_days if report.freshness_days is not None else 'unknown'} days since last update")
    for alert in report.alerts:
        print(f"  ! {alert}")
    for rec in report.recommendations:
        print(f"  -> {rec}")


def execute_ramp_analysis(args):
    """Borough-level ramp completion rates with 95% Wilson score CIs."""
    from socrata_toolkit.analyst.ramp_analysis import (
        aggregate_ramp_status,
        compute_borough_completion_rates,
        fetch_ramp_full_corpus,
    )

    df = fetch_ramp_full_corpus(os.getenv("SOCRATA_APP_TOKEN"))
    if args.borough and "borough" in df.columns:
        df = df[df["borough"].astype(str).str.upper().str.startswith(args.borough.upper())]
    if "total_complaints" not in df.columns:
        df = aggregate_ramp_status(df)
    result = compute_borough_completion_rates(df)
    table = result.pop("comparison_table")
    overall = result.pop("overall_completion_rate", 0.0)

    if args.json:
        print(json.dumps(
            {"overall_completion_rate": overall,
             "boroughs": table.to_dict(orient="records") if not table.empty else []},
            indent=2, default=str,
        ))
        return
    if table.empty:
        print("No ramp data returned — check network access and SOCRATA_APP_TOKEN.")
        return
    print(table.to_string(index=False))
    print(f"\nOverall completion rate: {overall:.1%}  (n={len(df)})")


def execute_quality_score(args):
    """Composite 0-100 quality score for a live dataset sample."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig
    from socrata_toolkit.governance.core import compute_quality_score

    key, fourfour = _resolve_fourfour(args.dataset)
    client = SocrataClient(SocrataConfig())
    df = client.fetch_dataframe(args.domain, fourfour, max_rows=args.max_rows)
    if df.empty:
        print(f"{key} ({fourfour}): no rows fetched — cannot score.")
        return
    score = compute_quality_score(
        df,
        key_columns=args.key_column or None,
        date_column=args.date_column,
        freshness_days_threshold=args.freshness_days,
    )
    if args.json:
        print(json.dumps({
            "overall": score.overall, "completeness": score.completeness,
            "validity": score.validity, "consistency": score.consistency,
            "freshness": score.freshness, "sample_rows": len(df),
        }, indent=2))
        return
    print(f"{key} ({fourfour}) - quality score on {len(df)} sampled rows")
    print(f"  Overall:      {score.overall:.1f}/100")
    print(f"  Completeness: {score.completeness:.1f}   Validity: {score.validity:.1f}")
    print(f"  Consistency:  {score.consistency:.1f}   Freshness: {score.freshness:.1f}")


def main():
    """Main CLI entry point with subcommands"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(
        description="NYC DOT SIM analyst toolkit CLI"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    nlquery_parser = subparsers.add_parser('query', help='Ask a natural language question')
    nlquery_parser.add_argument("question", help="Natural language question")
    nlquery_parser.add_argument("--expand", action="store_true")
    nlquery_parser.add_argument("--helpful", action="store_true")
    nlquery_parser.add_argument("--wrong", action="store_true")
    nlquery_parser.add_argument("--corrected-kpi", type=str, default=None)
    nlquery_parser.add_argument("--registry", type=str, default="config/kpi_registry.json")
    nlquery_parser.add_argument("--db", type=str, default="data/local_db/router_observability.duckdb")
    nlquery_parser.add_argument("--json", action="store_true")

    eval_parser = subparsers.add_parser('evaluate', help='Evaluate router accuracy')
    eval_parser.add_argument("--registry", type=str, default="config/kpi_registry_full.json")
    eval_parser.add_argument("--variants", type=str, default="training/question_variants_full.jsonl")

    train_parser = subparsers.add_parser('train', help='Optimize router weights')
    train_parser.add_argument("--db", type=str, default="data/local_db/router_observability.duckdb")
    train_parser.add_argument("--iterations", type=int, default=10)

    subparsers.add_parser('demo', help='Run end-to-end demo')

    readiness_parser = subparsers.add_parser('readiness', help='Print deployment readiness report')
    readiness_parser.add_argument("--json", action="store_true", help="Emit the full report as JSON")
    readiness_parser.add_argument("--pytest", action="store_true", help="Also run the test suite as a reliability check")

    health_parser = subparsers.add_parser('health', help='Classify dataset health from live Socrata metadata')
    health_parser.add_argument("dataset", help="Dataset key (e.g. violations) or 4x4 id (e.g. 6kbp-uz6m)")
    health_parser.add_argument("--domain", default=_DEFAULT_DOMAIN)
    health_parser.add_argument("--json", action="store_true")

    ramp_parser = subparsers.add_parser('ramp-analysis', help='Borough ramp completion rates with 95%% Wilson CIs')
    ramp_parser.add_argument("--borough", default=None, help="Filter to one borough (prefix match, e.g. MN or MANHATTAN)")
    ramp_parser.add_argument("--json", action="store_true")

    quality_parser = subparsers.add_parser('quality-score', help='Composite 0-100 quality score for a dataset sample')
    quality_parser.add_argument("dataset", help="Dataset key or 4x4 id")
    quality_parser.add_argument("--domain", default=_DEFAULT_DOMAIN)
    quality_parser.add_argument("--key-column", action="append", default=None, help="Uniqueness key column (repeatable)")
    quality_parser.add_argument("--date-column", default=None)
    quality_parser.add_argument("--max-rows", type=int, default=10_000)
    quality_parser.add_argument("--freshness-days", type=int, default=30)
    quality_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == 'evaluate':
        execute_evaluate(args)
    elif args.command == 'train':
        execute_train(args)
    elif args.command == 'demo':
        execute_demo(args)
    elif args.command == 'query':
        execute_nlquery(args)
    elif args.command == 'readiness':
        execute_readiness(args)
    elif args.command == 'health':
        execute_health(args)
    elif args.command == 'ramp-analysis':
        execute_ramp_analysis(args)
    elif args.command == 'quality-score':
        execute_quality_score(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
