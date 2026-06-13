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
  Anchor,
  Breadcrumbs,
  Badge,
  Loader,
  Center,
  Card,
} from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { seasonApi, type RosterPlayer } from "../../api/season";

export function TeamPage() {
  const { sessionId = "", teamName = "" } = useParams();
  const team = decodeURIComponent(teamName);

  const roster = useQuery({
    queryKey: ["roster", sessionId, team],
    queryFn: () => seasonApi.roster(sessionId, team),
  });
  const standings = useQuery({
    queryKey: ["standings", sessionId],
    queryFn: () => seasonApi.standings(sessionId),
  });

  const record = standings.data?.find((s) => s.team_name === team);

  const cols = useMemo<MRT_ColumnDef<RosterPlayer>[]>(
    () => [
      { accessorKey: "number", header: "#", size: 50 },
      {
        accessorKey: "name",
        header: "Player",
        Cell: ({ row }) => (
          <Anchor
            component={Link}
            to={`/league/${sessionId}/team/${encodeURIComponent(team)}/player/${encodeURIComponent(
              row.original.name,
            )}`}
            fw={600}
          >
            {row.original.name}
          </Anchor>
        ),
      },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "year_abbr", header: "Yr", size: 60 },
      {
        accessorKey: "overall",
        header: "OVR",
        size: 70,
        Cell: ({ cell }) => (
          <Badge variant="light" color={ovrColor(cell.getValue<number>())}>
            {cell.getValue<number>()}
          </Badge>
        ),
      },
      { accessorKey: "speed", header: "SPD", size: 65 },
      { accessorKey: "power", header: "POW", size: 65 },
      { accessorKey: "agility", header: "AGI", size: 65 },
      { accessorKey: "hands", header: "HND", size: 65 },
      { accessorKey: "awareness", header: "AWR", size: 65 },
      { accessorKey: "tackling", header: "TKL", size: 65 },
      { accessorKey: "kicking", header: "KICK", size: 70 },
      {
        accessorKey: "depth_status",
        header: "Status",
        size: 90,
        Cell: ({ cell }) => {
          const v = cell.getValue<string>();
          if (v === "healthy") return <Text size="xs" c="dimmed">—</Text>;
          return (
            <Badge size="xs" color={v === "out" ? "red" : "orange"} variant="light">
              {v}
            </Badge>
          );
        },
      },
    ],
    [sessionId, team],
  );

  const table = useMantineReactTable({
    columns: cols,
    data: roster.data?.roster ?? [],
    state: { isLoading: roster.isLoading },
    initialState: {
      density: "xs",
      sorting: [{ id: "overall", desc: true }],
      showGlobalFilter: true,
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    mantineTableContainerProps: { style: { maxHeight: "68vh" } },
  });

  if (roster.isError) {
    return (
      <Card>
        <Text c="red">
          Couldn't load this roster — the season may have expired.{" "}
          <Anchor component={Link} to={`/league/${sessionId}`}>
            Back to season
          </Anchor>
        </Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Anchor component={Link} to={`/league/${sessionId}`} size="sm">
          Season
        </Anchor>
        <Text size="sm">{team}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>{team}</Title>
          {record && (
            <Group gap="xs">
              <Badge variant="light">
                {record.wins}-{record.losses}
                {record.ties ? `-${record.ties}` : ""}
              </Badge>
              <Text size="sm" c="dimmed">
                {record.conference} · PF {record.points_for} / PA {record.points_against}
              </Text>
            </Group>
          )}
        </Stack>
        {roster.data?.prestige != null && (
          <Badge size="lg" variant="light" color="grape">
            Prestige {roster.data.prestige}
          </Badge>
        )}
      </Group>

      {roster.isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : (
        <MantineReactTable table={table} />
      )}
    </Stack>
  );
}

function ovrColor(ovr: number) {
  if (ovr >= 85) return "teal";
  if (ovr >= 75) return "indigo";
  if (ovr >= 65) return "gray";
  return "red";
}
