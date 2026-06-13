import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Badge,
  Button,
  SimpleGrid,
  Loader,
  Center,
} from "@mantine/core";
import { IconChevronRight, IconPlus, IconStack2 } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { wvlApi } from "../../api/wvl";

export function WVLIndex() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["wvl-active"], queryFn: wvlApi.active });

  const create = useMutation({
    mutationFn: () => wvlApi.newSeason(),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["wvl-active"] });
      navigate(`/wvl/${r.session_id}`);
    },
    onError: () => notifications.show({ message: "Couldn't start WVL season", color: "red" }),
  });

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>WVL — World Viperball League</Title>
          <Text c="dimmed" size="sm">
            Four tiers, promotion &amp; relegation across 64 clubs.
          </Text>
        </Stack>
        <Button leftSection={<IconPlus size={16} />} onClick={() => create.mutate()} loading={create.isPending}>
          New WVL season
        </Button>
      </Group>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">No active WVL seasons. Start one above.</Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          {data.map((s) => (
            <Card key={s.session_id} component={Link} to={`/wvl/${s.session_id}`} padding="md" style={{ textDecoration: "none" }}>
              <Group justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <IconStack2 size={18} color="var(--mantine-color-orange-6)" />
                  <div>
                    <Text fw={600}>World Viperball League</Text>
                    <Text size="xs" c="dimmed">
                      {s.status.tiers.length} tiers ·{" "}
                      {s.status.tiers.reduce((n, t) => n + t.team_count, 0)} clubs
                    </Text>
                  </div>
                </Group>
                <Group gap="xs" wrap="nowrap">
                  <Badge variant="light" color="orange" size="sm">
                    {s.status.phase.replace(/_/g, " ")}
                  </Badge>
                  <IconChevronRight size={16} color="var(--mantine-color-gray-5)" />
                </Group>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
