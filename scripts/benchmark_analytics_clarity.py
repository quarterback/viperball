#!/usr/bin/env python3
"""Focused scoring-value, DTW-band and EPA-scope full-engine audit.

Reuses the existing integration CI rather than introducing a new workflow.
Run: PYTHONHASHSEED=0 python scripts/benchmark_analytics_clarity.py --games 12
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.game_engine import ViperballEngine, load_team_from_json
from engine.dtw import calculate_game_dtw
from engine.epa import EPA_SCOPE


def run(games=12, seed=20261124):
    files = sorted((ROOT / "data" / "teams").glob("*.json"))
    teams = [load_team_from_json(str(f), fresh=False) for f in
             (files[0], files[1], files[len(files)//2], files[len(files)//2+1])]
    counts = Counter()
    failures = []
    for n in range(games):
        home, away = (deepcopy(teams[n%4]), deepcopy(teams[(n+1)%4]))
        random.seed(seed + n)
        result = ViperballEngine(home, away, seed=seed+n,
                                 neutral_site=True,
                                 weather="rain" if n%2 else "clear").simulate_game()
        dtw = calculate_game_dtw(
            result,
            result["stats"]["home"].get("viperball_metrics"),
            result["stats"]["away"].get("viperball_metrics"))
        comps = dtw["component_edges"]
        if abs(sum(comps[k] for k in (
                "raw_performance", "delta_context", "turnover_bonus_conversion"))
                - comps["final_edge"]) > 0.0002:
            failures.append([n, "component sum", comps])
        if max(dtw["home_dtw"], dtw["away_dtw"]) < .55 and (
                dtw["upset"] or dtw["deserved_winner"] != "toss-up"):
            failures.append([n, "false close upset", dtw])
        for side in ("home", "away"):
            st = result["stats"][side]
            dye = st["dye"]
            buckets = [dye[x] for x in ("penalty_kill", "power_play", "neutral")]
            side_drives = [d for d in result["drive_summary"] if d.get("team") == side]
            if sum(b["count"] for b in buckets) != len(side_drives):
                failures.append([n, side, "bucket drive count"])
            if any(b["touchdowns"] + b["kicks"] != b["scores"] for b in buckets):
                failures.append([n, side, "scoring incidence", buckets])
            points = sum(b["points"] for b in buckets)
            official = result["final_score"][side]["score"]
            if points > official + .01 or points < 0:
                failures.append([n, side, "offensive drive points exceed final",points,official])
            if any(b["count"] and abs(
                    b["points_per_drive"] - b["points"]/b["count"]) > .011 for b in buckets):
                failures.append([n, side, "points per drive",buckets])
            if st["epa"].get("scope") != EPA_SCOPE:
                failures.append([n, side, "EPA scope metadata missing"])
            counts["team_games"] += 1
            counts["drive_points_x2"] += round(points*2)
            counts["offensive_touchdowns"] += sum(b["touchdowns"] for b in buckets)
            counts["scoring_kicks"] += sum(b["kicks"] for b in buckets)
            counts["power_play_drives"] += dye["power_play"]["count"]
    # A 50/50 adjusted edge cannot be an upset even if one team won.
    level = calculate_game_dtw({
        "final_score":{"home":{"score":50,"team":"Home"},
                       "away":{"score":49,"team":"Away"}},
        "stats":{"home":{}, "away":{}},
    })
    if level["upset"] or level["deserved_winner"] != "toss-up":
        failures.append(["equal signals labeled upset",level])
    return dict(counts), failures


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--games",type=int,default=12)
    p.add_argument("--seed",type=int,default=20261124)
    args=p.parse_args()
    counts,failures=run(args.games,args.seed)
    print(json.dumps({"seed":args.seed,"games":args.games,
                      "summary":counts,"failures":failures},indent=2))
    if failures:
        raise SystemExit(f"{len(failures)} analytics checks failed")


if __name__=="__main__":
    main()
