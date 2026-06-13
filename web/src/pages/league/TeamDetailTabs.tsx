import { useMemo } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import { Stack, Card, Text, Group, Badge, SimpleGrid, Loader, Center } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useDataGrid } from "../../components/DataGrid";
import {
  seasonApi,
  type ChemPlayer,
  type CoachCardLite,
} from "../../api/season";

// ── Team chemistry ──────────────────────────────────────────────
export function ChemistryTab({ sid, team }: { sid: string; team: string }) {
  const q = useQuery({
    queryKey: ["chemistry", sid, team],
    queryFn: () => seasonApi.chemistry(sid, team),
  });
  const cols = useMemo<MRT_ColumnDef<ChemPlayer>[]>(
    () => [
      { accessorKey: "name", header: "Player" },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "overall", header: "OVR", size: 70 },
      { accessorKey: "voice", header: "Voice", size: 80 },
      { accessorKey: "glue", header: "Glue", size: 80 },
      { accessorKey: "pull", header: "Pull", size: 80 },
      { accessorKey: "reach", header: "Reach", size: 80 },
      {
        accessorKey: "drama_current",
        header: "Drama",
        size: 80,
        Cell: ({ cell }) => cell.getValue<number>() ?? "—",
      },
      {
        accessorKey: "fit",
        header: "Fit",
        size: 70,
        Cell: ({ cell }) => cell.getValue<number>() ?? "—",
      },
    ],
    [],
  );
  const table = useDataGrid(cols, q.data?.players ?? [], {
    isLoading: q.isLoading,
    sorting: [{ id: "glue", desc: true }],
  });
  if (q.isLoading)
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  const hc = q.data?.hc;
  return (
    <Stack gap="md">
      {hc && (hc.name || hc.chemistry_archetype) && (
        <Card withBorder padding="sm">
          <Group gap="xs">
            <Text size="sm" c="dimmed">
              Head coach:
            </Text>
            <Text fw={600} size="sm">
              {hc.name}
            </Text>
            {hc.classification && (
              <Badge size="xs" variant="light">
                {hc.classification}
              </Badge>
            )}
            {hc.chemistry_archetype && (
              <Badge size="xs" variant="light" color="grape">
                {hc.chemistry_archetype}
              </Badge>
            )}
          </Group>
          {hc.message && (
            <Text size="xs" c="dimmed" mt={4}>
              {hc.message}
            </Text>
          )}
        </Card>
      )}
      <MantineReactTable table={table} />
    </Stack>
  );
}

// ── Coaching staff ──────────────────────────────────────────────
export function CoachingTab({ sid, team }: { sid: string; team: string }) {
  const q = useQuery({
    queryKey: ["coaching-staff", sid, team],
    queryFn: () => seasonApi.coachingStaff(sid, team),
  });
  if (q.isLoading)
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  const raw = q.data?.staff;
  const staff: { role: string; card: CoachCardLite }[] = raw
    ? Array.isArray(raw)
      ? raw.map((c) => ({ role: c.role ?? "", card: c }))
      : Object.entries(raw).map(([role, card]) => ({ role, card }))
    : [];
  if (!staff.length) return <Text c="dimmed">No coaching staff data.</Text>;

  return (
    <Stack gap="md">
      {q.data?.dev_aura_max_boost_pct != null && (
        <Badge variant="light" color="teal" w="fit-content">
          Development aura: +{q.data.dev_aura_max_boost_pct}% max
        </Badge>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {staff.map(({ role, card }, i) => (
          <Card key={i} withBorder padding="sm">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              {(role || (card.role as string) || "Coach").replace(/_/g, " ")}
            </Text>
            <Text fw={600}>{card.name ?? "—"}</Text>
            <Group gap="xs" mt={4}>
              {card.classification && (
                <Badge size="xs" variant="light">
                  {card.classification}
                </Badge>
              )}
              {card.overall != null && (
                <Badge size="xs" variant="light" color="gray">
                  OVR {card.overall}
                </Badge>
              )}
            </Group>
          </Card>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
