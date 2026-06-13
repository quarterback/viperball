import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Badge,
  Button,
  Tabs,
  Breadcrumbs,
  Anchor,
  Loader,
  Center,
  Card,
  Modal,
  Table,
  SimpleGrid,
  Paper,
  Divider,
  Tooltip,
} from "@mantine/core";
import {
  IconChevronRight,
  IconPlayerTrackNext,
  IconPlayerSkipForward,
  IconCalendarPlus,
  IconTrophy,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../../components/DataGrid";
import {
  wvlApi,
  type WVLStandRow,
  type WVLPlayer,
  type WVLCareerSeason,
} from "../../api/wvl";

// ── Player career modal: the payoff — one card, college + pro, all seasons ──
function PlayerCareerModal({
  leagueId,
  playerId,
  onClose,
}: {
  leagueId: string;
  playerId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["wvl-player", leagueId, playerId],
    queryFn: () => wvlApi.player(leagueId, playerId!),
    enabled: !!playerId,
  });
  const seasons: WVLCareerSeason[] = Array.isArray(data?.career_seasons)
    ? (data!.career_seasons as WVLCareerSeason[])
    : [];

  return (
    <Modal opened={!!playerId} onClose={onClose} size="lg" title="Career" centered>
      {isLoading || !data ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : (
        <Stack gap="md">
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={3}>{data.name}</Title>
              <Text size="sm" c="dimmed">
                {data.position} · {data.archetype} · {data.nationality}
              </Text>
              <Group gap="xs" mt={4}>
                <Badge variant="light">OVR {data.overall}</Badge>
                {data.age != null && <Badge variant="light" color="gray">Age {data.age}</Badge>}
                <Badge variant="light" color={data.status === "retired" ? "gray" : "teal"}>
                  {data.status}
                </Badge>
                <Badge variant="light" color="orange">{data.club}</Badge>
              </Group>
            </div>
            <Paper p="sm" withBorder>
              <Text size="xs" c="dimmed" ta="center">CAREER</Text>
              <Group gap="lg">
                <div>
                  <Text fw={700} size="lg" ta="center">{data.career_yards}</Text>
                  <Text size="xs" c="dimmed" ta="center">yards</Text>
                </div>
                <div>
                  <Text fw={700} size="lg" ta="center">{data.career_touchdowns}</Text>
                  <Text size="xs" c="dimmed" ta="center">TD</Text>
                </div>
                <div>
                  <Text fw={700} size="lg" ta="center">{data.career_games}</Text>
                  <Text size="xs" c="dimmed" ta="center">games</Text>
                </div>
              </Group>
            </Paper>
          </Group>

          <Divider label="Season by season" labelPosition="left" />
          <Table striped withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>League</Table.Th>
                <Table.Th>Team</Table.Th>
                <Table.Th ta="right">G</Table.Th>
                <Table.Th ta="right">Yards</Table.Th>
                <Table.Th ta="right">TD</Table.Th>
                <Table.Th ta="right">TKL</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {seasons.map((s, i) => (
                <Table.Tr key={i}>
                  <Table.Td>{s.year}</Table.Td>
                  <Table.Td>
                    <Badge size="xs" variant="light" color={s.league === "WVL" ? "orange" : "indigo"}>
                      {s.league}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{s.team}</Table.Td>
                  <Table.Td ta="right">{s.games}</Table.Td>
                  <Table.Td ta="right">{s.yards}</Table.Td>
                  <Table.Td ta="right">{s.touchdowns}</Table.Td>
                  <Table.Td ta="right">{s.tackles}</Table.Td>
                </Table.Tr>
              ))}
              {seasons.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text c="dimmed" size="sm">No seasons recorded yet — sim some games.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Stack>
      )}
    </Modal>
  );
}

function StandingsTable({ rows }: { rows: WVLStandRow[] }) {
  const cols = useMemo<MRT_ColumnDef<WVLStandRow>[]>(
    () => [
      { accessorKey: "position", header: "#", size: 50 },
      { accessorKey: "team_name", header: "Club" },
      {
        header: "Record",
        id: "record",
        size: 100,
        accessorFn: (r) => `${r.wins}-${r.losses}${r.ties ? `-${r.ties}` : ""}`,
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
    ],
    [],
  );
  const table = useDataGrid(cols, rows, { sorting: [{ id: "position", desc: false }], maxHeight: "62vh" });
  return <MantineReactTable table={table} />;
}

function PlayersTable({
  rows,
  onPick,
}: {
  rows: WVLPlayer[];
  onPick: (pid: string) => void;
}) {
  const cols = useMemo<MRT_ColumnDef<WVLPlayer>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Player",
        Cell: ({ row }) => (
          <Anchor size="sm" onClick={() => onPick(row.original.player_id)}>
            {row.original.name}
          </Anchor>
        ),
      },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "club", header: "Club" },
      { accessorKey: "overall", header: "OVR", size: 70 },
      {
        accessorKey: "age",
        header: "Age",
        size: 60,
        Cell: ({ cell }) => cell.getValue<number | null>() ?? "—",
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 90,
        Cell: ({ cell }) => {
          const v = cell.getValue<string>();
          return (
            <Badge size="xs" variant="light" color={v === "retired" ? "gray" : "teal"}>
              {v}
            </Badge>
          );
        },
      },
      { accessorKey: "career_seasons", header: "Sea", size: 60 },
      { accessorKey: "career_games", header: "G", size: 60 },
      { accessorKey: "career_yards", header: "Career Yds", size: 110 },
      { accessorKey: "career_touchdowns", header: "Career TD", size: 100 },
      { accessorKey: "season_yards", header: "Yr Yds", size: 90 },
    ],
    [onPick],
  );
  const table = useDataGrid(cols, rows, {
    sorting: [{ id: "career_yards", desc: true }],
    maxHeight: "62vh",
    paginateOver: 40,
  });
  return <MantineReactTable table={table} />;
}

