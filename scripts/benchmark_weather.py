"""WEA-02 matched weather study.

Plays the same matchups and seeds under controlled conditions and reports
what each condition does: ball handling, kicking, punting, kick passing, play
mix, fatigue and scoring. Wind conditions also split kicks by whether the
kicking team had the wind at its back.

No scoring target: scoring is reported, not tuned.

    python scripts/benchmark_weather.py --games 60
"""
import argparse
import collections
import multiprocessing as mp
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.game_engine import ViperballEngine  # noqa: E402
from engine.weather import GameWeather, Reading, Venue  # noqa: E402
from scripts.benchmark_engine import build_matchups, overrides  # noqa: E402


def _game(periods, venue=None):
    return GameWeather(periods=[Reading(**vars(p)) for p in periods], venue=venue or Venue())


def conditions():
    calm = Reading(temp_f=65, humidity=0.5)
    return {
        "clear": lambda: _game([calm] * 4),
        "light rain": lambda: _game([Reading(temp_f=52, precip="rain", intensity=0.25,
                                             humidity=0.9)] * 4),
        "heavy rain": lambda: _game([Reading(temp_f=50, precip="rain", intensity=0.85,
                                             humidity=0.95)] * 4),
        "heavy rain, turf": lambda: _game([Reading(temp_f=50, precip="rain", intensity=0.85,
                                                   humidity=0.95)] * 4,
                                          Venue(surface="turf")),
        "snow": lambda: _game([Reading(temp_f=26, precip="snow", intensity=0.6,
                                       humidity=0.85)] * 4),
        "cold, 20F": lambda: _game([Reading(temp_f=20, humidity=0.5)] * 4),
        "heat, 96F humid": lambda: _game([Reading(temp_f=96, humidity=0.7)] * 4),
        "wind 25 along": lambda: _game([Reading(temp_f=55, wind_mph=25, wind_dir=0)] * 4),
        "crosswind 25": lambda: _game([Reading(temp_f=55, wind_mph=25, wind_dir=90)] * 4),
        "dome": lambda: _game([Reading(temp_f=70, humidity=0.45)] * 4,
                              Venue(roof="dome", surface="turf")),
        "altitude 7000": lambda: _game([calm] * 4, Venue(altitude_ft=7000)),
    }


def _sign(side, quarter):
    home_north = quarter % 2 == 1
    north = home_north if side == "home" else not home_north
    return 1 if north else -1


def run_condition(args):
    name, games, seed = args
    make = conditions()[name]
    teams, styles, pairs = build_matchups(games, seed)
    t = collections.Counter()
    for i, (home, away) in enumerate(pairs):
        wx = make()
        r = ViperballEngine(teams[home], teams[away], seed=seed + i, weather=wx,
                            style_overrides=overrides(styles, home, away)).simulate_game()
        along = wx.reading(1).wind_along
        for side in ("home", "away"):
            s = r["stats"][side]
            t["team_games"] += 1
            t["points"] += r["final_score"][side]["score"]
            t["touchdowns"] += s["touchdowns"]
            t["fumbles_lost"] += s["fumbles_lost"]
            t["muffs"] += s["muffs"]
            t["dk_att"] += s["drop_kicks_attempted"]
            t["dk_made"] += s["drop_kicks_made"]
            t["pk_att"] += s["place_kicks_attempted"]
            t["pk_made"] += s["place_kicks_made"]
            t["kp_att"] += s["kick_passes_attempted"]
            t["kp_comp"] += s["kick_passes_completed"]
            t["rush"] += s["rushing_carries"]
            t["plays"] += s["total_plays"]
            t["penalties"] += s["penalties"]
            t["fatigue"] += s["avg_fatigue"]
            t["yards"] += s["total_yards"]
        for p in r["play_by_play"]:
            side, pt = p.get("snap_possession") or p["possession"], p["play_type"]
            tail = along * _sign(side, min(4, p["quarter"]))
            leg = "with" if tail > 1 else ("into" if tail < -1 else "even")
            if pt == "kick_pass" and p.get("kick_pass_subfamily") == "bomb":
                t["bombs"] += 1
            if pt in ("drop_kick", "place_kick"):
                t[f"kick_{leg}"] += 1
                if p["result"] == "successful_kick":
                    t[f"kick_{leg}_made"] += 1
            if pt == "punt":
                m = re.search(r"punt → (\d+) yards", p.get("description", ""))
                if m:
                    t[f"punt_{leg}"] += 1
                    t[f"punt_{leg}_yds"] += int(m.group(1))
    return name, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args()
    names = list(conditions())
    jobs = [(n, args.games, args.seed) for n in names]
    with mp.Pool(args.workers) as pool:
        results = dict(pool.map(run_condition, jobs))

    def per(t, k):
        return t[k] / max(1, t["team_games"])

    print(f"{args.games} games per condition, seed {args.seed}; per team per game\n")
    hdr = (f"{'condition':18s} {'pts':>5s} {'TD':>5s} {'fum':>5s} {'muff':>5s} {'SK%':>5s} "
           f"{'SKatt':>5s} {'FG%':>5s} {'KP%':>5s} {'bomb':>5s} {'rush%':>5s} "
           f"{'pen':>5s} {'fatg':>5s} {'yds':>5s}")
    print(hdr)
    for n in names:
        t = results[n]
        sk = t["dk_made"] / max(1, t["dk_att"]) * 100
        fg = t["pk_made"] / max(1, t["pk_att"]) * 100
        kp = t["kp_comp"] / max(1, t["kp_att"]) * 100
        rush = t["rush"] / max(1, t["plays"]) * 100
        print(f"{n:18s} {per(t,'points'):5.1f} {per(t,'touchdowns'):5.2f} "
              f"{per(t,'fumbles_lost'):5.2f} {per(t,'muffs'):5.2f} {sk:5.1f} "
              f"{per(t,'dk_att'):5.2f} {fg:5.1f} {kp:5.1f} {per(t,'bombs'):5.2f} {rush:5.1f} "
              f"{per(t,'penalties'):5.2f} {per(t,'fatigue'):5.1f} {per(t,'yards'):5.0f}")
    for n in ("wind 25 along",):
        t = results[n]
        print(f"\n{n}: kicks with the wind {t['kick_with']} "
              f"({t['kick_with_made'] / max(1, t['kick_with']) * 100:.0f}% made), "
              f"into it {t['kick_into']} "
              f"({t['kick_into_made'] / max(1, t['kick_into']) * 100:.0f}% made)")
        for leg in ("with", "into"):
            print(f"  punts {leg} the wind: {t[f'punt_{leg}']}, "
                  f"avg {t[f'punt_{leg}_yds'] / max(1, t[f'punt_{leg}']):.1f} yds")


if __name__ == "__main__":
    main()
