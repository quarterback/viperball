import { useMemo, useState } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import {
  Stack,
  Group,
  Text,
  Card,
  Stepper,
  Button,
  NumberInput,
  Badge,
  SimpleGrid,
  Loader,
  Center,
  Tooltip,
} from "@mantine/core";
import { IconCheck, IconCoin, IconStar } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../../components/DataGrid";
import {
  offseasonApi,
  type PortalEntry,
  type Recruit,
} from "../../api/dynasty";

const PHASES = ["nil", "portal", "recruiting", "ready"];
const money = (n: number) => `$${(n / 1000).toFixed(0)}k`;

export function OffseasonFlow({ sid, onComplete }: { sid: string; onComplete: () => void }) {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["offseason-status", sid],
    queryFn: () => offseasonApi.status(sid),
  });
  const phase = status.data?.phase ?? "nil";
  const activeStep = Math.max(0, PHASES.indexOf(phase));

  const refetchAll = () =>
    ["offseason-status", "offseason-nil", "offseason-portal", "offseason-recruiting"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k, sid] }),
    );

  if (status.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Card>
      <Group justify="space-between" mb="md">
        <Text fw={700}>Offseason</Text>
        <Badge variant="light" color="grape">
          {phase}
        </Badge>
      </Group>
      <Stepper active={activeStep} size="sm" mb="md">
        <Stepper.Step label="NIL" />
        <Stepper.Step label="Portal" />
        <Stepper.Step label="Recruiting" />
        <Stepper.Step label="Finalize" />
      </Stepper>

      {phase === "nil" && <NilPhase sid={sid} onDone={refetchAll} />}
      {phase === "portal" && <PortalPhase sid={sid} onDone={refetchAll} />}
      {phase === "recruiting" && <RecruitingPhase sid={sid} onDone={refetchAll} />}
      {phase === "ready" && <ReadyPhase sid={sid} onComplete={onComplete} />}
    </Card>
  );
}

// ── NIL allocation ──────────────────────────────────────────────
function NilPhase({ sid, onDone }: { sid: string; onDone: () => void }) {
  const nil = useQuery({ queryKey: ["offseason-nil", sid], queryFn: () => offseasonApi.nil(sid) });
  const [recruiting, setRecruiting] = useState(0);
  const [portal, setPortal] = useState(0);
  const [retention, setRetention] = useState(0);

  const allocate = useMutation({
    mutationFn: () => offseasonApi.allocateNil(sid, recruiting, portal, retention),
    onSuccess: () => {
      notifications.show({ message: "Budget allocated", color: "grape" });
      onDone();
    },
    onError: () => notifications.show({ message: "Allocation failed", color: "red" }),
  });

  if (nil.isLoading) return <Loader size="sm" />;
  const budget = nil.data?.annual_budget ?? 0;
  const remaining = budget - recruiting - portal - retention;

  return (
    <Stack gap="md">
      <Group gap="xs">
        <IconCoin size={16} color="var(--mantine-color-yellow-6)" />
        <Text size="sm">
          Annual NIL budget: <b>{money(budget)}</b> · Unallocated:{" "}
          <Text span c={remaining < 0 ? "red" : "dimmed"}>
            {money(remaining)}
          </Text>
        </Text>
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <NumberInput label="Recruiting pool" value={recruiting} min={0} step={1000} onChange={(v) => setRecruiting(Number(v) || 0)} />
        <NumberInput label="Portal pool" value={portal} min={0} step={1000} onChange={(v) => setPortal(Number(v) || 0)} />
        <NumberInput label="Retention pool" value={retention} min={0} step={1000} onChange={(v) => setRetention(Number(v) || 0)} />
      </SimpleGrid>
      <Button
        onClick={() => allocate.mutate()}
        loading={allocate.isPending}
        disabled={remaining < 0}
        w="fit-content"
      >
        Allocate &amp; continue to portal
      </Button>
    </Stack>
  );
}

// ── Transfer portal ─────────────────────────────────────────────
function PortalPhase({ sid, onDone }: { sid: string; onDone: () => void }) {
  const qc = useQueryClient();
  const portal = useQuery({
    queryKey: ["offseason-portal", sid],
    queryFn: () => offseasonApi.portal(sid),
  });

  const refetch = () => qc.invalidateQueries({ queryKey: ["offseason-portal", sid] });
  const offer = useMutation({
    mutationFn: (i: number) => offseasonApi.portalOffer(sid, i, 0),
    onSuccess: refetch,
  });
  const commit = useMutation({
    mutationFn: (i: number) => offseasonApi.portalCommit(sid, i),
    onSuccess: refetch,
  });
  const resolve = useMutation({
    mutationFn: () => offseasonApi.portalResolve(sid),
    onSuccess: () => {
      notifications.show({ message: "Portal resolved", color: "grape" });
      onDone();
    },
  });

  const cols = useMemo<MRT_ColumnDef<PortalEntry>[]>(
    () => [
      { accessorKey: "player_name", header: "Player" },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "overall", header: "OVR", size: 70 },
      { accessorKey: "year", header: "Yr", size: 80 },
      { accessorKey: "origin_team", header: "From" },
      { accessorKey: "offers_count", header: "Offers", size: 80 },
    ],
    [],
  );
  const table = useDataGrid(cols, portal.data?.entries ?? [], {
    isLoading: portal.isLoading,
    sorting: [{ id: "overall", desc: true }],
    maxHeight: "44vh",
    extra: {
      enableRowActions: true,
      positionActionsColumn: "last",
      renderRowActions: ({ row }: { row: { original: PortalEntry } }) => (
        <Group gap={4} wrap="nowrap">
          <Button size="compact-xs" variant="light" onClick={() => offer.mutate(row.original.global_index)}>
            Offer
          </Button>
          <Button size="compact-xs" onClick={() => commit.mutate(row.original.global_index)}>
            Sign
          </Button>
        </Group>
      ),
    },
  });

  return (
    <Stack gap="sm">
      <MantineReactTable table={table} />
      <Button
        color="grape"
        onClick={() => resolve.mutate()}
        loading={resolve.isPending}
        w="fit-content"
      >
        Resolve portal &amp; continue to recruiting
      </Button>
    </Stack>
  );
}

