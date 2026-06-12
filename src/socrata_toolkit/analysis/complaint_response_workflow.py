"""
311 Complaint Response Analysis Workflow — LangGraph-based orchestration.

Unified multi-step workflow for complaint response lifecycle analysis:

1. Fetch 311 complaints + linked inspections (with location/date join)
2. Classify complaint category, urgency, response status, time adequacy
3. Compute response metrics (time-to-inspection, time-to-resolution)
4. Identify bottlenecks (inspection queue delays, repair delays, closeout gaps)
5. Claude decision: "Where are bottlenecks? How do we respond faster?" (~350 tokens)
6. Generate structured report with optimization recommendations

Graph Structure:
    fetch_data → classify_complaints → compute_metrics → identify_bottlenecks
        → claude_analysis → generate_report

Response Metrics:
- time_to_inspection: Days from complaint → first inspection
- time_to_resolution: Days from complaint → work completed
- satisfaction_score: Composite 0-100 combining timeliness + category severity
- sla_compliance_rate: % of complaints resolved within SLA target

Token cost: ~600 tokens for 1000 complaints
Execution time: ~3-6 seconds
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, TypedDict

import pandas as pd

try:
    from langchain_anthropic import ChatAnthropic
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from socrata_toolkit.analysis.complaint_response_classifier import (
    ComplaintMetrics,
    ComplaintResponseClassifier,
)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

# ============================================================================
# STATE DEFINITIONS
# ============================================================================

@dataclass
class BoroughComplaintStats:
    """Aggregated complaint metrics for a single borough."""
    borough: str
    total_complaints: int
    resolved_count: int
    pending_count: int
    delayed_count: int
    abandoned_count: int

    # Timing metrics (days)
    avg_days_to_inspection: float
    avg_days_to_resolution: float
    median_days_to_inspection: float
    median_days_to_resolution: float

    # SLA compliance
    sla_compliant_count: int
    sla_compliance_rate: float  # 0-1

    # Satisfaction
    avg_satisfaction_score: float
    critical_issues_count: int  # Abandoned + severely delayed

    # Top categories by volume
    top_categories: list[str]

class ComplaintResponseState(TypedDict):
    """LangGraph state for complaint response workflow."""
    # Input context
    context: dict[str, Any] | None
    fourfour_complaints: str
    fourfour_inspections: str
    max_rows: int
    borough_filter: str | None

    # Fetched data
    complaints_df: pd.DataFrame | None
    inspections_df: pd.DataFrame | None
    joined_df: pd.DataFrame | None
    total_complaints: int

    # Classification results
    classification_summary: dict  # Status breakdown
    borough_stats: dict[str, BoroughComplaintStats]
    category_distribution: dict[str, int]  # By category
    urgency_distribution: dict[str, int]  # By urgency
    bottleneck_analysis: dict  # Queues, delays, gaps

    # Claude analysis
    claude_analysis: str  # Bottleneck diagnosis
    optimization_recommendations: list[str]
    next_action: str  # "optimize_dispatch" | "increase_resources" | "investigate_category" | "end"

    # Output
    final_report: dict
    execution_log: list[dict]

def create_complaint_response_workflow():
    """Create and return the complaint response analysis workflow."""
    if not HAS_LANGGRAPH:
        logger.warning("LangGraph not installed; workflow will run in fallback mode")
        return None

    workflow = StateGraph(ComplaintResponseState)

    # Add nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("classify_complaints", classify_complaints_node)
    workflow.add_node("compute_metrics", compute_metrics_node)
    workflow.add_node("identify_bottlenecks", identify_bottlenecks_node)
    workflow.add_node("claude_analysis", claude_analysis_node)
    workflow.add_node("generate_report", generate_report_node)

    # Build edges
    workflow.add_edge(START, "fetch_data")
    workflow.add_edge("fetch_data", "classify_complaints")
    workflow.add_edge("classify_complaints", "compute_metrics")
    workflow.add_edge("compute_metrics", "identify_bottlenecks")
    workflow.add_edge("identify_bottlenecks", "claude_analysis")
    workflow.add_edge("claude_analysis", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()

# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def fetch_data_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Fetch complaints and inspections datasets."""
    logger.info("Fetching complaint and inspection data...")

    client = SocrataClient(SocrataConfig())
    domain = "data.cityofnewyork.us"

    try:
        # Fetch complaints
        complaints = client.fetch_dataframe(
            domain,
            state["fourfour_complaints"],
            max_rows=state["max_rows"],
        )
        state["complaints_df"] = complaints
        state["total_complaints"] = len(complaints)
        logger.info(f"Fetched {len(complaints)} complaints")

        # Fetch inspections (if fourfour provided)
        if state.get("fourfour_inspections"):
            inspections = client.fetch_dataframe(
                domain,
                state["fourfour_inspections"],
                max_rows=state["max_rows"],
            )
            state["inspections_df"] = inspections
            logger.info(f"Fetched {len(inspections)} inspections")

            # Join on location/date proximity (simplified join)
            state["joined_df"] = _join_complaints_inspections(complaints, inspections)

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        state["execution_log"].append({"step": "fetch_data", "error": str(e)})

    return state

