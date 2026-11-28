"""CCH-08: bounded, season-end tactical preference learning for college coaches.

Use only the completed team's own games attributed to the actual coordinator.
Within-game, similar down/distance/field-zone contrasts are descriptive feedback,
not causal estimates. No generic performance multiplier or change of identity.
"""
from collections import defaultdict
from statistics import mean

MIN_GAMES = 6
MIN_ARM = 30
LIMIT = .06
STEP = .015
MENTOR_LIMIT = .025
MENTOR_STEP = .005
RUN = {"dive_option", "power", "sweep_option", "speed_option", "counter", "draw", "viper_jet"}

def clamp(v, limit):
    return max(-limit, min(limit, v))

def _value(play):
    # Bound outliers; measure a scrimmage advance relative to the task.
    # Turnover labels get no credit, even if the ball traveled downfield.
    if play.get("result") in ("fumble", "kick_pass_intercepted", "lateral_intercepted",
                              "int_return_td", "turnover_on_downs"):
        return -1.0
    if play.get("result") in ("first_down", "touchdown"):
        return 1.0
    return max(-1.0, min(1.0, (play.get("yards") or 0) / max(1, play.get("yards_to_go") or 20)))

def observe(season, team, card, role):
    if season is None or role not in ("oc", "dc"):
        return {"games":0,"high":0,"low":0,"contrast":None}
    game_effects, high, low = [], 0, 0
    for game in list(season.schedule) + list(getattr(season, "playoff_bracket", ())):
        if not game.completed or team not in (game.home_team, game.away_team):
            continue
        result = game.full_result or {}
        side = "home" if game.home_team == team else "away"
        ledger = result.get("coach_tactics" if role == "oc" else "defensive_coach_tactics", {}).get(side, {})
        if ledger.get("oc_id" if role == "oc" else "dc_id") != card.coach_id:
            continue
        cells = defaultdict(lambda: [[], []])
        for p in result.get("play_by_play", ()):
            if (p.get("penalty") or {}).get("nullified"):
                continue
            family = p.get("play_family")
            if role == "oc":
                if p.get("snap_possession") != side or family not in RUN | {"kick_pass"}:
                    continue
                arm = int(family == "kick_pass")
            else:
                call = p.get("defensive_call") or {}
                if family != "kick_pass" or call.get("defending_side") != side or call.get("intended_rushers") is None:
                    continue
                arm = int(call["intended_rushers"] >= 4)
            down, ytg, fp = p.get("down"), p.get("yards_to_go"), p.get("field_position")
            if down is None or ytg is None or fp is None:
                continue
            key = (down >= 4, ytg <= 5, fp >= 80, fp < 20)
            cells[key][arm].append(_value(p))
        matched = [(a,b) for a,b in cells.values() if a and b]
        if matched:
            game_effects.append(mean(mean(b)-mean(a) for a,b in matched))
            low += sum(len(a) for a,b in matched)
            high += sum(len(b) for a,b in matched)
    effect = mean(game_effects) if game_effects else None
    return {"games":len(game_effects),"high":high,"low":low,
            "contrast":round(effect,5) if effect is not None else None}

def adapt(card, role, team, year, season):
    from engine.coach_tactics import ensure_coach_tactical_profile
    if role not in ("oc","dc"):
        return None
    profile = ensure_coach_tactical_profile(card)
    state = profile.get("learning", {})
    if state.get("last_year", -1) >= year:
        return None
    data = observe(season, team, card, role)
    key = "kick_mix" if role == "oc" else "pressure"
    previous = float(state.get(key, 0.0))
    sliders = card.personality_sliders or {}
    receptivity = max(0., min(1., sliders.get("adaptability",50)/100)) * (1-max(0.,min(1.,sliders.get("stubbornness",50)/100)))
    enough = data["games"] >= MIN_GAMES and min(data["high"],data["low"]) >= MIN_ARM
    # Shrink noisy evidence and limit yearly and lifetime movement.
    change = 0.0
    if enough:
        weight = min(data["high"], data["low"]) / (min(data["high"],data["low"])+60)
        signal = data["contrast"] * (1 if role=="oc" else -1)
        change = clamp(signal * weight * receptivity * .10, STEP)
    revised = round(clamp(previous+change,LIMIT),5)
    event = {"year":year,"team":team,"role":role,"coach_id":card.coach_id,
             "key":key,"before":previous,"after":revised,"sufficient":enough,**data}
    profile["learning"] = {**state, key:revised, "last_year":year,
                           "history":list(state.get("history",[]))[-19:]+[event]}
    return event

