import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Tabs,
  Button,
  Badge,
  Breadcrumbs,
  Anchor,
  Loader,
  Center,
  Card,
  Select,
  SimpleGrid,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconChevronRight,
  IconPlayerTrackNext,
  IconPlayerSkipForward,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import {
  proApi,
  PRO_LEAGUE_NAME,
  type ProStandingRow,
  type ProGame,
  type ProStatLeader,
} from "../../api/pro";

const STAT_CATEGORIES = [
  "rushing",
  "kick_pass",
  "scoring",
  "total_yards",
  "defense",
  "sacks",
  "kick_returns",
  "laterals",
  "keeper",
];

export function ProHub() {
  const { league = "", sessionId = "" } = useParams();
  const qc = useQueryClient();
  const [statCat, setStatCat] = useState("scoring");

  const status = useQuery({
    queryKey: ["pro-status", league, sessionId],
    queryFn: () => proApi.status(league, sessionId),
  });
  const standings = useQuery({
    queryKey: ["pro-standings", league, sessionId],
    queryFn: () => proApi.standings(league, sessionId),
  });
  const schedule = useQuery({
    queryKey: ["pro-schedule", league, sessionId],
    queryFn: () => proApi.schedule(league, sessionId),
  });
  const stats = useQuery({
    queryKey: ["pro-stats", league, sessionId],
    queryFn: () => proApi.stats(league, sessionId),
  });
  const bracket = useQuery({
    queryKey: ["pro-bracket", league, sessionId],
    queryFn: () => proApi.bracket(league, sessionId),
  });

  const invalidate = () =>
    ["pro-status", "pro-standings", "pro-schedule", "pro-stats", "pro-bracket"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k, league, sessionId] }),
    );

  const simWeek = useMutation({
    mutationFn: () => proApi.simWeek(league, sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated a week", color: "teal" });
      invalidate();
    },
  });
  const simAll = useMutation({
    mutationFn: () => proApi.simAll(league, sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated remaining season", color: "teal" });
      invalidate();
    },
  });

  const standingsCols = useMemo<MRT_ColumnDef<ProStandingRow>[]>(
    () => [
      { accessorKey: "division", header: "Div", size: 110, filterVariant: "select" },
      { accessorKey: "team_name", header: "Team" },
      {
        header: "Record",
        id: "record",
        size: 90,
        accessorFn: (r) => `${r.wins}-${r.losses}${r.ties ? `-${r.ties}` : ""}`,
        sortingFn: (a, b) => a.original.pct - b.original.pct,
      },
      { accessorKey: "pf", header: "PF", size: 70 },
      { accessorKey: "pa", header: "PA", size: 70 },
      {
        accessorKey: "diff",
        header: "Diff",
        size: 80,
        Cell: ({ cell }) => {
          const v = cell.getValue<number>();
          return (
            <Text size="sm" c={v > 0 ? "teal" : v < 0 ? "red" : undefined}>
              {v > 0 ? "+" : ""}
              {v}
            </Text>
          );
        },
      },
      { accessorKey: "streak", header: "Strk", size: 70 },
      { accessorKey: "last_5", header: "L5", size: 80 },
    ],
    [],
  );

  const scheduleCols = useMemo<MRT_ColumnDef<ProGame>[]>(
    () => [
      { accessorKey: "week", header: "Wk", size: 60, filterVariant: "select" },
      {
        header: "Matchup",
        id: "matchup",
        accessorFn: (g) => `${g.away_name} @ ${g.home_name}`,
      },
      {
        header: "Score",
        id: "score",
        size: 110,
        accessorFn: (g) => (g.completed ? `${g.away_score}-${g.home_score}` : ""),
        Cell: ({ row }) => {
          const g = row.original;
          if (!g.completed)
            return (
              <Badge size="xs" variant="light" color="gray">
                scheduled
              </Badge>
            );
          return (
            <Text size="sm" ff="monospace">
              {g.away_score} – {g.home_score}
            </Text>
          );
        },
      },
    ],
    [],
  );

  const statCols = useMemo<MRT_ColumnDef<ProStatLeader>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "team", header: "Team", size: 130 },
      { accessorKey: "position", header: "Pos", size: 70 },
      {
        accessorKey: "value",
        header: "Value",
        size: 90,
        Cell: ({ cell }) => <b>{cell.getValue<number>()}</b>,
      },
      { accessorKey: "games", header: "G", size: 60 },
    ],
    [],
  );

  const standingsTable = useDataGrid(standingsCols, standings.data ?? [], {
    isLoading: standings.isLoading,
    sorting: [{ id: "record", desc: true }],
  });
  const scheduleTable = useDataGrid(scheduleCols, schedule.data ?? [], {
    isLoading: schedule.isLoading,
    sorting: [{ id: "week", desc: false }],
  });
  const statRows = stats.data?.[statCat] ?? [];
  const statTable = useDataGrid(statCols, statRows, {
    isLoading: stats.isLoading,
    sorting: [{ id: "value", desc: true }],
  });

  if (status.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (status.isError) {
    return (
      <Card>
        <Text c="red">
          This pro season isn't loaded.{" "}
          <Anchor component={Link} to="/pro">
            Back to Pro Leagues
          </Anchor>
        </Text>
      </Card>
    );
  }

  const st = status.data!;
  const done = st.current_week >= st.total_weeks && st.phase !== "playoffs";

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/pro" size="sm">
          Pro Leagues
        </Anchor>
        <Text size="sm">{PRO_LEAGUE_NAME[league] ?? league}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>{PRO_LEAGUE_NAME[league] ?? league}</Title>
          <Group gap="xs">
            <Badge variant="light" color="teal">
              {st.phase.replace(/_/g, " ")}
            </Badge>
            <Text size="sm" c="dimmed">
              Week {st.current_week} / {st.total_weeks}
            </Text>
            {st.champion_name && (
              <Badge variant="light" color="teal">
                🏆 {st.champion_name}
              </Badge>
            )}
          </Group>
        </Stack>
        <Group gap="xs">
          <Button
            leftSection={<IconPlayerTrackNext size={16} />}
            color="teal"
            onClick={() => simWeek.mutate()}
            loading={simWeek.isPending}
            disabled={done}
          >
            Sim Week
          </Button>
          <Button
            variant="default"
            leftSection={<IconPlayerSkipForward size={16} />}
            onClick={() => simAll.mutate()}
            loading={simAll.isPending}
            disabled={done}
          >
            Sim Rest
          </Button>
        </Group>
      </Group>

      <Tabs defaultValue="standings" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="standings">Standings</Tabs.Tab>
          <Tabs.Tab value="schedule">Schedule</Tabs.Tab>
          <Tabs.Tab value="leaders">Leaders</Tabs.Tab>
          <Tabs.Tab value="playoffs">Playoffs</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="standings" pt="md">
          <MantineReactTable table={standingsTable} />
        </Tabs.Panel>
        <Tabs.Panel value="schedule" pt="md">
          <MantineReactTable table={scheduleTable} />
        </Tabs.Panel>
        <Tabs.Panel value="leaders" pt="md">
          <Select
            label="Category"
            data={STAT_CATEGORIES.map((c) => ({ value: c, label: c.replace(/_/g, " ") }))}
            value={statCat}
            onChange={(v) => setStatCat(v ?? "scoring")}
            w={200}
            mb="sm"
          />
          <MantineReactTable table={statTable} />
        </Tabs.Panel>
        <Tabs.Panel value="playoffs" pt="md">
          {bracket.data && bracket.data.rounds.length > 0 ? (
            <Stack gap="md">
              {bracket.data.champion_name && (
                <Badge size="lg" color="teal" variant="light">
                  🏆 Champion: {bracket.data.champion_name}
                </Badge>
              )}
              {bracket.data.rounds.map((rd) => (
                <Card key={rd.round_name}>
                  <Text fw={600} mb="sm">
                    {rd.round_name}
                  </Text>
                  <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
                    {rd.matchups.map((m, i) => (
                      <Card key={i} padding="sm" withBorder>
                        <Group justify="space-between">
                          <Text size="sm" fw={m.winner === m.away?.team_key ? 700 : 400}>
                            {m.away?.team_name ?? "TBD"}
                          </Text>
                          <Text size="sm" ff="monospace">
                            {m.away_score ?? ""}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm" fw={m.winner === m.home?.team_key ? 700 : 400}>
                            {m.home?.team_name ?? "TBD"}
                          </Text>
                          <Text size="sm" ff="monospace">
                            {m.home_score ?? ""}
                          </Text>
                        </Group>
                      </Card>
                    ))}
                  </SimpleGrid>
                </Card>
              ))}
            </Stack>
          ) : (
            <Text c="dimmed">No playoff bracket yet — finish the regular season.</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
