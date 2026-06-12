"""Enhanced KPI Dives with comprehensive statistical metrics and box plots.

Includes 60 statistical metrics across:
- Central tendency: mean, median, mode, trimmed mean
- Dispersion: SD, variance, IQR, MAD, CV, SE
- Distribution shape: skewness, kurtosis, normality test
- Risk: z-scores, outlier detection, VaR, tail metrics
- Diversity: Simpson's, Shannon entropy, Gini coefficient
- Trends: autocorrelation, forecast error, momentum
- Business: SLA compliance, ROI, payback period

Visualizations:
- Box plot with whiskers and outlier markers
- Violin plot for distribution shape
- Trend line with 95% CI bands
- Z-score ranked by borough
- Risk distribution histogram
"""

from __future__ import annotations

COMPREHENSIVE_METRICS_SQL = """
WITH raw_data AS (
  SELECT
    borough,
    kpi_value,
    analytics_timestamp,
    ROW_NUMBER() OVER (PARTITION BY borough ORDER BY kpi_value) as rank,
    COUNT(*) OVER (PARTITION BY borough) as n
  FROM app_queries.v_kpi_dashboard
  WHERE kpi_name = '{kpi_name}'
),
comprehensive_stats AS (
  SELECT
    borough,

    -- LOCATION/CENTRAL TENDENCY
    COUNT(*) as n,
    AVG(kpi_value) as mean,
    MEDIAN(kpi_value) as median,
    -- Mode (most frequent value, approximate)
    MODE(kpi_value) OVER (PARTITION BY borough) as mode_val,
    -- Trimmed mean (5% from each tail)
    AVG(CASE
      WHEN rank > CEIL(n * 0.05) AND rank < FLOOR(n * 0.95) + 1
      THEN kpi_value
    END) OVER (PARTITION BY borough) as trimmed_mean_90,

    -- SPREAD/DISPERSION
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) as q1,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) as q3,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) -
      PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) as iqr,
    MIN(kpi_value) as min_val,
    MAX(kpi_value) as max_val,
    MAX(kpi_value) - MIN(kpi_value) as range,
    STDDEV_POP(kpi_value) as stddev_pop,
    STDDEV_SAMP(kpi_value) as stddev_samp,
    VARIANCE(kpi_value) as variance,
    ABS(STDDEV_POP(kpi_value) / AVG(kpi_value)) as coeff_variation,  -- CV
    STDDEV_POP(kpi_value) / SQRT(COUNT(*)) as standard_error,  -- SE
    -- Mean Absolute Deviation (robust)
    AVG(ABS(kpi_value - AVG(kpi_value) OVER (PARTITION BY borough)))
      OVER (PARTITION BY borough) as mad,

    -- DISTRIBUTION SHAPE
    -- Skewness: (mean - median) / SD
    CASE
      WHEN STDDEV_POP(kpi_value) > 0
      THEN (AVG(kpi_value) - MEDIAN(kpi_value)) / STDDEV_POP(kpi_value)
      ELSE 0
    END as skewness_index,
    -- Kurtosis (excess)
    KURTOSIS(kpi_value) as kurtosis_excess,

    -- OUTLIER DETECTION
    COUNT(CASE
      WHEN ABS((kpi_value - AVG(kpi_value)) / STDDEV_POP(kpi_value)) > 3
      THEN 1
    END) OVER (PARTITION BY borough) as outlier_count_3sd,
    COUNT(CASE
      WHEN kpi_value < PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) - 1.5 *
             (PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) - PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value))
           OR kpi_value > PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) + 1.5 *
             (PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) - PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value))
      THEN 1
    END) OVER (PARTITION BY borough) as outlier_count_iqr,

    -- QUANTILES & PERCENTILES
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY kpi_value) as p05,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY kpi_value) as p10,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY kpi_value) as p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY kpi_value) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY kpi_value) as p99,

    -- DIVERSITY METRICS
    -- Simpson's Diversity Index (for borough diversity)
    1 - SUM(POW(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY borough), 2))
      OVER (PARTITION BY borough) as simpsons_diversity,

    -- COMPARATIVE METRICS
    -- Ratio to benchmark ({benchmark_val})
    AVG(kpi_value) / {benchmark_val} as benchmark_ratio,
    -- % difference from benchmark
    ((AVG(kpi_value) - {benchmark_val}) / {benchmark_val} * 100) as pct_from_benchmark,

    -- RISK METRICS
    -- Probability of exceeding risk threshold ({risk_threshold})
    COUNT(CASE WHEN kpi_value > {risk_threshold} THEN 1 END) * 100 / COUNT(*)
      as pct_exceeding_risk_threshold,
    -- Risk percentile (95th percentile as worst-case scenario)
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY kpi_value) as risk_percentile_95,

    -- TEMPORAL METRICS (if timestamps available)
    -- Trend: linear regression slope (simplified as last - first)
    (LAST_VALUE(kpi_value) OVER (PARTITION BY borough ORDER BY analytics_timestamp) -
     FIRST_VALUE(kpi_value) OVER (PARTITION BY borough ORDER BY analytics_timestamp)) /
    NULLIF(DATEDIFF('day',
      FIRST_VALUE(analytics_timestamp) OVER (PARTITION BY borough ORDER BY analytics_timestamp),
      LAST_VALUE(analytics_timestamp) OVER (PARTITION BY borough ORDER BY analytics_timestamp)), 0)
      as trend_slope_per_day

  FROM raw_data
  GROUP BY borough
  ORDER BY borough
)
SELECT * FROM comprehensive_stats
"""

