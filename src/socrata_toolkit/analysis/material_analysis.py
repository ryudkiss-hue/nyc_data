"""Sidewalk Material Degradation Analysis — Survival Curves & Cost-Benefit.

Quantifies failure curves by material type (concrete vs asphalt) using Kaplan-Meier
survival analysis. Computes median lifespan, material economics, and log-rank tests
to identify material-specific failure patterns.

Example::

    from socrata_toolkit.analysis.material_analysis import MaterialDegradationAnalysis
    import pandas as pd

    df_survival = pd.DataFrame({
        'material_type': ['concrete', 'asphalt', 'concrete', 'asphalt'],
        'time_in_months': [156, 108, 180, 96],
        'event': [1, 1, 0, 1],  # 1=failure observed, 0=censored
        'borough': ['Manhattan', 'Manhattan', 'Brooklyn', 'Brooklyn'],
    })

    analysis = MaterialDegradationAnalysis(df_survival)
    results = analysis.fit()
    print(f"Concrete median lifespan: {results['km_curves']['concrete']['median_survival_months']} months")
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "MaterialDegradationAnalysis",
    "SurvivalDataPrep",
]


def _get_statsmodels():
    """Lazy import statsmodels for survival analysis."""
    try:
        from lifelines import CoxPHFitter, KaplanMeierFitter, NelsonAalenFitter
        from lifelines.statistics import logrank_test

        return {
            "KaplanMeierFitter": KaplanMeierFitter,
            "CoxPHFitter": CoxPHFitter,
            "NelsonAalenFitter": NelsonAalenFitter,
            "logrank_test": logrank_test,
        }
    except ImportError:
        # Fallback to manual KM implementation
        return None


class SurvivalDataPrep:
    """Prepare inspection + violation data for survival analysis."""

    @staticmethod
    def prepare_time_to_event(
        inspections_df: pd.DataFrame,
        violations_df: pd.DataFrame,
        cutoff_date: str | pd.Timestamp | None = None,
        min_followup_months: float = 6,
    ) -> pd.DataFrame:
        """Prepare time-to-event data from inspections and violations.

        Args:
            inspections_df: DataFrame with columns:
                - block_id, material_type, inspection_date, borough
            violations_df: DataFrame with columns:
                - block_id, violation_date (or first_violation_date)
            cutoff_date: Observation end date (default: today)
            min_followup_months: Minimum followup time before censoring

        Returns:
            DataFrame with columns:
            - material_type, time_in_months, event, borough, block_id
        """
        if cutoff_date is None:
            cutoff_date = pd.Timestamp.now()
        else:
            cutoff_date = pd.to_datetime(cutoff_date)

        # Convert dates
        inspections_df = inspections_df.copy()
        violations_df = violations_df.copy()

        inspections_df["inspection_date"] = pd.to_datetime(
            inspections_df.get("inspection_date", inspections_df.get("date"))
        )
        violations_df["violation_date"] = pd.to_datetime(
            violations_df.get("violation_date", violations_df.get("date"))
        )

        # Get installation date (earliest inspection per block)
        installation_dates = (
            inspections_df.groupby("block_id")["inspection_date"].min().reset_index()
        )
        installation_dates.rename(
            columns={"inspection_date": "installation_date"}, inplace=True
        )

        # Get first violation date per block
        first_violations = (
            violations_df.groupby("block_id")["violation_date"].min().reset_index()
        )
        first_violations.rename(
            columns={"violation_date": "first_violation_date"}, inplace=True
        )

        # Merge: inspections + violations
        df = inspections_df[["block_id", "material_type", "borough"]].drop_duplicates()
        df = df.merge(installation_dates, on="block_id", how="left")
        df = df.merge(first_violations, on="block_id", how="left")

        # Compute time-to-event
        df["time_in_months"] = (
            df["first_violation_date"] - df["installation_date"]
        ).dt.days / 30.44
        df["event"] = (~df["first_violation_date"].isna()).astype(int)

        # Censor observations with insufficient followup
        df.loc[df["time_in_months"] < min_followup_months, "event"] = 0
        df["time_in_months"] = df["time_in_months"].clip(lower=min_followup_months)

        # Cap at 25 years (right-censoring)
        df.loc[df["time_in_months"] > 300, "time_in_months"] = 300
        df.loc[df["time_in_months"] > 300, "event"] = 0

        return df[["material_type", "time_in_months", "event", "borough", "block_id"]]


class MaterialDegradationAnalysis:
    """Kaplan-Meier survival analysis by material type.

    Attributes:
        df: Survival data (material_type, time_in_months, event, borough)
        km_results: Dict of KM results per material
        cox_results: Cox proportional hazards results
    """

    def __init__(self, survival_df: pd.DataFrame):
        """Initialize with survival data.

        Args:
            survival_df: DataFrame with columns:
                - material_type, time_in_months, event, borough (optional)
        """
        self.df = survival_df.copy()
        self.km_results = {}
        self.cox_results = None
        self._kmf = None

    def fit(self) -> dict[str, Any]:
        """Run full material degradation analysis.

        Returns:
            Dict with keys:
            - km_curves: KM results per material {material: {median, n_events, ...}}
            - log_rank_tests: P-values for pairwise material comparisons
            - material_economics: Cost-benefit analysis
        """
        # Try to use lifelines, fallback to manual KM
        statsmodels_dict = _get_statsmodels()

        if statsmodels_dict:
            self._fit_with_lifelines(statsmodels_dict)
        else:
            self._fit_manual_km()

        results = {
            "km_curves": self.km_results,
            "log_rank_tests": self._compute_log_rank_tests(),
            "material_economics": self._compute_material_economics(),
        }

        return results

    def _fit_with_lifelines(self, statsmodels_dict: dict) -> None:
        """Fit KM curves using lifelines library."""
        KaplanMeierFitter = statsmodels_dict["KaplanMeierFitter"]

        for material in self.df["material_type"].unique():
            if pd.isna(material):
                continue

            material_data = self.df[self.df["material_type"] == material]
            kmf = KaplanMeierFitter()
            kmf.fit(
                durations=material_data["time_in_months"],
                event_observed=material_data["event"],
                label=material,
            )

            # Extract survival function
            survival_func = kmf.survival_function_.values.flatten()
            time_points = kmf.survival_function_.index.values

            # Confidence interval
            ci = kmf.confidence_interval_survival_function_
            ci_lower = ci.iloc[:, 0].values if ci.shape[1] > 0 else survival_func
            ci_upper = (
                ci.iloc[:, 1].values if ci.shape[1] > 1 else survival_func
            )

            self.km_results[material] = {
                "time_points": time_points.tolist(),
                "survival_prob": survival_func.tolist(),
                "ci_lower": ci_lower.tolist(),
                "ci_upper": ci_upper.tolist(),
                "median_survival_months": (
                    kmf.median_survival_time_
                    if kmf.median_survival_time_ is not None
                    else np.nan
                ),
                "n_at_risk": len(material_data),
                "n_events": int(material_data["event"].sum()),
            }

    def _fit_manual_km(self) -> None:
        """Fallback KM implementation using numpy (no lifelines)."""
        for material in self.df["material_type"].unique():
            if pd.isna(material):
                continue

            material_data = self.df[self.df["material_type"] == material].sort_values(
                "time_in_months"
            )

            # Manual KM calculation
            times = material_data["time_in_months"].values
            events = material_data["event"].values

            unique_times = np.unique(times)
            survival_probs = []
            ci_lower_list = []
            ci_upper_list = []

            for t in unique_times:
                at_risk = np.sum(times >= t)
                events_at_t = np.sum((times == t) & (events == 1))

                if at_risk > 0:
                    surv_prob = 1.0 - (events_at_t / at_risk)
                    survival_probs.append(surv_prob)

                    # Simple Greenwood CI
                    var = (events_at_t) / (at_risk * (at_risk - events_at_t))
                    se = np.sqrt(var) if var > 0 else 0
                    ci_lower_list.append(max(0, surv_prob - 1.96 * se))
                    ci_upper_list.append(min(1, surv_prob + 1.96 * se))

            # Compute cumulative survival
            cumulative_survival = np.cumprod(survival_probs)

            # Median survival time
            median_idx = np.where(cumulative_survival < 0.5)[0]
            median_time = (
                unique_times[median_idx[0]] if len(median_idx) > 0 else np.nan
            )

            self.km_results[material] = {
                "time_points": unique_times.tolist(),
                "survival_prob": cumulative_survival.tolist(),
                "ci_lower": ci_lower_list,
                "ci_upper": ci_upper_list,
                "median_survival_months": median_time,
                "n_at_risk": len(material_data),
                "n_events": int(material_data["event"].sum()),
            }

    def _compute_log_rank_tests(self) -> dict[tuple[str, str], dict[str, float]]:
        """Compute log-rank tests for pairwise material comparisons.

        Returns:
            Dict with keys (material1, material2) and values {p_value, significant}
        """
        statsmodels_dict = _get_statsmodels()
        if not statsmodels_dict:
            return {}

        logrank_test = statsmodels_dict["logrank_test"]
        materials = [m for m in self.df["material_type"].unique() if pd.notna(m)]
        n_comparisons = len(materials) * (len(materials) - 1) / 2
        alpha_corrected = 0.05 / max(n_comparisons, 1)

        results = {}
        for i, mat1 in enumerate(materials):
            for mat2 in materials[i + 1:]:
                data1 = self.df[self.df["material_type"] == mat1]
                data2 = self.df[self.df["material_type"] == mat2]

                try:
                    test = logrank_test(
                        durations_A=data1["time_in_months"],
                        durations_B=data2["time_in_months"],
                        event_observed_A=data1["event"],
                        event_observed_B=data2["event"],
                    )
                    results[(mat1, mat2)] = {
                        "test_statistic": float(test.test_statistic),
                        "p_value": float(test.p_value),
                        "significant": test.p_value < alpha_corrected,
                    }
                except Exception:
                    # If test fails, mark as not significant
                    results[(mat1, mat2)] = {
                        "test_statistic": np.nan,
                        "p_value": np.nan,
                        "significant": False,
                    }

        return results

    def _compute_material_economics(self) -> pd.DataFrame:
        """Compute cost-benefit metrics by material.

        Assumptions:
        - Unit installation cost: concrete=$80/sqft, asphalt=$40/sqft
        - Annual maintenance: $200 per failure event
        - Analysis horizon: 20 years

        Returns:
            DataFrame with economics by material
        """
        unit_costs = {
            "concrete": 80.0,
            "asphalt": 40.0,
            "stone": 100.0,
            "other": 60.0,
        }

        economics = {}
        for material, km_result in self.km_results.items():
            median_months = km_result.get("median_survival_months", 120)
            median_years = median_months / 12 if not pd.isna(median_months) else 10

            # Estimate installation volume and cost
            n_blocks = km_result.get("n_at_risk", 100)
            unit_cost = unit_costs.get(material, 60.0)
            total_install = n_blocks * unit_cost

            # Annual replacement rate
            annual_failures = km_result.get("n_events", 10) / 20
            annual_maintenance = annual_failures * 200

            # 20-year horizon
            cost_20yr = total_install + (annual_maintenance * 20)

            economics[material] = {
                "median_lifespan_years": median_years,
                "installation_cost_total": total_install,
                "annual_maintenance_cost": annual_maintenance,
                "20_year_total_cost": cost_20yr,
                "cost_per_year": cost_20yr / 20,
                "cost_per_year_of_lifespan": cost_20yr / max(median_years, 1),
            }

        return pd.DataFrame(economics).T

    def get_cumulative_hazard(self) -> dict[str, dict[str, list]]:
        """Get cumulative hazard function by material (Nelson-Aalen).

        Returns:
            Dict with material names as keys, containing time_points and hazard values
        """
        cumulative_hazard = {}
        for material, km_result in self.km_results.items():
            # Cumulative hazard: -ln(S(t))
            survival_probs = np.array(km_result["survival_prob"])
            hazard = -np.log(np.maximum(survival_probs, 0.001))  # Avoid log(0)

            cumulative_hazard[material] = {
                "time_points": km_result["time_points"],
                "hazard": hazard.tolist(),
            }

        return cumulative_hazard
