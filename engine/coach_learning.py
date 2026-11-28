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
