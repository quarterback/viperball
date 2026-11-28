#!/usr/bin/env python3
"""PBK-06: paired full-engine offensive package policy calibration.

For each legal roster/package fit, compare the same roster, staff, opponent,
weather and seed with one installed plan enabled or suppressed. No forced
calls, no production coefficient changes. Whole-game paired effects include
downstream changes in game state; eligible-snap splits are observational.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

from benchmark_defensive_coaches import ROOT, coach, dc_variant
from engine.game_engine import ViperballEngine, load_team_from_json
from engine.playbook_catalog import packages_for_roster
from engine.team_installation import league_roster_profiles, new_installation

TURNOVERS = {"turnover_on_downs", "kick_pass_intercepted", "lateral_intercepted",
             "int_return_td", "fumble"}
METRICS = ("points", "points_allowed", "margin", "yards", "touchdowns",
           "fumbles_lost", "kick_pass_interceptions", "eligible", "selected",
           "eligible_resolved", "eligible_yards", "eligible_explosives",
           "eligible_turnover_results", "eligible_first_down_or_td",
           "eligible_kick_attempts", "eligible_completions", "eligible_sacks",
           "eligible_penalty_nullified", "eligible_family_target",
           "eligible_formation_target", "eligible_subtype_target",
           "eligible_subtype_evaluated")

class ControlEngine(ViperballEngine):
    """Keep eligibility instrumentation and package RNG; suppress only plan bias."""
    def _begin_offensive_plan(self, action=None):
        super()._begin_offensive_plan(action)
        if self.state.possession == "home" and self._offensive_plan_event:
            self._active_offensive_plan = None
            self._drive_plan_trace = None
            self._offensive_plan_event["package_id"] = None
            self._offensive_plan_event.pop("familiarity", None)

    def _package_snap_kick_shift(self, kicker, score_diff):
        if self.state.possession == "home":
            return 0.0
        return super()._package_snap_kick_shift(kicker, score_diff)

def divide(a, b):
    return round(a / b, 4) if b else None

def measure(game, pkg, enabled):
    pid = pkg["package_id"]
    counts = Counter()
    stats = game["stats"]["home"]
    points = game["final_score"]["home"]["score"]
    allowed = game["final_score"]["away"]["score"]
    counts.update(points=points, points_allowed=allowed, margin=points-allowed,
                  yards=stats["total_yards"], touchdowns=stats["touchdowns"],
                  fumbles_lost=stats["fumbles_lost"],
                  kick_pass_interceptions=stats["kick_pass_interceptions"])
    observed = {"selected": Counter(), "ordinary": Counter()}
    situations = {}
    for play in game["play_by_play"]:
        call = play.get("offensive_call") or {}
        if call.get("offense_side") != "home" or pid not in call.get("eligible", []):
            continue
        selected = call.get("package_id")
        if selected not in (None, pid) or (selected and not enabled):
            raise RuntimeError("Unexpected experimental package selection")
        counts["eligible"] += 1
        counts["selected"] += int(bool(selected))
        bucket = observed["selected" if selected else "ordinary"]
        key = "|".join(sorted(call.get("situations", [])))
        situation = situations.setdefault(key, Counter())
        choice = call.get("choices", {})
        for row in (bucket, situation):
            row["eligible"] += 1
            row["selected"] += int(bool(selected))
            for field, tags, name in (
                ("formation", "formation_tags", "formation_target"),
                ("family", "play_family_tags", "family_target"),
                ("kick_pass", "kick_pass_tags", "subtype_target"),
            ):
                if field in choice and pkg[tags]:
                    row[name+"_evaluated"] += 1
                    row[name] += int(choice[field] in pkg[tags])
            if (play.get("penalty") or {}).get("nullified"):
                row["penalty_nullified"] += 1
                continue
            y = play.get("yards") or 0
            result = play.get("result")
            row["resolved"] += 1
            row["yards"] += y
            row["explosives"] += int(y >= 30)
            row["turnover_results"] += int(result in TURNOVERS)
            row["first_down_or_td"] += int(result in ("first_down", "touchdown"))
            rush = play.get("rush_event") or {}
            if rush:
                row["kick_attempts"] += 1
                row["completions"] += int(rush["completed"])
                row["sacks"] += int(rush["outcome"] == "sack")
    summary = game["coach_tactics"]["home"]["selected"]
    if counts["eligible"] != summary.get("packages_eligible", {}).get(pid, 0):
        raise RuntimeError("Eligibility ledger mismatch")
    if counts["selected"] != summary.get("packages", {}).get(pid, 0):
        raise RuntimeError("Selection ledger mismatch")
    for bucket in observed.values():
        for name, value in bucket.items():
            if name not in ("eligible", "selected"):
                counts["eligible_"+name] += value
    return dict(counts), {k:dict(v) for k,v in observed.items()}, {
        k:dict(v) for k,v in situations.items()}

def paired_summary(rows):
    result = {}
    for key in METRICS:
        diffs = [r["enabled"].get(key, 0)-r["control"].get(key, 0) for r in rows]
        n = len(diffs)
        result[key] = {"pairs": n, "mean_delta": divide(sum(diffs), n),
                       "paired_sd": round(statistics.stdev(diffs), 4) if n > 1 else None,
                       "min": min(diffs) if n else None, "max": max(diffs) if n else None}
    for arm in ("enabled", "control"):
        totals = Counter()
        for row in rows:
            totals.update(row[arm])
        result[arm] = {"totals": dict(totals),
            "selection_rate": divide(totals["selected"], totals["eligible"]),
            "yards_per_resolved_eligible_snap": divide(totals["eligible_yards"], totals["eligible_resolved"]),
            "explosive_rate": divide(totals["eligible_explosives"], totals["eligible_resolved"]),
            "turnover_result_rate": divide(totals["eligible_turnover_results"], totals["eligible_resolved"]),
            "conversion_or_td_rate": divide(totals["eligible_first_down_or_td"], totals["eligible_resolved"]),
            "completion_rate": divide(totals["eligible_completions"], totals["eligible_kick_attempts"]),
            "sack_rate": divide(totals["eligible_sacks"], totals["eligible_kick_attempts"]),
            "family_target_rate": divide(totals["eligible_family_target"], totals["eligible_family_target_evaluated"]),
            "formation_target_rate": divide(totals["eligible_formation_target"], totals["eligible_formation_target_evaluated"]),
            "subtype_target_rate": divide(totals["eligible_subtype_target"], totals["eligible_subtype_evaluated"])}
    return result

def run(seeds, seed, out):
    random.seed(seed)
    files = sorted((ROOT/"data"/"teams").glob("*.json"))
    teams = {}
    for f in files:
        t = load_team_from_json(str(f), fresh=True)
        teams[t.name] = t
    profiles = league_roster_profiles(teams)
    names = sorted(teams)
    fingerprint = hashlib.sha256(json.dumps(profiles, sort_keys=True).encode()).hexdigest()
    catalog = json.loads((ROOT/"data"/"playbooks"/"packages.json").read_text())["packages"]
    defenses = json.loads((ROOT/"data"/"playbooks"/"families.json").read_text())["defense"]
    report = {"seed":seed, "seeds_per_cell":seeds, "roster_profile_sha256":fingerprint,
              "rosters":len(teams), "complete":False, "packages":{}}
    out.mkdir(parents=True, exist_ok=True)
    def checkpoint():
        (out/"offensive_calibration.json").write_text(json.dumps(report, indent=2))
    for pkg in (p for p in catalog if p["side"] == "offense"):
        pid = pkg["package_id"]
        native = pkg["origin_family"]
        borrowed = "balanced" if "balanced" in pkg["compatible_families"] and native != "balanced" else next(
            f for f in pkg["compatible_families"] if f != native)
        counters = [d for d in pkg["countered_by"] if d in defenses]
        noncounter = next(d for d in sorted(defenses) if d not in counters)
        cells = {}
        all_rows = []
        for style, origin in ((native, "native"), (borrowed, "borrowed")):
            eligible = [n for n in names if any(
                p["package_id"] == pid and p["meets_personnel"]
                for p in packages_for_roster("offense", style, profiles[n]))]
            if not eligible:
                cells[origin] = {"status":"no fitting roster"}
                continue
            for defense, matchup in ((counters[0], "catalog_counter"), (noncounter, "noncounter")) if counters else ((noncounter, "noncounter"),):
                rows = []
                for n in range(seeds):
                    # Rotate fitted rosters and opponents without choosing by outcome.
                    index = int(hashlib.sha256(f"{pid}:{n}".encode()).hexdigest()[:8],16)
                    home_name = eligible[index % len(eligible)]
                    away_name = names[(index//len(eligible)) % len(names)]
                    if away_name == home_name:
                        away_name = names[(names.index(away_name)+1)%len(names)]
                    staff = {"head_coach":coach("pbk-hc","head_coach"),
                             "oc":coach("pbk-oc","oc")}
                    opposition = {"head_coach":coach("pbk-away-hc","head_coach"),
                                  "dc":dc_variant("run_wall" if n%2 == 0 else "selective_pressure")}
                    home, away = deepcopy(teams[home_name]), deepcopy(teams[away_name])
                    rec = new_installation(home.name,staff,style,noncounter,2026)
                    familiarity = (.65, 1.0)[n%2]
                    rec["offense"].update(familiarity=1.0, family_familiarity=1.0,
                        packages=[{"package_id":pid,"familiarity":familiarity}])
                    home.installation = rec
                    weather = ("clear", "rain")[n%2]
                    row = {"seed":seed+n, "home":home_name, "away":away_name,
                           "style":style, "defense":defense, "weather":weather,
                           "familiarity":familiarity}
                    for arm, engine in (("control", ControlEngine), ("enabled", ViperballEngine)):
                        random.seed(seed+n)
                        game = engine(deepcopy(home),deepcopy(away),seed=seed+n,
                            neutral_site=True,weather=weather,home_coaching=deepcopy(staff),
                            away_coaching=deepcopy(opposition),style_overrides={
                                home.name:style,away.name+"_defense":defense}).simulate_game()
                        row[arm], row[arm+"_observed"], row[arm+"_situations"] = measure(
                            game,pkg,arm=="enabled")
                    rows.append(row)
                cell = origin+"|"+matchup
                cells[cell] = {"status":"measured", "rows":rows, "summary":paired_summary(rows)}
                all_rows.extend(rows)
        report["packages"][pid] = {"catalog":pkg, "cells":cells, "summary":paired_summary(all_rows)}
        checkpoint()
        print("PACKAGE",pid,"pairs",len(all_rows),"summary",json.dumps(report["packages"][pid]["summary"]),flush=True)
    report["complete"] = True
    checkpoint()
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,default=2,help="paired games per package/family/matchup cell")
    p.add_argument("--seed",type=int,default=20261125)
    p.add_argument("--out",type=Path,default=Path("reports/offensive-calibration"))
    a = p.parse_args()
    if a.seeds < 1:
        p.error("at least one seed is required")
    run(a.seeds,a.seed,a.out)
