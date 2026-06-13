import { useMemo } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import { Stack, Card, Text, Group, Badge, SimpleGrid, Table, Loader, Center } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import {
  seasonApi,
  type InjuryRecord,
  type AwardEntry,
  type Standing,
} from "../../api/season";

// ── Conferences: standings grouped by conference ────────────────
export function ConferencesTab({ sid }: { sid: string }) {
  const q = useQuery({
    queryKey: ["conferences", sid],
    queryFn: () => seasonApi.conferences(sid),
  });
  if (q.isLoading)
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  const confs = q.data?.conferences ?? {};
  const champions = q.data?.champions ?? {};
  const names = Object.keys(confs).sort();
  if (!names.length) return <Text c="dimmed">No conference data.</Text>;

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      {names.map((name) => {
        const rows: Standing[] = confs[name].standings ?? [];
        return (
          <Card key={name} withBorder padding="sm">
            <Group justify="space-between" mb="xs">
              <Text fw={700} size="sm">
                {name}
              </Text>
              {champions[name] && (
                <Badge size="xs" color="teal" variant="light">
                  🏆 {champions[name]}
                </Badge>
              )}
            </Group>
            <Table striped withRowBorders={false} verticalSpacing={2} fz="sm">
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.team_name}>
                    <Table.Td>{r.team_name}</Table.Td>
                    <Table.Td ta="right">
                      {r.conf_wins}-{r.conf_losses}
                    </Table.Td>
                    <Table.Td ta="right" c="dimmed">
                      {r.wins}-{r.losses}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        );
      })}
    </SimpleGrid>
  );
}

// ── Injuries: active injury report ──────────────────────────────
export function InjuriesTab({ sid }: { sid: string }) {
  const q = useQuery({
    queryKey: ["injuries", sid],
    queryFn: () => seasonApi.injuries(sid),
  });
  const cols = useMemo<MRT_ColumnDef<InjuryRecord>[]>(
    () => [
      { accessorKey: "player_name", header: "Player" },
      { accessorKey: "team_name", header: "Team" },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "body_part", header: "Injury", size: 120 },
      { accessorKey: "category", header: "Type", size: 100 },
      {
        accessorKey: "weeks_out",
        header: "Out",
        size: 90,
        Cell: ({ row }) =>
          row.original.is_season_ending ? (
            <Badge size="xs" color="red" variant="light">
              season
            </Badge>
          ) : (
            <Text size="sm">{row.original.weeks_out} wk</Text>
          ),
      },
    ],
    [],
  );
  const table = useDataGrid(cols, q.data?.active ?? [], {
    isLoading: q.isLoading,
    sorting: [{ id: "weeks_out", desc: true }],
  });
  if (!q.isLoading && !(q.data?.active ?? []).length)
    return <Text c="dimmed">No active injuries.</Text>;
  return <MantineReactTable table={table} />;
}

// ── Awards: season honors ───────────────────────────────────────
export function AwardsTab({ sid }: { sid: string }) {
  const q = useQuery({
    queryKey: ["awards", sid],
    queryFn: () => seasonApi.awards(sid),
  });
  const cols = useMemo<MRT_ColumnDef<AwardEntry>[]>(
    () => [
      { accessorKey: "award_name", header: "Award" },
      { accessorKey: "player_name", header: "Player" },
      { accessorKey: "team_name", header: "Team" },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "overall_rating", header: "OVR", size: 70 },
    ],
    [],
  );
  const awards = q.data?.individual_awards ?? [];
  const table = useDataGrid(cols, awards, { isLoading: q.isLoading });

  const coy = q.data?.coach_of_year;
  const coyText =
    typeof coy === "string" ? coy : coy ? `${coy.name ?? ""} (${coy.team_name ?? ""})` : null;

  if (q.isLoading)
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  if (!awards.length && !coyText)
    return <Text c="dimmed">No awards yet — finish the season.</Text>;

  return (
    <Stack gap="md">
      {coyText && (
        <Card withBorder padding="sm">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Coach of the Year
          </Text>
          <Text fw={700}>{coyText}</Text>
        </Card>
      )}
      {awards.length > 0 && <MantineReactTable table={table} />}
    </Stack>
  );
}