// ── Recruiting ──────────────────────────────────────────────────
function RecruitingPhase({ sid, onDone }: { sid: string; onDone: () => void }) {
  const qc = useQueryClient();
  const rec = useQuery({
    queryKey: ["offseason-recruiting", sid],
    queryFn: () => offseasonApi.recruiting(sid),
  });
  const refetch = () => qc.invalidateQueries({ queryKey: ["offseason-recruiting", sid] });
  const scout = useMutation({
    mutationFn: ({ i, level }: { i: number; level: "basic" | "full" }) =>
      offseasonApi.scout(sid, i, level),
    onSuccess: refetch,
  });
  const offer = useMutation({
    mutationFn: (i: number) => offseasonApi.recruitOffer(sid, i),
    onSuccess: refetch,
  });
  const resolve = useMutation({
    mutationFn: () => offseasonApi.recruitResolve(sid),
    onSuccess: () => {
      notifications.show({ message: "Recruiting resolved", color: "grape" });
      onDone();
    },
  });

  const cols = useMemo<MRT_ColumnDef<Recruit>[]>(
    () => [
      { accessorKey: "name", header: "Recruit" },
      { accessorKey: "position", header: "Pos", size: 70 },
      {
        accessorKey: "stars",
        header: "Stars",
        size: 90,
        Cell: ({ cell }) => (
          <Group gap={1}>
            {Array.from({ length: cell.getValue<number>() }).map((_, i) => (
              <IconStar key={i} size={12} fill="var(--mantine-color-yellow-5)" color="var(--mantine-color-yellow-6)" />
            ))}
          </Group>
        ),
      },
      { accessorKey: "region", header: "Region" },
      {
        accessorKey: "scout_level",
        header: "Scouted",
        size: 90,
        Cell: ({ cell }) => {
          const v = cell.getValue<string>();
          return v === "none" ? <Text size="xs" c="dimmed">—</Text> : <Badge size="xs" variant="light">{v}</Badge>;
        },
      },
      {
        accessorKey: "true_overall",
        header: "OVR",
        size: 70,
        Cell: ({ cell }) => cell.getValue<number>() ?? <Text size="xs" c="dimmed">?</Text>,
      },
    ],
    [],
  );
  const table = useDataGrid(cols, rec.data?.recruits ?? [], {
    isLoading: rec.isLoading,
    sorting: [{ id: "stars", desc: true }],
    maxHeight: "40vh",
    extra: {
      enableRowActions: true,
      positionActionsColumn: "last",
      renderRowActions: ({ row }: { row: { original: Recruit } }) => (
        <Group gap={4} wrap="nowrap">
          <Tooltip label="Scout (1 pt)">
            <Button size="compact-xs" variant="subtle" onClick={() => scout.mutate({ i: row.original.pool_index, level: "basic" })}>
              Scout
            </Button>
          </Tooltip>
          <Tooltip label="Full scout (3 pts)">
            <Button size="compact-xs" variant="subtle" onClick={() => scout.mutate({ i: row.original.pool_index, level: "full" })}>
              Full
            </Button>
          </Tooltip>
          <Button size="compact-xs" onClick={() => offer.mutate(row.original.pool_index)}>
            Offer
          </Button>
        </Group>
      ),
    },
  });

  return (
    <Stack gap="sm">
      {rec.data?.board && (
        <Group gap="lg">
          <Text size="sm">
            Scholarships: <b>{rec.data.board.scholarships_available}</b>
          </Text>
          <Text size="sm">
            Scouting points: <b>{rec.data.board.scouting_points}</b>
          </Text>
          <Text size="sm">
            Max offers: <b>{rec.data.board.max_offers}</b>
          </Text>
        </Group>
      )}
      <MantineReactTable table={table} />
      <Button color="grape" onClick={() => resolve.mutate()} loading={resolve.isPending} w="fit-content">
        Resolve recruiting &amp; finish offseason
      </Button>
    </Stack>
  );
}

// ── Finalize ────────────────────────────────────────────────────
function ReadyPhase({ sid, onComplete }: { sid: string; onComplete: () => void }) {
  const complete = useMutation({
    mutationFn: () => offseasonApi.complete(sid),
    onSuccess: () => {
      notifications.show({ message: "Offseason complete — ready for next season", color: "grape" });
      onComplete();
    },
    onError: () => notifications.show({ message: "Finalize failed", color: "red" }),
  });
  return (
    <Stack gap="sm" align="flex-start">
      <Group gap="xs">
        <IconCheck size={18} color="var(--mantine-color-teal-6)" />
        <Text>Offseason moves complete. Finalize to roll rosters into next season.</Text>
      </Group>
      <Button color="grape" onClick={() => complete.mutate()} loading={complete.isPending}>
        Finalize &amp; continue
      </Button>
    </Stack>
  );
}
