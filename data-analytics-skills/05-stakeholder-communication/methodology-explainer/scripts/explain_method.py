"""
explain_method.py — Plain-language explanations of analytical methods for NYC DOT audiences.

Usage:
    python explain_method.py --method wilson_score
    python explain_method.py --method iqr_outlier --audience manager
    python explain_method.py --method z_score --audience council
"""

import argparse

EXPLANATIONS = {
    "wilson_score": {
        "name": "Wilson Score Confidence Interval",
        "formula": "p̂ ± z√(p̂(1-p̂)/n + z²/4n²) / (1 + z²/n)",
        "plain": (
            "A Wilson Score interval tells us the realistic range for a rate or proportion "
            "when our sample is small. Instead of just saying '62% of ramps are complete', "
            "it says '62%, and we're 95% confident the true rate is between 58% and 66%.' "
            "It's more accurate than the simple formula when fewer than 1,000 records are counted."
        ),
        "nyc_dot_example": (
            "Ramp completion rate in Staten Island: 124 of 187 ramps complete = 66.3%. "
            "Wilson 95% CI: [59.1%, 72.9%]. Report as '66% (95% CI: 59–73%)' rather than just '66%'."
        ),
        "audience_versions": {
            "field_staff": "The 66% rate includes a ±7% margin — it accounts for the fact that we haven't checked every ramp.",
            "manager": "The Wilson Score gives us a confidence range of 59–73%, which means leadership can trust the 66% figure to within about 7 points.",
            "council": "Ramp completion in SI is approximately 66%, with a statistical margin of ±7% at 95% confidence.",
            "public": "About 2 in 3 ramps in Staten Island are complete, give or take.",
        },
    },
    "iqr_outlier": {
        "name": "IQR-Based Outlier Detection",
        "formula": "Outlier if value < Q1 − 1.5×IQR  or  value > Q3 + 1.5×IQR\nwhere IQR = Q3 − Q1",
        "plain": (
            "IQR outlier detection finds values that are unusually far from the middle 50% of the data. "
            "It splits data into quartiles, and anything more than 1.5× the middle-50% range away from "
            "the edges is flagged as an outlier. It's robust to skewed distributions — unlike z-scores, "
            "it doesn't assume a bell curve."
        ),
        "nyc_dot_example": (
            "Days to close a violation: Q1=5, Q3=21, IQR=16. "
            "Lower fence: 5 − 24 = −19 (impossible, so no lower outliers). "
            "Upper fence: 21 + 24 = 45 days. Any violation taking > 45 days to close is flagged as an outlier."
        ),
        "audience_versions": {
            "field_staff": "We flagged violations that took more than 45 days to close — those are the ones that fell through the cracks.",
            "manager": "The IQR method flagged 3.2% of violations as outliers — cases taking more than 45 days. These warrant individual review.",
            "council": "Our analysis identified 312 violations (3.2%) that took significantly longer than typical to resolve, flagged for operational review.",
            "public": "A small number of cases took much longer than average to fix. We've identified them and are reviewing why.",
        },
    },
    "z_score": {
        "name": "Z-Score Standardisation",
        "formula": "z = (x − μ) / σ",
        "plain": (
            "A z-score measures how many standard deviations a value is from the average. "
            "A z-score of 0 means exactly average. +2 means 2 standard deviations above average — "
            "unusual. −2 means unusually low. We typically flag values with |z| > 3 as anomalies."
        ),
        "nyc_dot_example": (
            "Average daily inspections in BK: μ=120, σ=18. "
            "On 2026-05-15, only 62 inspections were logged. z = (62−120)/18 = −3.2. "
            "This is flagged as anomalously low — likely a data entry gap or unplanned crew absence."
        ),
        "audience_versions": {
            "field_staff": "On May 15, BK logged 62 inspections — that's 3 standard deviations below normal. Something went wrong that day.",
            "manager": "May 15 showed statistically anomalous low activity in BK (z=−3.2). Recommend confirming with field log.",
            "council": "Our monitoring system flagged May 15 as an outlier in Brooklyn inspection activity, which we are investigating.",
            "public": "We noticed an unusual dip in inspections on one day in May and are looking into the cause.",
        },
    },
    "linear_regression": {
        "name": "Linear Regression (Trend Line)",
        "formula": "y = β₀ + β₁x  |  β₁ = Σ(xᵢ−x̄)(yᵢ−ȳ) / Σ(xᵢ−x̄)²",
        "plain": (
            "Linear regression fits the best straight line through data points. "
            "The slope (β₁) tells us the average change in y for each unit increase in x. "
            "R² tells us how much of the variation in y is explained by x — closer to 1 is better."
        ),
        "nyc_dot_example": (
            "Violations per month over 12 months: slope = +42 violations/month, R²=0.78. "
            "Interpretation: violations are growing by ~42 per month, and time explains 78% of that variation."
        ),
        "audience_versions": {
            "field_staff": "The trend line shows violations are growing by about 42 per month — if this continues, we'll hit 6,000 open by August.",
            "manager": "Linear regression shows a statistically significant upward trend of +42 violations/month (R²=0.78). Forecast: 5,900 open by Q3.",
            "council": "Data shows violations are rising at approximately 42 per month. At this rate, the backlog will reach 6,000 by August without intervention.",
            "public": "Sidewalk violation reports have been increasing each month. The City is reviewing inspector capacity.",
        },
    },
    "kmeans": {
        "name": "K-Means Clustering",
        "formula": "Minimise Σ Σ ||xᵢ − μₖ||²  (sum of squared distances from each point to its cluster centre)",
        "plain": (
            "K-means groups data points into k clusters so that points within each cluster "
            "are as similar as possible. The algorithm repeatedly assigns each point to its "
            "nearest cluster centre, then recomputes the centres, until assignments stabilise. "
            "It requires choosing k in advance — we use silhouette score to validate the choice."
        ),
        "nyc_dot_example": (
            "Segmenting 87,000 sidewalk units by defect_count, days_since_inspection, violation_rate. "
            "k=4: Cluster A (high-risk, 18%), Cluster B (moderate, 35%), "
            "Cluster C (low-risk, 40%), Cluster D (new/no data, 7%). "
            "Silhouette score = 0.52 — reasonable separation."
        ),
        "audience_versions": {
            "field_staff": "We grouped sidewalk units into 4 buckets by risk level. About 1 in 5 units are in the high-risk group and need priority attention.",
            "manager": "K-means clustering identified 4 operational segments. The 18% high-risk segment accounts for 61% of all open violations.",
            "council": "Data analysis grouped sidewalk units into four risk tiers. The highest-risk tier (18% of units) requires prioritised inspection.",
            "public": "The City has identified which sidewalks need the most attention, based on inspection history and reported issues.",
        },
    },
}


