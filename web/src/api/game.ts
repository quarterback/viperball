// Single one-off game simulator (POST /simulate).
import { apiGet, apiSend } from "./client";
import type { FullResult } from "./season";

export interface SimulateBody {
  home: string;
  away: string;
  seed?: number | null;
  styles?: Record<string, { offense_style: string; defense_style: string; st_scheme: string }>;
  weather?: string;
}

// /simulate returns the same shape as a game's full_result, plus a couple extras.
export interface GameSimResult extends FullResult {
  weather_label?: string;
  seed?: number;
  home_style?: string;
  away_style?: string;
}

export const gameApi = {
  simulate: (body: SimulateBody) => apiSend<GameSimResult>("POST", "/simulate", body),
  weather: () =>
    apiGet<{ conditions: { key: string; label: string }[] }>("/weather-conditions").then(
      (r) => r.conditions,
    ),
};
