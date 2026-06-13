import { useEffect, useState } from "react";
import {
  Modal,
  Stack,
  Group,
  TextInput,
  NumberInput,
  Select,
  SimpleGrid,
  Button,
  Text,
} from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import {
  seasonApi,
  VIPERBALL_POSITIONS,
  CLASS_YEARS,
  type RosterPlayer,
} from "../../api/season";

const ATTR_FIELDS: { key: string; label: string }[] = [
  { key: "speed", label: "Speed" },
  { key: "power", label: "Power" },
  { key: "agility", label: "Agility" },
  { key: "hands", label: "Hands" },
  { key: "awareness", label: "Awareness" },
  { key: "stamina", label: "Stamina" },
  { key: "tackling", label: "Tackling" },
  { key: "kicking", label: "Kicking" },
  { key: "kick_power", label: "Kick power" },
  { key: "kick_accuracy", label: "Kick acc." },
  { key: "lateral_skill", label: "Lateral" },
];

type FormState = Record<string, string | number>;

function initialFrom(p: RosterPlayer | null): FormState {
  if (!p) {
    const blank: FormState = { name: "", number: 0, position: "Halfback", year: "Freshman", potential: 3, height: "5-10", weight: 175, hometown_city: "", hometown_state: "" };
    ATTR_FIELDS.forEach((a) => (blank[a.key] = 70));
    return blank;
  }
  const s: FormState = {
    name: p.name,
    number: p.number,
    position: p.position_full,
    year: p.year ?? "Sophomore",
    potential: p.potential ?? 3,
    height: p.height,
    weight: p.weight,
    hometown_city: p.hometown_city,
    hometown_state: p.hometown_state,
  };
  ATTR_FIELDS.forEach(
    (a) => (s[a.key] = ((p as unknown as Record<string, unknown>)[a.key] as number) ?? 70),
  );
  return s;
}

export function PlayerFormModal({
  opened,
  onClose,
  sid,
  team,
  player,
  mode,
}: {
  opened: boolean;
  onClose: () => void;
  sid: string;
  team: string;
  player: RosterPlayer | null;
  mode: "edit" | "add";
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(initialFrom(player));
  useEffect(() => {
    if (opened) setForm(initialFrom(player));
  }, [opened, player]);

  const set = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }));

  const save = useMutation({
    mutationFn: () => {
      if (mode === "edit" && player) {
        return seasonApi.editPlayer(sid, team, player.name, form);
      }
      const { name, position, ...attributes } = form;
      return seasonApi.addPlayer(sid, team, String(name), String(position), attributes);
    },
    onSuccess: () => {
      notifications.show({ message: mode === "edit" ? "Player updated" : "Player added", color: "indigo" });
      qc.invalidateQueries({ queryKey: ["roster", sid, team] });
      onClose();
    },
    onError: () => notifications.show({ message: "Save failed", color: "red" }),
  });

  return (
    <Modal opened={opened} onClose={onClose} title={mode === "edit" ? `Edit ${player?.name}` : "Add player"} size="lg">
      <Stack gap="sm">
        <Group grow>
          <TextInput label="Name" value={String(form.name)} onChange={(e) => set("name", e.currentTarget.value)} />
          <NumberInput label="Number" value={Number(form.number)} min={0} max={99} onChange={(v) => set("number", Number(v) || 0)} w={120} />
        </Group>
        <Group grow>
          <Select label="Position" data={VIPERBALL_POSITIONS} value={String(form.position)} onChange={(v) => set("position", v ?? "Halfback")} />
          <Select label="Class" data={CLASS_YEARS} value={String(form.year)} onChange={(v) => set("year", v ?? "Freshman")} />
          <NumberInput label="Potential" value={Number(form.potential)} min={1} max={5} onChange={(v) => set("potential", Number(v) || 3)} />
        </Group>
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          {ATTR_FIELDS.map((a) => (
            <NumberInput
              key={a.key}
              label={a.label}
              value={Number(form[a.key])}
              min={0}
              max={99}
              onChange={(v) => set(a.key, Number(v) || 0)}
            />
          ))}
        </SimpleGrid>
        <Group grow>
          <TextInput label="Height" value={String(form.height)} onChange={(e) => set("height", e.currentTarget.value)} />
          <NumberInput label="Weight" value={Number(form.weight)} min={100} max={400} onChange={(v) => set("weight", Number(v) || 0)} />
          <TextInput label="Hometown city" value={String(form.hometown_city)} onChange={(e) => set("hometown_city", e.currentTarget.value)} />
          <TextInput label="State" value={String(form.hometown_state)} onChange={(e) => set("hometown_state", e.currentTarget.value)} />
        </Group>
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!String(form.name).trim()}>
            {mode === "edit" ? "Save" : "Add player"}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function MovePlayerModal({
  opened,
  onClose,
  sid,
  fromTeam,
  player,
  teams,
}: {
  opened: boolean;
  onClose: () => void;
  sid: string;
  fromTeam: string;
  player: RosterPlayer | null;
  teams: string[];
}) {
  const qc = useQueryClient();
  const [target, setTarget] = useState<string | null>(null);
  useEffect(() => {
    if (opened) setTarget(null);
  }, [opened]);

  const move = useMutation({
    mutationFn: () => seasonApi.movePlayer(sid, player!.name, fromTeam, target!),
    onSuccess: () => {
      notifications.show({ message: `Moved ${player?.name} to ${target}`, color: "indigo" });
      qc.invalidateQueries({ queryKey: ["roster", sid, fromTeam] });
      if (target) qc.invalidateQueries({ queryKey: ["roster", sid, target] });
      onClose();
    },
    onError: () => notifications.show({ message: "Move failed", color: "red" }),
  });

  return (
    <Modal opened={opened} onClose={onClose} title={`Move ${player?.name}`} size="sm">
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          From {fromTeam} to:
        </Text>
        <Select
          placeholder="Destination team"
          data={teams.filter((t) => t !== fromTeam)}
          value={target}
          onChange={setTarget}
          searchable
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => move.mutate()} loading={move.isPending} disabled={!target}>
            Move
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
