import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Text,
  Card,
  Badge,
  Button,
  Select,
  SimpleGrid,
  Loader,
  Center,
  Title,
} from "@mantine/core";
import { IconPlayerSkipForward, IconBallFootball } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../components/DataGrid";
import { fivApi, CONFEDERATIONS, type FivGroupStanding } from "../api/fiv";

export function ConfederationsTab() {
  const qc = useQueryClient();
  const [conf, setConf] = useState("cav");

  const standings = useQuery({
    queryKey: ["fiv-conf-standings", conf],
    queryFn: () => fivApi.confStandings(conf),
  });
  const bracket = useQuery({
    queryKey: ["fiv-conf-bracket", conf],
    queryFn: () => fivApi.confBracket(conf),
  });

  const sim = useMutation({
    mutationFn: () => fivApi.confSimAll(conf),
    onSuccess: () => {
      notifications.show({ message: "Confederation simulated", color: "cyan" });
      qc.invalidateQueries({ queryKey: ["fiv-conf-standings", conf] });
      qc.invalidateQueries({ queryKey: ["fiv-conf-bracket", conf] });
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });

  const cols = useMemo<MRT_ColumnDef<FivGroupStanding>[]>(
    () => [
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
      { accessorKey: "point_diff", header: "Diff", size: 80 },
      { accessorKey: "pts", header: "Pts", size: 70, Cell: ({ cell }) => <b>{cell.getValue<number>()}</b> },
    ],
    [],
  );
  const table = useDataGrid(cols, standings.data ?? [], {
    isLoading: standings.isLoading,
    sorting: [{ id: "pts", desc: true }],
  });

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Select
          label="Confederation"
          data={CONFEDERATIONS.map((c) => ({ value: c.id, label: c.name }))}
          value={conf}
          onChange={(v) => setConf(v ?? "cav")}
          w={280}
        />
        <Button leftSection={<IconPlayerSkipForward size={16} />} color="cyan" onClick={() => sim.mutate()} loading={sim.isPending}>
          Sim confederation
        </Button>
      </Group>

      {standings.data && standings.data.length > 0 ? (
        <MantineReactTable table={table} />
      ) : (
        <Text c="dimmed">No standings yet — sim the confederation.</Text>
      )}

      {bracket.data && bracket.data.knockout_rounds.length > 0 && (
        <Card>
          <Group justify="space-between" mb="sm">
            <Text fw={700}>Knockout</Text>
            {bracket.data.champion && (
              <Badge color="teal" variant="light">
                🏆 {bracket.data.champion}
              </Badge>
            )}
          </Group>
          <Stack gap="sm">
            {bracket.data.knockout_rounds.map((rd) => (
              <div key={rd.round_name}>
                <Text size="sm" fw={600} mb={4}>
                  {rd.round_name}
                </Text>
                <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
                  {rd.matchups.map((m, i) => (
                    <Card key={i} padding="xs" withBorder>
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
              </div>
            ))}
          </Stack>
        </Card>
      )}
    </Stack>
  );
}

export function WCStatsTab() {
  const stats = useQuery({ queryKey: ["fiv-wc-stats"], queryFn: fivApi.worldcupStats });
  if (stats.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }
  const gb = stats.data?.golden_boot;
  const mvp = stats.data?.mvp;
  const nameOf = (x: typeof gb) => x?.name ?? x?.player ?? "—";
  const teamOf = (x: typeof gb) => x?.team ?? x?.code ?? "";
  if (!gb && !mvp) return <Text c="dimmed">No World Cup awards yet — finish the tournament.</Text>;
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }}>
      {gb && (
        <Card withBorder>
          <Group gap="xs" mb={4}>
            <IconBallFootball size={16} color="var(--mantine-color-yellow-6)" />
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Golden Boot
            </Text>
          </Group>
          <Title order={3}>{nameOf(gb)}</Title>
          <Text c="dimmed" size="sm">
            {teamOf(gb)} {gb.goals != null ? `· ${gb.goals} goals` : gb.tds != null ? `· ${gb.tds} TD` : ""}
          </Text>
        </Card>
      )}
      {mvp && (
        <Card withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb={4}>
            Tournament MVP
          </Text>
          <Title order={3}>{nameOf(mvp)}</Title>
          <Text c="dimmed" size="sm">
            {teamOf(mvp)}
          </Text>
        </Card>
      )}
    </SimpleGrid>
  );
}
