"""
SLA Compliance Reporting Workflow - LangGraph Orchestration

End-to-end workflow for monitoring SLA compliance across 26 NYC DOT datasets.
Uses LangGraph state machine to coordinate:
  1. Fetch freshness metrics for all datasets
  2. Classify against SLA tiers (HIGH 14d, MEDIUM 30d, LOW 60d)
  3. Identify root causes and trends
  4. Route to Claude for analysis (~400 tokens)
  5. Generate executive summary with action items

Output: JSON report with status, recommendations, and audit trail.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

from socrata_toolkit.analysis.sla_status import (
    ComplianceStatus,
    SLAComplianceReport,
    SLAMetricSnapshot,
    SLAStatusClassifier,
    SLAStatusRecord,
    SLATier,
)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

# ============================================================================
# WORKFLOW STATE
# ============================================================================

@dataclass
class SLAComplianceState(dict):
    """LangGraph state for SLA compliance workflow."""

    # Input configuration
    include_full_corpus: bool = False
    sample_size: int = 10000
    save_report: bool = True
    report_path: str = "data/sla_compliance_report.json"

    # Fetch results
    all_metadata: dict[str, Any] = field(default_factory=dict)
    fetch_errors: dict[str, str] = field(default_factory=dict)

    # Classification results
    sla_records: list[SLAStatusRecord] = field(default_factory=list)
    classification_summary: dict[str, int] = field(default_factory=dict)

    # Claude analysis
    claude_analysis: str = ""
    action_items: list[str] = field(default_factory=list)

    # Final report
    compliance_report: SLAComplianceReport | None = None
    execution_log: list[dict[str, Any]] = field(default_factory=list)

    def __init__(self):
        """Initialize state."""
        super().__init__()
        self.update({
            "include_full_corpus": False,
            "sample_size": 10000,
            "save_report": True,
            "report_path": "data/sla_compliance_report.json",
            "all_metadata": {},
            "fetch_errors": {},
            "sla_records": [],
            "classification_summary": {},
            "claude_analysis": "",
            "action_items": [],
            "compliance_report": None,
            "execution_log": [],
        })

# ============================================================================
# WORKFLOW NODES
# ============================================================================

def _load_dataset_config() -> dict[str, dict[str, str]]:
    """Load dataset configuration from data/dataset_config.json."""
    import json
    import os

    config_path = "data/dataset_config.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)

    # Fallback: hardcoded 26-dataset registry from CLAUDE.md
    return {
        "inspection": {"fourfour": "dntt-gqwq"},
        "violations": {"fourfour": "6kbp-uz6m"},
        "built": {"fourfour": "ugc8-s3f6"},
        "lot_info": {"fourfour": "i642-2fxq"},
        "reinspection": {"fourfour": "gx72-kirf"},
        "tree_damage": {"fourfour": "j6v2-6uxq"},
        "dismissals": {"fourfour": "p4u2-3jgx"},
        "correspondences": {"fourfour": "bheb-sjfi"},
        "curb_metal_protruding": {"fourfour": "i2y3-sx2e"},
        "ramp_locations": {"fourfour": "ufzp-rrqu"},
        "ramp_complaints": {"fourfour": "jagj-gttd"},
        "ramp_progress": {"fourfour": "e7gc-ub6z"},
        "permits": {"fourfour": "tqtj-sjs8"},
        "street_permits": {"fourfour": "tqtj-sjs8"},  # Alias
        "street_construction_inspections": {"fourfour": "ydkf-mpxb"},
        "street_closures_block": {"fourfour": "i6b5-j7bu"},
        "permit_stipulations": {"fourfour": "gsgx-6efw"},
        "street_resurfacing_schedule": {"fourfour": "xnfm-u3k5"},
        "street_resurfacing_inhouse": {"fourfour": "ffaf-8mrv"},
        "capital_blocks": {"fourfour": "jvk9-k4re"},
        "capital_intersections": {"fourfour": "97nd-ff3i"},
        "weekly_construction": {"fourfour": "r528-jcks"},
        "step_streets": {"fourfour": "u9au-h79y"},
        "sidewalk_planimetric": {"fourfour": "vfx9-tbb6"},
        "pedestrian_demand": {"fourfour": "fwpa-qxaf"},
        "mappluto": {"fourfour": "64uk-42ks"},
        "complaints_311": {"fourfour": "erm2-nwe9"},
    }

def fetch_dataset_metadata(state: SLAComplianceState) -> dict[str, Any]:
    """
    Node 1: Fetch metadata for all 26 datasets to get freshness metrics.

    Retrieves last_modified, row_count for each dataset in registry.
    Handles API errors gracefully and logs them for root cause analysis.
    """
    logger.info("[FETCH] Getting metadata for all datasets")

    client = SocrataClient(SocrataConfig())
    config = _load_dataset_config()

    metadata = {}
    errors = {}

    for dataset_key, dataset_config in config.items():
        fourfour = dataset_config.get("fourfour")
        if not fourfour:
            logger.warning(f"Skipping {dataset_key}: no fourfour ID")
            continue

        try:
            logger.debug(f"Fetching metadata for {dataset_key} ({fourfour})")
            meta = client.get_metadata("data.cityofnewyork.us", fourfour)

            # Extract relevant fields
            metadata[dataset_key] = {
                "fourfour": fourfour,
                "name": meta.get("name", ""),
                "last_modified": meta.get("last_modified", None),
                "row_count": meta.get("row_count", 0),
                "description": meta.get("description", ""),
                "category": meta.get("category", ""),
            }
            logger.debug(f"  ✓ {dataset_key}: {metadata[dataset_key]['row_count']} rows, "
                        f"updated {metadata[dataset_key]['last_modified']}")

        except Exception as e:
            error_msg = str(e)
            errors[dataset_key] = error_msg
            logger.warning(f"  ✗ {dataset_key}: {error_msg}")

    state["all_metadata"] = metadata
    state["fetch_errors"] = errors

    state["execution_log"].append({
        "step": "fetch_dataset_metadata",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "datasets_fetched": len(metadata),
        "fetch_errors": len(errors),
    })

    logger.info(f"[FETCH] Completed: {len(metadata)} datasets fetched, {len(errors)} errors")
    return state

def classify_sla_status(state: SLAComplianceState) -> dict[str, Any]:
    """
    Node 2: Classify each dataset against SLA tier.

    For each dataset:
      1. Determine SLA tier from CLAUDE.md registry (HIGH/MEDIUM/LOW)
      2. Calculate days_since_update
      3. Run SLAStatusClassifier to get status, root cause, trend
      4. Store in sla_records

    Metrics:
      - COMPLIANT: within SLA threshold
      - AT_RISK: within 80% of threshold
      - BREACHED: exceeds threshold
    """
    logger.info("[CLASSIFY] Classifying datasets against SLA tiers")

    classifier = SLAStatusClassifier(at_risk_threshold_pct=0.80)

    # Map dataset_key → SLA tier from config
    sla_tier_map = {
        # Core inspection & violations (HIGH tier)
        "inspection": SLATier.HIGH,
        "violations": SLATier.HIGH,
        "dismissals": SLATier.HIGH,
        "ramp_complaints": SLATier.HIGH,
        # Core ramps (HIGH tier)
        "ramp_progress": SLATier.HIGH,
        # Permits & construction (MEDIUM tier)
        "permits": SLATier.MEDIUM,
        "street_permits": SLATier.MEDIUM,
        "street_construction_inspections": SLATier.MEDIUM,
        "street_resurfacing_schedule": SLATier.MEDIUM,
        "street_resurfacing_inhouse": SLATier.MEDIUM,
        "capital_intersections": SLATier.MEDIUM,
        # Supporting data (LOW tier)
        "built": SLATier.LOW,
        "lot_info": SLATier.LOW,
        "reinspection": SLATier.LOW,
        "tree_damage": SLATier.LOW,
        "correspondences": SLATier.LOW,
        "curb_metal_protruding": SLATier.LOW,
        "ramp_locations": SLATier.LOW,
        "weekly_construction": SLATier.LOW,
        "capital_blocks": SLATier.LOW,
        "permit_stipulations": SLATier.LOW,
        "street_closures_block": SLATier.LOW,
        "step_streets": SLATier.LOW,
        "sidewalk_planimetric": SLATier.LOW,
        "pedestrian_demand": SLATier.LOW,
        "mappluto": SLATier.LOW,
        "complaints_311": SLATier.LOW,
    }

    records = []
    summary = {
        ComplianceStatus.COMPLIANT.value: 0,
        ComplianceStatus.AT_RISK.value: 0,
        ComplianceStatus.BREACHED.value: 0,
    }

    now = datetime.now(timezone.utc)

    for dataset_key, metadata in state["all_metadata"].items():
        sla_tier = sla_tier_map.get(dataset_key, SLATier.LOW)

        # Parse last_modified timestamp
        last_modified = None
        days_since_update = float("inf")

        if metadata["last_modified"]:
            try:
                if isinstance(metadata["last_modified"], str):
                    last_modified = datetime.fromisoformat(
                        metadata["last_modified"].replace("Z", "+00:00")
                    )
                else:
                    last_modified = metadata["last_modified"]

                if last_modified.tzinfo is None:
                    last_modified = last_modified.replace(tzinfo=timezone.utc)

                days_since_update = (now - last_modified).total_seconds() / 86400.0
            except Exception as e:
                logger.warning(f"Failed to parse last_modified for {dataset_key}: {e}")

        # Check for errors in fetch phase
        error_context = None
        if dataset_key in state["fetch_errors"]:
            error_context = {
                "api_error": True,
                "error_message": state["fetch_errors"][dataset_key],
            }

        # Create snapshot and classify
        snapshot = SLAMetricSnapshot(
            timestamp=now,
            dataset_key=dataset_key,
            fourfour=metadata["fourfour"],
            last_modified=last_modified or now,
            row_count=metadata["row_count"],
            sla_tier=sla_tier,
            days_since_update=days_since_update,
        )

        record = classifier.classify(snapshot, error_context=error_context)
        records.append(record)

        summary[record.compliance_status.value] += 1
        logger.debug(f"  {dataset_key}: {record.compliance_status.value} "
                    f"({record.days_since_update:.1f}d / {record.sla_threshold_days}d)")

    state["sla_records"] = records
    state["classification_summary"] = summary

    state["execution_log"].append({
        "step": "classify_sla_status",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "records_classified": len(records),
        "summary": summary,
    })

    logger.info(f"[CLASSIFY] Completed: {summary}")
    return state

def analyze_with_claude(state: SLAComplianceState) -> dict[str, Any]:
    """
    Node 3: Call Claude to analyze breaches and trends.

    Claude receives:
      - Count of compliant, at-risk, breached datasets
      - List of critical breaches (HIGH tier + breached)
      - Root cause distribution
      - Trend summary

    Claude outputs (~400 tokens):
      - Root cause analysis ("Why are we seeing these breaches?")
      - Trend insights
      - Operational recommendations
    """
    logger.info("[CLAUDE] Analyzing SLA compliance with Claude")

    if not state["sla_records"]:
        logger.warning("No records to analyze")
        state["claude_analysis"] = "No datasets to analyze."
        return state

    # Prepare summary for Claude
    critical_breaches = [
        r.dataset_key
        for r in state["sla_records"]
        if r.sla_tier == SLATier.HIGH and r.compliance_status == ComplianceStatus.BREACHED
    ]

    at_risk = [
        r.dataset_key
        for r in state["sla_records"]
        if r.compliance_status == ComplianceStatus.AT_RISK
    ]

    # Root cause distribution
    root_causes = {}
    for r in state["sla_records"]:
        if r.compliance_status != ComplianceStatus.COMPLIANT:
            cause = r.root_cause.value
            root_causes[cause] = root_causes.get(cause, 0) + 1

    # Trend distribution
    trends = {}
    for r in state["sla_records"]:
        trend = r.trend.value
        trends[trend] = trends.get(trend, 0) + 1

    # Build prompt for Claude
    summary_text = f"""
