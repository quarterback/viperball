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
from statistics import mean
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
# AI OWNER BEHAVIOR PROFILES
# ═══════════════════════════════════════════════════════════════

AI_OWNER_PROFILES = {
    "aggressive": {
        "label": "Aggressive Investor",
        "description": "Heavy payroll spending, frequent roster turnover, risk of instability.",
        "spending_ratio": 0.80,
        "patience": 2,
        "infra_weight": 0.5,
    },
    "balanced": {
        "label": "Balanced Owner",
        "description": "Moderate spend, stable finances, middling growth.",
        "spending_ratio": 0.60,
        "patience": 3,
        "infra_weight": 0.6,
    },
    "frugal": {
        "label": "Frugal Owner",
        "description": "Rarely signs expensive players, large cash reserves, rarely elite.",
        "spending_ratio": 0.40,
        "patience": 5,
        "infra_weight": 0.5,
    },
    "builder": {
        "label": "Builder",
        "description": "Heavy academy investment, slower rise, strong long-term performance.",
        "spending_ratio": 0.55,
        "patience": 5,
        "infra_weight": 0.9,
    },
    "vanity": {
        "label": "Vanity Project",
        "description": "Extremely high payroll, debt accumulation, boom-bust cycles.",
        "spending_ratio": 0.90,
        "patience": 1,
        "infra_weight": 0.3,
    },
}


def assign_ai_owner_profile(prestige: int, rng: Optional[random.Random] = None) -> str:
    """Assign an AI owner profile key based on club prestige."""
    if rng is None:
        rng = random.Random()
    if prestige >= 80:
        return rng.choice(["aggressive", "aggressive", "vanity", "balanced"])
    elif prestige >= 60:
        return rng.choice(["balanced", "aggressive", "balanced", "frugal"])
    elif prestige >= 40:
        return rng.choice(["balanced", "frugal", "builder", "frugal"])
    else:
        return rng.choice(["frugal", "builder", "builder", "frugal"])


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
class ClubLoan:
    """A loan taken against the club's future revenue."""
    amount: float           # principal in millions
    interest_rate: float    # annual rate, e.g. 0.08
    annual_payment: float   # fixed annual repayment in millions
    years_remaining: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ClubLoan":
        return cls(**d)


@dataclass
class ClubFinancials:
    """Financial summary for one season."""
    year: int
    tier: int
    # Revenue streams
    total_revenue: float = 0.0
    ticket_revenue: float = 0.0
    broadcast_revenue: float = 0.0
    sponsorship_revenue: float = 0.0
    merchandise_revenue: float = 0.0
    prize_money: float = 0.0
    # Expenses
    total_expenses: float = 0.0
    roster_cost: float = 0.0
    president_cost: float = 0.0
    base_ops_cost: float = 0.0
    investment_spend: float = 0.0
    loan_payments: float = 0.0
    infra_maintenance: float = 0.0
    # Summary
    net_income: float = 0.0
    attendance_avg: int = 0
    fanbase_end: int = 0
    bankroll_start: float = 0.0
    bankroll_end: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ClubFinancials":
        # Backward-compat: old saves used "revenue"/"expenses" keys
        if "revenue" in d and "total_revenue" not in d:
            d = dict(d)
            d["total_revenue"] = d.pop("revenue")
        if "expenses" in d and "total_expenses" not in d:
            d = dict(d)
            d["total_expenses"] = d.pop("expenses")
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: d[k] for k in known if k in d})


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

def apply_infrastructure_effects(team, infra):
    """
    Modify team attributes based on infrastructure levels.
    """

    # Training → player development multiplier
    team.dev_multiplier = 1.0 + (infra.get("training", 1.0) * 0.02)

    # Medical → injury probability reduction
    team.injury_modifier = max(0.6, 1.0 - infra.get("science", 1.0) * 0.03)

    # Scouting → free agent discovery bonus
    team.fa_quality_bonus = infra.get("scouting", 0.0) * 0.05

    # Youth → academy prospect rating boost
    team.youth_rating_bonus = infra.get("youth", 1.0) * 1.5

    # Marketing → fanbase growth multiplier
    team.fan_growth_multiplier = 1.0 + infra.get("marketing", 1.0) * 0.03

    # Stadium → attendance multiplier
    team.attendance_multiplier = 1.0 + infra.get("stadium", 1.0) * 0.02


