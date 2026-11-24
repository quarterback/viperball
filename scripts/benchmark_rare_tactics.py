#!/usr/bin/env python3
"""Rare tactics: observe natural eligibility, then replay matched pre-snap states.

The production game is never forced. Experimental forks fix a legal
scrimmage response AFTER the DC call; they are single-snap experiments,
not season frequencies or independent full-game results.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import random
from benchmark_defensive_coaches import ROOT, coach, dc_variant
from benchmark_defensive_packages import summarize_rush
from engine.game_engine import (ViperballEngine, load_team_from_json,
    PlayFamily, KickPassSubFamily, PLAY_FAMILY_TO_TYPE)
from engine.team_installation import new_installation, active_situations
from engine.defensive_commitments import eligibility
from engine.playbook_catalog import get_package

CASES = [
    ("kick_in", "predator", "afl_kick_in_press", "boot_raid"),
    ("ride", "chaos", "lax_ride", "boot_raid"),
    ("exhaustion", "predator", "predator_exhaustion_press", "boot_raid"),
    ("overload", "blitz_pack", None, "boot_raid"),
]
RESPONSES = [(PlayFamily.KICK_PASS, KickPassSubFamily.QUICK_KICK),
             (PlayFamily.KICK_PASS, KickPassSubFamily.TERRITORY),
             (PlayFamily.KICK_PASS, KickPassSubFamily.BOMB),
             (PlayFamily.POWER, None), (PlayFamily.SPEED_OPTION, None)]

class AlwaysActivate:
    """Experimental selection stream: one installed eligible package only."""
    def random(self):
        return 0.0
    def choices(self, population, weights=None, k=1):
        return [population[0]] * k

def urgent(context):
    return ((context["quarter"] >= 3 and context["score_diff"] <= -9)
            or (context["down"] >= 5 and context["yards_to_go"] <= 8))

class ProbeEngine(ViperballEngine):
    # Collector belongs to the study, not the engine being copied.
    collector = None
    forced_subfamily = None
    probe_package_mode = None

    def _choose_defensive_package(self, side, tactics, situations=None, context=None):
        if self.probe_package_mode == "off":
            return None
        return super()._choose_defensive_package(side, tactics, situations, context)

    def _select_kick_pass_subfamily(self, kicker):
        if self.forced_subfamily is not None:
            return self.forced_subfamily
        return super()._select_kick_pass_subfamily(kicker)

    def _begin_defensive_call(self, formation):
        if self.state.possession == "home" and self.collector is not None:
            self.collector.observe(self, formation)
        super()._begin_defensive_call(formation)

class Study:
    def __init__(self, case, package, cap):
        self.case, self.package, self.cap = case, package, cap
        self.natural = Counter()
        self.taken = Counter()
        self.per_game = Counter()
        self.groups = defaultdict(Counter)
        self.pairs = defaultdict(Counter)
        self.primary_tags = get_package(package)["situation_tags"] if package else []

    def observe(self, engine, formation):
        state = engine.state
        context = engine._package_context(state.away_score-state.home_score)
        tags = active_situations(context)
        tier = eligibility(self.package, tags, context, self.primary_tags) if self.package else 0
        self.natural["scrimmage_calls"] += 1
        if tier:
            self.natural["primary_eligible" if tier == 1 else "secondary_eligible"] += 1
        if urgent(context):
            self.natural["urgent_eligible"] += 1
        if self.case == "overload":
            if urgent(context):
                self.probe(engine, formation, "urgent")
            return
        if tier:
            self.probe(engine, formation, "primary" if tier == 1 else "secondary")
        # Exhaustion is rare with the rotating XI. Replay real early-down
        # formations at controlled energy levels; keep these distinct from
        # the natural sample, with identical energy in both arms.
        if self.case == "exhaustion" and "early_down" in tags:
            self.probe(engine, formation, "controlled_tired_offense", energy=65)
        if self.case == "exhaustion" and context["drive_play_index"] <= 3:
            self.probe(engine, formation, "controlled_moderate_offense", energy=78)
        # Compare defender readiness at identical offensive energy and
        # source states; these are enriched replays, not natural calls.
        if self.case == "exhaustion" and "early_down" in tags:
            for oe in (65, 72):
                for de in (90, 65, 50):
                    self.probe(engine, formation, f"relative_{oe}_{de}",
                               energy=oe, defense_energy=de)

    def probe(self, engine, formation, scenario, energy=None, defense_energy=None):
        if self.taken[scenario] >= self.cap or self.per_game[scenario] >= 4:
            return
        n = self.taken[scenario]
        options = RESPONSES[:3] if self.case == "overload" else RESPONSES
        family, subtype = options[n % len(options)]
        response = subtype.value if subtype else family.value
        rng_state = random.getstate()
        try:
            results = {}
            for arm in (("2","4","6") if self.case == "overload" else ("off","on")):
                clone = deepcopy(engine)
                random.setstate(rng_state)
                clone._lineup_cache = {}
                if energy is not None:
                    for p in clone.home_team.players:
                        p.game_energy = float(energy)
                if defense_energy is not None:
                    for p in clone.away_team.players:
                        p.game_energy = float(defense_energy)
                clone.probe_package_mode = "off" if arm == "off" else None
                if arm == "on":
                    clone._defensive_package_rng["away"] = AlwaysActivate()
                # Call the real resolver without re-entering the collector.
                ViperballEngine._begin_defensive_call(clone, formation)
                call = clone._active_dc_call()
                if arm == "on" and call.get("package_id") != self.package:
                    raise RuntimeError("Forced eligible package failed to activate")
                if self.case == "overload":
                    call["intended_rushers"] = int(arm)
                    call["blitz"] = int(arm) >= 3
                # Fixed response is applied only after the pre-snap call.
                clone.forced_subfamily = subtype
                clone._play_start_possession = clone.state.possession
                clone._credit_snap_counts()
                before = sum(p.game_energy for p in clone.away_team.players)
                play = clone._dispatch_play(PLAY_FAMILY_TO_TYPE[family], family)
                after = sum(p.game_energy for p in clone.away_team.players)
                rush = clone._rush_event or {}
                g = self.groups[(scenario, response, arm)]
                g["snaps"] += 1
                g["yards"] += play.yards_gained
                g["explosives"] += int(play.yards_gained >= 30)
                g["defense_energy_loss_milli"] += round(1000*(before-after))
                g["turnovers"] += int(clone.state.possession != "home")
                if rush:
                    summarize_rush(g, rush)
                    g["intended_rushers"] += rush["intended_rusher_count"]
                    for field in ("rusher_energy", "blocker_energy", "rush_skill",
                                  "protection_skill", "sack_probability",
                                  "completion_before", "package_coverage_delta",
                                  "coverage_cost"):
                        value = rush.get(field)
                        if value is not None:
                            g[field + "_observations"] += 1
                            g[field + "_milli"] += round(1000 * value)
                    if rush.get("rusher_energy") is not None and rush.get("blocker_energy") is not None:
                        g["relative_energy_observations"] += 1
                        g["relative_energy_milli"] += round(1000 * (
                            rush["rusher_energy"] - rush["blocker_energy"]))
                results[arm] = (play.yards_gained, int(rush.get("pressure", False)),
                                int(rush.get("completed", False)), before-after)
            base = "2" if self.case == "overload" else "off"
            for arm, values in results.items():
                if arm == base:
                    continue
                d = self.pairs[(scenario,response,arm)]
                d["pairs"] += 1
                for i, key in enumerate(("yards", "pressure", "completion", "energy_loss")):
                    diff = values[i] - results[base][i]
                    scale = 1000 if key == "energy_loss" else 1
                    d[key+"_delta"] += round(diff*scale)
                    d[key+"_delta_sq"] += round(diff*diff*scale*scale)
            self.taken[scenario] += 1
            self.per_game[scenario] += 1
        finally:
            random.setstate(rng_state)

    def finish(self):
        return {"natural": dict(self.natural), "sampled": dict(self.taken),
                "groups": {"|".join(k): dict(v) for k,v in self.groups.items()},
                "paired": {"|".join(k): dict(v) for k,v in self.pairs.items()}}

def run(games, cap, seed):
    random.seed(seed)
    paths = sorted((ROOT / "data" / "teams").glob("*.json"))
    teams = [load_team_from_json(str(paths[i]), fresh=False)
             for i in (0, 1, len(paths)//2, len(paths)//2+1)]
    out = {}
    for case,scheme,package,attack in CASES:
        study = Study(case, package, cap)
        ProbeEngine.collector = study
        for n in range(games):
            study.per_game.clear()
            i = 2*(n%2)
            a,b = deepcopy(teams[i]),deepcopy(teams[i+1])
            staff = {"head_coach":coach("rare-hc","head_coach"),
                     "dc":dc_variant("run_wall" if (n//2)%2 == 0 else "selective_pressure")}
            rec = new_installation(b.name, staff, attack, scheme, 2026)
            rec["defense"].update(familiarity=1.0, family_familiarity=1.0,
                packages=[{"package_id":package,"familiarity":1.0}] if package else [])
            b.installation = rec
            game = ProbeEngine(a,b,seed=seed+n,neutral_site=True,weather="clear",
                 away_coaching=staff,style_overrides={a.name:attack,b.name+"_defense":scheme}).simulate_game()
            dc = game["defensive_coach_tactics"]["away"]
            study.natural["activated"] += dc["packages"]["selected"].get(package,0)
            study.natural["secondary_activated"] += dc["packages"].get("secondary_selected",{}).get(package,0)
            study.natural["actual_six_attempts"] += game["defensive_rush"]["away"]["by_count"].get("6",{}).get("attempts",0)
        ProbeEngine.collector = None
        out[case] = study.finish()
        print(case, "natural", study.natural, "sampled", study.taken, flush=True)
    return out

def report(result):
    for case, data in result.items():
        print("CASE", case)
        for key,g in sorted(data["groups"].items()):
            n = g["snaps"]
            attempts = g.get("attempts",0)
            def rate(field, denom):
                return round(g.get(field,0)/denom,4) if denom else None
            print(key, "n",n,"yards",rate("yards",n),
                  "pressure",rate("pressure",attempts),"sack",rate("sack",attempts),
                  "complete",rate("completions",attempts),
                  "released_completion",rate("completions",attempts-g.get("sack",0)),
                  "rushers",rate("rushers",attempts),
                  "energy_loss",round(g.get("defense_energy_loss_milli",0)/n/1000,3),
                  "explosive",rate("explosives",n),
                  "rusher_energy",rate("rusher_energy_milli",1000*g.get("rusher_energy_observations",0)),
                  "blocker_energy",rate("blocker_energy_milli",1000*g.get("blocker_energy_observations",0)),
                  "sack_probability",rate("sack_probability_milli",1000*g.get("sack_probability_observations",0)),
                  "coverage_cost",rate("coverage_cost_milli",1000*g.get("coverage_cost_observations",0)))
        for key,g in sorted(data["paired"].items()):
            n = g["pairs"]
            print("PAIR",key,"n",n, "yards_delta",round(g["yards_delta"]/n,3),
                  "pressure_delta",round(g["pressure_delta"]/n,4),
                  "completion_delta",round(g["completion_delta"]/n,4))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--games",type=int,default=48)
    p.add_argument("--cap",type=int,default=120)
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--out",default="reports/rare-defense")
    args = p.parse_args()
    result = run(args.games,args.cap,args.seed)
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"rare_results.json").write_text(json.dumps({"seed":args.seed,
        "natural_games_per_case":args.games,"cap":args.cap,"results":result},indent=2))
    report(result)
