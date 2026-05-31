"""
Scan text for technical jargon that should be translated for business audiences.

Checks against a built-in list of data/stats/ML terms and flags each occurrence
with a suggested plain-language replacement.

Usage:
    python jargon_detector.py --input draft.txt
    python jargon_detector.py --text "The p-value was 0.03 and the model's RMSE improved."
    python jargon_detector.py --input draft.txt --output flagged.json
"""

import argparse
import json
import re
import sys

JARGON_MAP = {
    r"\bp[\s-]?value\b": "probability-of-chance result",
    r"\bstatistical(?:ly)?\s+significant\b": "unlikely to be random chance",
    r"\bconfidence interval\b": "likely range for the true value",
    r"\bstandard deviation\b": "typical spread around the average",
    r"\bstandard error\b": "uncertainty in the estimate",
    r"\bcorrelation coefficient\b": "strength of the relationship",
    r"\bregression\b": "predictive formula",
    r"\brmse\b": "average prediction error",
    r"\bmae\b": "average prediction error",
    r"\br[\s-]?squared\b": "how well the model fits the data",
    r"\bauc\b": "model accuracy score",
    r"\broc\b": "model performance curve",
    r"\bprecision\b(?!\s+of\s+a\s+measurement)": "share of predicted positives that are correct",
    r"\brecall\b": "share of actual positives the model catches",
    r"\bf1[\s-]?score\b": "balanced accuracy score",
    r"\bhyperparameter\b": "model setting",
    r"\bfeature importance\b": "which inputs drive the model most",
    r"\btraining\s+(?:set|data)\b": "historical data used to build the model",
    r"\btest\s+(?:set|data)\b": "held-out data used to evaluate the model",
    r"\boverfitting\b": "model memorised the training data and won't generalise",
    r"\bcross[\s-]?validation\b": "robustness check across multiple data splits",
    r"\boutlier\b": "unusually extreme data point",
    r"\bcohort\b": "group of users who started at the same time",
    r"\bfunnel\b": "step-by-step conversion sequence",
    r"\bgranularity\b": "level of detail",
    r"\baggregate(?:d)?\b": "combined / summed",
    r"\bnormalise(?:d)?\b": "adjusted for fair comparison",
    r"\bindex(?:ed)?\b(?!\s+to\b)": "scaled relative to a baseline",
    r"\blatency\b": "response time",
    r"\bthroughput\b": "volume processed per unit of time",
    r"\bcardinality\b": "number of unique values",
    r"\bsql\b": "database query",
    r"\betl\b": "data pipeline",
    r"\bdbt\b": "data transformation tool",
    r"\bapi\b": "data connection",
}


def detect_jargon(text: str) -> list[dict]:
    findings = []
    for pattern, suggestion in JARGON_MAP.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "term": match.group(),
                "position": match.start(),
                "suggestion": suggestion,
                "context": text[max(0, match.start() - 40): match.end() + 40].strip(),
            })
    findings.sort(key=lambda x: x["position"])
    return findings


def main():
    parser = argparse.ArgumentParser(description="Detect technical jargon in text.")
    parser.add_argument("--input", help="Path to text file")
    parser.add_argument("--text", help="Text string to check directly")
    parser.add_argument("--output", help="Optional path to write JSON report")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.error("Provide --input or --text")

    findings = detect_jargon(text)

    print(f"\nJargon Detector: {len(findings)} term(s) flagged")
    for f in findings:
        print(f"  [{f['term']}] → consider: \"{f['suggestion']}\"")
        print(f"    context: ...{f['context']}...")

    if args.output:
        with open(args.output, "w") as out:
            json.dump(findings, out, indent=2)
        print(f"\nReport written to {args.output}")

    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sample = (
            "The regression model achieved an AUC of 0.84. The p-value for the "
            "key feature was 0.02, indicating statistical significance. "
            "Feature importance showed that cohort age was the top predictor."
        )
        print(f"Sample text:\n  {sample}\n")
        findings = detect_jargon(sample)
        print(f"Flagged {len(findings)} term(s):")
        for f in findings:
            print(f"  [{f['term']}] → \"{f['suggestion']}\"")
    else:
        main()
