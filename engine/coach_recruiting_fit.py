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


def recruiting_preferences(staff):
    """Resolve the same calling coaches and delegation used on game day."""
    if not staff:
        return {}
    off = resolve_offensive_tactics(staff)
    defense = resolve_defensive_tactics(staff)
    result = {}
    for tactics, catalog in ((off, OFFENSE), (defense, DEFENSE)):
        for pos, attrs in catalog.get(tactics.get("signature"), {}).items():
            # Defensive preferences own defensive roster positions. Do not
            # stack two independent boosts for a two-way prospect.
            result[pos] = (attrs, float(tactics.get("authority", 1.0)))
    return result


def recruiting_fit(recruit, preferences):
    """Signed fractional CPU target-score adjustment, bounded to +/-8%.

    Compare relevant skills to the prospect's overall skill mean. A strong
    all-round player is already rewarded by the ordinary targeting score.
    """
    spec = (preferences or {}).get(recruit.position)
    if not spec:
        return 0.0
    attrs, authority = spec
    values = {key: getattr(recruit, "true_" + key, None) for key in ATTRS}
    if any(values[key] is None for key in attrs) or any(v is None for v in values.values()):
        return 0.0
    baseline = sum(values.values()) / len(values)
    preferred = sum(values[key] for key in attrs) / len(attrs)
    return max(-MAX_FIT, min(MAX_FIT, (preferred - baseline) / 30 * MAX_FIT)) * max(0.0, min(1.0, authority))
