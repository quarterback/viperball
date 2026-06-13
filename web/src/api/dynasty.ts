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
