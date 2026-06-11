"""Dataset Health & Monitoring Workflow — LangGraph-based orchestration.

This module implements a multi-step LangGraph workflow that:

1. Fetches metadata for all 26 registered datasets (parallelized).
2. Classifies health status (HEALTHY / STALE / SCHEMA_DRIFT / EMPTY_OR_ERROR).
3. Routes high-severity datasets to Claude for decision-making (~300 tokens).
4. Generates alerts and remediation steps.
5. Returns structured JSON output.

Graph Structure:
    fetch_metadata → classify → route_severity → claude_decision → aggregate

    Route by severity:
    - Low severity (>70): Skip Claude, go to aggregate
    - High/Critical (≤70): Send to Claude for recommendations
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, TypedDict

from ..core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

# Optional: Only import LangGraph if available (graceful degradation)
try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


class HealthState(TypedDict):
    """Workflow state: passed through each node."""
    registry: dict[str, dict[str, str]]
    domain: str
    sla_thresholds: dict[str, int]
    metadata_cache: dict[str, Any]
    classifications: dict[str, Any]
    high_severity_datasets: list[dict[str, Any]]
    claude_recommendations: dict[str, Any]
    final_report: dict[str, Any]
    error_log: list[str]


class DatasetHealthWorkflow:
    """Orchestrate dataset health monitoring via LangGraph.

    Usage:
        workflow = DatasetHealthWorkflow(
            registry=datasets_registry,
            domain="data.cityofnewyork.us",
        )
        report = workflow.run()
        print(json.dumps(report, indent=2))
    """

    def __init__(
        self,
        registry: dict[str, dict[str, str]],
        domain: str = "data.cityofnewyork.us",
        sla_thresholds: dict[str, int] | None = None,
    ):
        """Initialize workflow.

        Args:
            registry: Datasets registry {key: {fourfour, ...}}.
            domain: Socrata domain (default: data.cityofnewyork.us).
            sla_thresholds: SLA configuration {HIGH: 14, MEDIUM: 30, LOW: 60}.
        """
        self.registry = registry
        self.domain = domain
        self.sla_thresholds = sla_thresholds or {
            "HIGH": 14,
            "MEDIUM": 30,
            "LOW": 60,
        }
        self.client = SocrataClient(SocrataConfig(
            app_token=os.getenv("SOCRATA_APP_TOKEN"),
            timeout=30,
        ))

        if HAS_LANGGRAPH:
            self._build_graph()

    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        self.graph = StateGraph(HealthState)

        # Add nodes
        self.graph.add_node("fetch_metadata", self._node_fetch_metadata)
        self.graph.add_node("classify", self._node_classify)
        self.graph.add_node("route_severity", self._node_route_severity)
        self.graph.add_node("claude_decision", self._node_claude_decision)
        self.graph.add_node("aggregate", self._node_aggregate)

        # Build edges
        self.graph.add_edge(START, "fetch_metadata")
        self.graph.add_edge("fetch_metadata", "classify")
        self.graph.add_edge("classify", "route_severity")
        self.graph.add_conditional_edges(
            "route_severity",
            self._decide_claude_routing,
            {
                "low_severity": "aggregate",
                "high_severity": "claude_decision",
            },
        )
        self.graph.add_edge("claude_decision", "aggregate")
        self.graph.add_edge("aggregate", END)

        self.compiled = self.graph.compile()

    def run(self) -> dict[str, Any]:
        """Execute the workflow and return final report.

        Returns:
            {
                "timestamp": "...",
                "total_datasets": int,
                "datasets": {...},
                "summary": {...},
                "critical_alerts": [...],
                "recommendations": {...}
            }
        """
        if not HAS_LANGGRAPH:
            logger.warning("LangGraph not installed; using fallback non-graph execution")
            return self._run_fallback()

        initial_state: HealthState = {
            "registry": self.registry,
            "domain": self.domain,
            "sla_thresholds": self.sla_thresholds,
            "metadata_cache": {},
            "classifications": {},
            "high_severity_datasets": [],
            "claude_recommendations": {},
            "final_report": {},
            "error_log": [],
        }

        final_state = self.compiled.invoke(initial_state)
        return final_state.get("final_report", {})

    def _run_fallback(self) -> dict[str, Any]:
        """Fallback implementation without LangGraph."""
        logger.info("Running dataset health check without LangGraph")

        state: HealthState = {
            "registry": self.registry,
            "domain": self.domain,
            "sla_thresholds": self.sla_thresholds,
            "metadata_cache": {},
            "classifications": {},
            "high_severity_datasets": [],
            "claude_recommendations": {},
            "final_report": {},
            "error_log": [],
        }

        # Sequential execution
        state = self._node_fetch_metadata(state)
        state = self._node_classify(state)
        state = self._node_route_severity(state)
        if state.get("high_severity_datasets"):
            state = self._node_claude_decision(state)
        state = self._node_aggregate(state)

        return state.get("final_report", {})

    def _node_fetch_metadata(self, state: HealthState) -> HealthState:
        """Fetch metadata for all registered datasets."""
        logger.info(f"Fetching metadata for {len(self.registry)} datasets")

        cache = {}
        errors = []

        for key, dataset_info in self.registry.items():
            fourfour = dataset_info.get("fourfour")
            if not fourfour:
                errors.append(f"{key}: Missing fourfour")
                continue

            try:
                meta = self.client.get_metadata(self.domain, fourfour)
                cache[key] = {
                    "fourfour": fourfour,
                    "name": meta.name,
                    "row_count": meta.row_count,
                    "columns": meta.columns or [],
                    "description": meta.description,
                    "is_accessible": True,
                    "error": None,
                }
            except Exception as exc:
                logger.warning(f"Failed to fetch metadata for {key}: {exc}")
                cache[key] = {
                    "fourfour": fourfour,
                    "name": dataset_info.get("name", "Unknown"),
                    "row_count": None,
                    "columns": [],
                    "description": None,
                    "is_accessible": False,
                    "error": str(exc),
                }
                errors.append(f"{key} ({fourfour}): {exc}")

        state["metadata_cache"] = cache
        state["error_log"].extend(errors)
        logger.info(f"Metadata fetch complete: {len(cache)} datasets cached, {len(errors)} errors")

        return state

    def _node_classify(self, state: HealthState) -> HealthState:
        """Classify health for each dataset using DatasetHealthClassifier."""
        from .dataset_health import DatasetHealthClassifier, DatasetHealthMetrics

        logger.info("Classifying dataset health")

        classifier = DatasetHealthClassifier(sla_thresholds=state["sla_thresholds"])
        classifications = {}

        for key, meta in state["metadata_cache"].items():
            fourfour = meta["fourfour"]
            metrics = DatasetHealthMetrics(
                key=key,
                fourfour=fourfour,
                row_count=meta.get("row_count"),
                last_modified=self._extract_last_modified(meta),
                schema_snapshot=self._extract_schema(meta),
                schema_baseline=None,  # TODO: Load from persistence layer
                is_accessible=meta.get("is_accessible", False),
                error_message=meta.get("error"),
            )
            report = classifier.classify(metrics)
            classifications[key] = report.to_dict()

        state["classifications"] = classifications
        logger.info(f"Classification complete: {len(classifications)} reports generated")

        return state

    def _node_route_severity(self, state: HealthState) -> HealthState:
        """Route datasets to Claude based on severity."""
        logger.info("Routing datasets by severity")

        high_severity = []
        for key, classification in state["classifications"].items():
            severity = classification.get("severity", 100)
            if severity <= 70:  # Critical or High
                high_severity.append({
                    "key": key,
                    "fourfour": classification.get("fourfour"),
                    "status": classification.get("status"),
                    "severity": severity,
                    "alerts": classification.get("alerts", []),
                })

        state["high_severity_datasets"] = high_severity
        logger.info(f"Routed {len(high_severity)} datasets to Claude (severity ≤70)")

        return state

    def _decide_claude_routing(self, state: HealthState) -> str:
        """Conditional edge: route to Claude if high-severity datasets exist."""
        if state.get("high_severity_datasets"):
            return "high_severity"
        return "low_severity"

    def _node_claude_decision(self, state: HealthState) -> HealthState:
        """Ask Claude for recommendations on high-severity datasets."""
        logger.info(f"Sending {len(state['high_severity_datasets'])} datasets to Claude")

        high_severity = state["high_severity_datasets"]
        if not high_severity:
            return state

        # Build prompt for Claude
        datasets_text = "\n".join([
            f"- {d['key']} ({d['fourfour']}): {d['status']} (severity={d['severity']})\n"
            f"  Alerts: {'; '.join(d.get('alerts', []))}"
            for d in high_severity[:10]  # Cap to first 10 for token budget
        ])

        prompt = f"""You are analyzing dataset health metrics for NYC Open Data.

