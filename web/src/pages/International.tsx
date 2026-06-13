import { useMemo } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Tabs,
  Button,
  Badge,
  Card,
  Loader,
  Center,
  SimpleGrid,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconWorld, IconPlayerSkipForward, IconPlus } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDataGrid } from "../components/DataGrid";
import {
  fivApi,
  type FivRanking,
  type FivGroupStanding,
} from "../api/fiv";
import { ConfederationsTab, WCStatsTab } from "./FivDepth";

export function International() {
  const qc = useQueryClient();

  const cycle = useQuery({ queryKey: ["fiv-cycle"], queryFn: fivApi.activeCycle });
  const rankings = useQuery({
    queryKey: ["fiv-rankings"],
    queryFn: fivApi.rankings,
    enabled: !!cycle.data,
  });
  const groups = useQuery({
    queryKey: ["fiv-groups"],
    queryFn: fivApi.groups,
    enabled: !!cycle.data,
  });
  const bracket = useQuery({
    queryKey: ["fiv-bracket"],
    queryFn: fivApi.bracket,
    enabled: !!cycle.data,
  });

  const invalidate = () =>
    ["fiv-cycle", "fiv-rankings", "fiv-groups", "fiv-bracket"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k] }),
    );

  const newCycle = useMutation({
    mutationFn: () => fivApi.newCycle(),
    onSuccess: () => {
      notifications.show({ message: "New FIV cycle created", color: "cyan" });
      invalidate();
    },
  });
  const simStage = useMutation({
    mutationFn: () => fivApi.simStage(),
    onSuccess: () => {
      notifications.show({ message: "Stage simulated", color: "cyan" });
      invalidate();
    },
  });

  const rankCols = useMemo<MRT_ColumnDef<FivRanking>[]>(
    () => [
      { accessorKey: "rank", header: "#", size: 60 },
      { accessorKey: "code", header: "Nation" },
      {
        accessorKey: "rating",
        header: "Rating",
        size: 110,
        Cell: ({ cell }) => <b>{Math.round(cell.getValue<number>())}</b>,
      },
    ],
    [],
  );

  const groupCols = useMemo<MRT_ColumnDef<FivGroupStanding>[]>(
    () => [
      { accessorKey: "group", header: "Group", size: 90 },
      { accessorKey: "team", header: "Nation" },
      {
        header: "W-D-L",
        id: "wdl",
        size: 100,
        accessorFn: (r) => `${r.w}-${r.d}-${r.l}`,
        sortingFn: (a, b) => a.original.pts - b.original.pts,
      },
      { accessorKey: "pf", header: "PF", size: 70 },
      { accessorKey: "pa", header: "PA", size: 70 },
      {
        accessorKey: "point_diff",
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
        accessorKey: "pts",
        header: "Pts",
        size: 70,
        Cell: ({ cell }) => <b>{cell.getValue<number>()}</b>,
      },
    ],
    [],
  );

  const rankTable = useDataGrid(rankCols, rankings.data ?? [], {
    isLoading: rankings.isLoading,
    sorting: [{ id: "rank", desc: false }],
  });
  const groupTable = useDataGrid(groupCols, groups.data ?? [], {
    isLoading: groups.isLoading,
    sorting: [{ id: "pts", desc: true }],
  });

  if (cycle.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!cycle.data) {
    return (
      <Stack gap="md" maw={640}>
        <Title order={2}>International — FIV</Title>
        <Card>
          <Stack gap="sm" align="flex-start">
            <Text c="dimmed">
              No active international cycle. Start one to draw the World Cup and run
              confederation play.
            </Text>
            <Button
              leftSection={<IconPlus size={16} />}
              color="cyan"
              onClick={() => newCycle.mutate()}
              loading={newCycle.isPending}
            >
              New FIV cycle
            </Button>
          </Stack>
        </Card>
      </Stack>
    );
  }

  const c = cycle.data;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Group gap="xs">
            <IconWorld size={22} color="var(--mantine-color-cyan-6)" />
            <Title order={2}>International — Cycle {c.cycle_number}</Title>
          </Group>
          <Group gap="xs">
            <Badge variant="light" color="cyan">
              {(c.world_cup?.phase ?? c.phase ?? "").replace(/_/g, " ")}
            </Badge>
            {c.host_nation && (
              <Text size="sm" c="dimmed">
                Host: {c.host_nation}
              </Text>
            )}
            {c.world_cup?.champion && (
              <Badge variant="light" color="teal">
                🏆 {c.world_cup.champion}
              </Badge>
            )}
          </Group>
        </Stack>
        <Group gap="xs">
          <Button
            leftSection={<IconPlayerSkipForward size={16} />}
            color="cyan"
            onClick={() => simStage.mutate()}
            loading={simStage.isPending}
          >
            Sim Stage
          </Button>
          <Button
            variant="default"
            leftSection={<IconPlus size={16} />}
            onClick={() => newCycle.mutate()}
            loading={newCycle.isPending}
          >
            New Cycle
          </Button>
        </Group>
      </Group>

      <Tabs defaultValue="rankings" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="rankings">World Rankings</Tabs.Tab>
          <Tabs.Tab value="confederations">Confederations</Tabs.Tab>
          <Tabs.Tab value="groups">World Cup Groups</Tabs.Tab>
          <Tabs.Tab value="bracket">Knockout</Tabs.Tab>
          <Tabs.Tab value="wcstats">WC Awards</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="rankings" pt="md">
          <MantineReactTable table={rankTable} />
        </Tabs.Panel>
        <Tabs.Panel value="confederations" pt="md">
          <ConfederationsTab />
        </Tabs.Panel>
        <Tabs.Panel value="wcstats" pt="md">
          <WCStatsTab />
        </Tabs.Panel>
        <Tabs.Panel value="groups" pt="md">
          {groups.data && groups.data.length > 0 ? (
            <MantineReactTable table={groupTable} />
          ) : (
            <Text c="dimmed">No World Cup groups drawn yet — sim through to the World Cup.</Text>
          )}
        </Tabs.Panel>
        <Tabs.Panel value="bracket" pt="md">
          {bracket.data && bracket.data.knockout_rounds.length > 0 ? (
            <Stack gap="md">
              {bracket.data.champion && (
                <Badge size="lg" color="teal" variant="light">
                  🏆 {bracket.data.champion}
                </Badge>
              )}
              {bracket.data.knockout_rounds.map((rd) => (
                <Card key={rd.round_name}>
                  <Group justify="space-between" mb="sm">
                    <Text fw={600}>{rd.round_name}</Text>
                    <Badge size="xs" variant="light" color={rd.completed ? "teal" : "gray"}>
                      {rd.completed ? "done" : "pending"}
                    </Badge>
                  </Group>
                  <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
                    {rd.matchups.map((m, i) => (
                      <Card key={i} padding="sm" withBorder>
                        <Group justify="space-between">
                          <Text size="sm">{m.away_code ?? "TBD"}</Text>
                          <Text size="sm" ff="monospace">
                            {m.away_score ?? ""}
                          </Text>
                        </Group>
                        <Group justify="space-between">
                          <Text size="sm">{m.home_code ?? "TBD"}</Text>
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
            <Text c="dimmed">No knockout bracket yet.</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
