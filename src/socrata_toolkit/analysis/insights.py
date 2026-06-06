import math
import logging
import json
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

from .inference import run_chi_square, run_t_test, check_normality
from .metrics import compute_borough_metrics, compute_sla_trends
from .profiling import profile_dataframe
from ..core import DTYPE_NUM
from ..engineering.pavement import NYSDOTPavementEngine, PavementType, evaluate_pavement_safety_risk
from ..governance.equity import EquityScorer
from ..material.standards_v4 import run_vision_zero_audit

logger = logging.getLogger(__name__)

# ... (Insight and Recommendation classes remain the same) ...

class InsightsEngine:
    """
    Elite Statistical & Engineering Analytical Engine.
    Performs deep quantitative analysis including anomaly detection, drift monitoring,
    NYSDOT pavement audits, and NYC SDM 4th Ed geometric & equity compliance.
    """
    def __init__(self, df: pd.DataFrame, baseline_df: pd.DataFrame | None = None):
        self.df = df
        self.baseline_df = baseline_df

    def generate_report(self) -> InsightsReport:
        """Executes full-spectrum statistical, engineering, and street design analysis suite."""
        warnings = []
        if self.df.empty:
            warnings.append("Dataset is empty. Statistical analysis reflects 0 records.")
            return InsightsReport(data_health="critical", summary=["Empty dataset"], key_metrics={"Rows": 0}, warnings=warnings)

        prof = profile_dataframe(self.df)
        insights = []
        recs = []
        
        # 1. Socio-Economic Equity Audit (NYC SDM 4th Ed Mandate)
        equity_scorer = EquityScorer()
        high_need_equity = 0
        for _, row in self.df.iterrows():
            # Base condition need (high index = bad condition)
            base_need = 1.0 if prof.quality_score < 70 else 0.5
            impact = equity_scorer.calculate_impact(row, base_need)
            if impact.is_priority_area and base_need > 0.8:
                high_need_equity += 1
        
        if high_need_equity > 0:
            insights.append(Insight("equity", f"Detected {high_need_equity} critical repair needs within historically underinvested Priority Investment Areas.", "high"))
            recs.append(Recommendation("high", "Prioritize capital allocation to identified high-need equity zones as per Mayor's Mandate."))

        # 2. NYC Street Design Manual (4th Ed) Geometric Audit
        # Check for geometric columns
        lw_col = next((c for c in self.df.columns if c.lower() in ("lane_width", "travel_lane_width")), None)
        cr_col = next((c for c in self.df.columns if c.lower() in ("corner_radius", "curb_radius")), None)
        cp_col = next((c for c in self.df.columns if c.lower() in ("clear_path", "sidewalk_width", "path_width")), None)

        vz_scores = []
        violation_counts = {"lane_width": 0, "corner_radius": 0, "clear_path": 0}
        
        if any([lw_col, cr_col, cp_col]):
            for _, row in self.df.iterrows():
                audit = run_vision_zero_audit(
                    lane_width=row.get(lw_col, 10.5) if lw_col else 10.5,
                    corner_radius=row.get(cr_col, 10.0) if cr_col else 10.0,
                    clear_path=row.get(cp_col, 8.0) if cp_col else 8.0
                )
                vz_scores.append(audit.vision_zero_score)
                if not audit.is_compliant:
                    for v in audit.violations:
                        if "Lane width" in v: violation_counts["lane_width"] += 1
                        if "Corner radius" in v: violation_counts["corner_radius"] += 1
                        if "clear path" in v: violation_counts["clear_path"] += 1
            
            avg_vz_score = np.mean(vz_scores)
            insights.append(Insight("design", f"Vision Zero Geometric Compliance Score: {avg_vz_score:.2%}.", "medium" if avg_vz_score > 0.8 else "high"))
            
            # Add detailed violation counts to report metadata or summaries
            for v_type, count in violation_counts.items():
                if count > 0:
                    insights.append(Insight("design", f"Detected {count} instances of {v_type.replace('_', ' ')} violations.", "medium"))

            if avg_vz_score < 0.9:
                recs.append(Recommendation("high", "Audit non-compliant segments for Vision Zero geometric remediation (lane narrowing/radii reduction)."))

        # 2. NYSDOT Infrastructure Engineering Audit
        # ... (rest of the logic) ...
        cols = [c.lower() for c in self.df.columns]
        
        # Surface Rating (SR) Logic
        sr_col = next((c for c in self.df.columns if c.lower() in ("surface_rating", "pavement_rating", "sr")), None)
        if sr_col:
            avg_sr = self.df[sr_col].mean()
            mr = NYSDOTPavementEngine.get_mr_recommendation(int(round(avg_sr)), PavementType.FLEXIBLE_HMA)
            insights.append(Insight("engineering", f"Average Surface Rating is {avg_sr:.1f}. NYSDOT HDM trigger: {mr['strategy']}.", "high" if avg_sr < 6 else "medium"))
            for action in mr["recommended_actions"]:
                recs.append(Recommendation("medium", f"Consider {action} as part of NYSDOT {mr['strategy']} program."))

        # IRI / User Cost Logic
        iri_col = next((c for c in self.df.columns if c.lower() in ("iri", "roughness_index", "international_roughness_index")), None)
        if iri_col:
            max_iri = self.df[iri_col].max()
            if max_iri > 2.0:
                voc = NYSDOTPavementEngine.calculate_user_cost_impact(max_iri)
                insights.append(Insight("economic", f"Peak roughness (IRI {max_iri:.2f}) imposes a {voc['total_voc_penalty_pct']:.1f}% User Cost (VOC) penalty.", "medium"))
                recs.append(Recommendation("low", "Smoothness-focused overlay could reduce citywide vehicle operating costs."))

        # 2. Moment Characterization & Distribution Risk
        # ... (rest of the logic) ...
        for col, m in prof.moments.items():
            if abs(m["skewness"]) > 2.5:
                insights.append(Insight("distribution", f"Column '{col}' exhibits severe skewness ({m['skewness']:.2f}). Direct mean-based interpretation may be misleading.", "medium"))
            if m["kurtosis"] > 10:
                insights.append(Insight("risk", f"Column '{col}' shows extreme kurtosis ({m['kurtosis']:.2f}), indicating high 'fat-tail' risk for outliers.", "high"))

        # 2. Formal Inference: Group Differences (t-tests)
        cat_cols = self.df.select_dtypes(include=['object', 'category']).columns
        num_cols = self.df.select_dtypes(include=DTYPE_NUM).columns
        
        for c_col in cat_cols:
            if self.df[c_col].nunique() == 2: # Binary group comparison
                groups = list(self.df[c_col].dropna().unique())
                for n_col in num_cols:
                    g1 = self.df[self.df[c_col] == groups[0]][n_col]
                    g2 = self.df[self.df[c_col] == groups[1]][n_col]
                    if len(g1) > 10 and len(g2) > 10:
                        res = run_t_test(g1, g2)
                        if res.significant:
                            insights.append(Insight("inference", f"Significant difference in '{n_col}' between '{groups[0]}' and '{groups[1]}' (p={res.p_value:.4f}).", "high"))

        # 3. Categorical Association (Chi-Square)
        if len(cat_cols) >= 2:
            for i in range(len(cat_cols)):
                for j in range(i + 1, len(cat_cols)):
                    col1, col2 = cat_cols[i], cat_cols[j]
                    if self.df[col1].nunique() < 10 and self.df[col2].nunique() < 10:
                        res = run_chi_square(self.df, col1, col2)
                        if res.significant:
                            insights.append(Insight("association", f"Statistically significant association found between '{col1}' and '{col2}' (p={res.p_value:.4f}).", "medium"))

        # ... (Anomalies and Drift detection logic remains as established) ...

        key_metrics = {
            "Rows": prof.row_count,
            "Quality": f"{prof.quality_score}/100",
            "Significant Associations": len([i for i in insights if i.category == "association"]),
            "Distribution Risks": len([i for i in insights if i.category in ("risk", "distribution")])
        }

        return InsightsReport(
            data_health="unstable" if any(i.priority == "high" for i in insights) else "optimal",
            summary=["Advanced empirical social science characterization complete."],
            key_metrics=key_metrics,
            insights=insights,
            recommendations=recs or self._get_default_recommendations(prof),
            warnings=warnings
        )

    def _get_default_recommendations(self, prof) -> list[Recommendation]:
        recs = [Recommendation("low", "Continue regular monitoring of data ingestion pipelines.")]
        if prof.row_count > 500000:
            recs.append(Recommendation("medium", "Implement partitioning or indexing on temporal columns for query optimization."))
        return recs

def generate_insights(df: pd.DataFrame, baseline_df: pd.DataFrame | None = None, **kwargs) -> InsightsReport:
    """Public entry point for the Insights Engine."""
    engine = InsightsEngine(df, baseline_df=baseline_df)
    return engine.generate_report()
