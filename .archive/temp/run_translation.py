#!/usr/bin/env python3
"""
Simulate the technical-to-business-translator workflow
"""

import re
from pathlib import Path

# Jargon dictionary (from the skill)
JARGON_DICT = {
    r'\bp[\s-]?value[s]?\b': 'probability of chance',
    r'\bstatistically significant\b': 'real and not due to random chance',
    r'\bconfidence interval[s]?\b': 'margin of error',
    r'\bstandard error\b': 'margin of error',
    r'\bregression\b': 'prediction model',
    r'\boutlier[s]?\b': 'unusually extreme value(s)',
    r'\bnull hypothesis\b': 'assumption being tested',
    r'\bAUC\b': 'model accuracy score',
    r'\bOLS\b': 'standard regression method',
    r'\bHuber-White\b': 'robust regression method',
    r'\bBreusch-Pagan\b': 'statistical test',
    r'\bDurbin-Watson\b': 'autocorrelation measure',
    r'\bADF test\b': 'stationarity test',
    r'\bARIMA\b': 'forecasting model',
    r'\bIQR\b': 'middle 50 percent range',
    r'\bheteroskedastic[ity]?\b': 'uneven spread',
    r'\bSocrata\b': 'NYC Open Data platform',
    r'\bschema drift\b': 'unexpected data format change',
}

print("=" * 70)
print("STEP 1: DETECT JARGON IN TECHNICAL REPORT")
print("=" * 70)

# Read the technical report
text = Path('technical_report.md').read_text()

# Find jargon
findings = []
seen_terms = set()

for pattern, replacement in JARGON_DICT.items():
    for match in re.finditer(pattern, text, re.IGNORECASE):
        term = match.group(0)
        if term.lower() not in seen_terms:
            findings.append({
                'term': term,
                'suggestion': replacement,
                'pattern': pattern,
            })
            seen_terms.add(term.lower())

print(f"\nFound {len(findings)} jargon terms:\n")
for i, f in enumerate(findings, 1):
    print(f"  [{i}] '{f['term']}'")
    print(f"       -> Replace with: \"{f['suggestion']}\"")

print("\n" + "=" * 70)
print("STEP 2: CREATE CLEANED VERSION")
print("=" * 70)

# Apply replacements
cleaned_text = text
for f in findings:
    cleaned_text = re.sub(
        f['pattern'],
        f"[{f['suggestion']}]",
        cleaned_text,
        flags=re.IGNORECASE
    )

Path('cleaned_report.md').write_text(cleaned_text)
print("\n[OK] Cleaned version saved to: cleaned_report.md")

print("\n" + "=" * 70)
print("STEP 3: SHOW BEFORE/AFTER EXCERPT")
print("=" * 70)

# Show a sample of the before/after
print("\n--- BEFORE (Technical) ---")
print(text[200:400])

print("\n--- AFTER (Cleaned) ---")
print(cleaned_text[200:400])

print("\n" + "=" * 70)
print("READABILITY SCORE")
print("=" * 70)

# Calculate readability
def word_count(text):
    return len(re.findall(r'\b\w+\b', text))

def sentence_count(text):
    return max(1, len(re.findall(r'[.!?]+', text)))

def syllable_count(word):
    word = word.lower().rstrip('e')
    count = len(re.findall(r'[aeiou]+', word))
    return max(1, count)

def flesch_kincaid_grade(text):
    words = re.findall(r'\b\w+\b', text)
    sentences = sentence_count(text)
    syllables = sum(syllable_count(w) for w in words)
    wc = len(words)
    if wc == 0 or sentences == 0:
        return 0.0
    return 0.39 * (wc / sentences) + 11.8 * (syllables / wc) - 15.59

original_grade = flesch_kincaid_grade(text)
cleaned_grade = flesch_kincaid_grade(cleaned_text)

print(f"\nOriginal grade level: {original_grade:.1f} (TARGET: <= 10.0)")
print(f"Cleaned grade level: {cleaned_grade:.1f}")

if cleaned_grade <= 10:
    print("[PASS] Meets readability target")
else:
    print("[WARN] ABOVE TARGET: Simplify sentence structure further")

print("\nNext step: Fill template with cleaned text + business implications")
