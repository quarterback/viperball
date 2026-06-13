// International / FIV API. One global cycle at a time (World Cup + rankings).
import { apiGet, apiSend } from "./client";

export interface FivRanking {
  rank: number;
  code: string;
  rating: number;
}

export interface FivGroupStanding {
  team: string;
  code: string;
  p: number;
  w: number;
  d: number;
  l: number;
  pf: number;
  pa: number;
  point_diff: number;
  pts: number;
  group?: string; // injected client-side
}

export interface FivGroup {
  group_name: string;
  standings: FivGroupStanding[];
}

export interface FivBracketMatchup {
  home_code?: string;
  away_code?: string;
  home_score?: number;
  away_score?: number;
  winner?: string;
  [k: string]: unknown;
}
export interface FivBracketRound {
  round_name: string;
  matchups: FivBracketMatchup[];
  completed: boolean;
}

export interface FivCycleSummary {
  cycle_number: number;
  phase: string;
  host_nation: string | null;
  // world_cup is large; we only read a few fields defensively
  world_cup?: { phase?: string; champion?: string | null };
}

export const fivApi = {
  // Active cycle may not exist (404/empty) — caller handles null.
  activeCycle: () =>
    apiGet<FivCycleSummary>("/api/fiv/cycle/active").catch(() => null),

  rankings: () =>
    apiGet<{ rankings: FivRanking[] }>("/api/fiv/rankings").then((r) => r.rankings),

  groups: () =>
    apiGet<{ groups: FivGroup[]; phase: string }>("/api/fiv/worldcup/groups").then((r) =>
      r.groups.flatMap((g) =>
        (g.standings ?? []).map((s) => ({ ...s, group: g.group_name })),
      ),
    ),

  bracket: () =>
    apiGet<{ knockout_rounds: FivBracketRound[]; champion: string | null }>(
      "/api/fiv/worldcup/bracket",
    ),

  newCycle: (seed?: number) =>
    apiSend("POST", "/api/fiv/cycle/new", { seed: seed ?? null, host_nation: null }),

  simStage: () => apiSend("POST", "/api/fiv/worldcup/sim-stage"),
};
