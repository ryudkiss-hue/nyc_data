"""Correspondence & Communication Audit Workflow — LangGraph-based orchestration.

This module implements a multi-step LangGraph workflow that:

1. Fetches correspondences dataset (bheb-sjfi) from live Socrata API
2. Classifies messages by type, tone, clarity, and compliance (spaCy deterministic)
3. Routes non-compliant/low-clarity messages to Claude for detailed analysis (~350 tokens)
4. Generates compliance report with good/bad examples and training recommendations
5. Returns structured JSON output with actionable remediation steps

Graph Structure:
    fetch_data → classify → route_severity → claude_analysis → aggregate

    Route by compliance:
    - Compliant (≥80% score): Skip Claude, go to aggregate
    - Needs review (50-79%): Send to Claude for detailed assessment
    - Non-compliant (<50%): Send to Claude for urgent recommendations
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, TypedDict, Optional
import anthropic

from ..core.client import SocrataClient, SocrataConfig
from .correspondence_classifier import CorrespondenceClassifier

logger = logging.getLogger(__name__)

# Optional: Only import LangGraph if available (graceful degradation)
try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


class CorrespondenceAuditState(TypedDict):
    """Workflow state: passed through each node."""
    domain: str
    fourfour: str
    max_rows: Optional[int]
    raw_data: dict
    classified_data: dict
    high_severity_records: list[dict]
    claude_recommendations: dict
    final_report: dict
    error_log: list[str]


class CorrespondenceAuditWorkflow:
    """Orchestrate correspondence audit via LangGraph.

    Usage:
        workflow = CorrespondenceAuditWorkflow(
            domain="data.cityofnewyork.us",
            fourfour="bheb-sjfi",
            max_rows=None  # All records
        )
        report = workflow.run()
        print(json.dumps(report, indent=2))
    """

    def __init__(
        self,
        domain: str = "data.cityofnewyork.us",
        fourfour: str = "bheb-sjfi",
        max_rows: Optional[int] = None,
    ):
        """Initialize workflow.

        Args:
            domain: Socrata domain (default: data.cityofnewyork.us)
            fourfour: Dataset fourfour ID (default: correspondences)
            max_rows: Maximum rows to fetch (None = all, use with caution)
        """
        self.domain = domain
        self.fourfour = fourfour
        self.max_rows = max_rows
        self.client = SocrataClient(SocrataConfig(
            app_token=os.getenv("SOCRATA_APP_TOKEN"),
            timeout=30,
        ))
        self.classifier = CorrespondenceClassifier()
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        if HAS_LANGGRAPH:
            self._build_graph()

    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        self.graph = StateGraph(CorrespondenceAuditState)

        # Add nodes
        self.graph.add_node("fetch_data", self._node_fetch_data)
        self.graph.add_node("classify", self._node_classify)
        self.graph.add_node("route_severity", self._node_route_severity)
        self.graph.add_node("claude_analysis", self._node_claude_analysis)
        self.graph.add_node("aggregate", self._node_aggregate)

        # Build edges
        self.graph.add_edge(START, "fetch_data")
        self.graph.add_edge("fetch_data", "classify")
        self.graph.add_edge("classify", "route_severity")
        self.graph.add_conditional_edges(
            "route_severity",
            self._decide_claude_routing,
            {
                "compliant": "aggregate",
                "needs_analysis": "claude_analysis",
            },
        )
        self.graph.add_edge("claude_analysis", "aggregate")
        self.graph.add_edge("aggregate", END)

        self.compiled = self.graph.compile()

    def run(self) -> dict[str, Any]:
        """Execute the workflow and return final report.

        Returns:
            {
                "timestamp": "...",
                "dataset": "correspondences (bheb-sjfi)",
                "total_records": int,
                "compliance_summary": {...},
                "by_type": {...},
                "by_tone": {...},
                "good_examples": [...],
                "bad_examples": [...],
                "training_recommendations": [...],
                "critical_alerts": [...]
            }
        """
        if not HAS_LANGGRAPH:
            logger.warning("LangGraph not installed; using fallback non-graph execution")
            return self._run_fallback()

        initial_state: CorrespondenceAuditState = {
            "domain": self.domain,
            "fourfour": self.fourfour,
            "max_rows": self.max_rows,
            "raw_data": {},
            "classified_data": {},
            "high_severity_records": [],
            "claude_recommendations": {},
            "final_report": {},
            "error_log": [],
        }

        final_state = self.compiled.invoke(initial_state)
        return final_state.get("final_report", {})

    def _run_fallback(self) -> dict[str, Any]:
        """Fallback implementation without LangGraph."""
        logger.info("Running correspondence audit without LangGraph")

        state: CorrespondenceAuditState = {
            "domain": self.domain,
            "fourfour": self.fourfour,
            "max_rows": self.max_rows,
            "raw_data": {},
            "classified_data": {},
            "high_severity_records": [],
            "claude_recommendations": {},
            "final_report": {},
            "error_log": [],
        }

        # Sequential execution
        state = self._node_fetch_data(state)
        state = self._node_classify(state)
        state = self._node_route_severity(state)
        if state.get("high_severity_records"):
            state = self._node_claude_analysis(state)
        state = self._node_aggregate(state)

        return state.get("final_report", {})

    def _node_fetch_data(self, state: CorrespondenceAuditState) -> CorrespondenceAuditState:
        """Fetch correspondences dataset from live Socrata API."""
        logger.info(f"Fetching correspondences from {self.domain}/{self.fourfour}")

        try:
            df = self.client.fetch_dataframe(self.domain, self.fourfour, max_rows=self.max_rows)
            state["raw_data"] = {
                "total_rows": len(df),
                "columns": df.columns.tolist(),
                "dataframe": df.to_dict(orient="records")[:100],  # Store first 100 for examples
            }
            logger.info(f"Fetched {len(df)} correspondence records")
        except Exception as exc:
            error_msg = f"Failed to fetch correspondences: {exc}"
            logger.error(error_msg)
            state["error_log"].append(error_msg)
            state["raw_data"] = {"total_rows": 0, "error": str(exc)}

        return state

    def _node_classify(self, state: CorrespondenceAuditState) -> CorrespondenceAuditState:
        """Classify all correspondence records using CorrespondenceClassifier."""
        logger.info("Classifying correspondence records")

        if not state["raw_data"].get("dataframe"):
            logger.warning("No data to classify")
            state["classified_data"] = {}
            return state

        try:
            import pandas as pd

            # Reconstruct dataframe from stored records
            df = pd.DataFrame(state["raw_data"]["dataframe"])

            # Enrich with classifications
            df_enriched = self.classifier.enrich_dataframe(df, text_column="issue")

            # Generate compliance summary
            compliance_summary = self.classifier.compliance_summary(df_enriched)

            state["classified_data"] = {
                "total_classified": len(df_enriched),
                "compliance_summary": compliance_summary,
                "by_type": df_enriched.groupby("correspondence_type").size().to_dict(),
                "by_tone": df_enriched.groupby("tone").size().to_dict(),
                "clarity_stats": {
                    "mean": float(df_enriched["clarity_score"].mean()),
                    "median": float(df_enriched["clarity_score"].median()),
                    "min": float(df_enriched["clarity_score"].min()),
                    "max": float(df_enriched["clarity_score"].max()),
                },
                "compliance_distribution": {
                    "compliant": int((df_enriched["compliance_status"] == "COMPLIANT").sum()),
                    "needs_review": int((df_enriched["compliance_status"] == "NEEDS_REVIEW").sum()),
                    "non_compliant": int((df_enriched["compliance_status"] == "NON_COMPLIANT").sum()),
                },
            }

            logger.info(f"Classification complete: {compliance_summary['compliance_rate']:.1f}% compliant")

        except Exception as exc:
            logger.error(f"Classification failed: {exc}")
            state["error_log"].append(f"Classification error: {exc}")
            state["classified_data"] = {}

        return state

    def _node_route_severity(self, state: CorrespondenceAuditState) -> CorrespondenceAuditState:
        """Route non-compliant records to Claude for detailed analysis."""
        logger.info("Routing by compliance severity")

        try:
            import pandas as pd

            if not state["raw_data"].get("dataframe"):
                return state

            df = pd.DataFrame(state["raw_data"]["dataframe"])
            df_enriched = self.classifier.enrich_dataframe(df, text_column="issue")

            # Flag problematic records: needs_review + non_compliant + low clarity
            problematic = df_enriched[
                (df_enriched["compliance_status"].isin(["NEEDS_REVIEW", "NON_COMPLIANT"]))
                | (df_enriched["clarity_score"] < 50)
            ].copy()

            state["high_severity_records"] = [
                {
                    "index": idx,
                    "date_received": row.get("date_received"),
                    "issue": row.get("issue"),
                    "resolution": row.get("resoultion"),  # Note: typo in dataset
                    "borough": row.get("borough"),
                    "compliance_status": row.get("compliance_status"),
                    "compliance_score": row.get("compliance_score"),
                    "tone": row.get("tone"),
                    "clarity_score": row.get("clarity_score"),
                }
                for idx, row in problematic.iterrows()
            ]

            logger.info(f"Identified {len(state['high_severity_records'])} records for detailed review")

        except Exception as exc:
            logger.error(f"Routing error: {exc}")
            state["error_log"].append(f"Routing error: {exc}")

        return state

    def _decide_claude_routing(self, state: CorrespondenceAuditState) -> str:
        """Determine if Claude analysis is needed."""
        compliance_rate = state["classified_data"].get("compliance_summary", {}).get("compliance_rate", 100)

        if compliance_rate >= 90 and len(state["high_severity_records"]) == 0:
            return "compliant"
        else:
            return "needs_analysis"

    def _node_claude_analysis(self, state: CorrespondenceAuditState) -> CorrespondenceAuditState:
        """Send problematic records to Claude for detailed recommendations."""
        logger.info(f"Sending {len(state['high_severity_records'])} records to Claude for analysis")

        if not state["high_severity_records"]:
            state["claude_recommendations"] = {}
            return state

        # Check if API key is available
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("ANTHROPIC_API_KEY not set; skipping Claude analysis")
            state["claude_recommendations"] = {"error": "API key not configured"}
            return state

        # Sample up to 5 problematic records for Claude analysis
        sample_records = state["high_severity_records"][:5]

        # Build prompt
        prompt = self._build_claude_prompt(sample_records, state["classified_data"])

        try:
            message = self.anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            response_text = message.content[0].text

            # Parse recommendations (simple extraction)
            state["claude_recommendations"] = {
                "model": "claude-haiku-4-5-20251001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis": response_text,
                "sample_records_analyzed": len(sample_records),
            }

            logger.info("Claude analysis complete")

        except Exception as exc:
            logger.error(f"Claude API error: {exc}")
            state["error_log"].append(f"Claude API error: {exc}")
            state["claude_recommendations"] = {"error": str(exc)}

        return state

    def _build_claude_prompt(self, sample_records: list[dict], classified_data: dict) -> str:
        """Build Claude analysis prompt from problematic records."""
        compliance_summary = classified_data.get("compliance_summary", {})

        prompt = f"""You are an NYC Department of Transportation compliance auditor.
