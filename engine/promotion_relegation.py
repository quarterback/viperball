"""
Promotion/Relegation Engine for the WVL
=========================================

Handles end-of-season tier movements between the 4-tier WVL pyramid:

Tier 1 ↔ Tier 2:
  - Bottom 3 in Tier 1 → relegated
  - Top 2 in Tier 2 → auto-promoted
  - 3rd in Tier 2 plays 16th in Tier 1 in a promotion/relegation playoff

Tier 2 ↔ Tier 3:
  - Bottom 3 in Tier 2 → relegated
  - Top 2 in Tier 3 → auto-promoted
  - 3rd in Tier 3 plays 18th in Tier 2 in a promotion/relegation playoff

Tier 3 ↔ Tier 4:
  - Bottom 2 in Tier 3 → relegated
  - Top 2 in Tier 4 → auto-promoted
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine.fast_sim import fast_sim_game
from engine.game_engine import load_team_from_json


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class TierMovement:
    """A single team moving between tiers."""
    team_key: str
    team_name: str
    from_tier: int
    to_tier: int
    reason: str  # "auto_promoted" | "auto_relegated" | "playoff_promoted" | "playoff_relegated"


@dataclass
class PromotionPlayoff:
    """A single-match promotion/relegation playoff."""
    higher_tier: int
    higher_tier_team_key: str
    higher_tier_team_name: str
    lower_tier_team_key: str
    lower_tier_team_name: str
    winner_key: Optional[str] = None
    winner_name: Optional[str] = None
    score: Optional[str] = None  # e.g., "24-18"


@dataclass
class PromotionRelegationResult:
    """Complete pro/rel result for one season."""
    movements: List[TierMovement] = field(default_factory=list)
    playoffs: List[PromotionPlayoff] = field(default_factory=list)
    new_tier_assignments: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "movements": [
                {
                    "team_key": m.team_key,
                    "team_name": m.team_name,
                    "from_tier": m.from_tier,
                    "to_tier": m.to_tier,
                    "reason": m.reason,
                }
                for m in self.movements
            ],
            "playoffs": [
                {
                    "higher_tier": p.higher_tier,
                    "higher_tier_team": p.higher_tier_team_key,
                    "lower_tier_team": p.lower_tier_team_key,
                    "winner": p.winner_key,
                    "score": p.score,
                }
                for p in self.playoffs
            ],
            "new_tier_assignments": self.new_tier_assignments,
        }

    @property
    def promoted_teams(self) -> List[TierMovement]:
        return [m for m in self.movements if m.to_tier < m.from_tier]

    @property
    def relegated_teams(self) -> List[TierMovement]:
        return [m for m in self.movements if m.to_tier > m.from_tier]


# ═══════════════════════════════════════════════════════════════
# STANDINGS HELPERS
# ═══════════════════════════════════════════════════════════════

def _sorted_standings(standings_list: List[dict]) -> List[dict]:
    """Sort standings by wins desc, then point differential desc."""
    return sorted(
        standings_list,
        key=lambda t: (-t.get("wins", 0), -(t.get("points_for", 0) - t.get("points_against", 0))),
    )


# ═══════════════════════════════════════════════════════════════
# PROMOTION PLAYOFF
# ═══════════════════════════════════════════════════════════════

def simulate_promotion_playoff(
    higher_tier_team_key: str,
    higher_tier_team_name: str,
    lower_tier_team_key: str,
    lower_tier_team_name: str,
    higher_tier: int,
    teams: Dict,
    rng: Optional[random.Random] = None,
) -> Tuple[PromotionPlayoff, List[TierMovement]]:
    """Simulate a single-match promotion/relegation playoff.

    The higher-tier team plays at home. Winner stays in / moves to higher tier.

    Args:
        higher_tier_team_key: Team key from the higher tier (fighting relegation)
        lower_tier_team_key: Team key from the lower tier (fighting for promotion)
        teams: Dict of team_key → Team objects (loaded game engine teams)

    Returns:
        (PromotionPlayoff result, list of TierMovement from this playoff)
    """
    if rng is None:
        rng = random.Random()

    playoff = PromotionPlayoff(
        higher_tier=higher_tier,
        higher_tier_team_key=higher_tier_team_key,
        higher_tier_team_name=higher_tier_team_name,
        lower_tier_team_key=lower_tier_team_key,
        lower_tier_team_name=lower_tier_team_name,
    )

    home_team = teams.get(higher_tier_team_key)
    away_team = teams.get(lower_tier_team_key)

    movements = []

    if home_team and away_team:
        result = fast_sim_game(home_team, away_team, seed=rng.randint(0, 999999) if rng else 0)
        home_score = result.get("home_score", 0)
        away_score = result.get("away_score", 0)
        playoff.score = f"{home_score}-{away_score}"

        if home_score >= away_score:
            # Higher tier team survives
            playoff.winner_key = higher_tier_team_key
            playoff.winner_name = higher_tier_team_name
            # No movements — everyone stays put
        else:
            # Lower tier team wins promotion
            playoff.winner_key = lower_tier_team_key
            playoff.winner_name = lower_tier_team_name
            movements.append(TierMovement(
                team_key=lower_tier_team_key,
                team_name=lower_tier_team_name,
                from_tier=higher_tier + 1,
                to_tier=higher_tier,
                reason="playoff_promoted",
            ))
            movements.append(TierMovement(
                team_key=higher_tier_team_key,
                team_name=higher_tier_team_name,
                from_tier=higher_tier,
                to_tier=higher_tier + 1,
                reason="playoff_relegated",
            ))
    else:
        # If teams can't be loaded, skip the playoff (no movement)
        playoff.winner_key = higher_tier_team_key
        playoff.winner_name = higher_tier_team_name

    return playoff, movements


# ═══════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════

def compute_tier_movements(
    tier_standings: Dict[int, List[dict]],
    tier_assignments: Dict[str, int],
    teams: Dict,
    rng: Optional[random.Random] = None,
) -> PromotionRelegationResult:
    """Compute all promotion/relegation movements for one season.

    Args:
        tier_standings: tier_number → list of {team_key, team_name, wins, losses, points_for, points_against}
                        Each list should be sorted by final position (best first).
        tier_assignments: current team_key → tier_number mapping
        teams: dict of team_key → Team objects for playoff simulation

    Returns:
        PromotionRelegationResult with all movements and updated tier assignments.
    """
    if rng is None:
        rng = random.Random()

    result = PromotionRelegationResult()
    new_assignments = dict(tier_assignments)

    # Process each tier boundary
    for boundary in _TIER_BOUNDARIES:
        higher_tier = boundary["higher_tier"]
        lower_tier = boundary["lower_tier"]

        higher_standings = _sorted_standings(tier_standings.get(higher_tier, []))
        lower_standings = _sorted_standings(tier_standings.get(lower_tier, []))

        if not higher_standings or not lower_standings:
            continue

        # Auto-relegation from higher tier
        relegate_count = boundary["relegate_count"]
        relegated = higher_standings[-relegate_count:] if relegate_count > 0 else []

        # Auto-promotion from lower tier
        promote_count = boundary["auto_promote_count"]
        promoted = lower_standings[:promote_count] if promote_count > 0 else []

        # Record auto-movements
        for team in relegated:
            # Check if this team is the playoff position team (handle separately)
            if boundary.get("playoff_enabled") and team == higher_standings[boundary["playoff_higher_pos"] - 1]:
                continue
            result.movements.append(TierMovement(
                team_key=team["team_key"],
                team_name=team["team_name"],
                from_tier=higher_tier,
                to_tier=lower_tier,
                reason="auto_relegated",
            ))
            new_assignments[team["team_key"]] = lower_tier

        for team in promoted:
            result.movements.append(TierMovement(
                team_key=team["team_key"],
                team_name=team["team_name"],
                from_tier=lower_tier,
                to_tier=higher_tier,
                reason="auto_promoted",
            ))
            new_assignments[team["team_key"]] = higher_tier

        # Promotion/relegation playoff
        if boundary.get("playoff_enabled"):
            h_pos = boundary["playoff_higher_pos"]  # 1-indexed position in higher tier
            l_pos = boundary["playoff_lower_pos"]    # 1-indexed position in lower tier

            if h_pos <= len(higher_standings) and l_pos <= len(lower_standings):
                h_team = higher_standings[h_pos - 1]
                l_team = lower_standings[l_pos - 1]

                playoff, playoff_movements = simulate_promotion_playoff(
                    higher_tier_team_key=h_team["team_key"],
                    higher_tier_team_name=h_team["team_name"],
                    lower_tier_team_key=l_team["team_key"],
                    lower_tier_team_name=l_team["team_name"],
                    higher_tier=higher_tier,
                    teams=teams,
                    rng=rng,
                )
                result.playoffs.append(playoff)
                for m in playoff_movements:
                    result.movements.append(m)
                    new_assignments[m.team_key] = m.to_tier

    result.new_tier_assignments = new_assignments
    return result


# Tier boundary definitions
_TIER_BOUNDARIES = [
    {
        "higher_tier": 1,
        "lower_tier": 2,
        "relegate_count": 3,       # Bottom 3 in T1 relegated (positions 16, 17, 18)
        "auto_promote_count": 2,   # Top 2 in T2 auto-promoted
        "playoff_enabled": True,
        "playoff_higher_pos": 16,  # 16th in T1 plays playoff
        "playoff_lower_pos": 3,    # 3rd in T2 plays playoff
    },
    {
        "higher_tier": 2,
        "lower_tier": 3,
        "relegate_count": 3,       # Bottom 3 in T2 relegated (positions 18, 19, 20)
        "auto_promote_count": 2,   # Top 2 in T3 auto-promoted
        "playoff_enabled": True,
        "playoff_higher_pos": 18,  # 18th in T2 plays playoff
        "playoff_lower_pos": 3,    # 3rd in T3 plays playoff
    },
    {
        "higher_tier": 3,
        "lower_tier": 4,
        "relegate_count": 2,       # Bottom 2 in T3 relegated
        "auto_promote_count": 2,   # Top 2 in T4 auto-promoted
        "playoff_enabled": False,
    },
]


def persist_tier_assignments(assignments: Dict[str, int], filepath: str):
    """Write tier assignments to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(assignments, f, indent=2)


def load_tier_assignments(filepath: str) -> Dict[str, int]:
    """Load tier assignments from a JSON file."""
    with open(filepath) as f:
        return json.load(f)
