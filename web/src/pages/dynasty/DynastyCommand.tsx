import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Card,
  Group,
  Stack,
  Text,
  Button,
  NumberInput,
  Select,
  Badge,
  Tooltip,
  ActionIcon,
  Loader,
  Center,
  Anchor,
} from "@mantine/core";
import {
  IconPlayerPlay,
  IconArrowRight,
  IconDice5,
  IconRocket,
} from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi } from "../../api/season";
import { dynastyCreateApi, offseasonApi, type DynastyStatus } from "../../api/dynasty";
import { OffseasonFlow } from "./OffseasonFlow";

export function DynastyCommand({ sid, status }: { sid: string; status: DynastyStatus }) {
  const qc = useQueryClient();

  const season = useQuery({
    queryKey: ["season-status", sid],
    queryFn: () => seasonApi.status(sid).catch(() => null),
  });
  const offseason = useQuery({
    queryKey: ["offseason-status", sid],
    queryFn: () => offseasonApi.status(sid),
  });

  const invalidate = () => {
    ["dynasty-status", "season-status", "offseason-status", "dynasty-histories", "dynasty-awards", "dynasty-records"].forEach(
      (k) => qc.invalidateQueries({ queryKey: [k, sid] }),
    );
  };

  const advance = useMutation({
    mutationFn: () => dynastyCreateApi.advance(sid),
    onSuccess: () => {
      notifications.show({ message: "Advanced to offseason", color: "grape" });
      invalidate();
    },
    onError: () => notifications.show({ message: "Advance failed (is the season finished?)", color: "red" }),
  });

  if (season.isLoading || offseason.isLoading) {
    return (
      <Card>
        <Center py="md">
          <Loader size="sm" />
        </Center>
      </Card>
    );
  }

  // 1. In the offseason loop.
  if (offseason.data) {
    return <OffseasonFlow sid={sid} onComplete={invalidate} />;
  }

  // 2. A season is active.
  if (season.data) {
    const s = season.data;
    const done = s.games_played >= s.total_games;
    return (
      <Card>
        <Group justify="space-between">
          <Stack gap={2}>
            <Text fw={700}>{s.name}</Text>
            <Text size="sm" c="dimmed">
              Week {s.current_week} / {s.total_weeks} · {s.games_played}/{s.total_games} games
              {s.champion ? ` · 🏆 ${s.champion}` : ""}
            </Text>
          </Stack>
          <Group gap="xs">
            <Button
              component={Link}
              to={`/league/${sid}`}
              variant="light"
              leftSection={<IconPlayerPlay size={16} />}
            >
              Play season
            </Button>
            <Button
              color="grape"
              rightSection={<IconArrowRight size={16} />}
              onClick={() => advance.mutate()}
              loading={advance.isPending}
              disabled={!done}
            >
              Advance to offseason
            </Button>
          </Group>
        </Group>
        {!done && (
          <Text size="xs" c="dimmed" mt="xs">
            Finish the season (Play → Sim Rest) to advance.
          </Text>
        )}
      </Card>
    );
  }

  // 3. No season yet — start one.
  return <StartSeasonForm sid={sid} status={status} onStarted={invalidate} />;
}

function StartSeasonForm({
  sid,
  status,
  onStarted,
}: {
  sid: string;
  status: DynastyStatus;
  onStarted: () => void;
}) {
  const navigate = useNavigate();
  const stylesQ = useQuery({ queryKey: ["styles"], queryFn: seasonApi.styles });

  const [offense, setOffense] = useState("balanced");
  const [defense, setDefense] = useState("swarm");
  const [st, setSt] = useState("aces");
  const [seed, setSeed] = useState(0);

  const start = useMutation({
    mutationFn: () =>
      dynastyCreateApi.startSeason(sid, {
        games_per_team: status.games_per_team ?? 12,
        playoff_size: status.playoff_size ?? 8,
        bowl_count: status.bowl_count ?? 4,
        offense_style: offense,
        defense_style: defense,
        st_scheme: st,
        ai_seed: seed || null,
      }),
    onSuccess: () => {
      notifications.show({ message: `Started ${status.current_year} season`, color: "grape" });
      onStarted();
      navigate(`/league/${sid}`);
    },
    onError: () => notifications.show({ message: "Couldn't start the season", color: "red" }),
  });

  const opts = (rec: Record<string, { label: string }> | undefined) =>
    Object.entries(rec ?? {}).map(([value, v]) => ({ value, label: v.label }));

  return (
    <Card>
      <Group justify="space-between" mb="md">
        <Text fw={700}>Start {status.current_year} season</Text>
        <Badge variant="light" color="grape">
          {status.coach.team}
        </Badge>
      </Group>
      <Group grow mb="md">
        <Select label="Offense" data={opts(stylesQ.data?.offense_styles)} value={offense} onChange={(v) => setOffense(v ?? "balanced")} />
        <Select label="Defense" data={opts(stylesQ.data?.defense_styles)} value={defense} onChange={(v) => setDefense(v ?? "swarm")} />
        <Select label="Special teams" data={opts(stylesQ.data?.st_schemes)} value={st} onChange={(v) => setSt(v ?? "aces")} />
      </Group>
      <Group align="flex-end">
        <NumberInput
          label="AI seed"
          description="0 = random"
          value={seed}
          min={0}
          max={999999}
          onChange={(v) => setSeed(Number(v) || 0)}
          w={220}
          rightSection={
            <Tooltip label="Random seed">
              <ActionIcon variant="subtle" onClick={() => setSeed(Math.floor(Math.random() * 999999) + 1)}>
                <IconDice5 size={16} />
              </ActionIcon>
            </Tooltip>
          }
        />
        <Button
          color="grape"
          leftSection={<IconRocket size={16} />}
          onClick={() => start.mutate()}
          loading={start.isPending}
        >
          Start season
        </Button>
      </Group>
      <Text size="xs" c="dimmed" mt="sm">
        Uses the dynasty's format (playoffs/bowls). You'll sim it in the{" "}
        <Anchor component={Link} to={`/league/${sid}`}>
          League hub
        </Anchor>
        , then return here to advance.
      </Text>
    </Card>
  );
}
