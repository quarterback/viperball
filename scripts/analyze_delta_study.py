#!/usr/bin/env python3
"""Summarize scripts/study_delta_yards.py output (paired bootstrap CIs)."""
import json, sys
from pathlib import Path
import numpy as np

src = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/delta_study") / "games.jsonl"
rows = [json.loads(l) for l in src.read_text().splitlines()]
pairs = {}
for r in rows:
    pairs.setdefault(r["n"], {})["on" if r["delta_on"] else "off"] = r
ns = sorted(n for n, p in pairs.items() if len(p) == 2)


def game_metrics(r):
    diff = r["h"] - r["a"]
    fav_home = r["hs"] >= r["as"]
    winner_home = diff > 0
    margin = abs(diff)
    win_side = "home" if winner_home else "away"
    return {
        "fav_win": float(diff != 0 and winner_home == fav_home),
        "margin": margin,
        "within9": float(margin <= 9),
        "within5": float(margin <= 5),
        "ot": float(r["ot"]),
        "points": r["h"] + r["a"],
        "lead_changes": r["lead_changes"],
        "comeback9": float(diff != 0 and r["max_def"][win_side] >= 9),
        "comeback18": float(diff != 0 and r["max_def"][win_side] >= 18),
        "q4_trailer_wins": float(r["q4_diff"] != 0 and diff != 0 and (r["q4_diff"] > 0) != winner_home),
    }


M = {c: {k: np.array([game_metrics(pairs[n][c])[k] for n in ns])
         for k in game_metrics(pairs[ns[0]]["on"])} for c in ("on", "off")}
rng = np.random.default_rng(0)
idx = rng.integers(0, len(ns), size=(2000, len(ns)))
out = {"matchups": len(ns), "metrics": {}}
for k in M["on"]:
    on, off = M["on"][k], M["off"][k]
    d = on - off
    boots = d[idx].mean(axis=1)
    out["metrics"][k] = {"on": round(on.mean(), 4), "off": round(off.mean(), 4),
                         "diff": round(d.mean(), 4),
                         "ci95": [round(float(np.percentile(boots, 2.5)), 4),
                                  round(float(np.percentile(boots, 97.5)), 4)]}

flip = [n for n in ns if np.sign(pairs[n]["on"]["h"] - pairs[n]["on"]["a"]) != np.sign(pairs[n]["off"]["h"] - pairs[n]["off"]["a"])]
out["winner_flipped_rate"] = round(len(flip) / len(ns), 4)


def logistic_slope(c):
    x = np.array([pairs[n][c]["hs"] - pairs[n][c]["as"] for n in ns])
    y = np.array([float(pairs[n][c]["h"] > pairs[n][c]["a"]) for n in ns])
    X = np.c_[np.ones_like(x), x]; b = np.zeros(2)
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        b += np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (y - p))
    return round(float(b[1]), 4)


out["win_logit_per_strength_point"] = {c: logistic_slope(c) for c in ("on", "off")}
gap = np.array([abs(pairs[n]["on"]["hs"] - pairs[n]["on"]["as"]) for n in ns])
bins = [(0, 2), (2, 5), (5, 10), (10, 99)]
out["fav_win_by_strength_gap"] = {
    f"{lo}-{hi}": {"games": int(((gap >= lo) & (gap < hi)).sum()),
                   **{c: round(float(M[c]["fav_win"][(gap >= lo) & (gap < hi)].mean()), 4) for c in ("on", "off")}}
    for lo, hi in bins}

restarts = [(d, pairs[n]["on"]) for n in ns for d in pairs[n]["on"]["drives"] if d["origin"] == "score_restart"]
starts = np.array([d["start"] for d, _ in restarts])
costs = np.array([d["cost"] or 0 for d, _ in restarts])
out["restarts"] = {"count": len(restarts),
                   "mean_abs_shift_yards": round(float(np.abs(costs).mean()), 2),
                   "share_at_floor_1": round(float((starts <= 1).mean()), 4),
                   "share_at_ceiling_80": round(float((starts >= 80).mean()), 4),
                   "share_boosted": round(float((costs < 0).mean()), 4),
                   "share_penalized": round(float((costs > 0).mean()), 4)}


def ols(drs):
    y = np.array([d["pts"] or 0 for d, _ in drs], float)
    start = np.array([d["start"] for d, _ in drs], float)
    sgap = np.array([(g["hs"] - g["as"]) * (1 if d["team"] == "home" else -1) for d, g in drs])
    X = np.c_[np.ones_like(start), start, sgap]
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    bs = []
    r2 = np.random.default_rng(1)
    for _ in range(500):
        i = r2.integers(0, len(y), len(y))
        bs.append(np.linalg.lstsq(X[i], y[i], rcond=None)[0][1])
    return {"drives": len(y), "points_per_yard": round(float(b[1]), 4),
            "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "mean_points": round(float(y.mean()), 3)}


out["drive_value"] = {
    "score_restarts_delta_on": ols(restarts),
    "all_drives_start_1_to_50": ols([(d, pairs[n][c]) for n in ns for c in ("on", "off")
                                     for d in pairs[n][c]["drives"] if d["start"] and 1 <= d["start"] <= 50]),
}
print(json.dumps(out, indent=2))
