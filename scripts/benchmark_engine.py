"""Engine benchmark: run a fixed sample of full engine games and report what
the mechanics produce.  There are no scoring targets; compare runs against
each other.

Run after every engine change, from the repo root:

    python scripts/benchmark_engine.py            # 200 games
    python scripts/benchmark_engine.py --games 400

Matchups and seeds are fixed, so two runs of the same code print the same
numbers and a change shows up as a real difference. Each team plays its
season assigned offense, defense and special teams scheme, the same way
Season.simulate_game passes them to the engine.
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



def build_matchups(n_games: int, seed: int):
    random.seed(seed)  # fresh rosters are generated at random; fix them
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


def run_season(weeks: int):
    """Sim a real CVL season (conference schedule, fresh rosters, season
    schemes) through the same code the app uses, and report the same numbers.
    This is the true measure of margins; the random matchup sample overstates
    blowouts because it pairs top teams with bottom teams."""
    import tempfile
    os.environ["VIPERBALL_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "bench.db")
    from fastapi.testclient import TestClient
    import api.main as api
    client = TestClient(api.app)
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/season", json={"name": "Benchmark"}).raise_for_status()
    season = api.sessions[sid]["season"]
    for _ in range(weeks):
        if season.is_regular_season_complete():
            break
        season.simulate_week()
    games = [g for g in season.schedule if g.completed and g.full_result]
    stats = collections.defaultdict(list)
    margins, conf_margins = [], []
    for g in games:
        r = g.full_result
        m = abs(g.home_score - g.away_score)
        margins.append(m)
        if g.is_conference_game:
            conf_margins.append(m)
        for side in ("home", "away"):
            s = r["stats"][side]
            stats["points"].append(r["final_score"][side]["score"])
            stats["touchdowns"].append(s["touchdowns"])
            stats["snap_kicks_made"].append(s["drop_kicks_made"])
            stats["field_goals_made"].append(s["place_kicks_made"])
            stats["turnovers"].append(s["fumbles_lost"] + s["kick_pass_interceptions"] + s["lateral_interceptions"])
    print(f"Real season: {len(games)} games, {len(conf_margins)} conference games\n")
    print("Per team, per game")
    for key, values in stats.items():
        mean = statistics.mean(values)
        print(f"  {key:20} {mean:6.2f}")
    for label, ms in (("All games", margins), ("Conference games", conf_margins)):
        if ms:
            print(f"{label}: median margin {statistics.median(ms):.1f},"
                  f" decided by 30+ {sum(x >= 30 for x in ms) / len(ms):.0%},"
                  f" within 9 {sum(x <= 9 for x in ms) / len(ms):.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--season", type=int, default=0, metavar="WEEKS",
                    help="sim this many weeks of a real season instead of random matchups")
    args = ap.parse_args()
    if args.season:
        random.seed(args.seed)
        run_season(args.season)
        return

    teams, styles, pairs = build_matchups(args.games, args.seed)

    per_team = collections.defaultdict(list)
    drives = collections.defaultdict(lambda: [0, 0])
    td_lengths = []
    sixth_down_in_range = 0
    margins = []
    total_drives = 0

    for i, (home, away) in enumerate(pairs):
        engine = ViperballEngine(teams[home], teams[away], seed=args.seed + i,
                                 style_overrides=overrides(styles, home, away))
        result = engine.simulate_game()
        margins.append(abs(result["final_score"]["home"]["score"] - result["final_score"]["away"]["score"]))
        for side in ("home", "away"):
            s = result["stats"][side]
            per_team["points"].append(result["final_score"][side]["score"])
            per_team["touchdowns"].append(s["touchdowns"])
            per_team["snap_kicks_made"].append(s["drop_kicks_made"])
            per_team["snap_kick_attempts"].append(s["drop_kicks_attempted"])
            per_team["field_goals_made"].append(s["place_kicks_made"])
            per_team["plays"].append(s["total_plays"])
            per_team["turnovers"].append(s["fumbles_lost"] + s["kick_pass_interceptions"] + s["lateral_interceptions"])
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
        print(f"  {key:20} {mean:6.2f}")

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
    print(f"Final margin: median {statistics.median(margins):.1f},"
          f" decided by 30+ {sum(m >= 30 for m in margins) / len(margins):.0%}")
    print(f"Drives per team per game: {total_drives / max(1, args.games * 2):.1f}")


if __name__ == "__main__":
    main()
