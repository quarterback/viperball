"""Engine benchmark: run a fixed sample of full engine games and compare the
results with the documented targets.

Run after every engine change, from the repo root:

    python scripts/benchmark_engine.py            # 200 games
    python scripts/benchmark_engine.py --games 400

Matchups and seeds are fixed, so two runs of the same code print the same
numbers and a change shows up as a real difference. Each team plays its
season assigned offense, defense and special teams scheme, the same way
Season.simulate_game passes them to the engine.

Targets come from RULES_EVOLUTION_AAR.md (per team, per game: 45 to 50
points, 1.9 to 3.5 touchdowns, 3 to 5 snap kicks made) and the rule that
starting field position should matter.
"""

import argparse
import collections
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from engine import ViperballEngine, load_teams_from_directory  # noqa: E402
from engine.ai_coach import auto_assign_all_teams  # noqa: E402

TARGETS = {
    "points": (45.0, 50.0),
    "touchdowns": (1.9, 3.5),
    "snap_kicks_made": (3.0, 5.0),
}


def build_matchups(n_games: int, seed: int):
    teams = load_teams_from_directory(os.path.join(ROOT, "data", "teams"), fresh=True)
    styles = auto_assign_all_teams(os.path.join(ROOT, "data", "teams"), human_teams=[], seed=seed)
    rng = random.Random(seed)
    names = sorted(teams)
    pairs = [tuple(rng.sample(names, 2)) for _ in range(n_games)]
    return teams, styles, pairs


def overrides(styles, *team_names):
    out = {}
    for name in team_names:
        cfg = styles.get(name, {})
        out[name] = cfg.get("offense_style", "balanced")
        out[f"{name}_defense"] = cfg.get("defense_style", "swarm")
        out[f"{name}_st"] = cfg.get("st_scheme", "aces")
    return out


def bucket(start: int) -> str:
    if start < 15:
        return "own 1-14"
    if start <= 25:
        return "own 15-25"
    if start < 50:
        return "own 26-49"
    return "opp half"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    teams, styles, pairs = build_matchups(args.games, args.seed)

    per_team = collections.defaultdict(list)
    drives = collections.defaultdict(lambda: [0, 0])
    td_lengths = []
    sixth_down_in_range = 0
    total_drives = 0

    for i, (home, away) in enumerate(pairs):
        engine = ViperballEngine(teams[home], teams[away], seed=args.seed + i,
                                 style_overrides=overrides(styles, home, away))
        result = engine.simulate_game()
        for side in ("home", "away"):
            s = result["stats"][side]
            per_team["points"].append(result["final_score"][side]["score"])
            per_team["touchdowns"].append(s["touchdowns"])
            per_team["snap_kicks_made"].append(s["drop_kicks_made"])
            per_team["snap_kick_attempts"].append(s["drop_kicks_attempted"])
            per_team["field_goals_made"].append(s["place_kicks_made"])
            per_team["plays"].append(s["total_plays"])
        for d in result.get("drive_summary", []):
            start = d.get("start_yard_line")
            if start is None:
                continue
            total_drives += 1
            b = drives[bucket(start)]
            b[1] += 1
            b[0] += d.get("result") == "touchdown"
        for p in result["play_by_play"]:
            if p["result"] == "touchdown":
                td_lengths.append(p.get("yards") or 0)
            if p.get("down") == 6 and (100 - p["field_position"] + 10) <= 45:
                sixth_down_in_range += 1

    print(f"{args.games} games, seed {args.seed}\n")
    print("Per team, per game")
    for key, values in per_team.items():
        mean = statistics.mean(values)
        line = f"  {key:20} {mean:6.2f}"
        if key in TARGETS:
            lo, hi = TARGETS[key]
            mark = "ok" if lo <= mean <= hi else "OFF"
            line += f"   target {lo}-{hi}  {mark}"
        print(line)

    print("\nTouchdown rate by drive start")
    for name in ("own 1-14", "own 15-25", "own 26-49", "opp half"):
        tds, n = drives[name]
        print(f"  {name:10} {n:5} drives   {tds / max(1, n):5.0%}")

    td_lengths.sort()
    n = max(1, len(td_lengths))
    print("\nTouchdown play length")
    print(f"  median {td_lengths[len(td_lengths) // 2] if td_lengths else 0} yd,"
          f" 30+ yd {sum(y >= 30 for y in td_lengths) / n:.0%} of TDs")
    print(f"\n6th downs inside 45 yards of a kick: {sixth_down_in_range / max(1, args.games * 2):.2f} per team per game")
    print(f"Drives per team per game: {total_drives / max(1, args.games * 2):.1f}")


if __name__ == "__main__":
    main()
