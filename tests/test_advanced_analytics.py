from copy import deepcopy
import math

from engine.analytics_events import build_events,label_states,possession_boundary
from engine.empirical_ep import (fit,estimate,event_epa,alternatives,
                                 context_decomposition,state_keys,key_text)
from engine.dtw_research import fit as fit_dtw,predict,study


def state(side="home",fp=50,down=4,segment=0,quarter=1,home=0,away=0,bonus=None):
    return {"possession":side,"field_position":fp,"down":down,"yards_to_go":10,
            "quarter":quarter,"clock":300,"home_score":home,"away_score":away,
            "possession_id":segment,"origin":"score_restart","bonus_active":False,
            "bonus_recipient":bonus,"bonus_wait":1 if bonus else -1}


def play(s,typ,result,home,away,**extra):
    return {"analytics_before":s,"play_type":typ,"result":result,"home_score":home,
            "away_score":away,"snap_possession":s["possession"],"quarter":s["quarter"],**extra}


def game_fixture():
    plays=[
        play(state(),"kick_pass","touchdown",9,0),
        play(state("away",segment=1,home=9),"drop_kick","successful_kick",9,5),
        play(state("home",segment=2,home=9,away=5),"place_kick","successful_kick",12,5),
        play(state("away",segment=3,home=12,away=5),"punt","blocked_kick",21.5,5),
        play(state("away",segment=4,home=21.5,away=5),"run","safety",23.5,5),
        play(state("away",segment=5,home=23.5,away=5),"punt","pindown",23.5,6),
        {"play_type":"bonus_possession","result":"bonus_possession","home_score":23.5,"away_score":6,"quarter":1},
        play(state("home",segment=6,home=23.5,away=6),"penalty","penalty",23.5,6,penalty={"nullified":True}),
        play(state("home",segment=6,home=23.5,away=6,down=5),"run","turnover_on_downs",23.5,6),
    ]
    drives=[{"team":p["snap_possession"],"play_log_start":i,"play_log_end":i+1,"delta_cost":0}
            for i,p in enumerate(plays) if p.get("snap_possession")]
    return {"play_by_play":plays,"drive_summary":drives,"analytics_restart_baseline":20,
            "final_score":{"home":{"score":23.5},"away":{"score":6}}}


def test_event_attribution_and_boundaries():
    g=game_fixture();original=deepcopy(g);c=build_events(g,"g")
    assert g==original and c["score_consistent"] and c["drive_spans_valid"]
    assert c["missing_states"]==c["state_score_mismatches"]==0
    scores=[e for row in c["events"] for e in row["score_events"]]
    assert len({e["id"] for e in scores})==len(scores)
    assert c["score_totals"]=={"home":23.5,"away":6.}
    assert {e["method"] for e in scores}=={"kp_td","dk","pk","return_td","bell","safety","pindown"}
    assert [e["points"] for e in scores if e["method"] in ("return_td","bell")]==[9,.5]
    assert not any(e["drive_credit"] for e in scores if e["method"] in ("return_td","bell","safety"))
    assert c["events"][6]["marker"] and c["events"][7]["action"] is None
    assert possession_boundary(c["events"][3]["before_state"],c["events"][4]["before_state"])
    assert c["events"][-1]["after_state"] is None
    rows=label_states(c)
    first={r["horizon"]:r["target"] for r in rows if r["event_id"]=="g:p0"}
    assert first=={1:9.,2:4.}
    # Same-side possession change (safety then new series) is a boundary.
    safety={r["horizon"]:r["target"] for r in rows if r["event_id"]=="g:p4"}
    assert safety=={1:-2.,2:-1.}


def test_legacy_and_invalid_ledgers_are_not_guessed():
    g=game_fixture()
    del g["play_by_play"][0]["analytics_before"]
    c=build_events(g,"old")
    assert c["score_consistent"] and c["missing_states"]==1 and label_states(c)==[]
    g["final_score"]["home"]["score"]+=.5
    assert not build_events(g,"bad")["score_consistent"]
    g["play_by_play"][0].pop("home_score")
    assert not build_events(g,"missing")["available"]


def test_horizon_stops_at_half_not_quarter():
    g=game_fixture()
    for i,p in enumerate(g["play_by_play"]):
        if i>=2 and p.get("analytics_before"):
            p["analytics_before"]["quarter"]=3
    c=build_events(g,"half")
    rows=label_states(c)
    assert next(r["target"] for r in rows if r["event_id"]=="half:p1" and r["horizon"]==2)==5


def train_cell(s,values,horizon=2):
    return [{"state":s,"horizon":horizon,"target":y,"action":a,"game_id":str(i)}
            for i in range(10) for a,y in values]


def test_supported_values_actions_and_context_decomposition():
    s=state();neutral=state(fp=20);bonus=state(bonus="home")
    model=fit(train_cell(s,[("continue",2),("drop_kick",4)])+
              train_cell(neutral,[("continue",1)])+
              train_cell(bonus,[("continue",5)]),min_rows=5,min_games=5)
    assert estimate(model,s)["value"]==3
    a=alternatives(model,s,"continue")
    assert a["regret"]==2 and a["above_continue"]==0 and a["causal"] is False
    assert "place_kick" in a["unsupported"]
    assert alternatives(model,s,"punt") is None
    d=context_decomposition(model,bonus,20,True)
    assert d["delta"]==2 and d["bonus_context"]==2 and d["total"]==4
    assert abs(d["interaction_residual"])<1e-9
    assert estimate(model,state(bonus="away")) is None
    one_game=[{**r,"game_id":"same"} for r in train_cell(s,[("continue",2)])]
    assert estimate(fit(one_game,min_rows=5,min_games=5),s) is None


