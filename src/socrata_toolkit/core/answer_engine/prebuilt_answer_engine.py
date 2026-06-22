from typing import Dict, Optional

from ..routing.models import AnswerResult


class PreBuiltAnswerEngine:
    """
    Lookup pre-built answers from KPI registry.
    No LLM calls; fully deterministic and version-controlled.
    """

    def __init__(self, kpi_registry: Dict[str, Dict]):
        """
        Initialize with KPI registry.

        Args:
            kpi_registry: Dict mapping kpi_id -> KPI metadata
        """
        self.registry = kpi_registry

    def get_answer(self, kpi_id: str) -> Optional[AnswerResult]:
        """
        Retrieve pre-built answer for a matched KPI.

        Args:
            kpi_id: The matched KPI ID (e.g., "KPI-089")

        Returns:
            AnswerResult with datasets, SQL pattern, visualizations, etc.
            Returns None if KPI not found.
        """
        if kpi_id not in self.registry:
            return None

        metadata = self.registry[kpi_id]

        return AnswerResult(
            kpi_id=metadata.get('kpi_id'),
            kpi_name=metadata.get('kpi_name'),
            summary=metadata.get('summary', ''),
            datasets=metadata.get('datasets', []),
            sql_pattern=metadata.get('sql_pattern', ''),
            visualizations=metadata.get('visualization_metadata', []),
            confidence=1.0,  # Pre-built answers have full confidence
            source='prebuilt_answer_engine',
            related_kpis=metadata.get('related_kpis', [])
        )


__all__ = ["PreBuiltAnswerEngine"]
