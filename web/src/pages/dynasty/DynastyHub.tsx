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
  SimpleGrid,
} from "@mantine/core";
import { IconChevronRight, IconCrown } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import {
  dynastyApi,
  type TeamHistory,
  type SeasonAwards,
} from "../../api/dynasty";
import { DynastyCommand } from "./DynastyCommand";
import { ProgramsManager } from "./ProgramsManager";

// Which value key each record carries, and how to show it. Order is display order.
const RECORDS: { key: string; label: string; value: string; format?: (v: number) => string }[] = [
  { key: "most_wins_season", label: "Most wins (season)", value: "wins" },
  { key: "most_points_season", label: "Most points (season)", value: "points", format: (v) => v.toFixed(1) },
  { key: "best_defense_season", label: "Best defense (season)", value: "ppg_allowed", format: (v) => `${v.toFixed(1)} PPG` },
  { key: "most_championships", label: "Most championships", value: "championships" },
  { key: "highest_win_percentage", label: "Highest win %", value: "win_pct", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "most_coaching_wins", label: "Most coaching wins", value: "wins" },
  { key: "most_coaching_championships", label: "Most coaching titles", value: "championships" },
];

export function DynastyHub() {
  const { sessionId = "" } = useParams();

  const status = useQuery({
    queryKey: ["dynasty-status", sessionId],
    queryFn: () => dynastyApi.status(sessionId),
  });
  const histories = useQuery({
    queryKey: ["dynasty-histories", sessionId],
    queryFn: () => dynastyApi.teamHistories(sessionId),
  });
  const awards = useQuery({
    queryKey: ["dynasty-awards", sessionId],
    queryFn: () => dynastyApi.awards(sessionId),
  });
  const recordBook = useQuery({
    queryKey: ["dynasty-records", sessionId],
    queryFn: () => dynastyApi.recordBook(sessionId),
  });

  const histCols = useMemo<MRT_ColumnDef<TeamHistory>[]>(
    () => [
      { accessorKey: "team_name", header: "Team" },
      {
        header: "All-time",
        id: "record",
        size: 110,
        accessorFn: (r) => `${r.total_wins}-${r.total_losses}`,
        sortingFn: (a, b) => a.original.win_percentage - b.original.win_percentage,
      },
      {
        accessorKey: "win_percentage",
        header: "Win %",
        size: 90,
        Cell: ({ cell }) => (cell.getValue<number>() * 100).toFixed(1),
      },
      {
        accessorKey: "total_championships",
        header: "Titles",
        size: 80,
        Cell: ({ cell }) => {
          const v = cell.getValue<number>();
          return v ? (
            <Badge variant="light" color="grape">
              {v}
            </Badge>
          ) : (
            <Text size="sm" c="dimmed">
              0
            </Text>
          );
        },
      },
      { accessorKey: "total_playoff_appearances", header: "Playoffs", size: 90 },
      {
        header: "Best",
        id: "best",
        size: 110,
        accessorFn: (r) => `${r.best_season_wins}W (${r.best_season_year})`,
      },
    ],
    [],
  );

  const awardCols = useMemo<MRT_ColumnDef<SeasonAwards>[]>(
    () => [
      { accessorKey: "year", header: "Year", size: 80 },
      {
        accessorKey: "champion",
        header: "Champion",
        Cell: ({ cell }) => (
          <Badge variant="light" color="teal">
            🏆 {cell.getValue<string>()}
          </Badge>
        ),
      },
      { accessorKey: "coach_of_year", header: "Coach of Year" },
      { accessorKey: "highest_scoring", header: "Top Offense" },
      { accessorKey: "best_defense", header: "Top Defense" },
    ],
    [],
  );

  const histTable = useDataGrid(histCols, histories.data ?? [], {
    isLoading: histories.isLoading,
    sorting: [{ id: "win_percentage", desc: true }],
  });
  const awardTable = useDataGrid(awardCols, awards.data ?? [], {
    isLoading: awards.isLoading,
    sorting: [{ id: "year", desc: true }],
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
          Dynasty not loaded.{" "}
          <Anchor component={Link} to="/dynasty">
            Back to Dynasties
          </Anchor>
        </Text>
      </Card>
    );
  }

  const s = status.data!;
  const c = s.coach;

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/dynasty" size="sm">
          Dynasties
        </Anchor>
        <Text size="sm">{s.dynasty_name}</Text>
      </Breadcrumbs>

      <Group gap="xs">
        <IconCrown size={22} color="var(--mantine-color-grape-6)" />
        <Title order={2}>{s.dynasty_name}</Title>
        <Badge variant="light" color="grape">
          Year {s.current_year}
        </Badge>
      </Group>

      <Card>
        <Group justify="space-between" wrap="wrap">
          <Stack gap={2}>
            <Text fw={600}>{c.name}</Text>
            <Text size="sm" c="dimmed">
              {c.team} · {c.years_coached} seasons
            </Text>
          </Stack>
          <Group gap="xl">
            <Stat label="Career" value={`${c.career_wins}-${c.career_losses}`} />
            <Stat label="Win %" value={(c.win_percentage * 100).toFixed(1)} />
            <Stat label="Titles" value={c.championships} accent />
            <Stat label="Playoffs" value={c.playoff_appearances} />
            <Stat label="Conf titles" value={c.conference_titles} />
          </Group>
        </Group>
      </Card>

      <DynastyCommand sid={sessionId} status={s} />

      <Tabs defaultValue="histories" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="histories">Team Histories</Tabs.Tab>
          <Tabs.Tab value="programs">Programs</Tabs.Tab>
          <Tabs.Tab value="awards">Awards</Tabs.Tab>
          <Tabs.Tab value="records">Record Book</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="histories" pt="md">
          <MantineReactTable table={histTable} />
        </Tabs.Panel>
        <Tabs.Panel value="programs" pt="md">
          <ProgramsManager sid={sessionId} />
        </Tabs.Panel>
        <Tabs.Panel value="awards" pt="md">
          <MantineReactTable table={awardTable} />
        </Tabs.Panel>
        <Tabs.Panel value="records" pt="md">
          {(() => {
            const rb = recordBook.data;
            const set = RECORDS.filter((r) => rb?.[r.key] && (rb[r.key].team || rb[r.key].coach));
            if (!rb || set.length === 0) return <Text c="dimmed">No records yet.</Text>;
            return (
              <SimpleGrid cols={{ base: 2, sm: 3, lg: 4 }}>
                {set.map((r) => {
                  const e = rb[r.key];
                  const raw = e[r.value];
                  const shown = typeof raw === "number" && r.format ? r.format(raw) : String(raw ?? "");
                  const holder = e.team ?? e.coach;
                  return (
                    <Card key={r.key} padding="md">
                      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        {r.label}
                      </Text>
                      <Text size="xl" fw={800} mt={4}>
                        {shown}
                      </Text>
                      <Text size="sm">
                        {holder}
                        {e.year != null ? `, ${e.year}` : ""}
                      </Text>
                    </Card>
                  );
                })}
              </SimpleGrid>
            );
          })()}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

function Stat({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <Stack gap={0} align="center">
      <Text size="lg" fw={800} c={accent ? "grape" : undefined}>
        {value}
      </Text>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
    </Stack>
  );
}