def apply_investment_boosts(
    roster: list,
    allocation: InvestmentAllocation,
    investment_budget: float,
    owner_archetype: str,
    rng: Optional[random.Random] = None,
    infrastructure: Optional[Dict[str, float]] = None,
) -> Dict[str, int]:
    """Apply temporary annual boosts to roster based on investment allocation.

    Returns dict of {attr_name: total_boost_applied} for reporting.
    infra dict (optional) scales youth academy boosts by accumulated level.
    """
    if rng is None:
        rng = random.Random()
    if infrastructure is None:
        infrastructure = {}

    arch = OWNER_ARCHETYPES.get(owner_archetype, {})
    bonus_mult = arch.get("investment_bonus", 1.0)

    # Budget effectiveness: more money = stronger boosts (diminishing returns)
    budget_factor = min(2.5, investment_budget / 8.0) * bonus_mult
    boosts_applied = {}

    # Infrastructure multipliers: level 1–10 gives 1.0–2.0x for each category
    training_infra_mult = 1.0 + infrastructure.get("training", 1.0) / 10.0
    coaching_infra_mult = 1.0 + infrastructure.get("coaching", 1.0) / 10.0
    youth_infra_mult = 1.0 + infrastructure.get("youth", 1.0) / 10.0
    science_infra_mult = 1.0 + infrastructure.get("science", 1.0) / 10.0

    for card in roster:
        # Training Facilities → physical attrs (infra-scaled)
        if allocation.training > 0.05:
            raw = allocation.training * budget_factor * rng.uniform(1, 3) * training_infra_mult
            boost = max(0, min(5, int(raw)))
            for attr in ["speed", "stamina", "agility"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Coaching Staff Budget → mental attrs (infra-scaled)
        if allocation.coaching > 0.05:
            raw = allocation.coaching * budget_factor * rng.uniform(1, 3) * coaching_infra_mult
            boost = max(0, min(5, int(raw)))
            for attr in ["awareness", "tackling"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Youth Academy → development speed for young players (infra-scaled)
        if allocation.youth > 0.05 and getattr(card, "age", 30) and card.age is not None and card.age < 25:
            raw_boost = allocation.youth * budget_factor * rng.uniform(1, 5) * youth_infra_mult
            boost = max(0, min(7, int(raw_boost)))
            for attr in ["speed", "agility", "lateral_skill", "hands"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

        # Sports Science → injury resilience (infra-scaled)
        if allocation.science > 0.05:
            raw = allocation.science * budget_factor * rng.uniform(0.5, 2.5) * science_infra_mult
            boost = max(0, min(3, int(raw)))
            for attr in ["stamina", "power"]:
                old = getattr(card, attr)
                new = min(99, old + boost)
                if new != old:
                    setattr(card, attr, new)
                    boosts_applied[attr] = boosts_applied.get(attr, 0) + (new - old)

    return boosts_applied


# ═══════════════════════════════════════════════════════════════
# FANBASE MODEL
# ═══════════════════════════════════════════════════════════════

# Starting fanbase by tier; prestige scales within ±50%
_TIER_STARTING_FANBASE = {1: 60_000, 2: 28_000, 3: 12_000, 4: 5_000}

# Broadcast revenue by tier (millions) — largest fixed revenue driver
_BROADCAST_REVENUE = {1: 12.0, 2: 6.0, 3: 3.0, 4: 1.0}


def starting_fanbase(tier: int, prestige: int) -> int:
    """Compute a club's starting fanbase from tier and prestige (0–99)."""
    base = _TIER_STARTING_FANBASE.get(tier, 5_000)
    scale = 0.5 + prestige / 100.0   # 0.5× at prestige 0, 1.5× at prestige 100
    return max(1_000, round(base * scale))


def compute_fanbase_update(
    fanbase: float,
    wins: int,
    total_games: int,
    promoted: bool,
    relegated: bool,
    marketing_fraction: float,
) -> int:
    """Compute new fanbase after one season.

    Args:
        fanbase: Current fanbase size.
        wins: Season wins.
        total_games: Total games played.
        promoted: True if team was promoted this offseason.
        relegated: True if team was relegated this offseason.
        marketing_fraction: InvestmentAllocation.marketing value (0.0–1.0).

    Returns:
        New fanbase (integer, minimum 1000).
    """
    win_rate = wins / max(1, total_games)

    if win_rate > 0.55:
        perf_delta = 0.05 * fanbase
    elif win_rate < 0.40:
        perf_delta = -0.03 * fanbase
    else:
        perf_delta = 0.0

    marketing_growth = min(0.08, marketing_fraction * 2.0) * fanbase
    promotion_bonus = 0.15 * fanbase if promoted else 0.0
    relegation_loss = -0.20 * fanbase if relegated else 0.0

    new_fanbase = fanbase + perf_delta + marketing_growth + promotion_bonus + relegation_loss
    return max(1_000, round(new_fanbase))


# ═══════════════════════════════════════════════════════════════
# EXPANDED REVENUE STREAMS
# ═══════════════════════════════════════════════════════════════

_HOME_GAMES = {1: 17, 2: 19, 3: 12, 4: 12}
_TICKET_PRICE = {1: 45, 2: 35, 3: 25, 4: 18}       # dollars per seat
_SPONSOR_TIER_MULT = {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}


def compute_ticket_revenue(
    fanbase: float,
    tier: int,
    wins: int,
    total_games: int,
    stadium_fraction: float = 0.0,
) -> float:
    """Ticket revenue driven by fanbase, performance, and stadium investment."""
    home_games = _HOME_GAMES.get(tier, 12)
    ticket_price = _TICKET_PRICE.get(tier, 20)
    attendance_rate = 0.55 + (wins / max(1, total_games)) * 0.35
    # Stadium investment expands effective capacity slightly
    stadium_cap = fanbase * (1.0 + stadium_fraction * 0.5)
    effective_fans = min(fanbase, stadium_cap)
    return round(attendance_rate * effective_fans * ticket_price * home_games / 1_000_000, 2)


def compute_broadcast_revenue(tier: int) -> float:
    """Fixed broadcast rights deal by tier."""
    return _BROADCAST_REVENUE.get(tier, 1.0)


def compute_sponsorship_revenue(
    fanbase: float,
    marketing_fraction: float,
    tier: int,
) -> float:
    """Sponsorship driven by fanbase reach and marketing investment."""
    tier_mult = _SPONSOR_TIER_MULT.get(tier, 0.5)
    return round((fanbase / 50_000) * tier_mult * (0.8 + marketing_fraction * 0.4), 2)


def compute_merchandise_revenue(fanbase: float, marketing_fraction: float) -> float:
    """Merchandise revenue scales with fanbase and marketing."""
    merch_per_fan = 12 * (1.0 + marketing_fraction * 0.5)   # $12–18 per fan
    return round(fanbase * merch_per_fan / 1_000_000, 2)


def compute_prize_money(playoff_result: str, tier: int) -> float:
    """Prize money based on final league position."""
    base = {1: 10.0, 2: 5.0, 3: 2.5, 4: 1.0}.get(tier, 1.0)
    mult = {
        "champion": 1.0,
        "finalist": 0.5,
        "made_playoffs": 0.3,
        "none": 0.1,
    }.get(playoff_result, 0.1)
    return round(base * mult, 2)


# ═══════════════════════════════════════════════════════════════
# DEBT HELPERS
# ═══════════════════════════════════════════════════════════════

def compute_loan_payment(amount: float, rate: float, years: int) -> float:
    """Compute the fixed annual payment for a loan (annuity formula)."""
    if rate == 0 or years <= 0:
        return round(amount / max(1, years), 2)
    payment = amount * rate / (1 - (1 + rate) ** (-years))
    return round(payment, 2)


# ═══════════════════════════════════════════════════════════════
# FINANCIALS
# ═══════════════════════════════════════════════════════════════

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
    fanbase: float = 0.0,
    loan_payments: float = 0.0,
    infrastructure: Optional[Dict] = None,
) -> ClubFinancials:
    """Compute complete financial summary for one season."""
    total_games = wins + losses

    # Revenue streams
    ticket  = compute_ticket_revenue(fanbase, tier, wins, total_games, investment.stadium)
    bcast   = compute_broadcast_revenue(tier)
    sponsor = compute_sponsorship_revenue(fanbase, investment.marketing, tier)
    merch   = compute_merchandise_revenue(fanbase, investment.marketing)
    prize   = compute_prize_money(playoff_result, tier)
    total_rev = round(ticket + bcast + sponsor + merch + prize, 2)

    # Infrastructure maintenance: ₯0.5M per infra level across all categories
    infra_levels = infrastructure or {}
    infra_maintenance = round(sum(infra_levels.values()) * 0.5, 2) if infra_levels else 0.0

    # Expense breakdown
    roster_salary_total = sum(getattr(c, "contract_salary", 1) or 1 for c in roster)
    r_cost   = round(roster_salary_total * 0.15, 2)
    p_cost   = float(president.salary)
    ops_cost = 5.0
    total_exp = round(r_cost + p_cost + ops_cost + investment_budget + loan_payments + infra_maintenance, 2)

    net = round(total_rev - total_exp, 2)
    bankroll_end = round(bankroll_start + net, 2)

    attendance = int(
        (0.55 + (wins / max(1, total_games)) * 0.35)
        * min(fanbase, fanbase * (1 + investment.stadium * 0.5))
    )

    return ClubFinancials(
        year=year,
        tier=tier,
        total_revenue=total_rev,
        ticket_revenue=ticket,
        broadcast_revenue=bcast,
        sponsorship_revenue=sponsor,
        merchandise_revenue=merch,
        prize_money=prize,
        total_expenses=total_exp,
        roster_cost=r_cost,
        president_cost=p_cost,
        base_ops_cost=ops_cost,
        investment_spend=investment_budget,
        loan_payments=loan_payments,
        infra_maintenance=infra_maintenance,
        net_income=net,
        attendance_avg=attendance,
        fanbase_end=int(fanbase),
        bankroll_start=bankroll_start,
        bankroll_end=bankroll_end,
    )


# ═══════════════════════════════════════════════════════════════
# INVESTMENT MODIFIERS (in-season dice roll bonuses)
# ═══════════════════════════════════════════════════════════════

def compute_investment_modifier(allocation: InvestmentAllocation, budget: float) -> float:
    """Return an additive team-strength bonus (0–8 points on 0–100 scale).

    Used to inject in-season effects from investment spending into fast_sim
    without requiring attribute changes.  Specifically:
      - training  → offensive output (speed/agility)
      - coaching  → overall consistency
      - science   → marginal stamina / resilience
    """
    budget_scale = min(2.5, budget / 8.0)
    training_bonus = allocation.training * budget_scale * 3.0
    coaching_bonus = allocation.coaching * budget_scale * 2.5
    science_bonus  = allocation.science  * budget_scale * 1.5
    return min(8.0, training_bonus + coaching_bonus + science_bonus)


def generate_ai_investment(prestige: int, rng: Optional[random.Random] = None) -> InvestmentAllocation:
    """Generate a plausible investment allocation for an AI team based on prestige."""
    if rng is None:
        rng = random.Random()
    # Add slight randomness so teams aren't identical
    noise = lambda: rng.uniform(-0.03, 0.03)
    if prestige >= 75:
        return InvestmentAllocation(
            training=max(0, 0.30 + noise()),
            coaching=max(0, 0.25 + noise()),
            stadium=max(0, 0.15 + noise()),
            youth=max(0, 0.10 + noise()),
            science=max(0, 0.15 + noise()),
            marketing=max(0, 0.05 + noise()),
        )
    elif prestige >= 50:
        return InvestmentAllocation(
            training=max(0, 0.25 + noise()),
            coaching=max(0, 0.20 + noise()),
            stadium=max(0, 0.15 + noise()),
            youth=max(0, 0.20 + noise()),
            science=max(0, 0.10 + noise()),
            marketing=max(0, 0.10 + noise()),
        )
    else:
        return InvestmentAllocation(
            training=max(0, 0.20 + noise()),
            coaching=max(0, 0.15 + noise()),
            stadium=max(0, 0.10 + noise()),
            youth=max(0, 0.30 + noise()),
            science=max(0, 0.10 + noise()),
            marketing=max(0, 0.15 + noise()),
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


# ═══════════════════════════════════════════════════════════════
# 20-YEAR SCORING
# ═══════════════════════════════════════════════════════════════

def compute_club_valuation(
    revenue: float,
    fanbase: int,
    infra_total: float,
) -> float:
    """Estimate club market value in millions.

    Formula:
      club_value = revenue * 4 + fanbase * 50 + infra_total * 2
    """
    return round(
        revenue * 4
        + fanbase * 50
        + infra_total * 2,
        1,
    )


def compute_final_score(titles, avg_tier, fanbase, club_value, bankroll):
    """Compute owner's final/running score.

    Formula:
      titles * 500 + (5 - avg_tier) * 200 + fanbase * 0.1 + club_value + bankroll
    """
    return (
        titles * 500
        + (5 - avg_tier) * 200
        + fanbase * 0.1
        + club_value
        + bankroll
    )


def compute_final_score_report(dynasty) -> dict:
    """Compute owner's running/final score report dict.

    Works at any point in the dynasty — shows a 'running score' before 20 seasons
    and the 'final score' label at 20+.
    """
    hist = dynasty.team_histories.get(dynasty.owner.club_key)
    titles = len(hist.championship_years) if hist else 0
    tier_history = hist.tier_history if hist else []
    avg_tier = mean(tier_history) if tier_history else 4.0

    last_fin = None
    if dynasty.financial_history:
        last_fin = max(dynasty.financial_history.values(), key=lambda f: f.get("year", 0))
    rev = last_fin.get("total_revenue", last_fin.get("revenue", 0)) if last_fin else 0.0

    infra = getattr(dynasty, "infrastructure", {})
    fanbase = int(getattr(dynasty, "fanbase", 0))
    infra_total = sum(infra.values()) if infra else 6.0
    valuation = compute_club_valuation(rev, fanbase, infra_total)

    infra_values = list(infra.values()) if infra else []
    infra_avg = round(mean(infra_values), 1) if infra_values else 1.0

    score = compute_final_score(titles, avg_tier, fanbase, valuation, max(0.0, dynasty.owner.bankroll))

    return {
        "total": round(score),
        "league_titles": titles,
        "avg_tier": round(avg_tier, 1),
        "club_valuation_M": valuation,
        "fanbase": fanbase,
        "bankroll_M": round(dynasty.owner.bankroll, 1),
        "infra_avg": infra_avg,
        "is_final": dynasty.owner.seasons_owned >= 20,
    }


def club_health(financials, infra):
    """Compute club health metrics for dashboard display."""

    infra_score = sum(infra.values()) / len(infra) if infra else 1.0

    # Support both ClubFinancials dataclass and plain dict
    if isinstance(financials, dict):
        bankroll = financials.get("bankroll_end", financials.get("bankroll", 0))
        fanbase = financials.get("fanbase_end", financials.get("fanbase", 0))
        net_income = financials.get("net_income", 0)
    else:
        bankroll = getattr(financials, "bankroll_end", 0)
        fanbase = getattr(financials, "fanbase_end", 0)
        net_income = getattr(financials, "net_income", 0)

    return {
        "financial": bankroll,
        "infrastructure": infra_score,
        "fanbase": fanbase,
        "profit": net_income,
    }
