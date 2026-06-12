#!/usr/bin/env python
"""Verification script for domain_rules implementation."""
import sys
import traceback

def test_imports():
    """Test that the module imports correctly."""
    try:
        from socrata_toolkit.quality.domain_rules import (
            DomainRuleResult,
            validate_material_lifespan_rule,
            validate_borough_coverage_distribution,
            validate_permit_inspection_relationship,
            validate_all_domain_rules,
            summarize_domain_rule_results,
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_material_lifespan():
    """Test material_lifespan_rule."""
    try:
        import pandas as pd
        from socrata_toolkit.quality.domain_rules import validate_material_lifespan_rule

        # Create test data
        df = pd.DataFrame({
            "inspection_id": ["INS001", "INS002", "INS003", "INS004"],
            "material_type": ["concrete", "concrete", "asphalt", "asphalt"],
            "lifespan_years": [18.0, 19.0, 11.0, 10.5],
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
        })

        result = validate_material_lifespan_rule(df)

        assert result.status == "PASS", f"Expected PASS, got {result.status}"
        assert result.rows_affected == 0, f"Expected 0 affected rows, got {result.rows_affected}"
        assert result.rule_name == "material_lifespan_rule"

        print("✅ Material lifespan rule test PASSED")
        print(f"   Details: {result.details}")
        return True
    except Exception as e:
        print(f"❌ Material lifespan rule test FAILED: {e}")
        traceback.print_exc()
        return False

def test_borough_coverage():
    """Test borough_coverage_distribution rule."""
    try:
        import pandas as pd
        from socrata_toolkit.quality.domain_rules import validate_borough_coverage_distribution

        # Create test data with 40% Manhattan (PASS case)
        df = pd.DataFrame({
            "inspection_id": [f"INS{i:03d}" for i in range(100)],
            "borough": (
                (["MANHATTAN"] * 40)
                + (["BROOKLYN"] * 30)
                + (["QUEENS"] * 20)
                + (["BRONX"] * 10)
            ),
        })

        result = validate_borough_coverage_distribution(df)

        assert result.status == "PASS", f"Expected PASS, got {result.status}"
        assert result.rule_name == "borough_coverage_distribution"
        assert "40.0%" in result.details

        print("✅ Borough coverage rule test PASSED")
        print(f"   Details: {result.details}")
        return True
    except Exception as e:
        print(f"❌ Borough coverage rule test FAILED: {e}")
        traceback.print_exc()
        return False

def test_permit_inspection():
    """Test permit_inspection_relationship rule."""
    try:
        import pandas as pd
        from socrata_toolkit.quality.domain_rules import validate_permit_inspection_relationship

        # Create test data
        permits = pd.DataFrame({
            "permit_id": ["P001", "P002"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "start_date": ["2026-01-01", "2026-02-01"],
            "end_date": ["2026-03-01", "2026-04-01"],
            "latitude": [40.7128, 40.6501],
            "longitude": [-74.0060, -73.9496],
        })

        inspections = pd.DataFrame({
            "inspection_id": ["INS001", "INS002"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "inspection_date": ["2026-02-01", "2026-03-01"],
            "latitude": [40.7128, 40.6501],
            "longitude": [-74.0060, -73.9496],
        })

        result = validate_permit_inspection_relationship(permits, inspections)

        assert result.status in ["PASS", "WARNING"], f"Expected PASS/WARNING, got {result.status}"
        assert result.rule_name == "permit_inspection_relationship"

        print("✅ Permit-inspection relationship rule test PASSED")
        print(f"   Status: {result.status}, Details: {result.details}")
        return True
    except Exception as e:
        print(f"❌ Permit-inspection relationship rule test FAILED: {e}")
        traceback.print_exc()
        return False

def test_orchestration():
    """Test validate_all_domain_rules orchestrator."""
    try:
        import pandas as pd
        from socrata_toolkit.quality.domain_rules import validate_all_domain_rules

        df = pd.DataFrame({
            "inspection_id": [f"INS{i:03d}" for i in range(100)],
            "borough": (["MANHATTAN"] * 40) + (["BROOKLYN"] * 60),
            "material_type": (["concrete"] * 60) + (["asphalt"] * 40),
            "lifespan_years": ([18.0] * 60) + ([11.0] * 40),
        })

        results = validate_all_domain_rules(df)

        assert isinstance(results, list), f"Expected list, got {type(results)}"
        assert len(results) >= 2, f"Expected at least 2 results, got {len(results)}"
        assert all(hasattr(r, 'status') for r in results), "Results missing status attribute"

        print("✅ Rule orchestration test PASSED")
        print(f"   Rules executed: {[r.rule_name for r in results]}")
        print(f"   Statuses: {[r.status for r in results]}")
        return True
    except Exception as e:
        print(f"❌ Rule orchestration test FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all verification tests."""
    print("=" * 70)
    print("DOMAIN RULES VERIFICATION")
    print("=" * 70)

    tests = [
        ("Imports", test_imports),
        ("Material Lifespan Rule", test_material_lifespan),
        ("Borough Coverage Rule", test_borough_coverage),
        ("Permit-Inspection Rule", test_permit_inspection),
        ("Rule Orchestration", test_orchestration),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n▶ Testing {test_name}...")
        passed = test_func()
        results.append((test_name, passed))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("=" * 70)

    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
