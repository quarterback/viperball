// WVL — Career League. The destination for CVL graduates: the same player
// cards are imported and their careers persist, simulated game-by-game.
import { apiGet, apiSend } from "./client";

export interface WVLStatus {
  league_id: string;
  year: number;
  phase: string; // "regular" | "complete" | "preseason"
  current_week: number;
  total_weeks: number;
  clubs: number;
  tracked_players: number;
  active_players: number;
  seasons_completed: number;
  champion: string | null;
}

export interface WVLStandRow {
  team_key: string;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  pa: number;
  diff: number;
  games: number;
  position: number;
}

export interface WVLGame {
  home_key: string;
  away_key: string;
  home_name: string;
  away_name: string;
  home_score?: number;
  away_score?: number;
}
export interface WVLWeek {
  week: number;
  played: boolean;
  games: WVLGame[];
}

export interface WVLPlayer {
  player_id: string;
  name: string;
  position: string;
  overall: number;
  age: number | null;
  club: string;
  club_key: string | null;
  status: string;
  career_games: number;
  career_yards: number;
  career_touchdowns: number;
  career_seasons: number;
  season_yards: number;
  season_tds: number;
  season_games: number;
}

export interface WVLCareerSeason {
  year: number;
  team: string;
  games: number;
  yards: number;
  rushing_yards: number;
  lateral_yards: number;
  kick_pass_yards: number;
  touchdowns: number;
  tackles: number;
  fumbles: number;
  league: string; // "CVL" | "WVL"
}
export interface WVLPlayerDetail extends WVLPlayer {
  first_name: string;
  last_name: string;
  nationality: string;
  archetype: string;
  ratings: Record<string, number>;
  career_seasons_list?: WVLCareerSeason[];
  career_seasons: any; // overloaded: number on brief, array on detail
}

export interface WVLLeaders {
  season_yards: WVLPlayer[];
  season_tds: WVLPlayer[];
  career_yards: WVLPlayer[];
  career_touchdowns: WVLPlayer[];
}

export interface WVLHistoryEntry {
  year: number;
  champion: string | null;
  standings: WVLStandRow[];
}

export interface WVLGraduatePool {
  save_key: string;
  dynasty: string;
  year: number;
  player_count: number;
}

export interface WVLRoster {
  club_key: string;
  club_name: string;
  graduates: WVLPlayer[];
  graduate_count: number;
}

export const wvlApi = {
  newSeason: () =>
    apiSend<{ league_id: string; session_id: string; status: WVLStatus }>("POST", "/api/wvl/new"),
  active: () =>
    apiGet<{ sessions: { league_id: string; session_id: string; status: WVLStatus }[] }>(
      "/api/wvl/active",
    ).then((r) => r.sessions),
  status: (id: string) => apiGet<WVLStatus>(`/api/wvl/${id}/status`),
  standings: (id: string) =>
    apiGet<{ standings: WVLStandRow[] }>(`/api/wvl/${id}/standings`).then((r) => r.standings),
  schedule: (id: string) =>
    apiGet<{ weeks: WVLWeek[] }>(`/api/wvl/${id}/schedule`).then((r) => r.weeks),
  players: (id: string) =>
    apiGet<{ players: WVLPlayer[] }>(`/api/wvl/${id}/players`).then((r) => r.players),
  player: (id: string, pid: string) =>
    apiGet<WVLPlayerDetail>(`/api/wvl/${id}/player/${encodeURIComponent(pid)}`),
  leaders: (id: string) => apiGet<WVLLeaders>(`/api/wvl/${id}/leaders`),
  history: (id: string) =>
    apiGet<{ history: WVLHistoryEntry[] }>(`/api/wvl/${id}/history`).then((r) => r.history),
  roster: (id: string, clubKey: string) =>
    apiGet<WVLRoster>(`/api/wvl/${id}/roster/${encodeURIComponent(clubKey)}`),
  graduatePools: () =>
    apiGet<{ pools: WVLGraduatePool[] }>("/api/wvl/graduate-pools").then((r) => r.pools),
  simWeek: (id: string) =>
    apiSend<{ result: any; status: WVLStatus }>("POST", `/api/wvl/${id}/sim-week`),
  simAll: (id: string) =>
    apiSend<{ result: any; status: WVLStatus }>("POST", `/api/wvl/${id}/sim-all`),
  advanceSeason: (id: string) =>
    apiSend<{ result: any; status: WVLStatus }>("POST", `/api/wvl/${id}/advance-season`),
  importGraduates: (id: string) =>
    apiSend<{ result: any; status: WVLStatus }>("POST", `/api/wvl/${id}/import-graduates`),
};
