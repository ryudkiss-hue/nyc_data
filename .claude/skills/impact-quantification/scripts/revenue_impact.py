"""
revenue_impact.py — Estimate compliance revenue impact and fee recovery for NYC DOT SIM.

Models low/base/high ranges for:
- Increased violation fee collection from improved closure/compliance rates
- Avoided penalty costs from SLA breach reduction
- Value of faster ramp completion (accessibility compliance, federal funding eligibility)

Usage:
    python revenue_impact.py --scenario violation-fee-recovery
    python revenue_impact.py --open-violations 5200 --avg-fee 900 \
        --current-closure-rate 0.68 --target-closure-rate 0.80
    python revenue_impact.py --list-scenarios
"""

import argparse
import json
from dataclasses import asdict, dataclass

PRESET_SCENARIOS = {
    "violation-fee-recovery": {
        "description": "Increase violation closure rate from 68% to 80%, recovering additional fee revenue",
        "open_violations": 5200,
        "avg_fee_usd": 900,
        "current_closure_rate": 0.68,
        "target_closure_rate": 0.80,
    },
    "sla-breach-avoidance": {
        "description": "Reduce SLA breaches from 22% to 8% of datasets, avoiding compliance risk",
        "open_violations": 26,  # number of monitored datasets
        "avg_fee_usd": 15000,  # estimated compliance/remediation cost per breach
        "current_closure_rate": 0.78,  # pct datasets within SLA
        "target_closure_rate": 0.92,
    },
    "ramp-federal-funding": {
        "description": "Achieve 85% ADA ramp completion to unlock federal accessibility funding tier",
        "open_violations": 187000,  # ramp_progress total ~187K
        "avg_fee_usd": 1.20,  # per-ramp federal reimbursement rate (estimate)
        "current_closure_rate": 0.72,
        "target_closure_rate": 0.85,
    },
}


@dataclass
class RevenueImpactEstimate:
    initiative: str
    additional_units_closed: float
    incremental_revenue_low_usd: float
    incremental_revenue_base_usd: float
    incremental_revenue_high_usd: float
    current_annual_revenue_usd: float
    target_annual_revenue_usd: float
    pct_increase: float
    assumptions: list[str]


def compute_revenue_impact(
    initiative: str,
    open_violations: int,
    avg_fee_usd: float,
    current_closure_rate: float,
    target_closure_rate: float,
    uncertainty_pct: float = 0.25,
) -> RevenueImpactEstimate:
    current_closed = open_violations * current_closure_rate
    target_closed = open_violations * target_closure_rate
    additional_units = target_closed - current_closed

    current_revenue = current_closed * avg_fee_usd
    target_revenue = target_closed * avg_fee_usd
    incremental_base = additional_units * avg_fee_usd
    incremental_low = incremental_base * (1 - uncertainty_pct)
    incremental_high = incremental_base * (1 + uncertainty_pct)

    pct_increase = (
        ((target_revenue - current_revenue) / current_revenue * 100) if current_revenue else 0
    )

    assumptions = [
        f"Total addressable units: {open_violations:,}",
        f"Current closure rate: {current_closure_rate:.0%} → Target: {target_closure_rate:.0%}",
        f"Average fee / value per unit: ${avg_fee_usd:,.2f}",
        f"Additional units closed: {additional_units:,.0f}",
        f"Uncertainty band: ±{uncertainty_pct:.0%} applied to base estimate",
        "Assumes all additional closures result in fee collection (no write-offs modeled)",
        "Does not account for appeals, waivers, or payment plans",
        "Revenue realized in the same fiscal year as closures",
    ]

    return RevenueImpactEstimate(
        initiative=initiative,
        additional_units_closed=additional_units,
        incremental_revenue_low_usd=incremental_low,
        incremental_revenue_base_usd=incremental_base,
        incremental_revenue_high_usd=incremental_high,
        current_annual_revenue_usd=current_revenue,
        target_annual_revenue_usd=target_revenue,
        pct_increase=pct_increase,
        assumptions=assumptions,
    )


def print_report(est: RevenueImpactEstimate):
    print(f"\n{'=' * 60}")
    print("NYC DOT Revenue / Value Impact Estimate")
    print(f"Initiative: {est.initiative}")
    print(f"{'=' * 60}")
    print(f"Additional units closed:  {est.additional_units_closed:>10,.0f}")
    print()
    print(f"{'Metric':<35} {'Amount':>12}")
    print(f"{'-' * 50}")
    print(f"{'Current annual revenue/value':<35} ${est.current_annual_revenue_usd:>11,.0f}")
    print(f"{'Target annual revenue/value':<35} ${est.target_annual_revenue_usd:>11,.0f}")
    print(f"{'Increase':<35} {est.pct_increase:>10.1f}%")
    print()
    print(f"{'Incremental Impact Range':<35} {'Low':>10} {'Base':>10} {'High':>10}")
    print(f"{'-' * 65}")
    print(
        f"{'Revenue / value gain':<35} "
        f"${est.incremental_revenue_low_usd:>9,.0f} "
        f"${est.incremental_revenue_base_usd:>9,.0f} "
        f"${est.incremental_revenue_high_usd:>9,.0f}"
    )
    print(f"\nBase estimate: ${est.incremental_revenue_base_usd:,.0f}")
    print(
        f"Range: ${est.incremental_revenue_low_usd:,.0f} – ${est.incremental_revenue_high_usd:,.0f}"
    )
    print("\nAssumptions:")
    for a in est.assumptions:
        print(f"  • {a}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="NYC DOT revenue / value impact estimator")
    parser.add_argument("--initiative", help="Initiative name")
    parser.add_argument("--open-violations", type=int, help="Total addressable units")
    parser.add_argument("--avg-fee", type=float, help="Average fee or value per unit (USD)")
    parser.add_argument("--current-closure-rate", type=float, help="Current closure rate (0–1)")
    parser.add_argument("--target-closure-rate", type=float, help="Target closure rate (0–1)")
    parser.add_argument(
        "--uncertainty",
        type=float,
        default=0.25,
        help="Uncertainty band as decimal (default 0.25 = ±25%%)",
    )
    parser.add_argument("--scenario", choices=list(PRESET_SCENARIOS.keys()))
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.list_scenarios:
        for key, s in PRESET_SCENARIOS.items():
            print(f"  {key}: {s['description']}")
        return

    if args.scenario:
        s = PRESET_SCENARIOS[args.scenario]
        est = compute_revenue_impact(
            initiative=s["description"],
            open_violations=s["open_violations"],
            avg_fee_usd=s["avg_fee_usd"],
            current_closure_rate=s["current_closure_rate"],
            target_closure_rate=s["target_closure_rate"],
        )
    else:
        required = [
            "initiative",
            "open_violations",
            "avg_fee",
            "current_closure_rate",
            "target_closure_rate",
        ]
        missing = [r for r in required if getattr(args, r.replace("-", "_"), None) is None]
        if missing:
            parser.error(f"Missing: {missing}. Or use --scenario.")
        est = compute_revenue_impact(
            initiative=args.initiative,
            open_violations=args.open_violations,
            avg_fee_usd=args.avg_fee,
            current_closure_rate=args.current_closure_rate,
            target_closure_rate=args.target_closure_rate,
            uncertainty_pct=args.uncertainty,
        )

    if args.as_json:
        print(json.dumps(asdict(est), indent=2))
    else:
        print_report(est)


if __name__ == "__main__":
    main()
