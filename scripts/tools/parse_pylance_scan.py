import json
import sys

# Read the existing Pyright scan results
try:
    with open("final_pylance_scan.json", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        # Find JSON start
        json_start = content.find("{")
        if json_start > 0:
            content = content[json_start:]

    data = json.loads(content)

    # Extract summary statistics
    generalDiagnostics = data.get("generalDiagnostics", [])

    # Count by rule type
    error_counts = {}
    warning_counts = {}
    critical_errors = {}

    # Critical error types to focus on
    critical_rules = [
        "reportAttributeAccessIssue",
        "reportUndefinedVariable",
        "reportIncompatibleVariableOverride",
    ]

    for diag in generalDiagnostics:
        rule = diag.get("rule", "unknown")
        severity = diag.get("severity", "error")

        if severity == "error":
            error_counts[rule] = error_counts.get(rule, 0) + 1
            if rule in critical_rules:
                critical_errors[rule] = critical_errors.get(rule, 0) + 1
        else:
            warning_counts[rule] = warning_counts.get(rule, 0) + 1

    total_errors = len([d for d in generalDiagnostics if d.get("severity") == "error"])
    total_warnings = len([d for d in generalDiagnostics if d.get("severity") == "warning"])

    print(f"=== PYRIGHT SCAN RESULTS ===\n")
    print(f"Total Errors: {total_errors}")
    print(f"Total Warnings: {total_warnings}")

    print(f"\n=== ERROR BREAKDOWN ===")
    for rule, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rule}: {count}")

    print(f"\n=== CRITICAL ERRORS (Blocking) ===")
    total_critical = sum(critical_errors.values())
    print(f"  Total Critical: {total_critical}")
    for rule, count in sorted(critical_errors.items(), key=lambda x: x[1], reverse=True):
        print(f"    {rule}: {count}")

    print(f"\n=== WARNING BREAKDOWN ===")
    for rule, count in sorted(warning_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rule}: {count}")

    # Comparison to baseline
    baseline = 357
    net_change = total_errors - baseline
    improvement_pct = (
        ((baseline - total_errors) / baseline * 100)
        if total_errors < baseline
        else ((total_errors - baseline) / baseline * 100)
    )

    print(f"\n=== BASELINE COMPARISON ===")
    print(f"  Original Baseline: {baseline} errors")
    print(f"  Current Errors: {total_errors} errors")
    print(f"  Net Change: {net_change:+d} ({improvement_pct:+.1f}%)")

    if total_errors <= baseline:
        print(f"  Status: ✅ IMPROVEMENT")
    else:
        print(f"  Status: ❌ REGRESSION")

except json.JSONDecodeError as e:
    print(f"JSON Parse Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
