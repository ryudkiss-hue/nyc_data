"""Sentiment classification for 311 complaints and correspondences.

Hardcoded deterministic classifiers using spaCy + TextBlob sentiment.
Analyzes tone, root causes, repeat patterns, and community impact.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import spacy

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    text: str
    tone: str  # FRUSTRATED, ANGRY, RESIGNED, HELPFUL, NEUTRAL
    tone_confidence: float  # 0-100
    root_cause: str  # NEGLECT, POOR_QUALITY, SLOW_RESPONSE, LACK_OF_FOLLOWUP, OTHER
    root_cause_confidence: float  # 0-100
    is_repeat_complaint: bool  # YES, NO, LIKELY
    repeat_likelihood: float  # 0-100 (how likely based on language patterns)
    community_impact: str  # HIGH, MEDIUM, LOW
    impact_score: float  # 0-100
    extracted_keywords: list[str]
    address_context: Optional[str] = None
    sentiment_score: float = 0.0  # -1 to 1 from TextBlob


class SentimentClassifier:
    """Classify sentiment, tone, and root causes in 311 complaints and public correspondence."""

    # Tone patterns
    TONE_PATTERNS = {
        "FRUSTRATED": {
            "keywords": [
                "frustrated", "frustrating", "annoyed", "annoying", "inconvenient",
                "inconvenience", "tired", "tired of", "over it", "enough",
                "ridiculous", "absurd", "ridiculous", "waste", "wasted"
            ],
            "negation_boost": False,  # Don't flip meaning if negated
        },
        "ANGRY": {
            "keywords": [
                "angry", "furious", "outraged", "outrageous", "disgusted",
                "disgusting", "unacceptable", "unacceptable", "furious",
                "infuriated", "rage", "outrage", "fed up", "sick of"
            ],
            "negation_boost": False,
        },
        "RESIGNED": {
            "keywords": [
                "nothing can be done", "no point", "pointless", "doesn't matter",
                "always like this", "never fixed", "always broken", "give up",
                "no help", "no use", "hopeless", "helpless", "whatever"
            ],
            "negation_boost": False,
        },
        "HELPFUL": {
            "keywords": [
                "thank", "grateful", "appreciate", "appreciate", "appreciate",
                "helpful", "pleased", "satisfied", "excellent", "great",
                "wonderful", "amazing", "quickly", "fixed", "resolved"
            ],
            "negation_boost": True,  # Flip if negated
        },
        "NEUTRAL": {
            "keywords": [
                "report", "request", "please fix", "needs repair", "broken",
                "damaged", "issue", "problem", "concern", "observed"
            ],
            "negation_boost": False,
        },
    }

    # Root cause patterns
    ROOT_CAUSE_PATTERNS = {
        "NEGLECT": {
            "keywords": [
                "neglected", "neglect", "ignored", "ignore", "no attention",
                "no maintenance", "maintenance", "forgotten", "nobody cares",
                "not maintained", "unkempt", "unkempt", "dirty", "filthy"
            ],
            "description": "City not maintaining or attending to the issue"
        },
        "POOR_QUALITY": {
            "keywords": [
                "poor quality", "cheap", "cheaply made", "shoddy", "faulty",
                "defective", "breaks again", "keeps breaking", "constantly breaking",
                "never lasts", "inferior", "inadequate", "substandard"
            ],
            "description": "Repairs are low quality or materials fail quickly"
        },
        "SLOW_RESPONSE": {
            "keywords": [
                "slow", "slow response", "delayed", "delay", "takes too long",
                "months", "years", "waiting", "wait months", "wait years",
                "never comes", "never responds", "no response", "ignored"
            ],
            "description": "City takes too long to respond or repair"
        },
        "LACK_OF_FOLLOWUP": {
            "keywords": [
                "follow up", "follow-up", "followup", "no follow-up", "never follow up",
                "no update", "no communication", "no word", "hasn't heard back",
                "no closure", "unresolved", "still waiting", "still unfixed"
            ],
            "description": "No communication or closure after initial report"
        },
        "OTHER": {
            "keywords": [],
            "description": "Other or unknown root cause"
        },
    }

    # Repeat complaint patterns
    REPEAT_PATTERNS = {
        "SAME_ADDRESS": [
            "again", "still broken", "still not fixed", "same problem",
            "keeps breaking", "keeps happening", "recurring", "again and again"
        ],
        "SAME_ISSUE": [
            "same issue", "same problem", "same violation", "identical",
            "repeat violation", "recurring issue", "happens all the time"
        ],
        "HISTORY": [
            "reported before", "reported this", "already reported", "filed complaint",
            "called before", "contacted before", "last time", "months ago", "years ago"
        ]
    }

    # Community impact patterns
    COMMUNITY_IMPACT_PATTERNS = {
        "HIGH": {
            "keywords": [
                "safety", "safe", "unsafe", "dangerous", "hazard", "risk",
                "children", "elderly", "disabled", "wheelchair", "ada",
                "injury", "fell", "fallen", "broken leg", "accident", "multiple"
            ],
            "threshold": 4  # Need at least this many high-impact keywords
        },
        "MEDIUM": {
            "keywords": [
                "inconvenient", "inconvenience", "affects", "impacts", "blocks",
                "access", "business", "customers", "foot traffic", "frequent",
                "neighborhood", "block", "street", "people"
            ],
            "threshold": 3
        },
        "LOW": {
            "keywords": [
                "minor", "small", "cosmetic", "not urgent", "low priority",
                "just", "only", "single", "one location"
            ],
            "threshold": 2
        }
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize sentiment classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found. Install with: python -m spacy download {model_name}")
            raise

    def classify(self, text: str, address: Optional[str] = None) -> SentimentResult:
        """Classify a single text (complaint or correspondence).

        Args:
            text: The complaint or correspondence text.
            address: Optional address for context (tracked separately).

        Returns:
            SentimentResult with tone, root cause, repeat likelihood, impact.
        """
        if not text or not isinstance(text, str):
            return self._null_result(text, address)

        doc = self.nlp(text.lower())
        text_lower = text.lower()

        # Classify tone
        tone, tone_confidence = self._classify_tone(text_lower)

        # Classify root cause
        root_cause, root_cause_confidence = self._classify_root_cause(text_lower)

        # Detect repeat complaint patterns
        is_repeat, repeat_likelihood = self._detect_repeat_complaint(text_lower)

        # Assess community impact
        impact, impact_score = self._assess_community_impact(text_lower)

        # Extract keywords
        keywords = self._extract_keywords(text_lower)

        # Compute sentiment score using polarity clues
        sentiment_score = self._compute_sentiment_score(text_lower, tone)

        return SentimentResult(
            text=text[:200],  # First 200 chars
            tone=tone,
            tone_confidence=tone_confidence,
            root_cause=root_cause,
            root_cause_confidence=root_cause_confidence,
            is_repeat_complaint=is_repeat,
            repeat_likelihood=repeat_likelihood,
            community_impact=impact,
            impact_score=impact_score,
            extracted_keywords=keywords,
            address_context=address,
            sentiment_score=sentiment_score,
        )

    def classify_batch(self, texts: list[str], addresses: Optional[list[str]] = None) -> list[SentimentResult]:
        """Classify multiple texts.

        Args:
            texts: List of complaint/correspondence texts.
            addresses: Optional list of addresses (same length as texts).

        Returns:
            List of SentimentResult objects.
        """
        if addresses is None:
            addresses = [None] * len(texts)

        results = []
        for text, address in zip(texts, addresses):
            results.append(self.classify(text, address))
        return results

    def classify_dataframe(
        self,
        df: pd.DataFrame,
        text_column: str,
        address_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """Classify all texts in a DataFrame.

        Args:
            df: DataFrame with text data.
            text_column: Name of column containing text to classify.
            address_column: Optional column with address context.

        Returns:
            DataFrame with sentiment columns added.
        """
        texts = df[text_column].fillna("").tolist()
        addresses = None
        if address_column and address_column in df.columns:
            addresses = df[address_column].fillna("").tolist()

        results = self.classify_batch(texts, addresses)

        # Convert to DataFrame
        result_df = pd.DataFrame([
            {
                "tone": r.tone,
                "tone_confidence": r.tone_confidence,
                "root_cause": r.root_cause,
                "root_cause_confidence": r.root_cause_confidence,
                "is_repeat_complaint": r.is_repeat_complaint,
                "repeat_likelihood": r.repeat_likelihood,
                "community_impact": r.community_impact,
                "impact_score": r.impact_score,
                "sentiment_score": r.sentiment_score,
                "extracted_keywords": ";".join(r.extracted_keywords),
            }
            for r in results
        ])

        return pd.concat([df.reset_index(drop=True), result_df], axis=1)

    def _classify_tone(self, text: str) -> tuple[str, float]:
        """Classify tone of text."""
        max_score = 0
        best_tone = "NEUTRAL"
        best_confidence = 0

        for tone, pattern in self.TONE_PATTERNS.items():
            score = self._keyword_match_score(text, pattern["keywords"])
            if score > max_score:
                max_score = score
                best_tone = tone
                best_confidence = min(100, score * 10)  # Scale to 0-100

        return best_tone, best_confidence

    def _classify_root_cause(self, text: str) -> tuple[str, float]:
        """Classify root cause of complaint."""
        max_score = 0
        best_cause = "OTHER"
        best_confidence = 0

        for cause, pattern in self.ROOT_CAUSE_PATTERNS.items():
            if cause == "OTHER":
                continue
            score = self._keyword_match_score(text, pattern["keywords"])
            if score > max_score:
                max_score = score
                best_cause = cause
                best_confidence = min(100, score * 10)

        return best_cause, best_confidence

    def _detect_repeat_complaint(self, text: str) -> tuple[bool, float]:
        """Detect if this is likely a repeat complaint based on language patterns."""
        repeat_score = 0

        # Check for explicit repeat language
        for keyword in self.REPEAT_PATTERNS["SAME_ADDRESS"]:
            if keyword in text:
                repeat_score += 15

        for keyword in self.REPEAT_PATTERNS["SAME_ISSUE"]:
            if keyword in text:
                repeat_score += 10

        for keyword in self.REPEAT_PATTERNS["HISTORY"]:
            if keyword in text:
                repeat_score += 20

        is_repeat = repeat_score > 20
        likelihood = min(100, repeat_score)

        return is_repeat, likelihood

    def _assess_community_impact(self, text: str) -> tuple[str, float]:
        """Assess community impact level."""
        impact_scores = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }

        for level, pattern in self.COMMUNITY_IMPACT_PATTERNS.items():
            matches = self._keyword_match_score(text, pattern["keywords"])
            impact_scores[level] = matches

        # Determine level
        if impact_scores["HIGH"] >= self.COMMUNITY_IMPACT_PATTERNS["HIGH"]["threshold"]:
            return "HIGH", min(100, impact_scores["HIGH"] * 10)
        elif impact_scores["MEDIUM"] >= self.COMMUNITY_IMPACT_PATTERNS["MEDIUM"]["threshold"]:
            return "MEDIUM", min(100, impact_scores["MEDIUM"] * 10)
        else:
            return "LOW", min(100, impact_scores["LOW"] * 10)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text."""
        keywords = set()

        # Collect all matching keywords
        for tone, pattern in self.TONE_PATTERNS.items():
            for keyword in pattern["keywords"]:
                if keyword in text:
                    keywords.add(keyword)

        for cause, pattern in self.ROOT_CAUSE_PATTERNS.items():
            for keyword in pattern["keywords"]:
                if keyword in text:
                    keywords.add(keyword)

        for level, pattern in self.COMMUNITY_IMPACT_PATTERNS.items():
            for keyword in pattern["keywords"]:
                if keyword in text:
                    keywords.add(keyword)

        return sorted(list(keywords))

    def _keyword_match_score(self, text: str, keywords: list[str]) -> int:
        """Count how many keywords appear in text."""
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
        return score

    def _compute_sentiment_score(self, text: str, tone: str) -> float:
        """Compute sentiment score (-1 to 1) based on tone and polarity clues."""
        positive_words = [
            "thank", "grateful", "appreciate", "pleased", "satisfied",
            "excellent", "great", "wonderful", "amazing", "good", "well",
            "quickly", "resolved", "fixed", "helpful", "professional"
        ]

        negative_words = [
            "angry", "furious", "disgusted", "disgusting", "unacceptable",
            "ridiculous", "absurd", "waste", "frustrated", "annoyed",
            "frustrated", "tired", "sick", "rage", "outrage", "danger",
            "unsafe", "hazard", "neglected", "ignored", "never", "nothing"
        ]

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        # Tone mapping
        tone_bias = {
            "HELPFUL": 0.8,
            "NEUTRAL": 0.0,
            "RESIGNED": -0.5,
            "FRUSTRATED": -0.6,
            "ANGRY": -0.9,
        }

        score = (pos_count - neg_count) / total
        score += tone_bias.get(tone, 0.0) * 0.3

        return max(-1.0, min(1.0, score))

    def _null_result(self, text: str, address: Optional[str] = None) -> SentimentResult:
        """Return neutral result for empty or invalid text."""
        return SentimentResult(
            text="[empty]",
            tone="NEUTRAL",
            tone_confidence=0,
            root_cause="OTHER",
            root_cause_confidence=0,
            is_repeat_complaint=False,
            repeat_likelihood=0,
            community_impact="LOW",
            impact_score=0,
            extracted_keywords=[],
            address_context=address,
            sentiment_score=0.0,
        )
