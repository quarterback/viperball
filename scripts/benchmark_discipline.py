"""PEN-04: full-engine, seeded penalty and ejection calibration.

Run: python scripts/benchmark_discipline.py --games 1000 --seed 130300
JSON output contains counts and rates; no tuning or saving of rosters.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.game_engine import ViperballEngine, load_team_from_json


def run(games, seed):
    rng = random.Random(seed)
    files = sorted((ROOT / "data" / "teams").glob("*.json"))
    totals, types, reasons, by_team = Counter(), Counter(), Counter(), {}
    for i in range(games):
        home, away = rng.sample(files, 2)
        result = ViperballEngine(load_team_from_json(str(home)),
                                 load_team_from_json(str(away)),
                                 seed=seed + i).simulate_game()
        ejections = result["ejections"]
        totals["games_with_ejection"] += bool(ejections)
        totals["ejections"] += len(ejections)
        for event in ejections:
            reasons[event["reason"]] += 1
        for side, path in (("home", home), ("away", away)):
            row = result["stats"][side]
            team = by_team.setdefault(path.stem, Counter())
            team["games"] += 1
            for key in ("penalties", "penalty_yards", "penalties_declined",
                        "unsportsmanlike_fouls", "ejections"):
                totals[key if key != "ejections" else "team_ejections"] += row[key]
                team[key] += row[key]
            types.update(row["penalties_by_type"])
            assert row["ejections"] == sum(e["side"] == side for e in ejections)
        seen = set()
        for play in result["play_by_play"]:
            penalty = play.get("penalty") or {}
            if penalty.get("player_name"):
                key = (penalty["on_team"], penalty["player_name"])
                assert key not in seen, (i, key, play["description"])
                if penalty.get("ejection"):
                    seen.add(key)
        assert len(seen) == len(ejections)
    return {
        "games": games, "seed": seed, "counts": dict(totals),
        "rates_per_game": {key: value / games for key, value in totals.items()},
        "accepted_fouls_by_type": dict(types.most_common()),
        "ejections_by_reason": dict(reasons.most_common()),
        "by_team": {name: dict(row) for name, row in sorted(by_team.items())},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=130300)
    args = parser.parse_args()
    if args.games <= 0:
        parser.error("--games must be positive")
    print(json.dumps(run(args.games, args.seed), indent=2))