function LeadersPanel({ leagueId, onPick }: { leagueId: string; onPick: (pid: string) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["wvl-leaders", leagueId],
    queryFn: () => wvlApi.leaders(leagueId),
  });
  if (isLoading || !data)
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  const board = (title: string, list: WVLPlayer[], field: keyof WVLPlayer) => (
    <Card withBorder padding="sm">
      <Text fw={600} mb="xs">{title}</Text>
      <Stack gap={4}>
        {list.slice(0, 12).map((p, i) => (
          <Group key={p.player_id} justify="space-between" wrap="nowrap">
            <Anchor size="sm" onClick={() => onPick(p.player_id)} lineClamp={1}>
              {i + 1}. {p.name}
            </Anchor>
            <Group gap={6} wrap="nowrap">
              <Text size="xs" c="dimmed">{p.club}</Text>
              <Text size="sm" fw={600}>{p[field] as number}</Text>
            </Group>
          </Group>
        ))}
        {list.length === 0 && <Text size="sm" c="dimmed">No data yet.</Text>}
      </Stack>
    </Card>
  );
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      {board("Career Yards", data.career_yards, "career_yards")}
      {board("Career Touchdowns", data.career_touchdowns, "career_touchdowns")}
      {board("Season Yards", data.season_yards, "season_yards")}
      {board("Season Touchdowns", data.season_tds, "season_tds")}
    </SimpleGrid>
  );
}

function SchedulePanel({ leagueId }: { leagueId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["wvl-schedule", leagueId],
    queryFn: () => wvlApi.schedule(leagueId),
  });
  if (isLoading || !data)
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  return (
    <Stack gap="sm">
      {data.map((wk) => (
        <Card key={wk.week} withBorder padding="sm">
          <Group justify="space-between" mb={6}>
            <Text fw={600} size="sm">Week {wk.week}</Text>
            {wk.played ? (
              <Badge size="xs" variant="light" color="teal">final</Badge>
            ) : (
              <Badge size="xs" variant="light" color="gray">upcoming</Badge>
            )}
          </Group>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing={6}>
            {wk.games.map((g, i) => (
              <Text key={i} size="sm">
                {g.away_name}
                {typeof g.away_score === "number" ? ` ${g.away_score}` : ""} @ {g.home_name}
                {typeof g.home_score === "number" ? ` ${g.home_score}` : ""}
              </Text>
            ))}
          </SimpleGrid>
        </Card>
      ))}
    </Stack>
  );
}

function HistoryPanel({ leagueId }: { leagueId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["wvl-history", leagueId],
    queryFn: () => wvlApi.history(leagueId),
  });
  if (isLoading || !data)
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  if (data.length === 0)
    return <Text c="dimmed" size="sm">No completed seasons yet. Finish a season, then advance.</Text>;
  return (
    <Stack gap="sm">
      {data
        .slice()
        .reverse()
        .map((h) => (
          <Card key={h.year} withBorder padding="sm">
            <Group gap="xs">
              <IconTrophy size={16} color="var(--mantine-color-yellow-6)" />
              <Text fw={600}>{h.year}</Text>
              <Text>— {h.champion ?? "—"}</Text>
            </Group>
          </Card>
        ))}
    </Stack>
  );
}