def offense_bias(profile):
    base = dict(profile.get("offense",{}).get("family_bias",{}))
    state = profile.get("learning", {})
    delta = clamp(float(state.get("kick_mix", 0)), LIMIT) + mentor_bias(profile, "kick_mix")
    if delta:
        base["kick_pass"] = clamp(base.get("kick_pass",0)+delta,.20)
        for family in sorted(RUN):
            base[family] = clamp(base.get(family,0)-delta/len(RUN),.20)
    return base

def pressure_bias(profile):
    return clamp(float(profile.get("defense",{}).get("pressure_bias",0))+
                 clamp(float(profile.get("learning",{}).get("pressure",0)), LIMIT) +
                 mentor_bias(profile, "pressure"), .15)


def mentor_bias(profile, key):
    return clamp(float(profile.get("learning", {}).get("mentorship", {}).get(key, 0)), MENTOR_LIMIT)


def learn_from_mentor(card, mentor, role, team, year):
    """Learn a small tactical tendency after a verified shared season.

    Only the HC's relevant specialty is passed down, never their identity,
    rating, or learned performance bonus. Keep the apprentice's own
    season-evidence learning distinct from this exposure.
    """
    from engine.coach_tactics import ensure_coach_tactical_profile
    from engine.coach_career import management, slider
    if mentor is None or card.coach_id == mentor.coach_id or role not in ("oc", "dc"):
        return None
    if management(mentor).get("specialty") != role:
        return None
    if not any(
        x.get("coach_id") == mentor.coach_id and x.get("team_name") == team
        and x.get("year_start", year + 1) <= year <= x.get("year_end", year - 1)
        for x in card.coaching_tree
    ):
        return None
    profile = ensure_coach_tactical_profile(card)
    source = ensure_coach_tactical_profile(mentor)
    learning = profile.setdefault("learning", {})
    lineage = learning.setdefault("mentorship", {})
    if lineage.get("last_year", -1) >= year:
        return None
    key = "kick_mix" if role == "oc" else "pressure"
    before = mentor_bias(profile, key)
    if role == "oc":
        own = float(profile["offense"]["family_bias"].get("kick_pass", 0))
        target = float(source["offense"]["family_bias"].get("kick_pass", 0))
    else:
        own = float(profile["defense"].get("pressure_bias", 0))
        target = float(source["defense"].get("pressure_bias", 0))
    receptivity = slider(card, "adaptability") * (1 - slider(card, "stubbornness"))
    shift = clamp((target - own - before) * receptivity * .10, MENTOR_STEP)
    after = round(clamp(before + shift, MENTOR_LIMIT), 5)
    event = {"year": year, "team": team, "role": role, "coach_id": card.coach_id,
             "mentor_id": mentor.coach_id, "key": key, "before": before, "after": after}
    lineage.update({key: after, "last_year": year,
                    "history": list(lineage.get("history", []))[-19:] + [event]})
    return event


