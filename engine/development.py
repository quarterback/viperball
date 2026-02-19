"""
Viperball Player Development Arcs

Applies offseason attribute changes to PlayerCard objects based on:
- Development trait (normal / quick / slow / late_bloomer)
- Academic year (Freshman → Sophomore → Junior → Senior → Graduate)
- Potential (1-5 stars): higher potential = larger ceiling for gains
- Age/position: slight late-career decline in physical attributes

Called once per offseason by Dynasty.advance_season() AFTER awards are resolved.

Usage:
    from engine.development import apply_offseason_development

    report = apply_offseason_development(player_card)
    print(report.summary)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional
from engine.player_card import PlayerCard


# ──────────────────────────────────────────────
# YEAR ORDER
# ──────────────────────────────────────────────

_YEAR_ORDER = ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"]
_YEAR_INDEX = {y: i for i, y in enumerate(_YEAR_ORDER)}


def _next_year(year: str) -> str:
    idx = _YEAR_INDEX.get(year, 1)
    if idx >= len(_YEAR_ORDER) - 1:
        return "Graduate"   # Stays Graduate (5th year / grad student)
    return _YEAR_ORDER[idx + 1]


# ──────────────────────────────────────────────
# DEVELOPMENT REPORT
# ──────────────────────────────────────────────

@dataclass
class DevelopmentEvent:
    """A single notable change during offseason development."""
    player_name: str
    event_type: str   # "breakout" | "decline" | "steady_growth" | "stagnation"
    description: str
    attr_changes: dict = field(default_factory=dict)   # attr -> delta


@dataclass
class DevelopmentReport:
    """Results of all player development for a single offseason."""
    notable_events: List[DevelopmentEvent] = field(default_factory=list)
    year_updated: dict = field(default_factory=dict)   # player_name -> new year

    @property
    def breakouts(self) -> List[DevelopmentEvent]:
        return [e for e in self.notable_events if e.event_type == "breakout"]

    @property
    def declines(self) -> List[DevelopmentEvent]:
        return [e for e in self.notable_events if e.event_type == "decline"]

    def display(self):
        if self.breakouts:
            print(f"\n  BREAKOUT PLAYERS ({len(self.breakouts)})")
            print(f"  {'-' * 50}")
            for ev in self.breakouts:
                print(f"    {ev.player_name}: {ev.description}")
        if self.declines:
            print(f"\n  DECLINING PLAYERS ({len(self.declines)})")
            print(f"  {'-' * 50}")
            for ev in self.declines:
                print(f"    {ev.player_name}: {ev.description}")


# ──────────────────────────────────────────────
# ATTRIBUTE GAIN TABLES
# ──────────────────────────────────────────────

# Gain ranges (min, max) per attribute by development profile.
# All values represent potential +points in one offseason.
_GAINS_BY_PROFILE = {
    "quick": {
        "speed":        (2, 5),
        "stamina":      (2, 4),
        "agility":      (2, 5),
        "power":        (1, 3),
        "awareness":    (2, 5),
        "hands":        (2, 4),
        "kicking":      (1, 3),
        "kick_power":   (1, 3),
        "kick_accuracy":(1, 3),
        "lateral_skill":(2, 5),
        "tackling":     (1, 4),
    },
    "normal": {
        "speed":        (1, 3),
        "stamina":      (1, 3),
        "agility":      (1, 3),
        "power":        (1, 3),
        "awareness":    (1, 4),
        "hands":        (1, 3),
        "kicking":      (0, 2),
        "kick_power":   (0, 2),
        "kick_accuracy":(0, 2),
        "lateral_skill":(1, 3),
        "tackling":     (1, 3),
    },
    "slow": {
        "speed":        (0, 2),
        "stamina":      (0, 2),
        "agility":      (0, 2),
        "power":        (0, 2),
        "awareness":    (1, 3),
        "hands":        (0, 2),
        "kicking":      (0, 1),
        "kick_power":   (0, 1),
        "kick_accuracy":(0, 1),
        "lateral_skill":(0, 2),
        "tackling":     (0, 2),
    },
    "late_bloomer": {
        # Early years: minimal gains (Freshman, Sophomore)
        "early": {
            "speed":        (0, 1),
            "stamina":      (0, 2),
            "agility":      (0, 1),
            "power":        (0, 2),
            "awareness":    (1, 3),
            "hands":        (0, 1),
            "kicking":      (0, 1),
            "kick_power":   (0, 1),
            "kick_accuracy":(0, 1),
            "lateral_skill":(0, 1),
            "tackling":     (0, 2),
        },
        # Late years: large jumps (Junior → Senior / Senior → Graduate)
        "late": {
            "speed":        (3, 7),
            "stamina":      (2, 6),
            "agility":      (3, 7),
            "power":        (2, 5),
            "awareness":    (3, 7),
            "hands":        (2, 5),
            "kicking":      (2, 4),
            "kick_power":   (2, 4),
            "kick_accuracy":(2, 4),
            "lateral_skill":(3, 7),
            "tackling":     (2, 5),
        },
    },
}

# Physical decline in Senior/Graduate year (slight negative adjustment)
_SENIOR_DECLINE_ATTRS = ["speed", "stamina", "agility"]
_DECLINE_RANGE = (-2, 0)   # -2 to 0 points


def _clamp(val: int, lo: int = 40, hi: int = 99) -> int:
    return max(lo, min(hi, val))


# ──────────────────────────────────────────────
# MAIN FUNCTION
# ──────────────────────────────────────────────

def apply_offseason_development(
    card: PlayerCard,
    rng: Optional[random.Random] = None,
    dev_boost: float = 0.0,
) -> DevelopmentEvent | None:
    """
    Apply one offseason of development to a PlayerCard.

    Modifies attributes in-place and advances the player's year.
    Returns a DevelopmentEvent if the change is notable (breakout or decline),
    or None for routine development.

    Args:
        dev_boost: Extra development points from DraftyQueenz donations (0-8).
                   Scales the upper bound of gains upward.
    """
    if rng is None:
        rng = random.Random()

    dev = card.development
    year = card.year
    potential = card.potential
    year_idx = _YEAR_INDEX.get(year, 1)

    if dev == "late_bloomer":
        if year_idx <= 1:
            gains = _GAINS_BY_PROFILE["late_bloomer"]["early"]
        else:
            gains = _GAINS_BY_PROFILE["late_bloomer"]["late"]
    else:
        gains = _GAINS_BY_PROFILE.get(dev, _GAINS_BY_PROFILE["normal"])

    potential_scale = 0.6 + (potential - 1) * 0.1
    boost_scale = 1.0 + (dev_boost / 16.0)

    total_gain = 0
    attr_changes = {}
    attrs_to_develop = [
        "speed", "stamina", "agility", "power", "awareness",
        "hands", "kicking", "kick_power", "kick_accuracy",
        "lateral_skill", "tackling",
    ]

    for attr in attrs_to_develop:
        lo, hi = gains[attr]
        scaled_hi = max(lo, int(hi * potential_scale * boost_scale))
        delta = rng.randint(lo, scaled_hi)

        # Apply gain
        old_val = getattr(card, attr)
        new_val = _clamp(old_val + delta)
        setattr(card, attr, new_val)
        actual_delta = new_val - old_val
        if actual_delta != 0:
            attr_changes[attr] = actual_delta
        total_gain += actual_delta

    # Senior/Graduate physical decline for normal/slow
    event_type = None
    event_desc = None

    if year in ("Senior", "Graduate") and dev in ("normal", "slow"):
        for attr in _SENIOR_DECLINE_ATTRS:
            delta = rng.randint(_DECLINE_RANGE[0], _DECLINE_RANGE[1])
            old_val = getattr(card, attr)
            new_val = _clamp(old_val + delta)
            setattr(card, attr, new_val)
            actual = new_val - old_val
            if actual != 0:
                attr_changes[attr] = attr_changes.get(attr, 0) + actual

    # Classify event
    if dev == "late_bloomer" and year_idx >= 2 and total_gain >= 12:
        event_type = "breakout"
        event_desc = f"Late-bloomer breakout (+{total_gain} total attributes)"
    elif dev == "quick" and year_idx <= 1 and total_gain >= 15:
        event_type = "breakout"
        event_desc = f"Sophomore explosion (+{total_gain} total attributes)"
    elif year in ("Senior", "Graduate") and total_gain <= -3:
        event_type = "decline"
        event_desc = f"Physical decline in final year ({total_gain:+d} total attributes)"
    elif total_gain >= 10 and potential >= 4:
        event_type = "breakout"
        event_desc = f"High-potential breakout (+{total_gain} total attributes)"

    # Advance year (skip if redshirted)
    if getattr(card, '_redshirt_this_season', False):
        card._was_redshirted = True
        card.redshirt = True
    else:
        card.year = _next_year(year)

    if event_type:
        return DevelopmentEvent(
            player_name=card.full_name,
            event_type=event_type,
            description=event_desc,
            attr_changes=attr_changes,
        )
    return None


REDSHIRT_AI_RATE = 0.22


def apply_redshirt_decisions(
    players: list,
    injured_players: Optional[list] = None,
    is_human: bool = False,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Decide which players get redshirted this offseason.

    Eligibility:
    - Injured players (season-ending injury) are always eligible
    - Players who played 4 or fewer games are eligible
    - Only non-Graduate players can be redshirted

    AI teams redshirt ~22% of eligible players.
    Human teams must set redshirt manually (not handled here).

    Returns list of redshirted player names.
    """
    if rng is None:
        rng = random.Random()

    if injured_players is None:
        injured_players = []

    injured_names = set(injured_players)
    redshirted = []

    for card in players:
        year = card.year
        if year in ("Graduate", "graduate"):
            continue

        games = getattr(card, 'season_games_played', getattr(card, '_season_games', 99))
        is_injured = card.full_name in injured_names if hasattr(card, 'full_name') else False

        eligible = is_injured or games <= 4

        if not eligible:
            continue

        if is_human:
            continue

        if rng.random() < REDSHIRT_AI_RATE:
            card._redshirt_this_season = True
            redshirted.append(card.full_name if hasattr(card, 'full_name') else str(card))

    return redshirted


