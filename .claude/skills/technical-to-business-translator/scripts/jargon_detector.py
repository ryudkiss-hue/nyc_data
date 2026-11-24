"""
jargon_detector.py — Flag technical jargon in analyst text and suggest plain-language replacements.

Scores readability, flags statistical/data-science terms, and reports grade level.
Targets grade-10 readability for NYC DOT non-technical audiences.

Usage:
    python jargon_detector.py --file findings.md
    python jargon_detector.py --text "The model is statistically significant at p<0.05 with an AUC of 0.87"
    python jargon_detector.py --file report.md --output-clean cleaned_report.md
"""

import argparse
import re
import sys
from pathlib import Path

# Technical terms and their plain-language replacements
JARGON_DICT = {
    # Statistical
    r"\bp[\s-]?value[s]?\b": "probability of chance / confidence level",
    r"\bstatistically significant\b": "real and not due to random chance",
    r"\bconfidence interval[s]?\b": "margin of error / likely range",
    r"\bstandard deviation\b": "typical spread",
    r"\bvariance\b": "spread / variability",
    r"\bregression\b": "prediction model",
    r"\bcorrelation\b": "relationship between",
    r"\boutlier[s]?\b": "unusually high or low value(s)",
    r"\bnull hypothesis\b": "assumption being tested",
    r"\bstatistical power\b": "ability to detect a real difference",
    r"\bAUC\b": "model accuracy score",
    r"\bROC curve\b": "model accuracy chart",
    r"\bR-squared\b": "how well the model fits",
    r"\bp\s*<\s*0\.0[0-9]+": "statistically confirmed (95%+ confidence)",
    r"\bWilson Score\b": "margin of error (small-sample adjusted)",
    r"\bBayesian\b": "probability-based estimate using prior knowledge",
    r"\bMoran'?s I\b": "geographic clustering measure",
    r"\bDBSCAN\b": "geographic grouping algorithm",
    r"\bKMeans?\b": "automatic grouping method",
    r"\bCUSUM\b": "running trend alarm",
    r"\bsurvival (analysis|curve)\b": "time-to-resolution analysis",
    r"\bheteroskedastic\b": "unevenly spread values",
    # Data engineering
    r"\bETL\b": "data pipeline",
    r"\bSOQL\b": "database query",
    r"\bParquet\b": "data file format",
    r"\bDuckDB\b": "local database",
    r"\bschema\b": "data structure / column layout",
    r"\bfour[- ]?four\b": "dataset ID",
    r"\bAPI\b": "data connection",
    r"\bcache\b": "saved local copy",
    r"\bdelta fetch\b": "incremental data update",
    r"\bCDC\b": "change tracking",
    r"\blineage\b": "data history trail",
    r"\bupsert\b": "insert or update",
    # DOT-specific technical
    r"\bSLA\b": "data freshness deadline",
    r"\bSIM unit\b": "NYC DOT inspection program",
    r"\bSocrata\b": "NYC Open Data platform",
    r"\bthe_geom\b": "geographic location field",
    r"\bWGS84\b": "standard GPS coordinate system",
    r"\bEPSG:2263\b": "New York projection (feet)",
    r"\bTSP\b": "shortest-route calculation",
    r"\bthe fourfour\b": "dataset identifier code",
}


# Readability: approximate Flesch-Kincaid grade level
def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def sentence_count(text: str) -> int:
    return max(1, len(re.findall(r"[.!?]+", text)))


def syllable_count(word: str) -> int:
    word = word.lower().rstrip("e")
    count = len(re.findall(r"[aeiou]+", word))
    return max(1, count)


def flesch_kincaid_grade(text: str) -> float:
    words = re.findall(r"\b\w+\b", text)
    sentences = sentence_count(text)
    syllables = sum(syllable_count(w) for w in words)
    wc = len(words)
    if wc == 0 or sentences == 0:
        return 0.0
    return 0.39 * (wc / sentences) + 11.8 * (syllables / wc) - 15.59


def detect_jargon(text: str) -> list[dict]:
    findings = []
    for pattern, replacement in JARGON_DICT.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(
                {
                    "term": match.group(0),
                    "position": match.start(),
                    "suggestion": replacement,
                    "pattern": pattern,
                }
            )
    # Deduplicate by term (case-insensitive)
    seen = set()
    unique = []
    for f in sorted(findings, key=lambda x: x["position"]):
        key = f["term"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def apply_replacements(text: str, findings: list[dict]) -> str:
    result = text
    for f in findings:
        result = re.sub(f["pattern"], f["suggestion"], result, flags=re.IGNORECASE)
    return result


def print_report(text: str, findings: list[dict], grade: float):
    print(f"\n{'=' * 60}")
    print("NYC DOT Jargon Detection Report")
    print(f"{'=' * 60}")
    print(f"Words: {word_count(text)}  |  Sentences: {sentence_count(text)}")
    print(f"Flesch-Kincaid Grade Level: {grade:.1f}  (target: ≤ 10.0)")
    if grade <= 10:
        print("Readability: PASS")
    else:
        print("Readability: ABOVE TARGET — simplify sentence structure")
    print()

    if not findings:
        print("Jargon check: PASS — no flagged terms found.")
    else:
        print(f"Jargon check: {len(findings)} term(s) flagged:\n")
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] '{f['term']}'")
            print(f'       → Replace with: "{f["suggestion"]}"')
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="NYC DOT jargon detector and readability scorer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to text/markdown file to check")
    group.add_argument("--text", help="Inline text string to check")
    parser.add_argument("--output-clean", help="Write jargon-replaced version to this path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()
    else:
        text = args.text

    findings = detect_jargon(text)
    grade = flesch_kincaid_grade(text)

    if args.as_json:
        import json

        print(
            json.dumps(
                {
                    "grade_level": round(grade, 2),
                    "word_count": word_count(text),
                    "jargon_count": len(findings),
                    "findings": findings,
                },
                indent=2,
            )
        )
    else:
        print_report(text, findings, grade)

    if args.output_clean:
        cleaned = apply_replacements(text, findings)
        Path(args.output_clean).write_text(cleaned)
        print(f"Cleaned version written to: {args.output_clean}")

    sys.exit(0 if (not findings and grade <= 10) else 1)


if __name__ == "__main__":
    main()
