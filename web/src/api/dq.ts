// DraftyQueenz — a betting + daily-fantasy overlay on a running sim session.
// Redesigned: booster/donation mechanic dropped (it no longer affects the sim).
import { apiGet, apiSend } from "./client";

export interface DQStatus {
  bankroll: number;
  peak_bankroll: number;
  total_earned: number;
  total_wagered: number;
  roi: number;
  pick_accuracy: number;
  fantasy_top3_rate: number;
}

export interface TeamCtx {
  name: string;
  record: string;
  rank?: number;
  prestige?: number;
  star?: string;
  star_ovr?: number;
}
export interface GameOdds {
  game_idx: number;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  spread: number;
  over_under: number;
  home_moneyline: number;
  away_moneyline: number;
  home_ml_display: string;
  away_ml_display: string;
  home_ctx?: TeamCtx;
  away_ctx?: TeamCtx;
}

export interface PickRow {
  pick_type: string;
  matchup: string;
  selection: string;
  amount: number;
  payout: number;
  result: string;
}
export interface ParlayRow {
  legs: PickRow[];
  amount: number;
  multiplier: number;
  payout: number;
  result: string;
  potential_payout: number;
}

export interface FantasyPlayer {
  tag: string;
  name: string;
  team: string;
  position: string;
  position_name: string;
  overall: number;
  salary: number;
  projected: number;
  depth: string;
}
export interface RosterEntry {
  tag: string;
  name: string;
  team: string;
  position: string;
  slot_label: string;
  salary: number;
  points: number;
}
export interface FantasyRoster {
  manager: string;
  entries: Record<string, RosterEntry | null>;
  total_salary: number;
  total_points: number;
}

export type PickType = "winner" | "spread" | "over_under";
export interface ParlayLeg {
  pick_type: PickType;
  game_idx: number;
  selection: string;
}

export const dqApi = {
  status: (sid: string) => apiGet<DQStatus>(`/sessions/${sid}/dq/status`),
  odds: (sid: string, week: number) =>
    apiGet<{ week: number; odds: GameOdds[] }>(`/sessions/${sid}/dq/odds/${week}`),
  contest: (sid: string, week: number) =>
    apiGet<{ picks: PickRow[]; parlays: ParlayRow[]; resolved: boolean }>(
      `/sessions/${sid}/dq/contest/${week}`,
    ),
  pick: (sid: string, week: number, body: { pick_type: PickType; game_idx: number; selection: string; amount: number }) =>
    apiSend<{ bankroll: number }>("POST", `/sessions/${sid}/dq/pick/${week}`, body),
  parlay: (sid: string, week: number, legs: ParlayLeg[], amount: number) =>
    apiSend<{ bankroll: number }>("POST", `/sessions/${sid}/dq/parlay/${week}`, { legs, amount }),
  resolve: (sid: string, week: number) =>
    apiSend<{ prediction_earnings: number; fantasy_earnings: number; jackpot_bonus: number; bankroll: number; fantasy_rank?: number }>(
      "POST",
      `/sessions/${sid}/dq/resolve/${week}`,
    ),

  // Daily fantasy
  enterFantasy: (sid: string, week: number) =>
    apiSend<{ entered: boolean; bankroll: number; entry_fee: number }>(
      "POST",
      `/sessions/${sid}/dq/fantasy/enter/${week}`,
    ),
  pool: (sid: string, week: number) =>
    apiGet<{ pool: FantasyPlayer[]; salary_cap: number }>(`/sessions/${sid}/dq/fantasy/pool/${week}`),
  roster: (sid: string, week: number) =>
    apiGet<{ entered: boolean; roster: FantasyRoster | null; salary_remaining: number }>(
      `/sessions/${sid}/dq/fantasy/roster/${week}`,
    ),
  setSlot: (sid: string, week: number, slot: string, player_tag: string, team_name: string) =>
    apiSend<{ roster: FantasyRoster; salary_remaining: number }>(
      "POST",
      `/sessions/${sid}/dq/fantasy/set-slot/${week}`,
      { slot, player_tag, team_name },
    ),
  clearSlot: (sid: string, week: number, slot: string) =>
    apiSend<{ roster: FantasyRoster; salary_remaining: number }>(
      "DELETE",
      `/sessions/${sid}/dq/fantasy/clear-slot/${week}/${slot}`,
    ),

  history: (sid: string) =>
    apiGet<{ picks: (PickRow & { week: number; resolved: boolean })[]; total_won: number; total_lost: number; net: number }>(
      `/sessions/${sid}/dq/history`,
    ),
};

export const FANTASY_SLOTS = ["VP", "BALL1", "BALL2", "KP", "FLEX"];
export const SLOT_LABEL: Record<string, string> = {
  VP: "Viper",
  BALL1: "Ball carrier 1",
  BALL2: "Ball carrier 2",
  KP: "Keeper",
  FLEX: "Flex",
};
