from nicegui import ui
import pandas as pd

from .nlq_parser import parse_query
from .analysis import hotspot_density_mapbox, material_breakdown_pie_chart, gauge_chart

class QueryEngineBlock:
    """A Wolfram-Alpha-esque natural language query interface."""
    def __init__(self, workspace_state):
        self.state = workspace_state

    def render(self):
        with ui.card().classes('w-full border-2 border-blue-500 shadow-lg'):
            with ui.row().classes('w-full items-center gap-4'):
                self.query_input = ui.input(
                    placeholder='e.g., "Show hazardous defects in Brooklyn" or "Count inspections by material"'
                ).classes('flex-grow').props('outlined dense')
                
                ui.button('Compute', on_click=self.run_query, icon='functions').classes('bg-blue-600 text-white')

            self.results_container = ui.column().classes('w-full mt-4 items-center')

    async def run_query(self):
        """Parse the query and dispatch to the correct analysis/visualization function."""
        query_text = self.query_input.value
        if not query_text:
            return

        intent = parse_query(query_text)
        self.results_container.clear()

        with self.results_container:
            if not intent:
                ui.label("I'm sorry, I didn't understand that query.").classes('text-red-500')
                return

            # For this demo, we assume a single, pre-loaded 'defects' dataset
            if 'defects' not in self.state.datasets:
                ui.label("Please load a 'defects' dataset first.").classes('text-red-500')
                return
            
            df = self.state.datasets['defects']
            
            # Apply filters
            if 'borough' in intent.filters:
                df = df[df['borough'].str.upper() == intent.filters['borough']]
            if 'severity' in intent.filters:
                df = df[df['severity'].str.lower() == intent.filters['severity']]

            # --- Dispatcher Logic ---
            if intent.intent == 'show' and intent.target == 'defects':
                ui.label(f"Displaying map for: '{query_text}'").classes('italic text-gray-500 mb-2')
                fig = hotspot_density_mapbox(df, title=f"Query: {query_text}")
                ui.plotly(fig).classes('w-full h-[600px]')
                
            elif intent.intent == 'count' and intent.group_by == 'material_type':
                ui.label(f"Displaying chart for: '{query_text}'").classes('italic text-gray-500 mb-2')
                fig = material_breakdown_pie_chart(df, material_col='material_type', title=f"Query: {query_text}")
                ui.plotly(fig).classes('w-full h-[500px]')

            elif intent.intent == 'get' and intent.target == 'ada_compliance_rate':
                # Placeholder for actual calculation
                compliance_rate = 92.3 
                ui.label(f"Computing: '{query_text}'").classes('italic text-gray-500 mb-2')
                fig = gauge_chart(compliance_rate, target=95.0, title="ADA Compliance Rate")
                ui.plotly(fig).classes('w-full h-64')
            
            else:
                ui.label(f"I understood the intent, but a visualization for it isn't implemented yet.").classes('text-orange-500')
                ui.json_editor({'content': {'json': intent.__dict__}})