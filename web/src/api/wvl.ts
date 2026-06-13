// WVL — multi-tier (4-tier) league with promotion/relegation.
import { apiGet, apiSend } from "./client";

export interface WVLTierInfo {
  tier: number;
  name: string;
  team_count: number;
  total_weeks: number;
}
export interface WVLStatus {
  phase: string;
  current_week: number;
  tiers: WVLTierInfo[];
}

export interface WVLStandRow {
  team_key?: string;
  team_name: string;
  wins: number;
  losses: number;
  ties?: number;
  pf: number;
  pa: number;
  diff: number;
  pct?: number;
  streak?: string;
  last_5?: string;
  position?: number;
  zone?: string; // "promotion" | "relegation" | "playoff" | "safe"
}
export interface WVLTierStandings {
  tier: number;
  name: string;
  standings: {
    divisions: Record<string, WVLStandRow[]>;
    week?: number;
    total_weeks?: number;
  };
}

export const wvlApi = {
  newSeason: () => apiSend<{ session_id: string; status: WVLStatus }>("POST", "/api/wvl/new"),
  active: () =>
    apiGet<{ sessions: { session_id: string; status: WVLStatus }[] }>("/api/wvl/active").then(
      (r) => r.sessions,
    ),
  status: (sid: string) => apiGet<WVLStatus>(`/api/wvl/${sid}/status`),
  standings: (sid: string) =>
    apiGet<{ tiers: WVLTierStandings[] }>(`/api/wvl/${sid}/standings`).then((r) => r.tiers),
  simWeek: (sid: string) => apiSend<{ status: WVLStatus }>("POST", `/api/wvl/${sid}/sim-week`),
  simAll: (sid: string) => apiSend<{ status: WVLStatus }>("POST", `/api/wvl/${sid}/sim-all`),
};

export const ZONE_COLOR: Record<string, string> = {
  promotion: "teal",
  playoff: "indigo",
  relegation: "red",
  safe: "gray",
};
