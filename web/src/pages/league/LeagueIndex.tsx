import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Card,
  Stack,
  Title,
  Text,
  Group,
  Badge,
  SimpleGrid,
  Loader,
  Center,
  Progress,
} from "@mantine/core";
import { IconTrophy, IconChevronRight } from "@tabler/icons-react";
import { seasonApi } from "../../api/season";

export function LeagueIndex() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["college-sessions"],
    queryFn: seasonApi.listSessions,
  });

  return (
    <Stack gap="md">
      <Stack gap={2}>
        <Title order={2}>College — League Hub</Title>
        <Text c="dimmed" size="sm">
          Pick an active season to view standings, schedule, polls, and leaders.
        </Text>
      </Stack>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {isError && (
        <Card>
          <Text c="red">Couldn't reach the season API.</Text>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">
            No active college seasons. Create one in the legacy app (Play tab) and it'll appear
            here — the New-Season wizard is the next thing on the rebuild list.
          </Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {data.map((s) => {
            const pct = s.total_weeks
              ? Math.round((s.current_week / s.total_weeks) * 100)
              : 0;
            return (
              <Card
                key={s.session_id}
                component={Link}
                to={`/league/${s.session_id}`}
                padding="md"
                style={{ textDecoration: "none" }}
              >
                <Group justify="space-between" mb="xs" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <IconTrophy size={18} color="var(--mantine-color-indigo-6)" />
                    <Text fw={600} lineClamp={1}>
                      {s.name}
                    </Text>
                  </Group>
                  <IconChevronRight size={16} color="var(--mantine-color-gray-5)" />
                </Group>
                <Group gap="xs" mb="sm">
                  <Badge variant="light" radius="sm">
                    {s.phase.replace(/_/g, " ")}
                  </Badge>
                  <Badge variant="light" color="gray" radius="sm">
                    {s.team_count} teams
                  </Badge>
                  {s.champion && (
                    <Badge variant="light" color="teal" radius="sm">
                      🏆 {s.champion}
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed" mb={4}>
                  Week {s.current_week} / {s.total_weeks}
                </Text>
                <Progress value={pct} size="sm" radius="xl" />
              </Card>
            );
          })}
        </SimpleGrid>
      )}
    </Stack>
  );
}
