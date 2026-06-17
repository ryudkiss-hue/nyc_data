"""
Inspection Velocity Analysis Workflow (LangGraph).

Orchestrates:
1. Fetch inspections, violations, dismissals from Socrata
2. Group by inspector + date range
3. Compute metrics (velocity, quality, accuracy, efficiency)
4. Classify with VelocityClassifier
5. Query Claude for insights (~300 tokens) — "Who's underperforming? Why?"
6. Generate coaching recommendations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# STEP 1: Define Workflow State
# ============================================================================


@dataclass
class VelocityAnalysisContext:
    """Input context for velocity analysis."""
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    borough_filter: str | None = None  # "MANHATTAN", "BROOKLYN", etc. or None for all
    inspector_ids: list[str] | None = None  # Specific inspectors or None for all


class VelocityState(dict):
    """LangGraph state for velocity analysis workflow."""

    def __init__(self):
        super().__init__()
        # Input
        self["context"] = None  # VelocityAnalysisContext

        # Fetched data
        self["inspections_df"] = None  # pd.DataFrame
        self["violations_df"] = None
        self["dismissals_df"] = None
        self["fetch_status"] = "pending"

        # Computed metrics
        self["inspector_metrics"] = {}  # dict[inspector_id, list[VelocityMetrics]]
        self["metrics_status"] = "pending"

        # Classifications
        self["classifications"] = {}  # dict[inspector_id, VelocityClassification]
        self["summary_stats"] = {}  # High/Medium/Low counts, avg scores

        # Claude insights
        self["claude_assessment"] = ""  # Raw text response from Claude
        self["coaching_recommendations"] = {}  # dict[inspector_id, str]

        # Final output
        self["report"] = {}
        self["execution_log"] = []


# ============================================================================
# STEP 2: Helper Functions for Metric Computation
# ============================================================================


def compute_inspector_metrics(
    inspections: pd.DataFrame,
    violations: pd.DataFrame,
    dismissals: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    inspector_id: str,
) -> Any:  # Returns VelocityMetrics
    """
    Compute velocity metrics for one inspector in a period.

    Returns VelocityMetrics from velocity_classifier module.
    """
    from .velocity_classifier import VelocityMetrics

    # Filter to inspector + period
    insp_sub = inspections[
        (inspections.get("inspector_id") == inspector_id)
        & (pd.to_datetime(inspections.get("created_date", inspections.get("inspection_date", pd.Series())), errors="coerce") >= start_date)
        & (pd.to_datetime(inspections.get("created_date", inspections.get("inspection_date", pd.Series())), errors="coerce") <= end_date)
    ]

    if insp_sub.empty:
        return VelocityMetrics(
            inspector_id=inspector_id,
            inspector_name=None,
            period_start=start_date,
            period_end=end_date,
            data_quality_flag="LOW",
        )

    inspection_count = len(insp_sub)
    weeks = max((end_date - start_date).days / 7, 1.0)
    inspections_per_week = inspection_count / weeks

    # Violations for this inspector's inspections
    insp_ids = set(insp_sub.get("inspection_id", insp_sub.get("objectid", pd.Series())).dropna().unique())
    viol_sub = violations[violations.get("inspection_id", violations.get("objectid", pd.Series())).isin(insp_ids)]

    total_violations = len(viol_sub)
    violations_per_inspection = total_violations / max(inspection_count, 1)

    # Dismissals
    dism_sub = dismissals[dismissals.get("inspection_id", dismissals.get("objectid", pd.Series())).isin(insp_ids)]
    dismissal_count = len(dism_sub)
    dismissal_rate = dismissal_count / max(inspection_count, 1)

    # Accuracy (reopened violations)
    reopened_count = int(viol_sub.get("reopened", pd.Series()).fillna(0).sum()) if "reopened" in viol_sub.columns else 0
    reopened_rate = reopened_count / max(total_violations, 1)
    accuracy_ratio = max(0.0, (total_violations - reopened_count) / max(total_violations, 1))

    # Efficiency (time to close)
    avg_days_to_close = 0.0
    median_days_to_close = 0.0
    if "closed_date" in insp_sub.columns and "created_date" in insp_sub.columns:
        insp_sub_copy = insp_sub.copy()
        insp_sub_copy["days_to_close"] = (
            pd.to_datetime(insp_sub_copy["closed_date"], errors="coerce")
            - pd.to_datetime(insp_sub_copy["created_date"], errors="coerce")
        ).dt.days
        days = insp_sub_copy["days_to_close"].dropna()
        if not days.empty:
            avg_days_to_close = float(days.mean())
            median_days_to_close = float(days.median())

    # Consistency (std dev)
    velocity_std_dev = 0.0  # Would compute from weekly velocity trend if more data

    # Inspector name
    inspector_name = None
    if "inspector_name" in insp_sub.columns:
        names = insp_sub["inspector_name"].dropna().unique()
        if len(names) > 0:
            inspector_name = str(names[0])

    return VelocityMetrics(
        inspector_id=inspector_id,
        inspector_name=inspector_name,
        period_start=start_date,
        period_end=end_date,
        inspection_count=inspection_count,
        inspections_per_week=inspections_per_week,
        total_violations=total_violations,
        violations_per_inspection=violations_per_inspection,
        dismissal_count=dismissal_count,
        dismissal_rate=dismissal_rate,
        reopened_count=reopened_count,
        reopened_rate=reopened_rate,
        accuracy_ratio=accuracy_ratio,
        avg_days_to_close=avg_days_to_close,
        median_days_to_close=median_days_to_close,
        velocity_std_dev=velocity_std_dev,
        data_quality_flag="HIGH" if inspection_count >= 5 else "MEDIUM" if inspection_count >= 2 else "LOW",
        sample_size=inspection_count,
    )


# ============================================================================
# STEP 3: Workflow Nodes
# ============================================================================


def fetch_data(state: VelocityState) -> VelocityState:
    """Node 1: Fetch inspections, violations, dismissals from Socrata."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    logger.info("[FETCH] Fetching inspection data")
    ctx = state["context"]

    client = SocrataClient(SocrataConfig())

    # Build WHERE clauses
    where_inspection = f"created_date >= '{ctx.start_date.isoformat()}' AND created_date <= '{ctx.end_date.isoformat()}'"
    if ctx.borough_filter:
        where_inspection += f" AND upper(borough) = '{ctx.borough_filter.upper()}'"

    try:
        # Fetch inspections (fourfour: dntt-gqwq)
        insp_df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            "dntt-gqwq",
            max_rows=100000,
            where=where_inspection,
        )
        logger.info(f"[FETCH] Got {len(insp_df)} inspections")
        state["inspections_df"] = insp_df

        # Fetch violations (fourfour: 6kbp-uz6m)
        where_viol = f"created_date >= '{ctx.start_date.isoformat()}' AND created_date <= '{ctx.end_date.isoformat()}'"
        if ctx.borough_filter:
            where_viol += f" AND upper(borough) = '{ctx.borough_filter.upper()}'"
        viol_df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            "6kbp-uz6m",
            max_rows=200000,
            where=where_viol,
        )
        logger.info(f"[FETCH] Got {len(viol_df)} violations")
        state["violations_df"] = viol_df

        # Fetch dismissals (fourfour: p4u2-3jgx)
        where_dism = f"created_date >= '{ctx.start_date.isoformat()}' AND created_date <= '{ctx.end_date.isoformat()}'"
        if ctx.borough_filter:
            where_dism += f" AND upper(borough) = '{ctx.borough_filter.upper()}'"
        dism_df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            "p4u2-3jgx",
            max_rows=50000,
            where=where_dism,
        )
        logger.info(f"[FETCH] Got {len(dism_df)} dismissals")
        state["dismissals_df"] = dism_df

        state["fetch_status"] = "success"
    except Exception as e:
        logger.error(f"[FETCH] Error: {e}")
        state["fetch_status"] = f"error: {e}"
        state["inspections_df"] = pd.DataFrame()
        state["violations_df"] = pd.DataFrame()
        state["dismissals_df"] = pd.DataFrame()

    state["execution_log"].append({
        "step": "fetch_data",
        "timestamp": datetime.now().isoformat(),
        "status": state["fetch_status"],
        "inspections_count": len(state.get("inspections_df") or []),
        "violations_count": len(state.get("violations_df") or []),
        "dismissals_count": len(state.get("dismissals_df") or []),
    })

    return state