Analyze these correspondence samples and provide training recommendations.

COMPLIANCE AUDIT RESULTS:
- Total correspondences: {compliance_summary.get('total_correspondences', 'N/A')}
- Compliant: {compliance_summary.get('compliant', 0)} ({compliance_summary.get('compliance_rate', 0):.1f}%)
- Needs review: {compliance_summary.get('needs_review', 0)}
- Non-compliant: {compliance_summary.get('non_compliant', 0)}

PROBLEMATIC SAMPLES (detailed review needed):
"""

        for i, rec in enumerate(sample_records, 1):
            prompt += f"""
Sample {i}:
- Date: {rec.get('date_received', 'N/A')}
- Borough: {rec.get('borough', 'N/A')}
- Message: "{rec.get('issue', 'N/A')}"
- Compliance: {rec.get('compliance_status')} ({rec.get('compliance_score', 0):.0f}%)
- Tone: {rec.get('tone')} | Clarity: {rec.get('clarity_score', 0):.0f}%
"""

        prompt += """
ANALYSIS QUESTIONS:
1. Are these communications compliant with NYC administrative procedures?
2. What are the most common compliance failures?
3. What training should staff receive?
4. Provide 2-3 specific action items.

Format: Brief, actionable recommendations (under 150 words).
"""

        return prompt

    def _node_aggregate(self, state: CorrespondenceAuditState) -> CorrespondenceAuditState:
        """Aggregate results and generate final compliance report."""
        logger.info("Aggregating audit results")

        try:
            import pandas as pd

            df = pd.DataFrame(state["raw_data"]["dataframe"]) if state["raw_data"].get("dataframe") else pd.DataFrame()
            df_enriched = self.classifier.enrich_dataframe(df, text_column="issue") if len(df) > 0 else df

            # Extract good and bad examples
            good_examples = []
            bad_examples = []

            if len(df_enriched) > 0:
                compliant_records = df_enriched[df_enriched["compliance_status"] == "COMPLIANT"]
                if len(compliant_records) > 0:
                    cols = ["date_received", "issue", "tone"]
                    available_cols = [c for c in cols if c in compliant_records.columns]
                    good_examples = compliant_records.nlargest(2, "clarity_score")[available_cols].to_dict("records")

                problematic = df_enriched[df_enriched["compliance_status"].isin(["NEEDS_REVIEW", "NON_COMPLIANT"])]
                if len(problematic) > 0:
                    cols = ["date_received", "issue", "compliance_status"]
                    available_cols = [c for c in cols if c in problematic.columns]
                    bad_examples = problematic.nsmallest(2, "compliance_score")[available_cols].to_dict("records")

            compliance_summary = state["classified_data"].get("compliance_summary", {})

            state["final_report"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dataset": f"correspondences ({self.fourfour})",
                "domain": self.domain,
                "total_records_analyzed": state["raw_data"].get("total_rows", 0),
                "compliance_summary": compliance_summary,
                "distribution": {
                    "by_type": state["classified_data"].get("by_type", {}),
                    "by_tone": state["classified_data"].get("by_tone", {}),
                },
                "clarity_statistics": state["classified_data"].get("clarity_stats", {}),
                "good_examples": good_examples,
                "bad_examples": bad_examples,
                "claude_recommendations": state["claude_recommendations"],
                "critical_alerts": self._generate_alerts(compliance_summary),
                "errors": state["error_log"],
            }

            logger.info("Report generation complete")

        except Exception as exc:
            logger.error(f"Aggregation error: {exc}")
            state["error_log"].append(f"Aggregation error: {exc}")
            state["final_report"] = {"error": str(exc)}

        return state

    def _generate_alerts(self, compliance_summary: dict) -> list[str]:
        """Generate critical alerts based on compliance summary."""
        alerts = []

        compliance_rate = compliance_summary.get("compliance_rate", 100)
        if compliance_rate < 50:
            alerts.append("CRITICAL: Less than 50% of correspondences are compliant. Immediate training required.")
        elif compliance_rate < 75:
            alerts.append("WARNING: Less than 75% compliance rate. Review communication templates and staff training.")

        non_compliant = compliance_summary.get("non_compliant", 0)
        if non_compliant > 10:
            alerts.append(f"WARNING: {non_compliant} non-compliant records. Identify root causes in communication process.")

        return alerts