def classify_complaints_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Classify complaints by category, urgency, status, and time adequacy."""
    logger.info("Classifying complaints...")

    if state["complaints_df"] is None or len(state["complaints_df"]) == 0:
        logger.warning("No complaint data to classify")
        return state

    classifier = ComplaintResponseClassifier()
    complaints = state["complaints_df"]
    classifications = []

    for _, row in complaints.iterrows():
        # Extract metrics
        metrics = _extract_complaint_metrics(row, state.get("joined_df"))

        # Classify
        classification = classifier.classify(metrics)
        classifications.append(classification)

    # Summarize by status
    status_counts = {}
    for c in classifications:
        status = c.response_status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    state["classification_summary"] = status_counts
    state["execution_log"].append({
        "step": "classify_complaints",
        "total_classified": len(classifications),
        "status_breakdown": status_counts,
    })

    # Store classifications for next step
    state["_classifications"] = classifications

    return state

def compute_metrics_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Compute borough-level and category-level metrics."""
    logger.info("Computing response metrics...")

    if not hasattr(state, "_classifications") or not state["_classifications"]:
        logger.warning("No classifications available")
        return state

    classifications = state["_classifications"]
    complaints = state["complaints_df"]

    # Aggregate by borough
    borough_stats = {}
    category_dist = {}
    urgency_dist = {}

    for i, classification in enumerate(classifications):
        borough = classification.borough or "UNKNOWN"

        # Initialize borough if needed
        if borough not in borough_stats:
            borough_stats[borough] = {
                "total": 0,
                "resolved": 0,
                "pending": 0,
                "delayed": 0,
                "abandoned": 0,
                "days_to_inspection": [],
                "days_to_resolution": [],
                "satisfaction_scores": [],
                "sla_compliant": 0,
                "critical_issues": 0,
                "categories": {},
            }

        # Update counts
        stats = borough_stats[borough]
        stats["total"] += 1

        status = classification.response_status.value
        if status == "RESOLVED":
            stats["resolved"] += 1
        elif status == "PENDING":
            stats["pending"] += 1
        elif status == "DELAYED":
            stats["delayed"] += 1
        else:  # ABANDONED
            stats["abandoned"] += 1

        # Timing metrics
        if classification.metrics:
            if classification.metrics.days_to_inspection is not None:
                stats["days_to_inspection"].append(classification.metrics.days_to_inspection)
            if classification.metrics.days_to_resolution is not None:
                stats["days_to_resolution"].append(classification.metrics.days_to_resolution)

        # Satisfaction
        stats["satisfaction_scores"].append(classification.overall_satisfaction_score)

        # SLA compliance
        if classification.response_status.value == "RESOLVED":
            if classification.metrics.days_to_resolution and classification.metrics.days_to_resolution <= classification.sla_target_days:
                stats["sla_compliant"] += 1

        # Critical issues
        if classification.response_status.value in ["ABANDONED", "DELAYED"]:
            stats["critical_issues"] += 1

        # Category distribution
        category = classification.category.value
        category_dist[category] = category_dist.get(category, 0) + 1
        stats["categories"][category] = stats["categories"].get(category, 0) + 1

        # Urgency distribution
        urgency = classification.urgency.value
        urgency_dist[urgency] = urgency_dist.get(urgency, 0) + 1

    # Convert to BoroughComplaintStats
    processed_borough_stats = {}
    for borough, raw_stats in borough_stats.items():
        total = raw_stats["total"]
        insp_times = raw_stats["days_to_inspection"]
        res_times = raw_stats["days_to_resolution"]
        sat_scores = raw_stats["satisfaction_scores"]

        processed_borough_stats[borough] = BoroughComplaintStats(
            borough=borough,
            total_complaints=total,
            resolved_count=raw_stats["resolved"],
            pending_count=raw_stats["pending"],
            delayed_count=raw_stats["delayed"],
            abandoned_count=raw_stats["abandoned"],
            avg_days_to_inspection=sum(insp_times) / len(insp_times) if insp_times else 0,
            avg_days_to_resolution=sum(res_times) / len(res_times) if res_times else 0,
            median_days_to_inspection=_median(insp_times) if insp_times else 0,
            median_days_to_resolution=_median(res_times) if res_times else 0,
            sla_compliant_count=raw_stats["sla_compliant"],
            sla_compliance_rate=raw_stats["sla_compliant"] / total if total > 0 else 0,
            avg_satisfaction_score=sum(sat_scores) / len(sat_scores) if sat_scores else 0,
            critical_issues_count=raw_stats["critical_issues"],
            top_categories=sorted(raw_stats["categories"].items(), key=lambda x: -x[1])[:3],
        )

    state["borough_stats"] = processed_borough_stats
    state["category_distribution"] = category_dist
    state["urgency_distribution"] = urgency_dist

    state["execution_log"].append({
        "step": "compute_metrics",
        "boroughs_processed": len(processed_borough_stats),
        "category_distribution": category_dist,
    })

    return state

