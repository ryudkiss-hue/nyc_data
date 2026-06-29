import argparse
import json
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


def main():
    """Main CLI entry point with subcommands"""
    parser = argparse.ArgumentParser(
        description="NYC DOT SIM Natural Language Query Interface"
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
