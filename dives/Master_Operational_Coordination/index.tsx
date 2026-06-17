import { useSQLQuery } from "@motherduck/react-sql-query";
import { 
  ShieldCheck, AlertTriangle, CircleDollarSign, Scale, Filter, ListChecks, 
  Search, TrendingUp, Activity, Info, HardHat, Construction
} from "lucide-react";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Legend, LineChart, Line, ComposedChart, Cell
} from "recharts";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function OperationalCoordinationMaster() {
  const { data, isLoading, isError } = useSQLQuery(`
    WITH permit_agg AS (
      SELECT boroughname as borough, COUNT(*) as active_permits
      FROM "nyc_mission_control"."main"."street_permits"
      WHERE permitstatusshortdesc = 'ISSUED'
      GROUP BY 1
    ),
    violation_agg AS (
      SELECT borocode as borough, COUNT(*) as open_violations
      FROM "nyc_mission_control"."main"."violations"
      WHERE vdismissdate IS NULL
      GROUP BY 1
    )
    SELECT 
      v.borough, 
      v.open_violations, 
      COALESCE(p.active_permits, 0) as active_permits,
      (COALESCE(p.active_permits, 0) * 100.0 / v.open_violations) as coordination_density
    FROM violation_agg v
    LEFT JOIN permit_agg p ON v.borough = p.borough
    ORDER BY coordination_density DESC
  `);

  const rows = Array.isArray(data) ? data : [];

  if (isLoading) {
    return (
      <div style={{ padding: "100px", textAlign: "center", fontFamily: "sans-serif" }}>
        <Activity size={64} color="#FF8C00" />
        <h2 style={{ marginTop: "24px", color: "#666" }}>SYNCHRONIZING PERMIT CLUSTERS...</h2>
      </div>
    );
  }

  return (
    <div style={{ background: "#FFFFFF", color: "#000000", padding: "32px", fontFamily: "sans-serif", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "40px", borderBottom: "4px solid #FF8C00", paddingBottom: "20px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "32px", fontWeight: 900, textTransform: "uppercase" }}>Operational Coordination Scorecard</h1>
          <p style={{ color: "#666", fontSize: "18px", marginTop: "8px" }}>Active Permits vs. Pending Defects: Resource Alignment Analysis</p>
        </div>
        <div style={{ padding: "4px 12px", border: "2px solid #FF8C00", borderRadius: "4px", fontSize: "12px", fontWeight: "bold", color: "#FF8C00" }}>CAPITAL COORDINATION</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px", marginBottom: "40px" }}>
        <div style={{ padding: "32px", border: "1px solid #EEE", borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
          <h3 style={{ margin: "0 0 24px 0", fontSize: "20px", fontWeight: 800 }}>Permit vs. Violation Density</h3>
          <div style={{ width: "100%", height: "400px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rows} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="borough" fontSize={12} fontWeight={700} axisLine={false} tickLine={false} />
                <YAxis yAxisId="left" fontSize={12} axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" fontSize={12} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#000", color: "#FFF", borderRadius: "8px", border: "none" }} />
                <Legend verticalAlign="top" />
                <Bar yAxisId="left" dataKey="open_violations" name="Open Violations" fill="#005696" radius={[6, 6, 0, 0]} />
                <Bar yAxisId="left" dataKey="active_permits" name="Active Permits" fill="#FF8C00" radius={[6, 6, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="coordination_density" name="Coordination Index" stroke="#2E7D32" strokeWidth={4} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div style={{ padding: "32px", background: "#FFF3E0", borderLeft: "6px solid #FF8C00", borderRadius: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <Scale size={32} color="#FF8C00" />
              <div>
                <div style={{ fontSize: "12px", fontWeight: 800, color: "#666", textTransform: "uppercase" }}>Coordination Gap</div>
                <div style={{ fontSize: "32px", fontWeight: 900 }}>High Variance</div>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6 }}>
              The <strong>Coordination Index</strong> represents the ratio of active construction permits to pending sidewalk violations. Higher index indicates potential for "Dig Once" optimization.
            </p>
          </div>

          <div style={{ padding: "24px", background: "#E8F5E9", borderLeft: "6px solid #2E7D32", borderRadius: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <Construction size={24} color="#2E7D32" />
              <h4 style={{ margin: 0, fontSize: "18px", fontWeight: 800, color: "#2E7D32" }}>Resource Allocation</h4>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6 }}>
              Regions with low permit density but high violations represent "Maintenance Deserts" where projects are not adequately addressing utility needs.
            </p>
          </div>

          <div style={{ padding: "24px", border: "1px solid #EEE", borderRadius: "12px" }}>
            <h4 style={{ margin: "0 0 16px 0", fontSize: "16px", fontWeight: 800 }}>Borough Scorecard</h4>
            {rows.map(r => (
              <div key={r.borough} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #F4F4F4" }}>
                <span style={{ fontSize: "13px", fontWeight: 700 }}>{r.borough}</span>
                <span style={{ padding: "2px 10px", background: r.coordination_density > 10 ? "#E8F5E9" : "#FFEBEE", color: r.coordination_density > 10 ? "#2E7D32" : "#D32F2F", borderRadius: "12px", fontSize: "11px", fontWeight: 800 }}>
                  {(r.open_violations / (r.active_permits || 1)).toFixed(1)}X RATIO
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: "60px", borderTop: "1px solid #EEE", paddingTop: "20px", textAlign: "center" }}>
        <p style={{ fontSize: "12px", color: "#AAA", fontWeight: 600, letterSpacing: "1px" }}>NYC DOT SIM DASHBOARD · CAPITAL COORDINATION · CONFIDENTIAL</p>
      </div>
    </div>
  );
}
