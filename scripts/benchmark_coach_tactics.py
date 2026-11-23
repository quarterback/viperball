#!/usr/bin/env python3
"""CCH-02: paired coach-only full-engine experiment on one Boot Raid offense.

Each matchup uses the same roster, base scheme, head coach, opposing team,
weather and engine seed. Only the OC tactical_profile differs. An ablation
disables CCH-02 without disabling the existing HC coaching model.

Usage:
    PYTHONHASHSEED=0 python scripts/benchmark_coach_tactics.py --games 80
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.coaching import CoachCard  # noqa: E402
from engine.coach_tactics import OFFENSIVE_ARCHETYPES  # noqa: E402
from engine.game_engine import ViperballEngine, V2_ENGINE_CONFIG, load_team_from_json  # noqa: E402


def coach(cid, role):
    return CoachCard(
        coach_id=cid, first_name="Test", last_name=cid, age=47, gender="female",
        role=role, classification="scheme_master",
        instincts=76, leadership=72, composure=70, rotations=65,
        development=65, recruiting=65,
        personality_sliders={
            "aggression": 70, "risk_tolerance": 70, "chaos_appetite": 60,
            "tempo_preference": 67, "stubbornness": 25, "player_trust": 75,
            "adaptability": 72,
        },
    )


def variant(cid, archetype):
    oc = coach(cid, "oc")
    template = OFFENSIVE_ARCHETYPES[archetype]
    oc.tactical_profile["identity"]["offense_interpretation"] = archetype
    oc.tactical_profile["offense"] = {
        "formation_bias": dict(template["formation_bias"]),
        "family_bias": dict(template["family_bias"]),
        "kick_pass_bias": dict(template["kick_pass_bias"]),
        "featured_position": template["featured_position"],
    }
    return oc


def simulate(games, seed, enabled):
    random.seed(seed)
    team_paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    if len(team_paths) < 2:
        raise RuntimeError("Requires at least two college teams")
    offense = load_team_from_json(str(team_paths[0]), fresh=False)
    defense = load_team_from_json(str(team_paths[1]), fresh=False)
    hc = coach("shared-head-coach", "head_coach")
    profiles = {
        "vertical_attack": variant("oc-deep", "vertical_attack"),
        "run_to_kick": variant("oc-ground", "run_to_kick"),
    }
    original_enabled = V2_ENGINE_CONFIG.get("coach_tactics_enabled", True)
    results = {}
    try:
        V2_ENGINE_CONFIG["coach_tactics_enabled"] = enabled
        for label, oc in profiles.items():
            stat = defaultdict(Counter)
            scores = []
            for n in range(games):
                staff = {"head_coach": hc, "oc": oc}
                engine = ViperballEngine(
                    deepcopy(offense), deepcopy(defense),
                    seed=seed + n, home_coaching=staff,
                    style_overrides={
                        offense.name: "boot_raid",
                        defense.name: "balanced",
                    }, weather="clear", neutral_site=True,
                )
                result = engine.simulate_game()
                scores.append(result["final_score"]["home"]["score"])
                observed = result["coach_tactics"]["home"]
                if enabled and not observed:
                    raise RuntimeError("OC tactical profile missing in enabled run")
                for field, counts in observed.get("selected", {}).items():
                    if isinstance(counts, dict):
                        stat[field].update(counts)
                    elif isinstance(counts, (int, float)):
                        stat["featured"][field] += counts
            results[label] = {
                "profile": label,
                "games": games,
                "tactics_enabled": enabled,
                "mean_points": round(statistics.mean(scores), 3),
                "game_scores": scores,
                "selected": {name: dict(counts) for name, counts in stat.items()},
            }
    finally:
        V2_ENGINE_CONFIG["coach_tactics_enabled"] = original_enabled
    return results


def rate(data, group, key):
    vals = data.get("selected", {}).get(group, {})
    total = sum(vals.values())
    return round(vals.get(key, 0) / total, 4) if total else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--out", default="reports/cch02")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")
    enabled = simulate(args.games, args.seed, True)
    disabled = simulate(args.games, args.seed, False)
    # Ablation should make two OCs with identical preexisting attributes
    # indistinguishable when personal tactical signatures are disabled.
    # A mismatch signals an unrelated RNG or runtime coaching effect.
    if (disabled["vertical_attack"]["game_scores"]
            != disabled["run_to_kick"]["game_scores"]):
        raise AssertionError(
            "With CCH-02 disabled, the two identical-attribute coaches "
            "produced different scores; the experiment is not controlled."
        )
    report = {"seed": args.seed, "base_scheme": "boot_raid",
              "enabled": enabled, "disabled": disabled}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(f"CCH-02 paired {args.games} games per coach per mode; base Boot Raid; seed {args.seed}")
    for label in ("vertical_attack", "run_to_kick"):
        e, d = enabled[label], disabled[label]
        print(f"{label}: mean points {e['mean_points']:.2f}; disabled {d['mean_points']:.2f}")
        for metric, key in (("formation", "spread"), ("formation", "heavy"),
                            ("family", "kick_pass"), ("family", "power"),
                            ("kick_pass", "bomb"), ("kick_pass", "quick_kick")):
            print(f"  {metric}/{key}: {rate(e, metric, key)}")
    print("Disabled profiles return empty tracking dictionaries; the existing "
          "coaching system and base scheme remain active.")
    print(f"Full metrics: {out / 'results.json'}")


if __name__ == "__main__":
    main()
