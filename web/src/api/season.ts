// College season API — the live, in-memory season endpoints the League Hub renders.
import { apiGet, apiSend } from "./client";

const enc = encodeURIComponent;

export interface CollegeSession {
  session_id: string;
  name: string;
  phase: string;
  current_week: number;
  total_weeks: number;
  team_count: number;
  champion: string | null;
  human_teams: string[];
}

export interface SeasonStatus {
  phase: string;
  current_week: number;
  next_week: number;
  total_weeks: number;
  games_played: number;
  total_games: number;
  progress_pct: number;
  champion: string | null;
  name: string;
  team_count: number;
}

export interface Standing {
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  conference: string;
  games_played: number;
  win_percentage: number;
  points_for: number;
  points_against: number;
  point_differential: number;
  conf_wins: number;
  conf_losses: number;
  avg_ppd: number;
  kenpom?: Record<string, number>;
  dtw?: { luck_differential: number; expected_wins: number };
}

export interface Game {
  week: number;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  completed: boolean;
  is_conference_game: boolean;
  is_rivalry_game: boolean;
}

export interface PollEntry {
  rank: number;
  team_name: string;
  record: string;
  conference: string;
  power_index: number;
  rank_change: number;
  quality_wins: number;
}

export interface PlayerStat {
  name: string;
  team: string;
  conference: string;
  tag: string;
  archetype: string;
  touches: number;
  yards: number;
  tds: number;
  yards_per_touch: number;
  tackles: number;
  sacks: number;
}

export interface RosterPlayer {
  name: string;
  number: number;
  position: string;
  position_full: string;
  archetype: string;
  overall: number;
  year_abbr: string;
  speed: number;
  power: number;
  agility: number;
  hands: number;
  awareness: number;
  stamina: number;
  kicking: number;
  tackling: number;
  height: string;
  weight: number;
  hometown_city: string;
  hometown_state: string;
  depth_status: string;
}

export const seasonApi = {
  listSessions: () =>
    apiGet<{ sessions: CollegeSession[] }>("/api/sessions/college").then((r) => r.sessions),

  status: (sid: string) => apiGet<SeasonStatus>(`/sessions/${sid}/season/status`),

  standings: (sid: string) =>
    apiGet<{ standings: Standing[] }>(`/sessions/${sid}/season/standings`).then((r) => r.standings),

  schedule: (sid: string) =>
    apiGet<{ games: Game[] }>(`/sessions/${sid}/season/schedule`).then((r) => r.games),

  // Returns the most recent week's poll rankings (endpoint gives every week).
  polls: (sid: string) =>
    apiGet<{ polls: { week: number; rankings: PollEntry[] }[] }>(
      `/sessions/${sid}/season/polls`,
    ).then((r) => (r.polls.length ? r.polls[r.polls.length - 1].rankings : [])),

  leaders: (sid: string) =>
    apiGet<{ players: PlayerStat[] }>(`/sessions/${sid}/season/player-stats?min_touches=1`).then(
      (r) => r.players,
    ),

  roster: (sid: string, team: string) =>
    apiGet<{ team_name: string; roster: RosterPlayer[]; prestige: number | null }>(
      `/sessions/${sid}/season/roster/${enc(team)}`,
    ),

  simWeek: (sid: string) => apiSend("POST", `/sessions/${sid}/season/simulate-week`),
  simRest: (sid: string) => apiSend("POST", `/sessions/${sid}/season/simulate-rest`),

  teams: () =>
    apiGet<{ teams: { key: string; name: string }[] }>("/teams").then((r) => r.teams),
};

export interface NewSeasonConfig {
  name: string;
  human_teams: string[];
  ai_seed: number;
  games_per_team: number;
  playoff_size: number;
  bowl_count: number;
  num_conferences: number;
  history_years: number;
}

// Create a fresh session + season in one call, returning the new session id.
export async function createSeason(config: NewSeasonConfig): Promise<string> {
  const { session_id } = await apiSend<{ session_id: string }>("POST", "/sessions");
  await apiSend("POST", `/sessions/${session_id}/season`, config);
  return session_id;
}
