#!/usr/bin/env python3
"""Paired full-engine sensitivity check for DEF-01/02.

Each mode plays the same matchups with fresh per-game copies of the same
rosters and the same seeds. The formation-read fix is present in every mode.
The output is observational: there are no hard-coded winning-margin targets.

    python scripts/compare_defense_wiring.py --games 80 --seed 2026
"""

import argparse
from collections import defaultdict
from copy import deepcopy
import statistics

from benchmark_engine import build_matchups, overrides
from engine import V2_ENGINE_CONFIG, ViperballEngine


MODES = (
    ("previous_path", False, False),
    ("reads_only", True, False),
    ("schemes_only", False, True),
    ("combined", True, True),
)


def mean(values):
    return statistics.mean(values) if values else 0.0


def evaluate(teams, styles, pairs, seed, reads, schemes):
    original_reads = V2_ENGINE_CONFIG.get("defensive_reads_enabled", True)
    original_schemes = V2_ENGINE_CONFIG.get("defense_scheme_effects_enabled", True)
    data = defaultdict(list)
    scores_allowed_by_scheme = defaultdict(list)
    try:
        V2_ENGINE_CONFIG["defensive_reads_enabled"] = reads
        V2_ENGINE_CONFIG["defense_scheme_effects_enabled"] = schemes
        for index, (home, away) in enumerate(pairs):
            # Engine/role selection can mutate players, so clone before *each*
            # paired game rather than using teams carried over from prior games.
            engine = ViperballEngine(
                deepcopy(teams[home]),
                deepcopy(teams[away]),
                seed=seed + index,
                style_overrides=overrides(styles, home, away),
            )
            result = engine.simulate_game()
            fs = result["final_score"]
            stats = result["stats"]
            for side, name, opp in (("home", home, "away"),
                                    ("away", away, "home")):
                score = fs[side]["score"]
                s = stats[side]
                data["points"].append(score)
                data["touchdowns"].append(s.get("touchdowns", 0))
                data["snap_kicks"].append(s.get("drop_kicks_made", 0))
                data["place_kicks"].append(s.get("place_kicks_made", 0))
                data["plays"].append(s.get("total_plays", 0))
                scheme = styles.get(name, {}).get("defense_style", "swarm")
                scores_allowed_by_scheme[scheme].append(fs[opp]["score"])
                read = result.get("defensive_reads", {}).get(side, {})
                data["reads"].append(read.get("reads", 0))
                data["read_attempts"].append(read.get("attempts", 0))
            explosive = sum(
                (p.get("yards_gained", p.get("yards", 0)) or 0) >= 30
                for p in result.get("play_by_play", [])
            )
            data["explosive_plays"].append(explosive)
            data["margin"].append(abs(fs["home"]["score"] - fs["away"]["score"]))
    finally:
        V2_ENGINE_CONFIG["defensive_reads_enabled"] = original_reads
        V2_ENGINE_CONFIG["defense_scheme_effects_enabled"] = original_schemes

    return data, scores_allowed_by_scheme


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=80)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")

    teams, styles, pairs = build_matchups(args.games, args.seed)
    print(f"DEF-01/02 paired full-engine sample: {args.games} games per mode, seed {args.seed}")
    print("Same matchups and per-game roster copies; formation fix active in all modes.")
    print("Mode                pts/team  TD/team  DK/team  PK/team  explosive/game  reads/game  median margin")

    for label, reads, schemes in MODES:
        data, by_scheme = evaluate(teams, styles, pairs, args.seed, reads, schemes)
        print(f"{label:19} {mean(data['points']):8.2f}"
              f" {mean(data['touchdowns']):8.2f}"
              f" {mean(data['snap_kicks']):8.2f}"
              f" {mean(data['place_kicks']):8.2f}"
              f" {mean(data['explosive_plays']):15.2f}"
              f" {sum(data['reads']) / args.games:11.2f}"
              f" {statistics.median(data['margin']):13.2f}")
        print("  Points allowed by defense, sorted by scheme (sample size):")
        for defense, allowed in sorted(by_scheme.items()):
            print(f"    {defense:14} {mean(allowed):6.1f} ({len(allowed)} games)")


if __name__ == "__main__":
    main()
