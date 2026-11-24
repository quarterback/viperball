#!/usr/bin/env python3
"""Paired full-game package calibration and physical rush accounting."""
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
from engine.playbook_catalog import get_package
from engine.defensive_commitments import eligibility

# Each case is a native or compatible package, versus an offense that
# exercises its benefit or concession. Cases share roster pairs and seeds.
CASES = [
    ("fortress", "fortress_goal_line_stand", "ground_pound"),
    ("fortress", "fortress_short_yardage_wall", "ground_pound"),
    ("fortress", "fortress_short_yardage_wall", "lateral_spread"),
    ("lockdown", "lockdown_kick_range_shell", "boot_raid"),
    ("lockdown", "lockdown_long_yardage_bracket", "boot_raid"),
    ("lockdown", "lockdown_long_yardage_bracket", "ground_pound"),
    ("drift", "drift_prevent", "shock_and_awe"),
    ("blitz_pack", "blitz_short_yardage_pressure", "ground_pound"),
    ("blitz_pack", "rugby_rush_line", "lateral_spread"),
    ("predator", "afl_kick_in_press", "boot_raid"),
    ("chaos", "lax_ride", "boot_raid"),
    ("swarm", "swarm_containment", "lateral_spread"),
    ("shadow", "shadow_robber", "boot_raid"),
    ("chaos", "chaos_lateral_trap", "lateral_spread"),
    ("predator", "predator_exhaustion_press", "boot_raid"),
    # Same offense and roster for base scheme pressure comparison.
    ("swarm", None, "boot_raid"),
    ("blitz_pack", None, "boot_raid"),
    ("lockdown", None, "boot_raid"),
]

def eligible(package, call):
    if not package:
        return 0.0
    return eligibility(package, call.get("situations", []), call.get("tactical_context", {}),
                       get_package(package)["situation_tags"])

def summarize_rush(g, r):
    rushers, cover = set(r["rushers"]), set(r["coverage_players"])
    on = set(r["defenders_on_field"])
    if (len(rushers) != r["rusher_count"] or len(cover) != r["coverage_count"]
        or rushers & cover or rushers | cover != on
        or not 0 <= r["rusher_count"] <= min(6, max(0, len(on)-1))
        or len(set(r["blockers"])) != r["blocker_count"]
        or (r["rusher"] and r["rusher"] not in rushers)
        or (r["matched_coverage_defender"] and r["matched_coverage_defender"] not in cover)):
        raise RuntimeError("Rush assignment does not reconcile with on-field players")
    g["attempts"] += 1
    g[r["outcome"]] += 1
    g["pressure"] += int(r["pressure"])
    g["completions"] += int(r["completed"])
    g["rushers"] += r["rusher_count"]
    g["coverage_cost_bp"] += round(10000*r["coverage_cost"])
    g["package_coverage_delta_bp"] += round(10000*r["package_coverage_delta"])
    g["hurry_loss_bp"] += round(10000*(r["completion_before"]-r["completion_after"]))

