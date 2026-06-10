"""
Core Analytical Engine for the SIM Mission Control workstation.
Hardcodes the utilities and logic of the AI agent's internal skills.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

class AnalysisResult:
    """
    Unified data structure for analytical findings.

    Attributes:
        skill_name (str): Name of the skill that generated the result.
        success (bool): Whether the analysis completed without errors.
        data (dict[str, Any]): The primary analytical output (e.g., metrics, cluster maps).
        metadata (dict[str, Any]): Additional context (e.g., version, execution time).
        timestamp (str): ISO formatted UTC timestamp of completion.
    """

    def __init__(
        self,
        skill_name: str,
        success: bool,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None
    ):
        self.skill_name = skill_name
        self.success = success
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

        logger.debug("AnalysisResult created for %s (Success: %s)", skill_name, success)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the result to a dictionary for unified reporting."""
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

def log_analysis_result(manager: Any, result: AnalysisResult) -> None:
    """
    Persists an AnalysisResult to the DuckDB analysis_history table.

    Args:
        manager (DuckDBManager): Active database manager.
        result (AnalysisResult): The result to log.
    """
    import json

    # Ensure history table exists
    manager.conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            skill_name VARCHAR,
            success BOOLEAN,
            table_name VARCHAR,
            data JSON,
            metadata JSON
        )
    """)

    # Extract table_name from metadata if present
    table_name = result.metadata.get("table_name") or result.metadata.get("dataset_key") or "N/A"

    manager.conn.execute(
        "INSERT INTO analysis_history (skill_name, success, table_name, data, metadata) VALUES (?, ?, ?, ?, ?)",
        [result.skill_name, result.success, table_name, json.dumps(result.data), json.dumps(result.metadata)]
    )
    logger.info("Logged %s result for %s to analysis_history", result.skill_name, table_name)

class BaseSkill(ABC):
    """
    Abstract base class for all hardcoded analytical skills.

    Ensures a standardized interface for initialization, logging, and execution.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing %s", self.__class__.__name__)

    @abstractmethod
    def run(self, **kwargs) -> AnalysisResult:
        """
        Executes the skill's logic.

        Args:
            **kwargs: Skill-specific parameters.

        Returns:
            AnalysisResult: The findings from the execution.
        """
        pass
