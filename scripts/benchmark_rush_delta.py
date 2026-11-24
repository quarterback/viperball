#!/usr/bin/env python3
"""DEF-08 / DEL-01 paired full-engine attribution and restart study.

Same rosters and random seeds; vary only the committed-rusher credit
method and score-dependent restarts. Report effects; no desired win rate.
Run: PYTHONHASHSEED=0 python scripts/benchmark_rush_delta.py --games 24
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.game_engine import ViperballEngine, V2_ENGINE_CONFIG, load_team_from_json


def avg(xs):
    return round(statistics.mean(xs), 3) if xs else None


def run(games, seed):
    files = sorted((ROOT / "data" / "teams").glob("*.json"))
    teams = [load_team_from_json(str(files[i]), fresh=False) for i in
             (0, 1, len(files)//2, len(files)//2+1)]
    prior = {k: V2_ENGINE_CONFIG.get(k) for k in
             ("rush_credit_model", "delta_restarts_enabled")}
    output = {}
    scores = {}
    try:
        for credit in ("highest", "weighted"):
            for delta_on in (True, False):
                k = f"{credit}/delta_{'on' if delta_on else 'off'}"
                V2_ENGINE_CONFIG.update(rush_credit_model=credit,
                                        delta_restarts_enabled=delta_on)
                totals = Counter()
                shares, sack_rates, ppds, delta_yards, margins, points = ([] for _ in range(6))
                completed_scores = []
                for n in range(games):
                    random.seed(seed+n)
                    idx = 2 * (n % 2)
                    home, away = (deepcopy(teams[idx]), deepcopy(teams[idx+1]))
                    game = ViperballEngine(home, away, seed=seed+n, neutral_site=True,
                                          weather="rain" if n % 3 == 1 else "clear").simulate_game()
                    h = game["final_score"]["home"]["score"]
                    a = game["final_score"]["away"]["score"]
                    completed_scores.append([h, a])
                    margins.append(abs(h-a))
                    points.extend([h,a])
                    for side in ("home", "away"):
                        row = game["defensive_rush"][side]
                        stats = game["stats"][side]
                        totals["attempts"] += row["attempts"]
                        totals["sacks"] += row["sacks"]
                        totals["hurries"] += row["hurries"]
                        totals["pressures"] += row["pressures"]
                        totals["credited_sacks"] += sum(p["sacks"] for p in
                                                          game["player_stats"][side])
                        totals["credited_hurries"] += sum(p["hurries"] for p in
                                                            game["player_stats"][side])
                        # A physical rush is logged even when an accepted
                        # foul cancels the play and restores official stats.
                        for play in game["play_by_play"]:
                            rush = play.get("rush_event") or {}
                            foul = play.get("penalty") or {}
                            if rush.get("defending_side") == side and foul.get("nullified"):
                                totals["nullified_sacks"] += int(rush.get("outcome") == "sack")
                                totals["nullified_hurries"] += int(rush.get("outcome") == "hurry")
                        rushing = [p["sacks"] + p["lead_hurries"]
                                   for p in row["by_player"].values()]
                        total = sum(rushing)
                        if total:
                            shares.append(max(rushing)/total)
                        delta_yards.append(stats.get("delta_yards", 0))
                        ppds.append(stats.get("viperball_metrics", {}).get("ppd", 0))
                        if not delta_on and stats.get("delta_yards", 0) != 0:
                            raise RuntimeError("Neutral restarts produced nonzero delta")
                output[k] = {
                    "games": games, "team_games": games*2,
                    "mean_points": avg(points), "median_margin": statistics.median(margins),
                    "mean_ppd": avg(ppds), "mean_delta_yards": avg(delta_yards),
                    "mean_leader_credit_share": avg(shares),
                    "credit_teams": len(shares), "totals": dict(totals),
                    "pressure_rate": round(totals["pressures"]/max(1,totals["attempts"]),4),
                    "sack_rate": round(totals["sacks"]/max(1,totals["attempts"]),4),
                }
                expected_sacks = totals["sacks"] - totals["nullified_sacks"]
                expected_hurries = totals["hurries"] - totals["nullified_hurries"]
                if (totals["credited_sacks"] != expected_sacks or
                    totals["credited_hurries"] != expected_hurries):
                    raise RuntimeError(
                        f"Official rush credit parity {k}: "
                        f"sacks {totals['credited_sacks']}/{expected_sacks}, "
                        f"hurries {totals['credited_hurries']}/{expected_hurries}, "
                        f"physical {totals['sacks']}/{totals['hurries']}")
                scores[k] = completed_scores
        for credit in ("highest","weighted"):
            changed = sum(a!=b for a,b in zip(scores[f"{credit}/delta_on"],
                                               scores[f"{credit}/delta_off"]))
            output[f"{credit}/delta_counterfactual"] = {
                "matched_games": games, "changed_final_scores": changed,
                "mean_abs_home_score_difference": avg([
                    abs(a[0]-b[0]) for a,b in zip(scores[f"{credit}/delta_on"],
                                                    scores[f"{credit}/delta_off"])
                ])
            }
        return {"seed":seed,"results":output}
    finally:
        V2_ENGINE_CONFIG.update(prior)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games",type=int,default=24)
    parser.add_argument("--seed",type=int,default=20261124)
    parser.add_argument("--out",default=None)
    args=parser.parse_args()
    if args.games<1: parser.error("--games must be positive")
    result=run(args.games,args.seed)
    data=json.dumps(result,indent=2,sort_keys=True)
    if args.out:
        p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
    print(data)


if __name__=="__main__":
    main()
