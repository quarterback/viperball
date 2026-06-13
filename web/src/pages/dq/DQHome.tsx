import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Stack,
  Title,
  Text,
  Card,
  Group,
  Badge,
  SimpleGrid,
  Loader,
  Center,
} from "@mantine/core";
import { IconChevronRight, IconDice5 } from "@tabler/icons-react";
import { seasonApi } from "../../api/season";

export function DQHome() {
  const { data, isLoading } = useQuery({
    queryKey: ["college-sessions"],
    queryFn: seasonApi.listSessions,
  });

  return (
    <Stack gap="md" maw={900} mx="auto">
      <Stack gap={4}>
        <Title order={2}>Tonight's slates</Title>
        <Text c="dimmed">
          Bet the board and draft a daily lineup on any running season. Pick a season to play.
        </Text>
      </Stack>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">
            No active seasons to bet on. Start one in the{" "}
            <Text span fw={600}>
              Workbench
            </Text>{" "}
            (League Hub → New Season), then come back.
          </Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          {data.map((s) => (
            <Card
              key={s.session_id}
              component={Link}
              to={`/dq/${s.session_id}`}
              padding="md"
              style={{ textDecoration: "none" }}
            >
              <Group justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <IconDice5 size={18} color="var(--mantine-color-teal-6)" />
                  <div>
                    <Text fw={600} lineClamp={1}>
                      {s.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Week {s.current_week} / {s.total_weeks}
                    </Text>
                  </div>
                </Group>
                <Group gap="xs" wrap="nowrap">
                  {s.champion && (
                    <Badge variant="light" color="teal" size="sm">
                      final
                    </Badge>
                  )}
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
