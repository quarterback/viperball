#!/usr/bin/env python3
"""CCH-04: matched full engine games across team installation states.

Same Boot Raid roster, opponent, head coach, vertical attack OC, weather and
seeds in every condition. Only the team's installation record changes:

  none          no record (CCH-02 alone)
  new_hire      OC familiarity 0.30, a run first predecessor's trace at 0.45
  year_two      OC familiarity 0.50, the trace faded to 0.18
  established   OC familiarity 1.0, book 1.0, no trace, no packages
  packages      established plus Heavy Push and Quick Kick Chain at 1.0

`established` must replay `none` exactly. Usage:
    python scripts/benchmark_team_installation.py --games 80
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
from engine.coach_tactics import OFFENSIVE_ARCHETYPES, ensure_coach_tactical_profile  # noqa: E402
from engine.game_engine import ViperballEngine, load_team_from_json  # noqa: E402
from engine import team_installation as ti  # noqa: E402

KEYS = ("formation_bias", "family_bias", "kick_pass_bias")


def coach(cid, role, archetype=None):
    c = CoachCard(
        coach_id=cid, first_name="Test", last_name=cid, age=47, gender="female",
        role=role, classification="scheme_master", instincts=76, leadership=72,
        composure=70, rotations=65, development=65, recruiting=65,
        personality_sliders={"aggression": 70, "risk_tolerance": 70, "chaos_appetite": 60,
                             "tempo_preference": 67, "stubbornness": 25, "player_trust": 75,
                             "adaptability": 72})
    if archetype:
        p = ensure_coach_tactical_profile(c)
        tpl = OFFENSIVE_ARCHETYPES[archetype]
        p["identity"]["offense_interpretation"] = archetype
        p["offense"] = {**{k: dict(tpl[k]) for k in KEYS}, "featured_position": tpl["featured_position"]}
    return c


def records(offense_name, staff):
    base = ti.new_installation(offense_name, staff, "boot_raid", "balanced", 2026)
    old = {k: dict(OFFENSIVE_ARCHETYPES["run_to_kick"][k]) for k in KEYS}

    def with_(fam, trace, packages=()):
        r = deepcopy(base)
        r["offense"].update(familiarity=fam, family_familiarity=1.0, packages=[
            {"package_id": p, "familiarity": 1.0} for p in packages])
        r["offense"]["vestigial"] = ([{"coach_id": "oc-old", "signature": "run_to_kick",
                                       "weight": trace, "bias": old}] if trace else [])
        return r

    return {
        "none": None,
        "new_hire": with_(0.30, 0.45),
        "year_two": with_(0.50, 0.18),
        "established": with_(1.0, 0.0),
        "packages": with_(1.0, 0.0, ("gp_heavy_push", "ec_quick_kick_chain")),
    }


def simulate(games, seed):
    random.seed(seed)
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    offense = load_team_from_json(str(paths[0]), fresh=False)
    defense = load_team_from_json(str(paths[1]), fresh=False)
    staff = {"head_coach": coach("shared-head-coach", "head_coach"),
             "oc": coach("oc-deep", "oc", "vertical_attack")}
    out = {}
    for label, rec in records(offense.name, staff).items():
        stat = defaultdict(Counter)
        situ = defaultdict(Counter)
        scores = []
        logs = []
        for n in range(games):
            a, b = deepcopy(offense), deepcopy(defense)
            a.installation = deepcopy(rec)
            r = ViperballEngine(a, b, seed=seed + n, home_coaching=deepcopy(staff),
                                style_overrides={a.name: "boot_raid", b.name: "balanced"},
                                weather="clear", neutral_site=True).simulate_game()
            scores.append(r["final_score"]["home"]["score"])
            logs.append([p["description"] for p in r["play_by_play"]])
            sel = r["coach_tactics"]["home"].get("selected", {})
            for field, counts in sel.items():
                if isinstance(counts, dict):
                    stat[field].update(counts)
            hs = as_ = 0
            for p in r["play_by_play"]:
                fam = p.get("play_family")
                if p.get("possession") == "home" and fam not in (None, "punt", "snap_kick", "field_goal"):
                    live = ti.active_situations({
                        "down": p.get("down", 1), "yards_to_go": p.get("yards_to_go", 20),
                        "field_position": p.get("field_position", 25), "quarter": p.get("quarter", 1),
                        "time_remaining": p.get("time_remaining", 900), "score_diff": hs - as_})
                    for tag in ("short_yardage", "long_yardage"):
                        if tag in live:
                            situ[tag][fam] += 1
                hs, as_ = p.get("home_score", hs), p.get("away_score", as_)
        out[label] = {"mean_points": round(statistics.mean(scores), 2), "scores": scores,
                      "selected": {k: dict(v) for k, v in stat.items()},
                      "by_situation": {k: dict(v) for k, v in situ.items()}, "_logs": logs}
    return out


def share(counts, key):
    total = sum(counts.values())
    return round(counts.get(key, 0) / total, 4) if total else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=80)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--out", default="reports/cch04")
    args = ap.parse_args()
    res = simulate(args.games, args.seed)
    if res["established"]["_logs"] != res["none"]["_logs"]:
        raise AssertionError("A fully installed team must replay the no record games exactly")
    for v in res.values():
        v.pop("_logs")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"seed": args.seed, "games": args.games, "results": res},
                                                 indent=2), encoding="utf8")
    print(f"CCH-04, {args.games} matched games per condition, Boot Raid, vertical attack OC, seed {args.seed}")
    print("established replays none exactly: yes")
    hdr = f"{'condition':12}{'points':>8}{'spread':>8}{'heavy':>8}{'kick_pass':>10}{'power':>8}{'bomb':>7}{'quick':>7}{'SY run':>9}{'LY kick':>8}"
    print(hdr)
    for label, v in res.items():
        s = v["selected"]
        sy = v["by_situation"].get("short_yardage", {})
        ly = v["by_situation"].get("long_yardage", {})
        sy_power = (share(sy, "power") or 0) + (share(sy, "dive_option") or 0)
        ly_kick = share(ly, "kick_pass") or 0
        print(f"{label:12}{v['mean_points']:>8.2f}{share(s.get('formation', {}), 'spread') or 0:>8.3f}"
              f"{share(s.get('formation', {}), 'heavy') or 0:>8.3f}{share(s.get('family', {}), 'kick_pass') or 0:>10.3f}"
              f"{share(s.get('family', {}), 'power') or 0:>8.3f}{share(s.get('kick_pass', {}), 'bomb') or 0:>7.3f}"
              f"{share(s.get('kick_pass', {}), 'quick_kick') or 0:>7.3f}{sy_power:>9.3f}{ly_kick:>8.3f}")
    pk = res["packages"]["selected"].get("packages", {})
    print("package activations (plays):", pk)


if __name__ == "__main__":
    main()
