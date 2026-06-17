import { useSQLQuery } from "@motherduck/react-sql-query";
import { 
  ShieldCheck, AlertTriangle, CircleDollarSign, Scale, Filter, ListChecks, 
  Search, TrendingUp, Activity, Info, Trees, ChartDots
} from "lucide-react";
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ZAxis, Legend, Cell
} from "recharts";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v: unknown): number => (v != null ? Number(v) : 0);
const FMT = (b: string) => b === "STATEN ISLAND" ? "Staten Is." : b.charAt(0) + b.slice(1).toLowerCase();

export default function SpatialConflictsMaster() {
  const { data, isLoading, isError } = useSQLQuery(`
    WITH tree_agg AS (
      SELECT cb, COUNT(*) as tree_incidents
      FROM "nyc_mission_control"."main"."tree_damage"
      GROUP BY 1
    ),
    violation_agg AS (
      SELECT cb, COUNT(*) as sw_violations
      FROM "nyc_mission_control"."main"."violations"
      GROUP BY 1
    )
    SELECT 
      v.cb, 
      v.sw_violations as x, 
      t.tree_incidents as y,
      (v.sw_violations * 1.0 / t.tree_incidents) as sensitivity_index
    FROM violation_agg v
    JOIN tree_agg t ON v.cb = t.cb
    WHERE t.tree_incidents > 5
    ORDER BY sensitivity_index DESC
  `);

  const rows = Array.isArray(data) ? data : [];

  const n = rows.length;
  const sumX = rows.reduce((acc, r) => acc + r.x, 0);
  const sumY = rows.reduce((acc, r) => acc + r.y, 0);
  const sumXY = rows.reduce((acc, r) => acc + r.x * r.y, 0);
  const sumX2 = rows.reduce((acc, r) => acc + r.x * r.x, 0);
  const sumY2 = rows.reduce((acc, r) => acc + r.y * r.y, 0);
  
  const correlation = n > 0 ? (n * sumXY - sumX * sumY) / 
    Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY)) : 0;

  if (isLoading) {
    return (
      <div style={{ padding: "100px", textAlign: "center", fontFamily: "sans-serif" }}>
        <Activity size={64} color="#0083B0" />
        <h2 style={{ marginTop: "24px", color: "#666" }}>COMPUTING SPATIAL COVARIANCE...</h2>
      </div>
    );
  }

  return (
    <div style={{ background: "#FFFFFF", color: "#000000", padding: "32px", fontFamily: "sans-serif", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "40px", borderBottom: "4px solid #0083B0", paddingBottom: "20px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "32px", fontWeight: 900, textTransform: "uppercase" }}>Spatial Conflict Master Index</h1>
          <p style={{ color: "#666", fontSize: "18px", marginTop: "8px" }}>Green Canopy vs. Clear Paths: Ecological Correlation Analysis</p>
        </div>
        <div style={{ padding: "4px 12px", border: "2px solid #0083B0", borderRadius: "4px", fontSize: "12px", fontWeight: "bold", color: "#0083B0" }}>NYC DOT OFFICIAL</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "40px" }}>
        <div style={{ padding: "32px", border: "1px solid #EEE", borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
          <h3 style={{ margin: "0 0 24px 0", fontSize: "20px", fontWeight: 800 }}>The Correlation Engine</h3>
          <div style={{ width: "100%", height: "400px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="x" name="Sidewalk Violations" />
                <YAxis type="number" dataKey="y" name="Tree Incidents" />
                <ZAxis type="number" dataKey="sensitivity_index" range={[50, 400]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: "#000", color: "#FFF", borderRadius: "8px", border: "none" }} />
                <Legend verticalAlign="top" />
                <Scatter name="Community Boards" data={rows} fill="#0083B0">
                  {rows.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.sensitivity_index > 2 ? '#D32F2F' : '#2E7D32'} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div style={{ padding: "32px", background: "#F1F3F5", borderLeft: "6px solid #2E7D32", borderRadius: "4px" }}>
             <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <TrendingUp size={32} color="#2E7D32" />
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#666", textTransform: "uppercase" }}>Pearson Correlation (r)</div>
                <div style={{ fontSize: "32px", fontWeight: 900 }}>{correlation.toFixed(3)}</div>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6 }}>
              {correlation > 0.7 ? "Strong positive spatial association detected." : correlation > 0.4 ? "Moderate spatial coupling observed." : "Weak spatial correlation in current telemetry."}
              This coefficient measures the degree to which tree root expansion drives sidewalk displacement.
            </p>
          </div>

          <div style={{ padding: "24px", background: "#FFEBEE", borderLeft: "6px solid #D32F2F", borderRadius: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <AlertTriangle size={24} color="#D32F2F" />
              <h4 style={{ margin: 0, fontSize: "18px", fontWeight: 800, color: "#D32F2F" }}>Ecological Impact</h4>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6, color: "#B71C1C" }}>
              <strong>Critical Insight:</strong> Community Boards with a Sensitivity Index &gt; 2.0 (red) represent areas where infrastructure maintenance lags biological growth.
            </p>
          </div>

          <div style={{ padding: "24px", border: "1px solid #EEE", borderRadius: "12px" }}>
            <h4 style={{ margin: "0 0 16px 0", fontSize: "16px", fontWeight: 800 }}>Top Conflict Hotspots</h4>
            {rows.slice(0, 5).map(r => (
              <div key={r.cb} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #F4F4F4" }}>
                <span style={{ fontSize: "13px", fontWeight: 700 }}>CB {r.cb}</span>
                <span style={{ padding: "2px 10px", background: "#D32F2F", color: "#FFF", borderRadius: "12px", fontSize: "11px", fontWeight: 800 }}>{N(r.sensitivity_index).toFixed(2)} INDEX</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: "60px", borderTop: "1px solid #EEE", paddingTop: "20px", textAlign: "center" }}>
        <p style={{ fontSize: "12px", color: "#AAA", fontWeight: 600, letterSpacing: "1px" }}>NYC DOT SIM DASHBOARD · ENVIRONMENTAL OVERLAY · CONFIDENTIAL</p>
      </div>
    </div>
  );
}
