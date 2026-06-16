"""
LangGraph + Claude + spaCy Triage Workflow

Full integration: Socrata data fetch → spaCy classification → Claude decision → Tools → Report

This module orchestrates the complete NYC DOT violation triage workflow using LangGraph
as the state machine, spaCy for deterministic classification, and Claude for reasoning.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph

from socrata_toolkit.analysis.nlp_analysis import DatasetAnalyzerWithNLP
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.spatial.core import spatial_cluster

logger = logging.getLogger(__name__)


# ============================================================================
# STEP 1: Define Workflow State
# ============================================================================

@dataclass
class TriageContext:
    """Context passed through the triage workflow."""
    dataset_key: str
    fourfour: str
    max_rows: int
    borough_filter: Optional[str] = None
    severity_threshold: float = 70.0


class TriageState(dict):
    """LangGraph state for the triage workflow."""

    def __init__(self):
        super().__init__()
        # Input context
        self["context"] = None  # TriageContext
        self["dataframe"] = None  # pd.DataFrame

        # Classification results (spaCy)
        self["classification_summary"] = {}  # Dict with type breakdown
        self["high_severity_records"] = []  # List of dicts
        self["total_records"] = 0

        # Claude assessments
        self["claude_initial_assessment"] = ""  # Claude's first read
        self["next_action"] = ""  # "spatial_analysis" | "borough_focus" | "monitor" | "end"

        # Tool results (conditional)
        self["spatial_analysis_result"] = None
        self["borough_analysis_result"] = None

        # Final output
        self["final_recommendation"] = ""
        self["report_data"] = {}
        self["execution_log"] = []  # Audit trail


# ============================================================================
# STEP 2: Workflow Nodes (Each node is a step in the graph)
# ============================================================================

def fetch_data(state: TriageState) -> TriageState:
    """
    Node 1: Fetch data from Socrata.
    Deterministic, no LLM involved.
    """
    logger.info(f"[FETCH] Getting data for {state['context'].dataset_key}")

    client = SocrataClient(SocrataConfig())

    # Fetch with optional borough filter
    where_clause = ""
    if state["context"].borough_filter:
        where_clause = f"borough='{state['context'].borough_filter}'"

    df = client.fetch_dataframe(
        "data.cityofnewyork.us",
        state["context"].fourfour,
        max_rows=state["context"].max_rows,
        where=where_clause if where_clause else None,
    )

    state["dataframe"] = df
    state["total_records"] = len(df)

    state["execution_log"].append({
        "step": "fetch_data",
        "timestamp": datetime.now().isoformat(),
        "records_fetched": len(df),
        "status": "success"
    })

    logger.info(f"[FETCH] Retrieved {len(df)} records")
    return state


def classify_records(state: TriageState) -> TriageState:
    """
    Node 2: Classify all records using spaCy (deterministic, no LLM).
    Hardcoded NLP analysis.
    """
    logger.info("[CLASSIFY] Starting spaCy classification")

    analyzer = DatasetAnalyzerWithNLP()
    result = analyzer.analyze_dataset(
        state["dataframe"],
        state["context"].dataset_key
    )

    enriched_df = result["dataframe"]

    # Extract high-severity records
    high_severity = analyzer.get_high_severity_records(
        enriched_df,
        state["context"].dataset_key,
        severity_threshold=state["context"].severity_threshold
    )

    # Build summary for Claude
    summary_dict = result["summary"].to_dict() if result["summary"] is not None else {}

    state["classification_summary"] = {
        "total_records": len(enriched_df),
        "high_severity_count": len(high_severity),
        "by_category": summary_dict,
    }

    # Keep high-severity records for potential downstream use
    state["high_severity_records"] = high_severity.to_dict(orient="records")[:20]

    state["dataframe"] = enriched_df  # Update with classifications

    state["execution_log"].append({
        "step": "classify_records",
        "timestamp": datetime.now().isoformat(),
        "high_severity_count": len(high_severity),
        "summary": state["classification_summary"],
        "status": "success"
    })

    logger.info(f"[CLASSIFY] Found {len(high_severity)} high-severity records")
    return state


def claude_triage_decision(state: TriageState) -> TriageState:
    """
    Node 3: Claude reads hardcoded classification facts and decides next action.
    Claude is only interpreting facts, not parsing text.
    """
    logger.info("[CLAUDE] Making triage decision")

    llm = ChatAnthropic(model="claude-opus-4-8")

    # Build context for Claude
    summary_text = json.dumps(state["classification_summary"], indent=2)
    sample_records = json.dumps(state["high_severity_records"][:3], indent=2)

    prompt = f"""You are a NYC DOT triage analyst. Based on the hardcoded classification analysis below, determine the next action:

