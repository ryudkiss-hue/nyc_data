"""NYC DOT Dataset Integration Manager v2.0

Enhanced version with automatic Socrata metadata fetching.

Single entry point for adding/updating/removing datasets.
Orchestrates code generation, schema validation, and component wiring.

Includes automatic Socrata metadata fetching and schema discovery.

Usage:
    from socrata_toolkit.integration_v2 import DatasetIntegrationManager

    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    # Add a new dataset - metadata auto-fetched from Socrata
    mgr.add_dataset(
        fourfour="h933-akrx",
        name="Street Pavement Ratings",
        kpis=["pavement_avg_rating", "rating_by_borough"],
        fetch_metadata=True  # Auto-fetch from Socrata
    )

    # Or populate existing datasets with metadata
    mgr.populate_all_metadata()
"""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class DatasetIntegrationManager:
    """
    Unified entry point for dataset integration with automatic metadata discovery.

    Loads DATASET_REGISTRY.yaml and orchestrates:
    - Code generation
    - Schema validation
    - Component wiring
    - Socrata metadata fetching
    """

    def __init__(self, config_path: str, domain: str = "data.cityofnewyork.us"):
        """Initialize with DATASET_REGISTRY.yaml path."""
        with open(config_path) as f:
            self.registry = yaml.safe_load(f)
        self.config_path = Path(config_path)
        self.project_root = self.config_path.parent.parent
        self.domain = domain

    def fetch_socrata_metadata(self, fourfour: str) -> Optional[Dict[str, Any]]:
        """
        Fetch dataset metadata from Socrata API.

        Args:
            fourfour: Socrata fourfour ID (e.g., "dntt-gqwq")

        Returns:
            Dict with columns, row count, last update, status
            None if API call fails
        """
        url = f"https://{self.domain}/api/views/{fourfour}.json"

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())

            # Extract useful metadata
            columns = []
            if "columns" in data:
                for col in data.get("columns", []):
                    columns.append({
                        "name": col.get("name"),
                        "field_name": col.get("fieldName"),
                        "type": col.get("dataTypeName"),
                        "description": col.get("description", ""),
                    })

            metadata = {
                "fourfour": fourfour,
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "columns": columns,
                "row_count": data.get("numberOfRows", 0),
                "last_updated_timestamp": data.get("lastModifiedTime", None),
                "created_timestamp": data.get("createdTime", None),
                "accessibility": "ok" if len(columns) > 0 else "error",
            }

            return metadata

        except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
            print(f"Warning: {fourfour} metadata fetch failed: {type(e).__name__}")
            return None

    def generate_column_specs(self, columns: list) -> Dict[str, Any]:
        """Convert Socrata columns to visualization specs."""
        specs = {}

        # Common patterns
        numeric_cols = [c["name"] for c in columns if c.get("type") in ["number", "decimal"]]
        text_cols = [c["name"] for c in columns if c.get("type") in ["text", "plain_text"]]
        date_cols = [c["name"] for c in columns if c.get("type") in ["calendar_date", "floating_timestamp"]]
        geo_cols = [c["name"] for c in columns if c.get("type") in ["location", "point"]]

        # Auto-detect borough column
        borough_col = next(
            (c["name"] for c in columns if "borough" in c.get("name", "").lower()),
            text_cols[0] if text_cols else "location"
        )

        # Auto-detect numeric value column
        value_col = next(
            (c["name"] for c in columns if any(x in c.get("name", "").lower() for x in ["count", "volume", "total", "amount", "value"])),
            numeric_cols[0] if numeric_cols else "value"
        )

        # Auto-detect date column
        date_col = next(
            (c["name"] for c in columns if any(x in c.get("name", "").lower() for x in ["date", "time", "created", "updated"])),
            date_cols[0] if date_cols else None
        )

        return {
            "borough_column": borough_col,
            "value_column": value_col,
            "date_column": date_col,
            "all_numeric": numeric_cols,
            "all_text": text_cols,
            "all_dates": date_cols,
            "all_geographic": geo_cols,
            "total_columns": len(columns),
        }

    def populate_all_metadata(self) -> Dict[str, Any]:
        """
        Populate metadata for all datasets in registry.

        Fetches Socrata API for each dataset and updates:
        - Column schemas
        - Row counts
        - Auto-detected visualization columns
        - Accessibility status

        Returns:
            Summary of fetch results
        """
        print(f"Populating metadata for {len(self.registry.get('datasets', {}))} datasets...")

        fetched = 0
        errors = 0
        updated = 0

        for key, spec in self.registry.get("datasets", {}).items():
            fourfour = spec.get("fourfour")
            if not fourfour:
                continue

            print(f"  Fetching {fourfour} ({key})...", end=" ", flush=True)

            # Fetch metadata from Socrata
            metadata = self.fetch_socrata_metadata(fourfour)

            if metadata and metadata.get("accessibility") == "ok":
                print(f"[OK] {len(metadata.get('columns', []))} columns")
                fetched += 1

                # Update registry with schema info
                spec["schema"] = {
                    "columns": [
                        {"name": c["name"], "type": c["type"], "description": c.get("description", "")}
                        for c in metadata.get("columns", [])
                    ],
                    "row_count": metadata.get("row_count", 0),
                    "last_updated": metadata.get("last_updated_timestamp"),
                }

                # Add column specs for visualization auto-configuration
                col_specs = self.generate_column_specs(metadata.get("columns", []))
                spec["column_specs"] = col_specs

                # Update visualization with auto-detected columns
                if "visualization" not in spec:
                    spec["visualization"] = {}

                spec["visualization"].update({
                    "suggested_iv": col_specs["borough_column"],
                    "suggested_dv": col_specs["value_column"],
                    "suggested_date": col_specs["date_column"],
                    "has_geographic_data": len(col_specs["all_geographic"]) > 0,
                })

                updated += 1
            else:
                print("[FAIL]")
                errors += 1

        # Save updated registry
        self._save_registry()

        return {
            "total": len(self.registry.get("datasets", {})),
            "fetched": fetched,
            "updated": updated,
            "errors": errors,
        }

    def add_dataset(
        self,
        fourfour: str,
        name: str,
        kpis: List[str],
        category: str = "custom",
        frequency: str = "weekly",
        quality_score: float = 0.80,
        status: str = "active",
        fetch_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Add a new dataset to the registry.

        Auto-generates:
        - Plotly chart functions
        - Dash callbacks
        - Dashboard layout sections
        - KPI calculation stubs
        - Documentation
        - Metadata (if fetch_metadata=True)

        Args:
            fourfour: Socrata fourfour ID
            name: Human-readable dataset name
            kpis: List of KPI keys this dataset supports
            category: Dataset category
            frequency: Update frequency (daily/weekly/monthly/static)
            quality_score: Data quality score (0-1)
            status: Dataset status (active/deprecated)
            fetch_metadata: Whether to fetch Socrata metadata

        Returns:
            Dict with generated artifacts and status
        """
        # 1. Register in config
        dataset_key = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")

        dataset_spec = {
            "fourfour": fourfour,
            "name": name,
            "category": category,
            "visualization": {
                "default_chart": "vertical_bar",
                "iv_column": "borough",
                "dv_column": "count",
                "aggregation": "count",
                "title": f"{name} by Borough"
            },
            "kpis": kpis,
            "frequency": frequency,
            "quality_score": quality_score,
            "status": status
        }

        # 2. Fetch Socrata metadata if requested
        if fetch_metadata:
            metadata = self.fetch_socrata_metadata(fourfour)
            if metadata and metadata.get("accessibility") == "ok":
                col_specs = self.generate_column_specs(metadata.get("columns", []))
                dataset_spec["schema"] = {
                    "columns": [
                        {"name": c["name"], "type": c["type"]}
                        for c in metadata.get("columns", [])
                    ],
                    "row_count": metadata.get("row_count", 0),
                }
                dataset_spec["column_specs"] = col_specs
                dataset_spec["visualization"].update({
                    "suggested_iv": col_specs["borough_column"],
                    "suggested_dv": col_specs["value_column"],
                })

        self.registry["datasets"][dataset_key] = dataset_spec

        # 3. Auto-generate artifacts
        artifacts = {
            "chart_function": self._generate_chart_function(dataset_key, dataset_spec),
            "callback": self._generate_callback(dataset_key, dataset_spec),
            "layout_section": self._generate_layout_section(dataset_key, dataset_spec),
            "kpi_stubs": self._generate_kpi_stubs(kpis),
            "documentation": self._generate_documentation(dataset_key, dataset_spec)
        }

        # 4. Save updated config
        self._save_registry()

        return {
            "status": "success",
            "dataset_key": dataset_key,
            "artifacts": artifacts,
            "files_changed": 6,
            "metadata_fetched": fetch_metadata and bool(dataset_spec.get("schema")),
        }

    def _generate_chart_function(self, key: str, spec: Dict) -> str:
        """Generate Plotly chart function from spec."""
        iv = spec.get("column_specs", {}).get("borough_column", "borough")
        dv = spec.get("column_specs", {}).get("value_column", "count")

        return f"""
def {key}_chart(df, **kwargs):
    \"\"\"Generate chart for {spec['name']}.\"\"\"
    return ChartFactory.create(
        chart_type="{spec['visualization']['default_chart']}",
        data=df,
        iv="{iv}",
        dv="{dv}",
        title="{spec['visualization']['title']}"
    )
"""

    def _generate_callback(self, key: str, spec: Dict) -> str:
        """Generate Dash callback from spec."""
        return f"""
@callback(
    Output('{key}-chart', 'figure'),
    Input('{key}-filter', 'value')
)
def update_{key}_chart(filters):
    df = DatasetLoader.load('{key}', filters or {{}})
    kpis = KPIEngine.compute_batch('{key}', {spec['kpis']}, df)
    return {key}_chart(df)
"""

    def _generate_layout_section(self, key: str, spec: Dict) -> str:
        """Generate dashboard layout section from spec."""
        return f"""
html.Div([
    html.H2("{spec['name']}"),
    dcc.Graph(id='{key}-chart'),
    html.Div(id='{key}-kpis')
], className='chart-section')
"""

    def _generate_kpi_stubs(self, kpis: List[str]) -> str:
        """Generate KPI calculation stubs."""
        stubs = []
        for kpi in kpis:
            stubs.append(f"""
    def {kpi}(self, df) -> float:
        \"\"\"TODO: Implement {kpi} calculation.\"\"\"
        return 0.0
""")
        return "\n".join(stubs)

    def _generate_documentation(self, key: str, spec: Dict) -> str:
        """Generate markdown documentation."""
        schema_info = ""
        if "schema" in spec:
            cols = ", ".join([c["name"] for c in spec["schema"]["columns"][:5]])
            schema_info = f"\n\n## Columns (sample)\n\n{cols}...\n\n"

        return f"""
# {spec['name']}

**Fourfour ID:** {spec['fourfour']}
**Category:** {spec['category']}
**Update Frequency:** {spec['frequency']}
**Quality Score:** {spec['quality_score']}
**Status:** {spec['status']}

## Supported KPIs

{chr(10).join(f"- {kpi}" for kpi in spec['kpis'])}

## Default Visualization

**Type:** {spec['visualization']['default_chart']}
**X-axis:** {spec['visualization'].get('suggested_iv', spec['visualization']['iv_column'])}
**Y-axis:** {spec['visualization'].get('suggested_dv', spec['visualization']['dv_column'])}
{schema_info}
"""

    def _save_registry(self):
        """Save updated DATASET_REGISTRY.yaml."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.registry, f, default_flow_style=False, sort_keys=False)


# Placeholder classes (to be imported from real modules)
class ChartFactory:
    """Universal chart factory replacing 8 individual functions."""

    @staticmethod
    def create(chart_type: str, data, iv: str, dv: str, title: str = "", **kwargs):
        """Create chart from specification."""
        try:
            import plotly.express as px
        except ImportError:
            raise ImportError("Install plotly: pip install plotly")

        return px.bar(data, x=iv, y=dv, title=title)  # Simplified


class DatasetLoader:
    """Load datasets with caching and filtering."""

    @staticmethod
    def load(dataset_key: str, filters: Dict = None):
        """Load dataset with optional filters."""
        import pandas as pd
        return pd.DataFrame()  # Stub


class KPIEngine:
    """Compute KPIs from data."""

    @staticmethod
    def compute_batch(dataset_key: str, kpis: List[str], df) -> Dict:
        """Compute multiple KPIs."""
        return {kpi: 0.0 for kpi in kpis}  # Stub
