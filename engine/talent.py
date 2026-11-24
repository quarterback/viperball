"""League talent ladder for players created after the opening rosters.

The opening rosters (scripts/generate_rosters.py) roll each player's level
from TALENT_LADDER and her stats around that level, so a league has a few
stars, a thin middle and a long tail. Recruits, high school players and
portal players use the same ladder here, so a dynasty keeps the same shape
of talent as it ages instead of drifting toward one number.
"""
from __future__ import annotations

import random
from functools import lru_cache
from typing import Dict, Optional

from scripts.generate_rosters import (
    PLAYER_STAT_SPREAD,
    TALENT_LADDER,
    _POSITION_OFFSETS,
)

STAT_KEYS = (
    "speed", "stamina", "kicking", "lateral_skill", "tackling",
    "agility", "power", "awareness", "hands", "kick_power", "kick_accuracy",
)

# Class gaps used by the opening rosters (generate_player_attributes).
COLLEGE_YEAR_MOD = {"Freshman": -4, "Sophomore": -2, "Junior": 0, "Senior": 2, "Graduate": 2}
# High school players are measured against the college freshman they will
# become: a senior graduates at that level, a freshman is three years of
# growth (about 2 a year) short of it.
HS_YEAR_GAP = {"Senior": 0, "Junior": 2, "Sophomore": 4, "Freshman": 6}

# Share of each recruiting class by stars (same as recruiting._STAR_DISTRIBUTION).
STAR_SHARES = ((5, 0.03), (4, 0.12), (3, 0.35), (2, 0.35), (1, 0.15))


def roll_level(rng: Optional[random.Random] = None, shift: int = 0) -> int:
    """A player's level drawn from the league ladder."""
    rng = rng or random
    r = rng.random()
    cumulative = 0.0
    lo, hi = TALENT_LADDER[-1][1], TALENT_LADDER[-1][2]
    for prob, t_lo, t_hi in TALENT_LADDER:
        cumulative += prob
        if r < cumulative:
            lo, hi = t_lo, t_hi
            break
    return max(10, min(90, rng.randint(lo, hi) + shift))


@lru_cache(maxsize=1)
def _level_distribution() -> Dict[int, float]:
    dist: Dict[int, float] = {}
    for prob, lo, hi in TALENT_LADDER:
        each = prob / (hi - lo + 1)
        for level in range(lo, hi + 1):
            dist[level] = dist.get(level, 0.0) + each
    return dist


@lru_cache(maxsize=1)
def star_cutoffs() -> Dict[int, int]:
    """Lowest ladder level for each star rating, so stars keep their shares."""
    dist = _level_distribution()
    levels = sorted(dist, reverse=True)
    cutoffs: Dict[int, int] = {}
    target = 0.0
    cumulative = 0.0
    idx = 0
    for stars, share in STAR_SHARES[:-1]:
        target += share
        while idx < len(levels) and cumulative + dist[levels[idx]] <= target + 1e-9:
            cumulative += dist[levels[idx]]
            idx += 1
        cutoffs[stars] = levels[idx - 1] if idx else levels[0]
    cutoffs[1] = min(levels)
    return cutoffs


def stars_for_level(level: int) -> int:
    cut = star_cutoffs()
    for stars in (5, 4, 3, 2):
        if level >= cut[stars]:
            return stars
    return 1


def roll_level_for_stars(stars: int, rng: Optional[random.Random] = None) -> int:
    """A ladder level that rates as the given number of stars."""
    rng = rng or random
    for _ in range(400):
        level = roll_level(rng)
        if stars_for_level(level) == stars:
            return level
    cut = star_cutoffs()
    return cut.get(stars, 10)


def roll_stats(level: int, position: str, rng: Optional[random.Random] = None,
               year_mod: int = 0, ceiling: int = 96) -> Dict[str, int]:
    """Stats around a level, with position strengths, and a work rate."""
    rng = rng or random
    pos_off = _POSITION_OFFSETS.get(position, {})
    stats: Dict[str, int] = {}
    for stat in STAT_KEYS:
        center = level + pos_off.get(stat, 0) + year_mod
        stats[stat] = max(10, min(ceiling, int(round(rng.gauss(center, PLAYER_STAT_SPREAD)))))
    stats["work_rate"] = max(10, min(95, int(round(rng.gauss(stats["stamina"] * 0.5 + 18, 13)))))
    return stats
