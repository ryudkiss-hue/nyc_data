"""Layer 4: NL Answering - Ask what you want, get SQL + results (dual-mode).

DEFAULT MODE:
- Hardcoded intent classifier (12 metrics → intent mapping)
- Pattern matching for common question types
- Instant, no APIs

ENHANCED MODE (optional):
- Semantic matching (embed questions, find similar metrics)
- LangChain for multi-step reasoning
- Fallback to hardcoded if unavailable

Pattern:
  nlizer = NLAnalyzer(semantic_enabled=True)
  query = "Show me ramp completion by borough with confidence intervals"
  result = nlizer.ask(query)
  # Returns: {sql, intent, metric_id, result, confidence}
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Question intent types."""
    SHOW_METRIC = "show_metric"  # "Show me completion rate"
    COMPARE_METRIC = "compare"  # "Which borough has highest failure rate?"
    TREND = "trend"  # "How has completion changed over time?"
    ANOMALY = "anomaly"  # "Why did completion drop?"
    FORECAST = "forecast"  # "When will we reach 90% completion?"
    ROOT_CAUSE = "root_cause"  # "What's causing low completion?"
    UNKNOWN = "unknown"


@dataclass
class NLResult:
    """Result of NL query."""
    intent: IntentType
    metric_id: str
    sql: str
    confidence: float  # 0-1
    message: str  # Natural language explanation
    result: Optional[dict] = None  # Query result if executed


class IntentClassifierDefault:
    """Hardcoded intent classification (no API calls)."""

    def __init__(self, metrics_registry):
        self.metrics_registry = metrics_registry
        self.intent_patterns = self._build_patterns()

    def _build_patterns(self) -> dict:
        """Build hardcoded question patterns."""
        return {
            IntentType.SHOW_METRIC: {
                "patterns": [
                    "show me", "display", "what is", "how much", "percentage", "rate",
                    "give me", "calculate", "count"
                ],
                "metric_keywords": {
                    "completion": "completion_rate",
                    "failure": "condition_failure_rate",
                    "fresh": "freshness_days",
                    "conflict": "conflict_density",
                    "ramp": "completion_rate",
                    "sidewalk": "condition_failure_rate",
                },
            },
            IntentType.COMPARE_METRIC: {
                "patterns": ["compare", "which", "highest", "lowest", "most", "least", "better", "worse"],
            },
            IntentType.TREND: {
                "patterns": ["trend", "change", "over time", "monthly", "year", "growth", "decline"],
            },
            IntentType.ANOMALY: {
                "patterns": ["why", "drop", "spike", "unusual", "odd", "strange", "abnormal"],
            },
            IntentType.FORECAST: {
                "patterns": ["when", "forecast", "predict", "estimate", "expect", "project"],
            },
            IntentType.ROOT_CAUSE: {
                "patterns": ["cause", "reason", "because", "driving", "factor", "driver"],
            },
        }

    def classify(self, question: str) -> tuple[IntentType, str, float]:
        """Classify question intent.

        Returns: (intent_type, metric_id, confidence)
        """
        q_lower = question.lower()

        # Step 1: Find metric keyword
        metric_id = None
        for intent_type, config in self.intent_patterns.items():
            if "metric_keywords" in config:
                for keyword, mid in config["metric_keywords"].items():
                    if keyword in q_lower:
                        metric_id = mid
                        break

        if not metric_id:
            # Try to find any registered metric name in question
            for metric in self.metrics_registry.list_metrics():
                if metric.id.replace("_", " ") in q_lower or metric.name.lower() in q_lower:
                    metric_id = metric.id
                    break

        if not metric_id:
            return IntentType.UNKNOWN, None, 0.0

        # Step 2: Classify intent by pattern matching
        intent_scores = {}
        for intent_type, config in self.intent_patterns.items():
            patterns = config.get("patterns", [])
            matches = sum(1 for p in patterns if p in q_lower)
            intent_scores[intent_type] = matches

        # Pick intent with highest pattern matches
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent] / 3.0, 1.0)  # Normalize to 0-1

        return best_intent, metric_id, confidence


