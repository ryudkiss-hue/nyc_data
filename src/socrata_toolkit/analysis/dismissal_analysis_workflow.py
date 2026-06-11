"""
Dismissal Pattern Analysis Workflow: LangGraph + Claude + spaCy

Full integration for analyzing dismissal patterns in NYC SIM data:
  1. Fetch dismissals + violations (joined)
  2. Extract dismissal reason from text with DismissalReasonClassifier (spaCy)
  3. Classify each dismissal: Legal, Admin Error, Justified, Suspicious
  4. Analyze patterns by inspector + defect type + borough
  5. Claude assessment: "Which dismissals look suspicious? Inspector coaching?" (~350 tokens)
  6. Generate structured JSON audit report with flagged cases and recommendations

Token cost: ~1000 tokens for 1000+ dismissals
Execution time: ~8-12 seconds
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph
from langchain_anthropic import ChatAnthropic

from socrata_toolkit.analysis.dismissal_classifier import (
    DismissalCategory,
    DismissalClassification,
    DismissalReasonClassifier,
)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITIONS
# ============================================================================


@dataclass
class InspectorDismissalStats:
    """Dismissal statistics for a single inspector."""
    inspector_id: str
    inspector_name: str | None
    total_dismissals: int
    dismissal_rate: float  # dismissals / inspections
    suspicious_dismissals: int
    suspicious_rate: float
    avg_suspicion_score: float
    flagged_for_review: bool
    common_defect_types: List[str]


class DismissalAnalysisState(TypedDict):
    """LangGraph state for dismissal analysis workflow."""
    # Input context
    context: Optional[Dict[str, Any]]
    dismissals_fourfour: str
    violations_fourfour: str
    max_rows: int
    borough_filter: Optional[str]

    # Fetched data
    dismissals_df: Optional[pd.DataFrame]
    violations_df: Optional[pd.DataFrame]
    joined_df: Optional[pd.DataFrame]
    total_records: int

    # Classification results
    classifications: List[DismissalClassification]
    classification_summary: Dict  # Category breakdown
    inspector_stats: Dict[str, InspectorDismissalStats]  # By inspector_id
    flagged_dismissals: List[Dict]  # High-suspicion cases
    defect_pattern_analysis: Dict  # Defect type clustering

    # Claude assessments
    claude_pattern_assessment: str  # Initial read on patterns
    claude_coaching_recommendations: str  # Inspector coaching advice
    suspicious_case_summary: str  # Which cases to investigate

    # Output
    final_report: Dict
    execution_log: List[Dict]


def create_dismissal_workflow():
    """Create and return the dismissal analysis workflow."""
    workflow = StateGraph(DismissalAnalysisState)

    # Add nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("classify_dismissals", classify_dismissals_node)
    workflow.add_node("analyze_patterns", analyze_patterns_node)
    workflow.add_node("claude_assess", claude_assess_node)
    workflow.add_node("generate_report", generate_report_node)

    # Add edges
    workflow.add_edge("fetch_data", "classify_dismissals")
    workflow.add_edge("classify_dismissals", "analyze_patterns")
    workflow.add_edge("analyze_patterns", "claude_assess")
    workflow.add_edge("claude_assess", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# ============================================================================
# WORKFLOW NODES
# ============================================================================


def fetch_data_node(state: DismissalAnalysisState) -> DismissalAnalysisState:
    """Fetch dismissals and violations datasets from Socrata."""
    logger.info(
        f"[FETCH] Fetching dismissals (fourfour={state['dismissals_fourfour']}, "
        f"max_rows={state['max_rows']})"
    )

    client = SocrataClient(SocrataConfig())

    # Build where clause if borough filter provided
    where_clause = None
    if state.get("borough_filter"):
        where_clause = f"borough='{state['borough_filter']}'"

    # Fetch dismissals
    dismissals_df = client.fetch_dataframe(
        "data.cityofnewyork.us",
        state["dismissals_fourfour"],
        max_rows=state["max_rows"],
        where=where_clause,
    )

    # Fetch violations (for context)
    violations_df = client.fetch_dataframe(
        "data.cityofnewyork.us",
        state["violations_fourfour"],
        max_rows=state["max_rows"] * 3,
        where=where_clause,
    )

    # Join on inspection_id
    if not dismissals_df.empty and not violations_df.empty:
        # Common join keys (adapt based on actual schema)
        join_cols = ["inspection_id"] if "inspection_id" in dismissals_df.columns else []
        if join_cols and all(col in violations_df.columns for col in join_cols):
            joined_df = dismissals_df.merge(
                violations_df,
                on=join_cols,
                how="left",
                suffixes=("_dismissal", "_violation"),
            )
        else:
            joined_df = dismissals_df
    else:
        joined_df = dismissals_df

    state["dismissals_df"] = dismissals_df
    state["violations_df"] = violations_df
    state["joined_df"] = joined_df
    state["total_records"] = len(dismissals_df)

    state["execution_log"].append({
        "step": "fetch_data",
        "timestamp": datetime.now().isoformat(),
        "dismissals_fetched": len(dismissals_df),
        "violations_fetched": len(violations_df),
    })

    logger.info(f"[FETCH] Fetched {len(dismissals_df)} dismissals, {len(violations_df)} violations")
    return state


def classify_dismissals_node(state: DismissalAnalysisState) -> DismissalAnalysisState:
    """Classify each dismissal reason with DismissalReasonClassifier."""
    logger.info("[CLASSIFY] Starting dismissal classification")

    df = state["joined_df"] or state["dismissals_df"]
    if df.empty:
        logger.warning("[CLASSIFY] No data to classify")
        state["classifications"] = []
        state["classification_summary"] = {}
        return state

    classifier = DismissalReasonClassifier()

    # Compute inspector dismissal rates for context
    inspector_dismissal_rates = {}
    if "inspector_id" in df.columns and "inspection_id" in df.columns:
        inspector_dismissal_counts = df.groupby("inspector_id").size()
        total_insp_per_inspector = (
            df.groupby("inspector_id")["inspection_id"].nunique()
        )
        inspector_dismissal_rates = {
            insp_id: inspector_dismissal_counts.get(insp_id, 0) / total_insp_per_inspector.get(insp_id, 1)
            for insp_id in inspector_dismissal_counts.index
        }

    # Compute cohort average
    cohort_dismissal_rate = (
        len(df) / df["inspection_id"].nunique()
        if "inspection_id" in df.columns
        else 0.15
    )

    classifications = []
    for _, row in df.iterrows():
        dismissal_id = str(row.get("dismissal_id", ""))
        dismissal_reason = str(row.get("dismissal_reason", ""))
        inspection_id = row.get("inspection_id")
        defect_type = row.get("defect_type")
        inspector_id = row.get("inspector_id")

        insp_rate = inspector_dismissal_rates.get(inspector_id, cohort_dismissal_rate)

        classification = classifier.classify(
            dismissal_id=dismissal_id,
            dismissal_reason_text=dismissal_reason,
            inspection_id=inspection_id,
            defect_type=defect_type,
            inspector_id=inspector_id,
            inspector_dismissal_rate=insp_rate,
            inspector_cohort_rate=cohort_dismissal_rate,
        )
        classifications.append(classification)

    # Summarize by category
    category_counts = {}
    for cls in classifications:
        cat = cls.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    state["classifications"] = classifications
    state["classification_summary"] = category_counts

    state["execution_log"].append({
        "step": "classify_dismissals",
        "timestamp": datetime.now().isoformat(),
        "classified_count": len(classifications),
        "category_summary": category_counts,
    })

    logger.info(f"[CLASSIFY] Classified {len(classifications)} dismissals")
    return state


def analyze_patterns_node(state: DismissalAnalysisState) -> DismissalAnalysisState:
    """Analyze dismissal patterns by inspector, defect type, and borough."""
    logger.info("[ANALYZE] Starting pattern analysis")

    classifications = state["classifications"]
    df = state["joined_df"] or state["dismissals_df"]

    if not classifications or df.empty:
        state["inspector_stats"] = {}
        state["flagged_dismissals"] = []
        state["defect_pattern_analysis"] = {}
        return state

    # Build inspector statistics
    inspector_stats: Dict[str, InspectorDismissalStats] = {}
    for cls in classifications:
        if not cls.inspector_id:
            continue

        if cls.inspector_id not in inspector_stats:
            inspector_stats[cls.inspector_id] = InspectorDismissalStats(
                inspector_id=cls.inspector_id,
                inspector_name=None,
                total_dismissals=0,
                dismissal_rate=0.0,
                suspicious_dismissals=0,
                suspicious_rate=0.0,
                avg_suspicion_score=0.0,
                flagged_for_review=False,
                common_defect_types=[],
            )

        stats = inspector_stats[cls.inspector_id]
        stats.total_dismissals += 1

        if cls.requires_review:
            stats.suspicious_dismissals += 1

    # Compute rates and flag outliers
    avg_suspicious_rate = (
        sum(s.suspicious_dismissals for s in inspector_stats.values()) /
        sum(s.total_dismissals for s in inspector_stats.values())
        if sum(s.total_dismissals for s in inspector_stats.values()) > 0
        else 0.0
    )

    for insp_id, stats in inspector_stats.items():
        stats.dismissal_rate = (
            stats.total_dismissals / len(classifications)
            if classifications
            else 0.0
        )
        stats.suspicious_rate = (
            stats.suspicious_dismissals / stats.total_dismissals
            if stats.total_dismissals > 0
            else 0.0
        )
        stats.flagged_for_review = stats.suspicious_rate > avg_suspicious_rate * 1.5

    # Collect flagged dismissals
    flagged_dismissals = [
        cls.to_dict()
        for cls in classifications
        if cls.requires_review
    ]

    # Analyze defect type patterns
    defect_pattern_analysis = {}
    if "defect_type" in df.columns:
        for cls in classifications:
            if not cls.defect_type:
                continue
            if cls.defect_type not in defect_pattern_analysis:
                defect_pattern_analysis[cls.defect_type] = {
                    "total_dismissals": 0,
                    "suspicious_dismissals": 0,
                    "avg_suspicion_score": 0.0,
                }
            pattern = defect_pattern_analysis[cls.defect_type]
            pattern["total_dismissals"] += 1
            if cls.requires_review:
                pattern["suspicious_dismissals"] += 1
            pattern["avg_suspicion_score"] += cls.suspicion_score

        for pattern in defect_pattern_analysis.values():
            if pattern["total_dismissals"] > 0:
                pattern["avg_suspicion_score"] /= pattern["total_dismissals"]

    state["inspector_stats"] = inspector_stats
    state["flagged_dismissals"] = flagged_dismissals
    state["defect_pattern_analysis"] = defect_pattern_analysis

    state["execution_log"].append({
        "step": "analyze_patterns",
        "timestamp": datetime.now().isoformat(),
        "inspectors_analyzed": len(inspector_stats),
        "flagged_dismissals_count": len(flagged_dismissals),
        "defect_types_analyzed": len(defect_pattern_analysis),
    })

    logger.info(
        f"[ANALYZE] Analyzed {len(inspector_stats)} inspectors, "
        f"flagged {len(flagged_dismissals)} dismissals"
    )
    return state


def claude_assess_node(state: DismissalAnalysisState) -> DismissalAnalysisState:
    """Use Claude to assess patterns and recommend coaching."""
    logger.info("[CLAUDE] Starting Claude assessment")

    inspector_stats = state["inspector_stats"]
    flagged_dismissals = state["flagged_dismissals"]
    classification_summary = state["classification_summary"]

    # Build context for Claude
    outlier_inspectors = [
        (insp_id, stats)
        for insp_id, stats in inspector_stats.items()
        if stats.flagged_for_review
    ]

    top_flagged = sorted(
        flagged_dismissals,
        key=lambda x: x.get("suspicion_score", 0),
        reverse=True,
    )[:5]

    prompt = f"""
