#!/usr/bin/env python3
"""BOX-01 full-engine accounting smoke, based on finalized game results.

Run: PYTHONHASHSEED=0 python scripts/benchmark_boxscore_reconciliation.py --games 8
No artificial score correction: mismatches raise and print the failed seed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.box_score_ledger import scoring_ledger
from engine.game_engine import ViperballEngine, load_team_from_json


def run(games=8, seed=20261124):
    team_files = sorted((ROOT / "data" / "teams").glob("*.json"))
    if len(team_files) < 4:
        raise RuntimeError("Four team files required")
    teams = [load_team_from_json(str(p), fresh=False) for p in
             (team_files[0], team_files[1], team_files[len(team_files)//2],
              team_files[len(team_files)//2 + 1])]
    summary = Counter()
    failures = []
    for i in range(games):
        random.seed(seed + i)
        home, away = deepcopy(teams[(i % 2) * 2]), deepcopy(teams[(i % 2) * 2 + 1])
        game = ViperballEngine(home, away, seed=seed + i,
                              neutral_site=True,
                              weather=("clear", "rain")[i % 2]).simulate_game()
        final = {side: game["final_score"][side]["score"] for side in ("home", "away")}
        ledger = scoring_ledger(game["play_by_play"], final)
        for side in ("home", "away"):
            official = game["stats"][side]
            profile = official["viperball_metrics"]["scoring_profile"]
            players = game["player_stats"][side]
            if ledger is None:
                failures.append((i, side, "missing play score snapshots"))
                continue
            row = ledger[side]
            summary["games_sides"] += 1
            summary["points_x2"] += round(float(final[side]) * 2)
            summary["unclassified_x2"] += round(row["points"]["other"] * 2)
            summary["scoring_events"] += sum(row["counts"].values())
            if not row["score_consistent"]:
                prior = 0.0
                regressions = []
                for idx, play in enumerate(game["play_by_play"]):
                    score = play[side + "_score"]
                    if score < prior:
                        regressions.append({
                            "index": idx, "before": prior, "after": score,
                            "result": play.get("result"),
                            "play_type": play.get("play_type"),
                            "possession": play.get("possession"),
                            "snap_possession": play.get("snap_possession"),
                            "description": str(play.get("description", ""))[:100],
                        })
                    prior = score
                failures.append((i, side, "score ledger",
                                 row["unrecorded_points"], regressions[:3],
                                 "reversals", len(regressions)))
            if sum(row["points"].values()) != row["score_from_plays"]:
                failures.append((i, side, "method points not equal scoring events"))
            if profile["total_pts"] != final[side]:
                failures.append((i, side, "scoring profile differs from final score"))
            for key, player_key in (
                ("kick_passes_attempted", "kick_passes_thrown"),
                ("kick_passes_completed", "kick_passes_completed"),
                ("kick_pass_interceptions", "kick_pass_interceptions_thrown"),
            ):
                value = sum(p.get(player_key, 0) for p in players)
                if official[key] != value:
                    failures.append((i, side, key, official[key], value))
            if official["kick_passes_completed"] > official["kick_passes_attempted"]:
                failures.append((i, side, "impossible completion count"))
    return dict(summary), failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261124)
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")
    summary, failures = run(args.games, args.seed)
    print(json.dumps({"seed": args.seed, "games": args.games,
                      "summary": summary, "failures": failures}, indent=2))
    if failures:
        raise SystemExit(f"{len(failures)} box-score reconciliation failures")


if __name__ == "__main__":
    main()
