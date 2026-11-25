"""Read-only Viperball analytics portal. The live session is the data source.

Keep observed scoreboard totals separate from experimental, held-out values.
All rows are derived from completed games; historical missing fields remain None.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from engine.analytics_events import build_events, label_states
from engine.empirical_ep import fit, estimate, event_epa, alternatives, context_decomposition
from engine.dtw import calculate_game_dtw
from engine.box_score_ledger import scoring_ledger, reconcile_drive_scoring

VIEWS = {
    "overview":"Overview", "players":"Players", "teams":"Teams", "scoring":"Scoring",
    "expected":"Expected points", "decisions":"Decision value", "delta":"Delta & bonus",
    "dtw":"Deserve to Win", "plays":"Play finder", "drives":"Drive finder",
    "compare":"Team compare", "player_compare":"Player compare", "glossary":"Glossary",
}
ZONES = ("Own 1–19","Own 20–39","40–59","Opp 40–21","Opp 20–1")
PLAY_GROUPS={"raw":"Individual plays","team":"Possession team","opponent":"Opponent","down":"Down","zone":"Field zone","action":"Play type","family":"Play family","result":"Outcome","margin":"Score state","bucket":"Drive context","offense_school":"Offensive school","defense_school":"Defensive school","week":"Week"}
DRIVE_GROUPS={k:v for k,v in PLAY_GROUPS.items() if k not in ("down","action","family")}
DRIVE_GROUPS.update(raw="Individual drives",origin="Possession origin")
SPLIT_COLS=[("split","Split"),("n","Observations"),("yards","Total yds"),("yards_per","Yds/obs"),("points","Total pts"),("points_per","Pts/obs"),("ep_n","EP n"),("expected","Mean EP"),("epa_n","EPA n"),("epa","Mean EPA")]
ACTIONS = ("continue","drop_kick","place_kick","punt")
METHODS = ("rush_td","lateral_td","kp_td","return_td","dk","pk","safety","pindown","bell","other")
COLS = {
    "teams":[("team","Team"),("games","G"),("points","PF"),("against","PA"),("ppg","PF/G"),("papg","PA/G"),
             ("drives","Drives"),("ppd","Off PPD"),("opp_ppd","Opp PPD"),("turnover_margin","TO±"),("kick_pct","Kick %")],
    "scoring":[("team","Team"),("games","G"),("audited","Audited G"),("points","PF"),
               ("rush_td","Rush TD pts"),("lateral_td","Lat TD pts"),("kp_td","KP TD pts"),("return_td","Ret TD pts"),
               ("dk","Snap pts"),("pk","FG pts"),("safety","Safety pts"),("pindown","Pindown pts"),("bell","Bell pts"),
               ("other","Unknown pts"),("drive_points","Drive pts"),("non_drive_points","Non-drive pts"),("gap","Unaudited pts")],
    "expected":[("team","Team"),("value_n","EP n"),("event_n","Events"),("coverage","EP %"),
                ("expected","Mean EP"),("realized","Actual net"),("epa","Mean EPA"),("epa_n","EPA n"),("legacy_epa","Legacy EPA/play")],
    "decisions":[("team","Team"),("action","Action"),("n","Decisions"),("supported","Compared"),
                 ("coverage","Support %"),("value","Obs. value"),("above","Above continue"),("above_n","Ref n"),("regret","Regret")],
    "delta":[("team","Team"),("bucket","Context"),("drives","Drives"),("points","Drive pts"),
             ("ppd","PPD"),("score_pct","TD/kick %"),("delta_n","Delta n"),("delta_eligible","Delta eligible"),("bonus_n","Bonus n"),("bonus_eligible","Bonus eligible"),
             ("delta_value","Delta value"),("bonus_value","Bonus context")],
    "dtw":[("team","Team"),("games","G"),("wins","Wins"),("xwins","DTW xW"),("luck","W−xW"),
           ("upsets","Upsets won"),("raw","Raw edge"),("delta_edge","Delta edge"),("bonus_edge","Bonus edge"),
           ("candidate","Research xW"),("candidate_n","Research G"),("matched_legacy","Matched DTW xW")],
    "plays":[("week","Week"),("team","Possession"),("opponent","Opponent"),("quarter","Q"),("clock","Clock"),
             ("down","Down"),("distance","To go"),("field","Yard line"),("action","Play"),("result","Result"),
             ("family","Family"),("offense_school","Offense"),("defense_school","Defense"),("pressure","Pressure"),
             ("yards","Yds"),("points","Net pts"),("expected","Exp net"),("epa","EPA"),("description","Play description")],
    "drives":[("week","Week"),("team","Team"),("opponent","Opponent"),("quarter","Q"),("field","Start"),
              ("bucket","Context"),("origin","Origin"),("plays","Plays"),("yards","Yds"),("result","Result"),
              ("points","Off pts"),("expected","Exp net"),("delta_value","Delta value"),("bonus_value","Bonus context")],
}
DEFAULT_SORT={"teams":"ppg","scoring":"points","expected":"epa","decisions":"n","delta":"ppd",
              "dtw":"xwins","plays":"week","drives":"week"}


def zone(fp):
    if fp is None:return None
    return max(0,min(4,int(fp)//20))


def ratio(a,b,scale=1):
    return round(a/b*scale,3) if b else None


def safe_number(x):
    return x if isinstance(x,(int,float)) else None


def games_for(season, session_id=None):
    """Match the box-score route's week/index addressing exactly."""
    counters=defaultdict(int)
    for kind,games in (("regular",season.schedule),("playoff",getattr(season,"playoff_bracket",[]) or []),
                       ("bowl",[b.game for b in (getattr(season,"bowl_games",[]) or [])])):
        for g in games:
            key=(kind,g.week);idx=counters[key];counters[key]+=1
            if not g.completed:continue
            fr=getattr(g,"full_result",None)
            if not fr and session_id:
                try:
                    from engine.db import load_box_score
                    fr=load_box_score(session_id,g.week,g.home_team,g.away_team)
                except Exception:
                    fr=None
            yield {"id":f"{kind}:{g.week}:{idx}","kind":kind,"week":g.week,"idx":idx,
                   "home":g.home_team,"away":g.away_team,"result":fr,
                   "home_score":g.home_score,"away_score":g.away_score}