def learn_from_coordinator(hc, coordinator, role, team, year, season):
    """Upward learning after attributable, completed shared work.

    Only the relevant tactical tendency travels. Independent per-role
    annual guard; shares the existing mentorship lifetime bound.
    """
    from .coach_career import slider, active_management
    from .coach_tactics import ensure_coach_tactical_profile
    if hc is None or coordinator is None or hc is coordinator or role not in ("oc","dc"):
        return None
    if not active_management(hc):
        return None
    for card in (hc,coordinator):
        history = getattr(card,"career_development",{}).get("history",[])
        if not any(row.get("team")==team and row.get("year")==year for row in history):
            return None
    data = observe(season,team,coordinator,role)
    if data["games"] < MIN_GAMES or min(data["high"],data["low"]) < MIN_ARM:
        return None
    signal = data["contrast"] * (1 if role=="oc" else -1)
    if signal <= 0:
        return None
    profile = ensure_coach_tactical_profile(hc)
    source = ensure_coach_tactical_profile(coordinator)
    state = profile.setdefault("learning",{}).setdefault("mentorship",{})
    years = state.setdefault("upward_years",{})
    if years.get(role,-1)>=year:
        return None
    key = "kick_mix" if role=="oc" else "pressure"
    before = mentor_bias(profile,key)
    own = (profile["offense"]["family_bias"].get("kick_pass",0) if role=="oc" else profile["defense"].get("pressure_bias",0))
    target = (source["offense"]["family_bias"].get("kick_pass",0) if role=="oc" else source["defense"].get("pressure_bias",0))
    # Positive contrast supports the high arm only, not a reduction of it.
    receptive = slider(hc,"adaptability")*(1-slider(hc,"stubbornness"))
    change = clamp(max(0.,target-own-before)*receptive*min(1.,signal)*.10, MENTOR_STEP)
    after = round(clamp(before+change,MENTOR_LIMIT),5)
    event = {"year":year,"team":team,"role":role,"coach_id":hc.coach_id,
             "mentor_id":coordinator.coach_id,"direction":"upward","key":key,
             "before":before,"after":after,**data}
    years[role]=year
    state[key]=after
    state["history"]=list(state.get("history",[]))[-19:]+[event]
    return event


# ── Seagull learning ─────────────────────────────────────────────
#
# Coaches learn whether Seagulls work the same way they learn their kick
# mix: at season's end, from their own team's games, comparing Seagull snaps
# with ordinary snaps in matching situations. Three things are learned, each
# a small, bounded change to the coach's Seagull preference
# (engine/presnap.py):
#
# * the offensive coordinator: plays with a Seagull on the line or in the
#   Viper jersey against plays without one,
# * the defensive coordinator: plays with a Seagull on at defensive back,
#   Keeper or defensive line against plays without one, and what opponents'
#   Seagulls did against his defense,
# * the head coach: whether his coordinators' Seagull snaps came out ahead,
#   and what opponents' Seagulls did to his team on both sides of the ball.
#
# A staff that never lists a Seagull has no Seagull snaps of its own, so it
# can only learn from opponents. A coach who moves keeps what he learned.

SEAGULL_MIN_GAMES = 6
SEAGULL_MIN_ARM = 20
SEAGULL_STEP = .03     # most a coach's Seagull preference moves in one year
SEAGULL_LIMIT = .08    # most it moves over a career
SEAGULL_KEYS = {"head_coach": "listing", "oc": "offense", "dc": "defense"}


def _cell(play):
    down, ytg, fp = play.get("down"), play.get("yards_to_go"), play.get("field_position")
    if down is None or ytg is None or fp is None:
        return None
    return (down >= 4, ytg <= 5, fp >= 80, fp < 20)


def _offense_seagull(play):
    m = play.get("motion") or {}
    return bool(m.get("seagull_line") or m.get("seagull_viper"))


def _defense_seagull(play):
    return bool((play.get("motion") or {}).get("defense_seagull"))


def _contrast(games):
    """Mean over games of the matched cell difference (Seagull minus none)."""
    effects, with_n, without_n = [], 0, 0
    for cells in games:
        matched = [(a, b) for a, b in cells.values() if a and b]
        if matched:
            effects.append(mean(mean(b) - mean(a) for a, b in matched))
            without_n += sum(len(a) for a, b in matched)
            with_n += sum(len(b) for a, b in matched)
    return {"games": len(effects), "with": with_n, "without": without_n,
            "contrast": round(mean(effects), 5) if effects else None}


