import { useSQLQuery } from "@motherduck/react-sql-query";
import { 
  ShieldCheck, AlertTriangle, CircleDollarSign, Scale, Filter, ListChecks, 
  Search, TrendingUp, Activity, Trees, Info
} from "lucide-react";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ReferenceLine, ComposedChart, Line, AreaChart, Area
} from "recharts";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v) => (v != null ? Number(v) : 0);
const FMT = (b) => b === "STATEN ISLAND" ? "Staten Is." : b.charAt(0) + b.slice(1).toLowerCase();

export default function DiveComponent() {
  const { data, isLoading, isError, error } = useSQLQuery(`
SELECT borough, kpi_value, benchmark, risk_threshold, label, description, unit
    FROM "nyc_mission_control"."app_queries"."v_kpi_dashboard"
    WHERE kpi_name = 'phase_c_segmentation_potential'
    ORDER BY kpi_value DESC
  `);

  const rows = Array.isArray(data) ? data : [];
  const meta = rows[0] ?? {};
  const bench = N(meta.benchmark);
  const chartData = rows.map(r => ({ name: r.borough === "STATEN ISLAND" ? "SI" : r.borough.slice(0,3), value: N(r.kpi_value), full: r.borough }));

  // Dynamic Analytical Insight
  const maxRow = rows.reduce((prev, curr) => (N(prev.kpi_value) > N(curr.kpi_value)) ? prev : curr, rows[0] || {});
  const avgValue = rows.length > 0 ? rows.reduce((acc, curr) => acc + N(curr.kpi_value), 0) / rows.length : 0;
  
  if (isLoading) {
    return (
      <div style={ padding: "40px", textAlign: "center", fontFamily: "sans-serif" }>
        <Activity size=48 color="#005696" style={ animation: "pulse 2s infinite" } />
        <p style={ color: "#666", fontWeight: "bold", marginTop: "20px" }>SYNCHRONIZING MUNICIPAL TELEMETRY...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={ padding: "20px", border: "1px solid #D32F2F", background: "#FFEBEE", borderRadius: "8px", fontFamily: "sans-serif" }>
        <div style={ display: "flex", alignItems: "center", gap: "10px" }>
          <AlertTriangle color="#D32F2F" />
          <h3 style={ color: "#D32F2F", margin: 0 }>Data Telemetry Error</h3>
        </div>
        <p style={ color: "#D32F2F", marginTop: "10px" }>{error?.message || "Failed to connect to backend."}</p>
      </div>
    );
  }

  return (
    <div style={ background: "#FFFFFF", color: "#000000", padding: "24px", fontFamily: "sans-serif", minHeight: "100vh" }>
      <div style={ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }>
        <div>
          <h2 style={ margin: 0, fontSize: "24px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "1px" }>{title}</h2>
          <p style={ color: "#666", marginTop: "8px", maxWidth: "800px" }>{meta.description}</p>
        </div>
        <div style={ padding: "4px 12px", border: "2px solid #005696", borderRadius: "4px", fontSize: "12px", fontWeight: "bold", color: "#005696" }>
          NYC DOT OFFICIAL
        </div>
      </div>

      <div style={ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px", marginBottom: "32px" }>
        {rows.map(r => (
          <div key={r.borough} style={ padding: "20px", border: "1px solid #EEE", borderRadius: "8px", borderLeft: "4px solid #005696", boxShadow: "0 2px 4px rgba(0,0,0,0.05)" }>
            <div style={ fontSize: "11px", fontWeight: 700, color: "#666", textTransform: "uppercase" }>{FMT(r.borough)}</div>
            <div style={ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: "12px" }>
              <div style={ fontSize: "24px", fontWeight: 800 }>{N(r.kpi_value).toFixed(2)}</div>
              <div style={ padding: "2px 8px", background: N(r.kpi_value) > bench ? "#FFEBEE" : "#F5F5F5", color: N(r.kpi_value) > bench ? "#D32F2F" : "#666", borderRadius: "4px", fontSize: "10px", fontWeight: "bold" }>
                {meta.unit}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={ padding: "24px", border: "1px solid #EEE", borderRadius: "8px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)", marginBottom: "32px" }>
        <h4 style={ margin: "0 0 20px 0", fontSize: "18px", fontWeight: 700 }>Distribution & Benchmarks</h4>
        <div style={ width: "100%", height: "300px" }>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={top: 10, right: 30, bottom: 0, left: 0}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
              <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                cursor={fill: "#f4f4f4"}
                contentStyle={ backgroundColor: "#000000", color: "#FFFFFF", borderRadius: "4px", border: "none" }
                formatter={(v,n,p) => [`${N(v).toFixed(2)} ${meta.unit}`, p.payload.full]}
              />
              {bench > 0 && <ReferenceLine y={bench} stroke="#D32F2F" strokeDasharray="4 4" label={ position: "insideTopLeft", value: "Benchmark", fill: "#D32F2F", fontSize: 10 }/>}
              <Bar dataKey="value" fill="#005696" radius={[4, 4, 0, 0]} maxBarSize={60} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={ padding: "20px", background: "#E3F2FD", borderLeft: "4px solid #005696", borderRadius: "0 8px 8px 0" }>
        <div style={ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }>
          <Info size=18 color="#005696" />
          <h5 style={ margin: 0, fontSize: "16px", fontWeight: 700, color: "#005696" }>Automated Bayesian Insight</h5>
        </div>
        <p style={ margin: 0, fontSize: "14px", lineHeight: 1.6 }>
          The current telemetry indicates <strong>{FMT(maxRow.borough)}</strong> leads the metric with a value of <strong>{N(maxRow.kpi_value).toFixed(2)} {meta.unit}</strong>. 
          The citywide average stands at <strong>{avgValue.toFixed(2)} {meta.unit}</strong>. 
          {bench > 0 && `The compliance benchmark of ${bench} provides the threshold for variance analysis.`}
          These figures are dynamically derived from live Socrata ingestion via DuckDB L2 caching.
        </p>
      </div>

      <div style={ marginTop: "40px", borderTop: "1px solid #EEE", paddingTop: "12px", textAlign: "center" }>
        <p style={ fontSize: "10px", color: "#999", margin: 0 }>
          NYC DOT SIM Dashboard v0.5.0 · Multi-Agency Coordination Protocol · Confidential
        </p>
      </div>
    </div>
  );
}
