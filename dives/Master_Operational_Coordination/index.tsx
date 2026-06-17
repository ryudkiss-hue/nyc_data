import { useSQLQuery } from "@motherduck/react-sql-query";
import { 
  Card, Text, Title, Group, Badge, Loader, Alert, Stack, Divider, Container, 
  SimpleGrid, Paper, ThemeIcon, Table
} from "@mantine/core";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Legend, ComposedChart, Line
} from "recharts";
import { 
  IconAlertCircle, IconCrane, IconChecklist, IconBinary, IconScale 
} from "@tabler/icons-react";

export const REQUIRED_DATABASES = [
  { type: 'database', path: 'md:nyc_mission_control', alias: 'nyc_mission_control' }
];

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function OperationalCoordinationMaster() {
  // Query 1: Borough Coordination Baseline
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

  return (
    <Container fluid p="xl" style={{ background: "#FFFFFF", minHeight: "100vh" }}>
      <Stack spacing="lg">
        <Group position="apart">
          <div>
            <Title order={1} style={{ color: "#000000", fontWeight: 900, textTransform: "uppercase" }}>
              Operational Coordination Scorecard
            </Title>
            <Text c="dimmed" size="lg">
              Balancing active construction volume against pending infrastructure defects to optimize repair windows.
            </Text>
          </div>
          <Badge color="orange" size="xl" radius="sm" variant="filled">CAPITAL COORDINATION</Badge>
        </Group>

        <Divider color="#E0E0E0" />

        {isLoading ? (
          <Group position="center" my="xl">
            <Loader color="orange" variant="bars" />
            <Text weight={700}>Synthesizing Multi-Agency Permit Clusters...</Text>
          </Group>
        ) : (
          <>
            <SimpleGrid cols={2} breakpoints={[{ maxWidth: 'md', cols: 1 }]}>
              <Card withBorder radius="md" p="lg" shadow="sm">
                <Title order={3} mb="xl">Permit vs. Violation Density</Title>
                <ResponsiveContainer width="100%" height={350}>
                  <ComposedChart data={rows} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="borough" />
                    <YAxis yAxisId="left" orientation="left" label={{ value: 'Units', angle: -90, position: 'insideLeft' }} />
                    <YAxis yAxisId="right" orientation="right" label={{ value: 'Coordination %', angle: 90, position: 'insideRight' }} />
                    <Tooltip contentStyle={{ backgroundColor: "#000", color: "#FFF", borderRadius: "8px" }} />
                    <Legend />
                    <Bar yAxisId="left" dataKey="open_violations" name="Open Violations" fill="#005696" />
                    <Bar yAxisId="left" dataKey="active_permits" name="Active Permits" fill="#FF8C00" />
                    <Line yAxisId="right" type="monotone" dataKey="coordination_density" name="Coordination Index" stroke="#2E7D32" strokeWidth={3} />
                  </ComposedChart>
                </ResponsiveContainer>
              </Card>

              <Stack>
                <Paper withBorder p="xl" radius="md" shadow="sm">
                  <Group>
                    <ThemeIcon size="xl" radius="md" color="orange">
                      <IconScale size="1.5rem" />
                    </ThemeIcon>
                    <div>
                      <Text size="xs" color="dimmed" weight={700} tt="uppercase">Citywide Coordination Gap</Text>
                      <Title order={2}>High Variance</Title>
                    </div>
                  </Group>
                  <Text size="sm" mt="md">
                    The <strong>Coordination Index</strong> represents the ratio of active construction permits to pending sidewalk violations. 
                    A higher index indicates potential for "Dig Once" optimization where sidewalk repairs can be bundled with street cuts.
                  </Text>
                </Paper>

                <Alert icon={<IconCrane size="1rem" />} title="Resource Allocation Risk" color="orange" variant="light">
                  <Text size="sm">
                    <strong>Coordination Alert:</strong> Regions with low permit density but high violation counts represent "Maintenance Deserts" where capital projects are not adequately addressing subsurface utility needs alongside surface accessibility.
                  </Text>
                </Alert>

                <Card withBorder radius="md">
                  <Title order={4} mb="xs">Borough Scorecard</Title>
                  <Table verticalSpacing="sm">
                    <thead>
                      <tr>
                        <th>Borough</th>
                        <th>Vio/Perm Ratio</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(r => (
                        <tr key={r.borough}>
                          <td>{r.borough}</td>
                          <td>{(r.open_violations / (r.active_permits || 1)).toFixed(1)}x</td>
                          <td>
                            <Badge color={r.coordination_density > 10 ? "green" : "red"} variant="outline">
                              {r.coordination_density > 10 ? "OPTIMIZED" : "STALLED"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </Card>
              </Stack>
            </SimpleGrid>
          </>
        )}
      </Stack>
    </Container>
  );
}