CLASSIFICATION RESULTS FOR: {state['context'].dataset_key}
Total Records: {state['classification_summary']['total_records']}
High-Severity Items: {state['classification_summary']['high_severity_count']}
Severity Threshold: {state['context'].severity_threshold}

Category Breakdown:
{summary_text}

Sample High-Severity Records:
{sample_records}

Based on this analysis, which action should we take?

A) SPATIAL_ANALYSIS - Significant geographic concentration detected. Run spatial clustering.
B) BOROUGH_FOCUS - High-severity items warrant borough-specific deep dive.
C) MONITOR - Patterns are within normal range. Continue monitoring without escalation.
D) ESCALATE - Critical issues require immediate field inspection.

Respond with:
1. Your chosen action (A/B/C/D)
2. One sentence reasoning
3. Specific borough or area (if relevant)

Be concise."""

    response = llm.invoke(prompt)
    assessment = response.content

    state["claude_initial_assessment"] = assessment

    # Parse Claude's decision
    if "A)" in assessment or "SPATIAL" in assessment:
        state["next_action"] = "spatial_analysis"
    elif "B)" in assessment or "BOROUGH" in assessment:
        state["next_action"] = "borough_focus"
    elif "D)" in assessment or "ESCALATE" in assessment:
        state["next_action"] = "spatial_analysis"  # Escalations also get spatial analysis
    else:
        state["next_action"] = "monitor"

    state["execution_log"].append({
        "step": "claude_triage_decision",
        "timestamp": datetime.now().isoformat(),
        "decision": state["next_action"],
        "assessment": assessment,
        "status": "success"
    })

    logger.info(f"[CLAUDE] Decision: {state['next_action']}")
    return state


def route_decision(state: TriageState) -> str:
    """
    Conditional router: Direct workflow based on Claude's decision.
    """
    return state["next_action"]


def spatial_analysis_node(state: TriageState) -> TriageState:
    """
    Node 4a: If spatial analysis triggered, run clustering and hotspot detection.
    """
    logger.info("[SPATIAL] Running spatial analysis")

    if not state["high_severity_records"]:
        logger.warning("[SPATIAL] No high-severity records to analyze")
        state["spatial_analysis_result"] = {"clusters": 0, "hotspots": []}
        state["execution_log"].append({
            "step": "spatial_analysis",
            "timestamp": datetime.now().isoformat(),
            "status": "skipped (no records)"
        })
        return state

    # Convert records to GeoDataFrame and cluster
    enriched_df = state["dataframe"]
    high_severity_df = enriched_df[enriched_df.index.isin(
        [r.get("index") for r in state["high_severity_records"] if "index" in r]
    )]

    if "the_geom" not in enriched_df.columns:
        logger.warning("[SPATIAL] No geometry column found")
        state["spatial_analysis_result"] = {"clusters": 0, "message": "No geometry data"}
        return state

    # Cluster spatially (simplified)
    try:
        cluster_result = {
            "total_high_severity": len(high_severity_df),
            "clusters_detected": len(high_severity_df.groupby("borough").size()) if "borough" in high_severity_df.columns else 1,
            "affected_boroughs": list(high_severity_df["borough"].unique()) if "borough" in high_severity_df.columns else [],
        }
        state["spatial_analysis_result"] = cluster_result
    except Exception as e:
        logger.error(f"[SPATIAL] Error: {e}")
        state["spatial_analysis_result"] = {"error": str(e)}

    state["execution_log"].append({
        "step": "spatial_analysis",
        "timestamp": datetime.now().isoformat(),
        "result": state["spatial_analysis_result"],
        "status": "success"
    })

    logger.info(f"[SPATIAL] Found {state['spatial_analysis_result'].get('clusters_detected', 0)} clusters")
    return state


def borough_focus_node(state: TriageState) -> TriageState:
    """
    Node 4b: If borough focus triggered, do targeted analysis.
    """
    logger.info("[BOROUGH] Running borough-focused analysis")

    if not state["dataframe"].empty and "borough" in state["dataframe"].columns:
        borough_stats = (
            state["dataframe"]
            .groupby("borough")
            .size()
            .to_dict()
        )
        state["borough_analysis_result"] = borough_stats
    else:
        state["borough_analysis_result"] = {}

    state["execution_log"].append({
        "step": "borough_focus",
        "timestamp": datetime.now().isoformat(),
        "result": state["borough_analysis_result"],
        "status": "success"
    })

    logger.info(f"[BOROUGH] Analyzed {len(state['borough_analysis_result'])} boroughs")
    return state


def final_recommendation(state: TriageState) -> TriageState:
    """
    Node 5: Claude synthesizes all analysis and generates final recommendation.
    """
    logger.info("[FINAL] Generating final recommendation")

    llm = ChatAnthropic(model="claude-opus-4-8")

    # Compile all analysis results
    analysis_summary = f"""
