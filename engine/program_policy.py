"""CASE-04: program-building preferences separate from coach ability.

Persistent policy is derived from existing coach traits. It affects choices
within existing budgets and rules, never player ratings or signing odds.
"""
from .coach_career import active_management, slider, clip

TARGET_DEPTH = {"Offensive Line":8,"Defensive Line":7,"Halfback":4,
                "Wingback":4,"Slotback":4,"Zeroback":3,"Viper":3,"Keeper":3}


def program_policy(staff):
    hc = (staff or {}).get("head_coach")
    m = active_management(hc)
    if not m:
        return {}
    continuity = m.get("continuity", .5)
    adapt = slider(hc, "adaptability")
    development = m.get("development", .5)
    recruiting = m.get("recruiting", .5)
    return {"development_horizon": clip(.5*development + .3*continuity + .2*(1-recruiting)),
            "immediate_help": clip(.5*recruiting + .3*adapt + .2*(1-continuity)),
            "staff_innovation": clip(adapt*(1-continuity)),
            "continuity": continuity,
            "teaching_focus": development,
            "specialty": m.get("specialty")}


def roster_horizon(roster):
    """Count actual continuing players; graduating players cannot fill future needs."""
    counts = {}
    young = {}
    for player in roster or ():
        get = player.get if isinstance(player, dict) else lambda k, d=None: getattr(player,k,d)
        pos, year = get("position"), get("year")
        if not pos or year == "Graduate":
            continue
        counts[pos] = counts.get(pos, 0) + 1
        if year in ("Freshman","Sophomore"):
            young[pos] = young.get(pos, 0) + 1
    return {pos: {"continuing": counts.get(pos,0), "young":young.get(pos,0),
                  "gap":max(0,target-counts.get(pos,0))}
            for pos,target in TARGET_DEPTH.items()}


def recruit_preference(recruit, policy, horizon):
    """Small bounded ranking preference for developmental upside and depth."""
    if not policy:
        return 1.0
    position = horizon.get(recruit.position, {})
    gap = min(1., position.get("gap",0)/3)
    potential = clip((getattr(recruit,"true_potential",3)-3)/2,-1,1)
    teachable = clip((getattr(recruit,"coachability",50)-60)/35,-1,1)
    runway = clip((2-position.get("young",0))/2,-1,1)
    development = policy["development_horizon"]
    signal = development*(.45*potential+.35*teachable+.20*runway)
    signal += .35*policy["immediate_help"]*gap
    return 1 + clip(.04*signal,-.04,.04)


def portal_preference(entry, policy, horizon, preferences):
    """Relative target-score adjustment, never changes transfer eligibility."""
    if not policy:
        return 0.
    from .coach_recruiting_fit import recruiting_fit, ATTRS
    from types import SimpleNamespace
    player = entry.player_card
    attrs = {("true_"+key):getattr(player,key,None) for key in ATTRS}
    fit = recruiting_fit(SimpleNamespace(position=entry.position,**attrs), preferences)
    info = horizon.get(entry.position,{})
    gap = min(1.,info.get("gap",0)/3)
    experience = {"Freshman":0.,"Sophomore":.33,"Junior":.67,"Senior":1.}.get(getattr(player,"year",""),0.)
    potential = clip((getattr(player,"potential",3)-3)/2,-1,1)
    teaching = clip((getattr(player,"coachability",50)-60)/35,-1,1)
    immediate = policy["immediate_help"]*gap*(.5+.5*experience)
    future = policy["development_horizon"]*(.5*potential+.3*teaching+.2*(1-experience))
    return clip(4*(immediate+future)+25*fit,-5,5)


def program_report(staff, roster):
    return {"policy":program_policy(staff),"roster_horizon":roster_horizon(roster)}


def game_objective(staff, own_style, opponent_style):
    """One shared pregame objective; all units retain their own caller.
    Based only on known school and HC preferences, no hidden opponent calls.
    """
    hc = (staff or {}).get("head_coach")
    m = active_management(hc)
    if not m:
        return {}
    policy = program_policy(staff)
    explosive = opponent_style in {"shock_and_awe","quick_strike","stampede","chain_gang"}
    own_territory = own_style in {"ironclad","ball_control","boot_raid","six_shooter"}
    own_tempo = own_style in {"stampede","shock_and_awe","quick_strike"}
    patience = (policy["continuity"] + (1-slider(hc,"risk_tolerance")))/2
    if (explosive or own_territory) and patience >= .45:
        goal = "territory_control"
    elif own_tempo and slider(hc,"tempo_preference") >= .55:
        goal = "transition_attack"
    else:
        goal = "balanced"
    return {"objective":goal,"hc_id":hc.coach_id,"own_school":own_style,
            "opponent_school":opponent_style,
            "strength":round(.5*m.get("game_management",.5),4),
            "delegation":m.get("delegation",.6)}


def live_objective(plan, score_diff, quarter, seconds):
    """Clock and score override pregame goals. No rule or score changes."""
    if not plan or plan.get("objective") == "balanced":
        return {}
    goal = plan["objective"]
    if quarter == 4 and seconds <= 180:
        if score_diff < 0:
            goal = "urgent_score"
        elif score_diff > 0:
            goal = "protect_lead"
    return {**plan,"active_objective":goal}


def objective_bias(plan, unit):
    """Small relative choice preferences, not execution bonuses."""
    if not plan:
        return {}
    goal = plan["active_objective"]
    strength = plan["strength"]
    tables = {
        "territory_control": {
            "offense":{"power":.12,"dive_option":.10,"kick_pass":-.05,"lateral_spread":-.10},
            "defense":{"spread":.12,"aggressive":-.10},
            "st":{"field_position_bias":.10,"return_aggression":-.08}},
        "transition_attack":{
            "offense":{"speed_option":.12,"viper_jet":.10,"kick_pass":.08,"power":-.08},
            "defense":{"aggressive":.10,"stacked":-.05},
            "st":{"return_aggression":.10,"field_position_bias":-.06}},
        "urgent_score":{
            "offense":{"kick_pass":.12,"speed_option":.10,"power":-.12},
            "defense":{"aggressive":.12,"spread":-.05},
            "st":{"return_aggression":.12,"field_position_bias":-.08}},
        "protect_lead":{
            "offense":{"power":.12,"dive_option":.10,"lateral_spread":-.12,"kick_pass":-.08},
            "defense":{"spread":.12,"aggressive":-.10},
            "st":{"field_position_bias":.10,"return_aggression":-.10}},
    }
    return {k:v*strength for k,v in tables.get(goal,{}).get(unit,{}).items()}


def curriculum(staff, position, style_config=None):
    """Existing school/caller recruiting priorities also guide technical teaching.

    Return relative curriculum weights only for the existing technical
    instruction attributes. No additional development allowance.
    """
    from .coach_roles import position_role, TECHNICAL
    from .coach_recruiting_fit import recruiting_preferences
    role = position_role(position)
    if role not in TECHNICAL or not program_policy(staff):
        return {}
    prefs = recruiting_preferences(staff, style_config).get(position, ())
    priorities = {a:0. for a in TECHNICAL[role]}
    for attrs, weight in prefs:
        for attr in priorities:
            if attr in attrs:
                priorities[attr] += weight
    return priorities
