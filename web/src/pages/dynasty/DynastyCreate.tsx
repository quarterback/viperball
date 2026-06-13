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
  Radio,
  Slider,
  Badge,
  Loader,
  Center,
} from "@mantine/core";
import { IconChevronRight, IconRocket } from "@tabler/icons-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi } from "../../api/season";
import { dynastyCreateApi, type CreateDynastyConfig } from "../../api/dynasty";
import { ConferenceEditor } from "../../components/ConferenceEditor";

const PLAYOFF_OPTIONS = [4, 8, 12, 16, 24, 32];

export function DynastyCreate() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const teamsQ = useQuery({ queryKey: ["teams"], queryFn: seasonApi.teams });
  const confDefaultsQ = useQuery({
    queryKey: ["conference-defaults"],
    queryFn: seasonApi.conferenceDefaults,
  });
  const archetypesQ = useQuery({
    queryKey: ["program-archetypes"],
    queryFn: dynastyCreateApi.programArchetypes,
  });

  const teams = useMemo(() => teamsQ.data ?? [], [teamsQ.data]);
  const totalTeams = teams.length;

  const [dynastyName, setDynastyName] = useState("My Viperball Dynasty");
  const [coachName, setCoachName] = useState("Coach");
  const [coachTeam, setCoachTeam] = useState<string | null>(null);
  const [archetype, setArchetype] = useState<string | null>(null);
  const [startingYear, setStartingYear] = useState(2026);
  const [historyYears, setHistoryYears] = useState(0);
  const [playoffSize, setPlayoffSize] = useState(8);
  const [bowlCount, setBowlCount] = useState(4);
  const [gamesPerTeam, setGamesPerTeam] = useState(12);
  const [teamConf, setTeamConf] = useState<Record<string, string>>({});
  const [confFilter, setConfFilter] = useState("__all__");

  useEffect(() => {
    if (confDefaultsQ.data && Object.keys(teamConf).length === 0) {
      const map: Record<string, string> = {};
      for (const [conf, members] of Object.entries(confDefaultsQ.data))
        for (const t of members) map[t] = conf;
      setTeamConf(map);
    }
  }, [confDefaultsQ.data, teamConf]);

  // Default the archetype to regional_power (or first) once loaded.
  useEffect(() => {
    if (archetypesQ.data && !archetype) {
      const keys = Object.keys(archetypesQ.data);
      setArchetype(keys.includes("regional_power") ? "regional_power" : keys[0] ?? null);
    }
  }, [archetypesQ.data, archetype]);

  const confNames = useMemo(
    () => Array.from(new Set(Object.values(teamConf))).sort(),
    [teamConf],
  );
  const playoffOptions = PLAYOFF_OPTIONS.filter((p) => p <= totalTeams || totalTeams === 0);
  const maxBowls = Math.max(0, Math.min(16, Math.floor((totalTeams - playoffSize) / 2)));
  useEffect(() => setBowlCount((b) => Math.min(b, maxBowls)), [maxBowls]);

  const teamOptions = teams
    .filter((t) => confFilter === "__all__" || (teamConf[t.name] ?? t.conference) === confFilter)
    .map((t) => ({ value: t.name, label: `${t.name} (${teamConf[t.name] ?? t.conference})` }));

  const create = useMutation({
    mutationFn: () => {
      const conferences: Record<string, string[]> = {};
      for (const [t, c] of Object.entries(teamConf)) (conferences[c] ??= []).push(t);
      const cfg: CreateDynastyConfig = {
        dynasty_name: dynastyName,
        coach_name: coachName,
        coach_team: coachTeam!,
        starting_year: startingYear,
        program_archetype: archetype,
        history_years: historyYears,
        games_per_team: gamesPerTeam,
        playoff_size: playoffSize,
        bowl_count: bowlCount,
        num_conferences: confNames.length || 10,
        conferences,
      };
      return dynastyCreateApi.create(cfg);
    },
    onSuccess: (sid) => {
      notifications.show({ message: "Dynasty created", color: "grape" });
      navigate(`/dynasty/${sid}`);
    },
    onError: () => notifications.show({ message: "Couldn't create the dynasty", color: "red" }),
  });

  const loading = teamsQ.isLoading || confDefaultsQ.isLoading || archetypesQ.isLoading;
  if (loading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md" maw={760}>
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/dynasty" size="sm">
          Dynasties
        </Anchor>
        <Text size="sm">New Dynasty</Text>
      </Breadcrumbs>

      <Title order={2}>New Dynasty</Title>

      <Card>
        <Stepper active={step} onStepClick={setStep} size="sm">
          <Stepper.Step label="Coach & Team" description="Identity">
            <Stack gap="md" mt="md">
              <Group grow>
                <TextInput
                  label="Dynasty name"
                  value={dynastyName}
                  onChange={(e) => setDynastyName(e.currentTarget.value)}
                />
                <TextInput
                  label="Coach name"
                  value={coachName}
                  onChange={(e) => setCoachName(e.currentTarget.value)}
                />
              </Group>
              <Group align="flex-end" grow>
                <Select
                  label="Filter by conference"
                  data={[
                    { value: "__all__", label: "All teams" },
                    ...confNames.map((c) => ({ value: c, label: c })),
                  ]}
                  value={confFilter}
                  onChange={(v) => setConfFilter(v ?? "__all__")}
                />
                <Select
                  label="Your team"
                  placeholder="Pick a team"
                  data={teamOptions}
                  value={coachTeam}
                  onChange={setCoachTeam}
                  searchable
                />
              </Group>
              <NumberInput
                label="Starting year"
                value={startingYear}
                min={1906}
                max={2050}
                onChange={(v) => setStartingYear(Number(v) || 2026)}
                w={200}
              />
              {archetypesQ.data && (
                <div>
                  <Text size="sm" fw={500} mb={6}>
                    Program archetype
                  </Text>
                  <Radio.Group value={archetype} onChange={setArchetype}>
                    <Stack gap="xs">
                      {Object.entries(archetypesQ.data).map(([key, a]) => (
                        <Radio
                          key={key}
                          value={key}
                          label={
                            <span>
                              <Text span fw={600} size="sm">
                                {a.label}
                              </Text>
                              <Text span c="dimmed" size="xs">
                                {" "}
                                — {a.description}
                              </Text>
                            </span>
                          }
                        />
                      ))}
                    </Stack>
                  </Radio.Group>
                </div>
              )}
            </Stack>
          </Stepper.Step>

          <Stepper.Step label="Conferences" description="Alignment">
            <Stack gap="sm" mt="md">
              <ConferenceEditor
                teamConf={teamConf}
                onReassign={(t, c) => setTeamConf((m) => ({ ...m, [t]: c }))}
              />
            </Stack>
          </Stepper.Step>

          <Stepper.Step label="Format" description="Defaults">
            <Stack gap="lg" mt="md">
              <NumberInput
                label="Games per team"
                value={gamesPerTeam}
                min={6}
                max={16}
                onChange={(v) => setGamesPerTeam(Number(v) || 12)}
                w={200}
              />
              <div>
                <Text size="sm" fw={500} mb={6}>
                  Playoff teams
                </Text>
                <Radio.Group value={String(playoffSize)} onChange={(v) => setPlayoffSize(Number(v))}>
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
                  mt="xs"
                  mb="lg"
                />
              </div>
              <div>
                <Group justify="space-between">
                  <Text size="sm" fw={500}>
                    Years of league history
                  </Text>
                  <Badge variant="light">{historyYears}</Badge>
                </Group>
                <Slider min={0} max={100} value={historyYears} onChange={setHistoryYears} mt="xs" mb="lg" />
              </div>
            </Stack>
          </Stepper.Step>
        </Stepper>

        <Group justify="space-between" mt="xl">
          <Button variant="default" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
            Back
          </Button>
          {step < 2 ? (
            <Button onClick={() => setStep((s) => s + 1)} disabled={step === 0 && !coachTeam}>
              Next
            </Button>
          ) : (
            <Button
              leftSection={<IconRocket size={16} />}
              onClick={() => create.mutate()}
              loading={create.isPending}
              disabled={!coachTeam}
            >
              Create dynasty
            </Button>
          )}
        </Group>
      </Card>
    </Stack>
  );
}
