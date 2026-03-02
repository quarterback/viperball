"""
WVL Free Agency Pipeline
=========================

Handles player movement into and within the WVL:
1. Import graduating college players from a dynasty export (Option A)
2. Generate synthetic free agents when no college save exists (Option B)
3. Run free agency — AI presidents sign players based on needs, budget, attractiveness
4. Process retirements based on age/overall
5. Roster management (cuts to maintain 36-player limit)

The owner gets ONE targeted free agent pick per offseason (signed at any cost).
All other signings are fully autonomous via AI president.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine.player_card import PlayerCard
from engine.development import should_retire


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class FreeAgent:
    """A player available for signing."""
    player_card: PlayerCard
    asking_salary: int          # 1-5 tier
    preferred_tier: Optional[int] = None  # preferred league tier (higher = more prestigious)
    source: str = "synthetic"   # "college_export" | "synthetic" | "released" | "retired_reentry"

    @property
    def overall(self) -> int:
        return self.player_card.overall


@dataclass
class FreeAgencyResult:
    """Results of one offseason's free agency period."""
    signings: List[Dict] = field(default_factory=list)      # {player_name, team_key, salary}
    owner_targeted_signing: Optional[Dict] = None           # owner's one pick
    unsigned: List[str] = field(default_factory=list)        # player names that went unsigned
    retirements: List[str] = field(default_factory=list)     # player names that retired

    def to_dict(self) -> dict:
        return {
            "signings": self.signings,
            "owner_targeted_signing": self.owner_targeted_signing,
            "unsigned": self.unsigned,
            "retirements": self.retirements,
            "total_signed": len(self.signings),
        }


