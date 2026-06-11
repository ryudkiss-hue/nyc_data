"""Narrative Engine: Auto-generate insights from metrics (dual-mode: AI-enhanced + hardcoded fallback).

Modes:
- DEFAULT: Hardcoded insight templates (no API calls, fast, free)
- ENHANCED: LangChain + Claude API for rich narratives (requires ANTHROPIC_API_KEY)

Pattern:
  engine = NarrativeEngine(semantic_enabled=True)  # Tries AI, falls back to hardcoded
  insight = engine.generate_narrative(
    metric_id="completion_rate",
    value=82.5,
    ci_lower=79.2,
    ci_upper=85.1,
    context={"borough": "Brooklyn", "material": "concrete"}
  )
  # Output: "Brooklyn concrete ramps are 82.5% complete (95% CI [79.2%, 85.1%]),
  #          exceeding our 80% target..."
"""
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types of insights the engine can generate."""
    MEETS_SLA = "meets_sla"
    MISSES_SLA = "misses_sla"
    ANOMALY = "anomaly"
    TREND = "trend"
    CORRELATION = "correlation"
    OUTLIER = "outlier"


@dataclass
class Insight:
    """Single narrative insight."""
    type: InsightType
    metric_id: str
    value: float
    narrative: str  # Generated text
    confidence: float  # 0-1: how confident is this insight
    sla_threshold: Optional[float] = None
    sla_met: Optional[bool] = None
    context: Optional[Dict] = None


class NarrativeEngineDefault:
    """Hardcoded narrative templates (no API calls)."""

    def __init__(self):
        self.templates = self._build_templates()

    def _build_templates(self) -> Dict:
        """Build hardcoded insight templates."""
        return {
            "completion_rate": {
                "template": "{metric_name} in {borough} is {value:.1f}% (95% CI [{ci_lower:.1f}%, {ci_upper:.1f}%]). Target: {sla_threshold:.0f}%.",
                "above_sla": "Exceeds target by {diff:.1f} percentage points.",
                "below_sla": "Falls short of target by {diff:.1f} percentage points. Recommend prioritizing {context}.",
                "anomaly": "This represents a {change:.1f}% change from last month's {previous_value:.1f}%.",
            },
            "failure_rate": {
                "template": "{metric_name} in {borough} is {value:.1f}% (95% CI [{ci_lower:.1f}%, {ci_upper:.1f}%]). Target: <{sla_threshold:.0f}%.",
                "above_sla": "Below target rate. {context} is performing well.",
                "below_sla": "Exceeds safe threshold by {diff:.1f} percentage points. Priority repair areas: {context}.",
                "anomaly": "This increased {change:.1f}% from previous month.",
            },
            "freshness_days": {
                "template": "{metric_name}: {value:.0f} days old (SLA: <{sla_threshold:.0f} days).",
                "above_sla": "Data is current and fresh.",
                "below_sla": "Data is {diff:.0f} days overdue. Immediate refresh recommended.",
                "anomaly": "Update frequency has degraded; last update was {context}.",
            },
            "conflict_density": {
                "template": "{metric_name} in {borough}: {value:.1f}% (SLA: <{sla_threshold:.0f}%).",
                "above_sla": "Scheduling coordination is excellent; minimal conflicts.",
                "below_sla": "High conflict density indicates scheduling coordination issues. {context}.",
                "anomaly": "Conflicts spiked {change:.1f}%; investigate permit overlap.",
            },
        }

    def generate_narrative(
        self,
        metric_id: str,
        value: float,
        ci_lower: float,
        ci_upper: float,
        sla_threshold: float,
        sla_direction: str = "higher_is_better",
        context: Optional[Dict] = None,
        previous_value: Optional[float] = None,
    ) -> Insight:
        """Generate hardcoded narrative."""
        context = context or {}
        templates = self.templates.get(metric_id, self.templates["completion_rate"])

        # Compute SLA compliance
        if sla_direction == "higher_is_better":
            sla_met = value >= sla_threshold
            diff = value - sla_threshold
        else:
            sla_met = value <= sla_threshold
            diff = sla_threshold - value

        # Build narrative
        narrative = templates["template"].format(
            metric_name=metric_id.replace("_", " ").title(),
            value=value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            sla_threshold=sla_threshold,
            borough=context.get("borough", "Unknown"),
            context=context.get("detail", ""),
        )

        # Add SLA clause
        if sla_met:
            narrative += " " + templates["above_sla"].format(diff=diff, context=context.get("detail", ""))
            insight_type = InsightType.MEETS_SLA
        else:
            narrative += " " + templates["below_sla"].format(diff=diff, context=context.get("detail", ""))
            insight_type = InsightType.MISSES_SLA

        # Add anomaly detection if previous value available
        if previous_value is not None:
            change = ((value - previous_value) / previous_value * 100) if previous_value != 0 else 0
            if abs(change) > 10:  # >10% change is anomalous
                narrative += " " + templates["anomaly"].format(
                    change=change, previous_value=previous_value, context=context.get("detail", "")
                )
                insight_type = InsightType.ANOMALY

        return Insight(
            type=insight_type,
            metric_id=metric_id,
            value=value,
            narrative=narrative,
            confidence=0.95,  # High confidence for hardcoded templates
            sla_threshold=sla_threshold,
            sla_met=sla_met,
            context=context,
        )


class NarrativeEngineEnhanced:
    """LangChain + Claude API for rich narratives (optional)."""

    def __init__(self):
        try:
            from langchain.chat_models import ChatAnthropic
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain

            self.llm = ChatAnthropic(model="claude-opus-4-8")
            self.prompt_template = PromptTemplate(
                input_variables=["metric_id", "value", "ci_lower", "ci_upper", "sla_threshold", "sla_met", "context"],
                template="""Given a metric result, generate a concise 2-3 sentence business insight.

