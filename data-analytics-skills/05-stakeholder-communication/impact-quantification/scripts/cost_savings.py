"""
cost_savings.py — Estimate cost savings and efficiency impact for NYC DOT SIM initiatives.

Models low/base/high ranges for efficiency gains (inspector time, violation backlog reduction,
ramp completion acceleration) and operational cost avoidance.

Usage:
    python cost_savings.py --initiative "Reduce inspection backlog" \
        --current-backlog 12000 --target-backlog 8000 \
        --cost-per-unit 350 --hours-per-unit 2.5 \
        --inspector-hourly-rate 45
    python cost_savings.py --list-scenarios
"""

import argparse
import json
from dataclasses import asdict, dataclass

PRESET_SCENARIOS = {
    "inspection-backlog-reduction": {
        "description": "Reduce open inspection backlog by routing inspectors more efficiently",
        "current_backlog": 12000,
        "target_backlog": 8000,
        "cost_per_unit_usd": 350,
        "hours_per_unit": 2.5,
        "inspector_hourly_rate_usd": 45,
    },
    "violation-closure-improvement": {
        "description": "Increase violation closure rate from 68% to 80% in 90 days",
        "current_backlog": 5200,
        "target_backlog": 3100,
        "cost_per_unit_usd": 520,
        "hours_per_unit": 3.0,
        "inspector_hourly_rate_usd": 45,
    },
    "ramp-completion-acceleration": {
        "description": "Accelerate ramp program completions by 15% through better scheduling",
        "current_backlog": 2800,
        "target_backlog": 2380,
        "cost_per_unit_usd": 1200,
        "hours_per_unit": 8.0,
        "inspector_hourly_rate_usd": 55,
    },
}


@dataclass
class CostSavingsEstimate:
    initiative: str
    units_reduced: int
    # Direct cost avoidance
    direct_savings_low_usd: float
    direct_savings_base_usd: float
    direct_savings_high_usd: float
    # Labor hours recovered
    labor_hours_recovered: float
    labor_cost_recovered_usd: float
    # Total
    total_savings_low_usd: float
    total_savings_base_usd: float
    total_savings_high_usd: float
    assumptions: list[str]


def compute_savings(
    initiative: str,
    current_backlog: int,
    target_backlog: int,
    cost_per_unit_usd: float,
    hours_per_unit: float,
    inspector_hourly_rate_usd: float,
    uncertainty_pct: float = 0.20,
) -> CostSavingsEstimate:
    units_reduced = max(0, current_backlog - target_backlog)

    direct_base = units_reduced * cost_per_unit_usd
    direct_low = direct_base * (1 - uncertainty_pct)
    direct_high = direct_base * (1 + uncertainty_pct)

    labor_hours = units_reduced * hours_per_unit
    labor_cost = labor_hours * inspector_hourly_rate_usd

    total_base = direct_base + labor_cost
    total_low = direct_low + labor_cost * (1 - uncertainty_pct)
    total_high = direct_high + labor_cost * (1 + uncertainty_pct)

    assumptions = [
        f"Units reduced: {units_reduced:,} ({current_backlog:,} → {target_backlog:,})",
        f"Cost per unit: ${cost_per_unit_usd:,.0f} (direct costs: materials, admin, follow-up)",
        f"Hours per unit: {hours_per_unit} inspector-hours",
        f"Inspector fully-loaded hourly rate: ${inspector_hourly_rate_usd:.2f}/hr",
        f"Uncertainty band: ±{uncertainty_pct:.0%} applied to base estimate",
        "Savings assumed realized within fiscal year unless noted",
        "Does not include capital expenditure, overtime, or contractor costs",
    ]

    return CostSavingsEstimate(
        initiative=initiative,
        units_reduced=units_reduced,
        direct_savings_low_usd=direct_low,
        direct_savings_base_usd=direct_base,
        direct_savings_high_usd=direct_high,
        labor_hours_recovered=labor_hours,
        labor_cost_recovered_usd=labor_cost,
        total_savings_low_usd=total_low,
        total_savings_base_usd=total_base,
        total_savings_high_usd=total_high,
        assumptions=assumptions,
    )


