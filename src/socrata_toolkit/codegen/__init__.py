"""Code generation framework for config-driven dataset integration.

This module provides automated code generation from DATASET_REGISTRY.yaml:
- chart_generator: Generates plotly_charts.py functions
- callback_generator: Generates visualization_callbacks.py
- layout_generator: Generates dashboard layout sections
- kpi_generator: Generates KPI calculation stubs
- docs_generator: Regenerates markdown documentation

Usage:
    from socrata_toolkit.codegen import CodegenFramework

    codegen = CodegenFramework("docs/DATASET_REGISTRY.yaml")
    codegen.generate_all()  # Generates all 5 artifact types

    # Or generate selectively:
    codegen.generate_charts()
    codegen.generate_callbacks()
    codegen.generate_layout()
    codegen.generate_kpis()
    codegen.generate_docs()
"""

from __future__ import annotations

from .callback_generator import CallbackGenerator
from .chart_generator import ChartGenerator
from .docs_generator import DocsGenerator
from .kpi_generator import KPIGenerator
from .layout_generator import LayoutGenerator
from .registry_loader import RegistryLoader

__all__ = [
    "CodegenFramework",
    "ChartGenerator",
    "CallbackGenerator",
    "LayoutGenerator",
    "KPIGenerator",
    "DocsGenerator",
    "RegistryLoader",
]


class CodegenFramework:
    """Main orchestrator for config-driven code generation.

    Loads DATASET_REGISTRY.yaml and generates all integration artifacts
    in a single coordinated workflow.
    """

    def __init__(self, registry_path: str):
        """Initialize code generation framework.

        Args:
            registry_path: Path to DATASET_REGISTRY.yaml
        """
        self.registry_path = registry_path
        self.loader = RegistryLoader(registry_path)
        self.registry = self.loader.load()

        self.chart_gen = ChartGenerator(self.registry)
        self.callback_gen = CallbackGenerator(self.registry)
        self.layout_gen = LayoutGenerator(self.registry)
        self.kpi_gen = KPIGenerator(self.registry)
        self.docs_gen = DocsGenerator(self.registry)

    def generate_all(self) -> dict[str, str]:
        """Generate all artifacts from registry.

        Returns:
            dict mapping artifact type to output path
        """
        results = {}
        results["charts"] = self.generate_charts()
        results["callbacks"] = self.generate_callbacks()
        results["layout"] = self.generate_layout()
        results["kpis"] = self.generate_kpis()
        results["docs"] = self.generate_docs()
        return results

    def generate_charts(self) -> str:
        """Generate plotly_charts.py from registry.

        Returns:
            Path to generated file
        """
        return self.chart_gen.generate()

    def generate_callbacks(self) -> str:
        """Generate visualization_callbacks.py from registry.

        Returns:
            Path to generated file
        """
        return self.callback_gen.generate()

    def generate_layout(self) -> str:
        """Generate dashboard layout sections from registry.

        Returns:
            Path to generated file
        """
        return self.layout_gen.generate()

    def generate_kpis(self) -> str:
        """Generate KPI calculation stubs from registry.

        Returns:
            Path to generated file
        """
        return self.kpi_gen.generate()

    def generate_docs(self) -> str:
        """Regenerate markdown documentation from registry.

        Returns:
            Path to generated file
        """
        return self.docs_gen.generate()
