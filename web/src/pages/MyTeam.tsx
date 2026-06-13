import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Badge,
  Select,
  Tabs,
  SimpleGrid,
  Loader,
  Center,
  Progress,
} from "@mantine/core";
import { IconUsers, IconCoin } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../components/DataGrid";
import { seasonApi } from "../api/season";
import {
  myTeamApi,
  type MyTeamPlayer,
  type RetentionRisk,
  type PortalEntry,
} from "../api/myteam";

const money = (n: number) => `$${(n / 1000).toFixed(0)}k`;

export function MyTeam() {
  const [sid, setSid] = useState<string | null>(null);

  // Only college sessions with a human team can use the roster builder.
  const sessions = useQuery({
    queryKey: ["college-sessions"],
    queryFn: seasonApi.listSessions,
  });
  const eligible = (sessions.data ?? []).filter((s) => s.human_teams.length > 0);

  const dash = useQuery({
    queryKey: ["my-team", sid],
    queryFn: () => myTeamApi.dashboard(sid!),
    enabled: !!sid,
  });
  const retention = useQuery({
    queryKey: ["my-team-retention", sid],
    queryFn: () => myTeamApi.retention(sid!),
    enabled: !!sid,
  });
  const portal = useQuery({
    queryKey: ["my-team-portal", sid],
    queryFn: () => myTeamApi.portal(sid!),
    enabled: !!sid,
  });

  const rosterCols = useMemo<MRT_ColumnDef<MyTeamPlayer>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "position", header: "Pos", size: 70, filterVariant: "select" },
      { accessorKey: "year", header: "Yr", size: 90 },
      {
        accessorKey: "overall",
        header: "OVR",
        size: 70,
        Cell: ({ cell }) => <Badge variant="light">{cell.getValue<number>()}</Badge>,
      },
      { accessorKey: "potential", header: "POT", size: 70 },
    ],
    [],
  );

  const retentionCols = useMemo<MRT_ColumnDef<RetentionRisk>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "year", header: "Yr", size: 90 },
      { accessorKey: "overall", header: "OVR", size: 70 },
      {
        accessorKey: "retained",
        header: "Status",
        size: 100,
        Cell: ({ cell }) =>
          cell.getValue<boolean>() ? (
            <Badge color="teal" variant="light">
              retained
            </Badge>
          ) : (
            <Badge color="orange" variant="light">
              at risk
            </Badge>
          ),
      },
    ],
    [],
  );

  const portalCols = useMemo<MRT_ColumnDef<PortalEntry>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "position", header: "Pos", size: 70, filterVariant: "select" },
      { accessorKey: "year", header: "Yr", size: 90 },
      {
        accessorKey: "overall",
        header: "OVR",
        size: 70,
        Cell: ({ cell }) => <Badge variant="light">{cell.getValue<number>()}</Badge>,
      },
      {
        accessorKey: "my_bid",
        header: "My Bid",
        size: 100,
        Cell: ({ cell }) => {
          const v = cell.getValue<number | null>();
          return v ? money(v) : <Text size="sm" c="dimmed">—</Text>;
        },
      },
    ],
    [],
  );

  const rosterTable = useDataGrid(rosterCols, dash.data?.roster ?? [], {
    isLoading: dash.isLoading,
    sorting: [{ id: "overall", desc: true }],
  });
  const retentionTable = useDataGrid(retentionCols, retention.data?.risks ?? [], {
    isLoading: retention.isLoading,
  });
  const portalTable = useDataGrid(portalCols, portal.data?.available ?? [], {
    isLoading: portal.isLoading,
    sorting: [{ id: "overall", desc: true }],
  });

  return (
    <Stack gap="md">
      <Stack gap={2}>
        <Title order={2}>My Team</Title>
        <Text c="dimmed" size="sm">
          Roster builder — NIL budget, retention, and the transfer portal for your team.
        </Text>
      </Stack>

      <Card>
        <Select
          label="Team"
          placeholder={eligible.length ? "Pick your team's season" : "No seasons with a chosen team"}
          data={eligible.map((s) => ({
            value: s.session_id,
            label: `${s.human_teams[0]} — ${s.name}`,
          }))}
          value={sid}
          onChange={setSid}
          disabled={sessions.isLoading || eligible.length === 0}
          searchable
        />
        {!sessions.isLoading && eligible.length === 0 && (
          <Text size="xs" c="dimmed" mt="xs">
            Create a season with "Your team" set (New Season → pick a team) to use the builder.
          </Text>
        )}
      </Card>

      {sid && dash.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {sid && dash.data && (
        <>
          <Group gap="xs">
            <IconUsers size={20} color="var(--mantine-color-indigo-6)" />
            <Title order={3}>{dash.data.team_name}</Title>
            <Badge variant="light" color="grape">
              Prestige {dash.data.prestige}
            </Badge>
            <Badge variant="light" color="gray">
              {dash.data.roster_size} players
            </Badge>
          </Group>

          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            {(
              [
                ["Recruiting", dash.data.nil_budget.recruiting_remaining, dash.data.nil_budget.recruiting_pool],
                ["Portal", dash.data.nil_budget.portal_remaining, dash.data.nil_budget.portal_pool],
                ["Retention", dash.data.nil_budget.retention_remaining, dash.data.nil_budget.retention_pool],
              ] as [string, number, number][]
            ).map(([label, remaining, pool]) => (
              <Card key={label} padding="md">
                <Group gap={6} mb={4}>
                  <IconCoin size={14} color="var(--mantine-color-yellow-6)" />
                  <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                    {label} NIL
                  </Text>
                </Group>
                <Text size="lg" fw={800}>
                  {money(remaining)}{" "}
                  <Text span size="sm" c="dimmed" fw={400}>
                    / {money(pool)}
                  </Text>
                </Text>
                <Progress
                  mt={6}
                  value={pool ? (remaining / pool) * 100 : 0}
                  size="sm"
                  radius="xl"
                  color="yellow"
                />
              </Card>
            ))}
          </SimpleGrid>

          <Tabs defaultValue="roster" keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="roster">Roster</Tabs.Tab>
              <Tabs.Tab value="retention">
                Retention
                {dash.data.retention_risks_count > 0 && (
                  <Badge size="xs" color="orange" variant="light" ml={6}>
                    {dash.data.retention_risks_count}
                  </Badge>
                )}
              </Tabs.Tab>
              <Tabs.Tab value="portal">
                Portal
                {dash.data.portal_size > 0 && (
                  <Badge size="xs" variant="light" ml={6}>
                    {dash.data.portal_size}
                  </Badge>
                )}
              </Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="roster" pt="md">
              <MantineReactTable table={rosterTable} />
            </Tabs.Panel>
            <Tabs.Panel value="retention" pt="md">
              <MantineReactTable table={retentionTable} />
            </Tabs.Panel>
            <Tabs.Panel value="portal" pt="md">
              <MantineReactTable table={portalTable} />
            </Tabs.Panel>
          </Tabs>
        </>
      )}
    </Stack>
  );
}