def observe_seagulls(season, team):
    """Seagull evidence from one team's completed games.

    Returns four contrasts, each the matched difference in play value
    (scrimmage gain against the task, turnovers -1) between plays with a
    Seagull and plays without:

    * own_offense: our offense, our Seagull on or not (higher is good for us)
    * own_defense: opponents' offense, our Seagull on or not (lower is good)
    * opp_offense: opponents' offense, their Seagull on or not (higher hurt us)
    * opp_defense: our offense, their Seagull on or not (lower hurt us)
    """
    buckets = {k: [] for k in ("own_offense", "own_defense", "opp_offense", "opp_defense")}
    ids = {}
    if season is None:
        return {k: _contrast([]) for k in buckets}, ids
    for game in list(season.schedule) + list(getattr(season, "playoff_bracket", ())):
        if not getattr(game, "completed", False) or team not in (game.home_team, game.away_team):
            continue
        result = game.full_result or {}
        side = "home" if game.home_team == team else "away"
        ids.setdefault("oc", set()).add((result.get("coach_tactics", {}).get(side, {}) or {}).get("oc_id"))
        ids.setdefault("dc", set()).add((result.get("defensive_coach_tactics", {}).get(side, {}) or {}).get("dc_id"))
        cells = {k: defaultdict(lambda: [[], []]) for k in buckets}
        for p in result.get("play_by_play", ()):
            if (p.get("penalty") or {}).get("nullified") or not p.get("motion"):
                continue
            key = _cell(p)
            if key is None:
                continue
            v = _value(p)
            ours = p.get("snap_possession") == side
            if ours:
                cells["own_offense"][key][int(_offense_seagull(p))].append(v)
                cells["opp_defense"][key][int(_defense_seagull(p))].append(v)
            else:
                cells["own_defense"][key][int(_defense_seagull(p))].append(v)
                cells["opp_offense"][key][int(_offense_seagull(p))].append(v)
        for k in buckets:
            buckets[k].append(cells[k])
    return {k: _contrast(v) for k, v in buckets.items()}, ids


def _signal(data, sign):
    """Shrunk signal from one contrast, or None without enough evidence."""
    if data["contrast"] is None or data["games"] < SEAGULL_MIN_GAMES:
        return None
    arm = min(data["with"], data["without"])
    if arm < SEAGULL_MIN_ARM:
        return None
    return sign * data["contrast"] * arm / (arm + 60)


def seagull_learned(profile, role):
    """The learned change to this coach's Seagull preference (bounded)."""
    key = SEAGULL_KEYS.get(role)
    state = ((profile or {}).get("learning") or {}).get("seagull") or {}
    return clamp(float(state.get(key, 0.0)), SEAGULL_LIMIT) if key else 0.0


def adapt_seagull(card, role, team, year, season):
    """Season end Seagull learning for one coach. Returns the event or None.

    Coordinators learn only from games they called. Opponents' Seagulls
    count half as much as a coach's own, and say "copy what beat us": when
    they hurt his team, his preference rises.
    """
    from engine.coach_tactics import ensure_coach_tactical_profile
    key = SEAGULL_KEYS.get(role)
    if key is None or season is None:
        return None
    data, ids = observe_seagulls(season, team)
    if role in ("oc", "dc") and card.coach_id not in ids.get(role, set()):
        return None
    profile = ensure_coach_tactical_profile(card)
    learning = profile.setdefault("learning", {})
    state = learning.setdefault("seagull", {})
    if state.get("last_year", {}).get(key, -1) >= year:
        return None
    parts = []
    if role in ("oc", "head_coach"):
        parts.append((_signal(data["own_offense"], 1), 1.0))
    if role in ("dc", "head_coach"):
        parts.append((_signal(data["own_defense"], -1), 1.0))
        parts.append((_signal(data["opp_offense"], 1), 0.5))
    if role == "head_coach":
        parts.append((_signal(data["opp_defense"], -1), 0.5))
    usable = [(s, w) for s, w in parts if s is not None]
    sliders = card.personality_sliders or {}
    receptivity = (max(0., min(1., sliders.get("adaptability", 50) / 100))
                   * (1 - max(0., min(1., sliders.get("stubbornness", 50) / 100))))
    previous = float(state.get(key, 0.0))
    change = 0.0
    if usable:
        signal = sum(s * w for s, w in usable) / sum(w for _, w in usable)
        change = clamp(signal * receptivity, SEAGULL_STEP)
    revised = round(clamp(previous + change, SEAGULL_LIMIT), 5)
    event = {"year": year, "team": team, "role": role, "coach_id": card.coach_id,
             "key": "seagull_" + key, "before": previous, "after": revised,
             "sufficient": bool(usable), "evidence": data}
    state[key] = revised
    state["last_year"] = {**state.get("last_year", {}), key: year}
    state["history"] = list(state.get("history", []))[-19:] + [
        {k: v for k, v in event.items() if k != "evidence"}]
    return event
