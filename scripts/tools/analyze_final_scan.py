import json
from collections import defaultdict

data = json.load(open("final_comprehensive_scan.json"))
errors = data["generalDiagnostics"]

# Categorize by rule type and severity
error_types = defaultdict(int)
warning_types = defaultdict(int)

for err in errors:
    rule = err.get("rule", "unknown")
    severity = err.get("severity", "unknown")

    if severity == "error":
        error_types[rule] += 1
    elif severity == "warning":
        warning_types[rule] += 1

# Sort by count
sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
sorted_warnings = sorted(warning_types.items(), key=lambda x: x[1], reverse=True)

print("ERROR CATEGORIES (Top 10):")
print("=" * 70)
for rule, count in sorted_errors[:10]:
    print(f"{rule}: {count}")

print(f"\nWARNING CATEGORIES (Top 10):")
print("=" * 70)
for rule, count in sorted_warnings[:10]:
    print(f"{rule}: {count}")

print(f"\nSUMMARY:")
print("=" * 70)
print(f"Total Errors: {sum(ct for _, ct in error_types.items())}")
print(f"Total Warnings: {sum(ct for _, ct in warning_types.items())}")
print(f"All Diagnostics: {len(errors)}")

# Key error categories
report_attr = sum(
    count for rule, count in error_types.items() if "Attribute" in rule or "attribute" in rule
)
report_undefined = sum(
    count for rule, count in error_types.items() if "Undefined" in rule or "undefined" in rule
)
report_arg = sum(
    count
    for rule, count in error_types.items()
    if "Argument" in rule or "argument" in rule or "Call" in rule or "call" in rule
)

print(f"\nKEY METRICS:")
print("=" * 70)
print(f"reportAttributeAccessIssue: {report_attr}")
print(f"reportUndefinedVariable: {report_undefined}")
print(f"reportArgumentType/reportCallIssue: {report_arg}")
