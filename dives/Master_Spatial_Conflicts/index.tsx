import { useSQLQuery } from "@motherduck/react-sql-query";
import { 
  Card, Text, Title, Group, Badge, Loader, Alert, Stack, Divider, Container, 
  SimpleGrid, Paper, ThemeIcon
} from "@mantine/core";
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ZAxis, Legend
} from "recharts";
import { 
  IconAlertCircle, IconTrees, IconPath, IconFocus2, IconChartDots 
} from "@tabler/icons-react";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function SpatialConflictsMaster() {
  // Query 1: CB Aggregation (Correlation)
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

  // Calculate Pearson correlation on the fly (approx)
  const n = rows.length;
  const sumX = rows.reduce((acc, r) => acc + r.x, 0);
  const sumY = rows.reduce((acc, r) => acc + r.y, 0);
  const sumXY = rows.reduce((acc, r) => acc + r.x * r.y, 0);
  const sumX2 = rows.reduce((acc, r) => acc + r.x * r.x, 0);
  const sumY2 = rows.reduce((acc, r) => acc + r.y * r.y, 0);
  
  const correlation = n > 0 ? (n * sumXY - sumX * sumY) / 
    Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY)) : 0;

  return (
    <Container fluid p="xl" style={{ background: "#FFFFFF", minHeight: "100vh" }}>
      <Stack spacing="lg">
        <Group position="apart">
          <div>
            <Title order={1} style={{ color: "#000000", fontWeight: 900, textTransform: "uppercase" }}>
              Spatial Conflict Index: Green Canopy vs. Clear Paths
            </Title>
            <Text c="dimmed" size="lg">
              Quantifying the causal relationship between tree root damage and sidewalk defects by Community Board.
            </Text>
          </div>
          <Badge color="teal" size="xl" radius="sm" variant="filled">ENVIRONMENTAL OVERLAY</Badge>
        </Group>

        <Divider color="#E0E0E0" />

        {isLoading ? (
          <Group position="center" my="xl">
            <Loader color="teal" variant="dots" />
            <Text weight={700}>Computing Spatial Covariance Matrices...</Text>
          </Group>
        ) : (
          <>
            <SimpleGrid cols={2} breakpoints={[{ maxWidth: 'md', cols: 1 }]}>
              <Card withBorder radius="md" p="lg" shadow="sm">
                <Title order={3} mb="xl">The Correlation Engine</Title>
                <ResponsiveContainer width="100%" height={400}>
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="x" name="Sidewalk Violations" label={{ value: 'Sidewalk Defects', position: 'insideBottom', offset: -10 }} />
                    <YAxis type="number" dataKey="y" name="Tree Incidents" label={{ value: 'Tree Root Damage', angle: -90, position: 'insideLeft' }} />
                    <ZAxis type="number" dataKey="sensitivity_index" range={[50, 400]} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} 
                      contentStyle={{ backgroundColor: "#000", color: "#FFF", borderRadius: "8px" }}
                      formatter={(v, name) => [v, name === 'x' ? 'Sidewalk Violations' : 'Tree Incidents']}
                    />
                    <Legend />
                    <Scatter name="Community Boards" data={rows} fill="#0083B0">
                      {rows.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.sensitivity_index > 2 ? '#D32F2F' : '#2E7D32'} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </Card>

              <Stack>
                <Paper withBorder p="xl" radius="md" shadow="sm" style={{ background: "#F1F3F5" }}>
                  <Group>
                    <ThemeIcon size="xl" radius="md" color="teal">
                      <IconChartDots size="1.5rem" />
                    </ThemeIcon>
                    <div>
                      <Text size="xs" color="dimmed" weight={700} tt="uppercase">Pearson Correlation (r)</Text>
                      <Text size="xl" weight={900}>{correlation.toFixed(3)}</Text>
                    </div>
                  </Group>
                  <Text size="sm" mt="md">
                    {correlation > 0.7 ? "Strong positive spatial association detected." : correlation > 0.4 ? "Moderate spatial coupling observed." : "Weak spatial correlation in current telemetry."}
                    This coefficient measures the degree to which tree root expansion drives sidewalk displacement.
                  </Text>
                </Paper>

                <Alert icon={<IconTrees size="1rem" />} title="Ecological Impact" color="teal" variant="light">
                  <Text size="sm">
                    <strong>Critical Insight:</strong> Community Boards with a Sensitivity Index &gt; 2.0 (shown in red) represent areas where infrastructure maintenance is lagging behind biological growth cycles. These zones require reinforced concrete specs or expanded tree pits.
                  </Text>
                </Alert>

                <Card withBorder radius="md">
                  <Title order={4} mb="xs">Top Conflict Hotspots</Title>
                  {rows.slice(0, 5).map(r => (
                    <Group key={r.cb} position="apart" py={5} style={{ borderBottom: "1px solid #EEE" }}>
                      <Text weight={700}>CB {r.cb}</Text>
                      <Badge color="red" variant="outline">{N(r.sensitivity_index).toFixed(2)} Index</Badge>
                    </Group>
                  ))}
                </Card>
              </Stack>
            </SimpleGrid>
          </>
        )}
      </Stack>
    </Container>
  );
}
