#!/usr/bin/env python3
"""CCH-03 paired full-engine comparison: same defense family, different DCs.

No playbook packages or made-up defensive ratings. The OC, roster,
opponents and all existing coach attributes are held fixed while only a
stored DC defensive interpretation changes. The coach-only switch must
restore identical complete-game results for both DCs.

  PYTHONHASHSEED=0 python scripts/benchmark_defensive_coaches.py --games 40
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.coach_tactics import DEFENSIVE_ARCHETYPES  # noqa: E402
from engine.coaching import CoachCard  # noqa: E402
from engine.game_engine import V2_ENGINE_CONFIG, ViperballEngine, load_team_from_json  # noqa: E402


def coach(cid, role="dc"):
    return CoachCard(
        coach_id=cid, first_name="Benchmark", last_name=cid,
        gender="female", age=46, role=role, classification="scheme_master",
        instincts=75, leadership=70, composure=72, rotations=65,
        development=67, recruiting=63,
        personality_sliders={
            "aggression": 70, "risk_tolerance": 55,
            "adaptability": 70, "stubbornness": 35, "player_trust": 73,
        },
    )


def dc_variant(name):
    c = coach("dc-" + name)
    template = DEFENSIVE_ARCHETYPES[name]
    c.tactical_profile["identity"]["defense_interpretation"] = name
    c.tactical_profile["defense"] = {
        "pressure_bias": template["pressure_bias"],
        "run_support_bias": template["run_support_bias"],
        "coverage_focus": template["coverage_focus"],
        "read_focus": list(template["read_focus"]),
    }
    return c


def mean(values):
    return round(statistics.mean(values), 3) if values else None


def run(games, seed, scheme, enabled, teams):
    prior = V2_ENGINE_CONFIG.get("defensive_coach_tactics_enabled", True)
    result = {}
    try:
        V2_ENGINE_CONFIG["defensive_coach_tactics_enabled"] = enabled
        attack, defense = teams
        head = coach("constant-head-coach", "head_coach")
        for variant in ("selective_pressure", "run_wall"):
            staff = {"head_coach": head, "dc": dc_variant(variant)}
            team_points = []
            yardages = []
            called_blitz = 0
            called_total = 0
            alignments = Counter()
            read_attempts = Counter()
            read_successes = Counter()
            for n in range(games):
                game = ViperballEngine(
                    deepcopy(attack), deepcopy(defense), seed=seed + n,
                    neutral_site=True, weather="clear", away_coaching=staff,
                    style_overrides={
                        attack.name: "boot_raid",
                        defense.name + "_defense": scheme,
                    },
                ).simulate_game()
                team_points.append(game["final_score"]["home"]["score"])
                yardages.append(game["stats"]["home"]["total_yards"])
                choices = game["defensive_coach_tactics"]["away"]
                if enabled and not choices:
                    raise AssertionError("Missing DC decisions in enabled game")
                called_total += choices.get("calls", 0)
                called_blitz += choices.get("blitz_calls", 0)
                alignments.update(choices.get("alignments", {}))
                read_attempts.update(choices.get("read_attempts", {}))
                read_successes.update(choices.get("read_successes", {}))
            result[variant] = {
                "games": games, "points": team_points,
                "mean_points": mean(team_points),
                "mean_offense_yards": mean(yardages),
                "called_blitz": called_blitz,
                "called_total": called_total,
                "blitz_share": round(called_blitz / called_total, 4)
                               if called_total else None,
                "alignment_share": {
                    k: round(v / called_total, 4)
                    for k, v in sorted(alignments.items())
                } if called_total else {},
                "read_attempts": dict(read_attempts),
                "read_successes": dict(read_successes),
            }
    finally:
        V2_ENGINE_CONFIG["defensive_coach_tactics_enabled"] = prior
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--schemes", default="lockdown,blitz_pack")
    parser.add_argument("--out", default="reports/cch03")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()]
    if not schemes or any(s not in ("lockdown", "blitz_pack") for s in schemes):
        parser.error("--schemes must be lockdown and/or blitz_pack")

    random.seed(args.seed)
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    teams = (load_team_from_json(str(paths[0]), fresh=False),
             load_team_from_json(str(paths[1]), fresh=False))
    all_results = {}
    for scheme in schemes:
        enabled = run(args.games, args.seed, scheme, True, teams)
        disabled = run(args.games, args.seed, scheme, False, teams)
        if disabled["selective_pressure"]["points"] != disabled["run_wall"]["points"]:
            raise AssertionError(
                "DC tactical ablation is not controlled: identical old attributes "
                "give differing scores when CCH-03 is disabled")
        if (not enabled["selective_pressure"]["called_total"]
                or not enabled["run_wall"]["called_total"]):
            raise AssertionError("DC decisions never selected")
        if (enabled["selective_pressure"]["blitz_share"]
                == enabled["run_wall"]["blitz_share"]
                and enabled["selective_pressure"]["alignment_share"]
                == enabled["run_wall"]["alignment_share"]):
            raise AssertionError("Distinct DCs made identical choices")
        all_results[scheme] = {"enabled": enabled, "disabled": disabled}
        print(f"{scheme}: {args.games} games per DC per mode")
        for k, val in enabled.items():
            print(f"  {k:20}: blitz {val['blitz_share']:.1%}, "
                  f"alignments {val['alignment_share']}, "
                  f"offensive points/game {val['mean_points']:.2f}, "
                  f"yards/game {val['mean_offense_yards']:.2f}")
        print("  disabled coach profiles: identical per-game scoring (checked)")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({
        "seed": args.seed, "games_per_dc_mode": args.games,
        "base_offense": "boot_raid", "results": all_results,
    }, indent=2), encoding="utf8")
    print(f"Completed {len(schemes) * args.games * 4} full games. "
          f"Results at {out / 'results.json'}")


if __name__ == "__main__":
    main()
