"""
SaaS Business Metrics Calculator

Calculates core SaaS and subscription metrics: MRR, ARR, churn rate, NRR,
LTV, CAC, LTV:CAC ratio, payback period, and DAU/MAU engagement ratio.

Usage:
    python saas_metrics.py --demo
    python saas_metrics.py --mrr 500000 --churned-mrr 12000 --expanded-mrr 25000 \
        --new-mrr 40000
    python saas_metrics.py --ltv 3600 --cac 900
"""

import argparse
import sys


# ---- Individual metric calculators ------------------------------------------

def mrr_components(starting_mrr: float, new_mrr: float, expansion_mrr: float,
                   contraction_mrr: float, churned_mrr: float) -> dict:
    ending_mrr = starting_mrr + new_mrr + expansion_mrr - contraction_mrr - churned_mrr
    net_new_mrr = new_mrr + expansion_mrr - contraction_mrr - churned_mrr
    return {
        "starting_mrr": starting_mrr,
        "new_mrr": new_mrr,
        "expansion_mrr": expansion_mrr,
        "contraction_mrr": contraction_mrr,
        "churned_mrr": churned_mrr,
        "net_new_mrr": net_new_mrr,
        "ending_mrr": ending_mrr,
        "arr": ending_mrr * 12,
    }


def churn_rates(churned_customers: int, starting_customers: int,
                churned_mrr: float, starting_mrr: float) -> dict:
    logo_churn = churned_customers / starting_customers if starting_customers else 0
    revenue_churn = churned_mrr / starting_mrr if starting_mrr else 0
    return {
        "logo_churn_rate": round(logo_churn, 6),
        "revenue_churn_rate": round(revenue_churn, 6),
        "logo_churn_pct": round(logo_churn * 100, 2),
        "revenue_churn_pct": round(revenue_churn * 100, 2),
    }


def net_revenue_retention(starting_mrr: float, expansion_mrr: float,
                          contraction_mrr: float, churned_mrr: float) -> dict:
    nrr = (starting_mrr + expansion_mrr - contraction_mrr - churned_mrr) / starting_mrr \
          if starting_mrr else 0
    return {
        "nrr": round(nrr, 6),
        "nrr_pct": round(nrr * 100, 2),
    }


def ltv_cac(arpu: float, gross_margin: float, monthly_churn: float,
            cac: float) -> dict:
    """
    LTV = ARPU * gross_margin / monthly_churn_rate
    Payback period = CAC / (ARPU * gross_margin)
    """
    ltv = arpu * gross_margin / monthly_churn if monthly_churn > 0 else float("inf")
    ratio = ltv / cac if cac > 0 else float("inf")
    payback_months = cac / (arpu * gross_margin) if (arpu * gross_margin) > 0 else float("inf")
    return {
        "ltv": round(ltv, 2),
        "cac": cac,
        "ltv_cac_ratio": round(ratio, 2),
        "payback_months": round(payback_months, 1),
    }


def dau_mau(dau: int, mau: int) -> dict:
    ratio = dau / mau if mau > 0 else 0
    return {
        "dau": dau,
        "mau": mau,
        "dau_mau_ratio": round(ratio, 4),
        "dau_mau_pct": round(ratio * 100, 1),
        "interpretation": (
            "strong engagement (>20%)" if ratio > 0.20 else
            "moderate engagement (10-20%)" if ratio > 0.10 else
            "low engagement (<10%)"
        ),
    }


def format_mrr_report(mrr: dict) -> str:
    lines = [
        "--- MRR / ARR ---",
        f"  Starting MRR:     ${mrr['starting_mrr']:>12,.0f}",
        f"  + New:            ${mrr['new_mrr']:>12,.0f}",
        f"  + Expansion:      ${mrr['expansion_mrr']:>12,.0f}",
        f"  - Contraction:    ${mrr['contraction_mrr']:>12,.0f}",
        f"  - Churned:        ${mrr['churned_mrr']:>12,.0f}",
        f"  = Net New MRR:    ${mrr['net_new_mrr']:>12,.0f}",
        f"  Ending MRR:       ${mrr['ending_mrr']:>12,.0f}",
        f"  ARR:              ${mrr['arr']:>12,.0f}",
    ]
    return "\n".join(lines)