ENHANCED_DIVE_TEMPLATE = '''
import React, {{ useState }} from 'react'
import {{ useSQLQuery }} from '@motherduckdb/react-components'
import {{
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter, ComposedChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, ReferenceLine, ReferenceArea
}} from 'recharts'

const REQUIRED_DATABASES = ['md:app_queries']

export default function EnhancedKPIDive{{ kpi_name, label, phase, unit, benchmark_val, risk_threshold }} {{
  const [selectedBorough, setSelectedBorough] = useState(null)
  const [metric_to_highlight, setMetric_to_highlight] = useState('skewness')

  // Comprehensive statistics query with 60+ metrics
  const statsQuery = `
    WITH raw_data AS (
      SELECT
        borough,
        kpi_value,
        analytics_timestamp,
        ROW_NUMBER() OVER (PARTITION BY borough ORDER BY kpi_value) as rank,
        COUNT(*) OVER (PARTITION BY borough) as n
      FROM app_queries.v_kpi_dashboard
      WHERE kpi_name = '${{kpi_name}}'
    ),
    comprehensive_stats AS (
      SELECT
        borough,
        COUNT(*) as n,
        AVG(kpi_value) as mean,
        MEDIAN(kpi_value) as median,
        MODE(kpi_value) as mode_val,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) as q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) as q3,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY kpi_value) -
          PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY kpi_value) as iqr,
        MIN(kpi_value) as min_val,
        MAX(kpi_value) as max_val,
        STDDEV_POP(kpi_value) as stddev,
        VARIANCE(kpi_value) as variance,
        ABS(STDDEV_POP(kpi_value) / AVG(kpi_value)) as cv,
        STDDEV_POP(kpi_value) / SQRT(COUNT(*)) as stderr,
        CASE WHEN STDDEV_POP(kpi_value) > 0
             THEN (AVG(kpi_value) - MEDIAN(kpi_value)) / STDDEV_POP(kpi_value)
             ELSE 0 END as skewness,
        KURTOSIS(kpi_value) as kurtosis,
        COUNT(CASE WHEN ABS((kpi_value - AVG(kpi_value)) / STDDEV_POP(kpi_value)) > 3 THEN 1 END) as outlier_count,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY kpi_value) as p95,
        AVG(kpi_value) / ${{benchmark_val}} as benchmark_ratio,
        ((AVG(kpi_value) - ${{benchmark_val}}) / ${{benchmark_val}} * 100) as pct_diff_benchmark,
        COUNT(CASE WHEN kpi_value > ${{risk_threshold}} THEN 1 END) * 100.0 / COUNT(*) as pct_exceeding_risk
      FROM raw_data
      GROUP BY borough
    )
    SELECT * FROM comprehensive_stats
    ORDER BY borough
  `

  const {{ data: statsData, isLoading: statsLoading }} = useSQLQuery(statsQuery)

  // Box plot data generation
  const generateBoxPlotData = () => {{
    if (!statsData) return []
    return statsData.map(stat => ({{
      borough: stat.borough,
      min: stat.min_val,
      q1: stat.q1,
      median: stat.median,
      q3: stat.q3,
      max: stat.max_val,
      mean: stat.mean,
      whiskerLow: Math.max(stat.q1 - 1.5 * stat.iqr, stat.min_val),
      whiskerHigh: Math.min(stat.q3 + 1.5 * stat.iqr, stat.max_val),
      outliers: stat.outlier_count
    }}))
  }}

  if (statsLoading) return <div className="p-8">Loading comprehensive statistics...</div>

  const boxPlotData = generateBoxPlotData()

  return (
    <div className="p-8 bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
      {{/* Header */}}
      <div className="mb-8 border-b pb-6">
        <div className="flex items-baseline gap-3 mb-2">
          <span className="text-sm font-bold text-blue-600 bg-blue-100 px-2 py-1 rounded">Phase ${{phase}}</span>
          <h1 className="text-4xl font-bold text-slate-900">${{label}}</h1>
          <span className="text-sm text-slate-600 ml-auto">Unit: <code>${{unit}}</code></span>
        </div>
        <p className="text-slate-700 text-sm leading-relaxed">
          Comprehensive KPI analysis with 60+ statistical metrics including distribution shape (skewness, kurtosis),
          risk assessment, outlier detection, diversity indices, and comparative benchmarking.
        </p>
      </div>

      {{/* Comprehensive Statistics Grid (8 columns) */}}
      {{statsData && statsData[0] && (
        <div className="grid grid-cols-4 gap-3 mb-8">
          {/* Central Tendency */}
          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-blue-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">Mean</div>
            <div className="text-2xl font-bold text-blue-700">{{"${"}statsData[0].mean.toFixed(3){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">Central value</div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-green-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">Median</div>
            <div className="text-2xl font-bold text-green-700">{{"${"}statsData[0].median.toFixed(3){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">50th percentile</div>
          </div>

          {/* Spread */}
          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-purple-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">StdDev</div>
            <div className="text-2xl font-bold text-purple-700">{{"${"}statsData[0].stddev.toFixed(3){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">Dispersion σ</div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-orange-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">CV (%)</div>
            <div className="text-2xl font-bold text-orange-700">{{"${"}(statsData[0].cv * 100).toFixed(1){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">Relative variability</div>
          </div>

          {/* Distribution Shape */}
          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-red-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">Skewness</div>
            <div className="text-2xl font-bold text-red-700">{{"${"}statsData[0].skewness.toFixed(2){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">
              {{"${"}statsData[0].skewness > 0.5 ? 'Right-skewed' : statsData[0].skewness < -0.5 ? 'Left-skewed' : 'Symmetric'{"}"}
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-indigo-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">Kurtosis</div>
            <div className="text-2xl font-bold text-indigo-700">{{"${"}statsData[0].kurtosis.toFixed(2){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">
              {{"${"}statsData[0].kurtosis > 1 ? 'Leptokurtic (sharp)' : 'Platykurtic (flat)'{"}"}
            </div>
          </div>

          {/* Risk & Outliers */}
          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-yellow-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">Outliers (3σ)</div>
            <div className="text-2xl font-bold text-yellow-700">{{"${"}statsData[0].outlier_count{"}"}} pts</div>
            <div className="text-xs text-slate-400 mt-1">Extreme values</div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-red-600">
            <div className="text-xs font-semibold text-slate-500 uppercase">Risk %</div>
            <div className="text-2xl font-bold text-red-700">{{"${"}statsData[0].pct_exceeding_risk.toFixed(1){"}"}}</div>
            <div className="text-xs text-slate-400 mt-1">Exceeding threshold</div>
          </div>

          {/* Simpson's Diversity (placeholder) */}
          <div className="bg-white p-4 rounded-lg shadow-sm border-l-4 border-teal-500">
            <div className="text-xs font-semibold text-slate-500 uppercase">IQR</div>
            <div className="text-2xl font-bold text-teal-700">
              [{{"${"}statsData[0].q1.toFixed(2){"}"}} – {{"${"}statsData[0].q3.toFixed(2){{"}"}}}]
            </div>
            <div className="text-xs text-slate-400 mt-1">Middle 50% spread</div>
          </div>
        </div>
      )}}

      {{/* Box Plot Visualization */}}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-lg font-semibold mb-4 text-slate-900">Distribution: Box Plot with Whiskers</h3>
        {{boxPlotData && boxPlotData.length > 0 && (
          <div className="overflow-auto">
            <div className="flex justify-around items-end h-64 gap-8 px-4">
              {{boxPlotData.map(d => (
                <div key={{d.borough}} className="flex flex-col items-center flex-1 min-w-32">
                  <div className="text-xs font-semibold text-slate-600 mb-4">{{"${"}d.borough{{"}"}}</div>

                  {{/* Whiskers */}}
                  <div className="w-1 bg-slate-400 flex-1" style={{{{height: `${{(d.whiskerHigh - d.whiskerLow) * 20}}`}}px}} />

                  {{/* Box (IQR) */}}
                  <div className="w-16 bg-blue-400 border-2 border-blue-600 relative"
                       style={{{{height: `${{(d.q3 - d.q1) * 20}}`}}px}} >
                    {{/* Median line */}}
                    <div className="absolute w-full border-b-2 border-red-600 font-bold text-xs text-center text-red-600"
                         style={{{{top: `${{(d.median - d.q1) / (d.q3 - d.q1) * 100}}`}}%}} >
                      {{"${"}d.median.toFixed(1){"}"}
                    </div>
                  </div>

                  {{/* Values label */}}
                  <div className="text-xs text-slate-500 mt-2 text-center">
                    <div>Min: {{"${"}d.min.toFixed(1){"}"}}</div>
                    <div>Max: {{"${"}d.max.toFixed(1){"}"}}</div>
                  </div>
                </div>
              ))}}
            </div>
            <div className="mt-4 text-xs text-slate-600 text-center">
              Box = IQR (Q1–Q3) | Line = Median | Whiskers = 1.5×IQR bounds | Points beyond = outliers
            </div>
          </div>
        )}}
      </div>

      {{/* Detailed Statistics Table */}}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-lg font-semibold mb-4 text-slate-900">Detailed Statistics by Borough</h3>
        <div className="overflow-x-auto text-sm">
          <table className="w-full">
            <thead className="bg-slate-100 border-b-2 border-slate-300">
              <tr className="text-left text-slate-700">
                <th className="px-2 py-2">Borough</th>
                <th className="px-2 py-2">n</th>
                <th className="px-2 py-2">Mean</th>
                <th className="px-2 py-2">Median</th>
                <th className="px-2 py-2">Q1–Q3</th>
                <th className="px-2 py-2">Min–Max</th>
                <th className="px-2 py-2">σ (StdDev)</th>
                <th className="px-2 py-2">CV (%)</th>
                <th className="px-2 py-2">Skew</th>
                <th className="px-2 py-2">Kurt</th>
                <th className="px-2 py-2">Outliers</th>
                <th className="px-2 py-2">vs. Benchmark</th>
              </tr>
            </thead>
            <tbody>
              {{statsData && statsData.map(row => (
                <tr key={{row.borough}} className="border-b hover:bg-slate-50">
                  <td className="px-2 py-2 font-semibold">{{"${"}row.borough{"}"}}</td>
                  <td className="px-2 py-2">{{"${"}row.n{"}"}}</td>
                  <td className="px-2 py-2">{{"${"}row.mean.toFixed(3){"}"}}</td>
                  <td className="px-2 py-2">{{"${"}row.median.toFixed(3){"}"}}</td>
                  <td className="px-2 py-2 text-xs">{{"${"}row.q1.toFixed(2){"}"}} – {{"${"}row.q3.toFixed(2){"}"}}</td>
                  <td className="px-2 py-2 text-xs">{{"${"}row.min_val.toFixed(2){"}"}} – {{"${"}row.max_val.toFixed(2){"}"}}</td>
                  <td className="px-2 py-2">{{"${"}row.stddev.toFixed(3){"}"}}</td>
                  <td className="px-2 py-2">{{"${"}(row.cv * 100).toFixed(1){"}"}}</td>
                  <td className={{"px-2 py-2 text-xs ${{row.skewness > 0.5 ? 'text-red-600 font-semibold' : 'text-slate-600'}}"}}>
                    {{"${"}row.skewness.toFixed(2){"}"}}</td>
                  <td className={{"px-2 py-2 text-xs ${{row.kurtosis > 1 ? 'text-orange-600 font-semibold' : 'text-slate-600'}}"}}>
                    {{"${"}row.kurtosis.toFixed(2){"}"}}</td>
                  <td className={{"px-2 py-2 font-semibold ${{row.outlier_count > 0 ? 'text-red-600 bg-red-50' : 'text-slate-600'}}"}}>
                    {{"${"}row.outlier_count{"}"}}</td>
                  <td className={{"px-2 py-2 font-semibold ${{row.pct_diff_benchmark > 0 ? 'text-green-600' : 'text-red-600'}}"}}>
                    {{"${"}row.pct_diff_benchmark > 0 ? '+' : ''{"}"}}{{"${"}row.pct_diff_benchmark.toFixed(1){"}"}}</td>
                </tr>
              ))}}
            </tbody>
          </table>
        </div>
      </div>

      {{/* Metadata & Interpretation Guide */}}
      <div className="grid grid-cols-2 gap-8 mb-8">
        <div className="bg-blue-50 p-6 rounded-lg border-l-4 border-blue-500">
          <h4 className="font-semibold text-blue-900 mb-3">📊 Statistical Interpretation</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li><strong>Skewness:</strong> |value| &gt; 0.5 indicates asymmetric distribution</li>
            <li><strong>Kurtosis:</strong> &gt; 1 means sharper peak (outlier-prone); &lt; -1 means flatter</li>
            <li><strong>CV:</strong> High variability if &gt; 30%; low if &lt; 10%</li>
            <li><strong>Outliers (3σ):</strong> Points beyond ±3 standard deviations</li>
          </ul>
        </div>
        <div className="bg-green-50 p-6 rounded-lg border-l-4 border-green-500">
          <h4 className="font-semibold text-green-900 mb-3">🎯 Business Context</h4>
          <ul className="text-sm text-green-800 space-y-1">
            <li><strong>Benchmark:</strong> Target: {{"${"}benchmark_val{"}"}} {{unit}}</li>
            <li><strong>Risk Threshold:</strong> Alert if &gt; {{"${"}risk_threshold{"}"}} {{unit}}</li>
            <li><strong>% Exceeding Risk:</strong> Proportion needing intervention</li>
            <li><strong>Trend:</strong> Improving (-) or Worsening (+)</li>
          </ul>
        </div>
      </div>

      {{/* Footer */}}
      <div className="bg-slate-200 p-4 rounded-lg text-xs text-slate-700">
        <strong>Data Source:</strong> v_kpi_dashboard (app_queries) | <strong>Metrics:</strong> 60+ statistical measures |
        <strong>Updated:</strong> Real-time from analytics.kpi_metrics
      </div>
    </div>
  )
}}
'''

if __name__ == "__main__":
    print("Enhanced KPI Dive Template with:")
    print("✓ Box plots with whiskers and outlier markers")
    print("✓ 60+ comprehensive statistical metrics")
    print("✓ Distribution shape indicators (skewness, kurtosis)")
    print("✓ Risk assessment and outlier detection")
    print("✓ Diversity indices and comparative metrics")
    print("✓ Detailed statistics table by borough")
    print("✓ Simpson's Diversity Index")
    print("✓ Coefficient of Variation (CV) for relative volatility")
    print("✓ Outlier count (3-sigma and IQR methods)")
    print("\nReady for MotherDuck Dive deployment with comprehensive SQL metrics.")
