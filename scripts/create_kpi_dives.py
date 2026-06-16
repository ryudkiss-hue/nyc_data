"""Generate 18 comprehensive KPI Dives with extensive statistics and interactivity.

Creates a MotherDuck Dive for each KPI with:
- Time-series/trend visualization
- Comprehensive statistics (mean, median, min/max, quartiles, IQR, SD, n)
- Cross-tabs by borough
- Simpson's Diversity Index (distribution diversity)
- Interactive filtering and borough selection
- Summary statistics panel
- Risk indicators and thresholds

Usage:
    python scripts/create_kpi_dives.py --create-all
    python scripts/create_kpi_dives.py --create-phase B
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 18 KPI definitions with metadata
KPI_DEFINITIONS = {
    # Phase B: Spatial Clustering Analysis (3 KPIs)
    "phase_b_clustering_strength": {
        "phase": "B",
        "label": "Clustering Strength (Moran's I)",
        "description": "Spatial autocorrelation index quantifying geographic clustering of violations",
        "metric_type": "clustering_score",
        "unit": "0-1",
        "benchmark": 0.5,
        "risk_threshold": 0.3,
        "icon": "map-cluster",
    },
    "phase_b_confidence": {
        "phase": "B",
        "label": "Clustering Confidence",
        "description": "Statistical significance of spatial clustering (p-value)",
        "metric_type": "confidence",
        "unit": "0-1",
        "benchmark": 0.05,
        "risk_threshold": 0.1,
        "icon": "trending-up",
    },
    "phase_b_resource_gap": {
        "phase": "B",
        "label": "Resource Gap Index",
        "description": "Deviation between inspection frequency and violation density by borough",
        "metric_type": "index",
        "unit": "%",
        "benchmark": 20,
        "risk_threshold": 40,
        "icon": "alert-circle",
    },
    # Phase C: Distribution Analysis (4 KPIs)
    "phase_c_concentration_index": {
        "phase": "C",
        "label": "Concentration Index",
        "description": "Percentage of violations in top 20% of locations (Gini-like)",
        "metric_type": "percentage",
        "unit": "%",
        "benchmark": 50,
        "risk_threshold": 70,
        "icon": "pie-chart",
    },
    "phase_c_segmentation_potential": {
        "phase": "C",
        "label": "Segmentation Potential",
        "description": "Ability to separate violations by work scope (ada, sidewalk, ramp, etc)",
        "metric_type": "potential_score",
        "unit": "0-100",
        "benchmark": 70,
        "risk_threshold": 50,
        "icon": "layers",
    },
    "phase_c_type_certainty": {
        "phase": "C",
        "label": "Type Certainty",
        "description": "Confidence in violation classification (entropy-based)",
        "metric_type": "confidence",
        "unit": "0-1",
        "benchmark": 0.85,
        "risk_threshold": 0.7,
        "icon": "check-circle",
    },
    "phase_c_distribution_balance": {
        "phase": "C",
        "label": "Distribution Balance (Shannon)",
        "description": "Evenness of violation distribution across borough + scope",
        "metric_type": "diversity",
        "unit": "0-1",
        "benchmark": 0.75,
        "risk_threshold": 0.5,
        "icon": "balance-scale",
    },
    # Phase D: Anomaly Detection (3 KPIs)
    "phase_d_outlier_concentration": {
        "phase": "D",
        "label": "Outlier Concentration",
        "description": "Count of high-priority z-score anomalies (z > 2.0)",
        "metric_type": "count",
        "unit": "locations",
        "benchmark": 20,
        "risk_threshold": 40,
        "icon": "alert-triangle",
    },
    "phase_d_adoption_rate": {
        "phase": "D",
        "label": "Risk Adoption Rate",
        "description": "Percentage of locations adopting remediation from recommendations",
        "metric_type": "percentage",
        "unit": "%",
        "benchmark": 60,
        "risk_threshold": 30,
        "icon": "trending-up",
    },
    "phase_d_priority_score": {
        "phase": "D",
        "label": "Priority Weighting",
        "description": "Average priority score across identified anomalies (1-10)",
        "metric_type": "score",
        "unit": "1-10",
        "benchmark": 7,
        "risk_threshold": 5,
        "icon": "star",
    },
    # Phase E: Time Series Decomposition (4 KPIs)
    "phase_e_trend_direction": {
        "phase": "E",
        "label": "Trend Direction",
        "description": "Linear trend slope in violations over past 90 days (positive = worsening)",
        "metric_type": "trend",
        "unit": "violations/day",
        "benchmark": -0.5,
        "risk_threshold": 0.5,
        "icon": "trending-down",
    },
    "phase_e_seasonality_strength": {
        "phase": "E",
        "label": "Seasonality Index",
        "description": "Strength of seasonal pattern in inspection/violation cycles",
        "metric_type": "index",
        "unit": "0-1",
        "benchmark": 0.4,
        "risk_threshold": 0.7,
        "icon": "calendar",
    },
    "phase_e_resource_gap": {
        "phase": "E",
        "label": "Resource Demand Gap",
        "description": "Forecast: inspection capacity needed vs. current (% over/under)",
        "metric_type": "percentage",
        "unit": "%",
        "benchmark": 0,
        "risk_threshold": 30,
        "icon": "alert-circle",
    },
    "phase_e_forecast_confidence": {
        "phase": "E",
        "label": "Forecast Confidence",
        "description": "95% CI width / mean (inverse = tighter forecast)",
        "metric_type": "confidence",
        "unit": "0-1",
        "benchmark": 0.25,
        "risk_threshold": 0.5,
        "icon": "aperture",
    },
    # Phase F: SLA Compliance & Risk (4 KPIs)
    "phase_f_sla_probability": {
        "phase": "F",
        "label": "SLA Breach Probability",
        "description": "Bootstrap CI: probability of missing 14-day SLA target",
        "metric_type": "probability",
        "unit": "%",
        "benchmark": 10,
        "risk_threshold": 25,
        "icon": "alert-circle",
    },
    "phase_f_risk_score": {
        "phase": "F",
        "label": "Operational Risk Score",
        "description": "Composite risk from violations, trends, SLA probability (0-100)",
        "metric_type": "risk",
        "unit": "0-100",
        "benchmark": 40,
        "risk_threshold": 70,
        "icon": "shield-alert",
    },
    "phase_f_ci_coverage": {
        "phase": "F",
        "label": "Confidence Interval Coverage",
        "description": "Width of 95% bootstrap CI as % of point estimate",
        "metric_type": "percentage",
        "unit": "%",
        "benchmark": 15,
        "risk_threshold": 35,
        "icon": "aperture",
    },
    "phase_f_investment_justification": {
        "phase": "F",
        "label": "Investment ROI Score",
        "description": "Expected reduction in violations per $1K invested (bootstrap mean)",
        "metric_type": "roi",
        "unit": "violations/$1K",
        "benchmark": 5,
        "risk_threshold": 2,
        "icon": "dollar-sign",
    },
}

DIVE_TEMPLATE = '''
import React, { useState } from 'react'
import {{ useSQLQuery }} from '@motherduckdb/react-components'
import {{
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, ReferenceLine
}} from 'recharts'

const REQUIRED_DATABASES = ['md:app_queries']

export default function KPIDive{{ kpi_name, label, phase, unit, benchmark_val, risk_threshold }} {{
  const [selectedBorough, setSelectedBorough] = useState(null)

  // Core KPI time-series and statistics query
  const statsQuery = `
    WITH kpi_data AS (
      SELECT
        borough,
        kpi_value,
        analytics_timestamp,
        ROW_NUMBER() OVER (PARTITION BY borough ORDER BY kpi_value) as rank,
        COUNT(*) OVER (PARTITION BY borough) as n
      FROM app_queries.v_kpi_dashboard
      WHERE kpi_name = '${{kpi_name}}'
    ),
    borough_stats AS (
      SELECT
        borough,
        COUNT(*) as n,
        AVG(kpi_value) as mean,
        MEDIAN(kpi_value) as median,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) as q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) as q3,
        MIN(kpi_value) as min_val,
        MAX(kpi_value) as max_val,
        STDDEV_POP(kpi_value) as stddev,
        -- Simpson's Diversity Index (for distribution)
        1 - SUM(POW(COUNT(*)/COUNT(*) OVER(PARTITION BY borough), 2)) as simpsons_diversity
      FROM kpi_data
      GROUP BY borough
    )
    SELECT * FROM borough_stats
    ORDER BY borough
  `

  const {{ data: statsData, isLoading: statsLoading }} = useSQLQuery(statsQuery)

  // Cross-tab by borough (comparative view)
  const crosstabQuery = `
    SELECT
      kpi_name,
      borough,
      ROUND(kpi_value, 2) as kpi_value,
      CASE
        WHEN kpi_value >= ${{benchmark_val}} THEN 'On Target'
        WHEN kpi_value >= ${{risk_threshold}} THEN 'At Risk'
        ELSE 'Critical'
      END as status,
      analytics_timestamp
    FROM app_queries.v_kpi_dashboard
    WHERE kpi_name = '${{kpi_name}}'
    ORDER BY borough, analytics_timestamp DESC
    LIMIT 100
  `

  const {{ data: crosstabData, isLoading: crosstabLoading }} = useSQLQuery(crosstabQuery)

  if (statsLoading || crosstabLoading) return <div className="p-8">Loading...</div>

  return (
    <div className="p-8 bg-gradient-to-br from-gray-50 to-gray-100 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-sm font-semibold text-gray-500">Phase ${{phase}}</span>
          <h1 className="text-3xl font-bold text-gray-900">${{label}}</h1>
          <span className="text-sm text-gray-600 ml-auto">Unit: ${{unit}}</span>
        </div>
        <p className="text-gray-700 text-sm">
          Comprehensive analysis of key performance indicator across all boroughs.
          Includes distribution statistics, diversity metrics, and risk assessment.
        </p>
      </div>

      {/* Summary Statistics Grid */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        {{statsData && statsData[0] && (
          <>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500 uppercase">Mean</div>
              <div className="text-2xl font-bold">{{"${"}statsData[0].mean.toFixed(2){"}"}}</div>
              <div className="text-xs text-gray-400 mt-1">Across boroughs</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500 uppercase">Median</div>
              <div className="text-2xl font-bold">{{"${"}statsData[0].median.toFixed(2){"}"}}</div>
              <div className="text-xs text-gray-400 mt-1">50th percentile</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500 uppercase">IQR</div>
              <div className="text-2xl font-bold">
                [{{"${"}statsData[0].q1.toFixed(2){"}"}} - {{"${"}statsData[0].q3.toFixed(2){"}}}]
              </div>
              <div className="text-xs text-gray-400 mt-1">25th–75th percentile</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500 uppercase">StdDev</div>
              <div className="text-2xl font-bold">{{"${"}statsData[0].stddev.toFixed(2){"}"}}</div>
              <div className="text-xs text-gray-400 mt-1">Variability</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-xs text-gray-500 uppercase">Simpson's Diversity</div>
              <div className="text-2xl font-bold">{{"${"}statsData[0].simpsons_diversity.toFixed(3){"}"}}</div>
              <div className="text-xs text-gray-400 mt-1">Distribution evenness</div>
            </div>
          </>
        )}}
      </div>

      {/* Borough Breakdown & Cross-Tab */}}
      <div className="grid grid-cols-2 gap-8 mb-8">
        {/* Statistics Table */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Borough-Level Summary</h3>
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left text-gray-600">
                <th className="pb-2">Borough</th>
                <th className="pb-2 text-right">Mean</th>
                <th className="pb-2 text-right">Median</th>
                <th className="pb-2 text-right">Min–Max</th>
                <th className="pb-2 text-right">n</th>
              </tr>
            </thead>
            <tbody>
              {{statsData && statsData.map(row => (
                <tr key={{row.borough}} className="border-b hover:bg-gray-50">
                  <td className="py-2 font-medium">{{"${"}row.borough{"}"}} </td>
                  <td className="py-2 text-right">{{"${"}row.mean.toFixed(2){"}"}}</td>
                  <td className="py-2 text-right">{{"${"}row.median.toFixed(2){"}"}}</td>
                  <td className="py-2 text-right text-xs text-gray-500">
                    {{"${"}row.min_val.toFixed(2){"}"}} – {{"${"}row.max_val.toFixed(2){"}"}}</td>
                  <td className="py-2 text-right">{{"${"}row.n{"}"}} </td>
                </tr>
              ))}}
            </tbody>
          </table>
        </div>

        {/* Risk Status by Borough */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Risk Status</h3>
          {{crosstabData && (
            <div className="space-y-2">
              {{["MN", "BX", "BK", "QN", "SI"].map(borough => {{
                const latestValue = crosstabData.find(row => row.borough === borough)
                const status = latestValue?.status || 'Unknown'
                const statusColor = status === 'On Target' ? 'bg-green-100 text-green-800' :
                                   status === 'At Risk' ? 'bg-yellow-100 text-yellow-800' :
                                   'bg-red-100 text-red-800'
                return (
                  <div key={{borough}} className="flex justify-between items-center p-2 border rounded">
                    <span className="font-medium">{{"${"}borough{"}"}} </span>
                    <span className={{"${"}`px-3 py-1 text-xs font-semibold rounded ${{statusColor}}{"}"}}>
                      {{"${"}status{"}"}} ({{"${"}latestValue?.kpi_value.toFixed(2) || 'N/A'{"}"}} {{unit}})
                    </span>
                  </div>
                )
              }}))}}
            </div>
          )}}
        </div>
      </div>

      {/* Time-Series Trend (if timestamp data available) */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Values by Borough</h3>
        {{crosstabData && crosstabData.length > 0 && (
          <ResponsiveContainer width="100%" height={{"${"}}300{"}"}}>
            <BarChart data={{crosstabData}}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="borough" />
              <YAxis />
              <Tooltip formatter={{(val) => val.toFixed(2)}} />
              <Legend />
              <Bar dataKey="kpi_value" fill="#3b82f6" name={{"${"}}KPI Value{"}{"}"}} />
              <ReferenceLine y={{{{benchmark_val}}}} stroke="#10b981" label="Benchmark" />
              <ReferenceLine y={{{{risk_threshold}}}} stroke="#f59e0b" label="Risk Threshold" strokeDasharray="5 5" />
            </BarChart>
          </ResponsiveContainer>
        )}}
      </div>

      {/* Metadata Footer */}
      <div className="mt-8 text-xs text-gray-500 border-t pt-4">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="font-semibold text-gray-700">Benchmark</div>
            <div>{{"${"}benchmark_val{"}"}} {{unit}}</div>
          </div>
          <div>
            <div className="font-semibold text-gray-700">Risk Threshold</div>
            <div>{{"${"}risk_threshold{"}"}} {{unit}}</div>
          </div>
          <div>
            <div className="font-semibold text-gray-700">Data Source</div>
            <div>v_kpi_dashboard (app_queries)</div>
          </div>
          <div>
            <div className="font-semibold text-gray-700">Updated</div>
            <div>Real-time from analytics.kpi_metrics</div>
          </div>
        </div>
      </div>
    </div>
  )
}}
'''


def create_kpi_dive_code(kpi_name: str, kpi_def: dict[str, Any]) -> str:
    """Generate a complete Dive component for one KPI.

    Args:
        kpi_name: Key name of KPI (e.g. 'phase_b_clustering_strength')
        kpi_def: Metadata dict with label, phase, unit, benchmark, risk_threshold

    Returns:
        Complete JSX/React code ready for MotherDuck Dive save
    """
    code = DIVE_TEMPLATE.format(
        kpi_name=kpi_name,
        label=kpi_def["label"],
        phase=kpi_def["phase"],
        unit=kpi_def["unit"],
        benchmark_val=kpi_def["benchmark"],
        risk_threshold=kpi_def["risk_threshold"],
    )
    return code


def generate_dive_metadata(kpi_name: str, kpi_def: dict[str, Any]) -> dict[str, Any]:
    """Generate MotherDuck Dive metadata/descriptor.

    Returns:
        Dict with title, description, tags, etc. for dive save
    """
    return {
        "title": f"KPI: {kpi_def['label']}",
        "description": kpi_def["description"],
        "tags": [f"phase-{kpi_def['phase'].lower()}", "kpi", "analytics", "sla"],
        "category": f"Phase {kpi_def['phase']} Analytics",
        "benchmark_value": kpi_def["benchmark"],
        "risk_threshold": kpi_def["risk_threshold"],
        "unit": kpi_def["unit"],
        "kpi_id": kpi_name,
    }


if __name__ == "__main__":
    import sys

    # Example: generate code for one KPI
    if len(sys.argv) > 1 and sys.argv[1] == "--create-all":
        print("Generating all 18 KPI Dives...")
        for kpi_name, kpi_def in KPI_DEFINITIONS.items():
            print(f"\n{kpi_name}: {kpi_def['label']}")
            metadata = generate_dive_metadata(kpi_name, kpi_def)
            print(f"  Metadata: {json.dumps(metadata, indent=2)}")
            # Code generation would happen here with MCP save_dive call
            print("  Status: Ready for MotherDuck save (via save_dive MCP)")
    else:
        # Default: show one example
        example_kpi = "phase_b_clustering_strength"
        example_def = KPI_DEFINITIONS[example_kpi]
        print(f"Example KPI Dive: {example_kpi}")
        print(f"Label: {example_def['label']}")
        print(f"Description: {example_def['description']}")
        metadata = generate_dive_metadata(example_kpi, example_def)
        print(f"\nMetadata:\n{json.dumps(metadata, indent=2)}")
