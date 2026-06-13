import { useMemo } from "react";
import {
  MantineReactTable,
  useMantineReactTable,
  type MRT_ColumnDef,
} from "mantine-react-table";
import {
  Badge,
  Button,
  Group,
  Menu,
  ActionIcon,
  Stack,
  Title,
  Text,
  Tooltip,
} from "@mantine/core";
import {
  IconDots,
  IconGitFork,
  IconTrash,
  IconPencil,
  IconPlus,
  IconPlayerPlay,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import dayjs from "dayjs";
import {
  listSaves,
  forkSave,
  deleteSave,
  type SaveSummary,
  type SaveMode,
} from "../api/saves";

const MODE_COLOR: Record<SaveMode, string> = {
  college: "indigo",
  dynasty: "grape",
  pro: "teal",
  wvl: "orange",
  fiv: "cyan",
};

export function SavesLibrary() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery({
    queryKey: ["saves"],
    queryFn: listSaves,
  });

  const fork = useMutation({
    mutationFn: forkSave,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saves"] }),
  });
  const remove = useMutation({
    mutationFn: deleteSave,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saves"] }),
  });

  const columns = useMemo<MRT_ColumnDef<SaveSummary>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Experiment",
        Cell: ({ row }) => (
          <Stack gap={2}>
            <Text fw={600}>{row.original.name}</Text>
            {row.original.notes && (
              <Text size="xs" c="dimmed" lineClamp={1}>
                {row.original.notes}
              </Text>
            )}
          </Stack>
        ),
      },
      {
        accessorKey: "mode",
        header: "Mode",
        size: 110,
        Cell: ({ cell }) => {
          const mode = cell.getValue<SaveMode>();
          return (
            <Badge variant="light" color={MODE_COLOR[mode]} radius="sm">
              {mode}
            </Badge>
          );
        },
      },
      { accessorKey: "teams", header: "Teams" },
      { accessorKey: "progress", header: "Progress", size: 150 },
      {
        accessorKey: "seed",
        header: "Seed",
        size: 90,
        Cell: ({ cell }) =>
          cell.getValue<number | null>() ?? (
            <Text size="xs" c="dimmed">
              random
            </Text>
          ),
      },
      {
        accessorKey: "tags",
        header: "Tags",
        enableSorting: false,
        Cell: ({ cell }) => (
          <Group gap={4}>
            {cell.getValue<string[]>().map((t) => (
              <Badge key={t} size="xs" variant="dot" color="gray">
                {t}
              </Badge>
            ))}
          </Group>
        ),
      },
      {
        accessorKey: "lastSimmedAt",
        header: "Last simmed",
        size: 130,
        Cell: ({ cell }) => (
          <Tooltip label={dayjs(cell.getValue<string>()).format("YYYY-MM-DD HH:mm")}>
            <Text size="sm">{dayjs(cell.getValue<string>()).fromNow()}</Text>
          </Tooltip>
        ),
      },
    ],
    [],
  );

  const table = useMantineReactTable({
    columns,
    data,
    state: { isLoading },
    enableRowActions: true,
    positionActionsColumn: "last",
    initialState: {
      density: "xs",
      sorting: [{ id: "lastSimmedAt", desc: true }],
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    renderRowActions: ({ row }) => (
      <Group gap={4} wrap="nowrap">
        <Tooltip label="Open">
          <ActionIcon
            variant="subtle"
            onClick={() => navigate(`/league?save=${row.original.id}`)}
          >
            <IconPlayerPlay size={16} />
          </ActionIcon>
        </Tooltip>
        <Menu withinPortal position="bottom-end">
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray">
              <IconDots size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              leftSection={<IconGitFork size={14} />}
              onClick={() => fork.mutate(row.original.id)}
            >
              Fork experiment
            </Menu.Item>
            <Menu.Item leftSection={<IconPencil size={14} />} disabled>
              Rename / tag
            </Menu.Item>
            <Menu.Divider />
            <Menu.Item
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={() => remove.mutate(row.original.id)}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
    ),
  });

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>Saves & Experiments</Title>
          <Text c="dimmed" size="sm">
            Every run is a save you can open, fork, compare, and export.
          </Text>
        </Stack>
        <Button
          component={Link}
          to="/league/new"
          leftSection={<IconPlus size={16} />}
          variant="filled"
        >
          New experiment
        </Button>
      </Group>
      <MantineReactTable table={table} />
    </Stack>
  );
}
