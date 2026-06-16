"""Reusable statistics display component for all 73 visualizations.

Displays summary statistics below each chart in a consistent HTML format:
- Record count
- Mean, min, max range
- Data freshness (last_timestamp)
- Calculation method (hardcoded label)
- Confidence level
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StatisticsPanel:
    """Statistics data for display below a visualization.

    Attributes:
        record_count: Number of records in the dataset
        mean_value: Mean value (optional, if applicable)
        min_value: Minimum value in the data
        max_value: Maximum value in the data
        last_timestamp: When the data was last updated
        calculation_method: Description of how the metric was calculated
        confidence_level: Confidence level (e.g., "95%")
        additional_stats: Optional dict of additional statistics to display
    """

    record_count: int
    mean_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    last_timestamp: Optional[datetime] = None
    calculation_method: str = "Data-driven"
    confidence_level: str = "95%"
    additional_stats: Optional[dict] = None

    def to_html(self) -> str:
        """Render statistics as HTML panel.

        Returns:
            HTML string with styled statistics display
        """
        html_parts = [
            '<div class="statistics-panel" style="margin-top: 20px; padding: 15px; '
            'background-color: #f5f5f5; border-radius: 4px; border-left: 4px solid #1f77b4;">',
            '<h4 style="margin-top: 0; color: #333;">Summary Statistics</h4>',
            '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; font-size: 14px;">',
        ]

        # Record count
        html_parts.append(
            f'<div><strong>Records:</strong> {self.record_count:,}</div>'
        )

        # Mean value
        if self.mean_value is not None:
            html_parts.append(
                f'<div><strong>Mean:</strong> {self.mean_value:.2f}</div>'
            )

        # Range
        if self.min_value is not None and self.max_value is not None:
            html_parts.append(
                f'<div><strong>Range:</strong> '
                f'{self.min_value:.2f} – {self.max_value:.2f}</div>'
            )

        # Data freshness
        if self.last_timestamp:
            timestamp_str = self.last_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            html_parts.append(
                f'<div><strong>Data Freshness:</strong> {timestamp_str}</div>'
            )

        # Calculation method
        html_parts.append(
            f'<div><strong>Method:</strong> {self.calculation_method}</div>'
        )

        # Confidence level
        html_parts.append(
            f'<div><strong>Confidence:</strong> {self.confidence_level}</div>'
        )

        # Additional statistics
        if self.additional_stats:
            for key, value in self.additional_stats.items():
                if isinstance(value, float):
                    html_parts.append(
                        f'<div><strong>{key}:</strong> {value:.4f}</div>'
                    )
                else:
                    html_parts.append(
                        f'<div><strong>{key}:</strong> {value}</div>'
                    )

        html_parts.append("</div></div>")

        return "".join(html_parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of statistics
        """
        return {
            "record_count": self.record_count,
            "mean_value": self.mean_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "last_timestamp": (
                self.last_timestamp.isoformat()
                if self.last_timestamp
                else None
            ),
            "calculation_method": self.calculation_method,
            "confidence_level": self.confidence_level,
            "additional_stats": self.additional_stats,
        }
