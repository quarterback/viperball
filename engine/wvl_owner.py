"""
WVL Owner Mode Engine
======================

The human plays as a club owner with 4 levers:
1. Owner Archetype — personality, bankroll, patience
2. President Archetype — hire/fire, impacts coaching (not players)
3. One Targeted Free Agent — owner picks one FA per offseason
4. Investment Areas — marginal temporary boosts to players/club

All other operations (free agency, coaching, lineups) are AI-driven.
"""

import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# OWNER ARCHETYPES
# ═══════════════════════════════════════════════════════════════

OWNER_ARCHETYPES = {
    "sugar_daddy": {
        "label": "Sugar Daddy",
        "description": "Large bankroll, willing to overspend, impatient for results.",
        "starting_bankroll": 80,
        "patience_threshold": 2,    # seasons of losing before pressure mounts
        "fa_reputation_mod": 1.15,  # 15% boost to free agency attractiveness
        "investment_bonus": 1.1,    # 10% more effective investments
    },
    "patient_builder": {
        "label": "Patient Builder",
        "description": "Moderate budget, long-term vision, tolerates losing seasons.",
        "starting_bankroll": 50,
        "patience_threshold": 5,
        "fa_reputation_mod": 1.0,
        "investment_bonus": 1.05,
    },
    "youth_evangelist": {
        "label": "Youth Evangelist",
        "description": "Prefers signing young free agents, invests in training facilities.",
        "starting_bankroll": 45,
        "patience_threshold": 4,
        "fa_reputation_mod": 1.05,
        "investment_bonus": 1.2,   # Youth academy / training investments 20% more effective
    },
    "trophy_hunter": {
        "label": "Trophy Hunter",
        "description": "Throws money at star free agents, neglects infrastructure.",
        "starting_bankroll": 70,
        "patience_threshold": 2,
        "fa_reputation_mod": 1.2,
        "investment_bonus": 0.8,   # Infrastructure investments less effective
    },
    "hometown_hero": {
        "label": "Hometown Hero",
        "description": "Local owner, fan loyalty bonus, moderate budget.",
        "starting_bankroll": 40,
        "patience_threshold": 4,
        "fa_reputation_mod": 1.0,
        "investment_bonus": 1.0,
    },
    "corporate_group": {
        "label": "Corporate Group",
        "description": "Deep pockets but expects ROI. Will sell if not profitable.",
        "starting_bankroll": 65,
        "patience_threshold": 3,
        "fa_reputation_mod": 1.1,
        "investment_bonus": 1.0,
    },
    "underdog_dreamer": {
        "label": "Underdog Dreamer",
        "description": "Small bankroll, relies on smart president and scrappy signings.",
        "starting_bankroll": 25,
        "patience_threshold": 6,   # Very patient
        "fa_reputation_mod": 0.9,
        "investment_bonus": 1.0,
    },
}


# ═══════════════════════════════════════════════════════════════
# PRESIDENT ARCHETYPES
# ═══════════════════════════════════════════════════════════════

