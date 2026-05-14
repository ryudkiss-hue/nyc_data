import os
import asyncio
import pandas as pd
from nicegui import ui

from socrata_toolkit.analysis import parse_sim_complaints
from socrata_toolkit.ai import triage_complaints, triage_complaints_gemini, LegalPolicyEngine

class AITriageBlock:
    """
    Interactive GUI block to let users classify text columns 
    by routing them through either a Local LLM or Google Gemini.
    """
    def __init__(self, workspace_state):
        self.state = workspace_state

    def render(self):
        with ui.card().classes('w-full border border-gray-200 shadow-sm'):
            ui.label('🤖 AI Data Triage & Classification').classes('text-xl font-bold text-gray-800 dark:text-gray-200 mb-4')
            
            with ui.row().classes('w-full gap-4 items-start'):
                # Left column: Controls
                with ui.column().classes('w-1/3 bg-gray-50 dark:bg-gray-800 p-4 rounded shadow-inner'):
                    dataset_options = list(self.state.datasets.keys()) if self.state.datasets else []
                    self.ds_select = ui.select(dataset_options, label='1. Select Dataset', on_change=self.update_columns).classes('w-full')
                    self.text_col_select = ui.select([], label='2. Text Column (e.g., description)').classes('w-full')
                    
                    ui.separator().classes('my-4')
                    ui.label('AI Model Routing').classes('font-bold')
                    
                    self.model_toggle = ui.toggle(
                        options={
                            'stat': 'Quantitative Stats (No LLM)',
                            'local': 'Local LLM (OpenClaw/Ollama)', 
                            'gemini': 'Google Gemini API',
                            'legal': 'Legal Policy Engine'
                        },
                        value='local'
                    ).classes('w-full text-xs')
                    
                    self.local_url_input = ui.input('Local API URL', value='http://localhost:8000/v1/chat/completions').classes('w-full')
                    # Auto-populate the key if it exists in the environment (e.g. from Vault)
                    self.gemini_key_input = ui.input('Gemini API Key', value=os.getenv('GEMINI_API_KEY', ''), password=True, password_toggle_button=True).classes('w-full')
                    
                    # Dynamically show/hide inputs based on toggle using NiceGUI bindings
                    self.local_url_input.bind_visibility_from(self.model_toggle, 'value', backward=lambda v: v == 'local')
                    self.gemini_key_input.bind_visibility_from(self.model_toggle, 'value', backward=lambda v: v == 'gemini')
                    
                    ui.button('Run AI Triage', on_click=self.run_triage, icon='auto_awesome').classes('w-full bg-purple-600 text-white mt-4')
                
                # Right column: Results
                with ui.column().classes('w-3/5 flex-grow'):
                    self.results_container = ui.column().classes('w-full')
                    with self.results_container:
                        ui.label('Select a dataset and run triage to view AI classifications.').classes('italic text-gray-500')

    def update_columns(self):
        if not self.ds_select.value:
            return
        cols = self.state.datasets[self.ds_select.value].columns.tolist()
        self.text_col_select.options = cols
        
        # Auto-guess the text column to save the user time
        guess = next((c for c in cols if c.lower() in ['description', 'descriptor', 'text', 'complaint_details', 'resolution_description']), None)
        if guess:
            self.text_col_select.value = guess
        self.text_col_select.update()

    async def run_triage(self):
        if not self.ds_select.value or not self.text_col_select.value:
            ui.notify('Please select a dataset and a text column.', type='warning')
            return
            
        df = self.state.datasets[self.ds_select.value]
        # Limit to 50 rows for safety and speed during UI interaction
        process_df = df.head(50).copy()
        
        self.results_container.clear()
        with self.results_container:
            ui.spinner('dots', size='lg', color='purple')
            ui.label(f'Sending {len(process_df)} records to {self.model_toggle.value.upper()} model...').classes('italic text-gray-500')
            
        try:
            # 1. Run the heavy AI network call in a background thread to prevent UI freezing
            if self.model_toggle.value == 'stat':
                # Fast quantitative statistical parsing (Zipf's law, regex taxonomies)
                parsed_df = await asyncio.to_thread(parse_sim_complaints, process_df, self.text_col_select.value)
                # Map back to expected structure for the UI
                result_df = process_df.copy()
                result_df['_priority'] = parsed_df['_sim_category'].str.replace('_', ' ').str.title()
                result_df['_sim_keywords'] = parsed_df['_sim_unique_keywords'].apply(lambda x: ", ".join(x))
                result_df['_sim_severity'] = parsed_df['_sim_severity_score']
                
            elif self.model_toggle.value == 'local':
                url = self.local_url_input.value
                result_df = await asyncio.to_thread(triage_complaints, process_df, self.text_col_select.value, url)
            else:
                api_key = self.gemini_key_input.value
                if not api_key:
                    ui.notify('Please provide a Gemini API Key.', type='negative')
                    self.results_container.clear()
                    return
                result_df = await asyncio.to_thread(triage_complaints_gemini, process_df, self.text_col_select.value, 'gemini-1.5-flash', api_key)
            elif self.model_toggle.value == 'legal':
                engine = LegalPolicyEngine()
                memos = [engine.generate_compliance_memo(str(text)) for text in process_df[self.text_col_select.value]]
                result_df = process_df.copy()
                result_df['_priority'] = 'POLICY CHECKED'
                result_df['_compliance_memo'] = memos
            
            # 2. Update UI with the triaged results
            self.results_container.clear()
            with self.results_container:
                ui.label('✅ Triage Complete!').classes('text-green-600 font-bold text-lg')
                
                counts = result_df['_priority'].value_counts().to_dict()
                with ui.row().classes('gap-4 mb-4'):
                    for priority, count in counts.items():
                        color = 'red' if priority == 'CRITICAL' else 'orange' if priority == 'HIGH' else 'blue' if priority == 'MEDIUM' else 'gray'
                        ui.badge(f"{priority}: {count}", color=color).classes('text-sm')
                
                cols_to_show = [self.text_col_select.value, '_priority']
                col_defs = [
                    {'field': self.text_col_select.value, 'headerName': 'Original Text', 'flex': 1},
                    {'field': '_priority', 'headerName': 'Category / Severity', 'width': 200}
                ]
                
                # If we used the statistical parser, inject our extra data columns into the UI table!
                if '_sim_keywords' in result_df.columns:
                    cols_to_show.extend(['_sim_severity', '_sim_keywords'])
                    col_defs.append({'field': '_sim_severity', 'headerName': 'Stat Score', 'width': 120})
                    col_defs.append({'field': '_sim_keywords', 'headerName': 'Anomalous Terms', 'width': 180})
                    
                # If we used the Legal Policy Engine, show the memo column!
                if '_compliance_memo' in result_df.columns:
                    cols_to_show.append('_compliance_memo')
                    col_defs.append({'field': '_compliance_memo', 'headerName': 'Legal Compliance Memo', 'flex': 2, 'wrapText': True, 'autoHeight': True})

                display_data = result_df[cols_to_show].to_dict('records')
                ui.aggrid({'columnDefs': col_defs, 'rowData': display_data}).classes('w-full h-96')
                
        except Exception as e:
            self.results_container.clear()
            with self.results_container:
                ui.label(f'❌ Triage Failed: {str(e)}').classes('text-red-600 font-bold')
