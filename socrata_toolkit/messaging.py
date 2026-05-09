"""Messaging Bot Adapter for DOT Sidewalk Toolkit.

Provides a command parser that accepts natural-language-like queries
and returns structured responses from the toolkit. Designed to power
Slack bots, Teams bots, or any chat-based interface.

Supported queries:
- "status of contract C-12345"
- "manhattan backlog"
- "borough overview queens"
- "quality score"
- "kpi dashboard"
- "search sidewalk inspections"

Example::

    from socrata_toolkit.messaging import BotAdapter

    bot = BotAdapter()
    response = bot.handle("status of contract C-12345", context={"data": df})
    print(response.text)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class BotResponse:
    """Response from the bot adapter."""
    text: str
    data: Optional[Dict[str, Any]] = None
    attachments: List[str] = field(default_factory=list)
    intent: str = "unknown"
    confidence: float = 0.0


class BotAdapter:
    """Natural-language query handler for chat integrations.

    Parses incoming messages, identifies intent, and delegates to
    the appropriate toolkit module for a response.
    """

    def __init__(self, default_data: Optional[pd.DataFrame] = None) -> None:
        self.default_data = default_data
        self._intents = [
            (r"status\s+(?:of\s+)?contract\s+(\S+)", "contract_status"),
            (r"(manhattan|bronx|brooklyn|queens|staten\s*island)\s+backlog", "borough_backlog"),
            (r"borough\s+overview\s+(manhattan|bronx|brooklyn|queens|staten\s*island)", "borough_overview"),
            (r"quality\s+score", "quality_score"),
            (r"kpi\s+dashboard", "kpi_dashboard"),
            (r"search\s+(.+)", "search_datasets"),
            (r"help", "help"),
            (r"hi|hello|hey", "greeting"),
        ]

    def handle(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> BotResponse:
        """Parse a message and return a response.

        Args:
            message: User's message text.
            context: Optional dict with "data" (DataFrame) and other state.
        """
        ctx = context or {}
        df = ctx.get("data", self.default_data)
        msg_lower = message.lower().strip()

        for pattern, intent in self._intents:
            match = re.search(pattern, msg_lower)
            if match:
                handler = getattr(self, f"_handle_{intent}", None)
                if handler:
                    return handler(match, df, ctx)

        return BotResponse(
            text="I didn't understand that. Try 'help' to see what I can do.",
            intent="unknown",
            confidence=0.0,
        )

    def _handle_greeting(self, match, df, ctx) -> BotResponse:
        return BotResponse(
            text="Hey! I'm the DOT Sidewalk Toolkit bot. Ask me about contracts, boroughs, quality scores, or KPIs. Type 'help' for a full list.",
            intent="greeting", confidence=1.0,
        )

    def _handle_help(self, match, df, ctx) -> BotResponse:
        return BotResponse(
            text=(
                "Here's what I can help with:\n"
                "- 'status of contract C-12345' -- Contract status lookup\n"
                "- 'manhattan backlog' -- Borough pending repair count\n"
                "- 'borough overview queens' -- Borough summary\n"
                "- 'quality score' -- Data quality metrics\n"
                "- 'kpi dashboard' -- Program KPIs\n"
                "- 'search sidewalk inspections' -- Search NYC Open Data"
            ),
            intent="help", confidence=1.0,
        )

    def _handle_contract_status(self, match, df, ctx) -> BotResponse:
        contract_id = match.group(1).upper()
        if df is None or df.empty:
            return BotResponse(text=f"No data loaded. Can't look up contract {contract_id}.", intent="contract_status", confidence=0.5)

        contract_col = _find_col(df, ["contract_id", "contract", "contractid"])
        if not contract_col:
            return BotResponse(text="No contract ID column found in the data.", intent="contract_status", confidence=0.3)

        subset = df[df[contract_col].astype(str).str.upper() == contract_id]
        if subset.empty:
            return BotResponse(text=f"No records found for contract {contract_id}.", intent="contract_status", confidence=0.8)

        status_col = _find_col(df, ["status"])
        statuses = subset[status_col].value_counts().to_dict() if status_col else {}
        text = f"Contract {contract_id}: {len(subset)} records."
        if statuses:
            text += " Status: " + ", ".join(f"{k}: {v}" for k, v in statuses.items())

        return BotResponse(text=text, intent="contract_status", confidence=0.9, data={"contract_id": contract_id, "records": len(subset), "statuses": statuses})

    def _handle_borough_backlog(self, match, df, ctx) -> BotResponse:
        borough = match.group(1).upper().replace("  ", " ")
        if df is None or df.empty:
            return BotResponse(text="No data loaded.", intent="borough_backlog", confidence=0.5)

        boro_col = _find_col(df, ["borough"])
        status_col = _find_col(df, ["status"])
        if not boro_col:
            return BotResponse(text="No borough column found.", intent="borough_backlog", confidence=0.3)

        boro_data = df[df[boro_col].str.upper() == borough]
        total = len(boro_data)
        pending = int((boro_data[status_col] == "Pending Repair").sum()) if status_col else 0

        return BotResponse(
            text=f"{borough}: {total} total records, {pending} pending repairs.",
            intent="borough_backlog", confidence=0.9,
            data={"borough": borough, "total": total, "pending": pending},
        )

    def _handle_borough_overview(self, match, df, ctx) -> BotResponse:
        return self._handle_borough_backlog(match, df, ctx)

    def _handle_quality_score(self, match, df, ctx) -> BotResponse:
        if df is None or df.empty:
            return BotResponse(text="No data loaded for quality scoring.", intent="quality_score", confidence=0.5)

        from .governance import compute_quality_score
        score = compute_quality_score(df)
        return BotResponse(
            text=f"Quality Score: {score.overall:.1f}/100 (Completeness: {score.completeness:.1f}%, Consistency: {score.consistency:.1f}%)",
            intent="quality_score", confidence=0.9,
            data={"overall": score.overall, "completeness": score.completeness, "consistency": score.consistency},
        )

    def _handle_kpi_dashboard(self, match, df, ctx) -> BotResponse:
        if df is None or df.empty:
            return BotResponse(text="No data loaded for KPI computation.", intent="kpi_dashboard", confidence=0.5)

        from .program_metrics import compute_program_dashboard
        try:
            dashboard = compute_program_dashboard(df)
            metrics_text = ", ".join(f"{m.name}: {m.value:.2f} ({m.status})" for m in dashboard.metrics)
            return BotResponse(
                text=f"Program Health: {dashboard.overall_health.upper()}. {metrics_text}",
                intent="kpi_dashboard", confidence=0.9,
                data={"health": dashboard.overall_health},
            )
        except Exception as e:
            return BotResponse(text=f"Could not compute KPIs: {e}", intent="kpi_dashboard", confidence=0.5)

    def _handle_search_datasets(self, match, df, ctx) -> BotResponse:
        query = match.group(1).strip()
        try:
            from .client import SocrataClient
            client = SocrataClient()
            results = client.search(query=query, limit=5)
            if not results:
                return BotResponse(text=f"No datasets found for '{query}'.", intent="search_datasets", confidence=0.8)
            text = f"Found {len(results)} datasets:\n"
            for r in results:
                text += f"- {r.name} ({r.fourfour}) -- {r.domain}\n"
            return BotResponse(text=text, intent="search_datasets", confidence=0.9)
        except Exception as e:
            return BotResponse(text=f"Search failed: {e}", intent="search_datasets", confidence=0.3)


def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None