PRESIDENT_ARCHETYPES = {
    "old_guard": {
        "label": "Old Guard",
        "description": "Hires experienced coaches, conservative strategy, budget-conscious.",
        "acumen_range": (60, 80),
        "budget_mgmt_range": (70, 90),
        "recruiting_eye_range": (50, 70),
        "staff_hiring_range": (60, 80),
        "salary_range": (3, 6),
        "coaching_style_bias": ["ball_control", "ground_pound", "chain_gang"],
    },
    "innovator": {
        "label": "Innovator",
        "description": "Hires young coaches, experimental formations, higher variance.",
        "acumen_range": (55, 85),
        "budget_mgmt_range": (40, 70),
        "recruiting_eye_range": (60, 85),
        "staff_hiring_range": (55, 80),
        "salary_range": (4, 8),
        "coaching_style_bias": ["ghost", "lateral_spread", "shock_and_awe"],
    },
    "moneyball": {
        "label": "Moneyball",
        "description": "Analytics-driven, finds undervalued players, efficient spending.",
        "acumen_range": (70, 90),
        "budget_mgmt_range": (80, 95),
        "recruiting_eye_range": (75, 95),
        "staff_hiring_range": (65, 85),
        "salary_range": (3, 5),
        "coaching_style_bias": ["balanced", "east_coast", "ball_control"],
    },
    "big_spender": {
        "label": "Big Spender",
        "description": "Overpays for name-brand coaches, flashy but wasteful.",
        "acumen_range": (50, 75),
        "budget_mgmt_range": (25, 50),
        "recruiting_eye_range": (55, 75),
        "staff_hiring_range": (60, 85),
        "salary_range": (6, 10),
        "coaching_style_bias": ["shock_and_awe", "stampede", "boot_raid"],
    },
    "developer": {
        "label": "Developer",
        "description": "Promotes from within, builds coaching trees, slow but steady.",
        "acumen_range": (60, 80),
        "budget_mgmt_range": (65, 85),
        "recruiting_eye_range": (65, 85),
        "staff_hiring_range": (70, 90),
        "salary_range": (3, 6),
        "coaching_style_bias": ["ball_control", "chain_gang", "balanced"],
    },
    "dealmaker": {
        "label": "Dealmaker",
        "description": "Great at negotiations, discount signings, unpredictable strategy.",
        "acumen_range": (55, 80),
        "budget_mgmt_range": (75, 90),
        "recruiting_eye_range": (60, 80),
        "staff_hiring_range": (50, 75),
        "salary_range": (3, 5),
        "coaching_style_bias": ["slick_n_slide", "ghost", "lateral_spread"],
    },
}


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ClubOwner:
    """The human's owner profile."""
    name: str
    archetype: str
    club_key: str
    bankroll: float                              # current bankroll in millions
    investment_history: List[Dict] = field(default_factory=list)
    seasons_owned: int = 0
    consecutive_bad_seasons: int = 0             # for patience tracking

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ClubOwner":
        return cls(**d)


@dataclass
class TeamPresident:
    """AI-controlled team president."""
    name: str
    archetype: str
    acumen: int           # football IQ
    budget_mgmt: int      # how well they manage money
    recruiting_eye: int   # ability to identify talent
    staff_hiring: int     # ability to hire good coaches
    salary: int           # annual cost in millions
    contract_years: int
    years_served: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TeamPresident":
        return cls(**d)


@dataclass
class InvestmentAllocation:
    """Owner's annual investment allocation (fractions that sum to 1.0)."""
    training: float = 0.0       # Training Facilities → physical attrs
    coaching: float = 0.0       # Coaching Staff Budget → mental attrs
    stadium: float = 0.0        # Stadium Upgrade → FA attractiveness + attendance
    youth: float = 0.0          # Youth Academy → young player development
    science: float = 0.0        # Sports Science → injury + fatigue
    marketing: float = 0.0      # Marketing/Brand → FA attractiveness + attendance + prestige

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "InvestmentAllocation":
        return cls(**{k: d.get(k, 0.0) for k in cls.__dataclass_fields__})

    @property
    def total(self) -> float:
        return self.training + self.coaching + self.stadium + self.youth + self.science + self.marketing


@dataclass
class ClubFinancials:
    """Financial summary for one season."""
    year: int
    tier: int
    revenue: float = 0.0
    expenses: float = 0.0
    investment_spend: float = 0.0
    net_income: float = 0.0
    attendance_avg: int = 0
    bankroll_start: float = 0.0
    bankroll_end: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ClubFinancials":
        return cls(**d)


# ═══════════════════════════════════════════════════════════════
# PRESIDENT GENERATION
# ═══════════════════════════════════════════════════════════════

