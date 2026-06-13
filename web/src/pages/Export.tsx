import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Button,
  Badge,
  Table,
  Anchor,
  Loader,
  Center,
} from "@mantine/core";
import { IconDownload, IconArchive, IconFileExport } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi } from "../api/season";
import {
  exportApi,
  standingsJsonUrl,
  archiveJsonUrl,
  type ArchiveMeta,
} from "../api/exports";

export function Export() {
  const qc = useQueryClient();
  const sessions = useQuery({
    queryKey: ["college-sessions"],
    queryFn: seasonApi.listSessions,
  });
  const archives = useQuery({ queryKey: ["archives"], queryFn: exportApi.archives });

  const archive = useMutation({
    mutationFn: (sid: string) => exportApi.archiveSeason(sid),
    onSuccess: () => {
      notifications.show({ message: "Season archived", color: "indigo" });
      qc.invalidateQueries({ queryKey: ["archives"] });
    },
    onError: () => notifications.show({ message: "Archive failed", color: "red" }),
  });

  return (
    <Stack gap="md">
      <Stack gap={2}>
        <Title order={2}>Export</Title>
        <Text c="dimmed" size="sm">
          Pull standings/box scores out as JSON, or snapshot a finished season to the archive.
        </Text>
      </Stack>

      <Card>
        <Group gap="xs" mb="sm">
          <IconFileExport size={18} color="var(--mantine-color-indigo-6)" />
          <Text fw={600}>Active seasons</Text>
        </Group>
        {sessions.isLoading ? (
          <Center py="md">
            <Loader size="sm" />
          </Center>
        ) : (sessions.data ?? []).length === 0 ? (
          <Text c="dimmed" size="sm">
            No active seasons to export.
          </Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Season</Table.Th>
                <Table.Th>Progress</Table.Th>
                <Table.Th ta="right">Export</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(sessions.data ?? []).map((s) => (
                <Table.Tr key={s.session_id}>
                  <Table.Td>{s.name}</Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      Wk {s.current_week}/{s.total_weeks}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="flex-end">
                      <Button
                        component="a"
                        href={standingsJsonUrl(s.session_id)}
                        target="_blank"
                        rel="noreferrer"
                        size="xs"
                        variant="default"
                        leftSection={<IconDownload size={14} />}
                      >
                        Standings JSON
                      </Button>
                      <Button
                        size="xs"
                        leftSection={<IconArchive size={14} />}
                        onClick={() => archive.mutate(s.session_id)}
                        loading={archive.isPending}
                      >
                        Archive
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Card>
        <Group gap="xs" mb="sm">
          <IconArchive size={18} color="var(--mantine-color-grape-6)" />
          <Text fw={600}>Archived seasons</Text>
        </Group>
        {archives.isLoading ? (
          <Center py="md">
            <Loader size="sm" />
          </Center>
        ) : (archives.data ?? []).length === 0 ? (
          <Text c="dimmed" size="sm">
            No archives yet — archive a finished season above.
          </Text>
        ) : (
          <Stack gap="xs">
            {(archives.data ?? []).map((a: ArchiveMeta) => (
              <Group key={a.save_key} justify="space-between">
                <Group gap="xs">
                  <Text size="sm">{a.label || a.save_key}</Text>
                  <Badge size="xs" variant="light" color="gray">
                    {(a.data_size / 1024).toFixed(0)} KB
                  </Badge>
                </Group>
                <Anchor href={archiveJsonUrl(a.save_key)} target="_blank" rel="noreferrer" size="sm">
                  Download JSON
                </Anchor>
              </Group>
            ))}
          </Stack>
        )}
      </Card>
    </Stack>
  );
}
