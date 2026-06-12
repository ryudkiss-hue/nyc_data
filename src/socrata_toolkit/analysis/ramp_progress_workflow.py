"""
Ramp Progress Tracking Workflow: LangGraph + Claude + spaCy

Full integration for tracking NYC ramp completion:
  1. Fetch ramp_progress dataset (e7gc-ub6z)
  2. Classify progress descriptions with RampStatusClassifier (spaCy)
  3. Compute borough completion rates with Wilson Score CIs
  4. Claude assessment: "Which boroughs are behind? Why?" (~300 tokens)
  5. Generate structured JSON report with trends and recommendations

Token cost: ~800 tokens for 1000+ ramps
Execution time: ~5-8 seconds
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional, TypedDict

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph

from socrata_toolkit.analysis.confidence_intervals import (
    wilson_score_confidence_interval,
)
from socrata_toolkit.analysis.ramp_status import (
    BlockerType,
    RampStatus,
    RampStatusClassifier,
)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

# ============================================================================
# STATE DEFINITIONS
# ============================================================================

@dataclass
class BoroughRampStats:
    """Statistics for ramps in a single borough."""
    borough: str
    total_ramps: int
    completed_ramps: int
    in_progress_ramps: int
    blocked_ramps: int
    not_started_ramps: int
    completion_rate: float
    ci_lower: float
    ci_upper: float
    reliability: str  # "high" | "medium" | "low"
    common_blockers: list[str]
    avg_work_stage: float

class RampProgressState(TypedDict):
    """LangGraph state for ramp progress workflow."""
    # Input context
    context: dict[str, Any] | None
    fourfour: str
    max_rows: int
    borough_filter: str | None

    # Fetched data
    dataframe: pd.DataFrame | None
    total_records: int

    # Classification results
    classification_summary: dict  # Status breakdown
    borough_stats: dict[str, BoroughRampStats]  # By borough
    high_blocker_ramps: list[dict]  # Ramps with multiple blockers
    blocker_summary: dict  # Blocker type breakdown

    # Claude assessments
    claude_assessment: str  # Initial read on data
    claude_analysis: str  # Deeper why/recommendations
    next_action: str  # "complete" | "escalate_borough" | "investigate_blockers" | "end"

    # Output
    final_report: dict
    execution_log: list[dict]

def create_ramp_workflow():
    """Create and return the ramp progress tracking workflow."""
    workflow = StateGraph(RampProgressState)

    # Add nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("classify_progress", classify_progress_node)
    workflow.add_node("compute_stats", compute_stats_node)
    workflow.add_node("claude_assess", claude_assess_node)
    workflow.add_node("generate_report", generate_report_node)

    # Add edges
    workflow.add_edge("fetch_data", "classify_progress")
    workflow.add_edge("classify_progress", "compute_stats")
    workflow.add_edge("compute_stats", "claude_assess")
    workflow.add_edge("claude_assess", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()

# ============================================================================
# WORKFLOW NODES
# ============================================================================

def fetch_data_node(state: RampProgressState) -> RampProgressState:
    """Fetch ramp_progress dataset from Socrata."""
    logger.info(
        f"[FETCH] Fetching ramp_progress (fourfour={state['fourfour']}, "
        f"max_rows={state['max_rows']})"
    )

    client = SocrataClient(SocrataConfig())

    # Build where clause if borough filter provided
    where_clause = None
    if state.get("borough_filter"):
        where_clause = f"borough='{state['borough_filter']}'"

    # Fetch dataframe
    df = client.fetch_dataframe(
        "data.cityofnewyork.us",
        state["fourfour"],
        max_rows=state["max_rows"],
        where=where_clause,
    )

    state["dataframe"] = df
    state["total_records"] = len(df)

    state["execution_log"].append({
        "step": "fetch_data",
        "timestamp": datetime.now().isoformat(),
        "rows_fetched": len(df),
    })

    logger.info(f"[FETCH] Fetched {len(df)} ramp records")
    return state

def classify_progress_node(state: RampProgressState) -> RampProgressState:
    """Classify ramp progress using RampStatusClassifier."""
    logger.info("[CLASSIFY] Classifying ramp progress descriptions")

    if state["dataframe"] is None or len(state["dataframe"]) == 0:
        logger.warning("[CLASSIFY] No data to classify")
        state["execution_log"].append({
            "step": "classify_progress",
            "error": "No dataframe",
            "timestamp": datetime.now().isoformat(),
        })
        return state

    df = state["dataframe"]
    classifier = RampStatusClassifier()

    # Classify all progress descriptions
    descriptions = df.get("description", df.get("progress_notes", []))
    if descriptions is None:
        descriptions = []

    classifications = []
    for desc in descriptions:
        try:
            result = classifier.classify(str(desc))
            classifications.append(result)
        except Exception as e:
            logger.warning(f"Classification failed: {e}")

    # Create enriched dataframe with classification results
    df_enriched = df.copy()
    df_enriched["ramp_status"] = [
        c.status.value for c in classifications
    ]
    df_enriched["work_stage_percent"] = [
        c.work_stage_percent for c in classifications
    ]
    df_enriched["blocker_types"] = [
        [b.value for b in c.blocker_types] for c in classifications
    ]
    df_enriched["classification_confidence"] = [
        c.confidence_score for c in classifications
    ]

    state["dataframe"] = df_enriched

    # Summary statistics
    summary = RampStatusClassifier.summary_table(classifications)
    state["classification_summary"] = summary

    state["execution_log"].append({
        "step": "classify_progress",
        "timestamp": datetime.now().isoformat(),
        "total_classified": len(classifications),
        "summary": summary,
    })

    logger.info(
        f"[CLASSIFY] Classified {len(classifications)} ramps; "
        f"summary: {summary['status_breakdown']}"
    )
    return state

def compute_stats_node(state: RampProgressState) -> RampProgressState:
    """Compute borough-level statistics with Wilson Score CIs."""
    logger.info("[STATS] Computing borough statistics")

    if state["dataframe"] is None:
        return state

    df = state["dataframe"]
    borough_stats = {}
    blocker_summary = {
        blocker.value: 0 for blocker in BlockerType
    }

    # Group by borough
    borough_col = (
        "borough" if "borough" in df.columns else "location_borough"
    )
    if borough_col not in df.columns:
        logger.warning("[STATS] Borough column not found in dataframe")
        return state

    for borough in df[borough_col].unique():
        if pd.isna(borough):
            continue

        borough_df = df[df[borough_col] == borough]
        total = len(borough_df)

        # Count by status
        completed = (
            (borough_df["ramp_status"] == RampStatus.COMPLETED.value)
            .sum()
        )
        in_progress = (
            (borough_df["ramp_status"] == RampStatus.IN_PROGRESS.value)
            .sum()
        )
        blocked = (
            (borough_df["ramp_status"] == RampStatus.BLOCKED.value)
            .sum()
        )
        not_started = (
            (borough_df["ramp_status"] == RampStatus.NOT_STARTED.value)
            .sum()
        )

        # Wilson Score CI for completion rate
        ci = wilson_score_confidence_interval(
            completed, total, confidence_level=0.95
        )
        completion_rate = ci["point_estimate"]

        # Reliability based on sample size
        if total >= 100:
            reliability = "high"
        elif total >= 30:
            reliability = "medium"
        else:
            reliability = "low"

        # Common blockers in borough
        all_blockers = []
        for blocker_list in borough_df["blocker_types"]:
            all_blockers.extend(blocker_list if isinstance(blocker_list, list) else [])

        blocker_counts = {}
        for blocker in all_blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
            blocker_summary[blocker] += 1

        common_blockers = sorted(
            blocker_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        common_blocker_names = [b[0] for b in common_blockers]

        # Average work stage
        avg_stage = borough_df["work_stage_percent"].mean()

        borough_stats[borough] = BoroughRampStats(
            borough=borough,
            total_ramps=total,
            completed_ramps=completed,
            in_progress_ramps=in_progress,
            blocked_ramps=blocked,
            not_started_ramps=not_started,
            completion_rate=completion_rate,
            ci_lower=ci["lower_bound"],
            ci_upper=ci["upper_bound"],
            reliability=reliability,
            common_blockers=common_blocker_names,
            avg_work_stage=avg_stage,
        )

    state["borough_stats"] = borough_stats
    state["blocker_summary"] = blocker_summary

    # Find ramps with multiple blockers
    df["blocker_count"] = df["blocker_types"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    high_blocker_ramps = df[df["blocker_count"] >= 2].head(10).to_dict(
        orient="records"
    )
    state["high_blocker_ramps"] = high_blocker_ramps

    state["execution_log"].append({
        "step": "compute_stats",
        "timestamp": datetime.now().isoformat(),
        "boroughs_analyzed": len(borough_stats),
        "borough_stats": {
            b: asdict(s) for b, s in borough_stats.items()
        },
    })

    logger.info(f"[STATS] Computed stats for {len(borough_stats)} boroughs")
    return state

def claude_assess_node(state: RampProgressState) -> RampProgressState:
    """Claude: analyze why certain boroughs are behind."""
    logger.info("[CLAUDE] Running Claude assessment")

    if not state["borough_stats"]:
        logger.warning("[CLAUDE] No borough stats to assess")
        return state

    # Build assessment prompt
    stats_text = _format_borough_stats(state["borough_stats"])
    blocker_text = _format_blocker_summary(state["blocker_summary"])
    high_blocker_text = _format_high_blocker_ramps(state["high_blocker_ramps"])

    prompt = f"""