class NLAnalyzerDefault:
    """Hardcoded NL analyzer (no semantic matching)."""

    def __init__(self, metrics_registry):
        self.metrics_registry = metrics_registry
        self.classifier = IntentClassifierDefault(metrics_registry)

    def ask(self, question: str) -> NLResult:
        """Process natural language question."""
        # Classify intent
        intent, metric_id, confidence = self.classifier.classify(question)

        if intent == IntentType.UNKNOWN or not metric_id:
            return NLResult(
                intent=IntentType.UNKNOWN,
                metric_id=None,
                sql=None,
                confidence=0.0,
                message="I didn't understand the question. Try asking about: completion_rate, failure_rate, freshness_days, or conflict_density.",
            )

        metric = self.metrics_registry.get(metric_id)

        # Build SQL based on intent
        if intent == IntentType.SHOW_METRIC:
            sql = f"SELECT * FROM analytics.{metric_id} LIMIT 100"
        elif intent == IntentType.COMPARE_METRIC:
            sql = f"SELECT borough, {metric_id} FROM analytics.{metric_id} ORDER BY 2 DESC"
        elif intent == IntentType.TREND:
            sql = f"SELECT DATE_TRUNC('month', date) as month, AVG(value) FROM analytics.{metric_id} GROUP BY 1 ORDER BY 1 DESC LIMIT 12"
        else:
            sql = f"SELECT * FROM analytics.{metric_id} LIMIT 100"

        return NLResult(
            intent=intent,
            metric_id=metric_id,
            sql=sql,
            confidence=confidence,
            message=f"Found intent: {intent.value}. Querying {metric.name}.",
        )


class NLAnalyzerEnhanced:
    """Semantic matching NL analyzer (LangChain + embeddings)."""

    def __init__(self, metrics_registry):
        self.metrics_registry = metrics_registry
        self.available = False

        try:
            from langchain.chains import LLMChain
            from langchain.chat_models import ChatAnthropic
            from langchain.embeddings import OpenAIEmbeddings
            from langchain.prompts import PromptTemplate

            self.embeddings = OpenAIEmbeddings()
            self.llm = ChatAnthropic(model="claude-opus-4-8")

            # Embed all metric descriptions once
            self.metric_embeddings = {}
            for metric in metrics_registry.list_metrics():
                self.metric_embeddings[metric.id] = self.embeddings.embed_query(metric.description)

            self.sql_chain = LLMChain(
                llm=self.llm,
                prompt=PromptTemplate(
                    input_variables=["intent", "metric_id", "question"],
                    template="Generate SQL for: intent={intent}, metric={metric_id}, question={question}",
                ),
            )

            self.available = True
            logger.info("Enhanced NL analyzer initialized (semantic matching)")
        except ImportError:
            logger.warning("Semantic matching not available; using hardcoded classifier")

    def find_metric(self, question: str) -> tuple[str, float]:
        """Find best metric via semantic similarity."""
        if not self.available:
            return None, 0.0

        try:
            q_embedding = self.embeddings.embed_query(question)

            # Compute similarity to all metrics
            similarities = {}
            for metric_id, metric_embedding in self.metric_embeddings.items():
                # Cosine similarity
                sim = sum(a * b for a, b in zip(q_embedding, metric_embedding)) / (
                    (sum(a ** 2 for a in q_embedding) ** 0.5) * (sum(b ** 2 for b in metric_embedding) ** 0.5)
                )
                similarities[metric_id] = sim

            best_metric = max(similarities, key=similarities.get)
            return best_metric, similarities[best_metric]
        except Exception as e:
            logger.error(f"Semantic matching failed: {e}")
            return None, 0.0


class NLAnalyzer:
    """Dual-mode NL analyzer: hardcoded + optional semantic matching.

    Usage:
      analyzer = NLAnalyzer(metrics_registry, semantic_enabled=True)
      result = analyzer.ask("Show me ramp completion by borough")
      print(result.sql)  # Generated SQL
      print(result.message)  # Explanation
    """

    def __init__(self, metrics_registry, semantic_enabled: bool = True):
        self.metrics_registry = metrics_registry
        self.default_analyzer = NLAnalyzerDefault(metrics_registry)
        self.enhanced_analyzer = None

        if semantic_enabled:
            self.enhanced_analyzer = NLAnalyzerEnhanced(metrics_registry)

    def ask(self, question: str) -> NLResult:
        """Process natural language question with fallback."""
        # Try semantic matching first
        if self.enhanced_analyzer and self.enhanced_analyzer.available:
            metric_id, similarity = self.enhanced_analyzer.find_metric(question)
            if metric_id and similarity > 0.7:  # High confidence threshold
                # Generate SQL with LangChain
                try:
                    sql = self.enhanced_analyzer.sql_chain.run(
                        intent="semantic_match", metric_id=metric_id, question=question
                    )
                    return NLResult(
                        intent=IntentType.SHOW_METRIC,
                        metric_id=metric_id,
                        sql=sql.strip(),
                        confidence=similarity,
                        message=f"Matched metric: {metric_id} (semantic similarity: {similarity:.2f})",
                    )
                except Exception as e:
                    logger.warning(f"Semantic SQL generation failed, falling back: {e}")

        # Fall back to hardcoded analyzer
        return self.default_analyzer.ask(question)
