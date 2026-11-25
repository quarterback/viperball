"""EPA-02/03/04: experimental, offline empirical value model.

Never used to choose a live play or overwrite legacy EPA. Train on disjoint
whole games; values are expected net points for one or two possessions.
"""
from collections import defaultdict
from math import sqrt
from .analytics_events import possession_boundary, half
from .epa import calculate_ep

VERSION = "net-possession-exchange-v1"
MIN_ROWS = 30
MIN_GAMES = 8
ACTIONS = ("continue","drop_kick","place_kick","punt")


def bucket(x, width):
    return int(x)//width


def state_keys(s,horizon):
    """Hierarchical pooling; do not pool across bonus states or horizons."""
    side=s["possession"]
    diff=(s["home_score"]-s["away_score"])*(1 if side=="home" else -1)
    recipient=s.get("bonus_recipient")
    bonus=(bool(s.get("bonus_active")), "own" if recipient==side else
           "opp" if recipient in ("home","away") else "none", s.get("bonus_wait",-1) if recipient in ("home","away") else -1)
    fp=s["field_position"]; down=s["down"]; ytg=s["yards_to_go"]
    clock=s["clock"]; q=s["quarter"]
    common=(horizon,bonus)
    situ=(down,bucket(fp,10),bucket(ytg,5),bucket(diff,10),
          half(q),bucket(clock,180),s.get("origin"))
    # Fixed context for observational action comparisons.
    yield ("full",common,situ,s.get("offense_school"),s.get("defense_school"),s.get("strength_band"))
    yield ("situation",common,situ)
    yield ("down_distance",common,down,bucket(fp,10),bucket(ytg,5))
    yield ("field_down",common,down,bucket(fp,20))


def key_text(key):
    return repr(key)


def _add(store,key,game,y):
    cell=store[key].setdefault(game,[0,0.,0.])
    cell[0]+=1;cell[1]+=y;cell[2]+=y*y


def _summaries(store,min_rows,min_games):
    result={}
    for key, games in store.items():
        n=sum(g[0] for g in games.values()); g=len(games)
        if n<min_rows or g<min_games:continue
        total=sum(v[1] for v in games.values()); mu=total/n
        # Clustered SE for the play-weighted mean, not iid play errors.
        se=sqrt(g/(g-1)*sum((v[1]-mu*v[0])**2 for v in games.values()))/n if g>1 else None
        result[key]={"value":mu,"n":n,"games":g,"se":se}
    return result


def fit(rows,min_rows=MIN_ROWS,min_games=MIN_GAMES):
    states=defaultdict(dict);actions=defaultdict(dict)
    for row in rows:
        if row["state"].get("possession") not in ("home","away"):continue
        keys=list(state_keys(row["state"],row["horizon"]))
        for k in keys:_add(states,key_text(k),row["game_id"],row["target"])
        # Action alternatives must retain situational context. No fallback to
        # a broad field/down mean; observed selection is confounded.
        if row.get("action") in ACTIONS and row["horizon"]==2:
            for k in keys[:2]:
                _add(actions,key_text((k,row["action"])),row["game_id"],row["target"])
    return {"version":VERSION,"min_rows":min_rows,"min_games":min_games,
            "states":_summaries(states,min_rows,min_games),
            "actions":_summaries(actions,min_rows,min_games)}


def estimate(model,state,horizon=2,levels=None):
    if state is None:return None
    for k in state_keys(state,horizon):
        if levels is not None and k[0] not in levels:continue
        cell=model["states"].get(key_text(k))
        if cell:return {**cell,"level":k[0]}
    return None


def legacy_value(state,horizon):
    # Named comparison: gross fixed lookup, with a neutral opponent
    # possession subtracted for horizon two. Not the published legacy EPA.
    return calculate_ep(state["field_position"],state["down"])-(calculate_ep(20,1) if horizon==2 else 0)


def event_epa(model,row,horizon=2):
    before=row.get("before_state")
    if before is None:return None
    start=estimate(model,before,horizon)
    if start is None:return None
    after=row.get("after_state")
    remaining=horizon
    if after and possession_boundary(before,after):remaining-=1
    continuation=0.
    if after is not None and remaining>0:
        end=estimate(model,after,remaining)
        if end is None:return None
        continuation=end["value"]*(1 if after["possession"]==before["possession"] else -1)
    sign=1 if before["possession"]=="home" else -1
    return {"epa":sign*row["net_home"]+continuation-start["value"],
            "reward":sign*row["net_home"],"before":start["value"],"continuation":continuation,
            "horizon":horizon,"remaining":remaining if after else 0}


def alternatives(model,state,chosen):
    """Observed conditional means, not cloned-state causal estimates.

    All four action families are rules-legal on any normal down. Exclude
    markers, nullified snaps and forced terminal-kick paths upstream.
    Range is a feasibility/selection consideration, not a rules prohibition.
    Use a common exact context level for every supported action.
    """
    if chosen not in ACTIONS or not 1<=state.get("down",0)<=6:return None
    for k in list(state_keys(state,2))[:2]:
        values={a:model["actions"].get(key_text((k,a))) for a in ACTIONS}
        values={a:v for a,v in values.items() if v}
        if chosen not in values or len(values)<2:continue
        best=max(v["value"] for v in values.values())
        # Continue offense is the predeclared reference; no substitution
        # with the best action when the reference has no support.
        baseline=values.get("continue")
        return {"method":"observational_conditional_mean","causal":False,"level":k[0],
                "chosen":chosen,"legal_actions":list(ACTIONS),"supported":values,
                "unsupported":[a for a in ACTIONS if a not in values],
                "above_continue":values[chosen]["value"]-baseline["value"] if baseline else None,
                "regret":best-values[chosen]["value"]}
    return None


def context_decomposition(model,state,baseline,delta_restart=False):
    """Sequential conditional contrasts: neutral/no bonus -> actual field
    with no bonus -> actual bonus context. Not a causal entitlement effect.

    Keep the same score, down, time and schools. Active bonus drives cannot
    be interpreted as extra possessions lost or gained from this contrast.
    Use only matching support at the same pooling level.
    """
    if baseline is None:return None
    plain=dict(state,bonus_active=False,bonus_recipient=None,bonus_wait=-1)
    neutral=dict(plain,field_position=baseline) if delta_restart else plain
    for level in ("full","situation","down_distance","field_down"):
        a=estimate(model,neutral,2,{level}); b=estimate(model,plain,2,{level}); c=estimate(model,state,2,{level})
        if not (a and b and c):continue
        delta=b["value"]-a["value"];bonus=c["value"]-b["value"]
        return {"method":"conditional_context_contrast","causal":False,"level":level,
                "neutral_no_bonus":a,"actual_field_no_bonus":b,"actual":c,
                "delta":delta,"bonus_context":bonus,"total":c["value"]-a["value"],
                "interaction_residual":c["value"]-a["value"]-delta-bonus}
    return None
