"""
Viperball NIL (Name, Image, Likeness) System

Manages NIL budgets, deals, and the financial side of recruiting/retention.

Key concepts:
- Each team has an annual NIL budget based on program prestige + market size.
- NIL money is allocated across three pools:
  1. **Recruiting** — used to attract high-school recruits.
  2. **Portal** — used to lure transfer portal players.
  3. **Retention** — used to keep current roster players happy.
- Deals are individual contracts with players/recruits.
- Budget overspend has consequences (reduced future budget, NCAA-style warnings).

The NIL system is intentionally abstracted — it doesn't simulate real tax law
or contract specifics, it just provides a resource-management layer that
makes recruiting feel consequential.

Usage:
    from engine.nil_system import NILProgram, generate_nil_budget

    budget = generate_nil_budget(prestige=75, market="large")
    program = NILProgram(team_name="Gonzaga", annual_budget=budget)
    program.allocate("recruiting", 400_000)
    program.allocate("portal", 200_000)
    program.allocate("retention", 100_000)

    program.make_deal("recruiting", recruit_id="REC-2027-0001", amount=50_000)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# BUDGET GENERATION
# ──────────────────────────────────────────────

# Market size tiers (affects base NIL budget)
MARKET_TIERS = {
    "small":    (300_000, 600_000),
    "medium":   (500_000, 1_000_000),
    "large":    (800_000, 1_500_000),
    "mega":     (1_200_000, 2_500_000),
}

# Prestige multiplier: prestige 0-100 maps to 0.5x - 1.5x
def _prestige_multiplier(prestige: int) -> float:
    return 0.5 + (prestige / 100.0)


def generate_nil_budget(
    prestige: int,
    market: str = "medium",
    previous_season_wins: int = 5,
    championship: bool = False,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Generate an annual NIL budget for a team.

    Args:
        prestige:             Program prestige 0-100.
        market:               Market size tier.
        previous_season_wins: Wins last season (more wins = more donor support).
        championship:         True if won championship last season.
        rng:                  Seeded Random.

    Returns:
        Annual NIL budget in dollars (int).
    """
    if rng is None:
        rng = random.Random()

    lo, hi = MARKET_TIERS.get(market, MARKET_TIERS["medium"])
    base = rng.randint(lo, hi)

    # Prestige multiplier
    base = int(base * _prestige_multiplier(prestige))

    # Win bonus: +$20k per win over .500
    if previous_season_wins > 5:
        base += (previous_season_wins - 5) * 20_000

    # Championship bonus
    if championship:
        base += 300_000

    # Add randomness (±10%)
    noise = rng.uniform(0.90, 1.10)
    return int(base * noise)


# ──────────────────────────────────────────────
# NIL DEAL
# ──────────────────────────────────────────────

@dataclass
class NILDeal:
    """A single NIL deal with a player or recruit."""
    deal_id: str
    player_id: str        # recruit_id or player_card.player_id
    player_name: str
    team_name: str
    pool: str             # "recruiting" | "portal" | "retention"
    amount: float         # dollar amount
    year: int             # year the deal was made
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "deal_id": self.deal_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team_name": self.team_name,
            "pool": self.pool,
            "amount": self.amount,
            "year": self.year,
            "active": self.active,
        }


# ──────────────────────────────────────────────
# NIL PROGRAM
# ──────────────────────────────────────────────

