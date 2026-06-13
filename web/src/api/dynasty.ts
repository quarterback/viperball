// Dynasty API — saved multi-year careers, loaded into a session to browse.
import { apiGet, apiSend } from "./client";

export interface DynastySave {
  save_key: string;
  dynasty_name: string;
  coach_name: string;
  coach_team: string;
  current_year: number;
  seasons_played: number;
}

export interface DynastyCoach {
  name: string;
  team: string;
  career_wins: number;
  career_losses: number;
  win_percentage: number;
  championships: number;
  playoff_appearances: number;
  conference_titles: number;
  bowl_wins: number;
  years_coached: number;
}

export interface DynastyStatus {
  dynasty_name: string;
  current_year: number;
  coach: DynastyCoach;
  team_count: number;
  seasons_played: number;
  phase: string;
  games_per_team?: number;
  playoff_size?: number;
  bowl_count?: number;
}

export interface TeamHistory {
  team_name: string;
  total_wins: number;
  total_losses: number;
  total_championships: number;
  total_playoff_appearances: number;
  win_percentage: number;
  best_season_wins: number;
  best_season_year: number;
  championship_years: number[];
}

export interface SeasonAwards {
  year: number;
  champion: string;
  coach_of_year: string;
  highest_scoring: string;
  best_defense: string;
}

export const dynastyApi = {
  list: () =>
    apiGet<{ dynasties: DynastySave[] }>("/dynasties").then((r) => r.dynasties),

  // Create a session and load the saved dynasty into it; return the session id.
  open: async (saveKey: string): Promise<string> => {
    const { session_id } = await apiSend<{ session_id: string }>("POST", "/sessions");
    await apiSend(
      "POST",
      `/sessions/${session_id}/dynasty/load?save_key=${encodeURIComponent(saveKey)}`,
    );
    return session_id;
  },

  status: (sid: string) => apiGet<DynastyStatus>(`/sessions/${sid}/dynasty/status`),

  teamHistories: (sid: string) =>
    apiGet<{ team_histories: Record<string, TeamHistory> }>(
      `/sessions/${sid}/dynasty/team-histories`,
    ).then((r) => Object.values(r.team_histories)),

  awards: (sid: string) =>
    apiGet<{ awards_history: Record<string, SeasonAwards> }>(
      `/sessions/${sid}/dynasty/awards`,
    ).then((r) =>
      Object.entries(r.awards_history)
        .map(([year, a]) => ({ ...a, year: Number(year) }))
        .sort((a, b) => b.year - a.year),
    ),

  recordBook: (sid: string) =>
    apiGet<{ record_book: Record<string, number> }>(
      `/sessions/${sid}/dynasty/record-book`,
    ).then((r) => r.record_book),
};

// ─── Program archetypes (for dynasty creation) ───────────────────
export interface ProgramArchetype {
  label: string;
  description: string;
  prestige_range?: [number, number];
}

export interface CreateDynastyConfig {
  dynasty_name: string;
  coach_name: string;
  coach_team: string;
  starting_year: number;
  program_archetype: string | null;
  history_years: number;
  games_per_team: number;
  playoff_size: number;
  bowl_count: number;
  num_conferences: number;
  conferences: Record<string, string[]>;
}

export interface StartSeasonConfig {
  games_per_team: number;
  playoff_size: number;
  bowl_count: number;
  offense_style: string;
  defense_style: string;
  st_scheme: string;
  ai_seed: number | null;
}

export interface OffseasonStatus {
  phase: "nil" | "portal" | "recruiting" | "ready" | string;
  nil_budget?: number;
  nil_allocated?: number;
  portal_available?: number;
  recruit_pool_size?: number;
  retention_risks_count?: number;
  transfers_remaining?: number;
}

export const dynastyCreateApi = {
  programArchetypes: () =>
    apiGet<{ archetypes: Record<string, ProgramArchetype> }>("/program-archetypes").then(
      (r) => r.archetypes,
    ),

  // Create a session, create the dynasty in it, return the session id.
  create: async (cfg: CreateDynastyConfig): Promise<string> => {
    const { session_id } = await apiSend<{ session_id: string }>("POST", "/sessions");
    await apiSend("POST", `/sessions/${session_id}/dynasty`, cfg);
    return session_id;
  },

  startSeason: (sid: string, cfg: StartSeasonConfig) =>
    apiSend("POST", `/sessions/${sid}/dynasty/start-season`, cfg),

  advance: (sid: string) => apiSend("POST", `/sessions/${sid}/dynasty/advance`),
};

// ─── Offseason loop ──────────────────────────────────────────────
export interface PortalEntry {
  player_name: string;
  position: string;
  position_full: string;
  overall: number;
  year: string;
  origin_team: string;
  potential: number;
  offers_count: number;
  global_index: number;
}

export interface Recruit {
  name: string;
  position: string;
  position_full: string;
  stars: number;
  region: string;
  hometown: string;
  pool_index: number;
  scout_level: "none" | "basic" | "full" | string;
  true_overall?: number;
}

export const offseasonApi = {
  status: (sid: string) =>
    apiGet<OffseasonStatus>(`/sessions/${sid}/offseason/status`).catch(() => null),

  nil: (sid: string) =>
    apiGet<{
      annual_budget: number;
      recruiting_pool: number;
      portal_pool: number;
      retention_pool: number;
    }>(`/sessions/${sid}/offseason/nil`),
  allocateNil: (sid: string, recruiting_pool: number, portal_pool: number, retention_pool: number) =>
    apiSend("POST", `/sessions/${sid}/offseason/nil/allocate`, {
      recruiting_pool,
      portal_pool,
      retention_pool,
    }),

  portal: (sid: string) =>
    apiGet<{ entries: PortalEntry[]; total_available: number }>(
      `/sessions/${sid}/offseason/portal`,
    ),
  portalOffer: (sid: string, entry_index: number, nil_amount: number) =>
    apiSend("POST", `/sessions/${sid}/offseason/portal/offer`, { entry_index, nil_amount }),
  portalCommit: (sid: string, entry_index: number) =>
    apiSend("POST", `/sessions/${sid}/offseason/portal/commit`, { entry_index }),
  portalResolve: (sid: string) => apiSend("POST", `/sessions/${sid}/offseason/portal/resolve`),

  recruiting: (sid: string) =>
    apiGet<{
      recruits: Recruit[];
      board: { scholarships_available: number; scouting_points: number; max_offers: number };
    }>(`/sessions/${sid}/offseason/recruiting`),
  scout: (sid: string, recruit_index: number, level: "basic" | "full") =>
    apiSend("POST", `/sessions/${sid}/offseason/recruiting/scout`, { recruit_index, level }),
  recruitOffer: (sid: string, recruit_index: number) =>
    apiSend("POST", `/sessions/${sid}/offseason/recruiting/offer`, { recruit_index }),
  recruitResolve: (sid: string) => apiSend("POST", `/sessions/${sid}/offseason/recruiting/resolve`),

  complete: (sid: string) => apiSend("POST", `/sessions/${sid}/offseason/complete`),
};
