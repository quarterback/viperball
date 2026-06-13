import { useMemo } from "react";
import { MantineReactTable, type MRT_ColumnDef } from "mantine-react-table";
import { Card, Group, Text, Button, Badge } from "@mantine/core";
import { IconArrowsExchange, IconPlayerSkipForward } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { useDataGrid } from "../../components/DataGrid";
import { seasonApi, type SeasonPortalEntry } from "../../api/season";

/**
 * Pre-season transfer portal. The season opens in phase "portal"; you sign
 * transfers (if you have a human team) and/or skip to start the regular season.
 * The old app gated simming on clearing this; the SPA now does too.
 */
export function SeasonPortalPanel({ sid, onDone }: { sid: string; onDone: () => void }) {
  const qc = useQueryClient();
  const portal = useQuery({
    queryKey: ["season-portal", sid],
    queryFn: () => seasonApi.portal(sid),
  });

  const team = portal.data?.human_team ?? "";

  const commit = useMutation({
    mutationFn: (entry_index: number) => seasonApi.portalCommit(sid, team, entry_index),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["season-portal", sid] }),
    onError: () => notifications.show({ message: "Couldn't sign player", color: "red" }),
  });
  const skip = useMutation({
    mutationFn: () => seasonApi.portalSkip(sid),
    onSuccess: () => {
      notifications.show({ message: "Portal closed — regular season started", color: "indigo" });
      onDone();
    },
    onError: () => notifications.show({ message: "Couldn't start the season", color: "red" }),
  });

  const cols = useMemo<MRT_ColumnDef<SeasonPortalEntry>[]>(
    () => [
      {
        id: "name",
        header: "Player",
        accessorFn: (e) => e.player_name ?? e.name ?? "",
      },
      { accessorKey: "position", header: "Pos", size: 70 },
      { accessorKey: "overall", header: "OVR", size: 70 },
      { accessorKey: "year", header: "Yr", size: 80 },
      {
        id: "from",
        header: "From",
        accessorFn: (e) => e.origin_team ?? e.former_team ?? "",
      },
    ],
    [],
  );

  const entries = portal.data?.entries ?? [];
  const table = useDataGrid(cols, entries, {
    isLoading: portal.isLoading,
    sorting: [{ id: "overall", desc: true }],
    maxHeight: "44vh",
    extra: team
      ? {
          enableRowActions: true,
          positionActionsColumn: "last",
          renderRowActions: ({ row }: { row: { original: SeasonPortalEntry } }) => (
            <Button size="compact-xs" onClick={() => commit.mutate(row.original.global_index)}>
              Sign
            </Button>
          ),
        }
      : {},
  });

  return (
    <Card>
      <Group justify="space-between" mb="md">
        <Group gap="xs">
          <IconArrowsExchange size={18} color="var(--mantine-color-indigo-6)" />
          <Text fw={700}>Pre-season transfer portal</Text>
          {team && (
            <Badge variant="light">
              {team} · {portal.data?.transfers_remaining ?? 0} transfers left
            </Badge>
          )}
        </Group>
        <Button
          color="indigo"
          leftSection={<IconPlayerSkipForward size={16} />}
          onClick={() => skip.mutate()}
          loading={skip.isPending}
        >
          {team ? "Done — start regular season" : "Skip portal & start season"}
        </Button>
      </Group>
      {team ? (
        <MantineReactTable table={table} />
      ) : (
        <Text c="dimmed" size="sm">
          All-AI season — no transfers to make. Start the regular season to begin simming.
        </Text>
      )}
    </Card>
  );
}
