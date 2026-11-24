#!/usr/bin/env python3
"""ST-01/ST-02 paired full-engine special-teams study.

Run after merging the parallel PEN-01/INJ-01 branch, then compare outcomes:
  PYTHONHASHSEED=0 python scripts/benchmark_special_teams.py --games 20

The baseline and two STC profiles keep teams, weather, and game seeds fixed
within a scheme. Unlike a fast sim, this exercises full plays and player stats.
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
from engine.game_engine import ViperballEngine, ST_SCHEMES, load_team_from_json
from benchmark_defensive_coaches import coach


def st_coach(name, field_position, returns):
    c = coach("st-" + name, "stc")
    c.tactical_profile["special_teams"] = {
        "field_position_bias": field_position,
        "return_aggression": returns,
    }
    return c


def run(games, seed):
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    if len(paths) < 2:
        raise RuntimeError("Need at least two program files")
    original = [load_team_from_json(str(p), fresh=False) for p in (paths[0], paths[len(paths)//2])]
    profiles = {
        "no_stc": None,
        "territory": st_coach("territory", 0.5, -0.5),
        "attack": st_coach("attack", -0.5, 0.5),
    }
    results = {}
    for scheme in sorted(ST_SCHEMES):
        for weather in ("clear", "rain"):
            for profile, stc in profiles.items():
                totals = Counter()
                yards, scores = [], []
                for n in range(games):
                    random.seed(seed + n)
                    home, away = deepcopy(original)
                    home.st_scheme = scheme
                    away.st_scheme = "aces"
                    staff = {"stc": deepcopy(stc)} if stc is not None else None
                    result = ViperballEngine(
                        home, away, seed=seed + n, neutral_site=True, weather=weather,
                        home_coaching=staff,
                    ).simulate_game()
                    scores.append(result["final_score"]["home"]["score"])
                    for p in result["play_by_play"]:
                        typ = str(p.get("play_type", ""))
                        outcome = str(p.get("result", ""))
                        text = str(p.get("description", ""))
                        if typ in ("punt", "fake_punt", "drop_kick", "place_kick"):
                            totals["kicking_events"] += 1
                            totals[typ] += 1
                            totals["blocked"] += int("BLOCKED" in text)
                            totals["muffed"] += int("MUFFED" in text)
                            totals["return_td"] += int("RETURN" in text and "TOUCHDOWN" in text)
                            totals["pindown"] += int("PINDOWN" in text)
                            totals["bell"] += int("(+½)" in text)
                        if typ == "punt" and "returns " in text:
                            totals["punt_returns"] += 1
                    if result["final_score"]["home"]["score"] < 0:
                        raise AssertionError("Negative final score")
                key = f"{scheme}/{weather}/{profile}"
                results[key] = {
                    "games": games,
                    "scores": scores,
                    "mean_points": round(sum(scores) / games, 3),
                    "events": dict(totals),
                }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261124)
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")
    print(json.dumps({"seed": args.seed, "games_per_case": args.games,
                      "results": run(args.games, args.seed)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
