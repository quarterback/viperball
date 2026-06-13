import { useEffect, useMemo, useState } from "react";
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
  Radio,
  Slider,
  Badge,
  Loader,
  Center,
  Divider,
} from "@mantine/core";
import { IconChevronRight, IconDice5, IconRocket, IconTrash } from "@tabler/icons-react";
import { ConferenceEditor } from "../../components/ConferenceEditor";
import { useQuery, useMutation } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import {
  seasonApi,
  createSeason,
  type NewSeasonConfig,
  type TeamStyle,
} from "../../api/season";

const PLAYOFF_OPTIONS = [4, 8, 12, 16, 24, 32];
const DEFAULT_STYLE: TeamStyle = {
  offense_style: "balanced",
  defense_style: "swarm",
  st_scheme: "aces",
};

export function NewSeason() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const teamsQ = useQuery({ queryKey: ["teams"], queryFn: seasonApi.teams });
  const stylesQ = useQuery({ queryKey: ["styles"], queryFn: seasonApi.styles });
  const confDefaultsQ = useQuery({
    queryKey: ["conference-defaults"],
    queryFn: seasonApi.conferenceDefaults,
  });

  const teams = useMemo(() => teamsQ.data ?? [], [teamsQ.data]);
  const totalTeams = teams.length;

  // ── Form state ────────────────────────────────────────────────
  const [name, setName] = useState("2026 CVL Season");
  const [humanTeams, setHumanTeams] = useState<string[]>([]);
  const [humanConfigs, setHumanConfigs] = useState<Record<string, TeamStyle>>({});
  const [aiSeed, setAiSeed] = useState(0);
  const [teamConf, setTeamConf] = useState<Record<string, string>>({});
  const [playoffSize, setPlayoffSize] = useState(8);
  const [bowlCount, setBowlCount] = useState(4);
  const [historyYears, setHistoryYears] = useState(0);

  // Team-picker UI state
  const [confFilter, setConfFilter] = useState<string>("__all__");

  // Seed conference alignment from the geographic defaults once loaded.
  useEffect(() => {
    if (confDefaultsQ.data && Object.keys(teamConf).length === 0) {
      const map: Record<string, string> = {};
      for (const [conf, members] of Object.entries(confDefaultsQ.data)) {
        for (const t of members) map[t] = conf;
      }
      setTeamConf(map);
    }
  }, [confDefaultsQ.data, teamConf]);

  // ── Derived ───────────────────────────────────────────────────
  const confNames = useMemo(
    () => Array.from(new Set(Object.values(teamConf))).sort(),
    [teamConf],
  );

  const playoffOptions = PLAYOFF_OPTIONS.filter((p) => p <= totalTeams || totalTeams === 0);
  const maxBowls = Math.max(0, Math.min(16, Math.floor((totalTeams - playoffSize) / 2)));

  // Keep bowl count within the (playoff-dependent) max.
  useEffect(() => {
    setBowlCount((b) => Math.min(b, maxBowls));
  }, [maxBowls]);

  const styleOpts = (rec: Record<string, { label: string }> | undefined) =>
    Object.entries(rec ?? {}).map(([value, v]) => ({ value, label: v.label }));

  // ── Team picker ───────────────────────────────────────────────
  // Teams are identified by NAME everywhere (the season keys teams by name, and
  // /conference-defaults returns members by name), so human_teams / human_configs
  // / conferences all use the team name, not the file key.
  const addableTeams = teams
    .filter((t) => !humanTeams.includes(t.name))
    .filter((t) => confFilter === "__all__" || (teamConf[t.name] ?? t.conference) === confFilter);

  const addTeam = (name: string | null) => {
    if (!name || humanTeams.length >= 4 || humanTeams.includes(name)) return;
    setHumanTeams((h) => [...h, name]);
    setHumanConfigs((c) => ({ ...c, [name]: { ...DEFAULT_STYLE } }));
  };
  const removeTeam = (name: string) => {
    setHumanTeams((h) => h.filter((k) => k !== name));
    setHumanConfigs((c) => {
      const next = { ...c };
      delete next[name];
      return next;
    });
  };
  const setStyle = (name: string, field: keyof TeamStyle, value: string) =>
    setHumanConfigs((c) => ({ ...c, [name]: { ...c[name], [field]: value } }));

  // ── Submit ────────────────────────────────────────────────────
  const create = useMutation({
    mutationFn: () => {
      const conferences: Record<string, string[]> = {};
      for (const [t, c] of Object.entries(teamConf)) (conferences[c] ??= []).push(t);
      const config: NewSeasonConfig = {
        name,
        human_teams: humanTeams,
        human_configs: humanConfigs,
        ai_seed: aiSeed,
        games_per_team: 12,
        playoff_size: playoffSize,
        bowl_count: bowlCount,
        num_conferences: confNames.length || 10,
        history_years: historyYears,
        conferences,
      };
      return createSeason(config);
    },
    onSuccess: (sid) => {
      notifications.show({ message: "Season created", color: "indigo" });
      navigate(`/league/${sid}`);
    },
    onError: () =>
      notifications.show({ message: "Couldn't create the season", color: "red" }),
  });

  const loading = teamsQ.isLoading || stylesQ.isLoading || confDefaultsQ.isLoading;
  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md" maw={860}>
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/league" size="sm">
          League Hub
        </Anchor>
        <Text size="sm">New Season</Text>
      </Breadcrumbs>

      <Title order={2}>New Season</Title>
      <Text c="dimmed" size="sm" mt={-8}>
        {totalTeams} teams · {confNames.length} conferences · 12 games each. Fix the AI seed to
        make a run reproducible.
      </Text>

      <Card>
        <Stepper active={step} onStepClick={setStep} size="sm">
          {/* ── Step 1: teams & styles ── */}
          <Stepper.Step label="Teams & Styles" description="Your teams + AI seed">
            <Stack gap="md" mt="md">
              <TextInput
                label="Season name"
                value={name}
                onChange={(e) => setName(e.currentTarget.value)}
              />

              <div>
                <Text size="sm" fw={500} mb={4}>
                  Your teams{" "}
                  <Text span c="dimmed" fw={400}>
                    (up to 4 · leave empty for all-AI)
                  </Text>
                </Text>
                <Group align="flex-end" gap="sm">
                  <Select
                    label="Filter by conference"
                    data={[
                      { value: "__all__", label: "All teams" },
                      ...confNames.map((c) => ({ value: c, label: c })),
                    ]}
                    value={confFilter}
                    onChange={(v) => setConfFilter(v ?? "__all__")}
                    w={220}
                    size="sm"
                  />
                  <Select
                    label="Add team"
                    placeholder={humanTeams.length >= 4 ? "Max 4 teams" : "Pick a team"}
                    data={addableTeams.map((t) => ({
                      value: t.name,
                      label: `${t.name}${teamConf[t.name] ?? t.conference ? ` (${teamConf[t.name] ?? t.conference})` : ""}`,
                    }))}
                    value={null}
                    onChange={addTeam}
                    searchable
                    disabled={humanTeams.length >= 4}
                    w={320}
                    size="sm"
                  />
                </Group>
              </div>

              {humanTeams.length > 0 && (
                <SimpleGrid cols={{ base: 1, sm: 2 }}>
                  {humanTeams.map((key) => (
                    <Card key={key} padding="sm" withBorder>
                      <Group justify="space-between" mb="xs">
                        <Text fw={600}>{key}</Text>
                        <ActionIcon variant="subtle" color="red" onClick={() => removeTeam(key)}>
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Group>
                      <Stack gap="xs">
                        <Select
                          label="Offense"
                          size="xs"
                          data={styleOpts(stylesQ.data?.offense_styles)}
                          value={humanConfigs[key]?.offense_style ?? "balanced"}
                          onChange={(v) => setStyle(key, "offense_style", v ?? "balanced")}
                        />
                        <Select
                          label="Defense"
                          size="xs"
                          data={styleOpts(stylesQ.data?.defense_styles)}
                          value={humanConfigs[key]?.defense_style ?? "swarm"}
                          onChange={(v) => setStyle(key, "defense_style", v ?? "swarm")}
                        />
                        <Select
                          label="Special teams"
                          size="xs"
                          data={styleOpts(stylesQ.data?.st_schemes)}
                          value={humanConfigs[key]?.st_scheme ?? "aces"}
                          onChange={(v) => setStyle(key, "st_scheme", v ?? "aces")}
                        />
                      </Stack>
                    </Card>
                  ))}
                </SimpleGrid>
              )}

              <Divider />
              <NumberInput
                label="AI coaching seed"
                description="0 = random each run. A fixed seed reproduces / compares experiments."
                value={aiSeed}
                min={0}
                max={999999}
                onChange={(v) => setAiSeed(Number(v) || 0)}
                w={300}
                rightSection={
                  <Tooltip label="Random seed">
                    <ActionIcon
                      variant="subtle"
                      onClick={() => setAiSeed(Math.floor(Math.random() * 999999) + 1)}
                    >
                      <IconDice5 size={16} />
                    </ActionIcon>
                  </Tooltip>
                }
              />
            </Stack>
          </Stepper.Step>

          {/* ── Step 2: conferences ── */}
          <Stepper.Step label="Conferences" description="Alignment">
            <Stack gap="sm" mt="md">
              <ConferenceEditor
                teamConf={teamConf}
                onReassign={(t, c) => setTeamConf((m) => ({ ...m, [t]: c }))}
              />
            </Stack>
          </Stepper.Step>

          {/* ── Step 3: format ── */}
          <Stepper.Step label="Format" description="Playoffs, bowls, history">
            <Stack gap="lg" mt="md">
              <div>
                <Text size="sm" fw={500} mb={6}>
                  Playoff teams
                </Text>
                <Radio.Group
                  value={String(playoffSize)}
                  onChange={(v) => setPlayoffSize(Number(v))}
                >
                  <Group gap="md">
                    {playoffOptions.map((p) => (
                      <Radio key={p} value={String(p)} label={p} />
                    ))}
                  </Group>
                </Radio.Group>
              </div>

              <div>
                <Group justify="space-between">
                  <Text size="sm" fw={500}>
                    Bowl games
                  </Text>
                  <Badge variant="light">{bowlCount}</Badge>
                </Group>
                <Slider
                  min={0}
                  max={maxBowls}
                  value={bowlCount}
                  onChange={setBowlCount}
                  disabled={maxBowls === 0}
                  marks={[
                    { value: 0, label: "0" },
                    { value: maxBowls, label: String(maxBowls) },
                  ]}
                  mt="xs"
                  mb="lg"
                />
                <Text size="xs" c="dimmed">
                  Max {maxBowls} (teams left after the {playoffSize}-team playoff).
                </Text>
              </div>

              <div>
                <Group justify="space-between">
                  <Text size="sm" fw={500}>
                    Years of league history
                  </Text>
                  <Badge variant="light">{historyYears}</Badge>
                </Group>
                <Slider
                  min={0}
                  max={100}
                  value={historyYears}
                  onChange={setHistoryYears}
                  marks={[
                    { value: 0, label: "0" },
                    { value: 50, label: "50" },
                    { value: 100, label: "100" },
                  ]}
                  mt="xs"
                  mb="lg"
                />
                <Text size="xs" c="dimmed">
                  Pre-generates prior seasons so records, prestige, and rivalries have a past.
                </Text>
              </div>
            </Stack>
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
          {step < 2 ? (
            <Button onClick={() => setStep((s) => s + 1)}>Next</Button>
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
