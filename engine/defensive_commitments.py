"""Bounded tactical commitments for defensive packages and pressure.

All decisions use pre-snap state and prior completed plays only.
Primary and secondary eligibility share the same contract in game and benchmark.
"""
def eligibility(package_id, tags, context, primary_tags):
    tags = set(tags)
    fp = context.get("field_position", 0)
    down = context.get("down", 1)
    ytg = context.get("yards_to_go", 20)
    snap = context.get("drive_play_index", 0)
    deep = context.get("recent_deep_rate", 0.0)
    pass_rate = context.get("recent_kick_rate", 0.0)
    explosive = context.get("recent_explosive_rate", 0.0)
    perimeter = context.get("recent_perimeter_rate", 0.0)
    lateral = context.get("recent_lateral_rate", 0.0)
    offense_energy = context.get("offense_energy")
    primary = bool(tags.intersection(primary_tags))
    if package_id == "afl_kick_in_press":
        primary = {"backed_up", "first_play_of_drive"} <= tags
    if package_id == "lax_ride":
        primary = {"after_takeaway", "first_play_of_drive"} <= tags
    if package_id == "swarm_containment":
        primary = "early_down" in tags and perimeter >= .20
    if package_id == "shadow_robber":
        primary = "late_downs" in tags and pass_rate >= .25
    if package_id == "chaos_lateral_trap":
        primary = "early_down" in tags and lateral >= .15
    if package_id == "predator_exhaustion_press":
        primary = "early_down" in tags and offense_energy is not None and offense_energy < 75
    if primary:
        return 1.0
    secondary = {
        "fortress_goal_line_stand": fp >= 75,
        "fortress_short_yardage_wall": down >= 4 and ytg <= 8,
        "lockdown_kick_range_shell": fp >= 45 and down >= 3,
        "lockdown_long_yardage_bracket": deep >= .25 or (down >= 4 and ytg >= 9),
        "drift_prevent": explosive >= .20 or (deep >= .25 and context.get("score_diff", 0) > 0),
        "blitz_short_yardage_pressure": down >= 4 and ytg <= 8,
        "rugby_rush_line": down <= 3 and ytg >= 12,
        "afl_kick_in_press": fp <= 20 and snap <= 3,
        "lax_ride": "after_takeaway" in tags and 1 <= snap <= 3,
        "swarm_containment": "early_down" in tags or perimeter >= .25,
        "shadow_robber": down >= 4 or pass_rate >= .45,
        "chaos_lateral_trap": "early_down" in tags or lateral >= .20,
        "predator_exhaustion_press": offense_energy is not None and offense_energy < 82 and 1 <= snap <= 3,
    }.get(package_id, False)
    return .45 if secondary else 0.0

PRESS_PACKAGES = {"blitz_short_yardage_pressure", "rugby_rush_line", "afl_kick_in_press", "lax_ride", "predator_exhaustion_press"}
COVER_PACKAGES = {"lockdown_kick_range_shell", "lockdown_long_yardage_bracket", "drift_prevent", "shadow_robber", "swarm_containment", "chaos_lateral_trap"}
WALL_PACKAGES = {"fortress_goal_line_stand", "fortress_short_yardage_wall"}

def execution_strength(familiarity, energy, authority):
    # Scheme and individual execution already matter in the contest. A tired
    # group cannot fully execute the practiced package; no extra talent boost.
    readiness = max(.50, min(1.0, (energy if energy is not None else 85)/85))
    return min(1.0, max(0.0, familiarity * readiness * (.75 + .25*authority)))

def rush_commitment(rng, scheme, blitz, package, tactics, context, formation):
    """Return a legal intended 1–6 rusher call before family selection."""
    normal = 4 if blitz and scheme == "blitz_pack" else 3 if blitz else 2
    weights = {n: 0.0 for n in range(1,7)}
    weights[normal] = 1.0
    authority = tactics.get("authority", .65)
    pressure = tactics.get("pressure_bias", 0.0)
    aggression = tactics.get("aggression", .5)
    adapt = tactics.get("adaptability", .5)
    stubborn = tactics.get("stubbornness", .5)
    energy = context.get("defense_energy") or 75
    diff = context.get("score_diff", 0)
    down = context.get("down", 1)
    ytg = context.get("yards_to_go", 20)
    late = context.get("quarter", 1) >= 3
    chasing = late and diff <= -9
    protect = late and diff >= 9
    exposure = context.get("recent_explosive_rate", 0.0) * adapt * (1-.65*stubborn)
    appetite = max(.15, min(1.2, .55 + 1.5*pressure + .45*(aggression-.5) - .8*exposure))
    readiness = max(.1, min(1.0, (energy-40)/40))
    pid = package.get("package_id") if package else None
    strength = package.get("strength", 0.0) if package else 0.0
    weights[1] += authority * (.04 + .12*protect + .65*strength*(pid in COVER_PACKAGES))
    weights[2] += .15*authority + .25*strength*(pid in WALL_PACKAGES)
    weights[3] += .12*authority
    weights[4] += readiness*appetite*authority*(.08 + .35*strength*(pid in PRESS_PACKAGES))
    weights[5] += readiness*appetite*authority*(.025 + .12*chasing + .42*strength*(pid in PRESS_PACKAGES))
    # Six is reserved for urgent or fully committed pressure situations.
    urgent = chasing or (down >= 5 and ytg <= 8)
    if urgent:
        weights[6] += readiness*appetite*authority*(.035 + .22*strength*(pid in PRESS_PACKAGES))
    if protect or pid in COVER_PACKAGES:
        weights[4] *= .5
        weights[5] *= .25
        weights[6] *= .15
    if formation == "spread":
        weights[5] *= .75
        weights[6] *= .65
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]

# Extra coverage space is an actual cost in the kick-pass completion contest.
COVERAGE_DELTA = {0: -.06, 1: -.045, 2: 0, 3: .035, 4: .08, 5: .135, 6: .20}
