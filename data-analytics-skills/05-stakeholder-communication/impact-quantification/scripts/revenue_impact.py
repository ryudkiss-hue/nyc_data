"""
Estimate revenue impact of a proposed change.

Models:
  - conversion_lift: baseline_volume * lift_pct * avg_order_value
  - retention_improvement: saved_customers * avg_ltv
  - upsell: eligible_base * take_rate * incremental_arpu

Usage:
    python revenue_impact.py --model conversion_lift \
        --baseline-volume 10000 --lift-pct 0.02 --avg-order-value 85 --periods 12
    python revenue_impact.py --model retention_improvement \
        --saved-customers 500 --avg-ltv 1200
"""

import argparse
import sys


def conversion_lift(baseline_volume: float, lift_pct: float, avg_order_value: float,
                    periods: int = 12) -> dict:
    incremental_conversions = baseline_volume * lift_pct
    monthly_revenue = incremental_conversions * avg_order_value
    return {
        "model": "conversion_lift",
        "incremental_conversions_per_period": round(incremental_conversions, 1),
        "incremental_revenue_per_period": round(monthly_revenue, 2),
        "incremental_revenue_total": round(monthly_revenue * periods, 2),
        "periods": periods,
        "assumptions": {
            "baseline_volume": baseline_volume,
            "lift_pct": lift_pct,
            "avg_order_value": avg_order_value,
        },
    }


def retention_improvement(saved_customers: float, avg_ltv: float,
                           discount_rate: float = 0.0) -> dict:
    gross_impact = saved_customers * avg_ltv
    discounted_impact = gross_impact / (1 + discount_rate) if discount_rate > 0 else gross_impact
    return {
        "model": "retention_improvement",
        "saved_customers": saved_customers,
        "gross_ltv_impact": round(gross_impact, 2),
        "discounted_ltv_impact": round(discounted_impact, 2),
        "discount_rate": discount_rate,
        "assumptions": {
            "saved_customers": saved_customers,
            "avg_ltv": avg_ltv,
        },
    }


def upsell(eligible_base: float, take_rate: float, incremental_arpu: float,
           periods: int = 12) -> dict:
    adopters = eligible_base * take_rate
    monthly_revenue = adopters * incremental_arpu
    return {
        "model": "upsell",
        "expected_adopters": round(adopters, 1),
        "incremental_revenue_per_period": round(monthly_revenue, 2),
        "incremental_revenue_total": round(monthly_revenue * periods, 2),
        "periods": periods,
        "assumptions": {
            "eligible_base": eligible_base,
            "take_rate": take_rate,
            "incremental_arpu": incremental_arpu,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Estimate revenue impact.")
    parser.add_argument("--model", required=True,
                        choices=["conversion_lift", "retention_improvement", "upsell"])
    parser.add_argument("--baseline-volume", type=float)
    parser.add_argument("--lift-pct", type=float)
    parser.add_argument("--avg-order-value", type=float)
    parser.add_argument("--periods", type=int, default=12)
    parser.add_argument("--saved-customers", type=float)
    parser.add_argument("--avg-ltv", type=float)
    parser.add_argument("--discount-rate", type=float, default=0.0)
    parser.add_argument("--eligible-base", type=float)
    parser.add_argument("--take-rate", type=float)
    parser.add_argument("--incremental-arpu", type=float)
    args = parser.parse_args()

    if args.model == "conversion_lift":
        result = conversion_lift(args.baseline_volume, args.lift_pct, args.avg_order_value, args.periods)
    elif args.model == "retention_improvement":
        result = retention_improvement(args.saved_customers, args.avg_ltv, args.discount_rate)
    elif args.model == "upsell":
        result = upsell(args.eligible_base, args.take_rate, args.incremental_arpu, args.periods)

    for k, v in result.items():
        if k != "assumptions":
            print(f"  {k}: {v}")
    print(f"  assumptions: {result['assumptions']}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("=== Conversion Lift ===")
        r = conversion_lift(baseline_volume=10000, lift_pct=0.02, avg_order_value=85, periods=12)
        print(f"  Incremental revenue/month: ${r['incremental_revenue_per_period']:,.0f}")
        print(f"  Annual impact: ${r['incremental_revenue_total']:,.0f}")

        print("\n=== Retention Improvement ===")
        r2 = retention_improvement(saved_customers=500, avg_ltv=1200)
        print(f"  Gross LTV impact: ${r2['gross_ltv_impact']:,.0f}")
    else:
        main()
