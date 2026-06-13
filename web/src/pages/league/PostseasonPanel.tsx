import {
  Stack,
  Group,
  Text,
  Card,
  Button,
  Badge,
  SimpleGrid,
  Loader,
  Center,
} from "@mantine/core";
import { IconTournament, IconTrophy } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi, type Game, type BowlResult } from "../../api/season";

function GameLine({ g }: { g: Game }) {
  const awayWon = g.completed && g.away_score > g.home_score;
  return (
    <Card padding="sm" withBorder>
      <Group justify="space-between">
        <Text size="sm" fw={awayWon ? 700 : 400}>
          {g.away_team}
        </Text>
        <Text size="sm" ff="monospace">
          {g.completed ? g.away_score : ""}
        </Text>
      </Group>
      <Group justify="space-between">
        <Text size="sm" fw={g.completed && !awayWon ? 700 : 400}>
          {g.home_team}
        </Text>
        <Text size="sm" ff="monospace">
          {g.completed ? g.home_score : ""}
        </Text>
      </Group>
    </Card>
  );
}

export function PostseasonPanel({ sid }: { sid: string }) {
  const qc = useQueryClient();
  const bracket = useQuery({
    queryKey: ["playoff-bracket", sid],
    queryFn: () => seasonApi.playoffBracket(sid),
  });
  const bowls = useQuery({
    queryKey: ["bowl-results", sid],
    queryFn: () => seasonApi.bowlResults(sid),
  });

  const refetch = () => {
    qc.invalidateQueries({ queryKey: ["playoff-bracket", sid] });
    qc.invalidateQueries({ queryKey: ["bowl-results", sid] });
    qc.invalidateQueries({ queryKey: ["season-status", sid] });
    qc.invalidateQueries({ queryKey: ["standings", sid] });
  };

  const simPlayoffs = useMutation({
    mutationFn: () => seasonApi.simPlayoffs(sid),
    onSuccess: () => {
      notifications.show({ message: "Playoffs simulated", color: "indigo" });
      refetch();
    },
    onError: () =>
      notifications.show({ message: "Playoffs failed (finish the regular season first)", color: "red" }),
  });
  const simBowls = useMutation({
    mutationFn: () => seasonApi.simBowls(sid),
    onSuccess: () => {
      notifications.show({ message: "Bowls simulated", color: "indigo" });
      refetch();
    },
    onError: () =>
      notifications.show({ message: "Bowls failed (finish the regular season first)", color: "red" }),
  });

  if (bracket.isLoading || bowls.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  const bracketGames = bracket.data?.bracket ?? [];
  const champion = bracket.data?.champion;
  const bowlGames: BowlResult[] = bowls.data ?? [];

  return (
    <Stack gap="md">
      <Group gap="xs">
        <Button
          leftSection={<IconTournament size={16} />}
          onClick={() => simPlayoffs.mutate()}
          loading={simPlayoffs.isPending}
        >
          Sim Playoffs
        </Button>
        <Button
          variant="default"
          leftSection={<IconTrophy size={16} />}
          onClick={() => simBowls.mutate()}
          loading={simBowls.isPending}
        >
          Sim Bowls
        </Button>
      </Group>

      <Card>
        <Group justify="space-between" mb="sm">
          <Text fw={700}>Playoff bracket</Text>
          {champion && (
            <Badge size="lg" color="teal" variant="light" leftSection={<IconTrophy size={14} />}>
              {champion}
            </Badge>
          )}
        </Group>
        {bracketGames.length ? (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
            {bracketGames.map((g, i) => (
              <GameLine key={i} g={g} />
            ))}
          </SimpleGrid>
        ) : (
          <Text c="dimmed" size="sm">
            No playoffs run yet.
          </Text>
        )}
      </Card>

      <Card>
        <Text fw={700} mb="sm">
          Bowl games
        </Text>
        {bowlGames.length ? (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {bowlGames.map((b, i) => (
              <Card key={i} padding="sm" withBorder>
                <Group justify="space-between" mb={4}>
                  <Text size="sm" fw={600}>
                    {b.name}
                  </Text>
                  <Badge size="xs" variant="light" color="gray">
                    {b.tier}
                  </Badge>
                </Group>
                <GameLine g={b.game} />
              </Card>
            ))}
          </SimpleGrid>
        ) : (
          <Text c="dimmed" size="sm">
            No bowls run yet.
          </Text>
        )}
      </Card>
    </Stack>
  );
}