def run(games, seed):
    random.seed(seed)
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    # Two distinct matchups, alternated across matched conditions.
    teams = [load_team_from_json(str(paths[i]), fresh=False) for i in (0, 1, len(paths)//2, len(paths)//2+1)]
    staff = {"head_coach": coach("shared-hc", "head_coach"), "dc": dc_variant("run_wall")}
    out = {}
    old = V2_ENGINE_CONFIG.get("defensive_packages_enabled", True)
    try:
        for scheme, package, attack in CASES:
            label = f"{scheme}:{package or 'base'}:{attack}"
            for enabled in ((False, True) if package else (False,)):
                V2_ENGINE_CONFIG["defensive_packages_enabled"] = enabled
                counts, groups, scores = Counter(), defaultdict(Counter), []
                for n in range(games):
                    i = 2*(n % 2)
                    a, b = deepcopy(teams[i]), deepcopy(teams[i+1])
                    # Alternate DC signatures independently of roster matchup.
                    staff["dc"] = dc_variant("run_wall" if (n//2)%2 == 0 else "selective_pressure")
                    rec = new_installation(b.name, staff, "boot_raid", scheme, 2026)
                    rec["defense"].update(familiarity=1.0, family_familiarity=1.0,
                        packages=[{"package_id": package, "familiarity": 1.0}] if package else [])
                    b.installation = rec
                    game = ViperballEngine(a, b, seed=seed+n, neutral_site=True,
                        weather="clear", away_coaching=deepcopy(staff),
                        style_overrides={a.name: attack, b.name+"_defense": scheme}).simulate_game()
                    scores.append(game["final_score"]["home"]["score"])
                    dc = game["defensive_coach_tactics"]["away"]
                    counts["calls"] += dc["calls"]
                    counts["selected"] += dc["packages"]["selected"].get(package, 0)
                    counts["secondary_selected"] += dc["packages"].get("secondary_selected", {}).get(package, 0)
                    counts["blitz"] += dc["blitz_calls"]
                    for p in game["play_by_play"]:
                        call = p.get("defensive_call") or {}
                        rush = p.get("rush_event") or {}
                        selected = call.get("package_id") == package and bool(package)
                        if rush.get("defending_side") == "away":
                            for key in ("rush:all", "rush:count:"+str(rush["rusher_count"]),
                                        "rush:"+rush["subfamily"]):
                                summarize_rush(groups[key], rush)
                            summarize_rush(groups["rush:coach:"+dc["signature"]+":count:"+str(rush["rusher_count"])], rush)
                            if selected:
                                summarize_rush(groups["selected:rush:"+rush["subfamily"]], rush)
                        if call.get("defending_side") != "away" or p.get("yards") is None:
                            continue
                        tier = eligible(package, call)
                        if not tier:
                            if selected:
                                raise RuntimeError("Package called outside its situation")
                            continue
                        counts["eligible"] += 1
                        counts["secondary_eligible"] += int(tier < 1)
                        fam = p.get("play_family")
                        y = p["yards"]
                        keys = ["eligible:"+str(fam)]
                        if selected:
                            keys.append("selected:"+str(fam))
                        for key in keys:
                            g = groups[key]
                            g["snaps"] += 1
                            g["yards"] += y
                            g["explosives"] += int(y >= 30)
                            g["short_gains"] += int(0 < y <= 5)
                            g["conversions"] += int(y >= (p.get("yards_to_go") or 20))
                            if rush:
                                g["kick_attempts"] += 1
                                g["completions"] += int(rush["completed"])
                            if "run_tactical_delta" in call:
                                g["tactical_delta_bp"] += round(10000*call["run_tactical_delta"])
                                g["delta_observations"] += 1
                    summary = game["defensive_rush"]["away"]
                    counts["summary_attempts"] += summary["attempts"]
                    counts["summary_rushers"] += summary["rushers_committed"]
                if counts["summary_attempts"] != groups["rush:all"]["attempts"] or counts["summary_rushers"] != groups["rush:all"]["rushers"]:
                    raise RuntimeError("Game rush summary disagrees with play log")
                out[f"{label}:{enabled}"] = {"counts": dict(counts),
                    "mean_points_allowed": statistics.mean(scores),
                    "scores": scores, "groups": {k: dict(v) for k,v in groups.items()}}
    finally:
        V2_ENGINE_CONFIG["defensive_packages_enabled"] = old
    return out

def rate(g, key, denom):
    return round(g.get(key,0)/g[denom],4) if g.get(denom) else None

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
        g=v["groups"]["rush:all"]
        print(k, "counts", v["counts"], "points", round(v["mean_points_allowed"],2),
              "pressure",rate(g,"pressure","attempts"),"sack",rate(g,"sack","attempts"),
              "complete",rate(g,"completions","attempts"),"rushers",rate(g,"rushers","attempts"))
        for name,b in sorted(v["groups"].items()):
            if name.startswith("rush:count:"):
                print(" ",name,b["attempts"],"pressure",rate(b,"pressure","attempts"),"complete",rate(b,"completions","attempts"),"released_completion",round(b.get("completions",0)/max(1,b["attempts"]-b.get("sack",0)),4))
            elif name.startswith("eligible:"):
                print(" ",name,b["snaps"],"yards",rate(b,"yards","snaps"),"conversion",rate(b,"conversions","snaps"),
                      "complete",rate(b,"completions","kick_attempts"),"explosive",rate(b,"explosives","snaps"))
