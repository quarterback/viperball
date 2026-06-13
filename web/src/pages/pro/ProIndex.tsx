import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Badge,
  SimpleGrid,
  Button,
  Menu,
  Loader,
  Center,
  Progress,
} from "@mantine/core";
import { IconBallFootball, IconChevronRight, IconPlus } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { proApi, PRO_LEAGUES } from "../../api/pro";

export function ProIndex() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["pro-active"],
    queryFn: proApi.active,
  });

  const start = useMutation({
    mutationFn: (league: string) => proApi.newSeason(league),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["pro-active"] });
      navigate(`/pro/${res.league}/${res.session_id}`);
    },
    onError: () => notifications.show({ message: "Couldn't start league", color: "red" }),
  });

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Stack gap={2}>
          <Title order={2}>Pro Leagues</Title>
          <Text c="dimmed" size="sm">
            Professional Viperball — five leagues, promotion-grade rosters.
          </Text>
        </Stack>
        <Menu withinPortal position="bottom-end">
          <Menu.Target>
            <Button leftSection={<IconPlus size={16} />} loading={start.isPending}>
              Start a league
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            {PRO_LEAGUES.map((l) => (
              <Menu.Item key={l.id} onClick={() => start.mutate(l.id)}>
                {l.name}
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>
      </Group>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">No active pro seasons. Start one above.</Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {data.map((s) => {
            const st = s.status;
            const pct = st.total_weeks
              ? Math.round((st.current_week / st.total_weeks) * 100)
              : 0;
            return (
              <Card
                key={s.key}
                component={Link}
                to={`/pro/${s.league}/${s.key.replace(`${s.league}_`, "")}`}
                padding="md"
                style={{ textDecoration: "none" }}
              >
                <Group justify="space-between" mb="xs" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <IconBallFootball size={18} color="var(--mantine-color-teal-6)" />
                    <Text fw={600} lineClamp={1}>
                      {s.league_name}
                    </Text>
                  </Group>
                  <IconChevronRight size={16} color="var(--mantine-color-gray-5)" />
                </Group>
                <Group gap="xs" mb="sm">
                  <Badge variant="light" radius="sm">
                    {st.phase.replace(/_/g, " ")}
                  </Badge>
                  <Badge variant="light" color="gray" radius="sm">
                    {st.team_count} teams
                  </Badge>
                  {st.champion_name && (
                    <Badge variant="light" color="teal" radius="sm">
                      🏆 {st.champion_name}
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed" mb={4}>
                  Week {st.current_week} / {st.total_weeks}
                </Text>
                <Progress value={pct} size="sm" radius="xl" color="teal" />
              </Card>
            );
          })}
        </SimpleGrid>
      )}
    </Stack>
  );
}
