"""Public Sentiment Tracking Workflow — LangGraph-based orchestration.

This module implements a multi-step LangGraph workflow that:

1. Fetches complaints_311 + correspondences from live Socrata API.
2. Classifies sentiment, tone, root causes, and repeat patterns (spaCy + TextBlob).
3. Detects repeat complaints by address and issue type.
4. Routes high-impact issues to Claude for strategic recommendations (~350 tokens).
5. Generates sentiment dashboard + recommended messaging.
6. Returns structured JSON with insights and community sentiment summary.

Graph Structure:
    fetch_data → classify_sentiment → detect_repeats → route_severity → claude_analysis → aggregate

    Route by impact:
    - MEDIUM/LOW impact: Skip Claude, go to aggregate
    - HIGH impact + repeat: Send to Claude for messaging strategy
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from ..core.client import SocrataClient, SocrataConfig
from .sentiment_classifier import SentimentClassifier, SentimentResult

logger = logging.getLogger(__name__)

# Optional: Only import LangGraph if available (graceful degradation)
try:
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

# Optional: Import Anthropic for Claude analysis
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

class SentimentState(TypedDict):
    """Workflow state: passed through each node."""
    registry: dict[str, dict[str, str]]
    domain: str
    client: Any  # SocrataClient
    complaints_311: list[dict[str, Any]]
    correspondences: list[dict[str, Any]]
    sentiment_results: list[dict[str, Any]]
    repeat_clusters: list[dict[str, Any]]
    high_impact_issues: list[dict[str, Any]]
    claude_analysis: dict[str, Any]
    final_report: dict[str, Any]
    error_log: list[str]

class PublicSentimentWorkflow:
    """Orchestrate sentiment tracking via LangGraph.

    Usage:
        workflow = PublicSentimentWorkflow(
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
        complaints_key: str = "complaints_311",
        correspondences_key: str = "correspondences",
        sample_size: int = 5000,
    ):
        """Initialize workflow.

        Args:
            registry: Datasets registry {key: {fourfour, ...}}.
            domain: Socrata domain (default: data.cityofnewyork.us).
            complaints_key: Registry key for 311 complaints (default: complaints_311).
            correspondences_key: Registry key for correspondences (default: correspondences).
            sample_size: Max rows to fetch per dataset (default: 5000).
        """
        self.registry = registry
        self.domain = domain
        self.complaints_key = complaints_key
        self.correspondences_key = correspondences_key
        self.sample_size = sample_size
        self.client = SocrataClient(SocrataConfig())
        self.classifier = SentimentClassifier()

    def run(self) -> dict[str, Any]:
        """Execute the sentiment workflow.

        Returns:
            Final report with sentiment dashboard and recommendations.
        """
        if not HAS_LANGGRAPH:
            logger.warning("LangGraph not installed; running linear workflow")
            return self._run_linear()

        graph = self._build_graph()
        runner = graph.compile()

        initial_state: SentimentState = {
            "registry": self.registry,
            "domain": self.domain,
            "client": self.client,
            "complaints_311": [],
            "correspondences": [],
            "sentiment_results": [],
            "repeat_clusters": [],
            "high_impact_issues": [],
            "claude_analysis": {},
            "final_report": {},
            "error_log": [],
        }

        final_state = runner.invoke(initial_state)
        return final_state["final_report"]

    def _run_linear(self) -> dict[str, Any]:
        """Fallback linear execution without LangGraph."""
        state: SentimentState = {
            "registry": self.registry,
            "domain": self.domain,
            "client": self.client,
            "complaints_311": [],
            "correspondences": [],
            "sentiment_results": [],
            "repeat_clusters": [],
            "high_impact_issues": [],
            "claude_analysis": {},
            "final_report": {},
            "error_log": [],
        }

        state = self._fetch_data_node(state)
        state = self._classify_sentiment_node(state)
        state = self._detect_repeats_node(state)
        state = self._route_severity_node(state)

        if state["high_impact_issues"]:
            state = self._claude_analysis_node(state)

        state = self._aggregate_node(state)
        return state["final_report"]

    def _build_graph(self):
        """Build LangGraph workflow."""
        graph = StateGraph(SentimentState)

        # Add nodes
        graph.add_node("fetch_data", self._fetch_data_node)
        graph.add_node("classify_sentiment", self._classify_sentiment_node)
        graph.add_node("detect_repeats", self._detect_repeats_node)
        graph.add_node("route_severity", self._route_severity_node)
        graph.add_node("claude_analysis", self._claude_analysis_node)
        graph.add_node("aggregate", self._aggregate_node)

        # Add edges
        graph.add_edge(START, "fetch_data")
        graph.add_edge("fetch_data", "classify_sentiment")
        graph.add_edge("classify_sentiment", "detect_repeats")
        graph.add_edge("detect_repeats", "route_severity")

        # Conditional edge: route to Claude only if high impact
        def should_analyze_with_claude(state: SentimentState) -> str:
            if state["high_impact_issues"]:
                return "claude_analysis"
            return "aggregate"

        graph.add_conditional_edges(
            "route_severity",
            should_analyze_with_claude,
            {
                "claude_analysis": "claude_analysis",
                "aggregate": "aggregate",
            },
        )

        graph.add_edge("claude_analysis", "aggregate")
        graph.add_edge("aggregate", END)

        return graph

    def _fetch_data_node(self, state: SentimentState) -> SentimentState:
        """Fetch complaints_311 and correspondences from Socrata."""
        logger.info("Fetching complaints and correspondences...")

        try:
            # Fetch 311 complaints
            if self.complaints_key in self.registry:
                fourfour = self.registry[self.complaints_key]["fourfour"]
                complaints_df = self.client.fetch_dataframe(
                    self.domain,
                    fourfour,
                    max_rows=self.sample_size,
                )
                state["complaints_311"] = complaints_df.to_dict("records")
                logger.info(f"Fetched {len(state['complaints_311'])} complaints")

            # Fetch correspondences
            if self.correspondences_key in self.registry:
                fourfour = self.registry[self.correspondences_key]["fourfour"]
                correspondences_df = self.client.fetch_dataframe(
                    self.domain,
                    fourfour,
                    max_rows=self.sample_size,
                )
                state["correspondences"] = correspondences_df.to_dict("records")
                logger.info(f"Fetched {len(state['correspondences'])} correspondences")

        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}"
            logger.error(error_msg)
            state["error_log"].append(error_msg)

        return state

    def _classify_sentiment_node(self, state: SentimentState) -> SentimentState:
        """Classify sentiment for all texts."""
        logger.info("Classifying sentiment...")

        all_items = []

        # Process complaints
        for complaint in state["complaints_311"]:
            text = complaint.get("description", "") or complaint.get("comment", "")
            address = complaint.get("location", "") or complaint.get("street", "")

            result = self.classifier.classify(text, address)
            item = {
                **complaint,
                "sentiment_type": "complaint",
                "tone": result.tone,
                "tone_confidence": result.tone_confidence,
                "root_cause": result.root_cause,
                "root_cause_confidence": result.root_cause_confidence,
                "is_repeat_complaint": result.is_repeat_complaint,
                "repeat_likelihood": result.repeat_likelihood,
                "community_impact": result.community_impact,
                "impact_score": result.impact_score,
                "sentiment_score": result.sentiment_score,
                "extracted_keywords": result.extracted_keywords,
            }
            all_items.append(item)

        # Process correspondences
        for corr in state["correspondences"]:
            text = corr.get("comment", "") or corr.get("description", "")
            address = corr.get("location", "") or corr.get("street", "")

            result = self.classifier.classify(text, address)
            item = {
                **corr,
                "sentiment_type": "correspondence",
                "tone": result.tone,
                "tone_confidence": result.tone_confidence,
                "root_cause": result.root_cause,
                "root_cause_confidence": result.root_cause_confidence,
                "is_repeat_complaint": result.is_repeat_complaint,
                "repeat_likelihood": result.repeat_likelihood,
                "community_impact": result.community_impact,
                "impact_score": result.impact_score,
                "sentiment_score": result.sentiment_score,
                "extracted_keywords": result.extracted_keywords,
            }
            all_items.append(item)

        state["sentiment_results"] = all_items
        logger.info(f"Classified {len(all_items)} texts")

        return state

    def _detect_repeats_node(self, state: SentimentState) -> SentimentState:
        """Detect repeat complaints by address and issue type."""
        logger.info("Detecting repeat complaints...")

        # Group by address + root cause
        repeat_clusters = {}

        for item in state["sentiment_results"]:
            address = item.get("address_context") or item.get("location") or "UNKNOWN"
            root_cause = item.get("root_cause", "OTHER")
            key = (address, root_cause)

            if key not in repeat_clusters:
                repeat_clusters[key] = {
                    "address": address,
                    "root_cause": root_cause,
                    "count": 0,
                    "items": [],
                    "avg_sentiment_score": 0.0,
                    "tones": [],
                    "impact_scores": [],
                }

            repeat_clusters[key]["count"] += 1
            repeat_clusters[key]["items"].append(item)
            repeat_clusters[key]["tones"].append(item.get("tone", "NEUTRAL"))
            repeat_clusters[key]["impact_scores"].append(item.get("impact_score", 0))

        # Aggregate cluster stats
        clusters_list = []
        for (address, root_cause), cluster in repeat_clusters.items():
            avg_impact = sum(cluster["impact_scores"]) / len(cluster["impact_scores"]) if cluster["impact_scores"] else 0
            avg_sentiment = sum(item.get("sentiment_score", 0) for item in cluster["items"]) / len(cluster["items"]) if cluster["items"] else 0

            clusters_list.append({
                "address": address,
                "root_cause": root_cause,
                "repeat_count": cluster["count"],
                "is_repeat": cluster["count"] > 1,
                "avg_impact_score": avg_impact,
                "avg_sentiment_score": avg_sentiment,
                "dominant_tone": max(set(cluster["tones"]), key=cluster["tones"].count) if cluster["tones"] else "NEUTRAL",
                "items": cluster["items"],
            })

        # Sort by repeat count and impact
        clusters_list.sort(key=lambda x: (x["repeat_count"], x["avg_impact_score"]), reverse=True)

        state["repeat_clusters"] = clusters_list
        logger.info(f"Detected {len(clusters_list)} repeat clusters; {sum(1 for c in clusters_list if c['is_repeat'])} are repeats")

        return state

    def _route_severity_node(self, state: SentimentState) -> SentimentState:
        """Route high-impact issues for Claude analysis."""
        logger.info("Routing by severity...")

        high_impact_issues = [
            cluster for cluster in state["repeat_clusters"]
            if cluster["avg_impact_score"] >= 60 or cluster["repeat_count"] >= 3
        ]

        state["high_impact_issues"] = high_impact_issues
        logger.info(f"Found {len(high_impact_issues)} high-impact issues")

        return state

    def _claude_analysis_node(self, state: SentimentState) -> SentimentState:
        """Use Claude to analyze root causes and recommend messaging strategy."""
        logger.info("Running Claude analysis on high-impact issues...")

        if not HAS_ANTHROPIC:
            logger.warning("Anthropic SDK not installed; skipping Claude analysis")
            return state

        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set; skipping Claude analysis")
                return state

            client = anthropic.Anthropic(api_key=api_key)

            # Build prompt
            issues_summary = self._format_issues_for_claude(state["high_impact_issues"])
            prompt = f"""Analyze this public sentiment data from NYC sidewalk inspection complaints:

{issues_summary}

Provide a brief (3-4 sentences) strategic analysis covering:
1. Main drivers of public dissatisfaction
2. Communication gaps or perception issues
3. 1-2 specific messaging strategies to address sentiment

Focus on operational insights, not excuses."""

            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=350,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            analysis_text = message.content[0].text if message.content else ""
            state["claude_analysis"] = {
                "status": "success",
                "analysis": analysis_text,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
            }
            logger.info(f"Claude analysis complete ({message.usage.output_tokens} output tokens)")

        except Exception as e:
            error_msg = f"Claude analysis failed: {str(e)}"
            logger.error(error_msg)
            state["error_log"].append(error_msg)
            state["claude_analysis"] = {"status": "error", "error": error_msg}

        return state

    def _aggregate_node(self, state: SentimentState) -> SentimentState:
        """Aggregate results into final dashboard report."""
        logger.info("Aggregating results...")

        # Compute sentiment dashboard
        all_items = state["sentiment_results"]
        if not all_items:
            state["final_report"] = {
                "status": "empty",
                "message": "No complaints or correspondences fetched",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            return state

        # Tone distribution
        tone_counts = {}
        for item in all_items:
            tone = item.get("tone", "NEUTRAL")
            tone_counts[tone] = tone_counts.get(tone, 0) + 1

        # Root cause distribution
        root_cause_counts = {}
        for item in all_items:
            root_cause = item.get("root_cause", "OTHER")
            root_cause_counts[root_cause] = root_cause_counts.get(root_cause, 0) + 1

        # Impact distribution
        impact_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in all_items:
            impact = item.get("community_impact", "LOW")
            impact_counts[impact] += 1

        # Average sentiment score
        avg_sentiment = sum(item.get("sentiment_score", 0) for item in all_items) / len(all_items) if all_items else 0

        # Repeat statistics
        repeat_count = sum(1 for cluster in state["repeat_clusters"] if cluster["is_repeat"])

        # Build final report
        state["final_report"] = {
            "status": "success",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_summary": {
                "total_items": len(all_items),
                "complaints": len(state["complaints_311"]),
                "correspondences": len(state["correspondences"]),
                "repeat_clusters": len(state["repeat_clusters"]),
                "repeat_issues": repeat_count,
            },
            "sentiment_dashboard": {
                "tone_distribution": tone_counts,
                "root_cause_distribution": root_cause_counts,
                "impact_distribution": impact_counts,
                "avg_sentiment_score": round(avg_sentiment, 2),
                "sentiment_trend": self._classify_sentiment_trend(avg_sentiment),
            },
            "high_impact_clusters": [
                {
                    "address": cluster["address"],
                    "root_cause": cluster["root_cause"],
                    "repeat_count": cluster["repeat_count"],
                    "avg_impact_score": round(cluster["avg_impact_score"], 1),
                    "dominant_tone": cluster["dominant_tone"],
                    "avg_sentiment": round(cluster["avg_sentiment_score"], 2),
                }
                for cluster in state["high_impact_issues"][:10]  # Top 10
            ],
            "strategic_analysis": state.get("claude_analysis", {}),
            "errors": state.get("error_log", []),
        }

        logger.info("Aggregation complete")
        return state

    def _format_issues_for_claude(self, issues: list[dict[str, Any]]) -> str:
        """Format high-impact issues for Claude analysis."""
        lines = []
        for i, issue in enumerate(issues[:5], 1):  # Top 5
            lines.append(
                f"{i}. {issue['root_cause']} at {issue['address']}: "
                f"{issue['repeat_count']} reports, "
                f"avg impact {issue['avg_impact_score']:.0f}/100, "
                f"tone {issue['dominant_tone']}"
            )
        return "\n".join(lines)

    def _classify_sentiment_trend(self, avg_score: float) -> str:
        """Classify overall sentiment trend."""
        if avg_score > 0.2:
            return "POSITIVE"
        elif avg_score > -0.2:
            return "NEUTRAL"
        elif avg_score > -0.6:
            return "NEGATIVE"
        else:
            return "VERY_NEGATIVE"

def build_sentiment_report(
    registry: dict[str, dict[str, str]],
    domain: str = "data.cityofnewyork.us",
    output_file: str | None = None,
) -> dict[str, Any]:
    """Convenience function to build sentiment report.

    Args:
        registry: Datasets registry {key: {fourfour, ...}}.
        domain: Socrata domain.
        output_file: Optional path to save JSON report.

    Returns:
        Final report dictionary.
    """
    workflow = PublicSentimentWorkflow(registry=registry, domain=domain)
    report = workflow.run()

    if output_file:
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {output_file}")

    return report
