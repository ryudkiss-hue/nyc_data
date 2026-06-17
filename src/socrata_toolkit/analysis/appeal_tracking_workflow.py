"""
Appeal & Reinspection Tracking Workflow: LangGraph + Claude + spaCy

Full integration for tracking NYC inspector performance through appeals:
  1. Fetch reinspection + dismissals datasets (gx72-kirf, p4u2-3jgx)
  2. Classify appeal outcomes with AppealOutcomeClassifier (spaCy)
  3. Compute inspector-level statistics with performance signals
  4. Identify outliers: High overturn rate, procedural error patterns, trend degradation
  5. Claude assessment: "Who needs coaching? Systemic process issues?" (~350 tokens)
  6. Generate coaching recommendations + process improvements

Token cost: ~600-800 tokens for 100+ appeals
Execution time: ~4-6 seconds
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, TypedDict

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph

from socrata_toolkit.analysis.appeal_classifier import (
    AppealOutcomeClassifier,
    InspectorAppealAnalyzer,
)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITIONS
# ============================================================================

class AppealTrackingState(TypedDict):
    """LangGraph state for appeal & reinspection workflow."""
    # Input context
    context: dict[str, Any] | None
    max_rows: int
    include_coaching_plan: bool

    # Fetched data
    reinspection_df: pd.DataFrame | None
    dismissal_df: pd.DataFrame | None
    combined_appeals_df: pd.DataFrame | None
    total_appeals: int

    # Classification and analysis
    appeal_classifications: list[dict]
    inspector_stats: dict[str, dict]  # Serializable version
    outliers: list[dict]
    systemic_issues: dict[str, Any]

    # Claude assessments
    claude_assessment: str  # Initial performance analysis
    coaching_recommendations: str  # Detailed coaching plan (~350 tokens)
    next_action: str  # "complete" | "escalate_training" | "process_review" | "end"

    # Output
    final_report: dict
    execution_log: list[dict]


def create_appeal_tracking_workflow():
    """Create and return the appeal & reinspection tracking workflow."""
    workflow = StateGraph(AppealTrackingState)

    # Add nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("classify_appeals", classify_appeals_node)
    workflow.add_node("compute_inspector_stats", compute_inspector_stats_node)
    workflow.add_node("identify_outliers", identify_outliers_node)
    workflow.add_node("claude_assess", claude_assess_node)
    workflow.add_node("generate_coaching_plan", generate_coaching_plan_node)
    workflow.add_node("generate_report", generate_report_node)

    # Add edges
    workflow.add_edge("fetch_data", "classify_appeals")
    workflow.add_edge("classify_appeals", "compute_inspector_stats")
    workflow.add_edge("compute_inspector_stats", "identify_outliers")
    workflow.add_edge("identify_outliers", "claude_assess")
    workflow.add_edge("claude_assess", "generate_coaching_plan")
    workflow.add_edge("generate_coaching_plan", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def fetch_data_node(state: AppealTrackingState) -> AppealTrackingState:
    """Fetch reinspection and dismissal datasets from Socrata."""
    logger.info(f"[FETCH] Fetching appeal/reinspection data (max_rows={state['max_rows']})")

    client = SocrataClient(SocrataConfig())

    # Fetch reinspection data (gx72-kirf)
    reinspection_df = None
    try:
        reinspection_df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            "gx72-kirf",
            max_rows=state["max_rows"]
        )
        logger.info(f"[FETCH] Fetched {len(reinspection_df)} reinspection records")
    except Exception as e:
        logger.warning(f"[FETCH] Failed to fetch reinspection data: {e}")

    # Fetch dismissal data (p4u2-3jgx)
    dismissal_df = None
    try:
        dismissal_df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            "p4u2-3jgx",
            max_rows=state["max_rows"]
        )
        logger.info(f"[FETCH] Fetched {len(dismissal_df)} dismissal records")
    except Exception as e:
        logger.warning(f"[FETCH] Failed to fetch dismissal data: {e}")

    state["reinspection_df"] = reinspection_df
    state["dismissal_df"] = dismissal_df

    # Combine datasets for unified analysis
    combined = []
    if reinspection_df is not None:
        reinspection_df["_dataset"] = "reinspection"
        combined.append(reinspection_df)
    if dismissal_df is not None:
        dismissal_df["_dataset"] = "dismissal"
        combined.append(dismissal_df)

    if combined:
        state["combined_appeals_df"] = pd.concat(combined, axis=0, ignore_index=True)
        state["total_appeals"] = len(state["combined_appeals_df"])
    else:
        state["combined_appeals_df"] = None
        state["total_appeals"] = 0

    state["execution_log"].append({
        "step": "fetch_data",
        "timestamp": datetime.now().isoformat(),
        "reinspections": len(reinspection_df) if reinspection_df is not None else 0,
        "dismissals": len(dismissal_df) if dismissal_df is not None else 0,
        "total_appeals": state["total_appeals"],
    })

    logger.info(f"[FETCH] Total appeals combined: {state['total_appeals']}")
    return state


def classify_appeals_node(state: AppealTrackingState) -> AppealTrackingState:
    """Classify appeal outcomes and reasons using AppealOutcomeClassifier."""
    logger.info("[CLASSIFY] Classifying appeal outcomes")

    if state["combined_appeals_df"] is None or len(state["combined_appeals_df"]) == 0:
        logger.warning("[CLASSIFY] No data to classify")
        state["execution_log"].append({
            "step": "classify_appeals",
            "error": "No combined appeals dataframe",
            "timestamp": datetime.now().isoformat(),
        })
        return state

    df = state["combined_appeals_df"]
    classifier = AppealOutcomeClassifier()

    # Find text column to classify (try common names)
    text_column = None
    for col in ["description", "appeal_decision", "decision_notes", "notes", "remarks"]:
        if col in df.columns:
            text_column = col
            break

    if not text_column:
        logger.warning("[CLASSIFY] No suitable text column found")
        return state

    # Classify all appeals
    classifications = classifier.batch_classify(
        df[text_column].fillna("").astype(str).tolist()
    )

    # Enrich dataframe with classification results
    df_enriched = df.copy()
    df_enriched["appeal_resolution"] = [c.resolution.value for c in classifications]
    df_enriched["appeal_reason"] = [c.reason.value for c in classifications]
    df_enriched["resolution_confidence"] = [c.resolution_confidence for c in classifications]
    df_enriched["reason_confidence"] = [c.reason_confidence for c in classifications]
    df_enriched["keywords_matched"] = [c.keywords_matched for c in classifications]

    state["combined_appeals_df"] = df_enriched

    # Build classification summary
    resolution_counts = df_enriched["appeal_resolution"].value_counts().to_dict()
    reason_counts = df_enriched["appeal_reason"].value_counts().to_dict()

    classifications_summary = {
        "total_classified": len(classifications),
        "resolution_breakdown": resolution_counts,
        "reason_breakdown": reason_counts,
    }

    # Store for later
    state["appeal_classifications"] = [
        {
            "text": c.original_text[:100],
            "resolution": c.resolution.value,
            "reason": c.reason.value,
            "resolution_confidence": c.resolution_confidence,
        }
        for c in classifications[:50]  # Store first 50 for report
    ]

    state["execution_log"].append({
        "step": "classify_appeals",
        "timestamp": datetime.now().isoformat(),
        "total_classified": len(classifications),
        "summary": classifications_summary,
    })

    logger.info(
        f"[CLASSIFY] Classified {len(classifications)} appeals; "
        f"overturn rate: {resolution_counts.get('overturned', 0) / len(classifications):.1%}"
    )
    return state


def compute_inspector_stats_node(state: AppealTrackingState) -> AppealTrackingState:
    """Compute inspector-level statistics and performance signals."""
    logger.info("[STATS] Computing inspector statistics")

    if state["combined_appeals_df"] is None:
        return state

    df = state["combined_appeals_df"]

    # Check for inspector columns
    inspector_id_col = None
    inspector_name_col = None
    for col in ["inspector_id", "inspector", "assigned_to"]:
        if col in df.columns:
            inspector_id_col = col
            break
    for col in ["inspector_name", "inspector", "assigned_to"]:
        if col in df.columns:
            inspector_name_col = col
            break

    if not inspector_id_col or not inspector_name_col:
        logger.warning("[STATS] Inspector ID/name columns not found")
        state["inspector_stats"] = {}
        return state

    analyzer = InspectorAppealAnalyzer()

    # Compute stats
    try:
        stats = analyzer.compute_inspector_stats(
            df,
            inspector_id_col=inspector_id_col,
            inspector_name_col=inspector_name_col,
            outcome_col=[c for c in df.columns if "description" in c or "notes" in c][0] if any(c in df.columns for c in ["description", "notes"]) else "appeal_resolution",
            date_col="created_date" if "created_date" in df.columns else None
        )

        # Convert to serializable dict
        serializable_stats = {}
        for inspector_id, stat in stats.items():
            serializable_stats[inspector_id] = {
                "inspector_id": stat.inspector_id,
                "inspector_name": stat.inspector_name,
                "total_inspections": stat.total_inspections,
                "total_appeals": stat.total_appeals,
                "appeal_rate": stat.appeal_rate,
                "overturn_rate": stat.overturn_rate,
                "modification_rate": stat.modification_rate,
                "upheld_rate": stat.upheld_rate,
                "recent_trend": stat.recent_trend.value,
                "reliability": stat.reliability,
                "coaching_needed": stat.coaching_needed,
                "coaching_reason": stat.coaching_reason,
            }

        state["inspector_stats"] = serializable_stats

        # Compute systemic issues
        systemic = analyzer.compute_systemic_issues(df)
        state["systemic_issues"] = systemic

    except Exception as e:
        logger.error(f"[STATS] Failed to compute inspector stats: {e}")
        state["inspector_stats"] = {}
        state["systemic_issues"] = {}

    state["execution_log"].append({
        "step": "compute_inspector_stats",
        "timestamp": datetime.now().isoformat(),
        "inspectors_analyzed": len(state["inspector_stats"]),
    })

    logger.info(f"[STATS] Computed stats for {len(state['inspector_stats'])} inspectors")
    return state


def identify_outliers_node(state: AppealTrackingState) -> AppealTrackingState:
    """Identify inspectors with concerning performance signals."""
    logger.info("[OUTLIERS] Identifying performance outliers")

    outliers = []

    for inspector_id, stat in state["inspector_stats"].items():
        if stat.get("coaching_needed"):
            outliers.append({
                "inspector_id": inspector_id,
                "inspector_name": stat.get("inspector_name"),
                "overturn_rate": stat.get("overturn_rate"),
                "total_appeals": stat.get("total_appeals"),
                "reason": stat.get("coaching_reason"),
                "trend": stat.get("recent_trend"),
            })

    # Sort by overturn rate descending
    outliers.sort(key=lambda x: x.get("overturn_rate", 0), reverse=True)

    state["outliers"] = outliers[:10]  # Top 10 outliers

    state["execution_log"].append({
        "step": "identify_outliers",
        "timestamp": datetime.now().isoformat(),
        "outliers_count": len(outliers),
    })

    logger.info(f"[OUTLIERS] Identified {len(outliers)} performance outliers")
    return state


def claude_assess_node(state: AppealTrackingState) -> AppealTrackingState:
    """Claude: analyze performance patterns and identify coaching needs."""
    logger.info("[CLAUDE] Running performance assessment")

    if not state["outliers"] and not state["systemic_issues"]:
        logger.warning("[CLAUDE] No outliers or systemic issues to assess")
        state["claude_assessment"] = "No significant performance issues detected."
        return state

    # Build assessment prompt
    outliers_text = _format_outliers(state["outliers"])
    systemic_text = _format_systemic_issues(state["systemic_issues"])

    prompt = f"""
