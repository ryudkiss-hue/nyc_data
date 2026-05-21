from nicegui import ui

from ...viz import generate_semantic_network_map


class KnowledgeGraphBlock:
    """Interactive GUI block for visualizing the Semantic Knowledge Graph."""

    def __init__(self, workspace_state=None):
        self.state = workspace_state

    def render(self):
        """Renders the knowledge graph block."""
        with ui.card().classes("w-full border border-gray-200 shadow-sm"):
            with ui.row().classes("w-full items-center justify-between mb-4"):
                ui.label("🕸️ Toolkit Semantic Network Map").classes(
                    "text-xl font-bold text-gray-800 dark:text-gray-200"
                )
                ui.button("Refresh Map", icon="refresh", on_click=self.plot_map).classes(
                    "bg-blue-600 text-white outline"
                )

            self.map_container = ui.column().classes(
                "w-full items-center bg-gray-50 dark:bg-gray-900 rounded p-2"
            )
            self.plot_map()

    def plot_map(self):
        self.map_container.clear()
        with self.map_container:
            fig = generate_semantic_network_map()
            ui.plotly(fig).classes("w-full h-[700px]")