# ═══════════════════════════════════════════════════════════════
# POOL BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_free_agent_pool_from_import(filepath: str) -> List[FreeAgent]:
    """Load an exported CVL graduating class as a free agent pool.

    The export file is a JSON list of PlayerCard dicts produced by
    Dynasty.export_graduating_class().
    """
    with open(filepath) as f:
        data = json.load(f)

    pool = []
    for d in data:
        card = PlayerCard.from_dict(d)
        # Convert college player to pro
        if card.age is None:
            card.age = 22  # default graduating age
        card.pro_status = "free_agent"
        card.contract_years = 0
        card.contract_salary = 0

        salary = max(1, min(5, card.overall // 20))
        pool.append(FreeAgent(
            player_card=card,
            asking_salary=salary,
            source="college_export",
        ))

    return pool


def generate_synthetic_fa_pool(
    count: int = 70,
    rng: Optional[random.Random] = None,
) -> List[FreeAgent]:
    """Generate synthetic free agents matching CVL graduate quality distributions.

    Used when no college dynasty export is available.
    """
    if rng is None:
        rng = random.Random()

    from scripts.generate_wvl_teams import (
        FIRST_NAMES, LAST_NAMES, POSITION_ARCHETYPES, ROSTER_TEMPLATE,
    )

    positions = [pos for pos, _ in ROSTER_TEMPLATE]
    countries = list(FIRST_NAMES.keys())

    pool = []
    for i in range(count):
        position = rng.choice(positions)
        country = rng.choice(countries)

        firsts = FIRST_NAMES.get(country, FIRST_NAMES["England"])
        lasts = LAST_NAMES.get(country, LAST_NAMES["England"])
        first_name = rng.choice(firsts)
        last_name = rng.choice(lasts)

        # Stats: CVL graduate quality (55-88 range, gaussian centered at 68)
        stats = {}
        for attr in ["speed", "stamina", "kicking", "lateral_skill", "tackling",
                     "agility", "power", "awareness", "hands", "kick_power", "kick_accuracy"]:
            val = int(rng.gauss(68, 10))
            stats[attr] = max(45, min(90, val))

        age = rng.choice([21, 22, 22, 22, 23, 23])
        archetype = rng.choice(POSITION_ARCHETYPES.get(position, ["balanced"]))
        potential = rng.choices([1, 2, 3, 4, 5], weights=[5, 15, 40, 30, 10])[0]

        card = PlayerCard(
            player_id=f"syn_{i:04d}",
            first_name=first_name,
            last_name=last_name,
            number=rng.randint(2, 99),
            position=position,
            archetype=archetype,
            nationality=country,
            hometown_city="",
            hometown_state="",
            hometown_country=country,
            high_school="",
            height=f"{rng.randint(5, 6)}-{rng.randint(0, 11)}",
            weight=rng.randint(140, 220),
            year="Rookie",
            potential=potential,
            development=rng.choice(["normal", "normal", "quick", "slow", "late_bloomer"]),
            age=age,
            pro_status="free_agent",
            **stats,
        )

        salary = max(1, min(5, card.overall // 20))
        pool.append(FreeAgent(
            player_card=card,
            asking_salary=salary,
            source="synthetic",
        ))

    return pool


# ═══════════════════════════════════════════════════════════════
# FREE AGENCY ATTRACTIVENESS
# ═══════════════════════════════════════════════════════════════

def compute_fa_attractiveness(
    tier: int,
    recent_wins: int,
    total_games: int,
    stadium_investment: float = 0.0,
    brand_investment: float = 0.0,
    prestige: int = 50,
) -> float:
    """Compute a 0-100 attractiveness score for a club in free agency.

    Higher score = more likely to attract top free agents.
    """
    # Tier bonus: tier 1 is most attractive
    tier_score = {1: 40, 2: 28, 3: 16, 4: 8}.get(tier, 10)

    # Win rate bonus (0-20)
    win_rate = recent_wins / max(1, total_games)
    win_score = win_rate * 20

    # Prestige bonus (0-15)
    prestige_score = prestige / 100 * 15

    # Investment bonuses (0-10 each)
    stadium_score = min(10, stadium_investment * 10)
    brand_score = min(10, brand_investment * 10)

    total = tier_score + win_score + prestige_score + stadium_score + brand_score
    return min(100, max(0, total))


# ═══════════════════════════════════════════════════════════════
# ROSTER NEEDS ANALYSIS
# ═══════════════════════════════════════════════════════════════

IDEAL_POSITION_COUNTS = {
    "Viper": 3, "Zeroback": 3, "Halfback": 4, "Wingback": 4,
    "Slotback": 4, "Keeper": 3, "Offensive Line": 8, "Defensive Line": 7,
}

def _compute_roster_needs(roster: List[PlayerCard]) -> Dict[str, int]:
    """Return position → deficit (positive = need more players)."""
    current = {}
    for p in roster:
        current[p.position] = current.get(p.position, 0) + 1

    needs = {}
    for pos, ideal in IDEAL_POSITION_COUNTS.items():
        deficit = ideal - current.get(pos, 0)
        if deficit > 0:
            needs[pos] = deficit
    return needs


# ═══════════════════════════════════════════════════════════════
# MAIN FREE AGENCY ENGINE
# ═══════════════════════════════════════════════════════════════

def run_free_agency(
    pool: List[FreeAgent],
    team_rosters: Dict[str, List[PlayerCard]],
    team_attractiveness: Dict[str, float],
    team_budgets: Dict[str, int],
    owner_club_key: Optional[str] = None,
    owner_targeted_fa_name: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> FreeAgencyResult:
    """Run the full free agency process for all teams.

    Args:
        pool: List of available free agents
        team_rosters: team_key → list of current PlayerCard objects
        team_attractiveness: team_key → 0-100 attractiveness score
        team_budgets: team_key → available salary budget (1-20)
        owner_club_key: the human owner's club key
        owner_targeted_fa_name: name of the one FA the owner wants to sign
        rng: random generator
    """
    if rng is None:
        rng = random.Random()

    result = FreeAgencyResult()
    available = list(pool)
    ROSTER_LIMIT = 36

    # Step 1: Owner's targeted FA signed first
    if owner_club_key and owner_targeted_fa_name:
        for fa in available:
            if fa.player_card.full_name == owner_targeted_fa_name:
                fa.player_card.pro_team = owner_club_key
                fa.player_card.pro_status = "active"
                fa.player_card.contract_years = 3
                fa.player_card.contract_salary = fa.asking_salary
                team_rosters.setdefault(owner_club_key, []).append(fa.player_card)
                signing = {
                    "player_name": fa.player_card.full_name,
                    "team_key": owner_club_key,
                    "salary": fa.asking_salary,
                    "source": fa.source,
                    "targeted": True,
                }
                result.owner_targeted_signing = signing
                result.signings.append(signing)
                available.remove(fa)
                break

    # Step 2: Sort remaining FAs by overall (best first)
    available.sort(key=lambda fa: -fa.overall)

    # Step 3: AI teams sign in rounds (best teams pick first each round)
    teams_sorted = sorted(
        team_attractiveness.keys(),
        key=lambda k: -team_attractiveness.get(k, 0),
    )

    # Multiple rounds of signing
    for _round in range(3):
        if not available:
            break

        for team_key in teams_sorted:
            if not available:
                break

            roster = team_rosters.get(team_key, [])
            if len(roster) >= ROSTER_LIMIT:
                continue

            budget = team_budgets.get(team_key, 5)
            needs = _compute_roster_needs(roster)
            attractiveness = team_attractiveness.get(team_key, 50)

            # Find best available player that fits needs and budget
            best_fa = None
            for fa in available:
                # Can they afford this player?
                if fa.asking_salary > budget:
                    continue

                # Attractiveness check: better players want better clubs
                if fa.overall > 80 and attractiveness < 30:
                    if rng.random() > 0.15:  # 85% chance top player rejects weak club
                        continue

                # Positional need bonus
                pos_need = needs.get(fa.player_card.position, 0)
                if pos_need > 0 or len(roster) < 33:
                    best_fa = fa
                    break

            if best_fa:
                best_fa.player_card.pro_team = team_key
                best_fa.player_card.pro_status = "active"
                best_fa.player_card.contract_years = rng.randint(1, 4)
                best_fa.player_card.contract_salary = best_fa.asking_salary
                team_rosters.setdefault(team_key, []).append(best_fa.player_card)

                result.signings.append({
                    "player_name": best_fa.player_card.full_name,
                    "team_key": team_key,
                    "salary": best_fa.asking_salary,
                    "source": best_fa.source,
                    "targeted": False,
                })
                available.remove(best_fa)

    # Remaining unsigned
    result.unsigned = [fa.player_card.full_name for fa in available]
    return result


# ═══════════════════════════════════════════════════════════════
# RETIREMENTS
# ═══════════════════════════════════════════════════════════════

def process_retirements(
    team_rosters: Dict[str, List[PlayerCard]],
    rng: Optional[random.Random] = None,
) -> List[Dict]:
    """Process retirements across all teams. Returns list of retirement records."""
    if rng is None:
        rng = random.Random()

    retirements = []
    for team_key, roster in team_rosters.items():
        remaining = []
        for card in roster:
            if should_retire(card, rng):
                retirements.append({
                    "player_name": card.full_name,
                    "team_key": team_key,
                    "age": card.age,
                    "overall": card.overall,
                    "position": card.position,
                })
                card.pro_status = "retired"
            else:
                remaining.append(card)
        team_rosters[team_key] = remaining

    return retirements


# ═══════════════════════════════════════════════════════════════
# ROSTER CUTS
# ═══════════════════════════════════════════════════════════════

def apply_roster_cuts(
    team_rosters: Dict[str, List[PlayerCard]],
    limit: int = 36,
) -> List[Dict]:
    """Cut rosters down to limit. Worst-overall players cut first."""
    cuts = []
    for team_key, roster in team_rosters.items():
        if len(roster) <= limit:
            continue
        roster.sort(key=lambda c: -c.overall)
        while len(roster) > limit:
            cut = roster.pop()
            cuts.append({
                "player_name": cut.full_name,
                "team_key": team_key,
                "overall": cut.overall,
            })
            cut.pro_status = "free_agent"
        team_rosters[team_key] = roster

    return cuts
