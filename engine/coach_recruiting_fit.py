"""Coach-owned recruiting preferences, not player ratings or game bonuses.

CPU boards already rank using true overall. Fit is a small relative skill
preference on that same AI-only path; it never changes a recruit's attributes.
"""
from .coach_tactics import resolve_offensive_tactics, resolve_defensive_tactics

MAX_FIT = .08

OFFENSE = {
    "vertical_attack": {
        "Zeroback": ("kicking", "kick_power", "kick_accuracy"),
        "Viper": ("speed", "hands", "agility"),
        "Wingback": ("speed", "hands"), "Slotback": ("speed", "hands"),
        "Offensive Line": ("power", "awareness"),
    },
    "territory_control": {
        "Zeroback": ("kick_accuracy", "awareness", "kicking"),
        "Halfback": ("hands", "stamina"), "Offensive Line": ("power", "stamina"),
        "Keeper": ("kicking", "kick_accuracy", "hands"),
    },
    "run_to_kick": {
        "Halfback": ("power", "stamina", "hands"),
        "Offensive Line": ("power", "stamina"),
        "Zeroback": ("awareness", "agility", "hands"),
        "Wingback": ("power", "stamina"),
    },
    "spread_motion": {
        "Viper": ("agility", "speed", "lateral_skill"),
        "Wingback": ("agility", "speed", "lateral_skill"),
        "Slotback": ("agility", "hands", "lateral_skill"),
        "Zeroback": ("agility", "lateral_skill", "awareness"),
    },
}
DEFENSE = {
    "run_wall": {"Defensive Line": ("power", "tackling", "stamina"),
                 "Keeper": ("tackling", "awareness")},
    "deep_coverage": {"Defensive Line": ("awareness", "stamina"),
                      "Keeper": ("speed", "hands", "awareness")},
    "selective_pressure": {"Defensive Line": ("speed", "power", "agility"),
                           "Keeper": ("awareness", "tackling")},
    "pursuit_zone": {"Defensive Line": ("agility", "speed", "tackling"),
                     "Keeper": ("speed", "agility", "tackling")},
    "turnover_hunt": {"Defensive Line": ("agility", "tackling", "awareness"),
                      "Keeper": ("hands", "agility", "awareness")},
}
ATTRS = ("speed", "stamina", "agility", "power", "awareness", "hands",
         "kicking", "kick_power", "kick_accuracy", "lateral_skill", "tackling")


# Map existing game school IDs to skill preferences. Unknown or balanced
# schools have no school bonus; a coach's own interpretation still applies.
# These are recruiting affinities, not a second game playbook.
OFFENSE_SCHOOLS = {
    "ground_pound": "run_to_kick", "ground_control": "run_to_kick",
    "stampede": "run_to_kick",
    "boot_raid": "territory_control", "ball_control": "territory_control",
    "six_shooter": "territory_control", "ironclad": "territory_control",
    "east_coast": "territory_control", "possession_kp": "territory_control",
    "shock_and_awe": "vertical_attack", "quick_strike": "vertical_attack",
    "lateral_spread": "spread_motion", "chain_gang": "spread_motion",
    "slick_n_slide": "spread_motion", "ghost": "spread_motion", "mousetrap": "spread_motion",
}
DEFENSE_SCHOOLS = {
    "fortress": "run_wall", "trench_wall": "run_wall",
    "lockdown": "deep_coverage", "sky_cover": "deep_coverage",
    "blitz_pack": "selective_pressure", "keeper_hunt": "selective_pressure",
    "shadow": "pursuit_zone", "edge_net": "pursuit_zone",
    "predator": "turnover_hunt", "chaos": "turnover_hunt", "bounty_defense": "turnover_hunt",
    "drift": "deep_coverage", "bend_dont_break": "deep_coverage",
}


def recruiting_preferences(staff, style_config=None):
    """Blend the program's school and the actual calling coach's signature.

    School identity is the larger influence; a different coordinator can
    shift the target within that school. A missing school or staff is neutral.
    """
    style_config = style_config or {}
    off = resolve_offensive_tactics(staff)
    defense = resolve_defensive_tactics(staff)
    result = {}
    for side, tactics, catalog, schools in (
        ("offense", off, OFFENSE, OFFENSE_SCHOOLS),
        ("defense", defense, DEFENSE, DEFENSE_SCHOOLS),
    ):
        school = catalog.get(schools.get(style_config.get(side + "_style")), {})
        coach = catalog.get(tactics.get("signature"), {})
        for pos in sorted(set(school) | set(coach)):
            parts = []
            if pos in school:
                parts.append((school[pos], .65 if pos in coach else 1.0))
            if pos in coach:
                parts.append((coach[pos], (.35 if pos in school else 1.0)
                              * float(tactics.get("authority", 1.0))))
            # Defensive preferences own defensive roster positions when
            # present; never stack two independent fit bonuses.
            result[pos] = parts
    return result


def recruiting_fit(recruit, preferences):
    """Signed fractional CPU target-score adjustment, bounded to +/-8%.

    Compare relevant skills to the prospect's overall skill mean. A strong
    all-round player is already rewarded by the ordinary targeting score.
    """
    parts = (preferences or {}).get(recruit.position)
    if not parts:
        return 0.0
    values = {key: getattr(recruit, "true_" + key, None) for key in ATTRS}
    if any(v is None for v in values.values()):
        return 0.0
    baseline = sum(values.values()) / len(values)
    score = 0.0
    for attrs, weight in parts:
        preferred = sum(values[key] for key in attrs) / len(attrs)
        score += max(-MAX_FIT, min(MAX_FIT, (preferred - baseline) / 30 * MAX_FIT)) * weight
    return max(-MAX_FIT, min(MAX_FIT, score))
