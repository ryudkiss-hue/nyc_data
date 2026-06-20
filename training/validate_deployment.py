"""
Pre-deployment validation checklist for the dual-tier fuzzy router system.
Runs all checks before production deployment.
"""
import json
import sys
from pathlib import Path


def validate_kpi_registry(path: str = "config/kpi_registry_full.json") -> bool:
    """Validate KPI registry structure and content"""
    try:
        with open(path) as f:
            registry = json.load(f)

        required_fields = ["kpi_id", "kpi_name", "summary", "datasets", "sql_pattern"]

        for kpi_id, metadata in registry.items():
            if not all(f in metadata for f in required_fields):
                print(f"ERROR: {kpi_id} missing required fields")
                return False

        print(f"PASS: KPI registry ({len(registry)} KPIs)")
        return True
    except Exception as e:
        print(f"ERROR: KPI registry validation failed: {e}")
        return False


def validate_research_questions(path: str = "config/research_questions.json") -> bool:
    """Validate research questions structure"""
    try:
        with open(path) as f:
            questions = json.load(f)

        if not isinstance(questions, list) or len(questions) == 0:
            print("ERROR: Research questions must be non-empty list")
            return False

        print(f"PASS: Research questions ({len(questions)} questions)")
        return True
    except Exception as e:
        print(f"ERROR: Research questions validation failed: {e}")
        return False


def validate_question_variants(path: str = "training/question_variants_full.jsonl") -> bool:
    """Validate question variants exist and are formatted"""
    try:
        count = 0
        with open(path) as f:
            for line in f:
                json.loads(line)
                count += 1

        if count == 0:
            print("ERROR: No question variants found")
            return False

        print(f"PASS: Question variants ({count} total)")
        return True
    except Exception as e:
        print(f"ERROR: Question variants validation failed: {e}")
        return False


def validate_embeddings_cache(path: str = "cache/kpi_embeddings.json") -> bool:
    """Validate embeddings cache structure"""
    if not Path(path).exists():
        print("WARNING: Embeddings cache not found (will be generated on demand)")
        return True

    try:
        with open(path) as f:
            embeddings = json.load(f)

        print(f"PASS: Embeddings cache ({len(embeddings)} KPIs)")
        return True
    except Exception as e:
        print(f"ERROR: Embeddings cache validation failed: {e}")
        return False


def validate_dependencies() -> bool:
    """Check that required dependencies are installed"""
    try:
        import duckdb
        import pandas
        print("PASS: Core dependencies installed")
        return True
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        return False


def run_all_validations() -> bool:
    """Run complete deployment validation suite"""
    print("Running pre-deployment validation checklist...\n")

    checks = [
        ("Dependencies", validate_dependencies),
        ("KPI Registry", validate_kpi_registry),
        ("Research Questions", validate_research_questions),
        ("Question Variants", validate_question_variants),
        ("Embeddings Cache", validate_embeddings_cache),
    ]

    results = []
    for name, check in checks:
        try:
            result = check()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR: {name} check crashed: {e}")
            results.append((name, False))

    print("\n" + "="*50)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"SUMMARY: {passed}/{total} checks passed")

    if passed == total:
        print("STATUS: System ready for deployment")
        return True
    else:
        print("STATUS: Deployment blocked - fix above errors")
        return False


if __name__ == "__main__":
    success = run_all_validations()
    sys.exit(0 if success else 1)