def matching_games(games,filters):
    for g in games:
        if filters.get("scope") not in (None,"","all"):
            if filters["scope"]=="postseason" and g["kind"]=="regular":continue
            if filters["scope"]=="regular" and g["kind"]!="regular":continue
        if filters.get("week") and str(g["week"])!=str(filters["week"]):continue
        if filters.get("match") and str(g["idx"])!=str(filters["match"]):continue
        if filters.get("team") and filters["team"] not in (g["home"],g["away"]):continue
        if filters.get("opponent") and filters["opponent"] not in (g["home"],g["away"]):continue
        yield g


def team_ok(g,side,filters,conferences):
    team=g[side];opp=g["away" if side=="home" else "home"]
    return ((not filters.get("team") or team==filters["team"])
            and (not filters.get("opponent") or opp==filters["opponent"])
            and (not filters.get("conference") or conferences.get(team)==filters["conference"]))


def contract_for(g):
    fr=g["result"]
    if not fr:return None
    c=build_events(fr,g["id"])
    if not c.get("available") or not c.get("score_consistent"):return None
    return c


def fit_session_model(games):
    """Train only on earlier regular-season weeks, never on displayed holdout.

    Limit training to 120 games chosen by stable hash for bounded request cost.
    The model is experimental, local to the season and distinct from CI's
    national research corpus. No on-disk model or other session is loaded.
    """
    weeks=sorted({g["week"] for g in games if g["kind"]=="regular" and g["result"]})
    if len(weeks)<2:return {"model":None,"cutoff":None,"train_games":0,"reason":"At least two completed weeks are needed."}
    cutoff=weeks[(len(weeks)-1)//2]
    early=[g for g in games if g["kind"]=="regular" and g["week"]<=cutoff and g["result"]
           and g["result"].get("analytics_contract_version")==1]
    early.sort(key=lambda g:sha256(g["id"].encode()).hexdigest())
    ep_games=[g for g in early if int(sha256(g["id"].encode()).hexdigest()[:8],16)%4!=0][:120]
    dtw_games=[g for g in early if int(sha256(g["id"].encode()).hexdigest()[:8],16)%4==0][:120]
    n=0
    def rows():
        nonlocal n
        for g in ep_games:
            c=contract_for(g)
            if not c:continue
            labels=label_states(c)
            if not labels:continue
            n+=1
            for r in labels:yield {**r,"game_id":g["id"]}
    model=fit(rows())
    if n<8 or not model["states"]:
        return {"model":None,"cutoff":cutoff,"train_games":n,"reason":"Not enough new-contract games with supported state cells."}
    # DTW research fit uses separate earlier games, never EP training games
    # or later games. Sparse coverage may make it unavailable.
    from engine.dtw_research import fit as fit_dtw
    candidate_rows=[]
    for g in dtw_games:
        fr=g["result"];st=fr.get("stats",{})
        old=calculate_game_dtw(fr,st.get("home",{}).get("viperball_metrics"),st.get("away",{}).get("viperball_metrics"))
        features=dtw_features(g,model,old)
        if features:
            outcome=.5 if g["home_score"]==g["away_score"] else float(g["home_score"]>g["away_score"])
            candidate_rows.append({"features":features,"outcome":outcome})
    dtw_model=fit_dtw(candidate_rows,("exchange_epa","turnover_margin","stop_rate","kick_pass_pct","kicking_eff"))
    return {"model":model,"cutoff":cutoff,"train_games":n,"dtw_model":dtw_model,
            "dtw_train_games":len(candidate_rows),"reason":None}


def dtw_features(g,model,old):
    from engine.dtw_research import feature_vector
    from engine.viperball_metrics import calculate_to_margin
    c=contract_for(g)
    if not c or c["missing_states"] or c["state_score_mismatches"]:return None
    count=0;total=0.;events=0
    for row in c["events"]:
        s=row.get("before_state")
        if not s:continue
        events+=1
        e=event_epa(model,row)
        if e:
            count+=1;total+=e["epa"]*(1 if s["possession"]=="home" else -1)
    return feature_vector({"dtw_edges":old["edges"],"turnover_margin":calculate_to_margin(g["result"]["play_by_play"],"home")},
                          {"epa_coverage":count/max(1,events),"epa_home_per_event":total/count if count else None})


def heldout_model(g,training):
    return training["model"] if training.get("model") and (g["kind"]!="regular" or g["week"]>training["cutoff"]) else None


def play_matches(row,filters):
    if filters.get("q") and row.get("description") is not None:
        if filters["q"].casefold() not in " ".join(str(row.get(k,"")) for k in ("team","opponent","description","result")).casefold():return False
    for key in ("down","quarter","zone","action","result","margin","bucket","family","offense_school","defense_school","distance_band","pressure","origin"):
        if filters.get(key) not in (None,"") and str(row.get(key))!=str(filters[key]):return False
    return True


def distance_band(distance):
    if distance is None:return None
    return "short" if distance<=3 else "medium" if distance<=10 else "long"


def play_rows(g,contract,training,filters,conferences):
    if not contract:return
    raw=g["result"].get("play_by_play",[])
    model=heldout_model(g,training) if not contract["missing_states"] and not contract["state_score_mismatches"] else None
    for r,p in zip(contract["events"],raw):
        s=r.get("before_state") or {}
        side=r.get("snap_possession")
        if side not in ("home","away"):
            # Old logs may have only a mutable post-play possession. Do not
            # assign an ambiguous turnover/return to an offense.
            if p.get("result") not in ("gain","first_down","successful_kick"):continue
            side=p.get("possession")
        if side not in ("home","away") or r["marker"] or not team_ok(g,side,filters,conferences):continue
        sign=1 if side=="home" else -1
        fp=s.get("field_position",p.get("field_position"))
        diff=sign*(r["score_before"]["home"]-r["score_before"]["away"])
        row={"week":g["week"],"idx":g["idx"],"team":g[side],"opponent":g["away" if side=="home" else "home"],
             "quarter":r["quarter"],"clock":r["clock"],"down":s.get("down",p.get("down")),
             "distance":s.get("yards_to_go",p.get("yards_to_go")),"field":fp,"zone":zone(fp),
             "action":p.get("play_type"),"result":r["result"],"yards":p.get("yards"),"points":sign*r["net_home"],
             "family":p.get("play_family"),"offense_school":g["result"].get(side+"_style"),
             "defense_school":g["result"].get(("away" if side=="home" else "home")+"_defense_style"),
             "distance_band":distance_band(s.get("yards_to_go",p.get("yards_to_go"))),
             "pressure":("yes" if p["rush_event"].get("pressure") else "no") if p.get("rush_event") is not None else None,
             "origin":r.get("restart"),
             "description":p.get("description",""),"bucket":r.get("delta_bucket"),
             "margin":"leading" if diff>0 else "trailing" if diff<0 else "tied","expected":None,"epa":None}
        if not play_matches(row,filters):continue
        if model and s:
            value=estimate(model,s)
            e=event_epa(model,r)
            row["expected"]=round(value["value"],3) if value else None
            row["epa"]=round(e["epa"],3) if e else None
        yield row


def drive_rows(g,contract,training,filters,conferences):
    fr=g["result"]
    if not fr:return
    model=heldout_model(g,training) if contract and not contract["missing_states"] and not contract["state_score_mismatches"] else None
    by_id=defaultdict(list)
    if contract:
        for r in contract["events"]:
            by_id[r["drive_id"]].append(r)
    seen_possessions=set()
    for i,d in enumerate(fr.get("drive_summary",[])):
        side=d.get("team")
        if side not in ("home","away") or not team_ok(g,side,filters,conferences):continue
        cost=d.get("delta_cost",0)
        bucket="bonus" if d.get("bonus_drive") else "penalty_kill" if cost>0 else "power_play" if cost<0 else "neutral"
        ev=by_id.get(f'{g["id"]}:d{i}',[])
        s=next((r["before_state"] for r in ev if r["before_state"]),None)
        new_possession=bool(s and (s["possession"],s["possession_id"]) not in seen_possessions)
        if s:seen_possessions.add((s["possession"],s["possession_id"]))
        scored=any(e["drive_credit"] and e["method"] in ("rush_td","lateral_td","kp_td","dk","pk") for r in ev for e in r["score_events"])
        row={"week":g["week"],"idx":g["idx"],"team":g[side],"opponent":g["away" if side=="home" else "home"],
             "quarter":d.get("quarter"),"field":d.get("start_yard_line"),"zone":zone(d.get("start_yard_line")),
             "bucket":bucket,"origin":d.get("possession_origin"),"plays":d.get("plays"),"yards":d.get("yards"),
             "result":d.get("result"),"points":d.get("offensive_points"),"expected":None,"delta_value":None,"bonus_value":None,
             "offense_school":fr.get(side+"_style"),"defense_school":fr.get(("away" if side=="home" else "home")+"_defense_style"),
             "td_or_kick":scored if ev else None,
             "delta_eligible":bool(new_possession and s.get("origin")=="score_restart"),
             "bonus_eligible":bool(new_possession and (s.get("bonus_active") or s.get("bonus_recipient") in ("home","away")))}
        if s:
            diff=(s["home_score"]-s["away_score"])*(1 if side=="home" else -1)
            row["margin"]="leading" if diff>0 else "trailing" if diff<0 else "tied"
        if not play_matches(row,filters):continue
        if model and s:
            val=estimate(model,s)
            row["expected"]=round(val["value"],3) if val else None
            if row["delta_eligible"] or row["bonus_eligible"]:
                de=context_decomposition(model,s,contract.get("restart_baseline"),row["delta_eligible"])
                if de:
                    if row["delta_eligible"]:row["delta_value"]=round(de["delta"],3)
                    if row["bonus_eligible"]:row["bonus_value"]=round(de["bonus_context"],3)
        yield row


def build_report(games,view,filters,conferences,training=None):
    """Filter first; aggregate counts and denominators from actual records."""
    training=training or {"model":None,"cutoff":None,"train_games":0,"reason":"No model requested."}
    groups=defaultdict(Counter);rows=[];heat=defaultdict(Counter);coverage=Counter()
    group=filters.get("group","raw")
    split_groups=defaultdict(Counter)
    def collect(row):
        if group=="raw":
            rows.append(row);return
        key=row.get(group)
        b=split_groups[key];b["n"]+=1
        for field in ("yards","points","expected","epa"):
            v=safe_number(row.get(field))
            if v is not None:b[field]+=v;b[field+"_n"]+=1
    for g in matching_games(games,filters):
        fr=g["result"]
        coverage["games"]+=1
        if not fr:continue
        coverage["with_results"]+=1
        contract=contract_for(g) if view in ("overview","scoring","expected","decisions","delta","plays","drives") else None
        if contract:
            coverage["audited"]+=1
            coverage["new_contract"]+=int(not contract["missing_states"] and not contract["state_score_mismatches"])
        model=heldout_model(g,training)
        if view=="plays":
            for p in play_rows(g,contract,training,filters,conferences):
                collect(p)
                if p["down"] in range(1,7) and p["zone"] is not None:
                    h=heat[(p["down"],p["zone"])];h["n"]+=1;h["pts"]+=p["points"]
            continue
        if view=="drives":
            for d in drive_rows(g,contract,training,filters,conferences):collect(d)
            continue
        if view in ("delta",):
            for d in drive_rows(g,contract,training,filters,conferences):
                b=groups[(d["team"],d["bucket"])]
                b["drives"]+=1
                if d["points"] is not None:
                    b["audited"]+=1;b["points"]+=d["points"]
                    if d["td_or_kick"] is not None:
                        b["incidence_n"]+=1;b["scores"]+=int(d["td_or_kick"])
                b["delta_eligible"]+=int(d["delta_eligible"]);b["bonus_eligible"]+=int(d["bonus_eligible"])
                if d["delta_value"] is not None:
                    b["delta_n"]+=1;b["delta_value"]+=d["delta_value"]
                if d["bonus_value"] is not None:
                    b["bonus_n"]+=1;b["bonus_value"]+=d["bonus_value"]
            continue
        if view in ("expected","decisions"):
            if not contract:continue
            if contract["missing_states"] or contract["state_score_mismatches"]:model=None
            labels={}
            if model and view=="expected":
                labels={x["event_id"]:x["target"] for x in label_states(contract) if x["horizon"]==2}
            for r,p in zip(contract["events"],fr.get("play_by_play",[])):
                s=r["before_state"]
                if not s or not team_ok(g,s["possession"],filters,conferences):continue
                side=s["possession"];team=g[side]
                diff=(s["home_score"]-s["away_score"])*(1 if side=="home" else -1)
                row={"down":s["down"],"quarter":s["quarter"],"zone":zone(s["field_position"]),"action":r["action"],
                     "result":r["result"],"bucket":r["delta_bucket"],"margin":"leading" if diff>0 else "trailing" if diff<0 else "tied",
                     "family":p.get("play_family"),"offense_school":fr.get(side+"_style"),
                     "defense_school":fr.get(("away" if side=="home" else "home")+"_defense_style"),
                     "distance_band":distance_band(s.get("yards_to_go")),
                     "pressure":("yes" if p["rush_event"].get("pressure") else "no") if p.get("rush_event") is not None else None,
                     "origin":r.get("restart")}
                if not play_matches(row,filters):continue
                if view=="expected":
                    if not model:continue
                    b=groups[team];b["event_n"]+=1
                    v=estimate(model,s);e=event_epa(model,r)
                    if v and r["id"] in labels:
                        b["value_n"]+=1;b["expected"]+=v["value"];b["realized"]+=labels[r["id"]]
                        h=heat[(s["down"],zone(s["field_position"]))];h["n"]+=1;h["pts"]+=v["value"]
                    if e:
                        b["epa_n"]+=1;b["epa"]+=e["epa"]
                        legacy=safe_number(p.get("epa"))
                        if legacy is not None:b["legacy_n"]+=1;b["legacy_epa"]+=legacy
                elif r["action"]:
                    if not model:continue
                    b=groups[(team,r["action"])];b["n"]+=1
                    a=alternatives(model,s,r["action"])
                    if a:
                        b["supported"]+=1;b["value"]+=a["supported"][r["action"]]["value"];b["regret"]+=a["regret"]
                        if a["above_continue"] is not None:
                            b["above_n"]+=1;b["above"]+=a["above_continue"]
            continue
        st=fr.get("stats",{})
        dtw=calculate_game_dtw(fr,st.get("home",{}).get("viperball_metrics"),st.get("away",{}).get("viperball_metrics")) if view=="dtw" else None
        candidate=None
        if dtw and model and training.get("dtw_model"):
            from engine.dtw_research import predict
            candidate=predict(training["dtw_model"],dtw_features(g,model,dtw))
        for side in ("home","away"):
            if not team_ok(g,side,filters,conferences):continue
            opp="away" if side=="home" else "home";team=g[side]
            b=groups[team];a=st.get(side,{});other=st.get(opp,{})
            score=g[side+"_score"];against=g[opp+"_score"]
            if score is None or against is None:continue
            b["games"]+=1;b["points"]+=score;b["against"]+=against
            if view=="dtw":
                x=dtw[side+"_dtw"];sign=1 if side=="home" else -1
                win=1 if score>against else .5 if score==against else 0
                b["wins"]+=win;b["xwins"]+=x;b["upsets"]+=int(win==1 and dtw["upset"])
                if candidate is not None:
                    b["candidate_n"]+=1;b["candidate"]+=candidate if side=="home" else 1-candidate;b["matched_legacy"]+=x
                c=dtw["component_edges"]
                b["raw"]+=sign*c["raw_performance"];b["delta_edge"]+=sign*c["delta_context"];b["bonus_edge"]+=sign*c["turnover_bonus_conversion"]
                continue
            metrics=a.get("viperball_metrics") or {}
            b["turnover_margin"]+=metrics.get("to_margin",0) or 0
            b["kicks"]+=(a.get("drop_kicks_attempted",0) or 0)+(a.get("place_kicks_attempted",0) or 0)
            b["made"]+=(a.get("drop_kicks_made",0) or 0)+(a.get("place_kicks_made",0) or 0)
            recon=a.get("scoring_reconciliation") or {};orecon=other.get("scoring_reconciliation") or {}
            if recon.get("score_consistent"):
                b["drive_points"]+=recon["drive_points"];b["non_drive_points"]+=recon["non_drive_points"]
                b["drives"]+=sum(d.get("team")==side for d in fr.get("drive_summary",[]))
            if orecon.get("score_consistent"):
                b["opp_drive_points"]+=orecon["drive_points"]
                b["opp_drives"]+=sum(d.get("team")==opp for d in fr.get("drive_summary",[]))
            if contract:
                b["audited"]+=1;b["audited_score"]+=score
                for r in contract["events"]:
                    for e in r["score_events"]:
                        if e["team"]==side:b[e["method"]]+=e["points"]
    for key,b in groups.items():
        team=key[0] if isinstance(key,tuple) else key
        if view=="expected":
            rows.append({"team":team,"value_n":b["value_n"],"event_n":b["event_n"],"coverage":ratio(b["value_n"],b["event_n"],100),
                         "expected":ratio(b["expected"],b["value_n"]),"realized":ratio(b["realized"],b["value_n"]),
                         "epa":ratio(b["epa"],b["epa_n"]),"epa_n":b["epa_n"],"legacy_epa":ratio(b["legacy_epa"],b["legacy_n"])})
        elif view=="decisions":
            rows.append({"team":team,"action":key[1],"n":b["n"],"supported":b["supported"],"coverage":ratio(b["supported"],b["n"],100),
                         "value":ratio(b["value"],b["supported"]),"above":ratio(b["above"],b["above_n"]),"above_n":b["above_n"],"regret":ratio(b["regret"],b["supported"])})
        elif view=="delta":
            rows.append({"team":team,"bucket":key[1],"drives":b["drives"],"points":b["points"] if b["audited"] else None,
                         "ppd":ratio(b["points"],b["audited"]),"score_pct":ratio(b["scores"],b["incidence_n"],100),
                         "delta_eligible":b["delta_eligible"],"delta_n":b["delta_n"],
                         "bonus_eligible":b["bonus_eligible"],"bonus_n":b["bonus_n"],
                         "delta_value":ratio(b["delta_value"],b["delta_n"]),"bonus_value":ratio(b["bonus_value"],b["bonus_n"])})
        elif view=="dtw":
            rows.append({"team":team,"games":b["games"],"wins":b["wins"],"xwins":round(b["xwins"],2),"luck":round(b["wins"]-b["xwins"],2),
                         "upsets":b["upsets"],"raw":ratio(b["raw"],b["games"]),"delta_edge":ratio(b["delta_edge"],b["games"]),"bonus_edge":ratio(b["bonus_edge"],b["games"]),
                         "candidate_n":b["candidate_n"],"candidate":round(b["candidate"],3) if b["candidate_n"] else None,
                         "matched_legacy":round(b["matched_legacy"],3) if b["candidate_n"] else None})
        elif view=="scoring":
            rows.append({"team":team,"games":b["games"],"points":b["points"],"audited":b["audited"],
                         **{m:b[m] if b["audited"] else None for m in METHODS},
                         "drive_points":b["drive_points"] if b["drives"] else None,"non_drive_points":b["non_drive_points"] if b["drives"] else None,
                         "gap":b["points"]-b["audited_score"]})
        else:
            rows.append({"team":team,"games":b["games"],"points":b["points"],"against":b["against"],"ppg":ratio(b["points"],b["games"]),
                         "papg":ratio(b["against"],b["games"]),"drives":b["drives"],"ppd":ratio(b["drive_points"],b["drives"]),
                         "opp_ppd":ratio(b["opp_drive_points"],b["opp_drives"]),"turnover_margin":b["turnover_margin"],
                         "kick_pct":ratio(b["made"],b["kicks"],100)})
    if view in ("plays","drives") and group!="raw":
        for key,b in split_groups.items():
            label=ZONES[key] if group=="zone" and isinstance(key,int) and 0<=key<len(ZONES) else str(key).replace("_"," ").title() if key is not None and group not in ("team","opponent") else key or "Unknown"
            rows.append({"split":label,"group_key":key,"n":b["n"],"yards":b["yards"] if b["yards_n"] else None,
                         "yards_per":ratio(b["yards"],b["yards_n"]),"points":b["points"] if b["points_n"] else None,
                         "points_per":ratio(b["points"],b["points_n"]),"ep_n":b["expected_n"],"expected":ratio(b["expected"],b["expected_n"]),
                         "epa_n":b["epa_n"],"epa":ratio(b["epa"],b["epa_n"])})
    grid=[[{"n":heat[(d,z)]["n"],"value":ratio(heat[(d,z)]["pts"],heat[(d,z)]["n"]) if heat[(d,z)]["n"]>=10 else None}
           for z in range(5)] for d in range(1,7)]
    return {"rows":rows,"coverage":dict(coverage),"heatmap":grid}


def sorted_rows(rows,key,reverse=True):
    # Sort numeric and text columns safely; unknowns always at the bottom.
    known=[r for r in rows if r.get(key) is not None]
    missing=[r for r in rows if r.get(key) is None]
    return sorted(known,key=lambda r:r[key],reverse=reverse)+missing


def comparison(rows,selected):
    """Peer percentiles with explicit direction and minimum peer count."""
    result=[]
    for key,label,lower in (("ppg","Points/game",False),("papg","Points allowed/game",True),("ppd","Offensive PPD",False),
                           ("opp_ppd","Opponent PPD",True),("turnover_margin","Turnover margin/game",False),("kick_pct","Kick accuracy",False)):
        def value(r):
            return ratio(r.get(key,0),r.get("games",0)) if key=="turnover_margin" and r.get(key) is not None else r.get(key)
        peers=[value(r) for r in rows if value(r) is not None]
        values=[]
        for name in selected:
            row=next((r for r in rows if r["team"]==name),{})
            v=value(row)
            percentile=None
            if v is not None and len(peers)>=3:
                better=sum(x>v if lower else x<v for x in peers);equal=sum(x==v for x in peers)
                percentile=round(100*(better+.5*equal)/len(peers))
            values.append({"team":name,"value":v,"percentile":percentile})
        result.append({"metric":label,"peers":len(peers),"values":values})
    return result


def player_compare(rows, selected):
    """Position-matched percentile comparisons, with metric-specific eligibility."""
    from json import dumps
    identities={dumps([p["team"],p["name"]],ensure_ascii=False,separators=(",",":")):p for p in rows}
    chosen=[identities[x] for x in selected if x in identities][:4]
    metrics=[
        ("war","WAR",lambda p:p.get("touches",0)>=5),
        ("yards_per_touch","Yards/touch",lambda p:p.get("touches",0)>=10),
        ("wpa_per_play","Legacy WPA/play",lambda p:p.get("plays_involved",0)>=10),
        ("zbr","Zeroback rating",lambda p:p.get("zbr",0)>0),
        ("vpr","Viper rating",lambda p:p.get("vpr",0)>0),
        ("tackles","Tackles",lambda p:p.get("games_played",0)>0),
        ("sacks","Sacks",lambda p:p.get("games_played",0)>0),
        ("kick_accuracy","Kick accuracy",lambda p:p.get("kick_att",0)>=5),
    ]
    def value(p,key,qualifies):
        if not qualifies(p):return None
        if key=="kick_accuracy":return ratio(p.get("kick_made",0),p["kick_att"],100)
        return safe_number(p.get(key))
    result=[]
    for key,label,qualifies in metrics:
        vals=[]
        for p in chosen:
            peers=[v for r in rows if r.get("position")==p.get("position") and (v:=value(r,key,qualifies)) is not None]
            v=value(p,key,qualifies)
            pct=round(100*(sum(x<v for x in peers)+.5*sum(x==v for x in peers))/len(peers)) if v is not None and len(peers)>=3 else None
            vals.append({"team":p["name"]+" · "+p["team"],"value":v,"percentile":pct,"peers":len(peers)})
        result.append({"metric":label,"values":vals,"peers":None})
    return result
