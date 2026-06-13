import { AppShell, Group, NavLink, ScrollArea, Text, Badge, ActionIcon, Tooltip } from "@mantine/core";
import {
  IconLayoutGrid,
  IconTrophy,
  IconUsers,
  IconWorld,
  IconBallFootball,
  IconDownload,
  IconSearch,
  IconChartBar,
  IconCrown,
  IconDice5,
} from "@tabler/icons-react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { spotlight } from "@mantine/spotlight";
import { CommandPalette } from "./CommandPalette";

const NAV = [
  { to: "/", label: "Saves", icon: IconLayoutGrid, end: true },
  { to: "/game", label: "Game Sim", icon: IconDice5 },
  { to: "/league", label: "League Hub", icon: IconTrophy },
  { to: "/dynasty", label: "Dynasty", icon: IconCrown },
  { to: "/compare", label: "Compare Runs", icon: IconChartBar },
  { to: "/team", label: "My Team", icon: IconUsers },
  { to: "/pro", label: "Pro Leagues", icon: IconBallFootball },
  { to: "/international", label: "International", icon: IconWorld },
  { to: "/export", label: "Export", icon: IconDownload },
];

export function AppLayout() {
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 52 }}
      navbar={{ width: 220, breakpoint: "sm" }}
      padding="lg"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <IconBallFootball size={22} color="var(--mantine-color-indigo-6)" />
            <Text fw={900} size="sm" style={{ letterSpacing: "0.14em" }}>
              VIPERBALL
            </Text>
            <Badge variant="light" color="gray" size="xs" radius="sm">
              workbench
            </Badge>
          </Group>
          <Tooltip label="Search  (⌘K / Ctrl-K)">
            <ActionIcon variant="default" size="lg" onClick={() => spotlight.open()}>
              <IconSearch size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <ScrollArea>
          {NAV.map((item) => {
            const active = item.end
              ? pathname === item.to
              : pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                component={Link}
                to={item.to}
                label={item.label}
                leftSection={<item.icon size={18} stroke={1.6} />}
                active={active}
                variant="light"
              />
            );
          })}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <CommandPalette />
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
