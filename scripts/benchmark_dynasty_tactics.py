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

def verify_staffs(dyn, active):
    from engine.coach_roles import CORE_ROLES, ALL_ROLES, POSITION_ROLES
    from engine.position_staff import coverage
    owners = defaultdict(list)
    for team in sorted(active):
        staff = dyn._coaching_staffs.get(team, {})
        if not set(CORE_ROLES)<=set(staff)<=set(ALL_ROLES):
            raise RuntimeError(f"Incomplete or invalid staff at {team}: {sorted(staff)}")
        if not all(a["coach_id"] for a in coverage(staff).values()):
            raise RuntimeError(f"Uncovered teaching assignment at {team}")
        for role, card in staff.items():
            if card.team_name != team or card.role != role:
                raise RuntimeError(f"Coach employment metadata mismatch: {team}/{role}/{card.coach_id}")
            owners[card.coach_id].append((team, role))
    duplicates = {cid: slots for cid, slots in owners.items() if len(slots) > 1}
    if duplicates:
        raise RuntimeError("Duplicate active coach employment: " + json.dumps(duplicates))
    return {c.coach_id: c for team in active for c in dyn._coaching_staffs[team].values()}


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
            raise RuntimeError(f"Game includes inactive program: {name}")
        stats = fr["stats"][side]
        if stats.get("viperball_metrics", {}).get("scoring_profile", {}).get("score_consistent") is False:
            raise RuntimeError(f"Score ledger mismatch for {name}")
        # Physical snap ledger: exact participation, no player twice, and
        # the rush/coverage partition must be the credited defensive XI.
        for play in fr["play_by_play"]:
            lineup = play.get("snap_lineup")
            if not lineup or lineup["offense_side"] != side:
                continue
            for unit in ("offense","defense"):
                people = lineup[unit]
                if len(people) != len(set(people)) or len(people)>11:
                    raise RuntimeError("Invalid snap lineup")
                groups["participation:"+unit]["snaps"] += 1
                groups["participation:"+unit]["players"] += len(people)
                groups["participation:"+unit]["short"] += int(len(people)<11)
            rush = play.get("rush_event") or {}
            if rush and set(rush["defenders_on_field"]) != set(lineup["defense"]):
                raise RuntimeError("Rush personnel differ from credited defenders")
        energy = fr.get("game_day",{}).get("energy",{}).get(side,[])
        for player in energy:
            if player["snaps"] != player["offensive_snaps"] + player["defensive_snaps"]:
                raise RuntimeError("Player workload ledger mismatch")
            groups["participation:workload"]["players"] += 1
            groups["participation:workload"]["shifts"] += player["shifts"]
        # Offensive package ledger distinguishes opportunities, calls and
        # actual matching choices. All are attributed to the snapping side.
        oc = fr.get("coach_tactics", {}).get(side, {})
        choices = oc.get("selected", {})
        expected = {key: Counter() for key in ("packages_eligible", "packages",
                                               "packages_family_matched", "packages_all_matched")}
        for play in fr["play_by_play"]:
            call = play.get("offensive_call") or {}
            if call.get("offense_side") != side:
                continue
            for pid in call.get("eligible", []):
                expected["packages_eligible"][pid] += 1
                groups["offense_package:" + pid]["eligible"] += 1
            pid = call.get("package_id")
            if not pid:
                continue
            if pid not in call["eligible"]:
                raise RuntimeError("Offensive package selected outside eligibility")
            expected["packages"][pid] += 1
            row = groups["offense_package:" + pid]
            row["selected"] += 1
            matches = call.get("matches", {})
            if call.get("family_matched"):
                expected["packages_family_matched"][pid] += 1
                row["family_matched"] += 1
                if matches and all(matches.values()):
                    expected["packages_all_matched"][pid] += 1
                    row["all_matched"] += 1
            if not (play.get("penalty") or {}).get("nullified"):
                add_play(row, play)
        for key, counts in expected.items():
            if Counter(choices.get(key, {})) != counts:
                raise RuntimeError(f"Offensive package ledger mismatch: {name}/{key}")
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

