#!/usr/bin/env python3
"""STI-VAL integrated full-game special-teams benchmark.

Run: PYTHONHASHSEED=0 python scripts/benchmark_special_teams_integrated.py --games 100
Five ST schemes x three saved STC profiles x clear/rain x N games.  The
default of 100 is 3,000 games.

Every game in the study has its own seed and its own matchup drawn from
all program files, so rare events (return touchdowns, fakes, blocks) are
not the same few random draws repeated cell after cell.  Within a cell the
three coordinator profiles share the seed and the matchup, so they are a
paired comparison.

Neutral STC, not no-staff, is the matched control. The ST scheme and
coordinator affect only the home team. All events are attributed using the
recorded special_teams_event.kicking_side and the post-snap scoreboard.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.game_engine import ViperballEngine, ST_SCHEMES, load_team_from_json
from benchmark_defensive_coaches import coach


def staff(name, territory, aggression):
    c = coach("ST-integrated-"+name, "stc")
    c.tactical_profile["special_teams"]={
        "field_position_bias":territory,
        "return_aggression":aggression,
    }
    return {"stc":c}


def run(games=100,seed=20261124):
    paths=sorted((ROOT/"data"/"teams").glob("*.json"))
    if len(paths)<2:
        raise RuntimeError("Two roster files required")
    teams=[load_team_from_json(str(p),fresh=False) for p in paths]
    profiles={"neutral":(0.,0.),"territory":(.5,-.5),"attack":(-.5,.5)}
    output={}
    failures=[]
    for scheme_idx,scheme in enumerate(sorted(ST_SCHEMES)):
        for weather_idx,weather in enumerate(("clear","rain")):
            for profile,(territory,aggression) in profiles.items():
                counts=Counter()
                scores=[]
                for n in range(games):
                    # Same roster + seed across coordinator profiles, different
                    # seeds and matchups in every scheme/weather cell, so no
                    # game repeats anywhere else in the study.
                    match_seed=seed+(scheme_idx*2+weather_idx)*1_000_003+n
                    pick=random.Random(match_seed)
                    home_i,away_i=pick.sample(range(len(teams)),2)
                    random.seed(match_seed)
                    home=deepcopy(teams[home_i])
                    away=deepcopy(teams[away_i])
                    home.st_scheme=scheme
                    away.st_scheme="aces"
                    result=ViperballEngine(
                        home,away,seed=match_seed,neutral_site=True,
                        weather=weather,home_coaching=staff(profile,territory,aggression),
                    ).simulate_game()
                    scores.append(result["final_score"]["home"]["score"])
                    for side in ("home","away"):
                        st=result["stats"][side]
                        players=result["player_stats"][side]
                        for team_key,individual_key in (
                            ("drop_kicks_attempted","dk_att"),
                            ("place_kicks_attempted","pk_att"),
                            ("punt_returns","punt_returns"),
                            ("punt_return_yards","punt_return_yards"),
                        ):
                            player_total=sum(p.get(individual_key,0) for p in players)
                            if abs(st.get(team_key,0)-player_total)>0.001:
                                failures.append([scheme,weather,profile,n,side,team_key,
                                                 st.get(team_key),player_total])
                        profile_stats=st.get("viperball_metrics",{}).get("scoring_profile",{})
                        if profile_stats.get("score_consistent") is False:
                            failures.append([scheme,weather,profile,n,side,"score ledger"])
                    for p in result["play_by_play"]:
                        event=p.get("special_teams_event") or {}
                        if not event:
                            continue
                        kicker_side=event.get("kicking_side")
                        kind=event.get("kind")
                        if kicker_side=="home":
                            counts["home_"+kind]+=1
                            counts["home_"+str(event.get("result"))]+=1
                            counts["home_fakes"]+=int(bool(event.get("fake")))
                            counts["home_blocked_kicks"]+=int(kind in ("drop_kick","place_kick")
                                                             and event.get("result")=="blocked_kick")
                            if event.get("blocker"):
                                counts["named_blockers"]+=1
                            if event.get("nullified"):
                                counts["home_nullified"]+=1
                        if kicker_side=="away" and kind=="punt":
                            counts["home_punts_received"]+=1
                            counts["home_punt_return_td"]+=int(event.get("result")=="punt_return_td")
                            counts["home_muffs"]+=int(event.get("result")=="muffed_punt")
                            counts["home_return_yards"]+=int(event.get("return_yards") or 0)
                            counts["home_return_punts"]+=int(event.get("return_yards") is not None)
                        # A return credited to a player must not go backward.
                        if (kind=="punt" and event.get("return_yards") is not None
                            and not event.get("nullified")):
                            if event.get("return_yards",0)<0:
                                failures.append([scheme,weather,profile,n,"negative return"])
                key=f"{scheme}/{weather}/{profile}"
                output[key]={"games":games,"mean_home_points":round(sum(scores)/len(scores),3),
                             "events":dict(counts)}
    return {"seed":seed,"games_per_case":games,"cases":len(output),
            "summary":summarize(output),
            "full_games":len(output)*games,"results":output,
            "failures":failures[:50],"failure_count":len(failures)}


def summarize(output):
    """Per profile, pooled over every scheme and weather cell, as rates."""
    pooled={}
    for key,cell in output.items():
        profile=key.split("/")[2]
        agg=pooled.setdefault(profile,{"games":0,"points":0.0,"events":Counter()})
        agg["games"]+=cell["games"]
        agg["points"]+=cell["mean_home_points"]*cell["games"]
        agg["events"].update(cell["events"])
    summary={}
    for profile,agg in pooled.items():
        e=agg["events"]
        punts_received=e["home_punts_received"]
        kicks=e["home_drop_kick"]+e["home_place_kick"]
        rate=lambda num,den:round(num/den,4) if den else None
        summary[profile]={
            "games":agg["games"],
            "home_points_per_game":round(agg["points"]/agg["games"],2),
            "home_punts_per_game":round(e["home_punt"]/agg["games"],3),
            "home_snap_kicks_per_game":round(e["home_drop_kick"]/agg["games"],3),
            "home_fakes":e["home_fakes"],
            "home_kick_block_rate":rate(e["home_blocked_kicks"],kicks),
            "punts_received":punts_received,
            "muff_rate":rate(e["home_muffs"],punts_received),
            "return_td_rate":rate(e["home_punt_return_td"],punts_received),
            "return_tds":e["home_punt_return_td"],
            "yards_per_return":rate(e["home_return_yards"],e["home_return_punts"]),
        }
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--games",type=int,default=100)
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--out",default=None)
    args=p.parse_args()
    if args.games<1:p.error("--games must be positive")
    result=run(args.games,args.seed)
    text=json.dumps(result,indent=2,sort_keys=True)
    if args.out:
        path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    print(text)
    if result["failure_count"]:
        raise SystemExit(f"STI-VAL detected {result['failure_count']} accounting discrepancies")


if __name__=="__main__":
    main()
