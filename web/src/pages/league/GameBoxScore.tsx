import { useParams, Link } from "react-router-dom";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Text,
  Card,
  Breadcrumbs,
  Anchor,
  Loader,
  Center,
  Table,
  Title,
  Tabs,
} from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import { seasonApi, type BoxPlayerStat, type TeamGameStats } from "../../api/season";

const TEAM_STAT_ROWS: { key: keyof TeamGameStats; label: string }[] = [
  { key: "total_yards", label: "Total yards" },
  { key: "touchdowns", label: "Touchdowns" },
  { key: "turnovers", label: "Turnovers" },
  { key: "fumbles_lost", label: "Fumbles lost" },
];

function playerCols(): MRT_ColumnDef<BoxPlayerStat>[] {
  return [
    { accessorKey: "name", header: "Player" },
    { accessorKey: "tag", header: "Pos", size: 70 },
    { accessorKey: "yards", header: "Yds", size: 70 },
    { accessorKey: "tds", header: "TD", size: 60 },
    { accessorKey: "touches", header: "Tch", size: 70 },
    { accessorKey: "tackles", header: "Tkl", size: 70 },
  ];
}

export function GameBoxScore() {
  const { sessionId = "", week = "0", away = "", home = "" } = useParams();
  const awayTeam = decodeURIComponent(away);
  const homeTeam = decodeURIComponent(home);

  const games = useQuery({
    queryKey: ["schedule-week", sessionId, week],
    queryFn: () => seasonApi.scheduleWeek(sessionId, Number(week)),
  });
  const game = games.data?.find(
    (g) => g.away_team === awayTeam && g.home_team === homeTeam,
  );
  const fr = game?.full_result;

  const awayTable = useDataGrid(playerCols(), fr?.player_stats?.away ?? [], {
    sorting: [{ id: "yards", desc: true }],
    maxHeight: "40vh",
  });
  const homeTable = useDataGrid(playerCols(), fr?.player_stats?.home ?? [], {
    sorting: [{ id: "yards", desc: true }],
    maxHeight: "40vh",
  });

  if (games.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (!game || !fr) {
    return (
      <Card>
        <Text c="red">
          No box score for this game (it may not be played, or used the fast sim).{" "}
          <Anchor component={Link} to={`/league/${sessionId}`}>
            Back to season
          </Anchor>
        </Text>
      </Card>
    );
  }

  const fs = fr.final_score;

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Anchor component={Link} to={`/league/${sessionId}`} size="sm">
          Season
        </Anchor>
        <Text size="sm">
          Week {week}: {awayTeam} @ {homeTeam}
        </Text>
      </Breadcrumbs>

      <Card>
        <Group justify="center" gap="xl">
          <Stack gap={0} align="center">
            <Text fw={600}>{fs.away.team}</Text>
            <Title order={1}>{fs.away.score}</Title>
          </Stack>
          <Text c="dimmed">@</Text>
          <Stack gap={0} align="center">
            <Text fw={600}>{fs.home.team}</Text>
            <Title order={1}>{fs.home.score}</Title>
          </Stack>
        </Group>
      </Card>

      <Card>
        <Text fw={700} mb="sm">
          Team stats
        </Text>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{fs.away.team}</Table.Th>
              <Table.Th ta="center"></Table.Th>
              <Table.Th ta="right">{fs.home.team}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {TEAM_STAT_ROWS.map((r) => (
              <Table.Tr key={String(r.key)}>
                <Table.Td>{fr.stats.away?.[r.key] ?? "—"}</Table.Td>
                <Table.Td ta="center" c="dimmed">
                  {r.label}
                </Table.Td>
                <Table.Td ta="right">{fr.stats.home?.[r.key] ?? "—"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Tabs defaultValue="away">
        <Tabs.List>
          <Tabs.Tab value="away">{awayTeam}</Tabs.Tab>
          <Tabs.Tab value="home">{homeTeam}</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="away" pt="md">
          <MantineReactTable table={awayTable} />
        </Tabs.Panel>
        <Tabs.Panel value="home" pt="md">
          <MantineReactTable table={homeTable} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
