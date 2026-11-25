#!/usr/bin/env python3
"""Matched on/off study of Delta Yards restarts.

Each matchup is simulated twice with the same rosters, seed and weather,
once with score-proportional restarts and once with every post-score
drive starting at the 20. Run:
  PYTHONHASHSEED=0 python scripts/study_delta_yards.py --games 2000 --out reports/delta_study
"""
import argparse, json, random, statistics, sys
from copy import deepcopy
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.game_engine import ViperballEngine, V2_ENGINE_CONFIG, load_team_from_json

TEAMS = {}


def strength(team):
    top = sorted((p.overall for p in team.players), reverse=True)[:22]
    return statistics.mean(top)


def load_pool():
    files = sorted((ROOT / "data" / "teams").glob("*.json"))
    for f in files:
        t = load_team_from_json(str(f), fresh=False)
        TEAMS[f.stem] = (t, strength(t))


def lead_changes(plays):
    leader, changes = 0, 0
    for p in plays:
        d = (p.get("home_score") or 0) - (p.get("away_score") or 0)
        s = (d > 0) - (d < 0)
        if s and leader and s != leader:
            changes += 1
        if s:
            leader = s
    return changes


def play(job):
    n, home_id, away_id, seed, delta_on = job
    V2_ENGINE_CONFIG["delta_restarts_enabled"] = delta_on
    h, hs = TEAMS[home_id]
    a, as_ = TEAMS[away_id]
    random.seed(seed)
    g = ViperballEngine(deepcopy(h), deepcopy(a), seed=seed, neutral_site=True,
                        weather="rain" if n % 3 == 1 else "clear").simulate_game()
    plays = g["play_by_play"]
    hf, af = g["final_score"]["home"]["score"], g["final_score"]["away"]["score"]
    q4 = next((p for p in plays if p["quarter"] >= 4), plays[-1])
    max_def = {"home": 0, "away": 0}
    for p in plays:
        d = (p.get("home_score") or 0) - (p.get("away_score") or 0)
        max_def["home"] = max(max_def["home"], -d)
        max_def["away"] = max(max_def["away"], d)
    drives = []
    for d in g["drive_summary"]:
        drives.append({"team": d["team"], "start": d.get("start_yard_line"),
                       "origin": d.get("possession_origin"), "cost": d.get("delta_cost"),
                       "pts": d.get("offensive_points"), "q": d.get("quarter")})
    return {"n": n, "delta_on": delta_on, "home": home_id, "away": away_id,
            "hs": hs, "as": as_, "h": hf, "a": af,
            "ot": any(p["quarter"] > 4 for p in plays),
            "q4_diff": (q4.get("home_score") or 0) - (q4.get("away_score") or 0),
            "lead_changes": lead_changes(plays), "max_def": max_def,
            "delta_yards": {s: g["stats"][s].get("delta_yards", 0) for s in ("home", "away")},
            "drives": drives}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="reports/delta_study")
    args = ap.parse_args()
    load_pool()
    ids = sorted(TEAMS)
    rng = random.Random(args.seed)
    jobs = []
    for n in range(args.games):
        h, a = rng.sample(ids, 2)
        for on in (True, False):
            jobs.append((n, h, a, args.seed + n, on))
    with Pool(args.workers, initializer=load_pool) as pool:
        rows = pool.map(play, jobs, chunksize=8)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "games.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    print(len(rows), "games written to", out)


if __name__ == "__main__":
    main()
