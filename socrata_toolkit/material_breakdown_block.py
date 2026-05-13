from nicegui import ui
import pandas as pd
from typing import Any

from socrata_toolkit.analysis import material_breakdown_pie_chart, material_borough_subplots

class MaterialBreakdownBlock:
    """
    Interactive GUI block for visualizing the breakdown of Sidewalk materials
    across fetched datasets using Plotly Donut charts and subplots.
    """
    def __init__(self, workspace_state):
        self.state = workspace_state

    def render(self):
        """Renders the Material Breakdown block and controls."""
        with ui.card().classes('w-full border border-gray-200 shadow-sm'):
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label('📊 SDM Material Breakdown').classes('text-xl font-bold text-gray-800 dark:text-gray-200')
                
            with ui.row().classes('w-full items-end gap-4 mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded'):
                dataset_options = list(self.state.datasets.keys()) if self.state.datasets else []
                
                self.ds_select = ui.select(
                    dataset_options, 
                    label='1. Select Dataset', 
                    on_change=self.update_column_options
                ).classes('w-48')
                
                self.mat_select = ui.select([], label='2. Material Column').classes('w-40')
                self.boro_select = ui.select([], label='3. Borough Column (Opt)').classes('w-40')
                
                self.split_toggle = ui.switch('Split by Borough').classes('mt-4')
                
                ui.button('Generate Breakdown', on_click=self.plot_chart, icon='donut_large').classes('bg-purple-600 text-white ml-auto')

            self.chart_container = ui.column().classes('w-full items-center')

    def update_column_options(self):
        """Auto-populate and guess the relevant columns when a dataset is chosen."""
        if not self.ds_select.value:
            return
            
        df = self.state.datasets[self.ds_select.value]
        columns = df.columns.tolist()
        
        self.mat_select.options = columns
        self.boro_select.options = columns
        
        # Auto-guess columns to save the user time
        guess_mat = next((c for c in columns if c.lower() in ['material', 'material_type', 'surface', 'surface_type']), None)
        guess_boro = next((c for c in columns if c.lower() in ['borough', 'boro', 'county']), None)
        
        if guess_mat: self.mat_select.value = guess_mat
        if guess_boro: self.boro_select.value = guess_boro
        
        self.mat_select.update()
        self.boro_select.update()

    def plot_chart(self):
        """Renders the Plotly chart into the NiceGUI container."""
        if not self.ds_select.value or not self.mat_select.value:
            ui.notify('Please select a dataset and a material column.', type='warning')
            return
            
        df = self.state.datasets[self.ds_select.value]
        mat_col = self.mat_select.value
        boro_col = self.boro_select.value
        
        self.chart_container.clear()
        with self.chart_container:
            # Display Subplots if toggled and Borough column is available
            if self.split_toggle.value and boro_col and boro_col in df.columns:
                fig = material_borough_subplots(df, material_col=mat_col, borough_col=boro_col, title=f"Materials by Borough ({self.ds_select.value})")
            else:
                fig = material_breakdown_pie_chart(df, material_col=mat_col, title=f"Overall Material Composition ({self.ds_select.value})")
                
            ui.plotly(fig).classes('w-full h-[500px]')