import { Card, Stack, Title, Text, List, ThemeIcon, Badge } from "@mantine/core";
import { IconPointFilled } from "@tabler/icons-react";

/**
 * Phase-1 placeholders for screens that arrive in later phases. They state
 * exactly which endpoints back each screen so the build order is explicit.
 */
export function Placeholder({
  title,
  phase,
  blurb,
  endpoints,
}: {
  title: string;
  phase: string;
  blurb: string;
  endpoints: string[];
}) {
  return (
    <Stack gap="md" maw={760}>
      <Stack gap={4}>
        <Title order={2}>
          {title}{" "}
          <Badge variant="light" color="gray" radius="sm">
            {phase}
          </Badge>
        </Title>
        <Text c="dimmed">{blurb}</Text>
      </Stack>
      <Card>
        <Text fw={600} mb="xs" size="sm">
          Backed by these existing endpoints:
        </Text>
        <List
          spacing={4}
          size="sm"
          icon={
            <ThemeIcon size={14} radius="xl" variant="light" color="indigo">
              <IconPointFilled size={10} />
            </ThemeIcon>
          }
        >
          {endpoints.map((e) => (
            <List.Item key={e}>
              <Text ff="monospace" size="xs">
                {e}
              </Text>
            </List.Item>
          ))}
        </List>
      </Card>
    </Stack>
  );
}
