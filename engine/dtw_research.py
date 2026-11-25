"""DTW-02 offline retrospective outcome alignment, not pregame prediction.

The public DTW remains a descriptive index. This fitted comparison uses
postgame events (including scoring), and cannot establish deservedness.
"""
import math
from collections import defaultdict

LEGACY_SIGNALS=("set_efficiency","stop_rate","success_rate","pk_score_rate",
                "epa_per_play","conversion_pct","pk_efficiency","bonus_conv",
                "kick_pass_pct","pp_conversion","kicking_eff","mess_rate","team_rating")
FEATURES=("exchange_epa","turnover_margin","delta_context","bonus_context",
          "stop_rate","kick_pass_pct","kicking_eff","team_rating")


def sigmoid(x):
    return 1/(1+math.exp(-max(-30.,min(30.,x))))


def feature_vector(record, evaluation):
    """Keep candidate families distinct; missing support is not a zero."""
    if evaluation.get("epa_coverage",0)<.75 or evaluation.get("epa_home_per_event") is None:
        return None
    old=record["dtw_edges"]
    # Context totals are available only when all eligible comparisons have
    # support; otherwise exclude the context feature, not the entire game.
    delta=evaluation.get("delta_mean")
    bonus=evaluation.get("bonus_mean")
    return {
        "exchange_epa":math.tanh(evaluation["epa_home_per_event"]/.5),
        "turnover_margin":math.tanh(record["turnover_margin"]/3),
        "delta_context":math.tanh(delta/2) if delta is not None else None,
        "bonus_context":math.tanh(bonus/2) if bonus is not None else None,
        **{k:old.get(k) for k in ("stop_rate","kick_pass_pct","kicking_eff","team_rating")},
    }


def fit(rows,features,regularization=.05,iterations=250):
    """No intercept: swapping teams complements the estimate exactly."""
    data=[(tuple(r["features"][k] for k in features),r["outcome"]) for r in rows
          if r.get("features") and all(r["features"].get(k) is not None for k in features)]
    if len(data)<30:return None
    w=[0.]*len(features)
    for _ in range(iterations):
        grad=[0.]*len(w)
        for x,y in data:
            err=sigmoid(sum(a*b for a,b in zip(w,x)))-y
            for j,v in enumerate(x):grad[j]+=err*v
        for j in range(len(w)):w[j]-=.3*(grad[j]/len(data)+regularization*w[j])
    return {"features":list(features),"weights":dict(zip(features,w)),
            "training_games":len(data),"regularization":regularization,"intercept":0}


def predict(model,features):
    if not model or not features or any(features.get(k) is None for k in model["features"]):return None
    return sigmoid(sum(model["weights"][k]*features[k] for k in model["features"]))


def metrics(pairs):
    pairs=list(pairs)
    if not pairs:return {"n":0}
    bins=defaultdict(lambda:[0,0.,0.])
    for p,y in pairs:
        b=bins[min(9,int(p*10))];b[0]+=1;b[1]+=p;b[2]+=y
    return {"n":len(pairs),"brier":sum((p-y)**2 for p,y in pairs)/len(pairs),
            "log_loss":-sum(y*math.log(max(1e-9,p))+(1-y)*math.log(max(1e-9,1-p)) for p,y in pairs)/len(pairs),
            "calibration":{str(k):{"n":n,"prediction":p/n,"observed":y/n} for k,(n,p,y) in sorted(bins.items())}}


def study(train,test):
    # Baseline 13-signal audit and independent signal ablations. Exclude
    # quarter wins from the candidate: it is a direct scoreboard proxy.
    core=("exchange_epa","turnover_margin","stop_rate","kick_pass_pct","kicking_eff")
    candidates={"core":core,"without_turnovers":tuple(k for k in core if k!="turnover_margin"),
                "without_epa":tuple(k for k in core if k!="exchange_epa"),
                "with_rating":core+("team_rating",),
                "with_context":core+("delta_context","bonus_context")}
    result={"scope":"retrospective outcome alignment; no public DTW replacement",
            "legacy_all":metrics((r["legacy"],r["outcome"]) for r in test),
            "legacy_signals":{k:metrics((sigmoid(r["edges"][k]),r["outcome"]) for r in test if k in r["edges"]) for k in LEGACY_SIGNALS},
            "models":{}}
    for name,features in candidates.items():
        model=fit(train,features)
        matched=[(p,r) for r in test if (p:=predict(model,r.get("features"))) is not None]
        result["models"][name]={"model":model,"candidate":metrics((p,r["outcome"]) for p,r in matched),
            "legacy_same_games":metrics((r["legacy"],r["outcome"]) for p,r in matched),
            "disagreements":[{"game_id":r["game_id"],"candidate":p,"legacy":r["legacy"],"outcome":r["outcome"]}
                for p,r in matched if abs(p-r["legacy"])>=.20][:25]}
    return result
