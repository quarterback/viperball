"""PEN-03: player discipline, separate from yardage enforcement.

Rates are provisional until PEN-04's full-game calibration is run.
"""
IMMEDIATE_EJECTION = frozenset({"Targeting", "Fighting", "Throwing Punch"})
UNSPORTSMANLIKE = frozenset({
    "Unsportsmanlike Conduct", "Taunting", "Excessive Celebration",
    "Provoking Ill Will", "Obscene Language",
})
# Deliberately exclude routine procedural, equipment and safety fouls from
# the two-strike rule. Serious safety violations have their own rule above.
IMMEDIATE_RATE_SCALE = 0.20


def misconduct_kind(name):
    if name in IMMEDIATE_EJECTION:
        return "immediate"
    if name in UNSPORTSMANLIKE:
        return "conduct"
    return ""


def occurrence_multiplier(kind):
    """Reduce severe infractions pending empirical season calibration."""
    return IMMEDIATE_RATE_SCALE if kind == "immediate" else 1.0


def offender_weight(player):
    """Bounded awareness/fatigue proxy; no new persistent player rating."""
    awareness = max(0.0, min(99.0, float(getattr(player, "awareness", 50))))
    energy = max(0.0, min(100.0, float(getattr(player, "game_energy", 100))))
    return (1.25 - 0.50 * awareness / 99.0) * (1.0 + 0.35 * (1.0 - energy / 100.0))
