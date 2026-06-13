import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Tabs,
  Badge,
  Breadcrumbs,
  Anchor,
  Loader,
  Center,
  Card,
} from "@mantine/core";
import { IconChevronRight, IconArchive } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import { seasonApi, type Standing, type Game, type PollEntry } from "../../api/season";

/**
 * Read-only view of a saved (archived) college season. Renders the snapshot the
 * backend persists on each sim — same serializer shapes as the live hub, so the
 * grids match. Reload/compare experiments without resuming the sim.
 */
export function ArchiveView() {
  const { archiveKey = "" } = useParams();
  const archive = useQuery({
    queryKey: ["archive", archiveKey],
    queryFn: () => seasonApi.archive(archiveKey),
  });

  const standingsCols = useMemo<MRT_ColumnDef<Standing>[]>(
    () => [
      { accessorKey: "team_name", header: "Team" },
      { accessorKey: "conference", header: "Conf", size: 120 },
      {
        header: "Record",
        id: "record",
        size: 90,
        accessorFn: (r) => `${r.wins}-${r.losses}${r.ties ? `-${r.ties}` : ""}`,
        sortingFn: (a, b) => a.original.win_percentage - b.original.win_percentage,
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
    ],
    [],
  );

  const scheduleCols = useMemo<MRT_ColumnDef<Game>[]>(
    () => [
      { accessorKey: "week", header: "Wk", size: 60 },
      {
        header: "Matchup",
        id: "matchup",
        accessorFn: (g) => `${g.away_team} @ ${g.home_team}`,
      },
      {
        header: "Score",
        id: "score",
        size: 110,
        accessorFn: (g) => (g.completed ? `${g.away_score}-${g.home_score}` : ""),
        Cell: ({ row }) => {
          const g = row.original;
          return g.completed ? (
            <Text size="sm" ff="monospace">
              {g.away_score} – {g.home_score}
            </Text>
          ) : (
            <Badge size="xs" variant="light" color="gray">
              scheduled
            </Badge>
          );
        },
      },
    ],
    [],
  );

  const latestPoll = archive.data?.polls?.length
    ? archive.data.polls[archive.data.polls.length - 1].rankings
    : [];
  const pollCols = useMemo<MRT_ColumnDef<PollEntry>[]>(
    () => [
      { accessorKey: "rank", header: "#", size: 50 },
      { accessorKey: "team_name", header: "Team" },
      { accessorKey: "record", header: "Record", size: 90 },
      { accessorKey: "conference", header: "Conf", size: 120 },
      { accessorKey: "power_index", header: "Power", size: 90 },
    ],
    [],
  );

  const standingsTable = useDataGrid(standingsCols, archive.data?.standings ?? [], {
    sorting: [{ id: "record", desc: true }],
  });
  const scheduleTable = useDataGrid(scheduleCols, archive.data?.schedule ?? [], {
    sorting: [{ id: "week", desc: false }],
  });
  const pollTable = useDataGrid(pollCols, latestPoll, {
    sorting: [{ id: "rank", desc: false }],
  });

  if (archive.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (archive.isError || !archive.data) {
    return (
      <Card>
        <Text c="red">
          Couldn't load this saved season.{" "}
          <Anchor component={Link} to="/">
            Back to Saves
          </Anchor>
        </Text>
      </Card>
    );
  }

  const a = archive.data;

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/" size="sm">
          Saves
        </Anchor>
        <Text size="sm">{a.label || a.season_name}</Text>
      </Breadcrumbs>

      <Group gap="xs">
        <IconArchive size={22} color="var(--mantine-color-grape-6)" />
        <Title order={2}>{a.season_name || a.label}</Title>
        <Badge variant="light" color="gray">
          saved view
        </Badge>
        {a.champion && (
          <Badge variant="light" color="teal">
            🏆 {a.champion}
          </Badge>
        )}
      </Group>

      <Tabs defaultValue="standings" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="standings">Standings</Tabs.Tab>
          <Tabs.Tab value="schedule">Schedule</Tabs.Tab>
          <Tabs.Tab value="polls">Polls</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="standings" pt="md">
          <MantineReactTable table={standingsTable} />
        </Tabs.Panel>
        <Tabs.Panel value="schedule" pt="md">
          <MantineReactTable table={scheduleTable} />
        </Tabs.Panel>
        <Tabs.Panel value="polls" pt="md">
          {latestPoll.length ? (
            <MantineReactTable table={pollTable} />
          ) : (
            <Text c="dimmed">No polls in this snapshot.</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