def run(seasons, nteams, seed, out, *, national=False, longitudinal=False, analytics=False):
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory(prefix="viperball-dynasty-") as tmp:
        os.environ["VIPERBALL_DB_PATH"] = str(Path(tmp)/"study.sqlite3")
        import api.main as api
        from engine import db
        from engine.recruiting import auto_recruit_team
        random.seed(seed)
        paths=sorted((ROOT/"data"/"teams").glob("*.json"))
        selected = paths if national else [paths[round(i*(len(paths)-1)/(nteams-1))] for i in range(nteams)]
        nteams = len(selected)
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
        client=TestClient(api.app)
        def post(path, payload=None):
            r=client.post(path,json=payload if payload is not None else {})
            if r.status_code>=400:
                raise RuntimeError(f"{path}: {r.status_code} {r.text[:1200]}")
            return r.json()
        sid=post("/sessions")["session_id"]
        base=f"/sessions/{sid}"
        payload={"coach_team":human,"dynasty_name":"Tactical calibration",
            "starting_year":2026,"games_per_team":12,
            "playoff_size":8 if national else 4,"bowl_count":0,"history_years":0}
        if not national:
            payload["conferences"] = conf
        post(base+"/dynasty",payload)
        source_names = set(names)
        expected_active = None
        report={"seed":seed,"national":national,"source_programs":names,
                "requested_games_per_team":12,"years":[],"transitions":[]}
        out.mkdir(parents=True,exist_ok=True)
        def checkpoint():
            (out/"dynasty_results.json").write_text(json.dumps(report,indent=2,sort_keys=True))
        checkpoint()
        observer = None
        if longitudinal:
            from benchmark_longitudinal import Study
            observer = Study(out,seed,seasons)
        analytics_paths=[]
        prev_rosters=None
        prev_staff=None
        prev_units={}
        expected_rosters=None
        for index in range(seasons):
            year=2026+index
            setup=post(base+"/dynasty/start-season",{"ai_seed":seed+year,"offense_style":"balanced","defense_style":"swarm"})
            sess=api.sessions[sid]
            dyn, season=sess["dynasty"],sess["season"]
            if dyn.current_year != year:
                raise RuntimeError("Wrong dynasty year")
            active = set(season.teams)
            from engine.coach_school_continuity import planned_schools
            for team, config in planned_schools(dyn, year).items():
                if team in active and team != human:
                    if any(season.style_configs[team].get(k) != v for k,v in config.items()):
                        raise RuntimeError(f"Recruiting school plan not used at season opening: {team}")
            retired = set(getattr(dyn, "retired_programs", []) or [])
            if national and index == 0:
                auto_retired = setup.get("auto_retired")
                # The playable dynasty requires even program counts. Verify
                # its normal explicit retirement policy, never silently drop
                # a school to manufacture a passing schedule.
                permitted = {"Coast Guard", "Merchant Marine"}
                if len(source_names) % 2:
                    if auto_retired not in permitted or auto_retired not in retired:
                        raise RuntimeError("Missing expected odd-league retirement")
                    expected_active = source_names - {auto_retired}
                else:
                    expected_active = source_names
            elif expected_active is None:
                expected_active = source_names
            if active != expected_active:
                raise RuntimeError(f"Unexpected active programs: missing {sorted(expected_active-active)}, extra {sorted(active-expected_active)}")
            names = sorted(active)
            report["programs"] = names
            report["retired_programs"] = sorted(retired)
            report.setdefault("conference_sizes", {})[str(year)] = {
                c: len(set(ts) & active) for c, ts in season.conferences.items()
            }
            checkpoint()
            # A completed generated schedule is not evidence that the
            # requested schedule was fulfilled.
            scheduled_counts = Counter()
            scheduled_pairs = set()
            weekly_slots = set()
            for game in season.schedule:
                pair = tuple(sorted((game.home_team, game.away_team)))
                if not set(pair) <= active:
                    raise RuntimeError(f"Scheduled inactive or unknown program: {pair}")
                if pair[0] == pair[1] or pair in scheduled_pairs:
                    raise RuntimeError(f"Invalid or duplicate matchup: {pair}")
                scheduled_pairs.add(pair)
                for team in pair:
                    slot = (game.week, team)
                    if slot in weekly_slots:
                        raise RuntimeError(f"Double-booked program: {slot}")
                    weekly_slots.add(slot)
                    scheduled_counts[team] += 1
            expected_games = min(12, len(active) - 1)
            wrong = {t: scheduled_counts[t] for t in names
                     if scheduled_counts[t] != expected_games}
            report.setdefault("schedule_preflight", {})[str(year)] = {
                "active_programs": len(active), "requested_per_program": expected_games,
                "scheduled_games": len(season.schedule),
                "expected_games": len(active)*expected_games//2,
                "wrong_quota": wrong,
            }
            checkpoint()
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
                # Compare actual roster identities, names and positions rather
                # than a dictionary that can conceal duplicate entries.
                actual={t:sorted((p.player_id, p.name, p.position) for p in team.players)
                        for t,team in season.teams.items()}
                if actual!=expected_rosters:
                    differences={}
                    for t in sorted(set(actual) | set(expected_rosters)):
                        got=Counter(actual.get(t, []))
                        want=Counter(expected_rosters.get(t, []))
                        if got != want:
                            differences[t]={"missing":list((want-got).items()),"extra":list((got-want).items())}
                    raise RuntimeError("Reloaded next-season roster differs from finalized roster: "
                                       +json.dumps(differences,sort_keys=True))
            verify_staffs(dyn, active)
            if observer:
                observer.opening(year,dyn,season)
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
            regular_count = sum(g.completed and bool(g.full_result) for g in season.schedule)
            playoff_count = sum(g.completed and bool(g.full_result) for g in season.playoff_bracket)
            if regular_count != len(season.schedule) or regular_count != len(active)*expected_games//2:
                raise RuntimeError("Regular-season full-game count does not match schedule")
            if playoff_count != payload["playoff_size"] - 1 or not season.champion:
                raise RuntimeError("Incomplete playoff or missing champion")
            if len(measured) != regular_count + playoff_count:
                raise RuntimeError("Game measurement ledger does not reconcile")
            units={t:deepcopy(r["defense"]) for t,r in dyn._team_installations.items() if t in active}
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
            focus_funnel = defaultdict(lambda: defaultdict(Counter))
            for name, unit in units.items():
                from engine.coach_career import caller
                card = caller(dyn._coaching_staffs.get(name, {}),"dc")
                snap = defensive_adoption_snapshot(unit, card, profiles.get(name, {}))
                adoption[name] = snap
                for pid, row in snap["packages"].items():
                    bucket = funnel[pid]
                    bucket["programs"] += 1
                    for key in ("compatible", "personnel_ok", "callable", "installed",
                                "installed_by_current_dc"):
                        bucket[key] += int(row[key])
                    bucket["installable"] += int(row["personnel_ok"] and row["callable"])
                    focus_bucket = focus_funnel[snap.get("coverage_focus") or "unknown"][pid]
                    focus_bucket["programs"] += 1
                    focus_bucket["installable"] += int(row["personnel_ok"] and row["callable"])
                    focus_bucket["installed"] += int(row["installed"])
                    if row.get("preference_rank") is not None:
                        focus_bucket["top_two"] += int(row["preference_rank"] <= 2)
                    if row["personnel_ok"] and row["callable"] and not row["installed"]:
                        bucket["qualified_not_installed"] += 1
            for pid, bucket in funnel.items():
                for key in ("eligible", "selected", "secondary_selected"):
                    bucket[key + "_calls"] = packages[pid].get(key, 0)
            fit=roster_fit(season,dyn._team_installations)
            if fit:
                raise RuntimeError(f"Installed packages violate roster fit: {fit}")
            item={"year":year,"regular_games":sum(g.completed for g in season.schedule),
                  "playoff_games":sum(g.completed for g in season.playoff_bracket),
                  "champion":season.champion,"schedule_counts":{t:sum(t in (g.home_team,g.away_team) for g in season.schedule) for t in names},
                  "dc_changes":sorted(changes),"staff":staff,"first_units":first_units,"end_units":units,
                  "installed":dict(installed),"defensive_adoption":adoption,
                  "defensive_adoption_funnel":{k:dict(v) for k,v in funnel.items()},
                  "defensive_adoption_by_focus":{focus:{pid:dict(counts) for pid,counts in rows.items()}
                      for focus,rows in focus_funnel.items()},
                  "roster_fit_mismatches":fit,"roster_moves":roster_moves,
                  "weekly":weekly,"groups":{k:dict(v) for k,v in groups.items()},"packages":{k:dict(v) for k,v in packages.items()}}
            item["active_programs"] = len(active)
            item["retired_programs"] = sorted(retired)
            # Descriptive rating and depth distributions on the actual new
            # talent baseline; no target for scoring or roster strength.
            from engine.player_card import player_to_card
            ratings = defaultdict(list)
            depth = Counter()
            for name, team in season.teams.items():
                positions = Counter(p.position for p in team.players)
                for pos, count in positions.items():
                    depth[pos] += count
                for p in team.players:
                    card = player_to_card(p, name)
                    ratings[str(p.year)].append(card.overall)
            item["roster_observations"] = {
                "class_ratings": {k: {"n":len(v), "mean":average(v),
                    "median":statistics.median(v), "min":min(v), "max":max(v)}
                    for k,v in ratings.items()},
                "position_counts":dict(depth),
                "program_count":len(active),
            }
            print("ROSTER",year,json.dumps(item["roster_observations"],sort_keys=True),flush=True)
            if analytics:
                from benchmark_advanced_analytics import write_season
                analytics_paths.append(write_season(out,season,year,seed))
            report["years"].append(item)
            checkpoint()
            if observer:
                observer.season_end(year,dyn,season,item)
            print("YEAR",year,"regular",item["regular_games"],"playoffs",item["playoff_games"],
                "DC_changes",len(changes),"installed",sum(installed.values()),"package_ids",len(installed),
                "fit_mismatches",len(fit),"calls",sum(v.get("selected",0) for v in packages.values()),
                "rush",dict(groups["rush_total"]),"mean_carry",weekly[-1]["mean_carry"],flush=True)
            for pid, values in sorted(funnel.items()):
                print("ADOPTION",year,pid,dict(values),flush=True)
            for focus, rows in sorted(focus_funnel.items()):
                print("ADOPTION_FOCUS",year,focus,json.dumps({pid:dict(v) for pid,v in rows.items()},sort_keys=True),flush=True)
            for key,g in sorted(packages.items()):
                print("PACKAGE",year,key,dict(g),flush=True)
            for key,g in sorted(groups.items()):
                if key.startswith(("cohort:","familiarity:","offense_energy:","defense_energy:","rush_count:","offense_package:")):
                    print("GROUP",year,key,dict(g),flush=True)
            prev_rosters=start
            prev_staff=staff
            prev_units=units
            if index+1==seasons:
                break
            pre=deepcopy(dyn._team_installations)
            from engine.college_feeder import competition_index, verify_pipeline
            import hashlib
            from dataclasses import asdict
            old_league, old_pipeline = dyn._hs_league, dyn._hs_pipeline
            tracked_before = verify_pipeline(old_league,old_pipeline)
            hs_before = competition_index(old_league)
            expected_graduates = {p.recruit.recruit_id: asdict(p.recruit)
                                  for p in old_pipeline.classes["12th"]}
            hs_seniors = {pid for pid,(_,p) in hs_before.items() if p.year=="Senior"}
            from engine.coach_tactics import ensure_coach_tactical_profile
            before_coaches = {cid: (c.team_name, c.age, c.seasons_coached, c.career_wins, c.career_losses,
                                   deepcopy(ensure_coach_tactical_profile(c)))
                              for cid,c in verify_staffs(dyn, active).items()}
            played_records = {t: (rec.wins, rec.losses) for t,rec in season.standings.items()}
            adv=post(base+"/dynasty/advance")
            after_coaches = verify_staffs(dyn, active)
            retained_coaches = set(before_coaches) & set(after_coaches)
            for cid in retained_coaches:
                old_team, age, seasons_coached, wins, losses, profile = before_coaches[cid]
                c = after_coaches[cid]
                w,l = played_records[old_team]
                if (c.age, c.seasons_coached, c.career_wins, c.career_losses) != (age+1,seasons_coached+1,wins+w,losses+l):
                    raise RuntimeError(f"Coach season credit mismatch: {cid}")
                updated = deepcopy(ensure_coach_tactical_profile(c))
                learning = updated.pop("learning", {})
                prior = profile.get("learning", {})
                original = {k:v for k,v in profile.items() if k != "learning"}
                if updated != original:
                    raise RuntimeError(f"Coach base signature changed during employment transition: {cid}")
                from engine.coach_learning import LIMIT, STEP, MENTOR_LIMIT, MENTOR_STEP
                for key in ("kick_mix", "pressure"):
                    if abs(learning.get(key,0)) > LIMIT + 1e-6 or abs(learning.get(key,0)-prior.get(key,0)) > STEP + 1e-6:
                        raise RuntimeError(f"Unbounded tactical adaptation: {cid}/{key}")
                    m = learning.get("mentorship", {}).get(key, 0)
                    old_m = prior.get("mentorship", {}).get(key, 0)
                    if abs(m) > MENTOR_LIMIT + 1e-6 or abs(m-old_m) > MENTOR_STEP + 1e-6:
                        raise RuntimeError(f"Unbounded coaching-tree inheritance: {cid}/{key}")
            mentorship = dyn.coaching_history[year+1].get("mentorship", [])
            school_plan = planned_schools(dyn, year+1)
            if len({e["coach_id"] for e in mentorship}) != len(mentorship):
                raise RuntimeError("Duplicate mentorship season credit")
            if set(school_plan) != active - {human}:
                raise RuntimeError("Missing CPU school continuity plans")
            career_events = dyn.coaching_history[year+1].get("career_development", [])
            if len(career_events) != len(before_coaches) or len({e["team"]+"|"+e["role"] for e in career_events}) != len(before_coaches):
                raise RuntimeError("Career evidence ledger must cover each prior staff slot once")
            coach_events = dyn.coaching_history[year+1].get("development", [])
            if len(coach_events) != len(before_coaches) or len({e["coach_id"] for e in coach_events}) != len(before_coaches):
                raise RuntimeError("Coaching development ledger does not cover each prior active coach once")
            off=sess["offseason"]
            if observer:
                observer.developed(year,off["player_cards"])
            if {r.recruit_id:asdict(r) for r in off["recruit_pool"]} != expected_graduates:
                raise RuntimeError("College recruiting pool is not the tracked HS senior cohort")
            reserve_ids = {r.recruit_id for r in off["hs_walkon_reserve"]}
            if reserve_ids != hs_seniors-set(expected_graduates):
                raise RuntimeError("High school walk-on reserve does not reconcile with actual seniors")
            tracked_after = verify_pipeline(dyn._hs_league,dyn._hs_pipeline)
            hs_after = competition_index(dyn._hs_league)
            if set(hs_before)-set(hs_after) != hs_seniors or not (tracked_before-set(expected_graduates)) <= tracked_after:
                raise RuntimeError("High school roster or scouting cohort failed year continuity")
            if any(pid in hs_after for pid in expected_graduates):
                raise RuntimeError("Graduating recruits remain in HS competition")
            # Development and graduation may change attributes/class, never
            # introduce a new college identity before signing/finalization.
            prior_ids = {pid for roster in start.values() for pid in roster}
            off_ids = {c.player_id for cards in off["player_cards"].values() for c in cards}
            if off_ids != prior_ids:
                raise RuntimeError("Unexpected college identities before recruiting")
            graduating_ids = {c.player_id for cards in off["player_cards"].values()
                              for c in cards if c.year == "Graduate"}
            pool_ratings = [r.true_overall for r in off["recruit_pool"]]
            nil=off["nil_program"]
            budget=nil.annual_budget
            post(base+"/offseason/nil/allocate",{"recruiting_pool":budget*.5,"portal_pool":budget*.3,"retention_pool":budget*.2})
            portal=post(base+"/offseason/portal/resolve")
            # The designated human program uses the same existing AI recruiting
            # helper for its board; no forced signings or manual hires.
            from engine.roster_continuity import projected_rosters, COLLEGE_ROSTER_TARGET
            human_roster = projected_rosters(off["player_cards"], off["portal"])[human]
            board,offers=auto_recruit_team(human,off["recruit_pool"],dyn.team_prestige.get(human,50),
                dyn._estimate_team_regions().get(human,"midwest"),
                scholarships=max(0,COLLEGE_ROSTER_TARGET-len(human_roster)),
                nil_budget=nil.recruiting_pool,rng=random.Random(seed+year),
                current_roster=[{"position":p.position} for p in human_roster],
                coaching_staff=dyn._coaching_staffs.get(human),
                style_config=season.style_configs.get(human),
                position_staff=dyn._coaching_staffs.get(human))
            off["recruit_board"],off["nil_offers"]=board,offers
            recruiting=post(base+"/offseason/recruiting/resolve")
            signed_ids = {r.recruit_id for recruits in (dyn._pending_signed_recruits or {}).values()
                          for r in recruits}
            from engine.coach_recruiting_fit import recruiting_preferences, recruiting_fit, MAX_FIT
            fit_values = []
            for team, recruits in (dyn._pending_signed_recruits or {}).items():
                if team == human:
                    continue
                prefs = recruiting_preferences(dyn._coaching_staffs.get(team), school_plan.get(team))
                for recruit in recruits:
                    if not recruit.is_walkon:
                        fit_values.append(recruiting_fit(recruit, prefs))
            if any(abs(v) > MAX_FIT + 1e-6 for v in fit_values):
                raise RuntimeError("Unbounded recruit targeting fit")
            post(base+"/offseason/complete")
            expected=deepcopy(dyn._team_installations)
            expected_staff=staff_ids(dyn)
            expected_coach_cards = {t:{role:deepcopy(c.to_dict()) for role,c in staff.items()}
                                    for t,staff in dyn._coaching_staffs.items()}
            expected_pipeline=dyn._hs_pipeline.save_state() if dyn._hs_pipeline else None
            hs_digest = hashlib.sha256(json.dumps(dyn._hs_league.save_state(),sort_keys=True).encode()).hexdigest()
            expected_dispersal=list(dyn._pending_retired_dispersal)
            if expected_dispersal:
                raise RuntimeError(f"Unexpected pending retirements after season: {expected_dispersal}")
            saved_rosters=deepcopy(dyn._next_season_rosters)
            if set(saved_rosters) != active:
                raise RuntimeError(f"Offseason saved roster program mismatch: extra={sorted(set(saved_rosters)-active)}, missing={sorted(active-set(saved_rosters))}")
            walkon_details = dyn.recruiting_history[year+1].get("walkon_details", {})
            walkon_ids = {row["player_id"] for rows in walkon_details.values() for row in rows}
            final_ids = {row["player_id"] for rows in saved_rosters.values() for row in rows}
            from engine.talent import STAT_KEYS
            emergency_ids = {row["player_id"] for rows in walkon_details.values() for row in rows
                             if row["source"] == "emergency"}
            for rows in saved_rosters.values():
                for row in rows:
                    pid = row["player_id"]
                    if pid not in (signed_ids|walkon_ids)-emergency_ids:
                        continue
                    if pid not in hs_seniors:
                        raise RuntimeError("New college recruit has no graduating HS identity")
                    team, player = hs_before[pid]
                    if row["high_school"] != team.school_name or any(row["ratings"][attr] != getattr(player,attr) for attr in STAT_KEYS):
                        raise RuntimeError("College signing altered authoritative HS ratings or school")
            if final_ids != (prior_ids-graduating_ids)|signed_ids|walkon_ids:
                raise RuntimeError("College roster additions/departures do not reconcile")
            from engine.roster_continuity import COLLEGE_ROSTER_TARGET
            if any(len(rows) < COLLEGE_ROSTER_TARGET for rows in saved_rosters.values()):
                raise RuntimeError("Roster below existing college target after finalization")
            expected_rosters={t:sorted((r.get("player_id", ""), r["first_name"]+" "+r["last_name"], r["position"]) for r in rows)
                              for t,rows in saved_rosters.items()}
            loaded=db.load_dynasty(save_key=sid)
            if loaded is None or loaded._team_installations!=expected or staff_ids(loaded)!=expected_staff or loaded._next_season_rosters!=saved_rosters:
                raise RuntimeError("Application DB roundtrip lost installation, staff or roster")
            actual_coach_cards = {t:{role:c.to_dict() for role,c in staff.items()} for t,staff in loaded._coaching_staffs.items()}
            if actual_coach_cards != expected_coach_cards:
                differences = {t:{role:[k for k,v in card.items() if actual_coach_cards.get(t,{}).get(role,{}).get(k) != v]
                                  for role,card in staff.items() if actual_coach_cards.get(t,{}).get(role) != card}
                               for t,staff in expected_coach_cards.items() if actual_coach_cards.get(t) != staff}
                report["coach_save_differences"] = differences
                checkpoint()
                raise RuntimeError("Application DB roundtrip lost coaching career or tactical profile: " + json.dumps(differences,sort_keys=True))
            loaded_pipeline=loaded._hs_pipeline.save_state() if loaded._hs_pipeline else None
            if loaded._pending_retired_dispersal != expected_dispersal or set(loaded.retired_programs) != retired:
                raise RuntimeError("Application DB roundtrip lost program retirement state")
            if loaded_pipeline != expected_pipeline:
                raise RuntimeError("Application DB roundtrip lost high school pipeline state")
            if loaded._hs_league is None or hashlib.sha256(json.dumps(loaded._hs_league.save_state(),sort_keys=True).encode()).hexdigest() != hs_digest:
                raise RuntimeError("Application DB roundtrip lost high school competition state")
            verify_pipeline(loaded._hs_league,loaded._hs_pipeline)
            # Reload into the live session via the actual endpoint and continue.
            post(base+"/dynasty/load?save_key="+sid)
            trans={"from_year":year,"to_year":year+1,"database_roundtrip":True,
                "coach_career_continuity":{"retained":len(retained_coaches),
                    "departed":len(set(before_coaches)-set(after_coaches)),
                    "new":len(set(after_coaches)-set(before_coaches)),
                    "development_events":len(coach_events), "career_evidence":career_events,
                    "mentorship_events":mentorship, "planned_schools":school_plan,
                    "signed_recruit_fit":{"count":len(fit_values),
                        "mean":round(average(fit_values),5) if fit_values else None,
                        "positive":sum(v>0 for v in fit_values), "negative":sum(v<0 for v in fit_values)},
                    "position_staff_count":sum(r.startswith("pos_") for team in active for r in dyn._coaching_staffs[team]),
                    "position_payroll":sum(c.contract_salary for team in active for r,c in dyn._coaching_staffs[team].items() if r.startswith("pos_")),
                    "alumni_entries":len(dyn.coaching_history[year+1].get("alumni_candidates",[]))},
                "coach_hires":off["coaching"]["hires"],"teams_with_changes":off["coaching"]["teams_with_changes"],
                "transfers":portal["total_transfers"],"signed":recruiting["total_signed"],
                "hs_feeder":{"competition_players":len(hs_before),"graduating_seniors":len(hs_seniors),
                    "tracked_graduates":len(expected_graduates),"walkon_reserve":len(reserve_ids),"tracked_returning":len(tracked_before-set(expected_graduates)),
                    "next_competition_players":len(hs_after),"next_tracked":len(tracked_after),
                    "competition_games":len(dyn._hs_league.schedule),"save_parity":True},
                "college_cohort":{"graduated":len(graduating_ids),"signed_unique":len(signed_ids),
                    "walkons":len(walkon_ids),"emergency_walkons":sum(row["source"]=="emergency" for rows in walkon_details.values() for row in rows),
                    "pool_mean_overall":average(pool_ratings)},
                "retained_installations":len(expected),"roster_sizes":{t:len(r) for t,r in saved_rosters.items()},
                "mean_defense_familiarity_before":average([u["defense"]["familiarity"] for u in pre.values()]),
                "mean_defense_familiarity_after":average([u["defense"]["familiarity"] for u in expected.values()])}
            report["transitions"].append(trans)
            checkpoint()
            if observer:
                observer.transition(year,dyn,active,trans)
            print("TRANSITION",json.dumps(trans,sort_keys=True),flush=True)
        if analytics:
            from benchmark_advanced_analytics import analyze
            analyze(analytics_paths,out/"analytics",2026)
        report["complete"]=True
        checkpoint()
        if observer:
            observer.finish()
        print("COMPLETED",len(report["years"]),"seasons",sum(y["regular_games"]+y["playoff_games"] for y in report["years"]),"full games",flush=True)
        return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",type=int,default=3)
    p.add_argument("--teams",type=int,default=16)
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--out",default="reports/dynasty-calibration")
    p.add_argument("--national",action="store_true",help="Use all actual college program files and default conference alignment")
    p.add_argument("--longitudinal",action="store_true",help="Record annual coach, program and roster trajectories")
    a=p.parse_args()
    if a.seasons<2 or (not a.national and (a.teams<16 or a.teams%4)):
        p.error("Use at least two seasons; reduced leagues need at least 16 teams divisible by four")
    run(a.seasons,a.teams,a.seed,Path(a.out),national=a.national,longitudinal=a.longitudinal)