You are analyzing NYC DOT ramp completion progress. Here are the current statistics:

BOROUGH COMPLETION RATES:
{stats_text}

COMMON BLOCKERS:
{blocker_text}

HIGH-RISK RAMPS (Multiple Blockers):
{high_blocker_text}

Based on this data:
1. Which 2-3 boroughs are furthest behind? Why might that be?
2. What are the top 2-3 blockages slowing progress?
3. What's the recommended next action? (e.g., "Expedite permits in MN", "Allocate additional budget to BX")

Be concise (~300 tokens). Cite specific numbers.
"""

    client = ChatAnthropic(model="claude-haiku-4-5-20251001")
    message = client.invoke(prompt)
    assessment = message.content

    state["claude_assessment"] = assessment

    # Determine next action based on assessment
    assessment_lower = assessment.lower()
    if "permit" in assessment_lower:
        state["next_action"] = "escalate_borough"
    elif "budget" in assessment_lower:
        state["next_action"] = "investigate_blockers"
    else:
        state["next_action"] = "complete"

    state["execution_log"].append({
        "step": "claude_assess",
        "timestamp": datetime.now().isoformat(),
        "next_action": state["next_action"],
        "assessment_tokens": len(assessment.split()),
    })

    logger.info(f"[CLAUDE] Assessment complete (next_action={state['next_action']})")
    return state

def generate_report_node(state: RampProgressState) -> RampProgressState:
    """Generate final structured JSON report."""
    logger.info("[REPORT] Generating final report")

    report = {
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "fourfour": state["fourfour"],
            "total_ramps_analyzed": state["total_records"],
            "borough_filter": state.get("borough_filter"),
        },
        "summary": {
            "status_breakdown": state["classification_summary"]
            .get("status_breakdown", {}),
            "completion_rate_overall": state["classification_summary"].get(
                "status_percentages", {}
            ).get("COMPLETED", 0),
            "avg_work_stage": state["classification_summary"].get(
                "avg_work_stage", 0
            ),
        },
        "borough_analysis": {
            b: asdict(s) for b, s in state["borough_stats"].items()
        },
        "blocker_analysis": state["blocker_summary"],
        "high_risk_ramps": state["high_blocker_ramps"],
        "claude_assessment": state["claude_assessment"],
        "recommended_action": state["next_action"],
        "audit_log": state["execution_log"],
    }

    state["final_report"] = report

    state["execution_log"].append({
        "step": "generate_report",
        "timestamp": datetime.now().isoformat(),
        "report_size_bytes": len(json.dumps(report)),
    })

    logger.info("[REPORT] Report generation complete")
    return state

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_borough_stats(borough_stats: dict[str, BoroughRampStats]) -> str:
    """Format borough statistics as readable text."""
    lines = []
    for borough, stats in sorted(
        borough_stats.items(),
        key=lambda x: x[1].completion_rate
    ):
        lines.append(
            f"- {borough}: {stats.completion_rate*100:.1f}% complete "
            f"(95% CI: {stats.ci_lower*100:.1f}%-{stats.ci_upper*100:.1f}%) | "
            f"n={stats.total_ramps} | "
            f"Blocked: {stats.blocked_ramps} | "
            f"Avg stage: {stats.avg_work_stage:.0f}%"
        )
    return "\n".join(lines)

def _format_blocker_summary(blocker_summary: dict[str, int]) -> str:
    """Format blocker summary as readable text."""
    lines = []
    for blocker, count in sorted(
        blocker_summary.items(),
        key=lambda x: x[1],
        reverse=True
    ):
        if count > 0:
            lines.append(f"- {blocker}: {count} ramps affected")
    return "\n".join(lines) if lines else "- No blockers identified"

def _format_high_blocker_ramps(ramps: list[dict]) -> str:
    """Format high-risk ramps as readable text."""
    if not ramps:
        return "- None identified"

    lines = []
    for ramp in ramps[:5]:
        ramp_id = ramp.get("ramp_id", ramp.get("objectid", "???"))
        blockers = ramp.get("blocker_types", [])
        status = ramp.get("ramp_status", "UNKNOWN")
        lines.append(
            f"- Ramp {ramp_id}: {status} | "
            f"Blockers: {', '.join(blockers) if blockers else 'None'}"
        )
    return "\n".join(lines)

def run_ramp_workflow(
    fourfour: str = "e7gc-ub6z",
    max_rows: int = 1000,
    borough_filter: str | None = None,
) -> dict[str, Any]:
    """
    Run the complete ramp progress tracking workflow.

    Args:
        fourfour: Dataset fourfour ID (default: ramp_progress)
        max_rows: Max rows to fetch
        borough_filter: Optional borough code (e.g., "MN", "BX")

    Returns:
        Dict with final_report and execution log
    """
    workflow = create_ramp_workflow()

    initial_state: RampProgressState = {
        "context": {"dataset": "ramp_progress"},
        "fourfour": fourfour,
        "max_rows": max_rows,
        "borough_filter": borough_filter,
        "dataframe": None,
        "total_records": 0,
        "classification_summary": {},
        "borough_stats": {},
        "high_blocker_ramps": [],
        "blocker_summary": {},
        "claude_assessment": "",
        "claude_analysis": "",
        "next_action": "complete",
        "final_report": {},
        "execution_log": [],
    }

    result = workflow.invoke(initial_state)

    return {
        "final_report": result["final_report"],
        "execution_log": result["execution_log"],
        "total_records": result["total_records"],
    }

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    result = run_ramp_workflow(max_rows=500, borough_filter=None)
    print("\n" + "=" * 70)
    print("RAMP PROGRESS TRACKING REPORT")
    print("=" * 70)
    print(json.dumps(result["final_report"], indent=2, default=str))
