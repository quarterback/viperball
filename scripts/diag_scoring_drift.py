"""Scoring drift diagnostic: matched games with config overrides.

Usage: python scripts/diag_scoring_drift.py ROOT GAMES SEED [config_key=json ...]
ROOT is a checkout (use a git worktree to measure an older commit).
"""
import collections, json, os, random, statistics, sys
root = sys.argv[1]; games = int(sys.argv[2]); seed = int(sys.argv[3])
sys.path.insert(0, root); sys.path.insert(0, os.path.join(root, "scripts"))
os.chdir(root)
import benchmark_engine as B
from engine.game_engine import V2_ENGINE_CONFIG, ViperballEngine
for kv in sys.argv[4:]:
    k, v = kv.split("=")
    V2_ENGINE_CONFIG[k] = json.loads(v)
teams, styles, pairs = B.build_matchups(games, seed)
S = collections.defaultdict(list); drv = collections.Counter(); ndrv = 0; dyards = []
pt = collections.Counter(); ptyds = collections.defaultdict(list)
for i, (h, a) in enumerate(pairs):
    r = ViperballEngine(teams[h], teams[a], seed=seed + i, style_overrides=B.overrides(styles, h, a)).simulate_game()
    for side in ("home", "away"):
        s = r["stats"][side]
        for k in ("touchdowns", "rushing_touchdowns", "kick_pass_tds", "drop_kicks_made", "drop_kicks_attempted",
                  "place_kicks_made", "fumbles_lost", "kick_pass_interceptions", "lateral_interceptions", "muffs",
                  "turnovers_on_downs", "penalties", "penalty_yards", "total_plays", "total_yards", "punts",
                  "kick_passes_attempted", "kick_passes_completed", "rushing_yards", "rushing_carries",
                  "int_return_tds", "punt_return_tds", "kick_return_tds", "missed_dk_return_tds", "bells", "pindowns"):
            S[k].append(s.get(k, 0) or 0)
        S["points"].append(r["final_score"][side]["score"])
    for d in r.get("drive_summary", []):
        ndrv += 1; drv[d.get("result")] += 1; dyards.append(d.get("yards") or 0)
    for p in r["play_by_play"]:
        pt[p.get("play_type")] += 1; ptyds[p.get("play_type")].append(p.get("yards") or 0)
        ev = p.get("rush_event") or {}
        if isinstance(ev, dict) and ev:
            S["_rush"].append(1); S["_sack"].append(1 if ev.get("outcome") == "sack" else 0); S["_pressure"].append(1 if ev.get("pressure") else 0)
out = {k: round(statistics.mean(v), 3) for k, v in S.items() if not k.startswith("_")}
if S["_rush"]:
    out["rush_events_pg"] = round(len(S["_rush"]) / games / 2, 2)
    out["sack_rate"] = round(statistics.mean(S["_sack"]), 3); out["pressure_rate"] = round(statistics.mean(S["_pressure"]), 3)
out["kp_comp"] = round(sum(S["kick_passes_completed"]) / max(1, sum(S["kick_passes_attempted"])), 3)
out["ypc"] = round(sum(S["rushing_yards"]) / max(1, sum(S["rushing_carries"])), 2)
out["ypp"] = round(sum(S["total_yards"]) / max(1, sum(S["total_plays"])), 2)
out["drives_pg"] = round(ndrv / games / 2, 2); out["drive_yards"] = round(statistics.mean(dyards), 1)
out["drive_results"] = {k: round(v / ndrv, 3) for k, v in drv.most_common(14)}
out["play_types"] = {k: [round(v / games / 2, 1), round(statistics.mean(ptyds[k]), 2)] for k, v in pt.most_common(12)}
print(json.dumps(out))
