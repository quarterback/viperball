// Pro Leagues API. Five fixed leagues; sessions are created on demand.
import { apiGet, apiSend } from "./client";

export const PRO_LEAGUES: { id: string; name: string }[] = [
  { id: "nvl", name: "National Viperball League" },
  { id: "el", name: "Eurasian League" },
  { id: "al", name: "AfroLeague" },
  { id: "pl", name: "Pacific League" },
  { id: "la_league", name: "LigaAmerica" },
];

export const PRO_LEAGUE_NAME: Record<string, string> = Object.fromEntries(
  PRO_LEAGUES.map((l) => [l.id, l.name]),
);

export interface ProStatus {
  league: string;
  league_id: string;
  phase: string;
  current_week: number;
  total_weeks: number;
  champion: string | null;
  champion_name: string | null;
  team_count: number;
}

export interface ProActiveSession {
  key: string;
  league: string;
  league_name: string;
  status: ProStatus;
}

export interface ProStandingRow {
  team_key: string;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  points: number;
  pct: number;
  pf: number;
  pa: number;
  diff: number;
  div_record: string;
  streak: string;
  last_5: string;
  division?: string; // injected client-side
}

export interface ProGame {
  matchup_key: string;
  home_name: string;
  away_name: string;
  home_key: string;
  away_key: string;
  completed: boolean;
  home_score?: number;
  away_score?: number;
  week?: number; // injected client-side
}

export interface ProStatLeader {
  name: string;
  team: string;
  team_key: string;
  position: string;
  value: number;
  games: number;
  [k: string]: string | number;
}

export interface ProBracketTeam {
  team_key: string;
  team_name: string;
}
export interface ProBracketMatchup {
  home: ProBracketTeam;
  away: ProBracketTeam | null;
  round: string;
  home_score?: number;
  away_score?: number;
  winner?: string;
  winner_name?: string;
}
export interface ProBracketRound {
  round_name: string;
  matchups: ProBracketMatchup[];
  bye_teams: ProBracketTeam[];
  completed: boolean;
}

export const proApi = {
  active: () =>
    apiGet<{ active_sessions: ProActiveSession[] }>("/api/pro/active").then(
      (r) => r.active_sessions,
    ),

  newSeason: (league: string) =>
    apiSend<{ league: string; session_id: string; key: string }>(
      "POST",
      `/api/pro/${league}/new`,
    ),

  status: (league: string, sid: string) =>
    apiGet<ProStatus>(`/api/pro/${league}/${sid}/status`),

  // Flatten the division-keyed standings into rows with a division column.
  standings: (league: string, sid: string) =>
    apiGet<{ divisions: Record<string, ProStandingRow[]> }>(
      `/api/pro/${league}/${sid}/standings`,
    ).then((r) =>
      Object.entries(r.divisions).flatMap(([division, rows]) =>
        rows.map((row) => ({ ...row, division })),
      ),
    ),

  // Flatten weeks into a single game list with a week column.
  schedule: (league: string, sid: string) =>
    apiGet<{ weeks: { week: number; games: ProGame[] }[] }>(
      `/api/pro/${league}/${sid}/schedule`,
    ).then((r) => r.weeks.flatMap((w) => w.games.map((g) => ({ ...g, week: w.week })))),

  stats: (league: string, sid: string) =>
    apiGet<Record<string, ProStatLeader[]>>(`/api/pro/${league}/${sid}/stats?category=all`),

  bracket: (league: string, sid: string) =>
    apiGet<{ rounds: ProBracketRound[]; champion_name: string | null }>(
      `/api/pro/${league}/${sid}/playoffs/bracket`,
    ),

  simWeek: (league: string, sid: string) =>
    apiSend("POST", `/api/pro/${league}/${sid}/sim-week`),
  simAll: (league: string, sid: string) =>
    apiSend("POST", `/api/pro/${league}/${sid}/sim-all`),
};
