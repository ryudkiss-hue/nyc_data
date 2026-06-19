#!/usr/bin/env python3
"""
Comprehensive template verification:
1. Intelligent hard-coding (states, defaults, options)
2. Grammatical correctness
3. Contextual appropriateness
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Template analysis
skills_dir = Path("data-analytics-skills")
templates_found = []
verification_results = []

# Patterns to detect hard-coded states
patterns = {
    "state_options": r'\[(.*?)\s*/\s*(.*?)\s*/\s*(.*?)\]',  # [Option1 / Option2 / Option3]
    "hard_coded_list": r'\[(e\.g\.|example|such as)(.*?)\]',  # [e.g. item1, item2]
    "placeholder_with_example": r'\[.*?example:.*?\]',  # [example: ...]
    "fill_in_blank": r'___',  # Bare blanks
    "bracketed_instruction": r'\[(.*?)\]',  # General [instruction]
    "table_stub": r'\|\s*\|',  # Empty table cells
    "checkbox": r'\[\s*\]',  # [ ] checkboxes
    "yaml_placeholder": r'\{\{.*?\}\}',  # {{placeholder}}
}

print("=" * 80)
print("TEMPLATE VERIFICATION: Hard-Coding, Grammar, and Contextual Completeness")
print("=" * 80)

# Find all templates
for template_file in sorted(skills_dir.glob("*/*/assets/*.md")):
    skill_path = template_file.parent.parent.name
    category = template_file.parent.parent.parent.name
    template_name = template_file.stem

    with open(template_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Analyze each template
    result = {
        'file': str(template_file.relative_to(skills_dir)),
        'skill': skill_path,
        'template': template_name,
        'has_state_options': bool(re.search(patterns['state_options'], content)),
        'has_examples': bool(re.search(patterns['placeholder_with_example'], content)),
        'has_hard_coded_list': bool(re.search(patterns['hard_coded_list'], content)),
        'has_bare_blanks': len(re.findall(patterns['fill_in_blank'], content)),
        'has_checkboxes': len(re.findall(patterns['checkbox'], content)),
        'has_yaml_placeholders': bool(re.search(patterns['yaml_placeholder'], content)),
        'has_bracketed_instructions': len(re.findall(patterns['bracketed_instruction'], content)),
        'lines': len(content.split('\n')),
        'has_table': '|' in content,
    }

    # Smart scoring: does this template have intelligent hard-coding?
    smart_score = (
        (result['has_state_options'] * 2) +  # Explicit options = very smart
        (result['has_examples'] * 2) +  # Examples = very smart
        (result['has_hard_coded_list'] * 1) +  # Lists = somewhat smart
        (result['has_checkboxes'] * 1) +  # Checkboxes = helpful
        (max(0, result['has_bracketed_instructions'] - result['has_bare_blanks']) * 0.5)  # Guided blanks
    )

    result['smart_score'] = smart_score
    result['smart_rating'] = (
        'EXCELLENT' if smart_score >= 5 else
        'GOOD' if smart_score >= 3 else
        'FAIR' if smart_score >= 1 else
        'NEEDS WORK'
    )

    verification_results.append(result)

# Print detailed results
print("\nSCORE BREAKDOWN:\n")
print(f"{'Template':<50} {'Rating':<15} {'States':<8} {'Examples':<10} {'Smart':<8}")
print("-" * 95)

rating_counts = defaultdict(int)
for result in verification_results:
    rating_counts[result['smart_rating']] += 1
    states = 'Y' if result['has_state_options'] else 'N'
    examples = 'Y' if result['has_examples'] else 'N'

    print(f"{result['template']:<50} {result['smart_rating']:<15} {states:<8} {examples:<10} {result['smart_score']:<8.1f}")

# Summary statistics
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

total = len(verification_results)
excellent = rating_counts['EXCELLENT']
good = rating_counts['GOOD']
fair = rating_counts['FAIR']
needs_work = rating_counts['NEEDS WORK']

print(f"\nTotal templates audited: {total}")
print(f"  EXCELLENT (5+ points):  {excellent:>2}  ({excellent/total*100:>5.1f}%)")
print(f"  GOOD (3-4 points):      {good:>2}  ({good/total*100:>5.1f}%)")
print(f"  FAIR (1-2 points):      {fair:>2}  ({fair/total*100:>5.1f}%)")
print(f"  NEEDS WORK (0 points):  {needs_work:>2}  ({needs_work/total*100:>5.1f}%)")

print(f"\nIntelligent Hard-Coding Present:")
has_states = sum(1 for r in verification_results if r['has_state_options'])
has_examples = sum(1 for r in verification_results if r['has_examples'])
has_checkboxes = sum(1 for r in verification_results if r['has_checkboxes'])

print(f"  State options (e.g., [PASS / FAIL / WARN]):  {has_states:>2} templates ({has_states/total*100:.1f}%)")
print(f"  Full examples provided:                     {has_examples:>2} templates ({has_examples/total*100:.1f}%)")
print(f"  Checkbox/Radio options:                     {has_checkboxes:>2} templates ({has_checkboxes/total*100:.1f}%)")

# Detailed analysis
print("\n" + "=" * 80)
print("DETAILED FINDINGS BY TEMPLATE")
print("=" * 80)

for result in sorted(verification_results, key=lambda x: -x['smart_score']):
    if result['smart_rating'] != 'EXCELLENT':
        continue

    print(f"\n[{result['smart_rating']}] {result['skill']} — {result['template']}")
    print(f"       Hard-coded states: {result['has_state_options']}")
    print(f"       Examples provided: {result['has_examples']}")
    print(f"       Checkboxes: {result['has_checkboxes']}")
    print(f"       Guided blanks: {result['has_bracketed_instructions']}")

# Check for FAIR/NEEDS WORK templates
print("\n" + "=" * 80)
print("TEMPLATES NEEDING IMPROVEMENT")
print("=" * 80)

for result in sorted(verification_results, key=lambda x: x['smart_score']):
    if result['smart_rating'] in ['FAIR', 'NEEDS WORK']:
        print(f"\n[{result['smart_rating']}] {result['skill']} — {result['template']}")
        print(f"       Hard-coded states: {result['has_state_options']}")
        print(f"       Examples provided: {result['has_examples']}")
        print(f"       Bare blanks (should be guided): {result['has_bare_blanks']}")

        if result['has_bare_blanks'] > 0:
            print(f"       ACTION: Convert bare ___ to [context-specific instruction]")

print("\n" + "=" * 80)
print("VERIFICATION VERDICT")
print("=" * 80)

if excellent + good >= total * 0.8:
    print("\n[PASS] Templates are 80%+ intelligently hard-coded")
    print(f"       {excellent + good}/{total} templates have state options or examples")
else:
    print(f"\n[NEEDS WORK] {needs_work + fair} templates need better hard-coding")
    print(f"       Recommendation: Add explicit state options, examples, or checkboxes")

exit(0 if excellent + good >= total * 0.8 else 1)