# SLA Compliance Analysis Required

## Current State
- Total datasets: {len(state['sla_records'])}
- Compliant: {state['classification_summary'].get('compliant', 0)}
- At-risk: {state['classification_summary'].get('at_risk', 0)}
- Breached: {state['classification_summary'].get('breached', 0)}

## Critical Breaches (HIGH tier)
{', '.join(critical_breaches) if critical_breaches else 'None'}

## At-Risk Datasets
{', '.join(at_risk[:10]) if at_risk else 'None'}
{f'... and {len(at_risk) - 10} more' if len(at_risk) > 10 else ''}

## Root Cause Distribution
{json.dumps(root_causes, indent=2)}

## Trend Distribution
{json.dumps(trends, indent=2)}

## Questions for Analysis
1. What patterns do you see in these breaches?
2. Are there systemic issues (e.g., API outage) vs dataset-specific problems?
3. Which breaches are most urgent to address?
4. What preventive measures would help?

Please provide a concise analysis (2-3 paragraphs) focused on operational insights.
"""

    try:
        if not HAS_LANGCHAIN:
            logger.warning("[CLAUDE] langchain_anthropic not installed, skipping Claude analysis")
            state["claude_analysis"] = "Claude analysis skipped (langchain_anthropic not installed)"
        else:
            client = ChatAnthropic(model="claude-haiku-4-5-20251001")

            response = client.invoke([
                SystemMessage(content="You are an NYC DOT data operations expert analyzing dataset freshness issues."),
                HumanMessage(content=summary_text),
            ])

            state["claude_analysis"] = response.content

            logger.info("[CLAUDE] Analysis complete")

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        state["claude_analysis"] = f"Error calling Claude: {str(e)}"

    state["execution_log"].append({
        "step": "analyze_with_claude",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_length": len(state["claude_analysis"]),
    })

    return state

def generate_report(state: SLAComplianceState) -> dict[str, Any]:
    """
    Node 4: Compile final report and action items.

    Uses SLAStatusClassifier.compile_report() to create aggregate report.
    Derives action items from Claude analysis and breach classifications.
    """
    logger.info("[REPORT] Generating SLA compliance report")

    classifier = SLAStatusClassifier()

    # Compile report
    report = classifier.compile_report(
        records=state["sla_records"],
        claude_analysis=state["claude_analysis"],
    )

    # Derive action items from breaches and analysis
    action_items = []

    # Critical breaches → immediate action
    if report.critical_breaches:
        action_items.append(
            f"URGENT: Investigate critical breaches in {', '.join(report.critical_breaches)} "
            f"(HIGH tier datasets)"
        )

    # At-risk datasets → preventive action
    if report.at_risk_count > 0:
        action_items.append(
            f"Monitor {report.at_risk_count} at-risk datasets for imminent breaches. "
            f"Consider increasing refresh frequency."
        )

    # Root cause-specific actions
    api_down_count = sum(1 for r in state["sla_records"] if r.root_cause.value == "api_down")
    if api_down_count > 0:
        action_items.append(
            f"Verify Socrata API health. {api_down_count} datasets showing API-related issues."
        )

    data_quality_count = sum(1 for r in state["sla_records"] if r.root_cause.value == "data_quality")
    if data_quality_count > 0:
        action_items.append(
            f"Contact publishers: {data_quality_count} datasets have potential quality issues."
        )

    # Trend-based actions
    degrading_count = sum(1 for r in state["sla_records"] if r.trend.value == "degrading")
    if degrading_count > 0:
        action_items.append(
            f"Trend alert: {degrading_count} datasets are degrading. "
            f"Escalate to data governance team."
        )

    improving_count = sum(1 for r in state["sla_records"] if r.trend.value == "improving")
    if improving_count > 0:
        action_items.append(
            f"Positive trend: {improving_count} datasets improving. Continue current refresh strategy."
        )

    state["action_items"] = action_items
    state["compliance_report"] = report

    state["execution_log"].append({
        "step": "generate_report",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_items_count": len(action_items),
    })

    logger.info(f"[REPORT] Generated with {len(action_items)} action items")
    return state

def save_report(state: SLAComplianceState) -> dict[str, Any]:
    """
    Node 5: Optionally save report to disk.

    Saves JSON report to state["report_path"] if state["save_report"] is True.
    """
    if not state["save_report"]:
        logger.info("[SAVE] Skipping save (save_report=False)")
        return state

    logger.info(f"[SAVE] Writing report to {state['report_path']}")

    try:
        report = state["compliance_report"]

        # Build output dict
        output = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "execution_log": state["execution_log"],
            },
            "compliance": report.to_dict(),
            "action_items": state["action_items"],
        }

        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(state["report_path"]), exist_ok=True)

        # Write JSON
        with open(state["report_path"], "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"[SAVE] Report saved to {state['report_path']}")

    except Exception as e:
        logger.error(f"Failed to save report: {e}")

    state["execution_log"].append({
        "step": "save_report",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_path": state["report_path"],
    })

    return state

# ============================================================================
# GRAPH ASSEMBLY
# ============================================================================

def build_sla_compliance_graph() -> StateGraph:
    """Build the LangGraph state machine for SLA compliance reporting.

    Returns:
        StateGraph configured with nodes and edges
    """
    graph = StateGraph(dict)

    # Add nodes (order matters for readability, not execution)
    graph.add_node("fetch_metadata", fetch_dataset_metadata)
    graph.add_node("classify_sla", classify_sla_status)
    graph.add_node("analyze_claude", analyze_with_claude)
    graph.add_node("generate_report", generate_report)
    graph.add_node("save_report", save_report)

    # Add edges (sequential execution)
    graph.add_edge("fetch_metadata", "classify_sla")
    graph.add_edge("classify_sla", "analyze_claude")
    graph.add_edge("analyze_claude", "generate_report")
    graph.add_edge("generate_report", "save_report")
    graph.add_edge("save_report", END)

    # Set entry point
    graph.set_entry_point("fetch_metadata")

    return graph

def run_sla_compliance_workflow(
    include_full_corpus: bool = False,
    sample_size: int = 10000,
    save_report: bool = True,
    report_path: str = "data/sla_compliance_report.json",
) -> SLAComplianceReport:
    """Execute the SLA compliance workflow end-to-end.

    Args:
        include_full_corpus: If True, fetch all rows for sample datasets
        sample_size: Row limit for sample fetches
        save_report: If True, save JSON report to disk
        report_path: Where to save the report

    Returns:
        SLAComplianceReport with all findings

    Example:
        report = run_sla_compliance_workflow(save_report=True)
        print(f"Compliance: {report.overall_compliance_pct}%")
        for item in report.recommendations:
            print(f"  - {item}")
    """
    logger.info("=" * 70)
    logger.info("SLA COMPLIANCE WORKFLOW - START")
    logger.info("=" * 70)

    # Initialize state
    state = SLAComplianceState()
    state["include_full_corpus"] = include_full_corpus
    state["sample_size"] = sample_size
    state["save_report"] = save_report
    state["report_path"] = report_path

    # Build and run graph
    graph = build_sla_compliance_graph()
    compiled = graph.compile()

    # Execute
    final_state = compiled.invoke(state)

    logger.info("=" * 70)
    logger.info("SLA COMPLIANCE WORKFLOW - COMPLETE")
    logger.info("=" * 70)

    return final_state["compliance_report"]

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run workflow
    report = run_sla_compliance_workflow(save_report=True)

    # Print summary
    print("\n" + "=" * 70)
    print("SLA COMPLIANCE SUMMARY")
    print("=" * 70)
    print(f"Total datasets: {report.total_datasets}")
    print(f"Compliant: {report.compliant_count}")
    print(f"At-risk: {report.at_risk_count}")
    print(f"Breached: {report.breached_count}")
    print(f"Overall compliance: {report.overall_compliance_pct:.1f}%")

    if report.critical_breaches:
        print(f"\nCritical breaches: {', '.join(report.critical_breaches)}")

    if report.recommendations:
        print("\nRecommendations:")
        for item in report.recommendations:
            print(f"  - {item}")

    print("\nAnalysis:")
    print(report.claude_analysis[:500] + "..." if len(report.claude_analysis) > 500 else report.claude_analysis)
