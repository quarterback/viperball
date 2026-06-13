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

  // fastSim=false runs the full play-by-play engine; true uses the fast sim.
  simWeek: (sid: string, fastSim: boolean) =>
    apiSend("POST", `/sessions/${sid}/season/simulate-week`, { fast_sim: fastSim }),
  simRest: (sid: string, fastSim: boolean) =>
    apiSend("POST", `/sessions/${sid}/season/simulate-rest`, { fast_sim: fastSim }),

  // Pre-season transfer portal (phase "portal" before "regular").
  portal: (sid: string) =>
    apiGet<{
      entries: SeasonPortalEntry[];
      committed: SeasonPortalEntry[];
      transfers_remaining: number;
      human_team: string;
    }>(`/sessions/${sid}/season/portal`).catch(() => null),
  portalCommit: (sid: string, team_name: string, entry_index: number) =>
    apiSend("POST", `/sessions/${sid}/season/portal/commit`, { team_name, entry_index }),
  portalSkip: (sid: string) => apiSend("POST", `/sessions/${sid}/season/portal/skip`),

  // Read-only saved season (archive snapshot) — reuses live serializer shapes.
  archive: (key: string) =>
    apiGet<ArchiveSnapshot>(`/archives/${encodeURIComponent(key)}`),

  // ── Postseason ──
  simPlayoffs: (sid: string) => apiSend("POST", `/sessions/${sid}/season/playoffs`),
  simBowls: (sid: string) => apiSend("POST", `/sessions/${sid}/season/bowls`),
  playoffBracket: (sid: string) =>
    apiGet<{ bracket: Game[]; champion: string | null }>(
      `/sessions/${sid}/season/playoff-bracket`,
    ),
  bowlResults: (sid: string) =>
    apiGet<{ bowl_results: BowlResult[] }>(`/sessions/${sid}/season/bowl-results`).then(
      (r) => r.bowl_results,
    ),

  // ── Hub depth ──
  awards: (sid: string) => apiGet<SeasonAwardsResp>(`/sessions/${sid}/season/awards`),
  injuries: (sid: string) =>
    apiGet<{ active: InjuryRecord[]; season_log: InjuryRecord[] }>(
      `/sessions/${sid}/season/injuries`,
    ),
  conferences: (sid: string) =>
    apiGet<{ conferences: Record<string, ConferenceBlock>; champions: Record<string, string> }>(
      `/sessions/${sid}/season/conferences`,
    ),

  teams: () =>
    apiGet<{ teams: TeamMeta[] }>("/teams").then((r) => r.teams),

  styles: () => apiGet<StylesResponse>("/styles"),

  conferenceDefaults: () =>
    apiGet<{ conferences: Record<string, string[]> }>("/conference-defaults").then(
      (r) => r.conferences,
    ),
};

export interface TeamMeta {
  key: string;
  name: string;
  mascot?: string;
  conference?: string;
}

export interface StyleOption {
  label: string;
  description: string;
}
export interface StylesResponse {
  offense_styles: Record<string, StyleOption>;
  defense_styles: Record<string, StyleOption>;
  st_schemes: Record<string, StyleOption>;
}

export type TeamStyle = { offense_style: string; defense_style: string; st_scheme: string };

export interface BowlResult {
  name: string;
  tier: string;
  team_1_seed?: number;
  team_2_seed?: number;
  team_1_record?: string;
  team_2_record?: string;
  game: Game;
}

export interface InjuryRecord {
  player_name: string;
  team_name: string;
  position: string;
  category: string;
  description: string;
  body_part: string;
  week_injured: number;
  weeks_out: number;
  is_season_ending: boolean;
  game_status?: string;
}

export interface ConferenceBlock {
  teams: string[];
  standings: Standing[];
}

export interface AwardEntry {
  award_name: string;
  player_name: string;
  team_name: string;
  position: string;
  year_in_school?: string;
  overall_rating?: number;
  reason?: string;
}
export interface SeasonAwardsResp {
  individual_awards?: AwardEntry[];
  all_american_first?: AwardEntry[];
  coach_of_year?: { name?: string; team_name?: string } | string | null;
  error?: string;
}

export interface ArchiveSnapshot {
  type: string;
  label: string;
  season_name: string;
  champion: string | null;
  standings: Standing[];
  schedule: Game[];
  polls: { week: number; rankings: PollEntry[] }[];
  team_rosters: Record<string, { players: RosterPlayer[]; mascot?: string }>;
}

export interface SeasonPortalEntry {
  global_index: number;
  name?: string;
  player_name?: string;
  position?: string;
  overall?: number;
  year?: string;
  origin_team?: string;
  former_team?: string;
}

export interface NewSeasonConfig {
  name: string;
  human_teams: string[];
  human_configs: Record<string, TeamStyle>;
  ai_seed: number;
  games_per_team: number;
  playoff_size: number;
  bowl_count: number;
  num_conferences: number;
  history_years: number;
  conferences: Record<string, string[]>;
}

// Create a fresh session + season in one call, returning the new session id.
export async function createSeason(config: NewSeasonConfig): Promise<string> {
  const { session_id } = await apiSend<{ session_id: string }>("POST", "/sessions");
  await apiSend("POST", `/sessions/${session_id}/season`, config);
  return session_id;
}
