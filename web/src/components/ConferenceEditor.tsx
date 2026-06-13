import { useMemo, useState } from "react";
import { Stack, Group, Text, Card, Badge, Select, ScrollArea } from "@mantine/core";
import { IconChevronDown } from "@tabler/icons-react";

/**
 * Editable conference alignment, seeded from /conference-defaults. Teams are
 * identified by NAME (the season keys teams by name). Click a conference to
 * reassign its teams. Shared by Season Setup and Dynasty creation.
 */
export function ConferenceEditor({
  teamConf,
  onReassign,
}: {
  teamConf: Record<string, string>;
  onReassign: (team: string, conf: string) => void;
}) {
  const [openConf, setOpenConf] = useState<string | null>(null);

  const confNames = useMemo(
    () => Array.from(new Set(Object.values(teamConf))).sort(),
    [teamConf],
  );
  const teamsByConf = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const [t, c] of Object.entries(teamConf)) (m[c] ??= []).push(t);
    for (const c of Object.keys(m)) m[c].sort();
    return m;
  }, [teamConf]);

  return (
    <Stack gap="sm">
      <Text size="sm" c="dimmed">
        {confNames.length} conferences, {Object.keys(teamConf).length} teams. Click a conference
        to reassign its teams.
      </Text>
      <ScrollArea.Autosize mah={420}>
        <Stack gap={4}>
          {confNames.map((conf) => {
            const open = openConf === conf;
            const members = teamsByConf[conf] ?? [];
            return (
              <Card key={conf} padding="xs" withBorder>
                <Group
                  justify="space-between"
                  style={{ cursor: "pointer" }}
                  onClick={() => setOpenConf(open ? null : conf)}
                >
                  <Group gap="xs">
                    <IconChevronDown
                      size={16}
                      style={{
                        transform: open ? "rotate(0)" : "rotate(-90deg)",
                        transition: "transform .15s",
                      }}
                    />
                    <Text fw={600} size="sm">
                      {conf}
                    </Text>
                    <Badge size="xs" variant="light" color="gray">
                      {members.length}
                    </Badge>
                  </Group>
                </Group>
                {open && (
                  <Stack gap={4} mt="xs">
                    {members.map((t) => (
                      <Group key={t} justify="space-between" wrap="nowrap">
                        <Text size="sm">{t}</Text>
                        <Select
                          size="xs"
                          w={200}
                          data={confNames.map((c) => ({ value: c, label: c }))}
                          value={teamConf[t]}
                          onChange={(v) => v && onReassign(t, v)}
                          comboboxProps={{ withinPortal: true }}
                        />
                      </Group>
                    ))}
                  </Stack>
                )}
              </Card>
            );
          })}
        </Stack>
      </ScrollArea.Autosize>
    </Stack>
  );
}
