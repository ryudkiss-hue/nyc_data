#!/usr/bin/env python3
"""
Comprehensive template intelligence verification
Checks for: hard-coded states, examples, guided blanks, format specs
"""

import re
from pathlib import Path
from collections import defaultdict

skills_dir = Path("data-analytics-skills")
templates = sorted(skills_dir.glob("*/*/assets/*.md"))

results = []

print("=" * 100)
print("COMPREHENSIVE TEMPLATE INTELLIGENCE AUDIT")
print("=" * 100)
print(f"\nAuditing {len(templates)} templates...\n")

for template_file in templates:
    skill = template_file.parent.parent.name
    template_name = template_file.stem

    with open(template_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Intelligent detection patterns
    findings = {
        'skill': skill,
        'template': template_name,
        'file': template_file.name,
        'checks': {}
    }

    # Check 1: Explicit [Option / Option / Option] patterns
    state_patterns = re.findall(r'\[([A-Z][A-Za-z0-9\s]+(?:\s*/\s*[A-Z][A-Za-z0-9\s]+)+)\]', content)
    findings['checks']['explicit_states'] = len(state_patterns)

    # Check 2: HTML comment examples
    comment_examples = len(re.findall(r'<!--.*?example.*?-->', content, re.IGNORECASE | re.DOTALL))
    findings['checks']['comment_examples'] = comment_examples

    # Check 3: Inline examples (Example: ...)
    inline_examples = len(re.findall(r'[Ee]xample[s]?:\s*["\']?[^\n]+', content))
    findings['checks']['inline_examples'] = inline_examples

    # Check 4: Format specifications (YYYY-MM-DD, fourfour, etc.)
    format_specs = len(re.findall(r'(?:YYYY-MM-DD|format:|HH:MM|fourfour|UUID|email)', content))
    findings['checks']['format_specs'] = format_specs

    # Check 5: Checkbox/radio options [ ] or [X]
    checkboxes = len(re.findall(r'\[\s*[X\s]\s*\]', content))
    findings['checks']['checkboxes'] = checkboxes

    # Check 6: Hard-coded lists in tables
    table_rows = len(re.findall(r'\|\s*[A-Z][^|]*\|', content))
    findings['checks']['table_rows'] = table_rows

    # Check 7: Required/mandatory field markers
    required_markers = len(re.findall(r'\*\*required\*\*|\(required\)|\[required\]', content, re.IGNORECASE))
    findings['checks']['required_markers'] = required_markers

    # Check 8: Default values specified (default: X)
    defaults = len(re.findall(r'(?:default|Default):\s*[A-Za-z0-9]+', content))
    findings['checks']['default_values'] = defaults

    # Calculate intelligence score
    total_intelligence = (
        findings['checks']['explicit_states'] * 3 +
        findings['checks']['comment_examples'] * 2 +
        findings['checks']['inline_examples'] * 2 +
        findings['checks']['format_specs'] * 1 +
        findings['checks']['checkboxes'] * 1 +
        findings['checks']['table_rows'] * 0.5 +
        findings['checks']['required_markers'] * 2 +
        findings['checks']['default_values'] * 2
    )

    findings['intelligence_score'] = total_intelligence
    findings['rating'] = (
        'EXCELLENT' if total_intelligence >= 10 else
        'GOOD' if total_intelligence >= 5 else
        'FAIR' if total_intelligence >= 2 else
        'BASIC'
    )

    results.append(findings)

# Sort by intelligence score
results_sorted = sorted(results, key=lambda x: -x['intelligence_score'])

# Display results
print(f"{'Template':<45} {'Rating':<10} {'States':<8} {'Examples':<12} {'Specs':<8} {'Score':<8}")
print("-" * 100)

for r in results_sorted:
    states = r['checks']['explicit_states']
    examples = r['checks']['inline_examples'] + r['checks']['comment_examples']
    specs = r['checks']['format_specs']
    score = f"{r['intelligence_score']:.1f}"

    print(f"{r['template']:<45} {r['rating']:<10} {states:<8} {examples:<12} {specs:<8} {score:<8}")

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

ratings_count = defaultdict(int)
for r in results:
    ratings_count[r['rating']] += 1

total = len(results)
excellent = ratings_count['EXCELLENT']
good = ratings_count['GOOD']
fair = ratings_count['FAIR']
basic = ratings_count['BASIC']

print(f"\nTotal templates: {total}")
print(f"  EXCELLENT (10+ points): {excellent:>2} ({excellent/total*100:>5.1f}%)")
print(f"  GOOD (5-9 points):      {good:>2} ({good/total*100:>5.1f}%)")
print(f"  FAIR (2-4 points):      {fair:>2} ({fair/total*100:>5.1f}%)")
print(f"  BASIC (0-1 points):     {basic:>2} ({basic/total*100:>5.1f}%)")

print(f"\nIntelligent Hard-Coding Coverage:")
total_states = sum(r['checks']['explicit_states'] for r in results)
total_examples = sum(r['checks']['inline_examples'] + r['checks']['comment_examples'] for r in results)
total_specs = sum(r['checks']['format_specs'] for r in results)

print(f"  Explicit state options [A / B / C]:  {sum(1 for r in results if r['checks']['explicit_states'] > 0):>2} templates")
print(f"  Examples (inline or comment):        {sum(1 for r in results if total_examples > 0):>2} templates (total: {total_examples} examples)")
print(f"  Format specifications:                {sum(1 for r in results if r['checks']['format_specs'] > 0):>2} templates (total: {total_specs} specs)")

print(f"\nOverall Assessment:")
if excellent + good >= total * 0.75:
    print(f"[PASS] {excellent + good}/{total} templates ({(excellent+good)/total*100:.1f}%) have excellent/good intelligence")
    print(f"       Templates are intelligently hard-coded with states, examples, and format specs")
    exit(0)
else:
    print(f"[REVIEW] {excellent + good}/{total} templates rated EXCELLENT/GOOD")
    print(f"         {fair + basic} templates may benefit from additional hard-coding")
    exit(1)
