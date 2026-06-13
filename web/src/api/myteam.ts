// My Team — pre-season roster builder (NIL / retention / portal) for a human team.
import { apiGet } from "./client";

export interface NilBudget {
  annual_budget: number;
  recruiting_pool: number;
  portal_pool: number;
  retention_pool: number;
  recruiting_remaining: number;
  portal_remaining: number;
  retention_remaining: number;
}

export interface MyTeamPlayer {
  player_id: string;
  name: string;
  position: string;
  overall: number;
  potential: number;
  year: string;
  speed?: number;
  power?: number;
  agility?: number;
}

export interface MyTeamDashboard {
  session_id: string;
  team_name: string;
  prestige: number;
  phase: string;
  roster: MyTeamPlayer[];
  roster_size: number;
  position_gaps: Record<string, number>;
  nil_budget: NilBudget;
  retention_risks_count: number;
  portal_size: number;
}

export interface RetentionRisk extends MyTeamPlayer {
  retained: boolean;
}

export interface PortalEntry extends MyTeamPlayer {
  global_index: number;
  my_bid: number | null;
}

export const myTeamApi = {
  dashboard: (sid: string) => apiGet<MyTeamDashboard>(`/sessions/${sid}/my-team`),
  retention: (sid: string) =>
    apiGet<{ risks: RetentionRisk[]; retention_remaining: number; retained_count: number }>(
      `/sessions/${sid}/my-team/retention`,
    ),
  portal: (sid: string) =>
    apiGet<{
      available: PortalEntry[];
      committed: PortalEntry[];
      round: number;
      max_rounds: number;
      transfers_remaining: number;
      portal_remaining: number;
    }>(`/sessions/${sid}/my-team/portal`),
};