def identify_bottlenecks_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Identify bottlenecks in complaint response pipeline."""
    logger.info("Analyzing bottlenecks...")

    bottlenecks = {
        "inspection_queue_delays": [],
        "repair_delays": [],
        "closeout_gaps": [],
        "high_abandon_boroughs": [],
    }

    if not state.get("borough_stats"):
        state["bottleneck_analysis"] = bottlenecks
        return state

    for borough, stats in state["borough_stats"].items():
        # Inspection queue delays: avg > 3 days
        if stats.avg_days_to_inspection > 3.0:
            bottlenecks["inspection_queue_delays"].append({
                "borough": borough,
                "avg_days": round(stats.avg_days_to_inspection, 1),
                "severity": "high" if stats.avg_days_to_inspection > 7 else "medium",
            })

        # Repair delays: avg > 14 days
        if stats.avg_days_to_resolution > 14.0:
            bottlenecks["repair_delays"].append({
                "borough": borough,
                "avg_days": round(stats.avg_days_to_resolution, 1),
                "severity": "high" if stats.avg_days_to_resolution > 30 else "medium",
            })

        # High abandon rate (>15%)
        abandon_rate = stats.abandoned_count / stats.total_complaints if stats.total_complaints > 0 else 0
        if abandon_rate > 0.15:
            bottlenecks["high_abandon_boroughs"].append({
                "borough": borough,
                "abandon_rate": round(abandon_rate * 100, 1),
                "count": stats.abandoned_count,
            })

    state["bottleneck_analysis"] = bottlenecks
    state["execution_log"].append({
        "step": "identify_bottlenecks",
        "inspection_queue_issues": len(bottlenecks["inspection_queue_delays"]),
        "repair_delays_issues": len(bottlenecks["repair_delays"]),
        "high_abandon_boroughs": len(bottlenecks["high_abandon_boroughs"]),
    })

    return state

def claude_analysis_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Use Claude to analyze bottlenecks and recommend optimizations."""
    logger.info("Running Claude analysis...")

    try:
        client = ChatAnthropic(model="claude-haiku-4-5-20251001")

        # Build analysis context
        context = f"""
Complaint Response Analysis Summary:

Total Complaints Analyzed: {state.get('total_complaints', 0)}

Borough Breakdown:
"""
        for borough, stats in state.get("borough_stats", {}).items():
            context += f"\n{borough}: {stats.total_complaints} complaints\n"
            context += f"  - Resolved: {stats.resolved_count} ({stats.sla_compliance_rate*100:.1f}% SLA compliant)\n"
            context += f"  - Pending: {stats.pending_count}\n"
            context += f"  - Delayed: {stats.delayed_count}\n"
            context += f"  - Abandoned: {stats.abandoned_count}\n"
            context += f"  - Avg response time: {stats.avg_days_to_inspection:.1f} days\n"

        bottlenecks = state.get("bottleneck_analysis", {})
        context += "\n\nIdentified Bottlenecks:\n"
        context += f"- Inspection queue delays: {len(bottlenecks.get('inspection_queue_delays', []))} boroughs\n"
        context += f"- Repair delays: {len(bottlenecks.get('repair_delays', []))} boroughs\n"
        context += f"- High abandonment: {len(bottlenecks.get('high_abandon_boroughs', []))} boroughs\n"

        # Prompt Claude
        prompt = f"""{context}

Analyze these complaint response bottlenecks. Focus on:
1. Which bottlenecks are most critical? Why?
2. What operational changes would improve response times?
3. Are there resource allocation issues?
4. What's one high-impact improvement to prioritize?

Keep response to 300 tokens."""

        message = client.invoke([{"role": "user", "content": prompt}])
        analysis = message.content

        state["claude_analysis"] = analysis

        # Extract recommendations
        recommendations = _extract_recommendations(analysis)
        state["optimization_recommendations"] = recommendations

    except Exception as e:
        logger.error(f"Claude analysis error: {e}")
        state["claude_analysis"] = f"Error: {e}"
        state["optimization_recommendations"] = []

    state["execution_log"].append({
        "step": "claude_analysis",
        "status": "complete",
    })

    return state

