"""AN-02: deterministic, read-only event adapter for finalized game results."""
from collections import defaultdict
from .box_score_ledger import scoring_ledger, DRIVE_METHODS

VERSION = 1
SIDES = ("home", "away")
MARKERS = {"bonus_possession", "overtime"}


def half(q):
    return (q-1)//2 if q <= 4 else q-3


def action_of(play):
    kind = play.get("play_type")
    if kind in ("drop_kick", "place_kick", "punt"):
        return kind
    if kind not in MARKERS | {"penalty", "kneel", None}:
        return "continue"
    return None


def build_events(game, game_id):
    """IDs are scoped by caller-supplied unique game ID, never play_number.

    after_state is the next observed pre-resolution state, including restart
    processing. It is not the immediate post-snap spot. Unknowns stay null.
    """
    plays = game.get("play_by_play", [])
    drives = game.get("drive_summary", [])
    final = {s:game.get("final_score",{}).get(s,{}).get("score") for s in SIDES}
    scores = []
    ledger = scoring_ledger(plays,final,events=scores)
    if ledger is None:
        return {"version":VERSION,"game_id":game_id,"available":False,"reason":"missing_score_snapshots","events":[]}
    if any(final[s] is None for s in SIDES):
        return {"version":VERSION,"game_id":game_id,"available":False,"reason":"missing_final_score","events":[]}
    owners = {}
    span_valid = True
    for i,d in enumerate(drives):
        a,b=d.get("play_log_start"),d.get("play_log_end")
        if not (isinstance(a,int) and isinstance(b,int) and 0<=a<=b<=len(plays)):
            span_valid=False
            continue
        for j in range(a,b):
            if j in owners:
                span_valid=False
            owners[j]=i
    if not span_valid:
        owners={}
    by_play=defaultdict(list)
    for i,side,method,points in scores:
        d=drives[owners[i]] if i in owners else {}
        p=plays[i]
        # The score ledger identifies the scoring side, not necessarily a
        # specific player. Do not treat players[0] as the scorer.
        unit=("offense" if method in {"rush_td","lateral_td","kp_td"} else
              "special_teams" if method in {"dk","pk","pindown"} else
              "defense" if method=="safety" else
              "defense" if method=="return_td" and p.get("result")=="int_return_td" else
              "special_teams" if method=="return_td" and p.get("play_type") in {"punt","drop_kick","place_kick"} else None)
        st=p.get("special_teams_event") or {}
        player_label=None
        if method in {"dk","pk"} and st.get("kicking_side")==side:
            player_label=st.get("kicker")
        elif method=="return_td" and unit=="special_teams" and st.get("kicking_side")!=side:
            player_label=st.get("returner")
        by_play[i].append({"id":f"{game_id}:p{i}:s{len(by_play[i])}","team":side,
            "method":method,"points":points,"unit":unit,"player_id":None,"player_label":player_label,
            "drive_credit":bool(d and d.get("team")==side and method in DRIVE_METHODS)})
    rows=[]
    prev={s:0. for s in SIDES}
    for i,p in enumerate(plays):
        d=drives[owners[i]] if i in owners else {}
        before=p.get("analytics_before")
        if before:
            before=dict(before)
            side=before["possession"];opp="away" if side=="home" else "home"
            before["offense_school"]=game.get(side+"_style")
            before["defense_school"]=game.get(opp+"_defense_style")
            expectation=game.get("coach_expectation_home")
            before["strength_band"]=int((expectation if side=="home" else 1-expectation)*5) if expectation is not None else None
        after={s:float(p[s+"_score"]) for s in SIDES}
        marker=p.get("play_type") in MARKERS
        nullified=bool((p.get("penalty") or {}).get("nullified"))
        row={"id":f"{game_id}:p{i}","sequence":i,"play_number":p.get("play_number"),
             "drive_id":f"{game_id}:d{owners[i]}" if i in owners else None,
             "quarter":p.get("quarter"),"clock":before.get("clock") if before else p.get("time_remaining"),
             "before_state":before,"resolution_state":p.get("analytics_resolution"),"after_state":None,
             "score_before":dict(prev),"score_after":after,
             "snap_possession":before.get("possession") if before else p.get("snap_possession"),
             "possession_after_resolution":(p.get("analytics_resolution") or {}).get("possession"),
             "next_possession":None,"bonus_source_event_id":None,
             "restart":d.get("possession_origin") or p.get("possession_origin"),
             "delta_cost":d.get("delta_cost"),"bonus_drive":d.get("bonus_drive"),
             "result":p.get("result"),"play_type":p.get("play_type"),
             "penalty":p.get("penalty"),"nullified":nullified,"marker":marker,
             "state_score_matches":not before or all(before.get(s+"_score")==prev[s] for s in SIDES),
             "action":action_of(p) if before and not marker and not nullified and not p.get("analytics_terminal_kick") else None,
             "score_events":by_play[i],"net_home":after["home"]-prev["home"]-after["away"]+prev["away"]}
        rows.append(row);prev=after
    # Link only the next observed state in the same half. Markers remain
    # explicit in the audit stream; no state is fabricated for older games.
    next_state=None
    for row in reversed(rows):
        before=row["before_state"]
        if before and next_state and half(before["quarter"])==half(next_state["quarter"]):
            row["after_state"]=next_state
            row["next_possession"]=next_state["possession"]
        if before:
            next_state=before
    # Attribute a pending bonus only to a logged interception followed by
    # the actual recipient in the next recorded state. Clear at half/end
    # or cancellation. Marker awards carry the confirmed source when known.
    source=None
    for row in rows:
        a,b=row["before_state"],row["after_state"]
        if row["marker"]:
            if row["play_type"]=="bonus_possession":
                row["bonus_source_event_id"]=source
                source=None
            elif row["play_type"]=="overtime":
                source=None
            continue
        if a and a.get("bonus_recipient") not in SIDES and not a.get("bonus_active"):
            source=None
        if a and (a.get("bonus_recipient") in SIDES or a.get("bonus_active")):
            row["bonus_source_event_id"]=source
        if (a and b and row["result"] in ("kick_pass_intercepted","lateral_intercepted","int_return_td")
                and not row["nullified"] and a.get("bonus_recipient") not in SIDES
                and not a.get("bonus_active") and b.get("bonus_recipient") in SIDES):
            source=row["id"]
        if b is None or (b.get("bonus_recipient") not in SIDES and not b.get("bonus_active")):
            source=None
    totals={s:sum(e["points"] for row in rows for e in row["score_events"] if e["team"]==s) for s in SIDES}
    score_ok=all(ledger[s]["score_consistent"] and totals[s]==final[s] for s in SIDES)
    return {"version":VERSION,"game_id":game_id,"available":True,"score_consistent":score_ok,
            "drive_spans_valid":span_valid,"final":final,"score_totals":totals,
            "missing_states":sum(not r["before_state"] and not r["marker"] for r in rows),
            "unknown_score_units":sum(e["unit"] is None for r in rows for e in r["score_events"]),
            "state_score_mismatches":sum(not r["state_score_matches"] for r in rows),
            "restart_baseline":game.get("analytics_restart_baseline"),
            "events":rows}