Analyze the following dismissal pattern data from NYC SIM inspections and provide insights:

SUMMARY:
- Total dismissals analyzed: {sum(s.total_dismissals for s in inspector_stats.values())}
- Categories: {json.dumps(classification_summary, indent=2)}
- Flagged for review: {len(flagged_dismissals)}

OUTLIER INSPECTORS (above-average suspicious dismissal rate):
{json.dumps(
    [
        {{
            "inspector_id": insp_id,
            "total_dismissals": stats.total_dismissals,
            "suspicious_dismissals": stats.suspicious_dismissals,
            "suspicious_rate": round(stats.suspicious_rate, 3),
        }}
        for insp_id, stats in outlier_inspectors
    ],
    indent=2
) if outlier_inspectors else "None"}

TOP FLAGGED CASES (highest suspicion scores):
{json.dumps(top_flagged, indent=2) if top_flagged else "None"}

Based on this data:
1. Which inspector behaviors are concerning? Why?
2. What patterns suggest potential fraud or favoritism?
3. Which dismissals warrant immediate investigation?
4. What coaching or policy changes would address these issues?

Keep response to ~350 tokens focused on actionable insights.
"""

    try:
        client = ChatAnthropic(model="claude-haiku-4-5-20251001")
        message = client.invoke(prompt)
        assessment = message.content if hasattr(message, "content") else str(message)
    except Exception as e:
        logger.error(f"Claude assessment failed: {e}")
        assessment = f"Assessment unavailable: {str(e)}"

    # Extract key findings
    suspicious_summary = "\n".join(
        f"- {d['dismissal_id']}: {d['dismissal_reason'][:80]} "
        f"(suspicion={d['suspicion_score']}, inspector={d['inspector_id']})"
        for d in top_flagged
    )

    state["claude_pattern_assessment"] = assessment
    state["suspicious_case_summary"] = suspicious_summary
    state["claude_coaching_recommendations"] = assessment

    state["execution_log"].append({
        "step": "claude_assess",
        "timestamp": datetime.now().isoformat(),
        "assessment_tokens": len(assessment.split()),
    })

    logger.info("[CLAUDE] Assessment complete")
    return state


def generate_report_node(state: DismissalAnalysisState) -> DismissalAnalysisState:
    """Generate final structured JSON report."""
    logger.info("[REPORT] Generating final report")

    report = {
        "summary": {
            "total_dismissals": state["total_records"],
            "classifications": state["classification_summary"],
            "flagged_count": len(state["flagged_dismissals"]),
            "inspectors_analyzed": len(state["inspector_stats"]),
            "execution_time": (
                datetime.fromisoformat(
                    state["execution_log"][-1]["timestamp"]
                ) - datetime.fromisoformat(state["execution_log"][0]["timestamp"])
            ).total_seconds(),
        },
        "inspector_summary": {
            insp_id: {
                "total_dismissals": stats.total_dismissals,
                "dismissal_rate": round(stats.dismissal_rate, 3),
                "suspicious_dismissals": stats.suspicious_dismissals,
                "suspicious_rate": round(stats.suspicious_rate, 3),
                "flagged_for_review": stats.flagged_for_review,
            }
            for insp_id, stats in state["inspector_stats"].items()
        },
        "flagged_dismissals": state["flagged_dismissals"],
        "defect_patterns": state["defect_pattern_analysis"],
        "claude_assessment": state["claude_pattern_assessment"],
        "suspicious_cases_summary": state["suspicious_case_summary"],
        "execution_log": state["execution_log"],
    }

    state["final_report"] = report

    logger.info("[REPORT] Report generated successfully")
    return state


# ============================================================================
# EXECUTION HELPER
# ============================================================================


def run_dismissal_workflow(
    dismissals_fourfour: str = "p4u2-3jgx",
    violations_fourfour: str = "6kbp-uz6m",
    max_rows: int = 1000,
    borough_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the dismissal analysis workflow.

    Args:
        dismissals_fourfour: Dataset ID for dismissals (default: p4u2-3jgx)
        violations_fourfour: Dataset ID for violations (default: 6kbp-uz6m)
        max_rows: Max rows to fetch
        borough_filter: Optional borough to filter by (e.g., 'MANHATTAN')

    Returns:
        Final report dict with all results
    """
    logger.info("[START] Dismissal Analysis Workflow")

    workflow = create_dismissal_workflow()

    initial_state: DismissalAnalysisState = {
        "context": None,
        "dismissals_fourfour": dismissals_fourfour,
        "violations_fourfour": violations_fourfour,
        "max_rows": max_rows,
        "borough_filter": borough_filter,
        "dismissals_df": None,
        "violations_df": None,
        "joined_df": None,
        "total_records": 0,
        "classifications": [],
        "classification_summary": {},
        "inspector_stats": {},
        "flagged_dismissals": [],
        "defect_pattern_analysis": {},
        "claude_pattern_assessment": "",
        "claude_coaching_recommendations": "",
        "suspicious_case_summary": "",
        "final_report": {},
        "execution_log": [],
    }

    result = workflow.invoke(initial_state)

    logger.info("[COMPLETE] Dismissal Analysis Workflow")
    return result["final_report"]


if __name__ == "__main__":
    # Example execution
    logging.basicConfig(level=logging.INFO)
    report = run_dismissal_workflow(max_rows=500, borough_filter=None)
    print(json.dumps(report, indent=2, default=str))