def compute_metrics(state: VelocityState) -> VelocityState:
    """Node 2: Compute metrics per inspector."""
    logger.info("[METRICS] Computing velocity metrics")
    ctx = state["context"]
    insp_df = state.get("inspections_df") or pd.DataFrame()
    viol_df = state.get("violations_df") or pd.DataFrame()
    dism_df = state.get("dismissals_df") or pd.DataFrame()

    if insp_df.empty:
        logger.warning("[METRICS] No inspection data to analyze")
        state["metrics_status"] = "no_data"
        state["execution_log"].append({
            "step": "compute_metrics",
            "timestamp": datetime.now().isoformat(),
            "status": "no_data",
            "inspector_count": 0,
        })
        return state

    # Identify inspectors
    inspector_col = "inspector_id" if "inspector_id" in insp_df.columns else "assigned_to"
    inspectors = insp_df[inspector_col].dropna().unique()

    if ctx.inspector_ids:
        inspectors = [i for i in inspectors if i in ctx.inspector_ids]

    metrics_by_inspector = {}
    for inspector_id in inspectors:
        m = compute_inspector_metrics(
            insp_df, viol_df, dism_df,
            ctx.start_date, ctx.end_date,
            str(inspector_id)
        )
        metrics_by_inspector[str(inspector_id)] = [m]  # Wrap in list for historical pattern

    state["inspector_metrics"] = metrics_by_inspector
    state["metrics_status"] = "success"

    logger.info(f"[METRICS] Computed metrics for {len(metrics_by_inspector)} inspectors")

    state["execution_log"].append({
        "step": "compute_metrics",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "inspector_count": len(metrics_by_inspector),
    })

    return state


