"""
socrata_toolkit/material_breakdown_block.py - NiceGUI component for material analysis.
"""

from nicegui import ui

from .analysis import material_borough_subplots, material_breakdown_pie_chart


class MaterialBreakdownBlock:
    """
    NiceGUI block for visualizing material breakdown across boroughs.
    Used in the main NiceGUI app (app.py).
    """

    def __init__(self, workspace_state):
        self.state = workspace_state
        self.material_col = "material"
        self.borough_col = "borough"

    def render(self):
        self.container = ui.column().classes("w-full p-4")
        self.build()

    def build(self):
        with self.container:
            ui.label("Material Composition Analysis").classes("text-2xl font-bold mb-4")

            with ui.row().classes("w-full items-start gap-4"):
                # Left side: Global breakdown
                with ui.card().classes("p-4 flex-grow"):
                    ui.label("Global Distribution").classes("text-lg font-semibold mb-2")
                    self.global_chart_container = ui.column().classes("w-full")

                # Right side: Borough breakdown
                with ui.card().classes("p-4 flex-grow"):
                    ui.label("By Borough").classes("text-lg font-semibold mb-2")
                    self.borough_chart_container = ui.column().classes("w-full")

            self.update_charts()

    def update_charts(self):
        # Assume we run analysis on 'defects' dataset if present
        target_ds_name = (
            "defects"
            if "defects" in self.state.datasets
            else list(self.state.datasets.keys())[0] if self.state.datasets else None
        )

        if not target_ds_name:
            with self.global_chart_container:
                ui.label("No datasets loaded. Please fetch data first.").classes(
                    "text-gray-500 italic"
                )
            return

        df = self.state.datasets[target_ds_name]

        if df.empty:
            with self.global_chart_container:
                ui.label("No data available in selected dataset").classes("text-gray-500 italic")
            return

        # Global Pie Chart
        fig_global = material_breakdown_pie_chart(df, self.material_col)
        with self.global_chart_container:
            self.global_chart_container.clear()
            ui.plotly(fig_global).classes("w-full h-96")

        # Borough Subplots
        fig_boro = material_borough_subplots(df, self.material_col, self.borough_col)
        with self.borough_chart_container:
            self.borough_chart_container.clear()
            ui.plotly(fig_boro).classes("w-full h-96")

    async def refresh_data(self):
        """Update the block based on the current state."""
        self.update_charts()
