// Saves / Experiments API.
//
// This is the SPA's front door. The Phase 0 backend will expose /api/saves*;
// until then this module falls back to an in-browser MOCK store so the Saves
// Library is fully clickable today. When the real endpoints ship, delete the
// mock branch — the type contract below IS the contract the backend must meet.

import { apiGet, apiSend, ApiError } from "./client";

export type SaveMode = "college" | "dynasty" | "pro" | "wvl" | "fiv";

export interface SaveSummary {
  id: string;
  name: string;
  mode: SaveMode;
  /** Human label of the league/teams under test. */
  teams: string;
  /** e.g. "Week 8 / 12" or "Year 3 — Offseason". */
  progress: string;
  /** RNG seed for the run, when fixed — central to reproducible experiments. */
  seed: number | null;
  tags: string[];
  notes: string;
  createdAt: string; // ISO
  lastSimmedAt: string; // ISO
}

// ─── Real endpoints (Phase 0) ────────────────────────────────────
const USE_MOCK_FALLBACK = true;

export async function listSaves(): Promise<SaveSummary[]> {
  try {
    return await apiGet<SaveSummary[]>("/api/saves");
  } catch (e) {
    if (USE_MOCK_FALLBACK && e instanceof ApiError) return mock.list();
    throw e;
  }
}

export async function forkSave(id: string): Promise<SaveSummary> {
  try {
    return await apiSend<SaveSummary>("POST", `/api/saves/${id}/fork`);
  } catch (e) {
    if (USE_MOCK_FALLBACK && e instanceof ApiError) return mock.fork(id);
    throw e;
  }
}

export async function renameSave(id: string, name: string): Promise<SaveSummary> {
  try {
    return await apiSend<SaveSummary>("PATCH", `/api/saves/${id}`, { name });
  } catch (e) {
    if (USE_MOCK_FALLBACK && e instanceof ApiError) return mock.patch(id, { name });
    throw e;
  }
}

export async function deleteSave(id: string): Promise<void> {
  try {
    await apiSend<void>("DELETE", `/api/saves/${id}`);
  } catch (e) {
    if (USE_MOCK_FALLBACK && e instanceof ApiError) return mock.remove(id);
    throw e;
  }
}

// ─── Mock store (delete once Phase 0 lands) ──────────────────────
const KEY = "vb_mock_saves";

const seed: SaveSummary[] = [
  {
    id: "s1",
    name: "Baseline — default rules",
    mode: "college",
    teams: "Full CVL (102 teams)",
    progress: "Week 12 / 12 — Final",
    seed: 1001,
    tags: ["baseline"],
    notes: "Control run for rules tweaks.",
    createdAt: "2026-06-01T10:00:00Z",
    lastSimmedAt: "2026-06-01T10:42:00Z",
  },
  {
    id: "s2",
    name: "4th-down aggression +20%",
    mode: "college",
    teams: "Full CVL (102 teams)",
    progress: "Week 8 / 12",
    seed: 1001,
    tags: ["experiment", "4th-down"],
    notes: "Forked from baseline, same seed.",
    createdAt: "2026-06-03T14:00:00Z",
    lastSimmedAt: "2026-06-12T22:15:00Z",
  },
  {
    id: "s3",
    name: "Gonzaga dynasty",
    mode: "dynasty",
    teams: "Gonzaga",
    progress: "Year 4 — Offseason",
    seed: null,
    tags: ["dynasty"],
    notes: "",
    createdAt: "2026-05-20T09:00:00Z",
    lastSimmedAt: "2026-06-10T18:30:00Z",
  },
];

const mock = {
  read(): SaveSummary[] {
    const raw = localStorage.getItem(KEY);
    if (!raw) {
      localStorage.setItem(KEY, JSON.stringify(seed));
      return seed;
    }
    return JSON.parse(raw) as SaveSummary[];
  },
  write(list: SaveSummary[]) {
    localStorage.setItem(KEY, JSON.stringify(list));
  },
  async list() {
    return this.read();
  },
  async fork(id: string) {
    const list = this.read();
    const src = list.find((s) => s.id === id);
    if (!src) throw new Error("not found");
    const now = new Date().toISOString();
    const copy: SaveSummary = {
      ...src,
      id: `s${Date.now()}`,
      name: `${src.name} (fork)`,
      createdAt: now,
      lastSimmedAt: now,
    };
    this.write([copy, ...list]);
    return copy;
  },
  async patch(id: string, patch: Partial<SaveSummary>) {
    const list = this.read();
    const next = list.map((s) => (s.id === id ? { ...s, ...patch } : s));
    this.write(next);
    return next.find((s) => s.id === id)!;
  },
  async remove(id: string) {
    this.write(this.read().filter((s) => s.id !== id));
  },
};