def classify_performance(state: VelocityState) -> VelocityState:
    """Node 3: Classify performance using VelocityClassifier."""
    from .velocity_classifier import VelocityClassifier

    logger.info("[CLASSIFY] Classifying inspector performance")
    classifier = VelocityClassifier()

    classifications = {}
    for inspector_id, metrics_list in state.get("inspector_metrics", {}).items():
        if not metrics_list:
            continue
        current_metrics = metrics_list[-1]
        historical = metrics_list[:-1] if len(metrics_list) > 1 else None

        classification = classifier.classify(current_metrics, historical)
        classifications[inspector_id] = classification

    state["classifications"] = classifications

    # Summary stats
    tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    scores = []
    for c in classifications.values():
        tiers[c.performance_tier.value] += 1
        scores.append(c.composite_score)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    state["summary_stats"] = {
        "total_inspectors": len(classifications),
        "high_performers": tiers["HIGH"],
        "medium_performers": tiers["MEDIUM"],
        "low_performers": tiers["LOW"],
        "average_composite_score": round(avg_score, 1),
    }

    logger.info(
        f"[CLASSIFY] Results: {tiers['HIGH']} HIGH, {tiers['MEDIUM']} MEDIUM, {tiers['LOW']} LOW"
    )

    state["execution_log"].append({
        "step": "classify_performance",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "classifications": state["summary_stats"],
    })

    return state


def generate_claude_assessment(state: VelocityState) -> VelocityState:
    """Node 4: Query Claude for insights (~300 tokens)."""
    logger.info("[CLAUDE] Generating assessment")

    classifications = state.get("classifications", {})
    summary = state.get("summary_stats", {})

    if not classifications:
        state["claude_assessment"] = "No classification data to assess."
        return state

    # Build prompt for Claude
    low_performers = {
        k: v for k, v in classifications.items()
        if v.performance_tier.value == "LOW"
    }

    prompt = f"""
You are an NYC DOT Inspection Management expert. Analyze the following inspection velocity data and provide brief, actionable insights.

SUMMARY STATS:
- Total Inspectors: {summary.get('total_inspectors', 0)}
- High Performers: {summary.get('high_performers', 0)}
- Medium Performers: {summary.get('medium_performers', 0)}
- Low Performers: {summary.get('low_performers', 0)}
- Average Composite Score: {summary.get('average_composite_score', 0.0)}/100

LOW PERFORMERS (Requiring Attention):
"""

    for inspector_id, classification in list(low_performers.items())[:5]:  # Top 5
        prompt += f"""
Inspector {classification.inspector_name or inspector_id}:
  - Velocity: {classification.metrics.inspections_per_week:.1f} inspections/week
  - Violations per Inspection: {classification.metrics.violations_per_inspection:.2f}
  - Dismissal Rate: {classification.metrics.dismissal_rate*100:.1f}%
  - Reopened Rate: {classification.metrics.reopened_rate*100:.1f}%
  - Avg Days to Close: {classification.metrics.avg_days_to_close:.0f}
  - Flagged Issues: {', '.join(classification.flagged_issues)}
"""

    prompt += """
QUESTIONS:
1. Who are the top 2 underperforming inspectors and why?
2. What are the most critical issues limiting velocity across the team?
3. What immediate actions would improve performance?

Keep response to ~300 tokens. Be specific and actionable.
"""

    try:
        from langchain_anthropic import ChatAnthropic
        client = ChatAnthropic(model="claude-haiku-4-5-20251001")
        message = client.invoke(prompt)
        assessment = message.content if hasattr(message, "content") else str(message)
        state["claude_assessment"] = assessment
        logger.info("[CLAUDE] Assessment generated successfully")
    except ImportError:
        logger.warning("[CLAUDE] langchain_anthropic not installed; skipping Claude assessment")
        state["claude_assessment"] = "(Claude assessment skipped: langchain_anthropic not installed)"
    except Exception as e:
        logger.error(f"[CLAUDE] Error: {e}")
        state["claude_assessment"] = f"(Error generating assessment: {e})"

    state["execution_log"].append({
        "step": "generate_claude_assessment",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "assessment_preview": state["claude_assessment"][:200] + "..." if state["claude_assessment"] else "",
    })

    return state


