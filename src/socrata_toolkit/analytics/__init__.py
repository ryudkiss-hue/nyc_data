"""
Core Analytical Engine for the SIM Mission Control workstation.
Hardcodes the utilities and logic of the AI agent's internal skills.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

class AnalysisResult:
    """
    Unified data structure for analytical findings.
    
    Attributes:
        skill_name (str): Name of the skill that generated the result.
        success (bool): Whether the analysis completed without errors.
        data (Dict[str, Any]): The primary analytical output (e.g., metrics, cluster maps).
        metadata (Dict[str, Any]): Additional context (e.g., version, execution time).
        timestamp (str): ISO formatted UTC timestamp of completion.
    """
    
    def __init__(
        self,
        skill_name: str,
        success: bool,
        data: Dict[str, Any],
        metadata: Dict[str, Any] | None = None
    ):
        self.skill_name = skill_name
        self.success = success
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        logger.debug("AnalysisResult created for %s (Success: %s)", skill_name, success)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the result to a dictionary for unified reporting."""
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

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
