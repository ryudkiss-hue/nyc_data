"""
Produce low/base/high impact estimates using assumption uncertainty ranges.

Given a base estimate and a coefficient of variation (or explicit low/high multipliers),
computes a credible range for communication.

Usage:
    python confidence_interval.py --base 500000 --cv 0.3
    python confidence_interval.py --base 500000 --low-mult 0.5 --high-mult 1.8
    python confidence_interval.py --base 500000 --confidence low
"""

import argparse
import sys


CONFIDENCE_PRESETS = {
    "high":   {"low_mult": 0.8,  "high_mult": 1.2,  "label": "High confidence (±20%)"},
    "medium": {"low_mult": 0.6,  "high_mult": 1.6,  "label": "Medium confidence (−40% / +60%)"},
    "low":    {"low_mult": 0.3,  "high_mult": 2.5,  "label": "Low confidence (−70% / +150%)"},
}


def build_range(base: float, low_mult: float = None, high_mult: float = None,
                cv: float = None, confidence: str = None) -> dict:
    if confidence:
        preset = CONFIDENCE_PRESETS[confidence]
        low_mult = preset["low_mult"]
        high_mult = preset["high_mult"]
        label = preset["label"]
    elif cv:
        # Treat CV as 1-sigma; use ±2 sigma for low/high
        low_mult = max(0, 1 - 2 * cv)
        high_mult = 1 + 2 * cv
        label = f"CV-based range (CV={cv:.0%})"
    else:
        label = "Custom range"

    return {
        "base_estimate": round(base, 2),
        "low_estimate": round(base * low_mult, 2),
        "high_estimate": round(base * high_mult, 2),
        "range_label": label,
        "low_multiplier": round(low_mult, 3),
        "high_multiplier": round(high_mult, 3),
    }


def format_currency(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def main():
    parser = argparse.ArgumentParser(description="Build low/base/high impact range.")
    parser.add_argument("--base", type=float, required=True, help="Base (most likely) estimate")
    parser.add_argument("--cv", type=float, help="Coefficient of variation (e.g. 0.3 = 30%%)")
    parser.add_argument("--low-mult", type=float, help="Low-end multiplier (e.g. 0.5)")
    parser.add_argument("--high-mult", type=float, help="High-end multiplier (e.g. 1.8)")
    parser.add_argument("--confidence", choices=["high", "medium", "low"],
                        help="Preset confidence level")
    args = parser.parse_args()

    result = build_range(args.base, args.low_mult, args.high_mult, args.cv, args.confidence)

    print(f"\nImpact Range ({result['range_label']})")
    print(f"  Low:  {format_currency(result['low_estimate'])}")
    print(f"  Base: {format_currency(result['base_estimate'])}")
    print(f"  High: {format_currency(result['high_estimate'])}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for conf in ["high", "medium", "low"]:
            r = build_range(base=500_000, confidence=conf)
            print(f"{r['range_label']}: {format_currency(r['low_estimate'])} — "
                  f"{format_currency(r['base_estimate'])} — {format_currency(r['high_estimate'])}")
    else:
        main()
