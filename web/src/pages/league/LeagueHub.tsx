import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import {
  MantineReactTable,
  useMantineReactTable,
  type MRT_ColumnDef,
} from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Tabs,
  Button,
  Badge,
  Anchor,
  Breadcrumbs,
  Loader,
  Center,
  Card,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconPlayerTrackNext,
  IconPlayerSkipForward,
  IconChevronRight,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  seasonApi,
  type Standing,
  type Game,
  type PollEntry,
  type PlayerStat,
} from "../../api/season";

function teamLink(sid: string, team: string) {
  return `/league/${sid}/team/${encodeURIComponent(team)}`;
}

export function LeagueHub() {
  const { sessionId = "" } = useParams();
  const qc = useQueryClient();

  const status = useQuery({
    queryKey: ["season-status", sessionId],
    queryFn: () => seasonApi.status(sessionId),
  });
  const standings = useQuery({
    queryKey: ["standings", sessionId],
    queryFn: () => seasonApi.standings(sessionId),
  });
  const schedule = useQuery({
    queryKey: ["schedule", sessionId],
    queryFn: () => seasonApi.schedule(sessionId),
  });
  const polls = useQuery({
    queryKey: ["polls", sessionId],
    queryFn: () => seasonApi.polls(sessionId),
  });
  const leaders = useQuery({
    queryKey: ["leaders", sessionId],
    queryFn: () => seasonApi.leaders(sessionId),
  });

  const invalidateAll = () =>
    ["season-status", "standings", "schedule", "polls", "leaders"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k, sessionId] }),
    );

  const simWeek = useMutation({
    mutationFn: () => seasonApi.simWeek(sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated a week", color: "indigo" });
      invalidateAll();
    },
    onError: () => notifications.show({ message: "Sim failed", color: "red" }),
  });
  const simRest = useMutation({
    mutationFn: () => seasonApi.simRest(sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated rest of season", color: "indigo" });
      invalidateAll();
    },
    onError: () => notifications.show({ message: "Sim failed", color: "red" }),
  });

  // ── Columns ──────────────────────────────────────────────────
  const standingsCols = useMemo<MRT_ColumnDef<Standing>[]>(
    () => [
      {
        accessorKey: "team_name",
        header: "Team",
        Cell: ({ row }) => (
          <Anchor component={Link} to={teamLink(sessionId, row.original.team_name)} fw={600}>
            {row.original.team_name}
          </Anchor>
        ),
      },
      { accessorKey: "conference", header: "Conf", size: 90 },
      {
        header: "Record",
        id: "record",
        size: 90,
        accessorFn: (r) => `${r.wins}-${r.losses}${r.ties ? `-${r.ties}` : ""}`,
        sortingFn: (a, b) => a.original.win_percentage - b.original.win_percentage,
      },
      {
        accessorKey: "conf_wins",
        header: "Conf",
        size: 80,
        accessorFn: (r) => `${r.conf_wins}-${r.conf_losses}`,
      },
      { accessorKey: "points_for", header: "PF", size: 70 },
      { accessorKey: "points_against", header: "PA", size: 70 },
      {
        accessorKey: "point_differential",
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
      {
        header: "Luck",
        id: "luck",
        size: 80,
        accessorFn: (r) => r.dtw?.luck_differential ?? 0,
        Cell: ({ cell }) => {
          const v = cell.getValue<number>();
          return (
            <Text size="sm" c={v > 0 ? "orange" : v < 0 ? "blue" : "dimmed"}>
              {v > 0 ? "+" : ""}
              {v}
            </Text>
          );
        },
      },
    ],
    [sessionId],
  );

  const scheduleCols = useMemo<MRT_ColumnDef<Game>[]>(
    () => [
      { accessorKey: "week", header: "Wk", size: 60, filterVariant: "select" },
      {
        header: "Matchup",
        id: "matchup",
        accessorFn: (g) => `${g.away_team} @ ${g.home_team}`,
        Cell: ({ row }) => {
          const g = row.original;
          return (
            <Group gap={6} wrap="nowrap">
              <Anchor component={Link} to={teamLink(sessionId, g.away_team)} size="sm">
                {g.away_team}
              </Anchor>
              <Text size="xs" c="dimmed">
                @
              </Text>
              <Anchor component={Link} to={teamLink(sessionId, g.home_team)} size="sm">
                {g.home_team}
              </Anchor>
              {g.is_rivalry_game && (
                <Badge size="xs" color="orange" variant="light">
                  rivalry
                </Badge>
              )}
            </Group>
          );
        },
      },
      {
        header: "Score",
        id: "score",
        size: 110,
        accessorFn: (g) =>
          g.completed ? `${g.away_score}-${g.home_score}` : "",
        Cell: ({ row }) => {
          const g = row.original;
          if (!g.completed)
            return (
              <Badge size="xs" variant="light" color="gray">
                scheduled
              </Badge>
            );
          const awayWon = g.away_score > g.home_score;
          return (
            <Text size="sm" ff="monospace">
              <b style={{ color: awayWon ? "var(--mantine-color-teal-7)" : undefined }}>
                {g.away_score}
              </b>{" "}
              –{" "}
              <b style={{ color: !awayWon ? "var(--mantine-color-teal-7)" : undefined }}>
                {g.home_score}
              </b>
            </Text>
          );
        },
      },
      {
        accessorKey: "is_conference_game",
        header: "Conf",
        size: 70,
        Cell: ({ cell }) => (cell.getValue<boolean>() ? "✓" : ""),
      },
    ],
    [sessionId],
  );

  const pollCols = useMemo<MRT_ColumnDef<PollEntry>[]>(
    () => [
      { accessorKey: "rank", header: "#", size: 50 },
      {
        accessorKey: "team_name",
        header: "Team",
        Cell: ({ row }) => (
          <Anchor component={Link} to={teamLink(sessionId, row.original.team_name)} fw={600}>
            {row.original.team_name}
          </Anchor>
        ),
      },
      { accessorKey: "record", header: "Record", size: 90 },
      { accessorKey: "conference", header: "Conf", size: 90 },
      {
        accessorKey: "rank_change",
        header: "Δ",
        size: 60,
        Cell: ({ cell }) => {
          const v = cell.getValue<number>();
          if (!v) return <Text size="sm" c="dimmed">–</Text>;
          return (
            <Text size="sm" c={v > 0 ? "teal" : "red"}>
              {v > 0 ? `▲${v}` : `▼${Math.abs(v)}`}
            </Text>
          );
        },
      },
      { accessorKey: "power_index", header: "Power", size: 90 },
      { accessorKey: "quality_wins", header: "Q-Wins", size: 80 },
    ],
    [sessionId],
  );

  const leaderCols = useMemo<MRT_ColumnDef<PlayerStat>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      {
        accessorKey: "team",
        header: "Team",
        size: 120,
        Cell: ({ row }) => (
          <Anchor component={Link} to={teamLink(sessionId, row.original.team)} size="sm">
            {row.original.team}
          </Anchor>
        ),
      },
      { accessorKey: "tag", header: "Pos", size: 70 },
      { accessorKey: "touches", header: "Tch", size: 70 },
      { accessorKey: "yards", header: "Yds", size: 80 },
      { accessorKey: "tds", header: "TD", size: 60 },
      { accessorKey: "yards_per_touch", header: "Y/Tch", size: 80 },
      { accessorKey: "tackles", header: "Tkl", size: 70 },
    ],
    [sessionId],
  );

  const standingsTable = useGrid(standingsCols, standings.data ?? [], standings.isLoading, {
    sorting: [{ id: "record", desc: true }],
  });
  const scheduleTable = useGrid(scheduleCols, schedule.data ?? [], schedule.isLoading, {
    sorting: [{ id: "week", desc: false }],
  });
  const pollTable = useGrid(pollCols, polls.data ?? [], polls.isLoading, {
    sorting: [{ id: "rank", desc: false }],
  });
  const leaderTable = useGrid(leaderCols, leaders.data ?? [], leaders.isLoading, {
    sorting: [{ id: "yards", desc: true }],
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
          This season isn't loaded (sessions are in-memory and expire). Pick another from the{" "}
          <Anchor component={Link} to="/league">
            League Hub
          </Anchor>
          .
        </Text>
      </Card>
    );
  }

  const s = status.data!;

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Text size="sm">{s.name}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>{s.name}</Title>
          <Group gap="xs">
            <Badge variant="light">{s.phase.replace(/_/g, " ")}</Badge>
            <Text size="sm" c="dimmed">
              Week {s.current_week} / {s.total_weeks} · {s.games_played}/{s.total_games} games
            </Text>
            {s.champion && (
              <Badge variant="light" color="teal">
                🏆 {s.champion}
              </Badge>
            )}
          </Group>
        </Stack>
        <Group gap="xs">
          <Button
            leftSection={<IconPlayerTrackNext size={16} />}
            onClick={() => simWeek.mutate()}
            loading={simWeek.isPending}
            disabled={s.games_played >= s.total_games}
          >
            Sim Week
          </Button>
          <Button
            variant="default"
            leftSection={<IconPlayerSkipForward size={16} />}
            onClick={() => simRest.mutate()}
            loading={simRest.isPending}
            disabled={s.games_played >= s.total_games}
          >
            Sim Rest
          </Button>
        </Group>
      </Group>

      <Tabs defaultValue="standings" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="standings">Standings</Tabs.Tab>
          <Tabs.Tab value="schedule">Schedule</Tabs.Tab>
          <Tabs.Tab value="polls">Polls</Tabs.Tab>
          <Tabs.Tab value="leaders">Leaders</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="standings" pt="md">
          <MantineReactTable table={standingsTable} />
        </Tabs.Panel>
        <Tabs.Panel value="schedule" pt="md">
          <MantineReactTable table={scheduleTable} />
        </Tabs.Panel>
        <Tabs.Panel value="polls" pt="md">
          <MantineReactTable table={pollTable} />
        </Tabs.Panel>
        <Tabs.Panel value="leaders" pt="md">
          <MantineReactTable table={leaderTable} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

// Shared dense-grid config so every tab looks and behaves the same.
function useGrid<T extends Record<string, any>>(
  columns: MRT_ColumnDef<T>[],
  data: T[],
  isLoading: boolean,
  initial?: { sorting?: { id: string; desc: boolean }[] },
) {
  return useMantineReactTable({
    columns,
    data,
    state: { isLoading },
    enableFacetedValues: true,
    enablePagination: data.length > 50,
    initialState: {
      density: "xs",
      pagination: { pageSize: 50, pageIndex: 0 },
      showGlobalFilter: true,
      ...(initial?.sorting ? { sorting: initial.sorting } : {}),
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    mantineTableContainerProps: { style: { maxHeight: "65vh" } },
  });
}
