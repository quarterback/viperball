#!/usr/bin/env python3
"""Cross code concepts study (engine/cross_code.py).

Offense: for each new offensive call, games where the home team runs the
call's origin school with only that package installed at full familiarity,
against a defense that is not one of its listed counters. Reports how often
it was selected, its branches, and yards and turnovers on its snaps.

Defense: for each new defensive answer, paired games with the same teams,
staffs, weather and seed, with the package installed or not, against an
offense running the call it answers. Reports what the package did and the
offense's yards per snap on the targeted call in both arms.

    python3 scripts/study_cross_code.py --games 20
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_defensive_coaches import coach, dc_variant  # noqa: E402
from engine import cross_code as XC  # noqa: E402
from engine.game_engine import ViperballEngine, load_team_from_json  # noqa: E402
from engine.playbook_catalog import get_package  # noqa: E402
from engine.team_installation import new_installation  # noqa: E402

TURNOVERS = {"kick_pass_intercepted", "lateral_intercepted", "int_return_td", "fumble"}
# The offensive call each defensive answer is built to meet.
TARGET = {
    XC.D_EXCHANGE: (XC.FM_SWITCHBACK, "ghost"),
    XC.D_STAGGER: (XC.RL_UP_BACK_ACROSS, "east_coast"),
    XC.D_EDGE_ANCHOR: ("cape_cod_hook", "lateral_spread"),
    XC.D_SLIDE_REPLACE: (XC.CF_PIVOT_TURN, "ghost"),
    XC.D_CHANNEL_PRESS: (XC.FM_MIRROR_FLOOD, "lateral_spread"),
    XC.D_TRANSITION_NET: (XC.RL_WALL_RETURN, "east_coast"),
    XC.D_CROSS_RUSH: (XC.CF_HANDOFF_PUNISH, "mousetrap"),
    XC.D_SET_BREAKER: (XC.CF_SAME_LOOK_REVERSE, "ghost"),
}


def snaps(game, side, pid):
    rows = Counter()
    for play in game["play_by_play"]:
        call = play.get("offensive_call") or {}
        if (play.get("snap_possession") == side and not call.get("package_id")
                and play.get("play_type") in ("run", "kick_pass", "lateral_chain", "trick_play")):
            rows["base_snaps"] += 1
            rows["base_yards"] += play.get("yards") or 0
            rows["base_turnovers"] += int(play.get("result") in TURNOVERS)
        if call.get("offense_side") != side or call.get("package_id") != pid:
            continue
        rows["snaps"] += 1
        branch = (call.get("cross") or {}).get("branch")
        if branch:
            rows["b_snaps:" + branch] += 1
            rows["b_yards:" + branch] += play.get("yards") or 0
        rows["yards"] += play.get("yards") or 0
        rows["res:" + str(play.get("result"))] += 1
        rows["turnovers"] += int(play.get("result") in TURNOVERS)
        rows["first_down_or_td"] += int(play.get("result") in ("first_down", "touchdown"))
        if (call.get("design") or {}).get("family"):
            rows["designed"] += 1
    return rows


def play(home, away, seed, home_staff, away_staff, styles, weather):
    random.seed(seed)
    return ViperballEngine(deepcopy(home), deepcopy(away), seed=seed, neutral_site=True,
                           weather=weather, home_coaching=deepcopy(home_staff),
                           away_coaching=deepcopy(away_staff),
                           style_overrides=styles).simulate_game()


def offense_study(teams, names, games, seed):
    out = {}
    for pid in sorted(XC.OFFENSE):
        pkg = get_package(pid)
        style = pkg["origin_family"]
        counters = set(pkg["countered_by"])
        pool = [d for d in ("rotation", "lockdown", "fortress", "chaos", "drift", "swarm",
                            "shadow", "blitz_pack", "keeper_hunt", "predator") if d not in counters]
        # Handoff Punish needs earlier switches to scout, so it travels with Slip Cross.
        installed = ([XC.CF_SLIP_CROSS, pid] if pid == XC.CF_HANDOFF_PUNISH else [pid])
        total, branches = Counter(), Counter()
        for n in range(games):
            defense = pool[n % len(pool)]
            home = teams[names[(n * 7 + len(pid)) % len(names)]]
            away = teams[names[(n * 11 + 3) % len(names)]]
            if away.name == home.name:
                away = teams[names[(names.index(away.name) + 1) % len(names)]]
            staff = {"head_coach": coach("xc-hc", "head_coach"), "oc": coach("xc-oc", "oc")}
            opp = {"head_coach": coach("xc-away-hc", "head_coach"),
                   "dc": dc_variant("run_wall" if n % 2 == 0 else "selective_pressure")}
            h = deepcopy(home)
            rec = new_installation(h.name, staff, style, defense, 2026)
            rec["offense"].update(familiarity=1.0, family_familiarity=1.0,
                                  packages=[{"package_id": x, "familiarity": 1.0} for x in installed])
            h.installation = rec
            game = play(h, away, seed + n, staff, opp,
                        {h.name: style, away.name + "_defense": defense}, ("clear", "rain")[n % 2])
            total.update(snaps(game, "home", pid))
            branches.update(game["cross_code"]["home"]["offense"].get(pid, {}))
        s = total["snaps"]
        out[pid] = {"style": style, "defenses": pool, "games": games, "snaps": s,
                    "designed": total["designed"],
                    "yards_per_snap": round(total["yards"] / s, 2) if s else None,
                    "turnover_rate": round(total["turnovers"] / s, 3) if s else None,
                    "first_down_or_td_rate": round(total["first_down_or_td"] / s, 3) if s else None,
                    "base_yards_per_snap": (round(total["base_yards"] / total["base_snaps"], 2)
                                            if total["base_snaps"] else None),
                    "base_turnover_rate": (round(total["base_turnovers"] / total["base_snaps"], 3)
                                           if total["base_snaps"] else None),
                    "branches": {b: {"snaps": total["b_snaps:" + b],
                                     "yards_per_snap": round(total["b_yards:" + b] / total["b_snaps:" + b], 2)
                                     if total["b_snaps:" + b] else None} for b in sorted(branches)}}
        print("OFFENSE", pid, json.dumps(out[pid]), flush=True)
    return out


def defense_study(teams, names, games, seed):
    out = {}
    for pid in sorted(XC.DEFENSE):
        pkg = get_package(pid)
        dstyle = pkg["origin_family"]
        target, ostyle = TARGET[pid]
        arms = {}
        for arm in ("control", "installed"):
            total, mech = Counter(), Counter()
            for n in range(games):
                attack = teams[names[(n * 5 + 1) % len(names)]]
                defend = teams[names[(n * 13 + len(pid)) % len(names)]]
                if attack.name == defend.name:
                    defend = teams[names[(names.index(defend.name) + 1) % len(names)]]
                a_staff = {"head_coach": coach("xc-hc", "head_coach"), "oc": coach("xc-oc", "oc")}
                d_staff = {"head_coach": coach("xc-away-hc", "head_coach"),
                           "dc": dc_variant("run_wall" if n % 2 == 0 else "selective_pressure")}
                a, d = deepcopy(attack), deepcopy(defend)
                a_rec = new_installation(a.name, a_staff, ostyle, "swarm", 2026)
                a_rec["offense"].update(familiarity=1.0, family_familiarity=1.0,
                                        packages=[{"package_id": target, "familiarity": 1.0}])
                a.installation = a_rec
                d_rec = new_installation(d.name, d_staff, "ghost", dstyle, 2026)
                d_rec["defense"].update(familiarity=1.0, family_familiarity=1.0,
                                        packages=([{"package_id": pid, "familiarity": 1.0}]
                                                  if arm == "installed" else []))
                d.installation = d_rec
                game = play(a, d, seed + n, a_staff, d_staff,
                            {a.name: ostyle, d.name + "_defense": dstyle}, ("clear", "rain")[n % 2])
                total.update(snaps(game, "home", target))
                mech.update(game["cross_code"]["away"]["defense"].get(pid, {}))
                sel = game["defensive_coach_tactics"]["away"]["packages"]["selected"].get(pid, 0)
                mech["selected_snaps"] += sel
                st = game["stats"]["home"]
                total["points"] += game["final_score"]["home"]["score"]
                total["team_yards"] += st["total_yards"]
            s = total["snaps"]
            arms[arm] = {"target_snaps": s,
                         "target_yards_per_snap": round(total["yards"] / s, 2) if s else None,
                         "target_turnover_rate": round(total["turnovers"] / s, 3) if s else None,
                         "offense_points_per_game": round(total["points"] / games, 2),
                         "offense_yards_per_game": round(total["team_yards"] / games, 1),
                         "mechanics": dict(mech)}
        out[pid] = {"defense_style": dstyle, "target": target, "offense_style": ostyle,
                    "games": games, **arms}
        print("DEFENSE", pid, json.dumps(out[pid]), flush=True)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=20)
    p.add_argument("--seed", type=int, default=20261128)
    p.add_argument("--only", choices=("offense", "defense"), default=None)
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    teams = {}
    for f in sorted((ROOT / "data" / "teams").glob("*.json")):
        t = load_team_from_json(str(f), fresh=True)
        teams[t.name] = t
    names = sorted(teams)
    report = {"games": a.games, "seed": a.seed}
    if a.only in (None, "offense"):
        report["offense"] = offense_study(teams, names, a.games, a.seed)
    if a.only in (None, "defense"):
        report["defense"] = defense_study(teams, names, a.games, a.seed)
    if a.out:
        a.out.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