Classification Summary:
{json.dumps(state['classification_summary'], indent=2)}

Claude's Initial Assessment:
{state['claude_initial_assessment']}

Spatial Analysis Results:
{json.dumps(state['spatial_analysis_result'], indent=2) if state['spatial_analysis_result'] else "None"}

Borough Analysis:
{json.dumps(state['borough_analysis_result'], indent=2) if state['borough_analysis_result'] else "None"}
"""

    prompt = f"""Based on the complete triage analysis below, provide NYC DOT with:

1. Top 3 operational priorities
2. Which borough/area needs immediate attention
3. Estimated impact of addressing high-severity issues
4. Recommended next steps

{analysis_summary}

Be specific and actionable. NYC DOT supervisors will read this."""

    response = llm.invoke(prompt)
    state["final_recommendation"] = response.content

    # Compile report data
    state["report_data"] = {
        "dataset": state["context"].dataset_key,
        "timestamp": datetime.now().isoformat(),
        "total_records_analyzed": state["total_records"],
        "high_severity_count": state["classification_summary"]["high_severity_count"],
        "action_taken": state["next_action"],
        "recommendation": state["final_recommendation"],
        "audit_log": state["execution_log"],
    }

    state["execution_log"].append({
        "step": "final_recommendation",
        "timestamp": datetime.now().isoformat(),
        "status": "complete"
    })

    logger.info("[FINAL] Recommendation generated")
    return state


# ============================================================================
# STEP 3: Build the LangGraph Workflow
# ============================================================================

def build_triage_workflow() -> Any:
    """
    Assemble the LangGraph state machine.

    Workflow:
        Fetch Data
            ↓
        Classify (spaCy)
            ↓
        Claude Decision
            ↓
        ├─ Spatial Analysis (if needed)
        │   ↓
        ├─ Borough Focus (if needed)
        │   ↓
        └─ Monitor (if normal)
            ↓
        Final Recommendation
            ↓
            END
    """
    graph = StateGraph(TriageState)

    # Add nodes
    graph.add_node("fetch_data", fetch_data)
    graph.add_node("classify_records", classify_records)
    graph.add_node("claude_triage_decision", claude_triage_decision)
    graph.add_node("spatial_analysis", spatial_analysis_node)
    graph.add_node("borough_focus", borough_focus_node)
    graph.add_node("final_recommendation", final_recommendation)

    # Add edges
    graph.add_edge("fetch_data", "classify_records")
    graph.add_edge("classify_records", "claude_triage_decision")

    # Conditional routing based on Claude's decision
    graph.add_conditional_edges(
        "claude_triage_decision",
        route_decision,
        {
            "spatial_analysis": "spatial_analysis",
            "borough_focus": "borough_focus",
            "monitor": "final_recommendation",
            "end": END,
        }
    )

    # Both analysis paths lead to final recommendation
    graph.add_edge("spatial_analysis", "final_recommendation")
    graph.add_edge("borough_focus", "final_recommendation")
    graph.add_edge("final_recommendation", END)

    # Set entry point
    graph.set_entry_point("fetch_data")

    return graph.compile()


# ============================================================================
# STEP 4: Public API
# ============================================================================

def run_triage(
    dataset_key: str,
    fourfour: str,
    max_rows: int = 1000,
    borough_filter: Optional[str] = None,
    severity_threshold: float = 70.0,
) -> dict[str, Any]:
    """
    Run the complete triage workflow end-to-end.

    Args:
        dataset_key: Key from dataset registry (e.g., 'violations', 'complaints_311')
        fourfour: Socrata fourfour ID
        max_rows: Maximum records to fetch
        borough_filter: Optional borough filter (e.g., 'MN', 'BK')
        severity_threshold: Minimum severity to flag as high (0-100)

    Returns:
        Dict with final state and recommendations
    """
    logger.info(f"[WORKFLOW] Starting triage for {dataset_key}")

    # Initialize state
    state = TriageState()
    state["context"] = TriageContext(
        dataset_key=dataset_key,
        fourfour=fourfour,
        max_rows=max_rows,
        borough_filter=borough_filter,
        severity_threshold=severity_threshold,
    )
    state["execution_log"] = []

    # Build and run workflow
    workflow = build_triage_workflow()
    final_state = workflow.invoke(state)

    logger.info("[WORKFLOW] Triage complete")

    return {
        "dataset": dataset_key,
        "total_records": final_state["total_records"],
        "high_severity_count": final_state["classification_summary"]["high_severity_count"],
        "action_taken": final_state["next_action"],
        "initial_assessment": final_state["claude_initial_assessment"],
        "final_recommendation": final_state["final_recommendation"],
        "spatial_analysis": final_state["spatial_analysis_result"],
        "borough_analysis": final_state["borough_analysis_result"],
        "audit_log": final_state["execution_log"],
        "report_data": final_state["report_data"],
    }


def workflow_visualization() -> str:
    """Return ASCII visualization of the workflow graph."""
    return """
    ┌─────────────────┐
    │   Fetch Data    │  (Socrata API)
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  Classify       │  (spaCy NLP)
    │  (spaCy)        │
    └────────┬────────┘
             │
    ┌────────▼──────────────────┐
    │  Claude Triage Decision   │  (Cost: ~300 tokens)
    │  (Interpret facts)        │
    └────────┬──────────────────┘
             │
        ┌────┴────┬─────────┐
        │          │         │
    ┌───▼──┐  ┌───▼──┐  ┌──▼──┐
    │Spatial│ │Borough│ │Monitor
    │Analysis│ │Focus  │ │
    └───┬──┘  └───┬──┘  └──┬──┘
        │         │        │
        └────┬────┴────┬───┘
             │
    ┌────────▼──────────────────┐
    │  Final Recommendation     │  (Cost: ~400 tokens)
    │  (Claude synthesis)       │
    └────────┬──────────────────┘
             │
           ┌─▼─┐
           │END│
           └───┘

    Total Claude Tokens: ~700 per workflow
    spaCy Classification: ~100ms (no cost)
    """
