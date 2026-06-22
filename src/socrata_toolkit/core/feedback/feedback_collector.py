from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Dict, List, Optional


@dataclass
class FeedbackRecord:
    timestamp: str
    question: str
    matched_kpi_id: str
    helpful: bool
    corrected_kpi_id: Optional[str] = None


class FeedbackCollector:
    """
    Collects analyst feedback on routing results.
    Triggers retraining when threshold is reached.
    """

    def __init__(self, accumulation_threshold: int = 500):
        """
        Args:
            accumulation_threshold: # of feedback items before triggering retrain
        """
        self.feedback: List[FeedbackRecord] = []
        self.threshold = accumulation_threshold

    def mark_helpful(self, question: str, matched_kpi_id: str):
        """Mark a routing result as helpful"""
        record = FeedbackRecord(
            timestamp=datetime.now(UTC).isoformat(),
            question=question,
            matched_kpi_id=matched_kpi_id,
            helpful=True
        )
        self.feedback.append(record)

    def mark_wrong(self, question: str, matched_kpi_id: str, corrected_kpi_id: str):
        """Mark a routing result as wrong and provide correction"""
        record = FeedbackRecord(
            timestamp=datetime.now(UTC).isoformat(),
            question=question,
            matched_kpi_id=matched_kpi_id,
            helpful=False,
            corrected_kpi_id=corrected_kpi_id
        )
        self.feedback.append(record)

    def get_feedback(self) -> List[Dict]:
        """Get accumulated feedback as list of dicts"""
        return [asdict(f) for f in self.feedback]

    def should_retrain(self) -> bool:
        """Check if feedback threshold reached"""
        return len(self.feedback) >= self.threshold

    def clear_feedback(self):
        """Clear feedback after processing"""
        self.feedback = []


__all__ = ["FeedbackCollector", "FeedbackRecord"]
