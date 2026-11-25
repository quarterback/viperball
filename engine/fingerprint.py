"""COACH-FP-01: a team's coaching fingerprint, measured from its games.

Everything here is counted from completed games' play by play, so the panel
shows what a staff actually did, not what its settings say it should do.
"""
from collections import Counter
from typing import Dict, Optional

RUN_TYPES = {"run"}
KICK_TYPES = {"drop_kick", "place_kick"}


def _side(result: Dict, team_name: str) -> Optional[str]:
    for side in ("home", "away"):
        if (result.get("final_score", {}).get(side, {}).get("team") == team_name):
            return side
    return None


def team_fingerprint(games, team_name: str) -> Optional[Dict]:
    """games: completed season games with full_result. Returns None if the
    team has no games with play by play yet."""
    c = Counter()
    leans = Counter()
    lean_w = 0.0
    for g in games:
        r = getattr(g, "full_result", None) or {}
        if not r or not r.get("play_by_play"):
            continue
        if team_name not in (getattr(g, "home_team", None), getattr(g, "away_team", None)):
            continue
        side = "home" if g.home_team == team_name else "away"
        c["games"] += 1
        s = r.get("stats", {}).get(side, {})
        pts = r.get("final_score", {}).get(side, {}).get("score", 0) or 0
        c["points"] += pts
        c["td_points"] += 9 * (s.get("touchdowns", 0) or 0)
        plan = (r.get("game_plans") or {}).get(side) or {}
        if plan.get("lean"):
            leans[plan["lean"]] += 1
            lean_w += plan.get("weight", 0.0)
        for p in r["play_by_play"]:
            if (p.get("snap_possession") or p.get("possession")) != side:
                continue
            pt = p.get("play_type")
            if pt in ("penalty", "kneel", "bonus_possession"):
                continue
            c["plays"] += 1
            if pt in RUN_TYPES:
                c["runs"] += 1
            elif pt == "kick_pass":
                c["kick_passes"] += 1
            elif pt == "lateral_chain":
                c["laterals"] += 1
            down = p.get("down") or 0
            fp = p.get("field_position") or 0
            # Late downs past midfield: kick, punt or keep going?
            if down in (5, 6) and fp >= 50:
                c["late"] += 1
                if pt not in KICK_TYPES and pt != "punt":
                    c["late_go"] += 1
            # In snap kick range on downs 4 to 6: did they take the points?
            if down >= 4 and fp >= 60:
                c["range"] += 1
                if pt in KICK_TYPES:
                    c["range_kick"] += 1
    if not c["games"]:
        return None
    g = c["games"]

    def pct(a, b):
        return round(100.0 * c[a] / c[b]) if c[b] else None

    return {
        "games": g,
        "run_share": pct("runs", "plays"),
        "kick_pass_share": pct("kick_passes", "plays"),
        "lateral_share": pct("laterals", "plays"),
        "td_share": round(100.0 * c["td_points"] / c["points"]) if c["points"] else None,
        "late_down_go": pct("late_go", "late"),
        "kick_acceptance": pct("range_kick", "range"),
        "plays_per_game": round(c["plays"] / g, 1),
        "points_per_game": round(c["points"] / g, 1),
        "defense_lean": leans.most_common(1)[0][0] if leans else None,
        "defense_lean_weight": round(lean_w / sum(leans.values()), 2) if leans else 0.0,
    }
