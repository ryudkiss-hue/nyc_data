import os
import json
from pathlib import Path
from typing import Dict, List


class Config:
    """Configuration management for the fuzzy router system"""

    def __init__(self):
        """Initialize configuration from environment or defaults"""
        self.registry_path = os.getenv(
            "ROUTER_REGISTRY_PATH",
            "config/kpi_registry.json"
        )
        self.questions_path = os.getenv(
            "ROUTER_QUESTIONS_PATH",
            "config/research_questions.json"
        )
        self.embeddings_cache_path = os.getenv(
            "ROUTER_EMBEDDINGS_CACHE_PATH",
            "cache/kpi_embeddings.json"
        )
        self.db_path = os.getenv(
            "ROUTER_OBSERVABILITY_DB",
            "data/local_db/router_observability.duckdb"
        )
        self.debug = os.getenv("ROUTER_DEBUG", "").lower() in ("true", "1", "yes")

    def load_kpi_registry(self) -> Dict:
        """Load KPI registry from file"""
        path = Path(self.registry_path)
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def load_research_questions(self) -> List:
        """Load research questions from file"""
        path = Path(self.questions_path)
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    def load_embeddings_cache(self) -> Dict:
        """Load embeddings cache from file"""
        path = Path(self.embeddings_cache_path)
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            Path(self.db_path).parent,
            Path(self.embeddings_cache_path).parent,
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)


_config = None


def get_config() -> Config:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_directories()
    return _config
