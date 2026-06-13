import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Stack,
  Group,
  Text,
  Card,
  Badge,
  Button,
  NumberInput,
  Tabs,
  Loader,
  Center,
  SimpleGrid,
  Anchor,
  Breadcrumbs,
  Menu,
  ActionIcon,
  Table,
} from "@mantine/core";
import { IconChevronRight, IconCoin, IconX, IconTrophy } from "@tabler/icons-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { seasonApi } from "../../api/season";
import {
  dqApi,
  FANTASY_SLOTS,
  SLOT_LABEL,
  type ParlayLeg,
  type GameOdds,
  type FantasyPlayer,
} from "../../api/dq";

const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

interface SlipLeg extends ParlayLeg {
  label: string;
}

export function DQBoard() {
  const { sessionId = "" } = useParams();
  const qc = useQueryClient();
  const [week, setWeek] = useState<number>(1);
  const [slip, setSlip] = useState<SlipLeg[]>([]);
  const [stake, setStake] = useState<number>(500);

  const status = useQuery({ queryKey: ["dq-status", sessionId], queryFn: () => dqApi.status(sessionId) });
  const season = useQuery({
    queryKey: ["season-status", sessionId],
    queryFn: () => seasonApi.status(sessionId).catch(() => null),
  });
  // default to the next unplayed week once the season loads
  useEffect(() => {
    if (season.data?.next_week) setWeek(season.data.next_week);
  }, [season.data?.next_week]);

  const odds = useQuery({
    queryKey: ["dq-odds", sessionId, week],
    queryFn: () => dqApi.odds(sessionId, week),
    enabled: week > 0,
  });
  const contest = useQuery({
    queryKey: ["dq-contest", sessionId, week],
    queryFn: () => dqApi.contest(sessionId, week),
    enabled: week > 0,
  });

  const refresh = () => {
    ["dq-status", "dq-contest", "dq-odds"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k, sessionId] }),
    );
  };

  const toggleLeg = (leg: SlipLeg) => {
    setSlip((s) => {
      const exists = s.find(
        (l) => l.game_idx === leg.game_idx && l.pick_type === leg.pick_type && l.selection === leg.selection,
      );
      if (exists) {
        return s.filter((l) => l !== exists);
      }
      // one leg per game for a parlay
      return [...s.filter((l) => l.game_idx !== leg.game_idx), leg];
    });
  };
  const legActive = (leg: SlipLeg) =>
    slip.some((l) => l.game_idx === leg.game_idx && l.pick_type === leg.pick_type && l.selection === leg.selection);

  const place = useMutation({
    mutationFn: async () => {
      if (slip.length === 1) {
        const l = slip[0];
        return dqApi.pick(sessionId, week, {
          pick_type: l.pick_type,
          game_idx: l.game_idx,
          selection: l.selection,
          amount: stake,
        });
      }
      return dqApi.parlay(sessionId, week, slip.map(({ pick_type, game_idx, selection }) => ({ pick_type, game_idx, selection })), stake);
    },
    onSuccess: () => {
      notifications.show({ message: slip.length > 1 ? "Parlay placed" : "Bet placed", color: "teal" });
      setSlip([]);
      refresh();
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });

  const resolve = useMutation({
    mutationFn: () => dqApi.resolve(sessionId, week),
    onSuccess: (r) => {
      notifications.show({
        message: `Week settled — bets ${money(r.prediction_earnings)}, fantasy ${money(r.fantasy_earnings)}${r.jackpot_bonus ? ` + jackpot ${money(r.jackpot_bonus)}` : ""}`,
        color: "teal",
        autoClose: 7000,
      });
      refresh();
      qc.invalidateQueries({ queryKey: ["dq-history", sessionId] });
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });

  if (status.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (status.isError) {
    return (
      <Card maw={600} mx="auto">
        <Text c="red">
          No DraftyQueenz on this session.{" "}
          <Anchor component={Link} to="/dq">
            Back
          </Anchor>
        </Text>
      </Card>
    );
  }

  const st = status.data!;
  const games = odds.data?.odds ?? [];

  return (
    <Stack gap="md" maw={1100} mx="auto">
      <Breadcrumbs separator={<IconChevronRight size={14} />}>
        <Anchor component={Link} to="/dq" size="sm">
          Slates
        </Anchor>
        <Text size="sm">{season.data?.name ?? "Season"}</Text>
      </Breadcrumbs>

      {/* bankroll bar */}
      <Card>
        <Group justify="space-between">
          <Group gap="xl">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Bankroll
              </Text>
              <Text size="xl" fw={800} c="teal">
                {money(st.bankroll)}
              </Text>
            </div>
            <Stat label="ROI" value={`${st.roi.toFixed(1)}%`} />
            <Stat label="Pick %" value={`${st.pick_accuracy.toFixed(0)}%`} />
            <Stat label="Wagered" value={money(st.total_wagered)} />
          </Group>
          <Group gap="xs" align="flex-end">
            <NumberInput label="Week" value={week} min={1} max={season.data?.total_weeks ?? 20} onChange={(v) => setWeek(Number(v) || 1)} w={90} />
            <Button
              variant="light"
              color="teal"
              leftSection={<IconTrophy size={16} />}
              onClick={() => resolve.mutate()}
              loading={resolve.isPending}
              disabled={contest.data?.resolved}
            >
              {contest.data?.resolved ? "Settled" : "Settle week"}
            </Button>
          </Group>
        </Group>
      </Card>

      <Tabs defaultValue="board" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="board">Board</Tabs.Tab>
          <Tabs.Tab value="fantasy">Daily Fantasy</Tabs.Tab>
          <Tabs.Tab value="tickets">My Tickets</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="board" pt="md">
          <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="md">
            <div style={{ gridColumn: "span 2" }}>
              {odds.isLoading ? (
                <Center py="xl">
                  <Loader />
                </Center>
              ) : games.length === 0 ? (
                <Text c="dimmed">No games to bet for week {week}.</Text>
              ) : (
                <Stack gap="sm">
                  {games.map((g) => (
                    <OddsCard key={g.game_idx} g={g} toggleLeg={toggleLeg} legActive={legActive} />
                  ))}
                </Stack>
              )}
            </div>
            <BetSlip
              slip={slip}
              stake={stake}
              setStake={setStake}
              place={() => place.mutate()}
              clear={() => setSlip([])}
              remove={(i) => setSlip((s) => s.filter((_, idx) => idx !== i))}
              placing={place.isPending}
            />
          </SimpleGrid>
        </Tabs.Panel>

        <Tabs.Panel value="fantasy" pt="md">
          <FantasyPanel sid={sessionId} week={week} />
        </Tabs.Panel>

        <Tabs.Panel value="tickets" pt="md">
          <TicketsPanel sid={sessionId} week={week} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="lg" fw={700}>
        {value}
      </Text>
    </div>
  );
}

function OddsCard({
  g,
  toggleLeg,
  legActive,
}: {
  g: GameOdds;
  toggleLeg: (l: SlipLeg) => void;
  legActive: (l: SlipLeg) => boolean;
}) {
  const btn = (leg: SlipLeg, sub?: string) => (
    <Button
      variant={legActive(leg) ? "filled" : "default"}
      color="teal"
      size="xs"
      onClick={() => toggleLeg(leg)}
      styles={{ root: { flex: 1 }, label: { display: "block" } }}
    >
      <Text size="xs" span>
        {leg.label}
      </Text>
      {sub && (
        <Text size="10px" c={legActive(leg) ? "white" : "dimmed"}>
          {sub}
        </Text>
      )}
    </Button>
  );
  return (
    <Card padding="sm" withBorder>
      <Group justify="space-between" mb="xs">
        <Text size="sm" fw={600}>
          {g.away_team} @ {g.home_team}
        </Text>
        <Text size="xs" c="dimmed">
          O/U {g.over_under.toFixed(1)}
        </Text>
      </Group>
      <Group gap="xs" grow>
        {btn({ game_idx: g.game_idx, pick_type: "winner", selection: g.away_team, label: g.away_team }, g.away_ml_display)}
        {btn({ game_idx: g.game_idx, pick_type: "winner", selection: g.home_team, label: g.home_team }, g.home_ml_display)}
      </Group>
      <Group gap="xs" grow mt={6}>
        {btn({ game_idx: g.game_idx, pick_type: "over_under", selection: "over", label: "Over" }, g.over_under.toFixed(1))}
        {btn({ game_idx: g.game_idx, pick_type: "over_under", selection: "under", label: "Under" }, g.over_under.toFixed(1))}
        {btn(
          { game_idx: g.game_idx, pick_type: "spread", selection: g.home_team, label: `${g.home_team} spread` },
          g.spread > 0 ? `+${g.spread}` : `${g.spread}`,
        )}
      </Group>
    </Card>
  );
}

function BetSlip({
  slip,
  stake,
  setStake,
  place,
  clear,
  remove,
  placing,
}: {
  slip: SlipLeg[];
  stake: number;
  setStake: (n: number) => void;
  place: () => void;
  clear: () => void;
  remove: (i: number) => void;
  placing: boolean;
}) {
  const isParlay = slip.length > 1;
  return (
    <Card withBorder style={{ position: "sticky", top: 72, alignSelf: "flex-start" }}>
      <Group justify="space-between" mb="xs">
        <Text fw={700}>Bet slip</Text>
        {slip.length > 0 && (
          <Anchor size="xs" onClick={clear}>
            clear
          </Anchor>
        )}
      </Group>
      {slip.length === 0 ? (
        <Text size="sm" c="dimmed">
          Tap odds to build a bet. One pick = straight bet; two or more = parlay.
        </Text>
      ) : (
        <Stack gap={6}>
          {slip.map((l, i) => (
            <Group key={i} justify="space-between" wrap="nowrap">
              <Text size="sm" lineClamp={1}>
                {l.label}
                {l.pick_type !== "winner" ? ` (${l.pick_type.replace("_", "/")})` : ""}
              </Text>
              <ActionIcon size="sm" variant="subtle" color="gray" onClick={() => remove(i)}>
                <IconX size={14} />
              </ActionIcon>
            </Group>
          ))}
          {isParlay && (
            <Badge variant="light" color="teal" w="fit-content">
              {slip.length}-leg parlay
            </Badge>
          )}
          <NumberInput
            label="Stake"
            leftSection={<IconCoin size={14} />}
            value={stake}
            min={250}
            max={25000}
            step={250}
            onChange={(v) => setStake(Number(v) || 0)}
            mt={4}
          />
          <Button color="teal" onClick={place} loading={placing} disabled={stake < 250}>
            Place {isParlay ? "parlay" : "bet"}
          </Button>
        </Stack>
      )}
    </Card>
  );
}

function FantasyPanel({ sid, week }: { sid: string; week: number }) {
  const qc = useQueryClient();
  const [posFilter, setPosFilter] = useState<string | null>(null);
  const roster = useQuery({ queryKey: ["dq-roster", sid, week], queryFn: () => dqApi.roster(sid, week) });
  const pool = useQuery({
    queryKey: ["dq-pool", sid, week],
    queryFn: () => dqApi.pool(sid, week),
    enabled: roster.data?.entered === true,
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["dq-roster", sid, week] });
    qc.invalidateQueries({ queryKey: ["dq-status", sid] });
  };

  const enter = useMutation({
    mutationFn: () => dqApi.enterFantasy(sid, week),
    onSuccess: () => {
      notifications.show({ message: "Entered the daily contest", color: "teal" });
      refresh();
    },
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });
  const setSlot = useMutation({
    mutationFn: ({ slot, p }: { slot: string; p: FantasyPlayer }) => dqApi.setSlot(sid, week, slot, p.tag, p.team),
    onSuccess: () => refresh(),
    onError: (e: unknown) => notifications.show({ message: String(e instanceof Error ? e.message : e), color: "red" }),
  });
  const clearSlot = useMutation({
    mutationFn: (slot: string) => dqApi.clearSlot(sid, week, slot),
    onSuccess: () => refresh(),
  });

  if (roster.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }
  if (!roster.data?.entered) {
    return (
      <Card maw={520}>
        <Stack gap="sm" align="flex-start">
          <Text>Draft a 5-slot lineup under the salary cap and climb tonight's board.</Text>
          <Button color="teal" onClick={() => enter.mutate()} loading={enter.isPending}>
            Enter — $2,500
          </Button>
        </Stack>
      </Card>
    );
  }

  const entries = roster.data.roster?.entries ?? {};
  const positions = ["VP", "HB", "ZB", "WB", "SB", "KP"];
  const players = (pool.data?.pool ?? []).filter((p) => !posFilter || p.position === posFilter);

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
      <Card withBorder>
        <Group justify="space-between" mb="xs">
          <Text fw={700}>Lineup</Text>
          <Badge variant="light" color="teal">
            {money(roster.data.salary_remaining)} cap left
          </Badge>
        </Group>
        <Stack gap={6}>
          {FANTASY_SLOTS.map((slot) => {
            const e = entries[slot];
            return (
              <Group key={slot} justify="space-between" wrap="nowrap">
                <Text size="xs" c="dimmed" w={90}>
                  {SLOT_LABEL[slot]}
                </Text>
                {e ? (
                  <Group gap="xs" justify="flex-end" wrap="nowrap" style={{ flex: 1 }}>
                    <Text size="sm" lineClamp={1}>
                      {e.name} · {e.team}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {money(e.salary)}
                    </Text>
                    <ActionIcon size="sm" variant="subtle" color="gray" onClick={() => clearSlot.mutate(slot)}>
                      <IconX size={14} />
                    </ActionIcon>
                  </Group>
                ) : (
                  <Text size="sm" c="dimmed">
                    empty
                  </Text>
                )}
              </Group>
            );
          })}
        </Stack>
      </Card>

      <Card withBorder>
        <Group justify="space-between" mb="xs">
          <Text fw={700}>Player pool</Text>
          <Group gap={4}>
            <Badge variant={posFilter ? "default" : "light"} style={{ cursor: "pointer" }} onClick={() => setPosFilter(null)}>
              All
            </Badge>
            {positions.map((p) => (
              <Badge key={p} variant={posFilter === p ? "light" : "default"} style={{ cursor: "pointer" }} onClick={() => setPosFilter(p)}>
                {p}
              </Badge>
            ))}
          </Group>
        </Group>
        <Table.ScrollContainer minWidth={0} mah="55vh">
          <Table striped highlightOnHover fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Player</Table.Th>
                <Table.Th>Pos</Table.Th>
                <Table.Th>$</Table.Th>
                <Table.Th>Proj</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {players.map((p) => (
                <Table.Tr key={`${p.team}-${p.tag}`}>
                  <Table.Td>
                    {p.name}{" "}
                    <Text span size="xs" c="dimmed">
                      {p.team}
                    </Text>
                  </Table.Td>
                  <Table.Td>{p.position}</Table.Td>
                  <Table.Td>{money(p.salary)}</Table.Td>
                  <Table.Td>{p.projected.toFixed(1)}</Table.Td>
                  <Table.Td>
                    <Menu withinPortal position="bottom-end">
                      <Menu.Target>
                        <Button size="compact-xs" variant="light">
                          Add
                        </Button>
                      </Menu.Target>
                      <Menu.Dropdown>
                        {FANTASY_SLOTS.map((slot) => (
                          <Menu.Item key={slot} onClick={() => setSlot.mutate({ slot, p })}>
                            {SLOT_LABEL[slot]}
                          </Menu.Item>
                        ))}
                      </Menu.Dropdown>
                    </Menu>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>
    </SimpleGrid>
  );
}

function TicketsPanel({ sid, week }: { sid: string; week: number }) {
  const contest = useQuery({ queryKey: ["dq-contest", sid, week], queryFn: () => dqApi.contest(sid, week) });
  const history = useQuery({ queryKey: ["dq-history", sid], queryFn: () => dqApi.history(sid) });
  if (contest.isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }
  const picks = contest.data?.picks ?? [];
  const parlays = contest.data?.parlays ?? [];
  const resultColor = (r: string) => (r === "win" ? "teal" : r === "loss" ? "red" : r === "push" ? "gray" : "yellow");
  return (
    <Stack gap="md">
      <Card withBorder>
        <Text fw={700} mb="xs">
          Week {week} tickets
        </Text>
        {picks.length === 0 && parlays.length === 0 ? (
          <Text size="sm" c="dimmed">
            No bets this week yet.
          </Text>
        ) : (
          <Stack gap={4}>
            {picks.map((p, i) => (
              <Group key={i} justify="space-between">
                <Text size="sm">
                  {p.selection} <Text span c="dimmed" size="xs">({p.pick_type}) · {p.matchup}</Text>
                </Text>
                <Group gap="xs">
                  <Text size="sm">{money(p.amount)}</Text>
                  <Badge size="xs" color={resultColor(p.result)} variant="light">
                    {p.result || "open"}
                  </Badge>
                </Group>
              </Group>
            ))}
            {parlays.map((p, i) => (
              <Group key={`pl${i}`} justify="space-between">
                <Text size="sm">{p.legs.length}-leg parlay ×{p.multiplier}</Text>
                <Group gap="xs">
                  <Text size="sm">{money(p.amount)} → {money(p.potential_payout)}</Text>
                  <Badge size="xs" color={resultColor(p.result)} variant="light">
                    {p.result || "open"}
                  </Badge>
                </Group>
              </Group>
            ))}
          </Stack>
        )}
      </Card>

      {history.data && (
        <Card withBorder>
          <Group justify="space-between" mb="xs">
            <Text fw={700}>Season ledger</Text>
            <Badge size="lg" variant="light" color={history.data.net >= 0 ? "teal" : "red"}>
              Net {history.data.net >= 0 ? "+" : ""}
              {money(history.data.net)}
            </Badge>
          </Group>
          <Text size="sm" c="dimmed">
            Won {money(history.data.total_won)} · Lost {money(history.data.total_lost)} across{" "}
            {history.data.picks.length} tickets
          </Text>
        </Card>
      )}
    </Stack>
  );
}
