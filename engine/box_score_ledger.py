"""Official box-score scoring ledger derived from finalized play scoreboard changes.

The possession of a play is not necessarily the scoring team: pick-sixes,
blocked kicks, returns and safeties can credit the defense. Score deltas are
authoritative; the result label determines the scoring *method* only.
Bonus possessions are a source of opportunity, never an extra score.
"""
from __future__ import annotations

from collections import defaultdict

METHODS = (
    "rush_td", "lateral_td", "kp_td", "return_td",
    "dk", "pk", "safety", "pindown", "bell", "other",
)


def scoring_ledger(plays, final_scores=None):
    """Return per-side counts, actual points and any reconciliation gap.

    A play can award a touchdown and a bell (9.5), and its scoring team
    can differ from its pre-snap possession. For historical play lists
    without after-score values, return None instead of guessing.
    """
    if not plays or not all(
        ("home_score" in p and "away_score" in p and
         p["home_score"] is not None and p["away_score"] is not None)
        for p in plays
    ):
        return None

    out = {side: {"counts": {m: 0 for m in METHODS},
                  "points": {m: 0.0 for m in METHODS},
                  "score_from_plays": 0.0,
                  "unrecorded_points": 0.0,
                  "score_consistent": True}
           for side in ("home", "away")}
    previous = {"home": 0.0, "away": 0.0}
    for p in plays:
        snap = p.get("snap_possession") or p.get("possession")
        typ, result = p.get("play_type"), p.get("result")
        for side in ("home", "away"):
            current = round(float(p[side + "_score"]) * 2) / 2
            gain = round((current - previous[side]) * 2) / 2
            previous[side] = current
            if gain < 0:
                # A scoreboard rollback means the play log is inconsistent.
                out[side]["score_consistent"] = False
                out[side]["unrecorded_points"] += gain
                continue
            if not gain:
                continue
            remaining = gain
            def add(method, points):
                nonlocal remaining
                out[side]["counts"][method] += 1
                out[side]["points"][method] += points
                remaining = round((remaining - points) * 2) / 2

            # A defensive recovery may accompany a 9-point return touchdown.
            if remaining >= 9 and result in (
                "touchdown", "punt_return_td", "kick_return_td",
                "missed_dk_return_td", "int_return_td", "blocked_kick",
            ):
                if side != snap or result in (
                    "punt_return_td", "kick_return_td", "missed_dk_return_td",
                    "int_return_td", "blocked_kick",
                ):
                    method = "return_td"
                elif typ == "kick_pass":
                    method = "kp_td"
                elif p.get("laterals"):
                    method = "lateral_td"
                else:
                    method = "rush_td"
                add(method, 9.0)
            if remaining >= 5 and typ == "drop_kick" and result == "successful_kick":
                add("dk", 5.0)
            if remaining >= 3 and typ == "place_kick" and result == "successful_kick":
                add("pk", 3.0)
            if remaining >= 2 and result == "safety":
                add("safety", 2.0)
            if remaining >= 1 and result == "pindown":
                add("pindown", 1.0)
            if remaining >= 0.5 and (result in (
                "fumble", "muffed_punt", "chaos_recovery", "blocked_kick",
                "missed_kick", "punt_return_td", "kick_return_td",
                "missed_dk_return_td", "int_return_td",
            ) or remaining == 0.5):
                add("bell", 0.5)
            if remaining:
                add("other", remaining)
            out[side]["score_from_plays"] += gain

    for side in ("home", "away"):
        o = out[side]
        o["score_from_plays"] = round(o["score_from_plays"], 1)
        if final_scores is not None:
            expected = final_scores.get(side)
            if expected is not None:
                o["unrecorded_points"] = round(
                    float(expected) - previous[side], 1)
                o["score_consistent"] &= o["unrecorded_points"] == 0
    return out
