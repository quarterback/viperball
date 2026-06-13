import { useMemo, useState } from "react";
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
  Card,
  MultiSelect,
  SimpleGrid,
  Badge,
  Loader,
  Center,
  Box,
} from "@mantine/core";
import { IconTrophy } from "@tabler/icons-react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { seasonApi, type Standing } from "../api/season";

interface Row {
  team: string;
  conference: string;
  [run: string]: string | number;
}

export function Compare() {
  const sessions = useQuery({
    queryKey: ["college-sessions"],
    queryFn: seasonApi.listSessions,
  });
  const [selected, setSelected] = useState<string[]>([]);

  const standingsQueries = useQueries({
    queries: selected.map((sid) => ({
      queryKey: ["standings", sid],
      queryFn: () => seasonApi.standings(sid),
    })),
  });

  const sessionsById = useMemo(
    () => Object.fromEntries((sessions.data ?? []).map((s) => [s.session_id, s])),
    [sessions.data],
  );

  const loading = standingsQueries.some((q) => q.isLoading);
  const allLoaded =
    selected.length > 0 && standingsQueries.every((q) => q.data !== undefined);

  // Build a team-keyed pivot: one wins-column per run + a divergence "spread".
  const { rows, columns } = useMemo(() => {
    if (!allLoaded) return { rows: [] as Row[], columns: [] as MRT_ColumnDef<Row>[] };

    const byTeam = new Map<string, Row>();
    const runKeys: string[] = [];

    selected.forEach((sid, i) => {
      const data = standingsQueries[i].data as Standing[];
      const runKey = `run_${sid}`;
      runKeys.push(runKey);
      for (const s of data) {
        let row = byTeam.get(s.team_name);
        if (!row) {
          row = { team: s.team_name, conference: s.conference };
          byTeam.set(s.team_name, row);
        }
        row[runKey] = s.wins;
        row[`${runKey}_rec`] = `${s.wins}-${s.losses}`;
      }
    });

    const rows = Array.from(byTeam.values()).map((r) => {
      const wins = runKeys
        .map((k) => (typeof r[k] === "number" ? (r[k] as number) : null))
        .filter((v): v is number => v !== null);
      r.spread = wins.length > 1 ? Math.max(...wins) - Math.min(...wins) : 0;
      return r;
    });

    const columns: MRT_ColumnDef<Row>[] = [
      { accessorKey: "team", header: "Team" },
      { accessorKey: "conference", header: "Conf", size: 90 },
      ...selected.map((sid, i) => {
        const runKey = `run_${sid}`;
        const s = sessionsById[sid];
        const label = s ? s.name : sid.slice(0, 6);
        return {
          id: runKey,
          header: `${label} · #${i + 1}`,
          accessorFn: (r: Row) => (typeof r[runKey] === "number" ? r[runKey] : -1),
          size: 130,
          Cell: ({ row }: { row: { original: Row } }) => {
            const rec = row.original[`${runKey}_rec`];
            return <Text size="sm" ff="monospace">{rec ?? "—"}</Text>;
          },
        } as MRT_ColumnDef<Row>;
      }),
      {
        accessorKey: "spread",
        header: "Δ Wins",
        size: 90,
        Cell: ({ cell }) => {
          const v = cell.getValue<number>();
          return (
            <Badge variant="light" color={v >= 3 ? "orange" : v >= 1 ? "yellow" : "gray"}>
              {v}
            </Badge>
          );
        },
      },
    ];

    return { rows, columns };
  }, [allLoaded, selected, standingsQueries, sessionsById]);

  const table = useMantineReactTable({
    columns,
    data: rows,
    enableFacetedValues: true,
    initialState: {
      density: "xs",
      sorting: [{ id: "spread", desc: true }],
      showGlobalFilter: true,
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    mantineTableContainerProps: { style: { maxHeight: "60vh" } },
  });

  const options = (sessions.data ?? []).map((s) => ({
    value: s.session_id,
    label: `${s.name} — Wk ${s.current_week}/${s.total_weeks}${
      s.champion ? ` · 🏆 ${s.champion}` : ""
    }`,
  }));

  return (
    <Stack gap="md">
      <Stack gap={2}>
        <Title order={2}>Compare Runs</Title>
        <Text c="dimmed" size="sm">
          Diff 2–4 seasons side by side. Best with the same league simmed under different
          seeds or rules — the Δ Wins column surfaces where outcomes diverged most.
        </Text>
      </Stack>

      <Card>
        <MultiSelect
          label="Seasons to compare"
          placeholder={selected.length ? "" : "Pick 2 or more active seasons"}
          data={options}
          value={selected}
          onChange={(v) => setSelected(v.slice(0, 4))}
          maxValues={4}
          searchable
          disabled={sessions.isLoading}
        />
        {sessions.data && sessions.data.length < 2 && (
          <Text size="xs" c="dimmed" mt="xs">
            Create a couple of seeded seasons (New Season → fix a seed → fork or re-run with a
            tweak) and they'll show up here.
          </Text>
        )}
      </Card>

      {selected.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          {selected.map((sid, i) => {
            const s = sessionsById[sid];
            return (
              <Card key={sid} padding="sm">
                <Text size="xs" c="dimmed">
                  Run #{i + 1}
                </Text>
                <Text fw={600} lineClamp={1}>
                  {s?.name ?? sid.slice(0, 8)}
                </Text>
                <Group gap={6} mt={4}>
                  {s?.champion ? (
                    <Badge variant="light" color="teal" leftSection={<IconTrophy size={12} />}>
                      {s.champion}
                    </Badge>
                  ) : (
                    <Badge variant="light" color="gray">
                      in progress
                    </Badge>
                  )}
                </Group>
              </Card>
            );
          })}
        </SimpleGrid>
      )}

      {loading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {allLoaded && !loading && (
        <Box>
          <MantineReactTable table={table} />
        </Box>
      )}
    </Stack>
  );
}