def generate_recommendations(state: VelocityState) -> VelocityState:
    """Node 5: Generate coaching recommendations for each underperformer."""
    logger.info("[RECOMMENDATIONS] Generating coaching recommendations")

    recommendations = {}
    for inspector_id, classification in state.get("classifications", {}).items():
        rec = (
            f"Performance Tier: {classification.performance_tier.value}\n"
            f"Composite Score: {classification.composite_score:.1f}/100\n"
            f"Coaching Focus: {classification.coaching_focus}\n"
        )
        if classification.flagged_issues:
            rec += f"Issues: {', '.join(classification.flagged_issues)}\n"
        recommendations[inspector_id] = rec

    state["coaching_recommendations"] = recommendations

    logger.info(f"[RECOMMENDATIONS] Generated for {len(recommendations)} inspectors")

    state["execution_log"].append({
        "step": "generate_recommendations",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "recommendation_count": len(recommendations),
    })

    return state


def build_report(state: VelocityState) -> VelocityState:
    """Node 6: Build final report."""
    logger.info("[REPORT] Building report")

    report = {
        "timestamp": datetime.now().isoformat(),
        "period": {
            "start_date": state["context"].start_date.isoformat() if state["context"] else None,
            "end_date": state["context"].end_date.isoformat() if state["context"] else None,
        },
        "summary": state.get("summary_stats", {}),
        "classifications": {
            k: v.to_dict() for k, v in state.get("classifications", {}).items()
        },
        "claude_assessment": state.get("claude_assessment", ""),
        "coaching_recommendations": state.get("coaching_recommendations", {}),
        "execution_log": state.get("execution_log", []),
    }

    state["report"] = report

    state["execution_log"].append({
        "step": "build_report",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    })

    return state


# ============================================================================
# STEP 4: Build Graph
# ============================================================================


def build_velocity_analysis_graph():
    """Construct and return the LangGraph workflow."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        logger.error("LangGraph not installed. Install with: pip install langgraph")
        return None

    graph = StateGraph(VelocityState)

    # Add nodes
    graph.add_node("fetch_data", fetch_data)
    graph.add_node("compute_metrics", compute_metrics)
    graph.add_node("classify_performance", classify_performance)
    graph.add_node("generate_claude_assessment", generate_claude_assessment)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("build_report", build_report)

    # Add edges (linear flow)
    graph.add_edge("fetch_data", "compute_metrics")
    graph.add_edge("compute_metrics", "classify_performance")
    graph.add_edge("classify_performance", "generate_claude_assessment")
    graph.add_edge("generate_claude_assessment", "generate_recommendations")
    graph.add_edge("generate_recommendations", "build_report")
    graph.add_edge("build_report", END)

    # Set entry point
    graph.set_entry_point("fetch_data")

    return graph.compile()


# ============================================================================
# STEP 5: Public API
# ============================================================================


def run_velocity_analysis(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    borough_filter: str | None = None,
    inspector_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the complete velocity analysis workflow.

    Args:
        start_date: Analysis period start
        end_date: Analysis period end
        borough_filter: Optional borough ("MANHATTAN", "BROOKLYN", etc.)
        inspector_ids: Optional list of specific inspector IDs to analyze

    Returns:
        Final report dict with classifications, Claude assessment, recommendations, logs
    """
    graph = build_velocity_analysis_graph()
    if not graph:
        return {"error": "LangGraph not available"}

    # Initialize state
    state = VelocityState()
    state["context"] = VelocityAnalysisContext(
        start_date=start_date,
        end_date=end_date,
        borough_filter=borough_filter,
        inspector_ids=inspector_ids,
    )

    # Run workflow
    logger.info(
        f"[WORKFLOW] Starting velocity analysis: {start_date} to {end_date} "
        f"(borough={borough_filter}, inspectors={inspector_ids})"
    )

    try:
        final_state = graph.invoke(state)
        return final_state.get("report", {})
    except Exception as e:
        logger.error(f"[WORKFLOW] Error: {e}")
        return {"error": str(e), "execution_log": state.get("execution_log", [])}
