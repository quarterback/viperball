import { useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
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
  Anchor,
  Breadcrumbs,
  Badge,
  Loader,
  Center,
  Card,
  Tabs,
  Button,
  ActionIcon,
  Tooltip,
  Modal,
  TextInput,
  NumberInput,
} from "@mantine/core";
import {
  IconChevronRight,
  IconPencil,
  IconArrowsExchange,
  IconPlus,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi, type RosterPlayer } from "../../api/season";
import { ChemistryTab, CoachingTab } from "./TeamDetailTabs";
import { PlayerFormModal, MovePlayerModal } from "./PlayerEditor";

export function TeamPage() {
  const { sessionId = "", teamName = "" } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const team = decodeURIComponent(teamName);

  const roster = useQuery({
    queryKey: ["roster", sessionId, team],
    queryFn: () => seasonApi.roster(sessionId, team),
  });
  const standings = useQuery({
    queryKey: ["standings", sessionId],
    queryFn: () => seasonApi.standings(sessionId),
  });
  const record = standings.data?.find((s) => s.team_name === team);
  const teamNames = useMemo(
    () => (standings.data ?? []).map((s) => s.team_name),
    [standings.data],
  );

  // editor state
  const [editPlayer, setEditPlayer] = useState<RosterPlayer | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [movePlayer, setMovePlayer] = useState<RosterPlayer | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sName, setSName] = useState(team);
  const [sCity, setSCity] = useState("");
  const [sState, setSState] = useState("");
  const [sMascot, setSMascot] = useState("");
  const [sPrestige, setSPrestige] = useState<number>(50);

  const openSettings = () => {
    setSName(team);
    setSCity("");
    setSState("");
    setSMascot("");
    setSPrestige(roster.data?.prestige ?? 50);
    setSettingsOpen(true);
  };

  const saveSettings = useMutation({
    mutationFn: async () => {
      await seasonApi.editTeamMeta(sessionId, team, {
        city: sCity || undefined,
        state: sState || undefined,
        mascot: sMascot || undefined,
        prestige: sPrestige,
      });
      const nm = sName.trim();
      if (nm && nm !== team) return seasonApi.renameTeam(sessionId, team, nm);
      return { new_name: team };
    },
    onSuccess: (res: { new_name: string }) => {
      notifications.show({ message: "Team settings saved", color: "indigo" });
      qc.invalidateQueries({ queryKey: ["standings", sessionId] });
      qc.invalidateQueries({ queryKey: ["roster", sessionId, team] });
      setSettingsOpen(false);
      if (res.new_name !== team) {
        navigate(`/league/${sessionId}/team/${encodeURIComponent(res.new_name)}`, { replace: true });
      }
    },
    onError: () => notifications.show({ message: "Save failed (name taken?)", color: "red" }),
  });

  const cols = useMemo<MRT_ColumnDef<RosterPlayer>[]>(
    () => [
      { accessorKey: "number", header: "#", size: 50 },
      {
        accessorKey: "name",
        header: "Player",
        Cell: ({ row }) => (
          <Anchor
            component={Link}
            to={`/league/${sessionId}/team/${encodeURIComponent(team)}/player/${encodeURIComponent(
              row.original.name,
            )}`}
            fw={600}
          >
            {row.original.name}
          </Anchor>
        ),
      },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "year_abbr", header: "Yr", size: 60 },
      {
        accessorKey: "overall",
        header: "OVR",
        size: 70,
        Cell: ({ cell }) => (
          <Badge variant="light" color={ovrColor(cell.getValue<number>())}>
            {cell.getValue<number>()}
          </Badge>
        ),
      },
      { accessorKey: "speed", header: "SPD", size: 65 },
      { accessorKey: "power", header: "POW", size: 65 },
      { accessorKey: "agility", header: "AGI", size: 65 },
      { accessorKey: "hands", header: "HND", size: 65 },
      { accessorKey: "awareness", header: "AWR", size: 65 },
      { accessorKey: "tackling", header: "TKL", size: 65 },
      { accessorKey: "kicking", header: "KICK", size: 70 },
    ],
    [sessionId, team],
  );

  const table = useMantineReactTable({
    columns: cols,
    data: roster.data?.roster ?? [],
    state: { isLoading: roster.isLoading },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <Group gap={4} wrap="nowrap">
        <Tooltip label="Edit">
          <ActionIcon variant="subtle" onClick={() => setEditPlayer(row.original)}>
            <IconPencil size={16} />
          </ActionIcon>
        </Tooltip>
        <Tooltip label="Move to another team">
          <ActionIcon variant="subtle" color="grape" onClick={() => setMovePlayer(row.original)}>
            <IconArrowsExchange size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>
    ),
    initialState: {
      density: "xs",
      sorting: [{ id: "overall", desc: true }],
      showGlobalFilter: true,
    },
    mantineTableProps: { striped: true, highlightOnHover: true },
    mantineTableContainerProps: { style: { maxHeight: "66vh" } },
  });

  if (roster.isError) {
    return (
      <Card>
        <Text c="red">
          Couldn't load this roster — the season may have expired.{" "}
          <Anchor component={Link} to={`/league/${sessionId}`}>
            Back to season
          </Anchor>
        </Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Anchor component={Link} to={`/league/${sessionId}`} size="sm">
          Season
        </Anchor>
        <Text size="sm">{team}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Group gap={6}>
            <Title order={2}>{team}</Title>
            <Tooltip label="Team settings (name, location, prestige)">
              <ActionIcon variant="subtle" color="gray" onClick={openSettings}>
                <IconPencil size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
          {record && (
            <Group gap="xs">
              <Badge variant="light">
                {record.wins}-{record.losses}
                {record.ties ? `-${record.ties}` : ""}
              </Badge>
              <Text size="sm" c="dimmed">
                {record.conference} · PF {record.points_for} / PA {record.points_against}
              </Text>
            </Group>
          )}
        </Stack>
        {roster.data?.prestige != null && (
          <Badge size="lg" variant="light" color="grape">
            Prestige {roster.data.prestige}
          </Badge>
        )}
      </Group>

      {roster.isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : (
        <Tabs defaultValue="roster" keepMounted={false}>
          <Tabs.List>
            <Tabs.Tab value="roster">Roster</Tabs.Tab>
            <Tabs.Tab value="chemistry">Chemistry</Tabs.Tab>
            <Tabs.Tab value="coaching">Coaching</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="roster" pt="md">
            <Group justify="flex-end" mb="xs">
              <Button
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={() => setAddOpen(true)}
              >
                Add player
              </Button>
            </Group>
            <MantineReactTable table={table} />
          </Tabs.Panel>
          <Tabs.Panel value="chemistry" pt="md">
            <ChemistryTab sid={sessionId} team={team} />
          </Tabs.Panel>
          <Tabs.Panel value="coaching" pt="md">
            <CoachingTab sid={sessionId} team={team} />
          </Tabs.Panel>
        </Tabs>
      )}

      {/* editor modals */}
      <PlayerFormModal
        opened={!!editPlayer}
        onClose={() => setEditPlayer(null)}
        sid={sessionId}
        team={team}
        player={editPlayer}
        mode="edit"
      />
      <PlayerFormModal
        opened={addOpen}
        onClose={() => setAddOpen(false)}
        sid={sessionId}
        team={team}
        player={null}
        mode="add"
      />
      <MovePlayerModal
        opened={!!movePlayer}
        onClose={() => setMovePlayer(null)}
        sid={sessionId}
        fromTeam={team}
        player={movePlayer}
        teams={teamNames}
      />
      <Modal opened={settingsOpen} onClose={() => setSettingsOpen(false)} title="Team settings" size="md">
        <Stack gap="sm">
          <TextInput label="Team name" value={sName} onChange={(e) => setSName(e.currentTarget.value)} data-autofocus />
          <Group grow>
            <TextInput label="City" value={sCity} onChange={(e) => setSCity(e.currentTarget.value)} placeholder="(unchanged if blank)" />
            <TextInput label="State" value={sState} onChange={(e) => setSState(e.currentTarget.value)} placeholder="(unchanged if blank)" />
          </Group>
          <Group grow>
            <TextInput label="Mascot" value={sMascot} onChange={(e) => setSMascot(e.currentTarget.value)} placeholder="(unchanged if blank)" />
            <NumberInput label="Prestige" value={sPrestige} min={0} max={99} onChange={(v) => setSPrestige(Number(v) || 0)} />
          </Group>
          <Text size="xs" c="dimmed">
            Renaming updates the schedule, conferences, and standings — best done before simming far.
            Blank city/state/mascot are left unchanged.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSettingsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => saveSettings.mutate()} loading={saveSettings.isPending} disabled={!sName.trim()}>
              Save
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

function ovrColor(ovr: number) {
  if (ovr >= 85) return "teal";
  if (ovr >= 75) return "indigo";
  if (ovr >= 65) return "gray";
  return "red";
}
