"""
Backend services for the Analytical Toolbox.
Bridges the Dash UI with the socrata_toolkit.analytics package.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from socrata_toolkit.analytics import log_analysis_result
from socrata_toolkit.analytics.quality import DataQualityAudit

logger = logging.getLogger(__name__)

def run_dataset_audit(manager: Any, dataset_key: str) -> dict[str, Any]:
    """
    Runs a DataQualityAudit on a locally cached dataset.
    """
    try:
        from socrata_toolkit.core import DuckDBRepository
        repo = DuckDBRepository(manager, dataset_key)
        df = repo.fetch_all(limit=10000)

        if df.empty:
            return {"success": False, "error": f"No data found for {dataset_key}"}

        audit = DataQualityAudit()
        result = audit.run(df=df, table_name=dataset_key)

        # Persist to history
        log_analysis_result(manager, result)

        return {
            "success": True,
            "skill_name": result.skill_name,
            "timestamp": result.timestamp,
            "data": result.data
        }
    except Exception as e:
        logger.error("Audit service failed for %s: %s", dataset_key, e)
        return {"success": False, "error": str(e)}

def get_analysis_history(manager: Any, limit: int = 20) -> list[dict[str, Any]]:
    """
    Retrieves the most recent analysis events from DuckDB.
    """
    try:
        query = f"SELECT timestamp, skill_name, table_name, success FROM analysis_history ORDER BY timestamp DESC LIMIT {limit}"
        df = manager.conn.execute(query).df()
        return df.to_dict("records")
    except Exception as e:
        logger.warning("Could not fetch analysis history: %s", e)
        return []

def synthesize_executive_summary(raw_findings: str) -> str:
    """
    Mock AI synthesis of analytical findings into an executive brief.
    In production, this would call the LLMProxy.
    """
    if not raw_findings:
        return "No findings provided."

    summary = [
        "### EXECUTIVE SUMMARY",
        f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}",
        "",
        "#### Key Findings",
        "- Analytical sweep identified significant variance in operational metrics.",
        "- Schema alignment remains within 98% of registry specifications.",
        "- Outlier detection flagged potential data entry anomalies in recent batches.",
        "",
        "#### Recommendations",
        "1. Immediate reconciliation of row counts for flagged datasets.",
        "2. Review Z-score > 3 records with relevant borough analysts.",
        "3. Standardize timestamp formatting to ensure 100% SODA3 compatibility."
    ]
    return "\n".join(summary)
