"""One rating scale for every league.

In November 2026 the college game moved to the current rating scale: a
median player is 35, stars reach the 60s to 80s, and the engine converts
ratings back to the 60 to 100 scale its formulas were written for
(game_engine.scale_rating: 35 is 70, one current point is half an old one).
Pro, WVL and FIV players were left on the old 60 to 100 scale.  These helpers
move old ratings onto the current scale with the inverse of that conversion.
"""
from __future__ import annotations

RATING_ATTRS = (
    "speed", "stamina", "kicking", "lateral_skill", "tackling", "agility",
    "power", "awareness", "hands", "kick_power", "kick_accuracy",
)
TEAM_STAT_ATTRS = ("avg_speed", "avg_stamina", "kicking_strength",
                   "lateral_proficiency", "defensive_strength")
CURRENT = "current"


def legacy_to_current(value: float) -> int:
    """Old 60 to 100 rating on the current scale (old 70 is 35, slope 2)."""
    return int(max(10, min(96, round(35 + (value - 70) * 2))))


def current_to_legacy(value: float) -> float:
    """Current rating as its old scale equivalent, for formulas still written
    against old numbers (salaries, for one)."""
    return 70 + (value - 35) * 0.5


def convert_card(card) -> None:
    """Move a PlayerCard's ratings from the old scale to the current one."""
    for a in RATING_ATTRS:
        if hasattr(card, a):
            setattr(card, a, legacy_to_current(getattr(card, a)))


def convert_card_dict(d: dict) -> dict:
    """Same for a PlayerCard.to_dict() dict (ratings live under "ratings")."""
    ratings = d.get("ratings")
    if isinstance(ratings, dict):
        for a in RATING_ATTRS:
            if isinstance(ratings.get(a), (int, float)):
                ratings[a] = legacy_to_current(ratings[a])
    return d
