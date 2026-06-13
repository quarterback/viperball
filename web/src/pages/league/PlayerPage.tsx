import { useParams, Link } from "react-router-dom";
import {
  Stack,
  Group,
  Title,
  Text,
  Anchor,
  Breadcrumbs,
  Badge,
  Loader,
  Center,
  Card,
  SimpleGrid,
  Progress,
} from "@mantine/core";
import { IconChevronRight, IconMapPin } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { seasonApi, type RosterPlayer } from "../../api/season";

const ATTRS: { key: keyof RosterPlayer; label: string }[] = [
  { key: "overall", label: "Overall" },
  { key: "speed", label: "Speed" },
  { key: "power", label: "Power" },
  { key: "agility", label: "Agility" },
  { key: "hands", label: "Hands" },
  { key: "awareness", label: "Awareness" },
  { key: "stamina", label: "Stamina" },
  { key: "tackling", label: "Tackling" },
  { key: "kicking", label: "Kicking" },
];

export function PlayerPage() {
  const { sessionId = "", teamName = "", playerName = "" } = useParams();
  const team = decodeURIComponent(teamName);
  const player = decodeURIComponent(playerName);

  const roster = useQuery({
    queryKey: ["roster", sessionId, team],
    queryFn: () => seasonApi.roster(sessionId, team),
  });

  const p = roster.data?.roster.find((r) => r.name === player);

  if (roster.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (!p) {
    return (
      <Card>
        <Text c="red">
          Player not found.{" "}
          <Anchor component={Link} to={`/league/${sessionId}/team/${encodeURIComponent(team)}`}>
            Back to {team}
          </Anchor>
        </Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Anchor component={Link} to={`/league/${sessionId}`} size="sm">
          Season
        </Anchor>
        <Anchor
          component={Link}
          to={`/league/${sessionId}/team/${encodeURIComponent(team)}`}
          size="sm"
        >
          {team}
        </Anchor>
        <Text size="sm">{p.name}</Text>
      </Breadcrumbs>

      <Group gap="md" align="center">
        <Title order={2}>
          <Text span c="dimmed" fw={400} size="xl">
            #{p.number}
          </Text>{" "}
          {p.name}
        </Title>
        <Badge size="lg" variant="light">
          {p.position_full}
        </Badge>
        <Badge size="lg" variant="light" color="gray">
          {p.year_abbr}
        </Badge>
        {p.archetype && (
          <Badge size="lg" variant="light" color="grape">
            {p.archetype}
          </Badge>
        )}
      </Group>

      <Group gap="lg" c="dimmed">
        <Group gap={4}>
          <IconMapPin size={14} />
          <Text size="sm">
            {[p.hometown_city, p.hometown_state].filter(Boolean).join(", ") || "Unknown"}
          </Text>
        </Group>
        {p.height && (
          <Text size="sm">
            {p.height}
            {p.weight ? ` · ${p.weight} lb` : ""}
          </Text>
        )}
        {p.depth_status !== "healthy" && (
          <Badge color="orange" variant="light" size="sm">
            {p.depth_status}
          </Badge>
        )}
      </Group>

      <Card>
        <Text fw={600} mb="md" size="sm">
          Attributes
        </Text>
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="lg">
          {ATTRS.map((a) => {
            const val = Number(p[a.key]) || 0;
            return (
              <Stack key={a.label} gap={4}>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    {a.label}
                  </Text>
                  <Text size="sm" fw={700}>
                    {val}
                  </Text>
                </Group>
                <Progress value={val} color={attrColor(val)} size="sm" radius="xl" />
              </Stack>
            );
          })}
        </SimpleGrid>
      </Card>
    </Stack>
  );
}

function attrColor(v: number) {
  if (v >= 85) return "teal";
  if (v >= 70) return "indigo";
  if (v >= 55) return "yellow";
  return "red";
}