@dataclass
class NILProgram:
    """
    A team's NIL program for a single year.

    Manages budget allocation across recruiting, portal, and retention pools.
    Tracks individual deals and enforces budget limits.
    """
    team_name: str
    annual_budget: int

    # Pool allocations (set by user or auto)
    recruiting_pool: float = 0.0
    portal_pool: float = 0.0
    retention_pool: float = 0.0

    # Deals
    deals: List[NILDeal] = field(default_factory=list)
    _deal_counter: int = 0

    # Warnings
    overspend_warnings: int = 0

    @property
    def total_allocated(self) -> float:
        return self.recruiting_pool + self.portal_pool + self.retention_pool

    @property
    def unallocated(self) -> float:
        return max(0.0, self.annual_budget - self.total_allocated)

    @property
    def total_spent(self) -> float:
        return sum(d.amount for d in self.deals if d.active)

    @property
    def recruiting_spent(self) -> float:
        return sum(d.amount for d in self.deals if d.active and d.pool == "recruiting")

    @property
    def portal_spent(self) -> float:
        return sum(d.amount for d in self.deals if d.active and d.pool == "portal")

    @property
    def retention_spent(self) -> float:
        return sum(d.amount for d in self.deals if d.active and d.pool == "retention")

    @property
    def recruiting_remaining(self) -> float:
        return max(0.0, self.recruiting_pool - self.recruiting_spent)

    @property
    def portal_remaining(self) -> float:
        return max(0.0, self.portal_pool - self.portal_spent)

    @property
    def retention_remaining(self) -> float:
        return max(0.0, self.retention_pool - self.retention_spent)

    def allocate(self, pool: str, amount: float) -> bool:
        """
        Set the allocation for a pool.

        Returns False if total allocations would exceed annual budget.
        """
        other_pools = {
            "recruiting": self.portal_pool + self.retention_pool,
            "portal": self.recruiting_pool + self.retention_pool,
            "retention": self.recruiting_pool + self.portal_pool,
        }
        if pool not in other_pools:
            return False

        if amount + other_pools[pool] > self.annual_budget:
            return False

        if pool == "recruiting":
            self.recruiting_pool = amount
        elif pool == "portal":
            self.portal_pool = amount
        elif pool == "retention":
            self.retention_pool = amount
        return True

    def auto_allocate(self) -> None:
        """Auto-allocate budget across pools (default split)."""
        self.recruiting_pool = self.annual_budget * 0.50
        self.portal_pool = self.annual_budget * 0.30
        self.retention_pool = self.annual_budget * 0.20

    def make_deal(
        self,
        pool: str,
        player_id: str,
        player_name: str,
        amount: float,
        year: int = 0,
    ) -> Optional[NILDeal]:
        """
        Create an NIL deal from a specific pool.

        Returns the NILDeal if successful, None if over budget.
        """
        remaining = {
            "recruiting": self.recruiting_remaining,
            "portal": self.portal_remaining,
            "retention": self.retention_remaining,
        }.get(pool, 0.0)

        if amount > remaining:
            # Allow 10% overspend with a warning
            if amount <= remaining * 1.10 + 1000:
                self.overspend_warnings += 1
            else:
                return None

        self._deal_counter += 1
        deal = NILDeal(
            deal_id=f"NIL-{self.team_name[:3].upper()}-{self._deal_counter:04d}",
            player_id=player_id,
            player_name=player_name,
            team_name=self.team_name,
            pool=pool,
            amount=amount,
            year=year,
        )
        self.deals.append(deal)
        return deal

    def cancel_deal(self, deal_id: str) -> bool:
        """Cancel an active deal, freeing the budget."""
        for deal in self.deals:
            if deal.deal_id == deal_id and deal.active:
                deal.active = False
                return True
        return False

    def get_deal_summary(self) -> dict:
        """Financial summary of the NIL program."""
        return {
            "team": self.team_name,
            "annual_budget": self.annual_budget,
            "recruiting_pool": self.recruiting_pool,
            "portal_pool": self.portal_pool,
            "retention_pool": self.retention_pool,
            "total_spent": self.total_spent,
            "recruiting_spent": self.recruiting_spent,
            "portal_spent": self.portal_spent,
            "retention_spent": self.retention_spent,
            "recruiting_remaining": self.recruiting_remaining,
            "portal_remaining": self.portal_remaining,
            "retention_remaining": self.retention_remaining,
            "active_deals": len([d for d in self.deals if d.active]),
            "overspend_warnings": self.overspend_warnings,
        }

    def to_dict(self) -> dict:
        return {
            "team_name": self.team_name,
            "annual_budget": self.annual_budget,
            "recruiting_pool": self.recruiting_pool,
            "portal_pool": self.portal_pool,
            "retention_pool": self.retention_pool,
            "deals": [d.to_dict() for d in self.deals],
            "overspend_warnings": self.overspend_warnings,
        }


# ──────────────────────────────────────────────
# RETENTION RISK
# ──────────────────────────────────────────────

@dataclass
class RetentionRisk:
    """Tracks which current roster players might leave without NIL retention."""
    player_id: str
    player_name: str
    position: str
    overall: int
    potential: int
    risk_level: str       # "low" | "medium" | "high"
    suggested_amount: float

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "overall": self.overall,
            "potential": self.potential,
            "risk_level": self.risk_level,
            "suggested_amount": self.suggested_amount,
        }


