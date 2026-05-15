import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import Any, final

from nicegui import ui

from nyc_data.socrata_toolkit.ai_triage_block import AITriageBlock
from nyc_data.socrata_toolkit.core import DEFAULT_DOMAIN, SocrataClient
from nyc_data.socrata_toolkit.daily_briefing_block import DailyBriefingBlock
from nyc_data.socrata_toolkit.knowledge_graph_block import KnowledgeGraphBlock
from nyc_data.socrata_toolkit.map_block import InteractiveMapBlock
from nyc_data.socrata_toolkit.material_breakdown_block import MaterialBreakdownBlock
from nyc_data.socrata_toolkit.query_engine_block import QueryEngineBlock
from nyc_data.socrata_toolkit.sandbox_block import SidewalkSandboxBlock


@final
class WorkspaceState:
    """Shared state to hold datasets across different UI tabs."""

    def __init__(self) -> None:
        self.datasets: dict[str, Any] = {}


state = WorkspaceState()

with ui.header().classes("bg-blue-900 text-white p-4 items-center justify-between"):
    _ = ui.label("🗽 NYC DOT Mission Control").classes("text-2xl font-bold")

    def load_data() -> None:
        ui.notify("Fetching latest 311 complaints from Socrata...", type="info")
        try:
            client = SocrataClient()
            df = client.fetch_dataframe(DEFAULT_DOMAIN, "erm2-nwe9", max_rows=500)
            state.datasets["defects"] = df
            ui.notify(f"✅ Loaded {len(df)} records into workspace!", type="positive")
        except Exception as e:
            ui.notify(f"❌ Error loading data: {e}", type="negative")

    _ = ui.button("Fetch 311 Data", icon="cloud_download", on_click=load_data).classes(
        "bg-green-600"
    )

with ui.tabs().classes("w-full") as tabs:
    t1 = ui.tab("Briefing", icon="newspaper")
    t2 = ui.tab("AI Triage", icon="smart_toy")
    t3 = ui.tab("NLQ Engine", icon="search")
    t4 = ui.tab("Map", icon="map")
    t5 = ui.tab("Knowledge Graph", icon="hub")
    t6 = ui.tab("Sandbox", icon="architecture")
    t7 = ui.tab("Materials", icon="pie_chart")

with ui.tab_panels(tabs, value=t1).classes("w-full max-w-7xl mx-auto mt-6 bg-transparent"):
    with ui.tab_panel(t1):
        DailyBriefingBlock(state).render()
    with ui.tab_panel(t2):
        AITriageBlock(state).render()
    with ui.tab_panel(t3):
        QueryEngineBlock(state).render()
    with ui.tab_panel(t4):
        InteractiveMapBlock(state).render()
    with ui.tab_panel(t5):
        KnowledgeGraphBlock(state).render()
    with ui.tab_panel(t6):
        SidewalkSandboxBlock().render()
    with ui.tab_panel(t7):
        MaterialBreakdownBlock(state).render()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="NYC DOT Mission Control", port=8501, dark=None)