def possession_boundary(a,b):
    return (a["possession_id"]!=b["possession_id"] or a["possession"]!=b["possession"]
            or half(a["quarter"])!=half(b["quarter"]))


def label_states(contract):
    """Net points through current and next possession, or end of half.

    Same-side restarts count as new possessions; quarter fragments do not.
    Values are from the pre-state ball owner's perspective. Both horizons
    (one or two possessions remaining) are modeled to make EPA telescopic.
    """
    if not contract.get("score_consistent") or contract.get("missing_states") or contract.get("state_score_mismatches"):
        return []
    rows=contract["events"]
    # Exclude synthetic scoreless markers. If a marker scores, the contract
    # still audits it but cannot supply a supported modeling horizon.
    if any(r["marker"] and r["net_home"] for r in rows):
        return []
    rows=[r for r in rows if r["before_state"]]
    out=[]
    for i,row in enumerate(rows):
        state=row["before_state"]
        sign=1 if state["possession"]=="home" else -1
        total=0.; segments=1
        for j in range(i,len(rows)):
            cur=rows[j]
            if j>i:
                a,b=rows[j-1]["before_state"],cur["before_state"]
                if half(a["quarter"])!=half(b["quarter"]):
                    break
                if possession_boundary(a,b):
                    if segments==1:
                        out.append({"event_id":row["id"],"state":state,"horizon":1,"target":sign*total,"action":row["action"]})
                    segments+=1
                    if segments>2:break
            total+=cur["net_home"]
        if segments==1:
            out.append({"event_id":row["id"],"state":state,"horizon":1,"target":sign*total,"action":row["action"]})
        out.append({"event_id":row["id"],"state":state,"horizon":2,"target":sign*total,"action":row["action"]})
    return out
