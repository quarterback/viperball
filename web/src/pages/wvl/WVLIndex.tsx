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
  Alert,
  List,
} from "@mantine/core";
import {
  IconChevronRight,
  IconPlus,
  IconWorld,
  IconSchool,
  IconInfoCircle,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { wvlApi } from "../../api/wvl";

export function WVLIndex() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["wvl-active"], queryFn: wvlApi.active });
  const pools = useQuery({ queryKey: ["wvl-pools"], queryFn: wvlApi.graduatePools });

  const create = useMutation({
    mutationFn: () => wvlApi.newSeason(),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["wvl-active"] });
      navigate(`/wvl/${r.league_id}`);
    },
    onError: () => notifications.show({ message: "Couldn't start a WVL career league", color: "red" }),
  });

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>WVL — Career League</Title>
          <Text c="dimmed" size="sm">
            The Galactic Premiership: where CVL graduates continue their careers. The same player
            cards carry over, simulated game-by-game, season after season.
          </Text>
        </Stack>
        <Button leftSection={<IconPlus size={16} />} onClick={() => create.mutate()} loading={create.isPending}>
          New career league
        </Button>
      </Group>

      <Alert variant="light" color="indigo" icon={<IconInfoCircle size={16} />}>
        Graduate a class in a <Link to="/dynasty">CVL Dynasty</Link> to feed real players into the
        WVL. New leagues import every available class automatically; if none exist yet, a starter
        roster is seeded so you can explore.
      </Alert>

      {pools.data && pools.data.length > 0 && (
        <Card withBorder>
          <Group gap="xs" mb="xs">
            <IconSchool size={18} color="var(--mantine-color-teal-6)" />
            <Text fw={600}>CVL graduate classes ready to import</Text>
          </Group>
          <List size="sm" spacing={2}>
            {pools.data.map((p) => (
              <List.Item key={p.save_key}>
                <b>{p.dynasty}</b> — class of {p.year} · {p.player_count} players
              </List.Item>
            ))}
          </List>
        </Card>
      )}

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">No career leagues yet. Start one above.</Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          {data.map((s) => (
            <Card
              key={s.league_id}
              component={Link}
              to={`/wvl/${s.league_id}`}
              padding="md"
              withBorder
              style={{ textDecoration: "none" }}
            >
              <Group justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <IconWorld size={18} color="var(--mantine-color-orange-6)" />
                  <div>
                    <Text fw={600}>Galactic Premiership · {s.status.year}</Text>
                    <Text size="xs" c="dimmed">
                      {s.status.clubs} clubs · {s.status.tracked_players} careers tracked ·{" "}
                      {s.status.seasons_completed} seasons done
                    </Text>
                  </div>
                </Group>
                <Group gap="xs" wrap="nowrap">
                  <Badge variant="light" color="orange" size="sm">
                    {s.status.champion ? `🏆 ${s.status.champion}` : s.status.phase}
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