def test_signed_epa_telescopes_over_fixed_exchange():
    a=state();b=state("away",segment=1,home=9)
    model=fit(train_cell(a,[("continue",4)],2)+train_cell(b,[("continue",5)],1),
              min_rows=5,min_games=5)
    first=event_epa(model,{"before_state":a,"after_state":b,"net_home":9},2)
    last=event_epa(model,{"before_state":b,"after_state":None,"net_home":-5},1)
    assert first["continuation"]==-5 and first["epa"]==0
    assert last["epa"]==0
    assert first["epa"]-last["epa"]==9-5-first["before"]


def test_dtw_no_intercept_symmetry_and_heldout_ablation():
    rows=[{"features":{"exchange_epa":v,"turnover_margin":v},"outcome":float(v>0)}
          for v in (-1.,1.) for _ in range(40)]
    model=fit_dtw(rows,("exchange_epa","turnover_margin"))
    x={"exchange_epa":.2,"turnover_margin":.3}
    assert math.isclose(predict(model,x)+predict(model,{k:-v for k,v in x.items()}),1.)
    assert predict(model,{"exchange_epa":0.,"turnover_margin":0.})==.5
    assert predict(model,{"exchange_epa":.2}) is None


def portal_game(i=0,week=1):
    from engine.box_score_ledger import reconcile_drive_scoring
    fr=game_fixture()
    parts,recon=reconcile_drive_scoring(fr["play_by_play"],fr["drive_summary"],{"home":23.5,"away":6})
    for d,methods in zip(fr["drive_summary"],parts):d["offensive_points"]=sum(methods.values())
    fr["stats"]={s:{"scoring_reconciliation":recon[s],"viperball_metrics":{"to_margin":0}} for s in ("home","away")}
    fr["analytics_contract_version"]=1
    return {"id":f"regular:{week}:{i}","week":week,"idx":i,"kind":"regular","home":"A","away":"B",
            "home_score":23.5,"away_score":6,"result":fr}


def test_analytics_portal_filters_scores_and_export_rows():
    from stats_site.analytics_portal import build_report,sorted_rows
    games=[portal_game(),portal_game(1)]
    conf={"A":"East","B":"West"}
    report=build_report(games,"scoring",{"team":"A"},conf)
    row=report["rows"][0]
    assert row["games"]==2 and row["points"]==47 and row["bell"]==1 and row["gap"]==0
    assert row["drive_points"]+row["non_drive_points"]==row["points"]
    plays=build_report(games,"plays",{"team":"A","down":"4","match":"0"},conf)
    assert plays["coverage"]["games"]==1
    assert plays["rows"] and all(r["team"]=="A" and r["down"]==4 and r["idx"]==0 for r in plays["rows"])
    drives=build_report(games,"drives",{"team":"B","opponent":"A"},conf)
    assert drives["rows"] and all(r["team"]=="B" for r in drives["rows"])
    assert sorted_rows([{"v":None},{"v":1},{"v":2}],"v")==[{"v":2},{"v":1},{"v":None}]


def test_portal_model_is_held_out_and_missing_is_explicit():
    from stats_site.analytics_portal import fit_session_model,heldout_model,build_report
    early=[portal_game(i,1) for i in range(65)]
    late=[portal_game(i,2) for i in range(5)]
    assert fit_session_model(early)["model"] is None
    train=fit_session_model(early+late)
    assert train["model"] is not None and train["cutoff"]==1
    assert heldout_model(early[0],train) is None
    assert heldout_model(late[0],train) is train["model"]
    results=build_report(early+late,"expected",{"week":"2"},{},train)["rows"]
    assert results and sum(r["event_n"] for r in results)==8*len(late)
    assert all(r["value_n"]<=r["event_n"] for r in results)
    old=portal_game()
    for p in old["result"]["play_by_play"]:p.pop("analytics_before",None)
    assert build_report([old],"scoring",{}, {})["rows"][0]["audited"]==1
    assert build_report([old],"expected",{}, {})["rows"]==[]


def test_player_comparison_qualifies_by_position_and_metric():
    import json
    from stats_site.analytics_portal import player_compare,comparison
    players=[{"team":"A","name":str(i),"position":"Viper","touches":20,"games_played":3,
              "war":float(i),"yards_per_touch":i,"kick_att":0} for i in range(5)]
    players.append({"team":"B","name":"Other","position":"Keeper","touches":20,"war":999})
    selected=[json.dumps(["A","4"],separators=(",",":"))]
    rows=player_compare(players,selected)
    war=next(r for r in rows if r["metric"]=="WAR")["values"][0]
    assert war["peers"]==5 and war["percentile"]==90
    kick=next(r for r in rows if r["metric"]=="Kick accuracy")["values"][0]
    assert kick["value"] is None and kick["percentile"] is None
    teams=[{"team":"A","games":2,"turnover_margin":2},{"team":"B","games":1,"turnover_margin":2},{"team":"C","games":2,"turnover_margin":0}]
    margin=next(r for r in comparison(teams,["A"]) if r["metric"]=="Turnover margin/game")
    assert margin["values"][0]["value"]==1 and margin["values"][0]["percentile"]==50
