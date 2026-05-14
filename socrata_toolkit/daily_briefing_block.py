import asyncio
from datetime import datetime
from pathlib import Path
from nicegui import ui
import pandas as pd

from socrata_toolkit.analysis import (
    compute_sla_metrics, 
    gauge_chart, 
    triage_funnel_chart,
    InsightsEngine,
    generate_executive_briefing_automated
)
from socrata_toolkit.engineering import compute_material_aware_kpis

class DailyBriefingBlock:
    """
    Generates a highly modular, executive-style intelligence report 
    synthesizing current datasets into actionable KPIs and text insights.
    """
    def __init__(self, workspace_state):
        self.state = workspace_state

    def render(self):
        with ui.card().classes('w-full border-t-4 border-blue-600 shadow-lg'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.column().classes('gap-0'):
                    ui.label('📰 Morning Executive Briefing').classes('text-2xl font-bold text-gray-800 dark:text-gray-200')
                    ui.label(f'Generated: {datetime.now().strftime("%A, %B %d, %Y - %H:%M")}').classes('text-sm text-gray-500')
                
                with ui.row().classes('gap-2'):
                    ui.button('Export to Desktop', icon='download', on_click=self.export_to_desktop).classes('bg-green-600 text-white shadow-md')
                    ui.button('Compile Report', icon='auto_awesome', on_click=self.generate_briefing).classes('bg-blue-600 text-white shadow-md')
            
            self.report_container = ui.column().classes('w-full gap-6')
            
            # Initial empty state
            with self.report_container:
                ui.label('Click "Compile Report" to analyze the current workspace state.').classes('italic text-gray-500')

    async def export_to_desktop(self):
        """Generates an executive briefing report and saves it directly to the user's OS desktop."""
        if not self.state.datasets:
            ui.notify('No datasets loaded. Please fetch data first.', type='warning')
            return
            
        target_ds_name = 'defects' if 'defects' in self.state.datasets else list(self.state.datasets.keys())[0]
        df = self.state.datasets[target_ds_name]
        
        report = generate_executive_briefing_automated(df)
        
        desktop_dir = Path.home() / "Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"NYC_DOT_Briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = desktop_dir / filename
        report.save(str(filepath))
        ui.notify(f'✅ Saved executive briefing to: {filepath}', type='positive', timeout=5000)

    async def generate_briefing(self):
        """Asynchronously orchestrates data across multiple analysis engines."""
        self.report_container.clear()
        
        if not self.state.datasets:
            with self.report_container:
                ui.notify('No datasets loaded. Please fetch data first.', type='warning')
                ui.label('⚠️ Action Required: Load a dataset (e.g., 311 complaints or repairs) to generate a briefing.').classes('text-red-500 font-semibold')
            return

        with self.report_container:
            ui.spinner('dots', size='lg', color='blue')
            ui.label("Running AI Insights & KPI Engines...").classes('italic text-gray-500 mb-4')
            
        # Assume we run analysis on the first available dataset (or a specific 'defects' dataset if present)
        target_ds_name = 'defects' if 'defects' in self.state.datasets else list(self.state.datasets.keys())[0]
        df = self.state.datasets[target_ds_name]

        # Offload heavy computations
        await asyncio.sleep(0.5) # Simulate processing for UI flow
        
        # 1. Natural Language Insights
        engine = InsightsEngine(df)
        text_insights = engine.generate()
        
        # 2. SLA & Operations Data
        sla_metrics = compute_sla_metrics(df, start_col='created_date', end_col='closed_date')
        
        # Clear spinner and draw the board
        self.report_container.clear()
        with self.report_container:
            
            # Section: Top-Line KPI Cards
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-grow bg-blue-50 dark:bg-blue-900/20 items-center p-4'):
                    ui.label('Total Records').classes('text-sm font-semibold uppercase text-gray-500')
                    ui.label(f'{len(df):,}').classes('text-4xl font-bold text-blue-600')
                
                with ui.card().classes('flex-grow bg-green-50 dark:bg-green-900/20 items-center p-4'):
                    ui.label('SLA Compliance Rate').classes('text-sm font-semibold uppercase text-gray-500')
                    ui.label(f'{sla_metrics.sla_compliance_rate}%').classes('text-4xl font-bold text-green-600')

                with ui.card().classes('flex-grow bg-red-50 dark:bg-red-900/20 items-center p-4'):
                    ui.label('SLA Violations').classes('text-sm font-semibold uppercase text-gray-500')
                    ui.label(f'{sla_metrics.violation_count:,}').classes('text-4xl font-bold text-red-600')

            # Section: Insights & Visuals
            with ui.row().classes('w-full gap-6 mt-4'):
                # Left: AI Insights
                with ui.column().classes('w-1/3 bg-gray-50 dark:bg-gray-800 p-4 rounded shadow-inner'):
                    ui.label('🧠 Automated Insights').classes('text-lg font-bold mb-2')
                    for insight in text_insights:
                        ui.label(f"• {insight}").classes('mb-2 text-md text-gray-700 dark:text-gray-300')

                # Right: Gauge Chart
                with ui.column().classes('flex-grow items-center'):
                    fig = gauge_chart(sla_metrics.sla_compliance_rate, target=95.0, title="Operations Health vs Target")
                    ui.plotly(fig).classes('w-full h-[300px]')
