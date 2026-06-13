import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Select,
  Loader,
  Center,
  Tabs,
  Badge,
  SimpleGrid,
} from "@mantine/core";
import { IconSchool, IconStarFilled } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../components/DataGrid";
import { dynastyApi } from "../api/dynasty";
import { recruitingApi, type ProspectRow } from "../api/recruiting";

const GRADE_LABEL: Record<string, string> = {
  "12th": "Incoming (12th)",
  "11th": "11th",
  "10th": "10th",
  "9th": "9th",
};

function Stars({ n }: { n: number }) {
  return (
    <Group gap={1} wrap="nowrap">
      {Array.from({ length: n }).map((_, i) => (
        <IconStarFilled key={i} size={11} color="var(--mantine-color-yellow-6)" />
      ))}
    </Group>
  );
}

function Board({ sid, grade }: { sid: string; grade: string }) {
  const q = useQuery({
    queryKey: ["recruiting-pipeline", sid, grade],
    queryFn: () => recruitingApi.pipeline(sid, grade),
  });

  const cols = useMemo<MRT_ColumnDef<ProspectRow>[]>(
    () => [
      { accessorKey: "rank", header: "#", size: 55 },
      { accessorKey: "name", header: "Recruit" },
      { accessorKey: "position", header: "Pos", size: 80 },
      {
        accessorKey: "scouted_stars",
        header: "Stars",
        size: 90,
        Cell: ({ cell }) => <Stars n={cell.getValue<number>()} />,
      },
      {
        accessorKey: "is_alpha",
        header: "Tier",
        size: 80,
        Cell: ({ row }) =>
          row.original.flag === "BREAKOUT" ? (
            <Badge size="xs" color="grape" variant="light">breakout</Badge>
          ) : row.original.is_alpha ? (
            <Badge size="xs" color="teal" variant="light">alpha</Badge>
          ) : null,
      },
      { accessorKey: "hometown", header: "Hometown" },
      { accessorKey: "region", header: "Region", size: 110 },
      { accessorKey: "height", header: "Ht", size: 65 },
      { accessorKey: "weight", header: "Wt", size: 65 },
      {
        id: "top_attr",
        header: "Top traits",
        Cell: ({ row }) => {
          const a = row.original.visible_attributes ?? {};
          const top = Object.entries(a)
            .sort((x, y) => y[1] - x[1])
            .slice(0, 3)
            .map(([k, v]) => `${k.slice(0, 3).toUpperCase()} ${v}`)
            .join("  ");
          return <Text size="xs" c="dimmed">{top}</Text>;
        },
      },
      { accessorKey: "gpa", header: "GPA", size: 70 },
    ],
    [],
  );

  const table = useDataGrid(cols, q.data?.board ?? [], {
    isLoading: q.isLoading,
    sorting: [{ id: "rank", desc: false }],
    maxHeight: "60vh",
    paginateOver: 50,
  });

  const summary = q.data?.summary?.[grade];

  return (
    <Stack gap="sm">
      {summary && (
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          <Card withBorder padding="xs">
            <Text size="xs" c="dimmed">Prospects</Text>
            <Text fw={700}>{summary.count}</Text>
          </Card>
          <Card withBorder padding="xs">
            <Text size="xs" c="dimmed">5-star</Text>
            <Text fw={700}>{summary.five_star ?? 0}</Text>
          </Card>
          <Card withBorder padding="xs">
            <Text size="xs" c="dimmed">4-star</Text>
            <Text fw={700}>{summary.four_star ?? 0}</Text>
          </Card>
          <Card withBorder padding="xs">
            <Text size="xs" c="dimmed">Avg stars</Text>
            <Text fw={700}>{summary.avg_scouted_stars ?? "—"}</Text>
          </Card>
        </SimpleGrid>
      )}
      <MantineReactTable table={table} />
    </Stack>
  );
}

export function Recruiting() {
  const dynasties = useQuery({ queryKey: ["dynasties"], queryFn: dynastyApi.list });
  const [saveKey, setSaveKey] = useState<string | null>(null);
  const [grade, setGrade] = useState("12th");

  // Open the chosen dynasty into a live session to read its pipeline.
  const session = useQuery({
    queryKey: ["dynasty-open", saveKey],
    queryFn: () => dynastyApi.open(saveKey!),
    enabled: !!saveKey,
  });

  const dynOpts = (dynasties.data ?? []).map((d) => ({
    value: d.save_key,
    label: `${d.dynasty_name} — ${d.coach_team} (Y${d.current_year})`,
  }));

  return (
    <Stack gap="md">
      <Group gap="xs">
        <IconSchool size={22} color="var(--mantine-color-teal-6)" />
        <Title order={2}>Recruiting</Title>
      </Group>
      <Text c="dimmed" size="sm" mt={-8}>
        Scan the incoming recruit class for any dynasty — before the offseason. Signing still
        happens in the dynasty offseason; this is the board to scope who's coming.
      </Text>

      <Card>
        <Group align="flex-end">
          <Select
            label="Dynasty"
            placeholder={dynasties.isLoading ? "Loading…" : "Pick a dynasty"}
            data={dynOpts}
            value={saveKey}
            onChange={setSaveKey}
            searchable
            w={360}
            disabled={dynasties.isLoading}
            nothingFoundMessage="No saved dynasties"
          />
        </Group>
      </Card>

      {!saveKey && (
        <Card>
          <Text c="dimmed">
            Pick a dynasty above to scan its recruit pipeline. No dynasties? Create one under{" "}
            <b>Dynasty → New Dynasty</b>.
          </Text>
        </Card>
      )}

      {saveKey && session.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {saveKey && session.isError && (
        <Card>
          <Text c="red">Couldn't open that dynasty.</Text>
        </Card>
      )}

      {saveKey && session.data && (
        <Tabs value={grade} onChange={(v) => setGrade(v ?? "12th")} keepMounted={false}>
          <Tabs.List>
            {["12th", "11th", "10th", "9th"].map((g) => (
              <Tabs.Tab key={g} value={g}>
                {GRADE_LABEL[g]}
              </Tabs.Tab>
            ))}
          </Tabs.List>
          <Tabs.Panel value={grade} pt="md">
            <Board sid={session.data} grade={grade} />
          </Tabs.Panel>
        </Tabs>
      )}
    </Stack>
  );
}