def assess_retention_risks(
    roster: list,
    team_prestige: int,
    team_wins: int,
    rng: Optional[random.Random] = None,
    retention_boost: float = 0.0,
) -> List[RetentionRisk]:
    """
    Assess which roster players are at risk of entering the portal
    and suggest NIL retention amounts.

    Args:
        roster:           List of PlayerCard objects.
        team_prestige:    0-100 prestige.
        team_wins:        Wins last season.
        rng:              Seeded Random.
        retention_boost:  DraftyQueenz retention donation bonus (0-20).
                          Directly reduces risk scores, making players less likely to leave.

    Returns:
        List of RetentionRisk objects for at-risk players.
    """
    if rng is None:
        rng = random.Random()

    risks: List[RetentionRisk] = []

    for card in roster:
        if card.year in ("Freshman", "Graduate"):
            continue

        risk_score = 0.0

        if card.overall >= 82:
            risk_score += 25.0
        elif card.overall >= 75:
            risk_score += 15.0

        if card.potential >= 4:
            risk_score += 20.0
        elif card.potential >= 3:
            risk_score += 10.0

        if team_prestige < 40:
            risk_score += 15.0
        elif team_prestige < 60:
            risk_score += 8.0

        if team_wins < 4:
            risk_score += 12.0
        elif team_wins < 6:
            risk_score += 5.0

        if getattr(card, 'redshirt_used', False) or getattr(card, 'redshirt', False):
            risk_score += 15.0

        risk_score += rng.uniform(-5, 10)

        risk_score -= retention_boost

        # Classify risk
        if risk_score >= 35:
            risk_level = "high"
            suggested = 40_000 + card.overall * 500
        elif risk_score >= 20:
            risk_level = "medium"
            suggested = 15_000 + card.overall * 200
        else:
            continue  # low risk — don't surface

        risks.append(RetentionRisk(
            player_id=card.player_id,
            player_name=card.full_name,
            position=card.position,
            overall=card.overall,
            potential=card.potential,
            risk_level=risk_level,
            suggested_amount=suggested,
        ))

    risks.sort(key=lambda r: (0 if r.risk_level == "high" else 1, -r.overall))
    return risks


# ──────────────────────────────────────────────
# AUTO NIL (CPU TEAMS)
# ──────────────────────────────────────────────

def auto_nil_program(
    team_name: str,
    prestige: int,
    market: str = "medium",
    previous_wins: int = 5,
    championship: bool = False,
    rng: Optional[random.Random] = None,
) -> NILProgram:
    """
    Generate and auto-allocate an NIL program for a CPU team.

    Returns a ready-to-use NILProgram with default allocation.
    """
    if rng is None:
        rng = random.Random()

    budget = generate_nil_budget(
        prestige=prestige,
        market=market,
        previous_season_wins=previous_wins,
        championship=championship,
        rng=rng,
    )
    program = NILProgram(team_name=team_name, annual_budget=budget)
    program.auto_allocate()
    return program


# ──────────────────────────────────────────────
# MARKET SIZE ESTIMATION
# ──────────────────────────────────────────────

# Rough market tier by state (used if no explicit mapping exists)
_STATE_MARKET = {
    "CA": "mega", "TX": "mega", "NY": "mega", "FL": "large",
    "IL": "large", "PA": "large", "OH": "large", "GA": "large",
    "NC": "large", "VA": "large", "NJ": "large", "WA": "large",
    "MA": "large", "MI": "large",
    "TN": "medium", "MO": "medium", "MD": "medium", "WI": "medium",
    "MN": "medium", "IN": "medium", "CO": "medium", "AZ": "medium",
    "OR": "medium", "CT": "medium", "SC": "medium", "LA": "medium",
    "KY": "medium", "AL": "medium",
}


def estimate_market_tier(state: str) -> str:
    """Estimate a team's market tier from its state."""
    return _STATE_MARKET.get(state, "small")


def compute_team_prestige(
    all_time_wins: int,
    all_time_losses: int,
    championships: int,
    recent_wins: int = 5,
) -> int:
    """
    Compute a team's prestige rating (0-100).

    Based on historical record + championships + recent performance.
    """
    total = all_time_wins + all_time_losses
    if total == 0:
        return 50  # new program, average prestige

    win_pct = all_time_wins / total

    # Base: win percentage (0-50 points)
    base = win_pct * 50

    # Championships (up to 30 points)
    champ_pts = min(30, championships * 8)

    # Recent performance (up to 20 points)
    recent_pts = min(20, recent_wins * 2)

    prestige = int(base + champ_pts + recent_pts)
    return max(10, min(99, prestige))
