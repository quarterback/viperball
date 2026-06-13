import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Select,
  NumberInput,
  Button,
  Tooltip,
  ActionIcon,
  Table,
  Loader,
  Center,
  Tabs,
  Badge,
} from "@mantine/core";
import { IconDice5, IconPlayerPlay } from "@tabler/icons-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../components/DataGrid";
import { seasonApi, type BoxPlayerStat, type TeamGameStats } from "../api/season";
import { gameApi, type GameSimResult } from "../api/game";

const TEAM_STATS: { key: keyof TeamGameStats; label: string }[] = [
  { key: "total_yards", label: "Total yards" },
  { key: "touchdowns", label: "Touchdowns" },
  { key: "turnovers", label: "Turnovers" },
  { key: "fumbles_lost", label: "Fumbles lost" },
];

export function GameSim() {
  const teams = useQuery({ queryKey: ["teams"], queryFn: seasonApi.teams });
  const weather = useQuery({ queryKey: ["weather"], queryFn: gameApi.weather });

  const [home, setHome] = useState<string | null>(null);
  const [away, setAway] = useState<string | null>(null);
  const [wx, setWx] = useState("clear");
  const [seed, setSeed] = useState(0);
  const [result, setResult] = useState<GameSimResult | null>(null);

  const teamOpts = (teams.data ?? []).map((t) => ({ value: t.name, label: t.name }));

  const sim = useMutation({
    mutationFn: () =>
      gameApi.simulate({ home: home!, away: away!, weather: wx, seed: seed || null }),
    onSuccess: (r) => setResult(r),
    onError: (e: unknown) =>
      notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });

  const cols = useMemo<MRT_ColumnDef<BoxPlayerStat>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "tag", header: "Pos", size: 70 },
      { accessorKey: "yards", header: "Yds", size: 70 },
      { accessorKey: "tds", header: "TD", size: 60 },
      { accessorKey: "touches", header: "Tch", size: 70 },
      { accessorKey: "tackles", header: "Tkl", size: 70 },
    ],
    [],
  );
  const awayTable = useDataGrid(cols, result?.player_stats?.away ?? [], { sorting: [{ id: "yards", desc: true }], maxHeight: "40vh" });
  const homeTable = useDataGrid(cols, result?.player_stats?.home ?? [], { sorting: [{ id: "yards", desc: true }], maxHeight: "40vh" });

  return (
    <Stack gap="md" maw={900}>
      <Group gap="xs">
        <IconDice5 size={22} color="var(--mantine-color-indigo-6)" />
        <Title order={2}>Game Simulator</Title>
      </Group>
      <Text c="dimmed" size="sm" mt={-8}>
        Sim a single one-off game between any two teams (uses each team's default styles).
      </Text>

      <Card>
        <Group grow align="flex-end">
          <Select label="Away team" data={teamOpts} value={away} onChange={setAway} searchable disabled={teams.isLoading} />
          <Select label="Home team" data={teamOpts} value={home} onChange={setHome} searchable disabled={teams.isLoading} />
        </Group>
        <Group align="flex-end" mt="sm">
          <Select
            label="Weather"
            data={(weather.data ?? [{ key: "clear", label: "Clear" }]).map((w) => ({ value: w.key, label: w.label }))}
            value={wx}
            onChange={(v) => setWx(v ?? "clear")}
            w={200}
          />
          <NumberInput
            label="Seed"
            description="0 = random"
            value={seed}
            min={0}
            onChange={(v) => setSeed(Number(v) || 0)}
            w={180}
            rightSection={
              <Tooltip label="Random">
                <ActionIcon variant="subtle" onClick={() => setSeed(Math.floor(Math.random() * 999999) + 1)}>
                  <IconDice5 size={16} />
                </ActionIcon>
              </Tooltip>
            }
          />
          <Button
            leftSection={<IconPlayerPlay size={16} />}
            onClick={() => sim.mutate()}
            loading={sim.isPending}
            disabled={!home || !away || home === away}
            ml="auto"
          >
            Simulate
          </Button>
        </Group>
      </Card>

      {sim.isPending && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {result && (
        <>
          <Card>
            <Group justify="center" gap="xl">
              <Stack gap={0} align="center">
                <Text fw={600}>{result.final_score.away.team}</Text>
                <Title order={1}>{result.final_score.away.score}</Title>
              </Stack>
              <Stack gap={4} align="center">
                <Text c="dimmed">@</Text>
                {result.weather_label && (
                  <Badge variant="light" size="xs">
                    {result.weather_label}
                  </Badge>
                )}
              </Stack>
              <Stack gap={0} align="center">
                <Text fw={600}>{result.final_score.home.team}</Text>
                <Title order={1}>{result.final_score.home.score}</Title>
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
                  <Table.Th>{result.final_score.away.team}</Table.Th>
                  <Table.Th ta="center" />
                  <Table.Th ta="right">{result.final_score.home.team}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {TEAM_STATS.map((r) => (
                  <Table.Tr key={String(r.key)}>
                    <Table.Td>{result.stats.away?.[r.key] ?? "—"}</Table.Td>
                    <Table.Td ta="center" c="dimmed">
                      {r.label}
                    </Table.Td>
                    <Table.Td ta="right">{result.stats.home?.[r.key] ?? "—"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>

          <Tabs defaultValue="away">
            <Tabs.List>
              <Tabs.Tab value="away">{result.final_score.away.team}</Tabs.Tab>
              <Tabs.Tab value="home">{result.final_score.home.team}</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="away" pt="md">
              <MantineReactTable table={awayTable} />
            </Tabs.Panel>
            <Tabs.Panel value="home" pt="md">
              <MantineReactTable table={homeTable} />
            </Tabs.Panel>
          </Tabs>
        </>
      )}
    </Stack>
  );
}
