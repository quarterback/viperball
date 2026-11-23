import { Card, Group, Progress, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { InstallationUnit, TeamInstallation } from "../api/season";

const words = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const pct = (v: number | undefined) => Math.round((v ?? 0) * 100);

function Bar({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div>
      <Group justify="space-between">
        <Text size="sm">{label}</Text>
        <Text size="sm" c="dimmed">
          {pct(value)}%
        </Text>
      </Group>
      <Progress value={pct(value)} size="sm" />
    </div>
  );
}

function Unit({ title, unit }: { title: string; unit?: InstallationUnit }) {
  if (!unit) return null;
  return (
    <Card withBorder>
      <Stack gap="sm">
        <Title order={5}>
          {title}: {words(unit.family)}
          {unit.signature ? `, ${words(unit.signature)}` : ""}
        </Title>
        <Bar label="Knows the coordinator's system" value={unit.familiarity} />
        <Bar label="Knows the base book" value={unit.family_familiarity} />
        <Text size="xs" c="dimmed">
          {unit.seasons_together} {unit.seasons_together === 1 ? "season" : "seasons"} together. The coordinator's
          tendencies show at {pct(unit.execution_factor)}% strength.
        </Text>
        {unit.vestigial.length > 0 && (
          <Text size="sm">
            Old habits: {unit.vestigial.map((v) => `${words(v.signature)} (${pct(v.weight)}%)`).join(", ")}
          </Text>
        )}
        {unit.packages.length > 0 ? (
          <Stack gap={4}>
            <Text size="sm" fw={600}>
              Installed packages
            </Text>
            {unit.packages.map((p) => (
              <Bar key={p.package_id} label={p.name} value={p.familiarity} />
            ))}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            No packages installed.
          </Text>
        )}
      </Stack>
    </Card>
  );
}

/** What a program has learned: familiarity with its coordinators and base
 *  books, fading habits from past coordinators, installed packages. */
export function InstallationPanel({ installation }: { installation?: TeamInstallation }) {
  if (!installation || (!installation.offense && !installation.defense)) {
    return (
      <Text size="sm" c="dimmed">
        Installation tracking starts with this team's first game.
      </Text>
    );
  }
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }}>
      <Unit title="Offense" unit={installation.offense} />
      <Unit title="Defense" unit={installation.defense} />
    </SimpleGrid>
  );
}