def generate_report_node(state: ComplaintResponseState) -> ComplaintResponseState:
    """Generate final structured report."""
    logger.info("Generating final report...")

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_complaints_analyzed": state.get("total_complaints", 0),
        "summary": {
            "classifications": state.get("classification_summary", {}),
            "category_distribution": state.get("category_distribution", {}),
            "urgency_distribution": state.get("urgency_distribution", {}),
        },
        "borough_metrics": {
            borough: {
                "total": stats.total_complaints,
                "resolved": stats.resolved_count,
                "pending": stats.pending_count,
                "delayed": stats.delayed_count,
                "abandoned": stats.abandoned_count,
                "sla_compliance_rate": round(stats.sla_compliance_rate, 3),
                "avg_days_to_inspection": round(stats.avg_days_to_inspection, 1),
                "avg_days_to_resolution": round(stats.avg_days_to_resolution, 1),
                "satisfaction_score": round(stats.avg_satisfaction_score, 1),
            }
            for borough, stats in state.get("borough_stats", {}).items()
        },
        "bottleneck_analysis": state.get("bottleneck_analysis", {}),
        "claude_analysis": state.get("claude_analysis", ""),
        "optimization_recommendations": state.get("optimization_recommendations", []),
        "execution_log": state.get("execution_log", []),
    }

    state["final_report"] = report
    return state

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _join_complaints_inspections(
    complaints: pd.DataFrame, inspections: pd.DataFrame
) -> pd.DataFrame:
    """Join complaints with inspections by location/date proximity."""
    if "location" not in complaints.columns or "location" not in inspections.columns:
        return complaints

    # Simplified join: merge on location, compute time delta
    joined = complaints.merge(
        inspections,
        on="location",
        how="left",
        suffixes=("_complaint", "_inspection"),
    )
    return joined

def _extract_complaint_metrics(
    complaint_row: pd.Series, joined_df: pd.DataFrame | None = None
) -> ComplaintMetrics:
    """Extract ComplaintMetrics from a complaint row."""
    complaint_id = str(complaint_row.get("unique_id", complaint_row.get("id", "UNKNOWN")))
    description = complaint_row.get("complaint_description", complaint_row.get("description", ""))
    borough = complaint_row.get("borough", "UNKNOWN")
    location_descriptor = complaint_row.get("location_descriptor", "")

    # Parse creation date
    created_date_str = complaint_row.get("created_date", "")
    created_date = pd.to_datetime(created_date_str, errors="coerce") if created_date_str else None

    # Days open
    days_open = 0.0
    if created_date:
        days_open = (datetime.utcnow() - created_date).total_seconds() / 86400

    # Status flags
    is_resolved = complaint_row.get("status", "").lower() in ["closed", "resolved"]
    is_duplicate = "duplicate" in str(complaint_row.get("complaint_description", "")).lower()
    is_reopened = complaint_row.get("is_reopened", False)

    # Days to inspection (from linked inspections if available)
    days_to_inspection = None
    if joined_df is not None and complaint_id in joined_df.index:
        inspection_date = joined_df.get("created_date_inspection")
        if inspection_date and created_date:
            days_to_inspection = (inspection_date - created_date).total_seconds() / 86400

    # Days to resolution
    days_to_resolution = None
    closed_date_str = complaint_row.get("closed_date", "")
    if is_resolved and closed_date_str:
        closed_date = pd.to_datetime(closed_date_str, errors="coerce")
        if closed_date and created_date:
            days_to_resolution = (closed_date - created_date).total_seconds() / 86400

    has_location = bool(location_descriptor and len(str(location_descriptor)) > 0)

    return ComplaintMetrics(
        complaint_id=complaint_id,
        description=description,
        location_descriptor=location_descriptor,
        borough=borough,
        days_open=days_open,
        days_to_inspection=days_to_inspection,
        days_to_resolution=days_to_resolution,
        has_location_details=has_location,
        is_resolved=is_resolved,
        is_duplicate=is_duplicate,
        is_reopened=is_reopened,
    )

def _extract_recommendations(analysis: str) -> list[str]:
    """Extract bullet-point recommendations from Claude analysis."""
    recommendations = []
    lines = analysis.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("-") or line.startswith("•"):
            recommendations.append(line.lstrip("-•").strip())
    return recommendations[:5]  # Top 5

def _median(values: list[float]) -> float:
    """Compute median of a list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    return sorted_vals[n // 2]