def apply_team_development(
    players: list,
    rng: Optional[random.Random] = None,
    dev_boost: float = 0.0,
) -> DevelopmentReport:
    """
    Apply offseason development to a list of PlayerCard objects.

    Args:
        players: list of PlayerCard objects
        rng: optional seeded Random instance for reproducibility
        dev_boost: DraftyQueenz development boost (0-8) to amplify stat gains

    Returns:
        DevelopmentReport with notable events
    """
    if rng is None:
        rng = random.Random()

    report = DevelopmentReport()

    for card in players:
        event = apply_offseason_development(card, rng=rng, dev_boost=dev_boost)
        if event:
            report.notable_events.append(event)
        report.year_updated[card.full_name] = card.year

    return report


def get_preseason_breakout_candidates(
    players: list,
    top_n: int = 3,
) -> list:
    """
    Return up to top_n players most likely to break out next season.

    Criteria:
    - late_bloomer developers approaching their junior/senior year
    - High potential (4-5 stars) on a normal development path in early years
    - High potential but overall rating noticeably below their potential ceiling
    """
    candidates = []

    for card in players:
        score = 0
        year_idx = _YEAR_INDEX.get(card.year, 1)
        ceiling = 60 + card.potential * 7   # rough potential ceiling estimate

        if card.development == "late_bloomer" and year_idx == 2:
            score += 40   # Junior late bloomer: prime breakout candidate
        elif card.development == "late_bloomer" and year_idx == 1:
            score += 20

        if card.potential >= 4 and card.overall < ceiling - 8:
            score += 25

        if card.development == "quick" and year_idx == 0:
            score += 30   # Freshman quick developer = sophomore jump incoming

        if score > 0:
            candidates.append((score, card))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [card for _, card in candidates[:top_n]]
