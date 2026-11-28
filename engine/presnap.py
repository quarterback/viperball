"""Formations, motion and the Seagull (rulebook v2.1, sections 11 to 13).

Helpers for ViperballEngine:

* listing a team's Seagulls before a game (college only),
* rolling backfield motion for a snap, and
* scaling the before the snap fouls by what actually happened on that snap.

The engine owns the lineup and the play resolution. Nothing here reads or
changes game state on its own.
"""

MIDFIELD_POSITIONS = ("Viper", "Halfback", "Wingback", "Slotback")
MAX_SEAGULLS = 2

# Fewest offensive players on the line at the snap, by level.
LINE_MINIMUM = {"high_school": 3, "college": 5, "pro": 5}

# How often an offense puts a Seagull on the line in place of a lineman,
# by offense style. Lateral and misdirection offenses use her most, power
# offenses least. Styles not listed use the default.
SEAGULL_LINE_RATE_DEFAULT = 0.10
SEAGULL_LINE_RATE = {
    "chain_gang": 0.22, "lateral_spread": 0.20, "ghost": 0.20,
    "slick_n_slide": 0.16, "boot_raid": 0.14,
    "ground_control": 0.06, "stampede": 0.06, "ball_control": 0.06,
}

# Backfield motion. Each midfield player off the line is in motion at the
# snap with chance MOTION_BASE + MOTION_SCALE * the style's pre_snap_motion.
MOTION_DEFAULT_PREF = 0.30
MOTION_BASE = 0.08
MOTION_SCALE = 0.30
MOTION_LATE_DOWN = 0.40      # downs 5 and 6 and kick mode: fewer movers
MOTION_DECOY_VIPER = 1.60    # a Decoy Viper goes in motion more often
SEAGULL_SLIDE_RATE = 0.85    # a Seagull on the line usually slides
SECOND_SEAGULL_RATE = 0.25   # both Seagulls on the line; only one may move

# High school short line: how often an offense lines up with fewer than five
# on the line, putting bench midfielders in for linemen, by style.
SHORT_LINE_RATE_DEFAULT = 0.12
SHORT_LINE_RATE = {
    "chain_gang": 0.35, "lateral_spread": 0.32, "ghost": 0.25, "slick_n_slide": 0.25,
    "boot_raid": 0.18, "ground_control": 0.05, "stampede": 0.05, "ball_control": 0.05,
}
SHORT_LINE_TWO = 0.35        # share of short line snaps with only three on the line


LISTING_GROUPS = ("Viper", "flanker", "Offensive Line", "Defensive Line", "Keeper",
                  "defensive back")
OPEN_FIELD = ("Viper", "flanker", "Keeper", "defensive back")


def list_seagulls(candidates, bars, max_listed=MAX_SEAGULLS):
    """The coach lists up to two Seagulls on the game sheet (college only).

    ``candidates`` are the players off the top midfield line, other than the
    starting Zeroback. ``bars`` holds, for each group, the fit of the player
    a Seagull would replace there. A player is listed in another group when
    she is a natural fit there (engine/position_fit.py) and her fit is
    within 3% of that bar. She needs at least one group besides her own, at
    least one open field group, and is listed in at most three. Returns
    ``[{"name", "groups"}]``.
    """
    from engine.position_fit import adaptability, fit, natural_fit, own_group
    picks = []
    for p in candidates:
        own = own_group(p)
        extras = []
        for group in LISTING_GROUPS:
            if group == own or group not in bars or not natural_fit(p, group):
                continue
            f = fit(p, group)
            if f >= bars[group] * 0.97:
                extras.append((group, f / max(1.0, bars[group])))
        if not extras:
            continue
        extras.sort(key=lambda e: e[1], reverse=True)
        groups = [own] + [g for g, _ in extras[:2]]
        # A Seagull is an athlete: at least one of her groups is in the open
        # field. A lineman who can play both lines is a cover player.
        if not any(g in OPEN_FIELD for g in groups):
            continue
        # Rank by fit across her groups, how many she covers and how
        # adaptable she is.
        value = (sum(fit(p, g) for g in groups) / len(groups) + 4 * len(groups)
                 + 0.2 * adaptability(p))
        picks.append((value, p.name, groups))
    picks.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [{"name": name, "groups": groups} for _, name, groups in picks[:max_listed]]


def motion_chance(motion_pref, late_down):
    chance = MOTION_BASE + MOTION_SCALE * max(0.0, min(1.0, motion_pref))
    return chance * (MOTION_LATE_DOWN if late_down else 1.0)


def presnap_foul_scale(name, ctx):
    """How much more or less likely a before the snap foul is on this snap.

    The catalog rate is the league average. Motion fouls need movers, the
    Viper jersey fouls need a jersey change, and a Seagull sliding on the
    line gives the Umpire something to judge.
    """
    if not ctx:
        return 1.0
    movers = ctx.get("movers", 0)
    slide = bool(ctx.get("seagull_slide"))
    jersey = bool(ctx.get("jersey_report"))
    if name == "Illegal Motion":
        two = len(ctx.get("seagull_line_all") or ()) > 1
        return 0.35 + 0.65 * movers + (0.5 if slide else 0.0) + (0.4 if two else 0.0)
    if name == "Illegal Formation":
        return 1.5 if ctx.get("short_line") else 1.0
    if name == "Illegal Shift":
        return 0.45 + 0.55 * movers
    if name == "False Start":
        return 1.3 if slide else 1.0
    if name == "Missing Viper Jersey":
        return 3.0 if jersey else 0.35
    if name == "Illegal Viper Substitution":
        if jersey:
            return 5.0
        return 1.0 if ctx.get("seagull_on_offense") else 0.0
    return 1.0
