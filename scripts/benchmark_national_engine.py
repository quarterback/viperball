#!/usr/bin/env python3
"""League-scale full-engine audit using actual college schedule and rosters.

No target tuning; output empirical distributions and schedule fulfillment.
Default two regular weeks, optionally --full-season. Requires real API
session path, not the fast simulator.
"""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import random
import statistics
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def mean(xs):
    return round(statistics.mean(xs),3) if xs else None


def run(seed=20261124,weeks=2,full=False):
    # Use isolated temporary application state; never touch persistent saves.
    with tempfile.TemporaryDirectory(prefix="viperball-national-") as temp:
        os.environ["VIPERBALL_DB_PATH"]=str(Path(temp)/"audit.db")
        random.seed(seed)
        from fastapi.testclient import TestClient
        import api.main as api
        client=TestClient(api.app)
        response=client.post("/sessions",json={})
        response.raise_for_status()
        sid=response.json()["session_id"]
        response=client.post(f"/sessions/{sid}/season",json={"name":"National audit"})
        response.raise_for_status()
        season=api.sessions[sid]["season"]
        all_teams=set(season.teams)
        scheduled=Counter()
        for game in season.schedule:
            if getattr(game,"is_playoff",False) or getattr(game,"is_bowl",False):
                continue
            if game.home_team in all_teams:scheduled[game.home_team]+=1
            if game.away_team in all_teams:scheduled[game.away_team]+=1
        initial_schedule={
            "teams":len(all_teams),"scheduled_regular_games":sum(scheduled.values())//2,
            "per_team":dict(sorted(Counter(scheduled.values()).items())),
            "under_scheduled":sorted([n for n in all_teams
                                      if scheduled[n]<max(scheduled.values(),default=0)]),
        }
        rounds=0
        while (not season.is_regular_season_complete()
               and (full or rounds<weeks)):
            season.simulate_week()
            rounds+=1
        games=[g for g in season.schedule if g.completed and g.full_result]
        team_metrics=defaultdict(list)
        totals=Counter()
        top_shares=[]
        for game in games:
            fr=game.full_result
            for side in ("home","away"):
                stats=fr["stats"][side]
                rush=fr.get("defensive_rush",{}).get(side,{})
                sc=fr["final_score"][side]["score"]
                team_metrics["points"].append(sc)
                team_metrics["ppd"].append(stats.get("viperball_metrics",{}).get("ppd",0))
                team_metrics["delta_yards"].append(stats.get("delta_yards",0))
                team_metrics["penalties"].append(stats.get("penalties",0))
                team_metrics["kick_pass_completion"].append(
                    stats.get("kick_passes_completed",0)/max(1,stats.get("kick_passes_attempted",0)))
                team_metrics["sacks_per_game"].append(rush.get("sacks",0))
                totals["rush_attempts"]+=rush.get("attempts",0)
                totals["pressure"]+=rush.get("pressures",0)
                totals["sacks"]+=rush.get("sacks",0)
                totals["hurries"]+=rush.get("hurries",0)
                totals["package_selected"]+=sum(
                    fr.get("defensive_coach_tactics",{}).get(side,{}).get("packages",{}).get("selected",{}).values())
                by=rush.get("by_player",{})
                credits=[p.get("sacks",0)+p.get("lead_hurries",0) for p in by.values()]
                if sum(credits):top_shares.append(max(credits)/sum(credits))
                profile=stats.get("viperball_metrics",{}).get("scoring_profile",{})
                if profile.get("score_consistent") is False:
                    totals["scoring_ledger_failures"]+=1
        totals["full_games"]=len(games)
        return {"seed":seed,"weeks_simulated":rounds,"regular_complete":season.is_regular_season_complete(),
                "schedule":initial_schedule,"mean":{k:mean(v) for k,v in team_metrics.items()},
                "rush_credit_median_leader_share":round(statistics.median(top_shares),4) if top_shares else None,
                "rush_credit_samples":len(top_shares),"totals":dict(totals)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--weeks",type=int,default=2)
    p.add_argument("--full-season",action="store_true")
    p.add_argument("--out",default=None)
    args=p.parse_args()
    if args.weeks<1:p.error("--weeks must be positive")
    result=run(args.seed,args.weeks,args.full_season)
    encoded=json.dumps(result,indent=2,sort_keys=True)
    if args.out:
        path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(encoded)
    print(encoded)


if __name__=="__main__":
    main()
