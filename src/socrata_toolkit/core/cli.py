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


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="NYC DOT SIM Natural Language Query Interface"
    )

    parser.add_argument("question", help="Natural language question to route")
    parser.add_argument("--expand", action="store_true", help="Include Tier 2 Claude expansion")
    parser.add_argument("--helpful", action="store_true", help="Mark result as helpful")
    parser.add_argument("--wrong", action="store_true", help="Mark result as wrong")
    parser.add_argument("--corrected-kpi", type=str, default=None, help="Corrected KPI ID")
    parser.add_argument("--registry", type=str, default="config/kpi_registry.json", help="Path to KPI registry")
    parser.add_argument("--db", type=str, default="data/local_db/router_observability.duckdb", help="Path to DuckDB store")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Load configuration
    kpi_registry = load_kpi_registry(args.registry)
    research_questions = load_research_questions()
    embeddings_cache = load_embeddings_cache()

    # Generate unique decision ID
    decision_id = str(uuid.uuid4())

    # Execute query
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

    # Store in observability
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

    # Output result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get('matched_kpi'):
            print(f"\nMatched: {result.get('kpi_name')}")
            print(f"Confidence: {result.get('confidence'):.2%}")
        else:
            print(f"\nNo match found")


if __name__ == "__main__":
    main()
