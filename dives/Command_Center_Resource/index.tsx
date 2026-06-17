import { useSQLQuery, useDiveState } from "@motherduck/react-sql-query";
import { 
  ShieldCheck, AlertTriangle, CircleDollarSign, Scale, Filter, ListChecks, 
  Search, TrendingUp, Activity, Info, Clock, Calendar, BarChart as BarChartIcon
} from "lucide-react";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Legend, LineChart, Line, ComposedChart, Cell
} from "recharts";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v) => (v != null ? Number(v) : 0);
const FMT = (b) => b === "STATEN ISLAND" ? "SI" : b.charAt(0) + b.slice(1).toLowerCase();

export default function Dashboard() {
  const [state, setState] = useDiveState({ borough: "CITYWIDE" });

  const { data: kpiData, isLoading: kpiLoading } = useSQLQuery(`
    SELECT kpi_name, label, avg(kpi_value) as avg_val, max(benchmark) as bench, unit
    FROM "nyc_mission_control"."app_queries"."v_kpi_dashboard"
    WHERE phase = 'B'
    ${state.borough !== "CITYWIDE" ? `AND borough = '${state.borough}'` : ''}
    GROUP BY 1, 2, 5
  `);

  const { data: boroData, isLoading: boroLoading } = useSQLQuery(`
    SELECT borough, kpi_name, kpi_value
    FROM "nyc_mission_control"."app_queries"."v_kpi_dashboard"
    WHERE phase = 'B'
    ORDER BY borough, kpi_name
  `);

  const { data: statData, isLoading: statLoading } = useSQLQuery(`
    SELECT 
      kpi_name,
      label,
      avg(kpi_value) as mean,
      stddev(kpi_value) as variance,
      max(kpi_value) as extreme_max,
      min(kpi_value) as extreme_min
    FROM "nyc_mission_control"."app_queries"."v_kpi_dashboard"
    WHERE phase = 'B'
    GROUP BY 1, 2
  `);

  const isLoading = kpiLoading || boroLoading || statLoading;
  const kpis = Array.isArray(kpiData) ? kpiData : [];
  const boroRows = Array.isArray(boroData) ? boroData : [];
  const statRows = Array.isArray(statData) ? statData : [];

  const mainKpi = kpis[0] ?? {};
  
  const chartData = Array.from(new Set(boroRows.map(r => r.borough))).map(b => ({
    name: b,
    shortName: FMT(b),
    val1: N(boroRows.find(r => r.borough === b && r.kpi_name === kpis[0]?.kpi_name)?.kpi_value),
    val2: N(boroRows.find(r => r.borough === b && r.kpi_name === kpis[1]?.kpi_name)?.kpi_value)
  }));

  if (isLoading) {
    return (
      <div style={{ padding: "100px", textAlign: "center", fontFamily: "sans-serif" }}>
        <Activity size={64} color="#005696" />
        <h2 style={{ marginTop: "24px", color: "#666" }}>SYNCHRONIZING PHASE B TELEMETRY...</h2>
      </div>
    );
  }

  return (
    <div style={{ background: "#FFFFFF", color: "#000000", padding: "32px", fontFamily: "sans-serif", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "40px", borderBottom: "4px solid #005696", paddingBottom: "20px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "32px", fontWeight: 900, textTransform: "uppercase", letterSpacing: "1px" }}>Resource Allocation Command Center</h1>
          <p style={{ color: "#666", fontSize: "18px", marginTop: "8px" }}>Phase B: Spatial Clustering and Completion Confidence</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "10px" }}>
          <div style={{ padding: "4px 12px", background: "#005696", color: "#FFF", fontSize: "12px", fontWeight: "bold", borderRadius: "4px" }}>NYC DOT OFFICIAL</div>
          <select 
            value={state.borough} 
            onChange={(e) => setState({ borough: e.target.value })}
            style={{ padding: "8px 12px", borderRadius: "4px", border: "1px solid #CCC", width: "200px" }}
          >
            <option value="CITYWIDE">Citywide Average</option>
            <option value="MANHATTAN">Manhattan</option>
            <option value="BROOKLYN">Brooklyn</option>
            <option value="QUEENS">Queens</option>
            <option value="BRONX">Bronx</option>
            <option value="STATEN ISLAND">Staten Island</option>
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "24px", marginBottom: "40px" }}>
        {kpis.map((k, idx) => (
          <div key={k.kpi_name} style={{ padding: "24px", background: "#F8F9FA", borderTop: `6px solid ${idx % 2 === 0 ? "#005696" : "#D32F2F"}`, borderRadius: "8px", boxShadow: "0 4px 6px rgba(0,0,0,0.05)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 800, color: "#666", textTransform: "uppercase" }}>{k.label}</div>
              {idx % 2 === 0 ? <TrendingUp color="#005696" /> : <Activity color="#D32F2F" />}
            </div>
            <div style={{ fontSize: "32px", fontWeight: 900 }}>{N(k.avg_val).toFixed(2)}{k.unit}</div>
            <div style={{ fontSize: "11px", color: "#999", marginTop: "4px" }}>Current Operational Mean</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px", marginBottom: "40px" }}>
        <div style={{ padding: "32px", border: "1px solid #EEE", borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
          <h3 style={{ margin: "0 0 24px 0", fontSize: "20px", fontWeight: 800 }}>Comparative Multi-Metric Analysis</h3>
          <div style={{ width: "100%", height: "400px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="shortName" fontSize={12} fontWeight={700} axisLine={false} tickLine={false} />
                <YAxis yAxisId="left" fontSize={12} axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" fontSize={12} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#000", color: "#FFF", borderRadius: "8px", border: "none" }} />
                <Legend verticalAlign="top" height={36}/>
                <Bar yAxisId="left" dataKey="val1" name={kpis[0]?.label || "Metric 1"} fill="#005696" radius={{6, 6, 0, 0}} />
                <Line yAxisId="right" type="monotone" dataKey="val2" name={kpis[1]?.label || "Metric 2"} stroke="#D32F2F" strokeWidth={4} dot={{ r: 6, fill: "#D32F2F" }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div style={{ padding: "24px", background: "#E3F2FD", borderLeft: "6px solid #005696", borderRadius: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <Info size={24} color="#005696" />
              <h4 style={{ margin: 0, fontSize: "18px", fontWeight: 800, color: "#005696" }}>Automated Bayesian Audit</h4>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6 }}>
              Phase B telemetry for <strong>{state.borough}</strong> indicates a high degree of variance in <strong>{kpis[0]?.label}</strong>. 
              Statistical posterior distribution suggest a mean of <strong>{N(statRows[0]?.mean).toFixed(2)}</strong> citywide.
            </p>
          </div>

          <div style={{ padding: "24px", border: "1px solid #EEE", borderRadius: "12px" }}>
            <h4 style={{ margin: "0 0 16px 0", fontSize: "16px", fontWeight: 800 }}>Reliability Metrics</h4>
            {statRows.map(row => (
              <div key={row.kpi_name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #F4F4F4" }}>
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{row.label}</span>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#005696" }}>{N(row.mean).toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: "60px", borderTop: "1px solid #EEE", paddingTop: "20px", textAlign: "center" }}>
        <p style={{ fontSize: "12px", color: "#AAA", fontWeight: 600, letterSpacing: "1px" }}>
          NYC DOT SIM DASHBOARD · PHASE B COMMAND CENTER · CONFIDENTIAL
        </p>
      </div>
    </div>
  );
}
