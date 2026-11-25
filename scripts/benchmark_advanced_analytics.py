#!/usr/bin/env python3
"""AN-VAL: offline reports using finalized full-engine games.

National mode is integrated with the existing API dynasty benchmark.
Standalone smoke: PYTHONHASHSEED=0 python scripts/benchmark_advanced_analytics.py --games 48
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False))


def revision(root=ROOT):
    return subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()


def record(game,game_id,season,seed):
    from engine.analytics_events import build_events,label_states
    from engine.dtw import calculate_game_dtw
    contract=build_events(game,game_id)
    if not contract.get("available") or not contract.get("score_consistent") or not contract.get("drive_spans_valid"):
        raise RuntimeError("Invalid scoring contract: "+game_id)
    if contract["missing_states"] or contract["state_score_mismatches"]:
        raise RuntimeError("Missing or inconsistent pre-state: "+game_id)
    st=game["stats"]
    dtw=calculate_game_dtw(game,st["home"].get("viperball_metrics"),st["away"].get("viperball_metrics"))
    totals=contract["final"]
    # One record per game, not per team. Full scores are outcomes only.
    turnover_margin=(st["home"].get("viperball_metrics") or {}).get("to_margin")
    if turnover_margin is None:
        turnover_margin=0
        for r in contract["events"]:
            if r["result"] in ("fumble","kick_pass_intercepted","lateral_intercepted","int_return_td") and not r["nullified"]:
                a,b=r["before_state"],r["after_state"]
                if a and b and a["possession"]!=b["possession"]:
                    turnover_margin+=1 if b["possession"]=="home" else -1
    team_rows={}
    for side in ("home","away"):
        drives=[d for d in game["drive_summary"] if d["team"]==side]
        recon=st[side].get("scoring_reconciliation") or {}
        if not recon.get("score_consistent") or recon["drive_points"]+recon["non_drive_points"]!=totals[side]:
            raise RuntimeError("Drive score reconciliation failed: "+game_id+"/"+side)
        channels=Counter();units=Counter()
        for row in contract["events"]:
            for e in row["score_events"]:
                if e["team"]==side:
                    channels[e["method"]]+=e["points"];units[e["unit"] or "unknown"]+=e["points"]
        team_rows[side]={"points":totals[side],"channels":dict(channels),"units":dict(units),
            "drives":len(drives),"drive_points":recon["drive_points"],
            "non_drive_points":recon["non_drive_points"],
            "dye":{k:{f:v for f,v in st[side]["dye"][k].items() if f in ("count","points","scores","touchdowns","kicks")}
                   for k in ("penalty_kill","power_play","neutral")},
            "bonus_drives":sum(bool(d.get("bonus_drive")) for d in drives),
            "bonus_scoring_drives":sum(bool(d.get("bonus_drive")) and d.get("offensive_points",0)>0 for d in drives),
            "scheme":game.get(side+"_style"),"defense":game.get(side+"_defense_style"),
            "strength_band":next((r["before_state"].get("strength_band") for r in contract["events"] if r["before_state"] and r["snap_possession"]==side),None)}
    return {"game_id":game_id,"season":season,"seed":seed,"game_seed":game.get("seed"),
            "contract":contract,"dtw_edges":dtw["edges"],"legacy_dtw":dtw["home_dtw"],
            "turnover_margin":turnover_margin,"teams":team_rows,
            "outcome":.5 if totals["home"]==totals["away"] else float(totals["home"]>totals["away"])}


def read_corpus(paths):
    for path in paths:
        with gzip.open(path,"rt") as f:
            for line in f:yield json.loads(line)


def write_season(out,season,year,seed):
    """Called by the actual API benchmark; retain regular and playoff games."""
    path=Path(out)/"analytics"/f"corpus-{year}.jsonl.gz"
    path.parent.mkdir(parents=True,exist_ok=True)
    games=list(season.schedule)+list(season.playoff_bracket)
    with gzip.open(path,"wt") as f:
        for i,g in enumerate(games):
            if g.completed and g.full_result:
                row=record(g.full_result,f"{seed}:{year}:{i}:{g.home_team}:{g.away_team}",year,seed)
                f.write(json.dumps(row,separators=(",",":"))+"\n")
    return path


def partition(record,first_season):
    if record["season"]!=first_season:return "test"
    # Disjoint games for EP fitting and retrospective DTW fitting.
    h=int(hashlib.sha256(record["game_id"].encode()).hexdigest()[:8],16)
    return "ep_train" if h%4!=0 else "dtw_train"


def observations(record):
    from engine.analytics_events import label_states
    for row in label_states(record["contract"]):
        yield {**row,"game_id":record["game_id"]}


def evaluate_game(record,model):
    from engine.empirical_ep import estimate,legacy_value,event_epa,alternatives,context_decomposition
    rows=record["contract"]["events"]
    stats=Counter(); by_state=defaultdict(Counter)
    for obs in observations(record):
        if obs["horizon"]!=2:continue
        s=obs["state"];y=obs["target"];pred=estimate(model,s)
        stats["label_n"]+=1
        if pred is None:continue
        p=pred["value"];old=legacy_value(s,2)
        for key in ("all","down:"+str(s["down"]),"field:"+str(int(s["field_position"])//20),
                    "scheme:"+str(s.get("offense_school")),"support:"+pred["level"]):
            b=by_state[key];b["n"]+=1;b["bias"]+=p-y;b["abs_error"]+=abs(p-y);b["sq_error"]+=(p-y)**2
            b["legacy_abs_error"]+=abs(old-y);b["legacy_sq_error"]+=(old-y)**2
            b["predicted"]+=p;b["observed"]+=y
        stats["value_n"]+=1
    prev=None
    for r in rows:
        s=r["before_state"]
        if s is None:continue
        sign=1 if s["possession"]=="home" else -1
        stats["event_n"]+=1
        val=event_epa(model,r)
        if val is not None:
            stats["epa_n"]+=1;stats["epa_home"]+=sign*val["epa"]
        if r["action"]:
            stats["decision_n"]+=1
            alt=alternatives(model,s,r["action"])
            if alt:
                stats["alternative_n"]+=1;stats["regret"]+=alt["regret"]
                if alt["above_continue"] is not None:
                    stats["above_n"]+=1;stats["above_continue"]+=alt["above_continue"]
        first=prev is None or s["possession_id"]!=prev["possession_id"] or s["possession"]!=prev["possession"]
        if first and s.get("origin")=="score_restart":
            stats["delta_n"]+=1
            dec=context_decomposition(model,s,record["contract"]["restart_baseline"],True)
            if dec:
                stats["delta_supported"]+=1;stats["delta"]+=sign*dec["delta"]
                if abs(dec["interaction_residual"])>1e-8:raise RuntimeError("Nonreconciling Delta decomposition")
        if first and (s.get("bonus_active") or s.get("bonus_recipient") in ("home","away")):
            stats["bonus_n"]+=1
            dec=context_decomposition(model,s,record["contract"]["restart_baseline"])
            if dec:
                stats["bonus_supported"]+=1;stats["bonus"]+=sign*dec["bonus_context"]
        prev=s
    result={"epa_coverage":stats["epa_n"]/max(1,stats["event_n"]),
            "epa_home_per_event":stats["epa_home"]/stats["epa_n"] if stats["epa_n"] else None,
            "delta_mean":stats["delta"]/stats["delta_n"] if stats["delta_n"] and stats["delta_supported"]==stats["delta_n"] else None,
            "bonus_mean":stats["bonus"]/stats["bonus_n"] if stats["bonus_n"] and stats["bonus_supported"]==stats["bonus_n"] else None}
    return result,stats,by_state


def rate_summary(c):
    n=c["n"]
    return {"n":n,"bias":c["bias"]/n,"mae":c["abs_error"]/n,"rmse":math.sqrt(c["sq_error"]/n),
            "legacy_mae":c["legacy_abs_error"]/n,"legacy_rmse":math.sqrt(c["legacy_sq_error"]/n),
            "predicted_mean":c["predicted"]/n,"observed_mean":c["observed"]/n} if n else {"n":0}


def distribution(values):
    if not values:return {"n":0}
    a=sorted(values);n=len(a)
    return {"n":n,"mean":sum(a)/n,"p10":a[int((n-1)*.1)],"median":a[(n-1)//2],"p90":a[int((n-1)*.9)]}


def aggregate(records):
    """AN-03: count-weighted rates, not means of team percentages."""
    groups=defaultdict(Counter);dist=defaultdict(list)
    for record in records:
        for side,t in record["teams"].items():
            for key in ("all","season:"+str(record["season"]),"offense:"+str(t["scheme"]),
                        "defense:"+str(t["defense"]),"strength:"+str(t["strength_band"])):
                b=groups[key];b["team_games"]+=1;b["points"]+=t["points"]
                b["drives"]+=t["drives"];b["drive_points"]+=t["drive_points"];b["non_drive_points"]+=t["non_drive_points"]
                b["bonus_drives"]+=t["bonus_drives"];b["bonus_scoring_drives"]+=t["bonus_scoring_drives"]
                for m,p in t["channels"].items():b["score:"+m]+=p
                for u,p in t["units"].items():b["unit:"+u]+=p
                for k,vals in t["dye"].items():
                    for field,v in vals.items():b[k+":"+field]+=v
                dist[key].append(t["points"])
    result={}
    for k,b in groups.items():
        if abs(sum(v for key,v in b.items() if key.startswith("score:"))-b["points"])>1e-8:
            raise RuntimeError("Aggregate score mismatch")
        if b["drive_points"]+b["non_drive_points"]!=b["points"]:raise RuntimeError("Aggregate drive mismatch")
        result[k]={"totals":dict(b),"points_distribution":distribution(dist[k]),
                   "ppd":b["drive_points"]/b["drives"] if b["drives"] else None,
                   "bonus_conversion":b["bonus_scoring_drives"]/b["bonus_drives"] if b["bonus_drives"] else None,
                   "sparse":b["team_games"]<30}
        result[k]["delta_buckets"]={s:{"n":b[s+":count"],"ppd":b[s+":points"]/b[s+":count"] if b[s+":count"] else None,
            "scoring_rate":b[s+":scores"]/b[s+":count"] if b[s+":count"] else None} for s in ("penalty_kill","power_play","neutral")}
    return result


def analyze(paths,out,first_season):
    from engine.empirical_ep import fit,VERSION
    from engine.dtw_research import study,feature_vector
    out=Path(out)
    model=fit(row for r in read_corpus(paths) if partition(r,first_season)=="ep_train" for row in observations(r))
    dump(out/"model.json",model)
    counts=Counter();stats=Counter();by_state=defaultdict(Counter);train=[];test=[]
    for r in read_corpus(paths):
        split=partition(r,first_season);counts[split]+=1
        if split=="ep_train":continue
        eval_,c,b=evaluate_game(r,model)
        item={"game_id":r["game_id"],"legacy":r["legacy_dtw"],"outcome":r["outcome"],
              "edges":r["dtw_edges"],"features":feature_vector(r,eval_)}
        if split=="dtw_train":train.append(item)
        else:
            test.append(item);stats.update(c)
            for k,v in b.items():by_state[k].update(v)
    if not counts["ep_train"] or not counts["dtw_train"] or not counts["test"]:
        raise RuntimeError("Insufficient disjoint corpus splits")
    rates={k:rate_summary(v) for k,v in by_state.items()}
    overall=rates.get("all",{"n":0})
    coverage=stats["value_n"]/max(1,stats["label_n"])
    acceptance=coverage>=.75 and overall.get("mae",math.inf)<=overall.get("legacy_mae",-math.inf)
    report={"version":VERSION,"revision":revision(),"split_counts":dict(counts),"heldout_metrics":rates,
            "heldout_counts":dict(stats),"coverage":coverage,
            "state_model_gate":{"thresholds":{"coverage":.75,"mae":"no worse than matched legacy comparison"},
                "passed":acceptance,"release":"experimental only; alternative/bonus causal validation not established"},
            "dtw":study(train,test),"national_baselines":aggregate(read_corpus(paths))}
    dump(out/"summary.json",report)
    print("ANALYTICS",json.dumps({"split":dict(counts),"coverage":coverage,"holdout":overall,"gate":acceptance,
                                "alternatives":stats["alternative_n"],"delta":stats["delta_supported"],"bonus":stats["bonus_supported"]},sort_keys=True),flush=True)
    return report


def sample(games,seed,out,trace_only=False,engine_root=ROOT):
    sys.path.insert(0,str(engine_root))
    from engine.game_engine import ViperballEngine,load_team_from_json
    files=sorted((engine_root/"data"/"teams").glob("*.json"))
    # Fixed roster pool, independently seeded games; use more than one school.
    random.seed(seed)
    teams=[load_team_from_json(str(files[i*(len(files)-1)//15]),fresh=False) for i in range(16)]
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if trace_only:
        traces=[]
        for i in range(games):
            result=ViperballEngine(deepcopy(teams[i%16]),deepcopy(teams[(i+5)%16]),seed=seed+i,neutral_site=True).simulate_game()
            for p in result["play_by_play"]:
                p.pop("analytics_before",None);p.pop("analytics_terminal_kick",None)
            payload={k:result[k] for k in ("final_score","play_by_play","drive_summary","stats","player_stats")}
            traces.append(hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest())
        dump(out/"trace.json",traces);return
    paths=[]
    for season in (0,1):
        path=out/f"corpus-{season}.jsonl.gz";paths.append(path)
        with gzip.open(path,"wt") as f:
            for i in range(games):
                gseed=seed+season*100000+i
                result=ViperballEngine(deepcopy(teams[i%16]),deepcopy(teams[(i+5+season)%16]),seed=gseed,
                                      neutral_site=True,weather="rain" if i%2 else "clear").simulate_game()
                f.write(json.dumps(record(result,f"{gseed}:{i}",season,seed+season*100000),separators=(",",":"))+"\n")
    analyze(paths,out,0)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--games",type=int,default=48)
    p.add_argument("--seed",type=int,default=20261124)
    p.add_argument("--out",type=Path,default=Path("reports/advanced-analytics"))
    p.add_argument("--trace-only",action="store_true")
    p.add_argument("--engine-root",type=Path,default=ROOT)
    args=p.parse_args()
    sample(args.games,args.seed,args.out,args.trace_only,args.engine_root)
