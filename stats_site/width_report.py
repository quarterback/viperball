"""Field width splits for the stats site: which side of the field each team
attacked, how it went, and where kicks came from. Reads the `width` record
the engine puts on each play (engine/field_width.py)."""

LIVE = ("run", "kick_pass", "lateral_chain", "trick_play")
KICKS = ("drop_kick", "place_kick")
SIDES = (("field", "Wide side"), ("boundary", "Short side"), ("middle", "Middle"))
HASHES = (("left_hash", "Left hash"), ("middle", "Between the hashes"), ("right_hash", "Right hash"))
SUCCESS = ("first_down", "touchdown")
MADE = ("successful_kick",)


def _blank():
    return {
        "sides": {k: {"plays": 0, "yards": 0, "success": 0} for k, _ in SIDES},
        "snaps": {k: 0 for k, _ in HASHES},
        "kicks": {k: {"att": 0, "made": 0} for k, _ in HASHES},
        "out_of_bounds": 0,
        "lean": {"wide": 0, "short": 0},
    }


def tally(plays, into=None):
    """Totals per offense side ("home"/"away") from one game's plays.

    `into` lets the caller add several games together; it maps a key the
    caller chooses to a totals dict, and `plays` yields (key, play).
    """
    out = into if into is not None else {}
    for key, p in plays:
        w = p.get("width") or {}
        if not w or (p.get("result") == "penalty"):
            continue
        t = out.setdefault(key, _blank())
        ptype = p.get("play_type")
        if w.get("hash") in t["snaps"]:
            t["snaps"][w["hash"]] += 1
        if ptype in LIVE and w.get("side_label") in t["sides"]:
            s = t["sides"][w["side_label"]]
            s["plays"] += 1
            s["yards"] += p.get("yards") or 0
            s["success"] += p.get("result") in SUCCESS
            if w.get("out_of_bounds"):
                t["out_of_bounds"] += 1
        if ptype in KICKS and w.get("hash") in t["kicks"]:
            k = t["kicks"][w["hash"]]
            k["att"] += 1
            k["made"] += p.get("result") in MADE
        if w.get("defense_lean") == 1:
            t["lean"]["wide"] += 1
        elif w.get("defense_lean") == -1:
            t["lean"]["short"] += 1
    return out


def rows(t):
    """Display rows for one team's totals."""
    if not t:
        return None
    live = sum(s["plays"] for s in t["sides"].values()) or 0
    sides = []
    for key, label in SIDES:
        s = t["sides"][key]
        if not s["plays"]:
            continue
        sides.append({
            "label": label, "plays": s["plays"],
            "share": round(100 * s["plays"] / live) if live else 0,
            "ypp": round(s["yards"] / s["plays"], 1),
            "success": round(100 * s["success"] / s["plays"]),
        })
    snaps = sum(t["snaps"].values()) or 0
    hashes = []
    for key, label in HASHES:
        k = t["kicks"][key]
        hashes.append({
            "label": label, "snaps": t["snaps"][key],
            "share": round(100 * t["snaps"][key] / snaps) if snaps else 0,
            "kicks": k["att"], "made": k["made"],
            "pct": round(100 * k["made"] / k["att"]) if k["att"] else None,
        })
    return {"sides": sides, "hashes": hashes, "out_of_bounds": t["out_of_bounds"],
            "lean_wide": t["lean"]["wide"], "lean_short": t["lean"]["short"]}


def game_report(result):
    """{"home": rows, "away": rows} for one game, by the team on offense."""
    plays = (result or {}).get("play_by_play") or []
    t = tally((p.get("snap_possession") or p.get("possession"), p) for p in plays)
    report = {side: rows(t.get(side)) for side in ("home", "away")}
    return report if any(report.values()) else None


def team_report(games, team):
    """Season totals for one team: its offense, and opponents against it.

    games: iterable of (home_team, away_team, full_result).
    """
    t = {}
    for home, away, fr in games:
        if team not in (home, away) or not fr:
            continue
        mine = "home" if team == home else "away"

        def keyed():
            for p in fr.get("play_by_play") or []:
                side = p.get("snap_possession") or p.get("possession")
                if side in ("home", "away"):
                    yield ("offense" if side == mine else "defense"), p
        tally(keyed(), t)
    report = {"offense": rows(t.get("offense")), "defense": rows(t.get("defense"))}
    return report if any(report.values()) else None