You are a NYC DOT quality assurance manager analyzing inspector appeal outcomes.
Review this performance data and provide actionable coaching insights.

TOP PERFORMANCE OUTLIERS:
{outliers_text}

SYSTEMIC PROCESS ISSUES:
{systemic_text}

Based on this analysis:
1. Which 2-3 inspectors need immediate coaching? Why?
2. What are the top 2-3 systemic process issues affecting all inspectors?
3. What specific coaching interventions would have the highest impact?
4. Are there systemic process improvements needed beyond individual coaching?

Be concise (~300 tokens). Cite specific percentages and reasons.
Focus on actionable next steps, not just diagnosis.
"""

    try:
        client = ChatAnthropic(model="claude-haiku-4-5-20251001")
        message = client.invoke(prompt)
        assessment = message.content
    except Exception as e:
        logger.error(f"[CLAUDE] Claude invocation failed: {e}")
        assessment = "Unable to generate assessment."

    state["claude_assessment"] = assessment

    # Determine next action
    assessment_lower = assessment.lower()
    if "procedural" in assessment_lower or "process" in assessment_lower:
        state["next_action"] = "process_review"
    elif "training" in assessment_lower or "coaching" in assessment_lower:
        state["next_action"] = "escalate_training"
    else:
        state["next_action"] = "complete"

    state["execution_log"].append({
        "step": "claude_assess",
        "timestamp": datetime.now().isoformat(),
        "next_action": state["next_action"],
    })

    logger.info(f"[CLAUDE] Assessment complete (next_action={state['next_action']})")
    return state


def generate_coaching_plan_node(state: AppealTrackingState) -> AppealTrackingState:
    """Generate detailed coaching recommendations for outliers."""
    logger.info("[COACHING] Generating coaching recommendations")

    if not state.get("include_coaching_plan") or not state["outliers"]:
        state["coaching_recommendations"] = "No coaching plan generated."
        return state

    recommendations = []

    for outlier in state["outliers"][:5]:  # Top 5 outliers
        inspector_name = outlier.get("inspector_name", "Unknown")
        overturn_rate = outlier.get("overturn_rate", 0)
        reason = outlier.get("reason", "Performance concern")
        trend = outlier.get("trend", "stable")

        if overturn_rate > 0.3:
            recs = [
                "Document all inspection findings with photo evidence",
                "Implement peer review before closing high-risk tickets",
                "Attend procedural accuracy refresher training",
            ]
        elif overturn_rate > 0.2:
            recs = [
                "Review standard severity assessment criteria",
                "Shadowing with high-performing inspector (5 inspections)",
            ]
        else:
            recs = [
                "General quality assurance review",
            ]

        recommendations.append({
            "inspector": inspector_name,
            "overturn_rate": f"{overturn_rate:.1%}",
            "reason": reason,
            "recommendations": recs,
        })

    coaching_text = _format_coaching_plan(recommendations)
    state["coaching_recommendations"] = coaching_text

    state["execution_log"].append({
        "step": "generate_coaching_plan",
        "timestamp": datetime.now().isoformat(),
        "inspectors_coached": len(recommendations),
    })

    logger.info(f"[COACHING] Generated coaching plan for {len(recommendations)} inspectors")
    return state


def generate_report_node(state: AppealTrackingState) -> AppealTrackingState:
    """Generate final structured JSON report."""
    logger.info("[REPORT] Generating final report")

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_appeals": state["total_appeals"],
            "appeals_analyzed": len(state["combined_appeals_df"]) if state["combined_appeals_df"] is not None else 0,
            "inspectors_analyzed": len(state["inspector_stats"]),
            "outliers_identified": len(state["outliers"]),
        },
        "classification_summary": {
            c["resolution"]: sum(1 for x in state["appeal_classifications"] if x["resolution"] == c["resolution"])
            for c in state["appeal_classifications"]
        } if state["appeal_classifications"] else {},
        "outlier_performance": state["outliers"][:5],
        "systemic_issues": state["systemic_issues"],
        "claude_assessment": state["claude_assessment"],
        "coaching_recommendations": state["coaching_recommendations"],
        "next_action": state["next_action"],
    }

    state["final_report"] = report

    state["execution_log"].append({
        "step": "generate_report",
        "timestamp": datetime.now().isoformat(),
        "report_size": len(json.dumps(report)),
    })

    logger.info("[REPORT] Report generation complete")
    return state


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_outliers(outliers: list[dict]) -> str:
    """Format outliers for Claude prompt."""
    if not outliers:
        return "No outliers detected."

    lines = []
    for outlier in outliers[:5]:
        lines.append(
            f"- {outlier['inspector_name']}: {outlier['overturn_rate']:.1%} overturn rate "
            f"({outlier['total_appeals']} appeals) - {outlier['reason']}"
        )
    return "\n".join(lines)


def _format_systemic_issues(issues: dict[str, Any]) -> str:
    """Format systemic issues for Claude prompt."""
    if not issues:
        return "No systemic issues identified."

    lines = []
    if "overall_reversal_rate" in issues:
        lines.append(f"Overall reversal rate: {issues['overall_reversal_rate']:.1%}")
    if "reversal_rate_by_reason" in issues:
        for reason, rate in list(issues["reversal_rate_by_reason"].items())[:3]:
            lines.append(f"  - {reason}: {rate:.1%}")
    if "recommended_improvements" in issues:
        for improvement in issues["recommended_improvements"]:
            lines.append(f"- {improvement}")

    return "\n".join(lines)


def _format_coaching_plan(recommendations: list[dict]) -> str:
    """Format coaching plan."""
    if not recommendations:
        return "No coaching recommendations."

    lines = ["COACHING PLAN:\n"]
    for rec in recommendations:
        lines.append(f"\n{rec['inspector']} (Overturn Rate: {rec['overturn_rate']})")
        lines.append(f"Reason: {rec['reason']}")
        lines.append("Recommended Actions:")
        for action in rec["recommendations"]:
            lines.append(f"  • {action}")

    return "\n".join(lines)
