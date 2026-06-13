import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  TextInput,
  NumberInput,
  Select,
  Stepper,
  Button,
  Breadcrumbs,
  Anchor,
  SimpleGrid,
  Tooltip,
  ActionIcon,
} from "@mantine/core";
import { IconChevronRight, IconDice5, IconRocket } from "@tabler/icons-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi, createSeason, type NewSeasonConfig } from "../../api/season";

export function NewSeason() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const teams = useQuery({ queryKey: ["teams"], queryFn: seasonApi.teams });

  const [cfg, setCfg] = useState<NewSeasonConfig>({
    name: "2026 CVL Season",
    human_teams: [],
    ai_seed: 0,
    games_per_team: 12,
    playoff_size: 8,
    bowl_count: 4,
    num_conferences: 10,
    history_years: 0,
  });
  const set = <K extends keyof NewSeasonConfig>(k: K, v: NewSeasonConfig[K]) =>
    setCfg((c) => ({ ...c, [k]: v }));

  const create = useMutation({
    mutationFn: () => createSeason(cfg),
    onSuccess: (sid) => {
      notifications.show({ message: "Season created", color: "indigo" });
      navigate(`/league/${sid}`);
    },
    onError: () =>
      notifications.show({ message: "Couldn't create the season", color: "red" }),
  });

  const teamOptions =
    teams.data?.map((t) => ({ value: t.key, label: t.name })) ?? [];

  return (
    <Stack gap="md" maw={720}>
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Text size="sm">New Season</Text>
      </Breadcrumbs>

      <Title order={2}>New Season</Title>
      <Text c="dimmed" size="sm" mt={-8}>
        Spin up a fresh experiment. Conferences, schedules, and AI styles are generated
        automatically — fix the seed to make a run reproducible.
      </Text>

      <Card>
        <Stepper active={step} onStepClick={setStep} size="sm">
          <Stepper.Step label="Identity" description="Name, team, seed">
            <Stack gap="md" mt="md">
              <TextInput
                label="Season name"
                value={cfg.name}
                onChange={(e) => set("name", e.currentTarget.value)}
              />
              <Select
                label="Your team (optional)"
                description="Leave empty for an all-AI league."
                placeholder="All AI"
                data={teamOptions}
                value={cfg.human_teams[0] ?? null}
                onChange={(v) => set("human_teams", v ? [v] : [])}
                searchable
                clearable
                disabled={teams.isLoading}
              />
              <NumberInput
                label="Seed"
                description="0 = random each run. Set a fixed seed to reproduce / compare experiments."
                value={cfg.ai_seed}
                min={0}
                onChange={(v) => set("ai_seed", Number(v) || 0)}
                rightSection={
                  <Tooltip label="Random seed">
                    <ActionIcon
                      variant="subtle"
                      onClick={() => set("ai_seed", Math.floor(Math.random() * 999999))}
                    >
                      <IconDice5 size={16} />
                    </ActionIcon>
                  </Tooltip>
                }
              />
            </Stack>
          </Stepper.Step>

          <Stepper.Step label="Format" description="Schedule & playoffs">
            <SimpleGrid cols={{ base: 1, sm: 2 }} mt="md">
              <NumberInput
                label="Games per team"
                value={cfg.games_per_team}
                min={4}
                max={16}
                onChange={(v) => set("games_per_team", Number(v) || 12)}
              />
              <NumberInput
                label="Conferences"
                value={cfg.num_conferences}
                min={2}
                max={16}
                onChange={(v) => set("num_conferences", Number(v) || 10)}
              />
              <NumberInput
                label="Playoff teams"
                value={cfg.playoff_size}
                min={2}
                max={16}
                onChange={(v) => set("playoff_size", Number(v) || 8)}
              />
              <NumberInput
                label="Bowl games"
                value={cfg.bowl_count}
                min={0}
                max={20}
                onChange={(v) => set("bowl_count", Number(v) || 0)}
              />
              <NumberInput
                label="History years"
                description="Pre-generate prior seasons for context."
                value={cfg.history_years}
                min={0}
                max={20}
                onChange={(v) => set("history_years", Number(v) || 0)}
              />
            </SimpleGrid>
          </Stepper.Step>
        </Stepper>

        <Group justify="space-between" mt="xl">
          <Button
            variant="default"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            Back
          </Button>
          {step === 0 ? (
            <Button onClick={() => setStep(1)}>Next</Button>
          ) : (
            <Button
              leftSection={<IconRocket size={16} />}
              onClick={() => create.mutate()}
              loading={create.isPending}
            >
              Create season
            </Button>
          )}
        </Group>
      </Card>
    </Stack>
  );
}
