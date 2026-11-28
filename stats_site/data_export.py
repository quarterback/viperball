"""Flat data tables for a college season, for Observable, spreadsheets and scripts.

Every table is a list of flat rows (one value per column, no nesting), so it
loads straight into Observable with FileAttachment, d3.csv or Plot without any
reshaping. Rows come from the games' full results.
"""
import csv
import io

from stats_site.analytics_portal import games_for

TABLES = {
    "games": "One row per game: teams, score, conferences, schemes, weather.",
    "team_games": "One row per team per game: the full team box score.",
    "player_games": "One row per player per game: the player box score.",
    "players": "One row per player: season totals.",
    "plays": "One row per play: down, distance, field position, call, result, EPA, and where the ball sat across the field.",
    "drives": "One row per drive: start, length, yards, result, points.",
    "standings": "One row per team: record and efficiency ratings.",
}


def _scalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


def _flatten(d, prefix=""):
    """Scalars as is; one level of scalar dicts as prefix_key; drop the rest."""
    out = {}
    for k, v in (d or {}).items():
        if _scalar(v):
            out[prefix + k] = v
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if _scalar(v2):
                    out[f"{prefix}{k}_{k2}"] = v2
    return out


def _games(season, session_id, week=None, team=None):
    for g in games_for(season, session_id):
        if week is not None and str(g["week"]) != str(week):
            continue
        if team and team not in (g["home"], g["away"]):
            continue
        yield g


def _side_team(g, side):
    return g["home"] if side == "home" else g["away"]


def _other(side):
    return "away" if side == "home" else "home"


def games_rows(season, session_id, week=None, team=None):
    conf = getattr(season, "team_conferences", {}) or {}
    for g in _games(season, session_id, week, team):
        fr = g["result"] or {}
        hs, as_ = g["home_score"], g["away_score"]
        yield {
            "game_id": g["id"], "kind": g["kind"], "week": g["week"],
            "home": g["home"], "away": g["away"],
            "home_score": hs, "away_score": as_,
            "winner": g["home"] if (hs or 0) > (as_ or 0) else g["away"] if (as_ or 0) > (hs or 0) else "",
            "margin": abs((hs or 0) - (as_ or 0)),
            "home_conference": conf.get(g["home"], ""), "away_conference": conf.get(g["away"], ""),
            "home_offense": fr.get("home_style"), "away_offense": fr.get("away_style"),
            "home_defense": fr.get("home_defense_style"), "away_defense": fr.get("away_defense_style"),
            "home_special_teams": fr.get("home_st_scheme"), "away_special_teams": fr.get("away_st_scheme"),
            "weather": fr.get("weather"), "rivalry": bool(fr.get("is_rivalry_game")),
        }


def team_games_rows(season, session_id, week=None, team=None):
    conf = getattr(season, "team_conferences", {}) or {}
    for g in _games(season, session_id, week, team):
        fr = g["result"]
        if not fr:
            continue
        for side in ("home", "away"):
            name, opp = _side_team(g, side), _side_team(g, _other(side))
            if team and name != team:
                continue
            pf = g[side + "_score"] or 0
            pa = g[_other(side) + "_score"] or 0
            row = {
                "game_id": g["id"], "kind": g["kind"], "week": g["week"],
                "team": name, "opponent": opp, "home_away": side,
                "conference": conf.get(name, ""),
                "points_for": pf, "points_against": pa,
                "result": "W" if pf > pa else "L" if pf < pa else "T",
                "offense": fr.get(side + "_style"), "defense": fr.get(side + "_defense_style"),
                "weather": fr.get("weather"),
            }
            row.update(_flatten((fr.get("stats") or {}).get(side)))
            yield row


def player_games_rows(season, session_id, week=None, team=None):
    for g in _games(season, session_id, week, team):
        fr = g["result"]
        if not fr:
            continue
        for side in ("home", "away"):
            name, opp = _side_team(g, side), _side_team(g, _other(side))
            if team and name != team:
                continue
            for p in (fr.get("player_stats") or {}).get(side) or []:
                row = {"game_id": g["id"], "week": g["week"], "team": name, "opponent": opp}
                row.update(_flatten(p))
                yield row


def plays_rows(season, session_id, week=None, team=None):
    for g in _games(season, session_id, week, team):
        fr = g["result"]
        if not fr:
            continue
        for p in fr.get("play_by_play") or []:
            side = p.get("snap_possession") or p.get("possession")
            if side not in ("home", "away"):
                continue
            offense = _side_team(g, side)
            if team and offense != team:
                continue
            call = p.get("defensive_call") or {}
            w = p.get("width") or {}
            d = w.get("defenders") or {}
            yield {
                "game_id": g["id"], "week": g["week"], "play_number": p.get("play_number"),
                "offense": offense, "defense": _side_team(g, _other(side)),
                "quarter": p.get("quarter"), "time_remaining": p.get("time_remaining"),
                "down": p.get("down"), "yards_to_go": p.get("yards_to_go"),
                "field_position": p.get("field_position"),
                "formation": p.get("formation"), "play_type": p.get("play_type"),
                "play_family": p.get("play_family"),
                "defense_alignment": call.get("alignment"), "blitz": call.get("blitz"),
                "result": p.get("result"), "yards": p.get("yards"),
                "home_score": p.get("home_score"), "away_score": p.get("away_score"),
                "ep_before": p.get("ep_before"), "epa": p.get("epa"),
                "origin": p.get("possession_origin"),
                "hash": w.get("hash"), "snap_x": w.get("snap_x"), "end_x": w.get("end_x"),
                "attack_side": w.get("side"), "side_label": w.get("side_label"),
                "side_room": w.get("room"), "side_value": w.get("value"),
                "defenders_left": d.get("left"), "defenders_box": d.get("box"),
                "defenders_right": d.get("right"), "defense_lean": w.get("defense_lean"),
                "out_of_bounds": w.get("out_of_bounds"),
                "description": p.get("description", ""),
            }


def drives_rows(season, session_id, week=None, team=None):
    for g in _games(season, session_id, week, team):
        fr = g["result"]
        if not fr:
            continue
        for i, d in enumerate(fr.get("drive_summary") or []):
            side = d.get("team")
            if side not in ("home", "away"):
                continue
            offense = _side_team(g, side)
            if team and offense != team:
                continue
            row = {"game_id": g["id"], "week": g["week"], "drive": i + 1,
                   "offense": offense, "defense": _side_team(g, _other(side))}
            row.update({k: v for k, v in d.items() if _scalar(v) and k != "team"})
            row["timeouts"] = len(d.get("timeouts") or [])
            yield row


def players_rows(player_agg, team=None):
    for p in player_agg:
        if team and p.get("team") != team:
            continue
        yield {k: v for k, v in p.items() if _scalar(v)}


def to_csv(rows):
    """CSV with a header that covers every column seen, in first seen order."""
    rows = list(rows)
    cols = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)

    def clean(v):
        # Keep spreadsheets from reading a value as a formula.
        if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + v
        return "" if v is None else v

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([clean(r.get(c)) for c in cols])
    return buf.getvalue()