Metric: {metric_id}
Value: {value:.1f}
95% CI: [{ci_lower:.1f}, {ci_upper:.1f}]
SLA Target: {sla_threshold:.1f}
SLA Met: {sla_met}
Context: {context}

Generate insight that:
1. States the finding clearly
2. Compares to SLA/target
3. Implies next action

Insight:""",
            )
            self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
            self.available = True
            logger.info("Enhanced narrative engine initialized (LangChain + Claude)")
        except ImportError:
            self.available = False
            logger.warning("LangChain not installed; falling back to hardcoded narratives")

    def generate_narrative(self, metric_id: str, value: float, ci_lower: float, ci_upper: float, sla_threshold: float, sla_direction: str = "higher_is_better", context: Optional[Dict] = None, **kwargs) -> str:
        """Generate enhanced narrative using Claude API."""
        if not self.available:
            return None

        context_str = ", ".join(f"{k}={v}" for k, v in (context or {}).items())
        sla_met = (value >= sla_threshold) if sla_direction == "higher_is_better" else (value <= sla_threshold)

        try:
            result = self.chain.run(
                metric_id=metric_id,
                value=value,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                sla_threshold=sla_threshold,
                sla_met=sla_met,
                context=context_str,
            )
            return result.strip()
        except Exception as e:
            logger.error(f"Enhanced narrative generation failed: {e}")
            return None


class NarrativeEngine:
    """Dual-mode narrative engine: hardcoded default + optional AI-enhanced.

    Usage:
      engine = NarrativeEngine(semantic_enabled=True)
      insight = engine.generate_narrative(
        metric_id="completion_rate",
        value=82.5,
        ci_lower=79.2,
        ci_upper=85.1,
        sla_threshold=80,
        context={"borough": "Brooklyn"}
      )
    """

    def __init__(self, semantic_enabled: bool = True):
        """Initialize engine.

        Args:
            semantic_enabled: Try to use LangChain + Claude (falls back to hardcoded if unavailable)
        """
        self.default_engine = NarrativeEngineDefault()
        self.enhanced_engine = None

        if semantic_enabled:
            self.enhanced_engine = NarrativeEngineEnhanced()
            if self.enhanced_engine.available:
                logger.info("NarrativeEngine operating in ENHANCED mode (AI-powered)")
            else:
                logger.info("NarrativeEngine operating in DEFAULT mode (hardcoded)")
        else:
            logger.info("NarrativeEngine operating in DEFAULT mode (AI disabled)")

    def generate_narrative(
        self,
        metric_id: str,
        value: float,
        ci_lower: float,
        ci_upper: float,
        sla_threshold: float,
        sla_direction: str = "higher_is_better",
        context: Optional[Dict] = None,
        previous_value: Optional[float] = None,
    ) -> Insight:
        """Generate insight with AI fallback to hardcoded.

        If enhanced mode available and AI succeeds, use rich narrative.
        Otherwise fall back to hardcoded templates.
        """
        # Try enhanced mode first
        if self.enhanced_engine and self.enhanced_engine.available:
            try:
                ai_narrative = self.enhanced_engine.generate_narrative(
                    metric_id=metric_id,
                    value=value,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    sla_threshold=sla_threshold,
                    sla_direction=sla_direction,
                    context=context,
                    previous_value=previous_value,
                )
                if ai_narrative:
                    # Compute SLA compliance
                    if sla_direction == "higher_is_better":
                        sla_met = value >= sla_threshold
                    else:
                        sla_met = value <= sla_threshold

                    return Insight(
                        type=InsightType.MEETS_SLA if sla_met else InsightType.MISSES_SLA,
                        metric_id=metric_id,
                        value=value,
                        narrative=ai_narrative,
                        confidence=0.90,
                        sla_threshold=sla_threshold,
                        sla_met=sla_met,
                        context=context,
                    )
            except Exception as e:
                logger.warning(f"Enhanced narrative generation failed, falling back: {e}")

        # Fall back to hardcoded templates
        return self.default_engine.generate_narrative(
            metric_id=metric_id,
            value=value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            sla_threshold=sla_threshold,
            sla_direction=sla_direction,
            context=context,
            previous_value=previous_value,
        )

    def is_enhanced(self) -> bool:
        """Check if enhanced mode is active."""
        return self.enhanced_engine and self.enhanced_engine.available