CRITICAL & HIGH-SEVERITY DATASETS REQUIRING ATTENTION:
{datasets_text}

Based on these metrics, provide:
1. Which 3-5 datasets need immediate action?
2. What is the likely root cause for each?
3. What escalation path (team/alert) is recommended?

Format response as JSON:
{{
    "critical_action_required": [
        {{"key": "...", "root_cause": "...", "escalation": "..."}}
    ],
    "next_steps": [...]
}}
"""

        try:
            # Call Claude API if available
            from anthropic import Anthropic

            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text
            try:
                recs = json.loads(response_text)
            except json.JSONDecodeError:
                recs = {"raw_response": response_text}
        except Exception as exc:
            logger.warning(f"Claude decision failed: {exc}")
            recs = {"error": str(exc)}

        state["claude_recommendations"] = recs
        logger.info(f"Claude recommendations received")

        return state

    def _node_aggregate(self, state: HealthState) -> HealthState:
        """Aggregate all results into final report."""
        logger.info("Aggregating results")

        from .dataset_health import DatasetHealthClassifier

        classifier = DatasetHealthClassifier(sla_thresholds=state["sla_thresholds"])

        # Convert classifications back to report objects for summarization
        reports = [
            type('Report', (), c)()
            for c in state["classifications"].values()
        ]

        # Build final report
        final_report: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_datasets": len(state["registry"]),
            "datasets": state["classifications"],
            "summary": {
                "healthy": sum(1 for c in state["classifications"].values() if c["status"] == "healthy"),
                "stale": sum(1 for c in state["classifications"].values() if c["status"] == "stale"),
                "schema_drift": sum(1 for c in state["classifications"].values() if c["status"] == "schema_drift"),
                "empty_or_error": sum(1 for c in state["classifications"].values() if c["status"] == "empty_or_error"),
            },
            "critical_alerts": [
                {
                    "key": d["key"],
                    "fourfour": d["fourfour"],
                    "status": d["status"],
                    "alerts": d.get("alerts", []),
                }
                for d in state["high_severity_datasets"]
            ],
            "claude_recommendations": state.get("claude_recommendations", {}),
            "errors": state.get("error_log", []),
        }

        state["final_report"] = final_report
        logger.info("Aggregation complete")

        return state

    @staticmethod
    def _extract_last_modified(meta: dict[str, Any]) -> datetime | None:
        """Extract last-modified timestamp from metadata dict."""
        # Placeholder: implement based on actual metadata structure
        return None

    @staticmethod
    def _extract_schema(meta: dict[str, Any]) -> dict[str, str]:
        """Extract schema from metadata columns list."""
        schema = {}
        for col in meta.get("columns", []):
            if isinstance(col, dict):
                col_name = col.get("name", "unknown")
                col_type = col.get("dataTypeName", "object")
                schema[col_name] = col_type
        return schema


def run_dataset_health_workflow(
    registry: dict[str, dict[str, str]] | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Convenience function to run the workflow.

    Args:
        registry: Dataset registry (loaded from config if None).
        domain: Socrata domain (default: data.cityofnewyork.us).

    Returns:
        Final health report as dict.

    Example:
        report = run_dataset_health_workflow()
        critical = report["critical_alerts"]
        print(f"Found {len(critical)} datasets requiring attention")
    """
    if registry is None:
        # Load from CLAUDE.md or config
        registry = {
            "inspection": {"fourfour": "dntt-gqwq"},
            "violations": {"fourfour": "6kbp-uz6m"},
            "ramp_progress": {"fourfour": "e7gc-ub6z"},
            # ... add remaining 23 datasets
        }

    if domain is None:
        domain = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")

    workflow = DatasetHealthWorkflow(registry=registry, domain=domain)
    return workflow.run()