def format_full_report(mrr: dict, churn: dict, nrr: dict, lc: dict, engagement: dict) -> str:
    lines = [
        "=" * 60,
        "SAAS METRICS DASHBOARD",
        "=" * 60,
        "",
        format_mrr_report(mrr),
        "",
        "--- Churn ---",
        f"  Logo churn rate:    {churn['logo_churn_pct']:.2f}%/month",
        f"  Revenue churn rate: {churn['revenue_churn_pct']:.2f}%/month",
        "",
        "--- Net Revenue Retention (NRR) ---",
        f"  NRR: {nrr['nrr_pct']:.1f}%  ({'healthy — expansion covers churn' if nrr['nrr'] >= 1.0 else 'below 100% — churn exceeds expansion'})",
        "",
        "--- LTV / CAC ---",
        f"  LTV:              ${lc['ltv']:>10,.0f}",
        f"  CAC:              ${lc['cac']:>10,.0f}",
        f"  LTV:CAC ratio:    {lc['ltv_cac_ratio']:.1f}x  ({'good (>3x)' if lc['ltv_cac_ratio'] >= 3 else 'needs improvement (<3x)'})",
        f"  Payback period:   {lc['payback_months']:.0f} months",
        "",
        "--- Engagement ---",
        f"  DAU: {engagement['dau']:,}  |  MAU: {engagement['mau']:,}",
        f"  DAU/MAU: {engagement['dau_mau_pct']:.1f}%  — {engagement['interpretation']}",
        "=" * 60,
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Calculate SaaS business metrics.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--mrr", type=float, help="Starting MRR")
    parser.add_argument("--new-mrr", type=float, default=0)
    parser.add_argument("--expanded-mrr", type=float, default=0)
    parser.add_argument("--contracted-mrr", type=float, default=0)
    parser.add_argument("--churned-mrr", type=float, default=0)
    parser.add_argument("--churned-customers", type=int, default=0)
    parser.add_argument("--starting-customers", type=int, default=1)
    parser.add_argument("--arpu", type=float, help="Average revenue per user (monthly)")
    parser.add_argument("--gross-margin", type=float, default=0.75)
    parser.add_argument("--monthly-churn", type=float, help="Monthly churn rate (decimal)")
    parser.add_argument("--cac", type=float, default=0)
    parser.add_argument("--dau", type=int, default=0)
    parser.add_argument("--mau", type=int, default=0)
    parser.add_argument("--ltv", type=float, help="Precomputed LTV")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if not args.mrr:
        parser.error("Provide --mrr or --demo")

    mrr = mrr_components(args.mrr, args.new_mrr, args.expanded_mrr,
                          args.contracted_mrr, args.churned_mrr)
    churn = churn_rates(args.churned_customers, args.starting_customers,
                        args.churned_mrr, args.mrr)
    nrr = net_revenue_retention(args.mrr, args.expanded_mrr,
                                args.contracted_mrr, args.churned_mrr)

    lc = {"ltv": args.ltv or 0, "cac": args.cac,
          "ltv_cac_ratio": (args.ltv / args.cac) if (args.ltv and args.cac) else 0,
          "payback_months": 0}
    if args.arpu and args.monthly_churn:
        lc = ltv_cac(args.arpu, args.gross_margin, args.monthly_churn, args.cac or 1)

    engagement = dau_mau(args.dau, args.mau)
    print(format_full_report(mrr, churn, nrr, lc, engagement))


def _demo():
    mrr = mrr_components(
        starting_mrr=500_000,
        new_mrr=45_000,
        expansion_mrr=22_000,
        contraction_mrr=8_000,
        churned_mrr=14_000,
    )
    churn = churn_rates(churned_customers=18, starting_customers=420,
                        churned_mrr=14_000, starting_mrr=500_000)
    nrr = net_revenue_retention(500_000, 22_000, 8_000, 14_000)
    lc = ltv_cac(arpu=1_190, gross_margin=0.78, monthly_churn=0.014, cac=4_200)
    engagement = dau_mau(dau=8_400, mau=31_000)
    print(format_full_report(mrr, churn, nrr, lc, engagement))


if __name__ == "__main__":
    _demo()
