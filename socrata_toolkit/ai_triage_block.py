import asyncio
import os

from nicegui import ui

from .ai import LegalPolicyEngine, triage_complaints, triage_complaints_gemini  # type: ignore
from .analysis import parse_sim_complaints


class AITriageBlock:
    """
    Interactive GUI block to let users classify text columns
    by routing them through either a Local LLM or Google Gemini.
    """

    def __init__(self, workspace_state):
        self.state = workspace_state
        self.ds_select = None
        self.text_col_select = None
        self.model_toggle = None
        self.local_url_input = None
        self.row_count_input = None
        self.gemini_key_input = None
        self.results_container = None

    def render(self):
        with ui.card().classes("w-full border border-gray-200 shadow-sm"):
            ui.label("🤖 AI Data Triage & Classification").classes(
                "text-xl font-bold text-gray-800 dark:text-gray-200 mb-4"
            )

            with ui.row().classes("w-full gap-4 items-start"):
                # Left column: Controls
                with ui.column().classes(
                    "w-1/3 bg-gray-50 dark:bg-gray-800 p-4 rounded shadow-inner"  # noqa: F841
                ):  # noqa: F841
                    dataset_options = (
                        list(self.state.datasets.keys()) if self.state.datasets else []
                    )
                    self.ds_select = ui.select(
                        dataset_options, label="1. Select Dataset", on_change=self.update_columns
                    ).classes("w-full")
                    self.text_col_select = ui.select(
                        [], label="2. Text Column (e.g., description)"
                    ).classes("w-full")
                    self.row_count_input = ui.number(
                        label="3. Rows to Process", value=50, min=1, max=500, step=1
                    ).classes("w-full")

                    ui.separator().classes("my-4")
                    ui.label("AI Model Routing").classes("font-bold")

                    self.model_toggle = ui.toggle(
                        options={
                            "stat": "Quantitative Stats (No LLM)",
                            "local": "Local LLM (OpenClaw/Ollama)",
                            "gemini": "Google Gemini API",
                            "legal": "Legal Policy Engine",
                        },
                        value="local",
                    ).classes("w-full text-xs")

                    self.local_url_input = ui.input(
                        "Local API URL", value="http://localhost:8000/v1/chat/completions"
                    ).classes("w-full")
                    # Auto-populate the key if it exists in the environment (e.g. from Vault)
                    self.gemini_key_input = ui.input(
                        "Gemini API Key",
                        value=os.getenv("GEMINI_API_KEY", ""),
                        password=True,
                        password_toggle_button=True,
                    ).classes("w-full")

                    # Dynamically show/hide inputs based on toggle using NiceGUI bindings
                    self.local_url_input.bind_visibility_from(
                        self.model_toggle, "value", backward=lambda v: v == "local"
                    )
                    self.gemini_key_input.bind_visibility_from(
                        self.model_toggle, "value", backward=lambda v: v == "gemini"
                    )

                    ui.button(
                        "Run AI Triage", on_click=self.run_triage, icon="auto_awesome"
                    ).classes("w-full bg-purple-600 text-white mt-4")

                # Right column: Results
                with ui.column().classes("w-3/5 flex-grow"):
                    self.results_container = ui.column().classes("w-full")
                    with self.results_container:
                        ui.label(
                            "Select a dataset and run triage to view AI classifications."
                        ).classes("italic text-gray-500")

    def update_columns(self) -> None:
        if not self.ds_select or not self.ds_select.value:
            return
        ds_name = str(self.ds_select.value)
        if ds_name not in self.state.datasets:
            return
        cols = self.state.datasets[ds_name].columns.tolist()
        if self.text_col_select:
            self.text_col_select.options = cols

            # Auto-guess the text column to save the user time
            guess = next(
                (
                    c
                    for c in cols
                    if c.lower()
                    in [
                        "description",
                        "descriptor",
                        "text",
                        "complaint_details",
                        "resolution_description",
                    ]
                ),
                None,
            )
            if guess:
                self.text_col_select.value = guess
            self.text_col_select.update()

    # --- Model Runner Methods ---

    async def _run_stat_model(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        """Run the fast quantitative statistical parsing model."""
        parsed_df = await asyncio.to_thread(parse_sim_complaints, df, text_col)
        priority_map = {
            "critical_accessibility_hazard": "CRITICAL",
            "trip_hazard": "HIGH",
            "ada_accessibility": "HIGH",
            "root_damage": "MEDIUM",
            "surface_damage": "MEDIUM",
            "water_pooling": "LOW",
            "general_maintenance": "LOW",
            "unknown": "INFO",
        }
        result_df = df.copy()
        result_df["_priority"] = parsed_df["_sim_category"].map(priority_map).fillna("INFO")
        result_df["_sim_keywords"] = parsed_df["_sim_unique_keywords"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else ""
        )
        result_df["_sim_severity"] = parsed_df["_sim_severity_score"]
        return result_df

    async def _run_local_model(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        """Run the local LLM triage model."""
        url = str(self.local_url_input.value) if self.local_url_input else ""
        return await asyncio.to_thread(triage_complaints, df, text_col, url)

    async def _run_gemini_model(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        """Run the Google Gemini triage model."""
        api_key = str(self.gemini_key_input.value) if self.gemini_key_input else ""
        if not api_key:
            ui.notify("Please provide a Gemini API Key.", type="negative")
            raise ValueError("Missing Gemini API Key")

        return await asyncio.to_thread(
            triage_complaints_gemini,
            df,
            text_col,
            "gemini-1.5-flash",
            api_key,
        )

    async def _run_legal_model(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        """Run the Legal Policy Engine model."""
        engine = LegalPolicyEngine()

        # This can be slow, so run it in a thread to avoid blocking the UI
        def _generate_memos():
            return [engine.generate_compliance_memo(str(text)) for text in df[text_col]]

        memos = await asyncio.to_thread(_generate_memos)

        result_df = df.copy()
        result_df["_priority"] = "POLICY CHECKED"
        result_df["_compliance_memo"] = memos
        return result_df

    # --- UI Rendering Methods ---

    def _render_results_grid(self, result_df: pd.DataFrame, text_col: str) -> None:
        """Render the final AG-Grid with triaged data."""
        cols_to_show = [text_col, "_priority"]
        col_defs = [
            {"field": text_col, "headerName": "Original Text", "flex": 1},
            {"field": "_priority", "headerName": "Category / Severity", "width": 200},
        ]

        # Dynamically add columns based on which model was run
        if "_sim_keywords" in result_df.columns:
            cols_to_show.extend(["_sim_severity", "_sim_keywords"])
            col_defs.extend(
                [
                    {"field": "_sim_severity", "headerName": "Stat Score", "width": 120},
                    {"field": "_sim_keywords", "headerName": "Anomalous Terms", "width": 180},
                ]
            )

        if "_compliance_memo" in result_df.columns:
            cols_to_show.append("_compliance_memo")
            col_defs.append(
                {
                    "field": "_compliance_memo",
                    "headerName": "Legal Compliance Memo",
                    "flex": 2,
                    "wrapText": True,
                    "autoHeight": True,
                }
            )

        display_data = result_df[cols_to_show].to_dict("records")
        ui.aggrid({"columnDefs": col_defs, "rowData": display_data}).classes("w-full h-96")

    # --- Main Event Handler ---

    async def run_triage(self) -> None:
        if (
            not self.ds_select
            or not self.text_col_select
            or not self.model_toggle
            or not self.row_count_input
            or not self.results_container
        ):
            return

        if not self.ds_select.value or not self.text_col_select.value:
            ui.notify("Please select a dataset and a text column.", type="warning")
            return

        ds_name = str(self.ds_select.value)
        text_col = str(self.text_col_select.value)
        model_type = str(self.model_toggle.value)

        row_count = int(self.row_count_input.value)
        process_df = self.state.datasets[ds_name].head(row_count).copy()

        self.results_container.clear()
        with self.results_container:  # noqa: F841
            with ui.row().classes("items-center gap-2"):
                ui.spinner("dots", size="lg", color="purple")
                ui.label(
                    f"Sending {len(process_df)} records to {model_type.upper()} model..."
                ).classes("italic text-gray-500")

        try:
            model_runners = {
                "stat": self._run_stat_model,
                "local": self._run_local_model,
                "gemini": self._run_gemini_model,
                "legal": self._run_legal_model,
            }
            runner = model_runners.get(model_type)
            if not runner:
                raise ValueError(f"Unknown model type: {model_type}")

            result_df = await runner(process_df, text_col)

            # 2. Update UI with the triaged results
            self.results_container.clear()
            with self.results_container:  # noqa: F841
                ui.label("✅ Triage Complete!").classes("text-green-600 font-bold text-lg")

                if "_priority" in result_df.columns:
                    counts = result_df["_priority"].value_counts().to_dict()
                    with ui.row().classes("gap-4 mb-4"):
                        for priority, count in counts.items():
                            color = (
                                "red"
                                if priority == "CRITICAL"
                                else (
                                    "orange"
                                    if priority == "HIGH"
                                    else "blue" if priority == "MEDIUM" else "gray"
                                )
                            )
                            ui.badge(f"{priority}: {count}", color=color).classes("text-sm")

                self._render_results_grid(result_df, text_col)

        except Exception as e:
            if self.results_container:
                self.results_container.clear()
                with self.results_container:
                    ui.label(f"❌ Triage Failed: {str(e)}").classes(
                        "text-red-600 font-bold"
                    )
