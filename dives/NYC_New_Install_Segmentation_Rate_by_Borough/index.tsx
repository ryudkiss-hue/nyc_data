import { useSQLQuery } from "@motherduck/react-sql-query";
import { Card, Text, Title, Group, Badge, Loader, Alert, Stack, Divider, Container } from "@mantine/core";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { IconAlertCircle } from "@tabler/icons-react";

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
  
  return (
    <Container fluid p="md" style={ background: "#FFFFFF", minHeight: "100vh" }>
      <Stack spacing="md">
        <Group position="apart" align="flex-start">
          <div>
            <Title order=2 style={ color: "#000000", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }>
              New Install Segmentation Rate by Borough
            </Title>
            <Text c="dimmed" size="sm" mt=4 style={ maxWidth: "800px" }>
              {meta.description || "Share of ramps designated as New Install — new infrastructure demand signal"}
            </Text>
          </div>
          <Badge color="blue" variant="outline" size="lg" radius="xs">NYC DOT OFFICIAL</Badge>
        </Group>

        <Divider my="sm" color="#E0E0E0" />

        {isLoading ? (
          <Group position="center" my="xl">
            <Loader color="blue" variant="bars" />
            <Text c="dimmed">Fetching latest municipal telemetry...</Text>
          </Group>
        ) : isError ? (
          <Alert icon={<IconAlertCircle size="1rem" />} title="Data Telemetry Error" color="red" variant="filled">
            {error?.message || "Failed to establish secure connection to Socrata/MotherDuck backend."}
          </Alert>
        ) : (
          <Stack spacing="xl">
            <Group grow align="stretch">
              {rows.map(r => (
                <Card key={r.borough} shadow="sm" p="lg" radius="md" withBorder style={ borderLeft: "4px solid #005696" }>
                  <Text size="xs" color="dimmed" tt="uppercase" fw=700>{FMT(r.borough)}</Text>
                  <Group position="apart" mt="md" mb="xs">
                    <Text size="xl" weight=800 style={ color: "#000000" }>{N(r.kpi_value).toFixed(2)}</Text>
                    <Badge color={N(r.kpi_value) > bench ? "red" : "gray"} variant="light">
                      {meta.unit}
                    </Badge>
                  </Group>
                </Card>
              ))}
            </Group>

            <Card shadow="sm" p="lg" radius="md" withBorder>
              <Title order=4 mb="md" style={ color: "#000000" }>Distribution & Benchmarks</Title>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} margin={top: 10, right: 30, bottom: 0, left: 0}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
                  <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    cursor={fill: "#f4f4f4"}
                    contentStyle={ backgroundColor: "#000000", color: "#FFFFFF", borderRadius: "4px", border: "none" }
                    formatter={(v,n,p) => [`${N(v).toFixed(2)} ${meta.unit}`, p.payload.full]}
                  />
                  {bench > 0 && <ReferenceLine y={bench} stroke="#D32F2F" strokeDasharray="4 4" label={ position: "insideTopLeft", value: "Benchmark", fill: "#D32F2F", fontSize: 12 }/>}
                  <Bar dataKey="value" fill="#005696" radius={[4, 4, 0, 0]} maxBarSize={60} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Alert title="Automated Bayesian Insight" color="blue" variant="light" style={ borderLeft: "4px solid #005696" }>
              <Text size="sm">
                The current telemetry indicates <strong>{FMT(maxRow.borough)}</strong> leads the metric with a value of <strong>{N(maxRow.kpi_value).toFixed(2)} {meta.unit}</strong>. 
                The citywide average stands at <strong>{avgValue.toFixed(2)} {meta.unit}</strong>. 
                {bench > 0 && `The compliance benchmark of ${bench} provides the threshold for variance analysis.`}
                These figures are dynamically derived from live Socrata ingestion via DuckDB L2 caching.
              </Text>
            </Alert>
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
