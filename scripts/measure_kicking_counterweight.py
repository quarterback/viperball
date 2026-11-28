"""Kicking counterweight measurement: N engine games between random pairs, same seeds.

Run from the repo root: python3 scripts/measure_kicking_counterweight.py 200
Prints per game figures as JSON. Used for docs/report_2026_11_28_kicking_counterweight.md.
"""
import glob, random, sys, json, statistics as st
sys.path.insert(0,'.')
from engine.game_engine import ViperballEngine, load_team_from_json
N=int(sys.argv[1]) if len(sys.argv) > 1 else 200; files=sorted(glob.glob('data/teams/*.json'))
rng=random.Random(11); agg={k:0 for k in "pts td sk_att sk_made fg_att fg_made punts pindowns d6_go d6_kick d6_punt drives score_drives".split()}
margins=[]; close=0
for g in range(N):
    a,b=rng.sample(files,2)
    r=ViperballEngine(load_team_from_json(a),load_team_from_json(b),seed=1000+g).simulate_game()
    fs=r["final_score"]; h,aw=fs["home"]["score"],fs["away"]["score"]
    agg["pts"]+=h+aw; margins.append(abs(h-aw)); close+= abs(h-aw)<=9
    for p in r["play_by_play"]:
        t=p.get("play_type"); res=p.get("result")
        if t=="drop_kick": agg["sk_att"]+=1; agg["sk_made"]+= res=="successful_kick"
        if t=="place_kick": agg["fg_att"]+=1; agg["fg_made"]+= res=="successful_kick"
        if t=="punt": agg["punts"]+=1
        if res=="pindown": agg["pindowns"]+=1
        if res=="touchdown": agg["td"]+=1
        if p.get("down")==6:
            if t in ("drop_kick","place_kick"): agg["d6_kick"]+=1
            elif t=="punt": agg["d6_punt"]+=1
            else: agg["d6_go"]+=1
    for d in r.get("drive_summary",[]) or []:
        agg["drives"]+=1; agg["score_drives"]+= d.get("result") in ("touchdown","successful_kick","punt_return_td","int_return_td","missed_dk_return_td")
out={k:v/N for k,v in agg.items()}
out["sk_acc"]=agg["sk_made"]/max(1,agg["sk_att"]); out["fg_acc"]=agg["fg_made"]/max(1,agg["fg_att"])
out["kick_pts"]=(agg["sk_made"]*5+agg["fg_made"]*3)/N
out["kick_share"]=out["kick_pts"]/out["pts"]; out["td_share"]=out["td"]*9/out["pts"]
out["margin"]=st.mean(margins); out["close_share"]=close/N
out["score_drive_rate"]=agg["score_drives"]/max(1,agg["drives"])
print(json.dumps(out))