_PRESIDENT_FIRST_NAMES = [
    "Alexandra", "Victoria", "Catherine", "Margaret", "Helena", "Diana",
    "Isabella", "Sophia", "Natalia", "Johanna", "Beatrice", "Clara",
    "Valentina", "Marina", "Ekaterina", "Helga", "Fiona", "Ingrid",
    "Ayumi", "Fatima", "Amara", "Lena", "Nadia", "Olga",
]

_PRESIDENT_LAST_NAMES = [
    "Sterling", "Blackwood", "Montague", "Ashworth", "Cavendish", "Thornton",
    "Beaumont", "Lancaster", "Hartwell", "Whitfield", "Crawford", "Pembroke",
    "Westbrook", "Aldridge", "Fairbanks", "Harrington", "Lockwood", "Prescott",
    "Northcott", "Caldwell", "Ainsworth", "Stratton", "Wentworth", "Dalton",
]


def generate_president_pool(
    count: int = 5,
    rng: Optional[random.Random] = None,
) -> List[TeamPresident]:
    """Generate a pool of available presidents to hire."""
    if rng is None:
        rng = random.Random()

    pool = []
    archetypes = list(PRESIDENT_ARCHETYPES.keys())

    for i in range(count):
        archetype_key = rng.choice(archetypes)
        arch = PRESIDENT_ARCHETYPES[archetype_key]

        first = rng.choice(_PRESIDENT_FIRST_NAMES)
        last = rng.choice(_PRESIDENT_LAST_NAMES)

        pool.append(TeamPresident(
            name=f"{first} {last}",
            archetype=archetype_key,
            acumen=rng.randint(*arch["acumen_range"]),
            budget_mgmt=rng.randint(*arch["budget_mgmt_range"]),
            recruiting_eye=rng.randint(*arch["recruiting_eye_range"]),
            staff_hiring=rng.randint(*arch["staff_hiring_range"]),
            salary=rng.randint(*arch["salary_range"]),
            contract_years=rng.randint(2, 5),
        ))

    return pool


# ═══════════════════════════════════════════════════════════════
# INVESTMENT BOOSTS
# ═══════════════════════════════════════════════════════════════

