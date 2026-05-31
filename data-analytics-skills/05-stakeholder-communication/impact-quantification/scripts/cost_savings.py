"""
Estimate cost savings from operational improvements.

Models:
  - headcount_efficiency: hours_saved * hourly_cost * headcount
  - error_reduction: error_rate_delta * cost_per_error * volume
  - infrastructure: current_cost * reduction_pct

Usage:
    python cost_savings.py --model headcount_efficiency \
        --hours-saved 5 --hourly-cost 80 --headcount 20 --periods 12
    python cost_savings.py --model error_reduction \
        --error-rate-current 0.05 --error-rate-new 0.01 \
        --cost-per-error 200 --volume 10000
"""

import argparse
import sys


def headcount_efficiency(hours_saved_per_person: float, hourly_cost: float,
                         headcount: int, periods: int = 12) -> dict:
    savings_per_period = hours_saved_per_person * hourly_cost * headcount
    return {
        "model": "headcount_efficiency",
        "savings_per_period": round(savings_per_period, 2),
        "savings_total": round(savings_per_period * periods, 2),
        "fte_equivalent": round(hours_saved_per_person * headcount / 160, 2),
        "periods": periods,
    }


def error_reduction(error_rate_current: float, error_rate_new: float,
                    cost_per_error: float, volume: float, periods: int = 12) -> dict:
    errors_avoided_per_period = (error_rate_current - error_rate_new) * volume
    savings_per_period = errors_avoided_per_period * cost_per_error
    return {
        "model": "error_reduction",
        "errors_avoided_per_period": round(errors_avoided_per_period, 1),
        "savings_per_period": round(savings_per_period, 2),
        "savings_total": round(savings_per_period * periods, 2),
        "periods": periods,
    }


def infrastructure(current_cost: float, reduction_pct: float, periods: int = 12) -> dict:
    savings_per_period = current_cost * reduction_pct
    return {
        "model": "infrastructure",
        "savings_per_period": round(savings_per_period, 2),
        "savings_total": round(savings_per_period * periods, 2),
        "new_cost_per_period": round(current_cost - savings_per_period, 2),
        "periods": periods,
    }


def main():
    parser = argparse.ArgumentParser(description="Estimate cost savings.")
    parser.add_argument("--model", required=True,
                        choices=["headcount_efficiency", "error_reduction", "infrastructure"])
    parser.add_argument("--hours-saved", type=float)
    parser.add_argument("--hourly-cost", type=float)
    parser.add_argument("--headcount", type=int)
    parser.add_argument("--error-rate-current", type=float)
    parser.add_argument("--error-rate-new", type=float)
    parser.add_argument("--cost-per-error", type=float)
    parser.add_argument("--volume", type=float)
    parser.add_argument("--current-cost", type=float)
    parser.add_argument("--reduction-pct", type=float)
    parser.add_argument("--periods", type=int, default=12)
    args = parser.parse_args()

    if args.model == "headcount_efficiency":
        result = headcount_efficiency(args.hours_saved, args.hourly_cost, args.headcount, args.periods)
    elif args.model == "error_reduction":
        result = error_reduction(args.error_rate_current, args.error_rate_new,
                                 args.cost_per_error, args.volume, args.periods)
    elif args.model == "infrastructure":
        result = infrastructure(args.current_cost, args.reduction_pct, args.periods)

    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("=== Headcount Efficiency ===")
        r = headcount_efficiency(hours_saved_per_person=5, hourly_cost=80, headcount=20, periods=12)
        print(f"  Annual savings: ${r['savings_total']:,.0f}")
        print(f"  FTE equivalent: {r['fte_equivalent']}")

        print("\n=== Error Reduction ===")
        r2 = error_reduction(error_rate_current=0.05, error_rate_new=0.01,
                             cost_per_error=200, volume=10000, periods=12)
        print(f"  Annual savings: ${r2['savings_total']:,.0f}")
    else:
        main()
