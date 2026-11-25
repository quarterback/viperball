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


def scoring_ledger(plays, final_scores=None, *, events=None):
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
    for index, p in enumerate(plays):
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
                if events is not None:
                    events.append((index, side, method, points))
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


# Offensive scoring methods eligible for a drive bucket. Pindowns count
# when the kicking side owns the drive; returns, bells and safeties never do.
DRIVE_METHODS = {"rush_td", "lateral_td", "kp_td", "dk", "pk", "pindown"}


def reconcile_drive_scoring(plays, drives, final_scores):
    """Partition recorded score events by explicit half-open drive log spans.

    Return per-drive method totals and per-team reconciliation. Missing
    spans or score snapshots are not sufficient for an audited historical box.
    """
    events = []
    ledger = scoring_ledger(plays, final_scores, events=events)
    if ledger is None:
        return None
    owner = {}
    for i, drive in enumerate(drives):
        start, end = drive.get("play_log_start"), drive.get("play_log_end")
        if not (isinstance(start, int) and isinstance(end, int)
                and 0 <= start <= end <= len(plays)):
            return None
        for j in range(start, end):
            if j in owner:
                return None
            owner[j] = i

    per_drive = [{m: 0.0 for m in METHODS} for _ in drives]
    teams = {side: {
        "drive_points": 0.0,
        "non_drive_by_method": {m: 0.0 for m in METHODS},
        "non_drive_points": 0.0,
        "final_score": float(final_scores[side]),
    } for side in ("home", "away")}
    for index, side, method, points in events:
        i = owner.get(index)
        team = teams[side]
        if (i is not None and drives[i]["team"] == side
                and method in DRIVE_METHODS):
            per_drive[i][method] += points
            team["drive_points"] += points
        else:
            team["non_drive_by_method"][method] += points
            team["non_drive_points"] += points

    for side, team in teams.items():
        team["unreconciled_points"] = (
            team["final_score"] - team["drive_points"] - team["non_drive_points"]
        )
        team["score_consistent"] = (
            ledger[side]["score_consistent"] and team["unreconciled_points"] == 0
        )
    return per_drive, teams
