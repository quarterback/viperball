#!/usr/bin/env python3
"""Matched CCH-05 games; compare installed package on/off, not score targets."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import random
import statistics
from benchmark_defensive_coaches import ROOT, coach, dc_variant
from engine.game_engine import V2_ENGINE_CONFIG, ViperballEngine, load_team_from_json
from engine.team_installation import new_installation

def run(games, seed):
    random.seed(seed)
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    offense, defense = [load_team_from_json(str(p), fresh=False) for p in paths[:2]]
    staff = {"head_coach": coach("shared-hc", "head_coach"), "dc": dc_variant("run_wall")}
    cases = [
        ("fortress", "fortress_short_yardage_wall", "ground_pound"),
        ("lockdown", "lockdown_long_yardage_bracket", "boot_raid"),
        ("blitz_pack", "blitz_short_yardage_pressure", "ground_pound"),
    ]
    out = {}
    old = V2_ENGINE_CONFIG.get("defensive_packages_enabled", True)
    try:
        for scheme, package, attack in cases:
            rec = new_installation(defense.name, staff, "boot_raid", scheme, 2026)
            rec["defense"].update(familiarity=1.0, family_familiarity=1.0,
                packages=[{"package_id": package, "familiarity": 1.0}])
            for enabled in (False, True):
                V2_ENGINE_CONFIG["defensive_packages_enabled"] = enabled
                counts = Counter()
                groups = defaultdict(Counter)
                scores = []
                for n in range(games):
                    a, b = deepcopy(offense), deepcopy(defense)
                    b.installation = deepcopy(rec)
                    game = ViperballEngine(a, b, seed=seed+n, neutral_site=True,
                        weather="clear", away_coaching=deepcopy(staff),
                        style_overrides={a.name: attack, b.name+"_defense": scheme}).simulate_game()
                    scores.append(game["final_score"]["home"]["score"])
                    dc = game["defensive_coach_tactics"]["away"]
                    counts["calls"] += dc["calls"]
                    counts["eligible"] += dc["packages"]["eligible"].get(package, 0)
                    counts["selected"] += dc["packages"]["selected"].get(package, 0)
                    counts["blitz"] += dc["blitz_calls"]
                    for p in game["play_by_play"]:
                        call = p.get("defensive_call") or {}
                        if call.get("defending_side") != "away":
                            continue
                        y = p.get("yards")
                        if y is None:
                            continue
                        # Compare within the same down/distance and family;
                        # selected-only data is descriptive, not causal.
                        ytg = p.get("yards_to_go") or 0
                        down = p.get("down") or 1
                        situation = ("short" if ytg <= 4 else
                                     "long" if ytg / max(1, 7-down) >= 5 else "other")
                        for key in [f"{situation}:{p.get('play_family')}",
                                    "selected" if call.get("package_id") else "unselected"]:
                            g = groups[key]
                            g["snaps"] += 1
                            g["yards"] += y
                            g["explosives"] += int(y >= 30)
                            g["blitz"] += int(call["blitz"])
                            g[call["alignment"]] += 1
                out[f"{scheme}:{enabled}"] = {"counts": dict(counts),
                    "mean_points_allowed": statistics.mean(scores),
                    "scores": scores, "groups": {k: dict(v) for k,v in groups.items()}}
    finally:
        V2_ENGINE_CONFIG["defensive_packages_enabled"] = old
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=40)
    p.add_argument("--seed", type=int, default=20261123)
    p.add_argument("--out", default="reports/cch05")
    args = p.parse_args()
    result = run(args.games, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out/"results.json").write_text(json.dumps({"seed": args.seed,
        "games_per_condition": args.games, "results": result}, indent=2))
    for k,v in result.items():
        print(k, v["counts"], "points allowed", round(v["mean_points_allowed"],2))