def explain(method: str, audience: str) -> None:
    if method not in EXPLANATIONS:
        print(f"[ERROR] Unknown method: '{method}'")
        print(f"Available methods: {', '.join(EXPLANATIONS)}")
        return

    info = EXPLANATIONS[method]
    print(f"\n{'=' * 60}")
    print(f"  {info['name']}")
    print(f"{'=' * 60}\n")
    print(f"FORMULA\n  {info['formula']}\n")
    print(f"PLAIN LANGUAGE\n  {info['plain']}\n")
    print(f"NYC DOT EXAMPLE\n  {info['nyc_dot_example']}\n")

    if audience in info["audience_versions"]:
        print(f"HOW TO SAY IT TO: {audience.upper().replace('_', ' ')}")
        print(f'  "{info["audience_versions"][audience]}"\n')
    else:
        print("HOW TO SAY IT (all audiences):")
        for aud, text in info["audience_versions"].items():
            print(f'  [{aud}]: "{text}"')
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Plain-language method explanations for NYC DOT audiences."
    )
    parser.add_argument(
        "--method",
        required=True,
        choices=list(EXPLANATIONS),
        help=f"Method to explain. Options: {', '.join(EXPLANATIONS)}",
    )
    parser.add_argument(
        "--audience",
        default="manager",
        choices=["field_staff", "manager", "council", "public"],
        help="Target audience for plain-language version",
    )
    args = parser.parse_args()
    explain(args.method, args.audience)


if __name__ == "__main__":
    main()