def apply_investment_boosts(
    roster: list,
    allocation: InvestmentAllocation,
    investment_budget: float,
    owner_archetype: str,
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """Apply temporary annual boosts to roster based on investment allocation.

    Returns dict of {attr_name: total_boost_applied} for reporting.
    """
    if rng is None:
        rng = random.Random()

    arch = OWNER_ARCHETYPES.get(owner_archetype, {})
    bonus_mult = arch.get("investment_bonus", 1.0)

    # Budget effectiveness: more money = stronger boosts (diminishing returns)
    budget_factor = min(2.0, investment_budget / 10.0) * bonus_mult
    boosts_applied = {}

    for card in roster:
        # Training Facilities → physical attrs
        if allocation.training > 0.05:
            boost = int(allocation.training * budget_factor * rng.uniform(1, 3))
            boost = max(0, min(3, boost))
            for attr in ["speed", "stamina", "agility"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Coaching Staff Budget → mental attrs
        if allocation.coaching > 0.05:
            boost = int(allocation.coaching * budget_factor * rng.uniform(1, 3))
            boost = max(0, min(3, boost))
            for attr in ["awareness", "tackling"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Youth Academy → development speed for young players
        if allocation.youth > 0.05 and getattr(card, "age", 30) and card.age is not None and card.age < 25:
            boost = int(allocation.youth * budget_factor * rng.uniform(1, 4))
            boost = max(0, min(4, boost))
            for attr in ["speed", "agility", "lateral_skill", "hands"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Sports Science → minor injury resilience (modeled as stamina + power boost)
        if allocation.science > 0.05:
            boost = int(allocation.science * budget_factor * rng.uniform(0.5, 2))
            boost = max(0, min(2, boost))
            for attr in ["stamina", "power"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

    return boosts_applied


# ═══════════════════════════════════════════════════════════════
# FINANCIALS
# ═══════════════════════════════════════════════════════════════

# Revenue by tier (base, in millions)
_TIER_BASE_REVENUE = {1: 20.0, 2: 12.0, 3: 7.0, 4: 4.0}


def compute_season_revenue(
    tier: int,
    wins: int,
    losses: int,
    playoff_result: str = "none",  # "none" | "made_playoffs" | "finalist" | "champion"
    stadium_investment: float = 0.0,
    brand_investment: float = 0.0,
) -> float:
    """Compute season revenue in millions."""
    base = _TIER_BASE_REVENUE.get(tier, 5.0)

    # Win bonus: ~0.3M per win
    total_games = max(1, wins + losses)
    win_rate = wins / total_games
    win_bonus = win_rate * 8.0

    # Playoff bonus
    playoff_bonus = {
        "none": 0.0,
        "made_playoffs": 3.0,
        "finalist": 6.0,
        "champion": 12.0,
    }.get(playoff_result, 0.0)

    # Investment bonuses
    stadium_bonus = stadium_investment * 4.0
    brand_bonus = brand_investment * 3.0

    return round(base + win_bonus + playoff_bonus + stadium_bonus + brand_bonus, 2)


def compute_season_expenses(
    roster_salary_total: int,
    president_salary: int,
    investment_spend: float,
) -> float:
    """Compute season expenses in millions."""
    # Roster cost: each salary tier ~1.5M
    roster_cost = roster_salary_total * 0.15

    # President cost
    pres_cost = president_salary * 1.0

    # Base operating costs
    base_ops = 5.0

    return round(roster_cost + pres_cost + base_ops + investment_spend, 2)


def compute_financials(
    year: int,
    tier: int,
    wins: int,
    losses: int,
    playoff_result: str,
    roster: list,
    president: TeamPresident,
    investment: InvestmentAllocation,
    investment_budget: float,
    bankroll_start: float,
) -> ClubFinancials:
    """Compute complete financial summary for one season."""
    # Revenue
    revenue = compute_season_revenue(
        tier=tier,
        wins=wins,
        losses=losses,
        playoff_result=playoff_result,
        stadium_investment=investment.stadium,
        brand_investment=investment.marketing,
    )

    # Expenses
    roster_salary_total = sum(
        getattr(c, "contract_salary", 1) or 1 for c in roster
    )
    expenses = compute_season_expenses(
        roster_salary_total=roster_salary_total,
        president_salary=president.salary,
        investment_spend=investment_budget,
    )

    net = revenue - expenses
    bankroll_end = bankroll_start + net

    return ClubFinancials(
        year=year,
        tier=tier,
        revenue=revenue,
        expenses=expenses,
        investment_spend=investment_budget,
        net_income=net,
        attendance_avg=int(10000 + (100 - tier * 15) * 200 + wins * 500),
        bankroll_start=bankroll_start,
        bankroll_end=bankroll_end,
    )


# ═══════════════════════════════════════════════════════════════
# AI PRESIDENT DECISIONS
# ═══════════════════════════════════════════════════════════════

def president_set_team_style(
    president: TeamPresident,
    rng: Optional[random.Random] = None,
) -> Dict[str, str]:
    """AI president picks offense/defense style based on their archetype bias."""
    if rng is None:
        rng = random.Random()

    arch = PRESIDENT_ARCHETYPES.get(president.archetype, PRESIDENT_ARCHETYPES["old_guard"])
    style_bias = arch.get("coaching_style_bias", ["balanced"])

    offense = rng.choice(style_bias)

    # Defense: somewhat independent of archetype
    defenses = ["swarm", "blitz_pack", "shadow", "fortress", "predator", "drift", "chaos", "lockdown"]
    defense = rng.choice(defenses)

    st_schemes = ["iron_curtain", "lightning_returns", "block_party", "chaos_unit", "aces"]
    st = rng.choice(st_schemes)

    return {
        "offense_style": offense,
        "defense_style": defense,
        "st_scheme": st,
    }
