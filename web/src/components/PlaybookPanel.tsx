import { Card, Group, Progress, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { PlaybookUnit, TeamPlaybook } from "../api/season";

/** A team's home book, the books its coaches borrow from and when, and
 *  where this season's calls actually came from. */
function Unit({ title, unit }: { title: string; unit: PlaybookUnit }) {
  return (
    <Card withBorder>
      <Stack gap="sm">
        <div>
          <Title order={4}>
            {title}: {unit.home.label}
          </Title>
          <Text size="sm" c="dimmed">
            {unit.home.description}
          </Text>
        </div>
        {unit.borrowed.length === 0 ? (
          <Text size="sm">Runs the home book only.</Text>
        ) : (
          <Stack gap={6}>
            <Text size="sm" fw={600}>
              Borrows from
            </Text>
            {unit.borrowed.map((b) => (
              <Group key={b.key} justify="space-between" wrap="nowrap" align="flex-start">
                <div>
                  <Text size="sm">{b.label}</Text>
                  <Text size="xs" c="dimmed">
                    Called {b.when.join(", ")}
                  </Text>
                </div>
                <Text size="sm" fw={600}>
                  {Math.round(b.share * 100)}%
                </Text>
              </Group>
            ))}
          </Stack>
        )}
        {unit.season_calls.length > 0 && (
          <Stack gap={6}>
            <Text size="sm" fw={600}>
              This season's calls
            </Text>
            {unit.season_calls.map((c) => (
              <div key={c.key}>
                <Group justify="space-between">
                  <Text size="xs">{c.label}</Text>
                  <Text size="xs" c="dimmed">
                    {c.calls} plays, {c.pct}%
                  </Text>
                </Group>
                <Progress value={c.pct} size="sm" />
              </div>
            ))}
          </Stack>
        )}
      </Stack>
    </Card>
  );
}

export function PlaybookPanel({ playbook }: { playbook?: TeamPlaybook }) {
  if (!playbook) return <Text c="dimmed">No playbook data for this team.</Text>;
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }}>
      <Unit title="Offense" unit={playbook.offense} />
      <Unit title="Defense" unit={playbook.defense} />
    </SimpleGrid>
  );
}
