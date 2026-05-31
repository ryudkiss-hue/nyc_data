"""
Estimate the token count of a text file or string.

Uses a character-based approximation (4 chars ≈ 1 token for English prose,
3 chars ≈ 1 token for code/JSON) and warns when approaching common context limits.

Usage:
    python token_counter.py --input bundle.txt
    python token_counter.py --input bundle.txt --limit 100000
    python token_counter.py --text "Some text to count"
"""

import argparse
import sys
from pathlib import Path

CONTEXT_LIMITS = {
    "claude-3-haiku":  200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-opus":   200_000,
    "gpt-4o":          128_000,
    "gpt-4-turbo":     128_000,
    "default":         100_000,
}

LAYER_TRIM_ORDER = ["format", "constraints", "prior_findings", "schema", "business", "task"]


def estimate_tokens(text: str, is_code: bool = False) -> int:
    chars_per_token = 3.0 if is_code else 4.0
    return int(len(text) / chars_per_token)


def classify_text(text: str) -> bool:
    code_signals = ["{", "def ", "SELECT ", "CREATE TABLE", "import ", "```"]
    code_count = sum(text.count(s) for s in code_signals)
    return code_count > 10


def count_file(path: str) -> dict:
    content = Path(path).read_text(encoding="utf-8")
    is_code = classify_text(content)
    tokens = estimate_tokens(content, is_code)
    return {
        "file": path,
        "characters": len(content),
        "estimated_tokens": tokens,
        "type": "code/structured" if is_code else "prose",
    }


def main():
    parser = argparse.ArgumentParser(description="Estimate token count of text files.")
    parser.add_argument("--input", help="Path to file to count")
    parser.add_argument("--text", help="Text string to count")
    parser.add_argument("--limit", type=int, default=100_000,
                        help="Token budget to check against (default 100,000)")
    parser.add_argument("--model", choices=list(CONTEXT_LIMITS.keys()),
                        default="default", help="Model context limit to use")
    args = parser.parse_args()

    limit = CONTEXT_LIMITS.get(args.model, args.limit) if args.model != "default" else args.limit

    if args.input:
        result = count_file(args.input)
        tokens = result["estimated_tokens"]
        print(f"\nFile: {result['file']}")
        print(f"  Type: {result['type']}")
        print(f"  Characters: {result['characters']:,}")
        print(f"  Estimated tokens: ~{tokens:,}")
    elif args.text:
        is_code = classify_text(args.text)
        tokens = estimate_tokens(args.text, is_code)
        print(f"  Estimated tokens: ~{tokens:,}")
    else:
        parser.error("Provide --input or --text")
        return

    pct = tokens / limit * 100
    print(f"  Token budget: {limit:,} ({pct:.0f}% used)")

    if tokens > limit:
        print(f"  ⚠ OVER BUDGET by ~{tokens - limit:,} tokens")
        print(f"  Trimming priority: {' → '.join(LAYER_TRIM_ORDER)}")
    elif pct > 80:
        print(f"  ⚠ WARNING: above 80% of budget — consider trimming lower-priority layers")
    else:
        print(f"  ✓ Within budget")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sample = "This is a sample sentence. " * 1000
        tokens = estimate_tokens(sample)
        print(f"Sample ({len(sample):,} chars): ~{tokens:,} tokens")
        for model, limit in CONTEXT_LIMITS.items():
            pct = tokens / limit * 100
            print(f"  {model}: {pct:.1f}% of {limit:,} token limit")
    else:
        main()
