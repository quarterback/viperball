import { AppShell, Group, Text, Badge, Anchor } from "@mantine/core";
import { IconDice5, IconArrowLeft } from "@tabler/icons-react";
import { Link, Outlet } from "react-router-dom";

export function DQLayout() {
  return (
    <AppShell header={{ height: 56 }} padding="lg">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <IconDice5 size={24} color="var(--mantine-color-teal-6)" />
            <Text fw={900} size="lg" style={{ letterSpacing: "0.04em" }}>
              Drafty
              <Text span c="teal" inherit>
                Queenz
              </Text>
            </Text>
            <Badge variant="light" color="teal" size="sm" radius="sm">
              BETA
            </Badge>
          </Group>
          <Anchor component={Link} to="/" size="sm" c="dimmed">
            <Group gap={4}>
              <IconArrowLeft size={14} />
              Workbench
            </Group>
          </Anchor>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
