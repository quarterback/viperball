import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Text,
  Card,
  Badge,
  Button,
  TextInput,
  NumberInput,
  Select,
  SimpleGrid,
  Loader,
  Center,
  Collapse,
} from "@mantine/core";
import { IconPlus, IconArchive, IconRotate } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../../components/DataGrid";
import { dynastyApi, type Program, type AddProgramBody } from "../../api/dynasty";

const ARCHETYPES = [
  "blue_blood",
  "national_power",
  "regional_power",
  "rebuilding",
  "doormat",
];

export function ProgramsManager({ sid }: { sid: string }) {
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const q = useQuery({ queryKey: ["programs", sid], queryFn: () => dynastyApi.programs(sid) });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["programs", sid] });

  const retire = useMutation({
    mutationFn: (team: string) => dynastyApi.retireProgram(sid, team),
    onSuccess: () => {
      notifications.show({ message: "Program retired (applies next season)", color: "grape" });
      invalidate();
    },
  });
  const restore = useMutation({
    mutationFn: ({ team, conf }: { team: string; conf?: string }) =>
      dynastyApi.restoreProgram(sid, team, conf),
    onSuccess: () => {
      notifications.show({ message: "Program restored", color: "grape" });
      invalidate();
    },
  });

  const cols = useMemo<MRT_ColumnDef<Program>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Program",
        Cell: ({ row }) => (
          <Group gap={6}>
            <Text size="sm" fw={600} c={row.original.retired ? "dimmed" : undefined}>
              {row.original.name}
            </Text>
            {row.original.custom && (
              <Badge size="xs" variant="light" color="cyan">
                new
              </Badge>
            )}
            {row.original.retired && (
              <Badge size="xs" variant="light" color="gray">
                retired
              </Badge>
            )}
          </Group>
        ),
      },
      { accessorKey: "conference", header: "Conference", Cell: ({ cell }) => cell.getValue<string>() ?? "—" },
      { accessorKey: "prestige", header: "Prestige", size: 90 },
      {
        header: "All-time",
        id: "record",
        size: 110,
        accessorFn: (r) => `${r.wins}-${r.losses}`,
      },
      {
        accessorKey: "championships",
        header: "Titles",
        size: 80,
        Cell: ({ cell }) =>
          cell.getValue<number>() ? (
            <Badge variant="light" color="grape">
              {cell.getValue<number>()}
            </Badge>
          ) : (
            "0"
          ),
      },
    ],
    [],
  );

  const conferences = q.data?.conferences ?? [];
  const table = useDataGrid(cols, q.data?.programs ?? [], {
    isLoading: q.isLoading,
    sorting: [{ id: "name", desc: false }],
    extra: {
      enableRowActions: true,
      positionActionsColumn: "last",
      renderRowActions: ({ row }: { row: { original: Program } }) =>
        row.original.retired ? (
          <Button
            size="compact-xs"
            variant="light"
            leftSection={<IconRotate size={14} />}
            onClick={() => restore.mutate({ team: row.original.name, conf: conferences[0] })}
          >
            Restore
          </Button>
        ) : (
          <Button
            size="compact-xs"
            variant="light"
            color="orange"
            leftSection={<IconArchive size={14} />}
            onClick={() => retire.mutate(row.original.name)}
          >
            Retire
          </Button>
        ),
    },
  });

  if (q.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          Add or retire programs. Changes take effect at the next season start, when the
          schedule rebuilds. Retired programs keep their pages/history; their non-graduating
          players disperse to other teams.
        </Text>
        <Button size="xs" leftSection={<IconPlus size={14} />} onClick={() => setAddOpen((o) => !o)}>
          Add program
        </Button>
      </Group>

      <Collapse in={addOpen}>
        <AddProgramForm sid={sid} conferences={conferences} onDone={() => { setAddOpen(false); invalidate(); }} />
      </Collapse>

      <MantineReactTable table={table} />
    </Stack>
  );
}

function AddProgramForm({
  sid,
  conferences,
  onDone,
}: {
  sid: string;
  conferences: string[];
  onDone: () => void;
}) {
  const [f, setF] = useState<AddProgramBody>({
    team_name: "",
    conference: conferences[0] ?? "",
    mascot: "",
    city: "",
    state: "",
    prestige: 45,
    program_archetype: "regional_power",
  });
  const set = <K extends keyof AddProgramBody>(k: K, v: AddProgramBody[K]) =>
    setF((s) => ({ ...s, [k]: v }));

  const add = useMutation({
    mutationFn: () => dynastyApi.addProgram(sid, f),
    onSuccess: () => {
      notifications.show({ message: `Added ${f.team_name} (joins next season)`, color: "cyan" });
      onDone();
    },
    onError: () => notifications.show({ message: "Add failed (name taken?)", color: "red" }),
  });

  return (
    <Card withBorder>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        <TextInput label="Program name" value={f.team_name} onChange={(e) => set("team_name", e.currentTarget.value)} />
        <Select label="Conference" data={conferences} value={f.conference} onChange={(v) => set("conference", v ?? "")} searchable />
        <TextInput label="Mascot" value={f.mascot} onChange={(e) => set("mascot", e.currentTarget.value)} />
        <TextInput label="City" value={f.city} onChange={(e) => set("city", e.currentTarget.value)} />
        <TextInput label="State" value={f.state} onChange={(e) => set("state", e.currentTarget.value)} />
        <NumberInput label="Prestige" value={f.prestige} min={0} max={99} onChange={(v) => set("prestige", Number(v) || 0)} />
        <Select label="Archetype" data={ARCHETYPES} value={f.program_archetype ?? "regional_power"} onChange={(v) => set("program_archetype", v)} />
      </SimpleGrid>
      <Group justify="flex-end" mt="md">
        <Button onClick={() => add.mutate()} loading={add.isPending} disabled={!f.team_name.trim() || !f.conference}>
          Add program
        </Button>
      </Group>
    </Card>
  );
}