export function WVLHub() {
  const { sessionId: leagueId = "" } = useParams();
  const qc = useQueryClient();
  const [pickedPlayer, setPickedPlayer] = useState<string | null>(null);

  const status = useQuery({ queryKey: ["wvl-status", leagueId], queryFn: () => wvlApi.status(leagueId) });
  const standings = useQuery({
    queryKey: ["wvl-standings", leagueId],
    queryFn: () => wvlApi.standings(leagueId),
  });
  const players = useQuery({
    queryKey: ["wvl-players", leagueId],
    queryFn: () => wvlApi.players(leagueId),
  });

  const invalidate = () => {
    ["wvl-status", "wvl-standings", "wvl-players", "wvl-leaders", "wvl-schedule", "wvl-history"].forEach(
      (k) => qc.invalidateQueries({ queryKey: [k, leagueId] }),
    );
  };

  const simWeek = useMutation({
    mutationFn: () => wvlApi.simWeek(leagueId),
    onSuccess: (r) => {
      notifications.show({ message: `Week ${r.status.current_week} simulated`, color: "orange" });
      invalidate();
    },
    onError: (e: unknown) =>
      notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });
  const simAll = useMutation({
    mutationFn: () => wvlApi.simAll(leagueId),
    onSuccess: (r) => {
      notifications.show({
        message: r.status.champion ? `Champion: ${r.status.champion}` : "Season simulated",
        color: "orange",
      });
      invalidate();
    },
    onError: (e: unknown) =>
      notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });
  const advance = useMutation({
    mutationFn: () => wvlApi.advanceSeason(leagueId),
    onSuccess: (r) => {
      notifications.show({
        message: `Advanced to ${r.status.year} — imported ${r.result?.imported ?? 0}, retired ${r.result?.retired ?? 0}`,
        color: "indigo",
      });
      invalidate();
    },
    onError: (e: unknown) =>
      notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
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
          WVL league not found.{" "}
          <Anchor component={Link} to="/wvl">
            Back
          </Anchor>
        </Text>
      </Card>
    );
  }
  const st = status.data!;
  const seasonComplete = st.phase === "complete";

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/wvl" size="sm">
          WVL
        </Anchor>
        <Text size="sm">Galactic Premiership · {st.year}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>Galactic Premiership · {st.year}</Title>
          <Group gap="xs">
            <Badge variant="light" color={seasonComplete ? "teal" : "orange"}>
              {seasonComplete ? "season complete" : `week ${st.current_week}/${st.total_weeks}`}
            </Badge>
            <Text size="sm" c="dimmed">
              {st.tracked_players} careers · {st.active_players} active · {st.seasons_completed} seasons done
            </Text>
            {st.champion && (
              <Badge variant="filled" color="yellow">🏆 {st.champion}</Badge>
            )}
          </Group>
        </Stack>
        <Group gap="xs">
          <Button
            color="orange"
            leftSection={<IconPlayerTrackNext size={16} />}
            onClick={() => simWeek.mutate()}
            loading={simWeek.isPending}
            disabled={seasonComplete}
          >
            Sim Week
          </Button>
          <Button
            variant="default"
            leftSection={<IconPlayerSkipForward size={16} />}
            onClick={() => simAll.mutate()}
            loading={simAll.isPending}
            disabled={seasonComplete}
          >
            Sim Season
          </Button>
          <Tooltip label="Close season, age & retire players, import next CVL class">
            <Button
              color="indigo"
              leftSection={<IconCalendarPlus size={16} />}
              onClick={() => advance.mutate()}
              loading={advance.isPending}
              disabled={!seasonComplete}
            >
              Advance Season
            </Button>
          </Tooltip>
        </Group>
      </Group>

      <Tabs defaultValue="standings" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="standings">Standings</Tabs.Tab>
          <Tabs.Tab value="players">Careers</Tabs.Tab>
          <Tabs.Tab value="leaders">Leaders</Tabs.Tab>
          <Tabs.Tab value="schedule">Schedule</Tabs.Tab>
          <Tabs.Tab value="history">History</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="standings" pt="md">
          {standings.isLoading ? (
            <Center py="xl"><Loader /></Center>
          ) : (
            <StandingsTable rows={standings.data ?? []} />
          )}
        </Tabs.Panel>

        <Tabs.Panel value="players" pt="md">
          {players.isLoading ? (
            <Center py="xl"><Loader /></Center>
          ) : (
            <PlayersTable rows={players.data ?? []} onPick={setPickedPlayer} />
          )}
        </Tabs.Panel>

        <Tabs.Panel value="leaders" pt="md">
          <LeadersPanel leagueId={leagueId} onPick={setPickedPlayer} />
        </Tabs.Panel>

        <Tabs.Panel value="schedule" pt="md">
          <SchedulePanel leagueId={leagueId} />
        </Tabs.Panel>

        <Tabs.Panel value="history" pt="md">
          <HistoryPanel leagueId={leagueId} />
        </Tabs.Panel>
      </Tabs>

      <PlayerCareerModal
        leagueId={leagueId}
        playerId={pickedPlayer}
        onClose={() => setPickedPlayer(null)}
      />
    </Stack>
  );
}
