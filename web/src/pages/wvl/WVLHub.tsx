import { useMemo } from "react";
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
} from "@mantine/core";
import { IconChevronRight, IconPlayerTrackNext, IconPlayerSkipForward } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../../components/DataGrid";
import { wvlApi, ZONE_COLOR, type WVLStandRow, type WVLTierStandings } from "../../api/wvl";

function flatten(tier: WVLTierStandings): WVLStandRow[] {
  const rows: WVLStandRow[] = [];
  for (const members of Object.values(tier.standings.divisions ?? {})) rows.push(...members);
  rows.sort((a, b) => (a.position ?? 99) - (b.position ?? 99));
  return rows;
}

function TierTable({ tier }: { tier: WVLTierStandings }) {
  const cols = useMemo<MRT_ColumnDef<WVLStandRow>[]>(
    () => [
      { accessorKey: "position", header: "#", size: 50 },
      {
        accessorKey: "team_name",
        header: "Club",
        Cell: ({ row }) => {
          const z = row.original.zone;
          return (
            <Group gap={6} wrap="nowrap">
              <Text size="sm">{row.original.team_name}</Text>
              {z && z !== "safe" && (
                <Badge size="xs" variant="light" color={ZONE_COLOR[z] ?? "gray"}>
                  {z}
                </Badge>
              )}
            </Group>
          );
        },
      },
      {
        header: "Record",
        id: "record",
        size: 90,
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
  const table = useDataGrid(cols, flatten(tier), { sorting: [{ id: "position", desc: false }], maxHeight: "60vh" });
  return <MantineReactTable table={table} />;
}

export function WVLHub() {
  const { sessionId = "" } = useParams();
  const qc = useQueryClient();

  const status = useQuery({ queryKey: ["wvl-status", sessionId], queryFn: () => wvlApi.status(sessionId) });
  const standings = useQuery({ queryKey: ["wvl-standings", sessionId], queryFn: () => wvlApi.standings(sessionId) });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["wvl-status", sessionId] });
    qc.invalidateQueries({ queryKey: ["wvl-standings", sessionId] });
  };
  const simWeek = useMutation({
    mutationFn: () => wvlApi.simWeek(sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated a week (all tiers)", color: "orange" });
      invalidate();
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });
  const simAll = useMutation({
    mutationFn: () => wvlApi.simAll(sessionId),
    onSuccess: () => {
      notifications.show({ message: "Simulated the season", color: "orange" });
      invalidate();
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
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
          WVL season not found.{" "}
          <Anchor component={Link} to="/wvl">
            Back
          </Anchor>
        </Text>
      </Card>
    );
  }
  const st = status.data!;
  const tiers = standings.data ?? [];

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/wvl" size="sm">
          WVL
        </Anchor>
        <Text size="sm">Season</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>World Viperball League</Title>
          <Badge variant="light" color="orange" w="fit-content">
            {st.phase.replace(/_/g, " ")}
          </Badge>
        </Stack>
        <Group gap="xs">
          <Button color="orange" leftSection={<IconPlayerTrackNext size={16} />} onClick={() => simWeek.mutate()} loading={simWeek.isPending}>
            Sim Week
          </Button>
          <Button variant="default" leftSection={<IconPlayerSkipForward size={16} />} onClick={() => simAll.mutate()} loading={simAll.isPending}>
            Sim Season
          </Button>
        </Group>
      </Group>

      {standings.isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : tiers.length === 0 ? (
        <Text c="dimmed">No standings yet.</Text>
      ) : (
        <Tabs defaultValue={String(tiers[0].tier)} keepMounted={false}>
          <Tabs.List>
            {tiers.map((t) => (
              <Tabs.Tab key={t.tier} value={String(t.tier)}>
                {t.name}
              </Tabs.Tab>
            ))}
          </Tabs.List>
          {tiers.map((t) => (
            <Tabs.Panel key={t.tier} value={String(t.tier)} pt="md">
              <TierTable tier={t} />
            </Tabs.Panel>
          ))}
        </Tabs>
      )}
    </Stack>
  );
}
