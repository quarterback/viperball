#!/usr/bin/env python3
"""Three-season tactical calibration using the playable college dynasty API.

Small real-program league, normal full-engine schedule, recruiting, portal,
coaching carousel, and database reloads. No forced installs or tactical calls.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def average(values):
    return round(statistics.mean(values),4) if values else None

def identity(p):
    return p.player_id or p.name

def snapshot(teams):
    return {name:{identity(p):{"name":p.name,"position":p.position,"year":p.year,
        "speed":p.speed,"stamina":p.stamina,"tackling":p.tackling,
        "awareness":p.awareness,"power":p.power,"work_rate":p.work_rate_rating}
        for p in t.players} for name,t in teams.items()}

def staff_ids(dyn):
    return {t: {role:c.coach_id for role,c in s.items()} for t,s in dyn._coaching_staffs.items()}

def add_play(bucket, play):
    bucket["snaps"] += 1
    y = play.get("yards") or 0
    bucket["yards"] += y
    bucket["explosives"] += int(y>=30)
    r = play.get("rush_event") or {}
    if r:
        bucket["kick_attempts"] += 1
        bucket["pressure"] += int(r["pressure"])
        bucket["sacks"] += int(r["outcome"]=="sack")
        bucket["hurries"] += int(r["outcome"]=="hurry")
        bucket["completions"] += int(r["completed"])
        bucket["rushers"] += r["rusher_count"]

def measure_game(game, year, groups, packages, teams, changes, fatigue, records):
    fr = game.full_result
    if not fr or "defensive_rush" not in fr:
        raise RuntimeError("Missing full-engine game result")
    scores = fr["final_score"]
    for side,name in (("home",game.home_team),("away",game.away_team)):
        if name not in teams:
            continue
        dc = fr["defensive_coach_tactics"][side]
        if not dc:
            raise RuntimeError("Active program without DC decisions: "+name)
        rec = records[name]["defense"]
        if dc["dc_id"] != rec["coach_id"]:
            raise RuntimeError("DC installation does not match game coach")
        g = groups["teams:"+name]
        g["games"] += 1
        g["calls"] += dc["calls"]
        g["points_allowed"] += scores["away" if side=="home" else "home"]["score"]
        factor = dc["installation_execution_factor"]
        g["execution_milli"] += round(1000*factor)
        cohort = "new_dc" if name in changes else "retained_dc"
        for key in ("cohort:"+cohort, "familiarity:"+("under_0.6" if factor<.6 else "0.6_to_0.85" if factor<.85 else "0.85_plus")):
            groups[key]["games"] += 1
            groups[key]["execution_milli"] += round(1000*factor)
            groups[key]["calls"] += dc["calls"]
            groups[key]["points_allowed"] += scores["away" if side=="home" else "home"]["score"]
            groups[key]["package_calls"] += sum(dc["packages"]["selected"].values())
            groups[key]["eligible_calls"] += sum(dc["packages"]["eligible"].values())
        for pid in ("eligible","selected","secondary_selected"):
            for pkg,n in dc["packages"].get(pid,{}).items():
                packages[pkg][pid] += n
        rush = fr["defensive_rush"][side]
        groups["rush_total"]["attempts"] += rush["attempts"]
        groups["rush_total"]["pressure"] += rush["pressures"]
        groups["rush_total"]["sacks"] += rush["sacks"]
        groups["rush_total"]["hurries"] += rush["hurries"]
        for count, values in rush["by_count"].items():
            groups["rush_count:"+count].update(values)
        for play in fr["play_by_play"]:
            call = play.get("defensive_call") or {}
            if call.get("defending_side") != side:
                continue
            context = call.get("tactical_context") or {}
            e = context.get("offense_energy")
            d = context.get("defense_energy")
            pid = call.get("package_id")
            if e is not None:
                key = "under_75" if e<75 else "75_to_82" if e<82 else "82_plus"
                add_play(groups["offense_energy:"+key],play)
                groups["offense_energy:"+key]["exhaustion_calls"] += int(pid=="predator_exhaustion_press")
            if d is not None:
                key = "under_75" if d<75 else "75_to_85" if d<85 else "85_plus"
                add_play(groups["defense_energy:"+key],play)
            if pid:
                add_play(packages[pid],play)
                packages[pid]["strength_milli"] += round(1000*call.get("package_strength",0))
                add_play(groups["selected:"+pid+":"+str(play.get("kick_pass_subfamily") or play.get("play_family"))],play)
            for key in ("cohort:"+cohort, "familiarity:"+("under_0.6" if factor<.6 else "0.6_to_0.85" if factor<.85 else "0.85_plus")):
                add_play(groups[key],play)

def roster_fit(season, records):
    from engine import playbook_catalog as pc
    from engine.team_installation import league_roster_profiles
    profiles = league_roster_profiles(season.teams)
    mismatches=[]
    for name,rec in records.items():
        if name not in profiles:
            continue
        for side in ("offense","defense"):
            unit=rec[side]
            valid={p["package_id"] for p in pc.packages_for_roster(side,unit["family"],profiles[name]) if p["meets_personnel"]}
            for pkg in unit["packages"]:
                if pkg["package_id"] not in valid:
                    mismatches.append({"team":name,"side":side,"package":pkg["package_id"]})
    return mismatches

def run(seasons, nteams, seed, out):
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory(prefix="viperball-dynasty-") as tmp:
        os.environ["VIPERBALL_DB_PATH"] = str(Path(tmp)/"study.sqlite3")
        import api.main as api
        from engine import db
        from engine.recruiting import auto_recruit_team
        random.seed(seed)
        paths=sorted((ROOT/"data"/"teams").glob("*.json"))
        selected=[paths[round(i*(len(paths)-1)/(nteams-1))] for i in range(nteams)]
        league_dir=Path(tmp)/"teams"
        league_dir.mkdir()
        names=[]
        for f in selected:
            shutil.copy(f,league_dir/f.name)
            info=json.loads(f.read_text())["team_info"]
            names.append(info.get("school") or info["school_name"])
        if len(set(names))!=nteams:
            raise RuntimeError("Duplicate program names")
        # Only the real program-file input is reduced. All API and engine
        # season/offseason functions run normally.
        api.TEAMS_DIR=str(league_dir)
        conf={"Calibration East":names[:nteams//2],"Calibration West":names[nteams//2:]}
        human=names[0]
        c=TestClient(api.app)
        def post(path, payload=None):
            r=c.post(path,json=payload if payload is not None else {})
            if r.status_code>=400:
                raise RuntimeError(f"{path}: {r.status_code} {r.text[:1200]}")
            return r.json()
        sid=post("/sessions")["session_id"]
        base=f"/sessions/{sid}"
        post(base+"/dynasty",{"coach_team":human,"dynasty_name":"Tactical calibration",
            "starting_year":2026,"conferences":conf,"games_per_team":12,
            "playoff_size":4,"bowl_count":0,"history_years":0})
        report={"seed":seed,"programs":names,"years":[],"transitions":[]}
        out.mkdir(parents=True,exist_ok=True)
        def checkpoint():
            (out/"dynasty_results.json").write_text(json.dumps(report,indent=2,sort_keys=True))
        checkpoint()
        prev_rosters=None
        prev_staff=None
        prev_units={}
        expected_rosters=None
        for index in range(seasons):
            year=2026+index
            post(base+"/dynasty/start-season",{"ai_seed":seed+year,"offense_style":"balanced","defense_style":"swarm"})
            sess=api.sessions[sid]
            dyn, season=sess["dynasty"],sess["season"]
            if dyn.current_year!=year or len(season.teams)!=nteams:
                raise RuntimeError("Wrong season or program count")
            # A completed generated schedule is not evidence that the
            # requested schedule was fulfilled.
            scheduled_counts = Counter()
            scheduled_pairs = set()
            weekly_slots = set()
            for game in season.schedule:
                pair = tuple(sorted((game.home_team, game.away_team)))
                if pair[0] == pair[1] or pair in scheduled_pairs:
                    raise RuntimeError(f"Invalid or duplicate matchup: {pair}")
                scheduled_pairs.add(pair)
                for team in pair:
                    slot = (game.week, team)
                    if slot in weekly_slots:
                        raise RuntimeError(f"Double-booked program: {slot}")
                    weekly_slots.add(slot)
                    scheduled_counts[team] += 1
            expected_games = min(12, nteams - 1)
            wrong = {t: scheduled_counts[t] for t in names
                     if scheduled_counts[t] != expected_games}
            if wrong:
                raise RuntimeError(f"Schedule quota mismatch (expected {expected_games}): {wrong}")
            start=snapshot(season.teams)
            identity_owners = defaultdict(list)
            for team_name, team in season.teams.items():
                for player in team.players:
                    identity_owners[identity(player)].append(
                        {"team": team_name, "name": player.name})
            duplicate_identities = {
                pid: owners for pid, owners in identity_owners.items()
                if len(owners) > 1
            }
            report.setdefault("identity_collisions",{})[str(year)]=duplicate_identities
            if duplicate_identities:
                checkpoint()
                raise RuntimeError("Duplicate player identities: "
                                   +json.dumps(duplicate_identities,sort_keys=True))
            if expected_rosters is not None:
                # Compare actual roster entries rather than a dictionary
                # keyed by player ID, which can conceal duplicate identities.
                actual={t:sorted(p.name for p in team.players) for t,team in season.teams.items()}
                if actual!=expected_rosters:
                    differences={}
                    for t in sorted(set(actual) | set(expected_rosters)):
                        got=Counter(actual.get(t, []))
                        want=Counter(expected_rosters.get(t, []))
                        if got != want:
                            differences[t]={"missing":dict(want-got),"extra":dict(got-want)}
                    raise RuntimeError("Reloaded next-season roster differs from finalized roster: "
                                       +json.dumps(differences,sort_keys=True))
            staff=staff_ids(dyn)
            changes={t for t in names if prev_staff and staff[t].get("dc")!=prev_staff[t].get("dc")}
            groups,packages=defaultdict(Counter),defaultdict(Counter)
            weekly=[]
            measured=set()
            first_units={}
            while sess["phase"]=="regular":
                step=post(base+"/season/simulate-week")
                if not step.get("games_count"):
                    raise RuntimeError("Season stalled before completion")
                for g in season.schedule:
                    if g.completed and id(g) not in measured:
                        measured.add(id(g))
                        measure_game(g,year,groups,packages,season.teams,changes,None,dyn._team_installations)
                for t,rec in dyn._team_installations.items():
                    first_units.setdefault(t,deepcopy(rec["defense"]))
                weekly.append({"week":step["week"],"games":step["games_count"],
                    "mean_carry":average([p.fatigue_carry for t in season.teams.values() for p in t.players])})
            post(base+"/season/playoffs")
            for g in season.playoff_bracket:
                if g.completed and id(g) not in measured:
                    measured.add(id(g))
                    measure_game(g,year,groups,packages,season.teams,changes,None,dyn._team_installations)
            units={t:deepcopy(r["defense"]) for t,r in dyn._team_installations.items()}
            installed=Counter(p["package_id"] for u in units.values() for p in u["packages"])
            roster_moves=[]
            if prev_rosters:
                for t,rows in start.items():
                    previous=prev_rosters[t]
                    keep=set(rows)&set(previous)
                    roster_moves.append({"team":t,"retained":len(keep),"arrivals":len(set(rows)-set(previous)),
                        "departures":len(set(previous)-set(rows)),
                        "retained_stamina_delta":average([rows[k]["stamina"]-previous[k]["stamina"] for k in keep]),
                        "retained_tackling_delta":average([rows[k]["tackling"]-previous[k]["tackling"] for k in keep])})
            from engine.team_installation import (
                defensive_adoption_snapshot, league_roster_profiles)
            profiles = league_roster_profiles(season.teams)
            adoption = {}
            funnel = defaultdict(Counter)
            for name, unit in units.items():
                card = dyn._coaching_staffs.get(name, {}).get("dc")
                snap = defensive_adoption_snapshot(unit, card, profiles.get(name, {}))
                adoption[name] = snap
                for pid, row in snap["packages"].items():
                    bucket = funnel[pid]
                    bucket["programs"] += 1
                    for key in ("compatible", "personnel_ok", "callable", "installed",
                                "installed_by_current_dc"):
                        bucket[key] += int(row[key])
                    bucket["installable"] += int(row["personnel_ok"] and row["callable"])
                    if row["personnel_ok"] and row["callable"] and not row["installed"]:
                        bucket["qualified_not_installed"] += 1
            for pid, bucket in funnel.items():
                for key in ("eligible", "selected", "secondary_selected"):
                    bucket[key + "_calls"] = packages[pid].get(key, 0)
            fit=roster_fit(season,dyn._team_installations)
            item={"year":year,"regular_games":sum(g.completed for g in season.schedule),
                  "playoff_games":sum(g.completed for g in season.playoff_bracket),
                  "champion":season.champion,"schedule_counts":{t:sum(t in (g.home_team,g.away_team) for g in season.schedule) for t in names},
                  "dc_changes":sorted(changes),"staff":staff,"first_units":first_units,"end_units":units,
                  "installed":dict(installed),"defensive_adoption":adoption,
                  "defensive_adoption_funnel":{k:dict(v) for k,v in funnel.items()},
                  "roster_fit_mismatches":fit,"roster_moves":roster_moves,
                  "weekly":weekly,"groups":{k:dict(v) for k,v in groups.items()},"packages":{k:dict(v) for k,v in packages.items()}}
            report["years"].append(item)
            checkpoint()
            print("YEAR",year,"regular",item["regular_games"],"playoffs",item["playoff_games"],
                "DC_changes",len(changes),"installed",sum(installed.values()),"package_ids",len(installed),
                "fit_mismatches",len(fit),"calls",sum(v.get("selected",0) for v in packages.values()),
                "rush",dict(groups["rush_total"]),"mean_carry",weekly[-1]["mean_carry"],flush=True)
            for pid, values in sorted(funnel.items()):
                print("ADOPTION",year,pid,dict(values),flush=True)
            for key,g in sorted(packages.items()):
                print("PACKAGE",year,key,dict(g),flush=True)
            for key,g in sorted(groups.items()):
                if key.startswith(("cohort:","familiarity:","offense_energy:","defense_energy:","rush_count:")):
                    print("GROUP",year,key,dict(g),flush=True)
            prev_rosters=start
            prev_staff=staff
            prev_units=units
            if index+1==seasons:
                break
            pre=deepcopy(dyn._team_installations)
            adv=post(base+"/dynasty/advance")
            off=sess["offseason"]
            nil=off["nil_program"]
            budget=nil.annual_budget
            post(base+"/offseason/nil/allocate",{"recruiting_pool":budget*.5,"portal_pool":budget*.3,"retention_pool":budget*.2})
            portal=post(base+"/offseason/portal/resolve")
            # The designated human program uses the same existing AI recruiting
            # helper for its board; no forced signings or manual hires.
            board,offers=auto_recruit_team(human,off["recruit_pool"],dyn.team_prestige.get(human,50),
                dyn._estimate_team_regions().get(human,"midwest"),scholarships=8,
                nil_budget=nil.recruiting_pool,rng=random.Random(seed+year),
                current_roster=[{"position":p.position} for p in off["player_cards"].get(human,[])])
            off["recruit_board"],off["nil_offers"]=board,offers
            recruiting=post(base+"/offseason/recruiting/resolve")
            post(base+"/offseason/complete")
            expected=deepcopy(dyn._team_installations)
            expected_staff=staff_ids(dyn)
            expected_pipeline=dyn._hs_pipeline.save_state() if dyn._hs_pipeline else None
            saved_rosters=deepcopy(dyn._next_season_rosters)
            expected_rosters={t:sorted((r["first_name"]+" "+r["last_name"]) for r in rows)
                              for t,rows in saved_rosters.items()}
            loaded=db.load_dynasty(save_key=sid)
            if loaded is None or loaded._team_installations!=expected or staff_ids(loaded)!=expected_staff or loaded._next_season_rosters!=saved_rosters:
                raise RuntimeError("Application DB roundtrip lost installation, staff or roster")
            loaded_pipeline=loaded._hs_pipeline.save_state() if loaded._hs_pipeline else None
            if loaded_pipeline != expected_pipeline:
                raise RuntimeError("Application DB roundtrip lost high school pipeline state")
            # Reload into the live session via the actual endpoint and continue.
            post(base+"/dynasty/load?save_key="+sid)
            trans={"from_year":year,"to_year":year+1,"database_roundtrip":True,
                "coach_hires":off["coaching"]["hires"],"teams_with_changes":off["coaching"]["teams_with_changes"],
                "transfers":portal["total_transfers"],"signed":recruiting["total_signed"],
                "retained_installations":len(expected),"roster_sizes":{t:len(r) for t,r in saved_rosters.items()},
                "mean_defense_familiarity_before":average([u["defense"]["familiarity"] for u in pre.values()]),
                "mean_defense_familiarity_after":average([u["defense"]["familiarity"] for u in expected.values()])}
            report["transitions"].append(trans)
            checkpoint()
            print("TRANSITION",json.dumps(trans,sort_keys=True),flush=True)
        report["complete"]=True
        checkpoint()
        print("COMPLETED",len(report["years"]),"seasons",sum(y["regular_games"]+y["playoff_games"] for y in report["years"]),"full games",flush=True)
        return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",type=int,default=3)
    p.add_argument("--teams",type=int,default=16)
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--out",default="reports/dynasty-calibration")
    a=p.parse_args()
    if a.teams<16 or a.teams%4 or a.seasons<2:
        p.error("Use at least 16 teams divisible by four and at least two seasons")
    run(a.seasons,a.teams,a.seed,Path(a.out))
