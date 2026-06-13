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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { offseasonApi, dynastyApi, type Recruit } from "../../api/dynasty";

const POSITIONS = [
  "Viper",
  "Zeroback",
  "Halfback",
  "Wingback",
  "Slotback",
  "Keeper",
  "Offensive Line",
  "Defensive Line",
];
const DEVELOPMENT = ["normal", "quick", "slow", "late_bloomer", "bust"];
const ATTRS: { key: string; label: string }[] = [
  { key: "true_speed", label: "Speed" },
  { key: "true_power", label: "Power" },
  { key: "true_agility", label: "Agility" },
  { key: "true_hands", label: "Hands" },
  { key: "true_awareness", label: "Awareness" },
  { key: "true_stamina", label: "Stamina" },
  { key: "true_tackling", label: "Tackling" },
  { key: "true_kicking", label: "Kicking" },
];

type FormState = Record<string, string | number>;

function splitName(name: string): [string, string] {
  const i = name.indexOf(" ");
  return i < 0 ? [name, ""] : [name.slice(0, i), name.slice(i + 1)];
}

export function RecruitEditModal({
  opened,
  onClose,
  sid,
  recruit,
}: {
  opened: boolean;
  onClose: () => void;
  sid: string;
  recruit: Recruit | null;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>({});

  useEffect(() => {
    if (opened && recruit) {
      const [first, last] = splitName(recruit.name);
      const f: FormState = {
        first_name: first,
        last_name: last,
        position: recruit.position_full || recruit.position,
        stars: recruit.stars,
        region: recruit.region ?? "",
        hometown: recruit.hometown ?? "",
        true_potential: recruit.true_potential ?? 3,
        true_development: recruit.true_development ?? "normal",
        gpa: recruit.gpa ?? 3.0,
        sat_score: recruit.sat_score ?? 1000,
      };
      ATTRS.forEach(
        (a) => (f[a.key] = ((recruit as unknown as Record<string, unknown>)[a.key] as number) ?? 70),
      );
      setForm(f);
    }
  }, [opened, recruit]);

  const set = (k: string, v: string | number) => setForm((s) => ({ ...s, [k]: v }));

  const save = useMutation({
    mutationFn: () => offseasonApi.editRecruit(sid, recruit!.pool_index, form),
    onSuccess: () => {
      notifications.show({ message: "Recruit updated", color: "grape" });
      qc.invalidateQueries({ queryKey: ["offseason-recruiting", sid] });
      onClose();
    },
    onError: () => notifications.show({ message: "Save failed", color: "red" }),
  });

  return (
    <Modal opened={opened} onClose={onClose} title={`Edit ${recruit?.name ?? "recruit"}`} size="lg">
      <Stack gap="sm">
        <Group grow>
          <TextInput label="First name" value={String(form.first_name ?? "")} onChange={(e) => set("first_name", e.currentTarget.value)} />
          <TextInput label="Last name" value={String(form.last_name ?? "")} onChange={(e) => set("last_name", e.currentTarget.value)} />
        </Group>
        <Group grow>
          <Select label="Position" data={POSITIONS} value={String(form.position ?? "Halfback")} onChange={(v) => set("position", v ?? "Halfback")} />
          <NumberInput label="Stars" value={Number(form.stars ?? 3)} min={1} max={5} onChange={(v) => set("stars", Number(v) || 3)} />
          <NumberInput label="Potential" value={Number(form.true_potential ?? 3)} min={1} max={5} onChange={(v) => set("true_potential", Number(v) || 3)} />
          <Select label="Development" data={DEVELOPMENT} value={String(form.true_development ?? "normal")} onChange={(v) => set("true_development", v ?? "normal")} />
        </Group>
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          {ATTRS.map((a) => (
            <NumberInput key={a.key} label={a.label} value={Number(form[a.key] ?? 70)} min={0} max={99} onChange={(v) => set(a.key, Number(v) || 0)} />
          ))}
        </SimpleGrid>
        <Group grow>
          <TextInput label="Region" value={String(form.region ?? "")} onChange={(e) => set("region", e.currentTarget.value)} />
          <TextInput label="Hometown" value={String(form.hometown ?? "")} onChange={(e) => set("hometown", e.currentTarget.value)} />
          <NumberInput label="GPA" value={Number(form.gpa ?? 3)} min={0} max={4} step={0.1} decimalScale={2} onChange={(v) => set("gpa", Number(v) || 0)} />
          <NumberInput label="SAT" value={Number(form.sat_score ?? 1000)} min={400} max={1600} onChange={(v) => set("sat_score", Number(v) || 0)} />
        </Group>
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function AssignRecruitModal({
  opened,
  onClose,
  sid,
  recruit,
}: {
  opened: boolean;
  onClose: () => void;
  sid: string;
  recruit: Recruit | null;
}) {
  const qc = useQueryClient();
  const [team, setTeam] = useState<string | null>(null);
  useEffect(() => {
    if (opened) setTeam(null);
  }, [opened]);

  const histories = useQuery_teams(sid, opened);

  const assign = useMutation({
    mutationFn: () => offseasonApi.assignRecruit(sid, recruit!.pool_index, team!),
    onSuccess: () => {
      notifications.show({ message: `Signed ${recruit?.name} to ${team}`, color: "grape" });
      qc.invalidateQueries({ queryKey: ["offseason-recruiting", sid] });
      onClose();
    },
    onError: () => notifications.show({ message: "Assign failed", color: "red" }),
  });

  return (
    <Modal opened={opened} onClose={onClose} title={`Assign ${recruit?.name ?? "recruit"}`} size="sm">
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          Signs this recruit to a team. They join the roster when the offseason completes.
        </Text>
        <Select
          placeholder="Team"
          data={histories}
          value={team}
          onChange={setTeam}
          searchable
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => assign.mutate()} loading={assign.isPending} disabled={!team}>
            Sign to team
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

// Team list for the assign dropdown (from dynasty team histories).
function useQuery_teams(sid: string, enabled: boolean): string[] {
  const q = useQuery({
    queryKey: ["dynasty-histories", sid],
    queryFn: () => dynastyApi.teamHistories(sid),
    enabled,
  });
  return (q.data ?? []).map((h) => h.team_name).sort();
}
