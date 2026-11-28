"""Formations, motion and the Seagull (rulebook v2.1, sections 11 to 13).

Helpers for ViperballEngine:

* listing a team's Seagulls before a game,
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


def list_seagulls(lines, bench, keepers, tackle_score, max_listed=MAX_SEAGULLS):
    """The coach lists up to two Seagulls on the game sheet.

    ``lines`` are the midfield lines built from the whole roster, best line
    first. Candidates are midfield players who are not on the top line:
    the lower lines and the bench. A Seagull plays her own group plus up to
    two more where she is as good as the players there now:

    * defensive back, if she tackles as well as the top line's fourth DB,
    * Keeper, if she rates within 5% of the weaker starting Keeper,
    * flanker, for a Viper who rates as well as the top line's weakest flanker.

    Only a Viper by position may be listed at Viper, so the player in the
    Viper jersey is always a Viper. Returns ``[{"name", "groups"}]``.
    """
    if not lines:
        return []
    top = lines[0]
    top_names = {p.name for p in top}
    dbs = sorted(top, key=tackle_score, reverse=True)[:4]
    db_bar = tackle_score(dbs[-1]) * 0.97 if dbs else None
    flankers = [p.overall for p in top if p.position != "Viper"]
    flank_bar = min(flankers) if flankers else None
    keeper_bar = min(k.overall for k in keepers[:2]) * 0.95 if keepers else None

    seen, picks = set(), []
    for p in [p for line in lines[1:] for p in line] + list(bench):
        if p.name in top_names or p.name in seen or p.position not in MIDFIELD_POSITIONS:
            continue
        seen.add(p.name)
        groups = ["Viper" if p.position == "Viper" else "flanker"]
        extras = []
        if db_bar is not None and tackle_score(p) >= db_bar:
            extras.append(("defensive back", tackle_score(p) / max(1.0, db_bar)))
        if keeper_bar is not None and p.overall >= keeper_bar:
            extras.append(("Keeper", p.overall / max(1.0, keeper_bar)))
        if p.position == "Viper" and flank_bar is not None and p.overall >= flank_bar:
            extras.append(("flanker", p.overall / max(1.0, flank_bar)))
        if not extras:
            continue
        extras.sort(key=lambda e: e[1], reverse=True)
        groups += [g for g, _ in extras[:2]]
        picks.append((p.overall + 3 * len(groups), p.name, groups))
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
        return 0.35 + 0.65 * movers + (0.5 if slide else 0.0)
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