def print_report(est: CostSavingsEstimate):
    print(f"\n{'=' * 60}")
    print("NYC DOT Cost Savings Estimate")
    print(f"Initiative: {est.initiative}")
    print(f"{'=' * 60}")
    print(f"Units reduced:            {est.units_reduced:>10,}")
    print(f"Labor hours recovered:    {est.labor_hours_recovered:>10,.0f} hrs")
    print()
    print(f"{'Component':<30} {'Low':>10} {'Base':>10} {'High':>10}")
    print(f"{'-' * 60}")
    print(
        f"{'Direct cost avoidance':<30} "
        f"${est.direct_savings_low_usd:>9,.0f} "
        f"${est.direct_savings_base_usd:>9,.0f} "
        f"${est.direct_savings_high_usd:>9,.0f}"
    )
    print(
        f"{'Labor cost recovered':<30} "
        f"${est.labor_cost_recovered_usd:>9,.0f} "
        f"${est.labor_cost_recovered_usd:>9,.0f} "
        f"${est.labor_cost_recovered_usd:>9,.0f}"
    )
    print(f"{'-' * 60}")
    print(
        f"{'TOTAL SAVINGS':<30} "
        f"${est.total_savings_low_usd:>9,.0f} "
        f"${est.total_savings_base_usd:>9,.0f} "
        f"${est.total_savings_high_usd:>9,.0f}"
    )
    print(f"\nBase estimate: ${est.total_savings_base_usd:,.0f}")
    print(f"Range: ${est.total_savings_low_usd:,.0f} – ${est.total_savings_high_usd:,.0f}")
    print("\nAssumptions:")
    for a in est.assumptions:
        print(f"  • {a}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="NYC DOT cost savings estimator")
    parser.add_argument("--initiative", help="Name of the initiative")
    parser.add_argument(
        "--current-backlog", type=int, help="Current unit count (before improvement)"
    )
    parser.add_argument("--target-backlog", type=int, help="Target unit count (after improvement)")
    parser.add_argument("--cost-per-unit", type=float, help="Direct cost per unit resolved (USD)")
    parser.add_argument("--hours-per-unit", type=float, help="Inspector hours per unit resolved")
    parser.add_argument(
        "--inspector-hourly-rate",
        type=float,
        default=45.0,
        help="Fully-loaded inspector hourly rate (default $45/hr)",
    )
    parser.add_argument(
        "--uncertainty",
        type=float,
        default=0.20,
        help="Uncertainty band as decimal (default 0.20 = ±20%%)",
    )
    parser.add_argument(
        "--scenario", choices=list(PRESET_SCENARIOS.keys()), help="Use a preset scenario"
    )
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.list_scenarios:
        for key, s in PRESET_SCENARIOS.items():
            print(f"  {key}: {s['description']}")
        return

    if args.scenario:
        s = PRESET_SCENARIOS[args.scenario]
        est = compute_savings(
            initiative=s["description"],
            current_backlog=s["current_backlog"],
            target_backlog=s["target_backlog"],
            cost_per_unit_usd=s["cost_per_unit_usd"],
            hours_per_unit=s["hours_per_unit"],
            inspector_hourly_rate_usd=s["inspector_hourly_rate_usd"],
        )
    else:
        required = [
            "initiative",
            "current_backlog",
            "target_backlog",
            "cost_per_unit",
            "hours_per_unit",
        ]
        missing = [r for r in required if not getattr(args, r.replace("-", "_"), None)]
        if missing:
            parser.error(f"Missing required arguments: {missing}. Or use --scenario.")
        est = compute_savings(
            initiative=args.initiative,
            current_backlog=args.current_backlog,
            target_backlog=args.target_backlog,
            cost_per_unit_usd=args.cost_per_unit,
            hours_per_unit=args.hours_per_unit,
            inspector_hourly_rate_usd=args.inspector_hourly_rate,
            uncertainty_pct=args.uncertainty,
        )

    if args.as_json:
        print(json.dumps(asdict(est), indent=2))
    else:
        print_report(est)


if __name__ == "__main__":
    main()
