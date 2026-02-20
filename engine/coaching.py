"""
Viperball Coaching System

Full coaching staff model: HC, OC, DC, STC — each with 6 attributes,
1 classification badge, contracts, salary pools, and a marketplace.

Coach attributes affect gameday simulation, player development, and recruiting.

Attribute Guide
---------------
- instincts     (25-95)  HIDDEN — not displayed numerically.  Drives mid-game
                          scheme adaptation speed and 4th-down decision quality.
- leadership    (25-95)  Momentum recovery, comeback execution, cascade prevention.
- composure     (25-95)  Non-linear: low = fiery (halftime fire-up), high = ice
                          (pressure-proof).  Neither extreme is strictly "better".
- rotations     (25-95)  Fatigue management and substitution patterns.
- development   (25-95)  Offseason player growth boost (feeds dev_boost).
- recruiting    (25-95)  Scouting accuracy, offer appeal, pipeline building.

Classification Guide
--------------------
- scheme_master    — Amplifies play-family modifiers; faster gameplan adaptation.
- gameday_manager  — Better situational calls; doubled halftime adjustments.
- motivator        — Trailing-at-half boost; faster momentum recovery.
- players_coach    — Retention bonus; chemistry that grows over the season.
- disciplinarian   — Fumble/muff reduction; variance compression.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

ATTR_MIN = 25
ATTR_MAX = 95

ROLES = ("head_coach", "oc", "dc", "stc")

CLASSIFICATIONS = (
    "scheme_master",
    "gameday_manager",
    "motivator",
    "players_coach",
    "disciplinarian",
)

CLASSIFICATION_LABELS = {
    "scheme_master":   "Scheme Master",
    "gameday_manager": "Gameday Manager",
    "motivator":       "Motivator",
    "players_coach":   "Players' Coach",
    "disciplinarian":  "Disciplinarian",
}

CLASSIFICATION_DESCRIPTIONS = {
    "scheme_master":   "Amplifies play-family modifiers and adapts the gameplan faster mid-game.",
    "gameday_manager": "Better situational calls: 4th-down accuracy, halftime adjustments, clock management.",
    "motivator":       "Fires up the team when trailing at halftime; recovers momentum faster after big plays.",
    "players_coach":   "Boosts retention and builds chemistry that compounds over the season.",
    "disciplinarian":  "Reduces fumbles and muffs; compresses outcome variance for fewer disasters.",
}


# Classification effect ranges — keyed by classification, each value is a dict
# of effect_name -> (lo, hi) or a fixed value.  The actual magnitude scales
# with the coach's relevant attribute.
CLASSIFICATION_EFFECTS = {
    "scheme_master": {
        "scheme_amplification":       (0.05, 0.12),
        "gameplan_adaptation_bonus":  (0.02, 0.06),
    },
    "gameday_manager": {
        "fourth_down_accuracy":         (0.05, 0.15),
        "halftime_adjustment_bonus":    (0.03, 0.08),
        "situational_amplification":    (0.04, 0.10),
    },
    "motivator": {
        "trailing_halftime_boost":      (1.05, 1.12),
        "momentum_recovery_plays":      (1, 3),      # plays faster
        "composure_amplification":      (1.10, 1.20),
    },
    "players_coach": {
        "retention_bonus":              (0.10, 0.25),
        "chemistry_bonus_per_game":     (0.003, 0.006),
        "recruiting_appeal_prestige":   (3, 8),
    },
    "disciplinarian": {
        "fumble_reduction":             (0.85, 0.95),
        "muff_reduction":              (0.80, 0.90),
        "variance_compression":        (0.90, 0.95),
        "gap_discipline_bonus":        (0.02, 0.06),
    },
}


# ──────────────────────────────────────────────
# SALARY TIERS  (coaching budget, not NIL)
# ──────────────────────────────────────────────

COACHING_SALARY_TIERS: Dict[str, Tuple[int, int]] = {
    "small":  (150_000, 300_000),
    "medium": (250_000, 500_000),
    "large":  (400_000, 750_000),
    "mega":   (600_000, 1_200_000),
}


# ──────────────────────────────────────────────
# DATACLASSES
# ──────────────────────────────────────────────

@dataclass
class CoachCareerStop:
    """One stint at a school in a particular role."""
    year_start: int
    year_end: Optional[int]
    team_name: str
    role: str
    wins: int = 0
    losses: int = 0
    championships: int = 0

    def to_dict(self) -> dict:
        return {
            "year_start": self.year_start,
            "year_end": self.year_end,
            "team_name": self.team_name,
            "role": self.role,
            "wins": self.wins,
            "losses": self.losses,
            "championships": self.championships,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CoachCareerStop":
        return cls(**d)


@dataclass
class CoachContract:
    """Active employment contract between a coach and a school."""
    coach_id: str
    role: str
    team_name: str
    annual_salary: int
    years_total: int
    years_remaining: int
    buyout: int
    year_signed: int

    def to_dict(self) -> dict:
        return {
            "coach_id": self.coach_id,
            "role": self.role,
            "team_name": self.team_name,
            "annual_salary": self.annual_salary,
            "years_total": self.years_total,
            "years_remaining": self.years_remaining,
            "buyout": self.buyout,
            "year_signed": self.year_signed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CoachContract":
        return cls(**d)


@dataclass
class CoachCard:
    """
    Sports-reference style coach profile.

    Six attributes, one classification badge, contract details,
    and full career history.
    """

    # Identity ─────────────────────────────────
    coach_id: str
    first_name: str
    last_name: str
    gender: str                  # "male" | "female" | "neutral"
    age: int

    # Role & classification ────────────────────
    role: str                    # "head_coach" | "oc" | "dc" | "stc"
    classification: str          # one of CLASSIFICATIONS

    # 6 Attributes (25-95) ─────────────────────
    instincts: int               # HIDDEN
    leadership: int
    composure: int
    rotations: int
    development: int
    recruiting: int

    # Contract ─────────────────────────────────
    contract_salary: int = 0
    contract_years_remaining: int = 0
    contract_buyout: int = 0
    year_signed: int = 0
    team_name: str = ""

    # Career stats ─────────────────────────────
    career_wins: int = 0
    career_losses: int = 0
    championships: int = 0
    seasons_coached: int = 0
    career_history: List[CoachCareerStop] = field(default_factory=list)

    # Former player link ───────────────────────
    is_former_player: bool = False
    former_player_id: Optional[str] = None

    # Coaching philosophy / flavor ─────────────
    philosophy: str = ""
    coaching_style: str = ""
    personality: str = ""
    background: str = ""

    # ── computed properties ───────────────────

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        return f"{self.first_name[0]}. {self.last_name}"

    @property
    def classification_label(self) -> str:
        return CLASSIFICATION_LABELS.get(self.classification, self.classification)

    @property
    def composure_label(self) -> str:
        """Human-readable composure description."""
        if self.composure <= 40:
            return "Fiery"
        elif self.composure <= 65:
            return "Balanced"
        else:
            return "Ice"

    @property
    def visible_score(self) -> int:
        """Weighted average of visible attributes — drives salary calculation.

        Instincts is excluded (hidden).
        """
        return int(
            self.leadership * 0.20
            + self.composure * 0.10
            + self.rotations * 0.15
            + self.development * 0.25
            + self.recruiting * 0.30
        )

    @property
    def win_percentage(self) -> float:
        total = self.career_wins + self.career_losses
        if total == 0:
            return 0.0
        return self.career_wins / total

    @property
    def overall(self) -> int:
        """0-99 overall rating using ALL 6 attributes (including instincts)."""
        return int(
            self.instincts * 0.20
            + self.leadership * 0.20
            + self.composure * 0.10
            + self.rotations * 0.15
            + self.development * 0.15
            + self.recruiting * 0.20
        )

    @property
    def star_rating(self) -> str:
        """Star display based on overall."""
        ovr = self.overall
        if ovr >= 85:
            stars = 5
        elif ovr >= 75:
            stars = 4
        elif ovr >= 65:
            stars = 3
        elif ovr >= 55:
            stars = 2
        else:
            stars = 1
        return "\u2605" * stars + "\u2606" * (5 - stars)

    # ── serialization ─────────────────────────

    def to_dict(self) -> dict:
        return {
            "coach_id": self.coach_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "gender": self.gender,
            "age": self.age,
            "role": self.role,
            "classification": self.classification,
            "instincts": self.instincts,
            "leadership": self.leadership,
            "composure": self.composure,
            "rotations": self.rotations,
            "development": self.development,
            "recruiting": self.recruiting,
            "contract_salary": self.contract_salary,
            "contract_years_remaining": self.contract_years_remaining,
            "contract_buyout": self.contract_buyout,
            "year_signed": self.year_signed,
            "team_name": self.team_name,
            "career_wins": self.career_wins,
            "career_losses": self.career_losses,
            "championships": self.championships,
            "seasons_coached": self.seasons_coached,
            "career_history": [s.to_dict() for s in self.career_history],
            "is_former_player": self.is_former_player,
            "former_player_id": self.former_player_id,
            "philosophy": self.philosophy,
            "coaching_style": self.coaching_style,
            "personality": self.personality,
            "background": self.background,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CoachCard":
        history = [
            CoachCareerStop.from_dict(s)
            for s in d.get("career_history", [])
        ]
        return cls(
            coach_id=d["coach_id"],
            first_name=d["first_name"],
            last_name=d["last_name"],
            gender=d.get("gender", "neutral"),
            age=d.get("age", 45),
            role=d["role"],
            classification=d["classification"],
            instincts=d["instincts"],
            leadership=d["leadership"],
            composure=d["composure"],
            rotations=d["rotations"],
            development=d["development"],
            recruiting=d["recruiting"],
            contract_salary=d.get("contract_salary", 0),
            contract_years_remaining=d.get("contract_years_remaining", 0),
            contract_buyout=d.get("contract_buyout", 0),
            year_signed=d.get("year_signed", 0),
            team_name=d.get("team_name", ""),
            career_wins=d.get("career_wins", 0),
            career_losses=d.get("career_losses", 0),
            championships=d.get("championships", 0),
            seasons_coached=d.get("seasons_coached", 0),
            career_history=history,
            is_former_player=d.get("is_former_player", False),
            former_player_id=d.get("former_player_id"),
            philosophy=d.get("philosophy", ""),
            coaching_style=d.get("coaching_style", ""),
            personality=d.get("personality", ""),
            background=d.get("background", ""),
        )


# ──────────────────────────────────────────────
# COACHING SALARY POOL
# ──────────────────────────────────────────────

@dataclass
class CoachingSalaryPool:
    """
    A team's coaching budget for a single year.

    Manages total salary cap and active contracts.
    Mirrors NILProgram structure.
    """
    team_name: str
    annual_budget: int
    contracts: List[CoachContract] = field(default_factory=list)

    @property
    def committed(self) -> int:
        """Total salary committed to active contracts."""
        return sum(c.annual_salary for c in self.contracts)

    @property
    def available(self) -> int:
        """Remaining budget after committed salaries."""
        return max(0, self.annual_budget - self.committed)

    def can_afford(self, salary: int) -> bool:
        return self.available >= salary

    def add_contract(self, contract: CoachContract) -> bool:
        """Add a contract if affordable.  Returns True on success."""
        if not self.can_afford(contract.annual_salary):
            return False
        self.contracts.append(contract)
        return True

    def release_contract(self, coach_id: str) -> int:
        """Remove a contract by coach_id.  Returns the buyout cost (0 if not found)."""
        for i, c in enumerate(self.contracts):
            if c.coach_id == coach_id:
                buyout = c.buyout if c.years_remaining > 0 else 0
                self.contracts.pop(i)
                return buyout
        return 0

    def get_summary(self) -> dict:
        return {
            "team_name": self.team_name,
            "annual_budget": self.annual_budget,
            "committed": self.committed,
            "available": self.available,
            "num_contracts": len(self.contracts),
            "contracts": [c.to_dict() for c in self.contracts],
        }

    def to_dict(self) -> dict:
        return self.get_summary()

    @classmethod
    def from_dict(cls, d: dict) -> "CoachingSalaryPool":
        pool = cls(
            team_name=d["team_name"],
            annual_budget=d["annual_budget"],
        )
        pool.contracts = [
            CoachContract.from_dict(c) for c in d.get("contracts", [])
        ]
        return pool


# ──────────────────────────────────────────────
# BUDGET GENERATION
# ──────────────────────────────────────────────

def _prestige_multiplier(prestige: int) -> float:
    """0.5x at prestige 0, 1.5x at prestige 100."""
    return 0.5 + (prestige / 100.0)


def generate_coaching_budget(
    prestige: int,
    market: str = "medium",
    previous_season_wins: int = 5,
    championship: bool = False,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Generate an annual coaching salary budget for a team.

    Same formula as generate_nil_budget but with coaching salary tiers.

    Args:
        prestige: 0-100 team prestige score
        market: "small" | "medium" | "large" | "mega"
        previous_season_wins: wins from prior season
        championship: whether the team won the championship
        rng: optional seeded Random

    Returns:
        int — annual coaching budget in dollars
    """
    if rng is None:
        rng = random.Random()

    lo, hi = COACHING_SALARY_TIERS.get(market, COACHING_SALARY_TIERS["medium"])
    base = rng.randint(lo, hi)
    base = int(base * _prestige_multiplier(prestige))

    # Win bonus
    if previous_season_wins > 5:
        base += (previous_season_wins - 5) * 10_000

    # Championship bonus
    if championship:
        base += 150_000

    # Random noise ±10%
    noise = rng.uniform(0.90, 1.10)
    return int(base * noise)


def auto_coaching_pool(
    team_name: str,
    prestige: int,
    market: str = "medium",
    previous_wins: int = 5,
    championship: bool = False,
    rng: Optional[random.Random] = None,
) -> CoachingSalaryPool:
    """Generate a coaching salary pool for a team."""
    budget = generate_coaching_budget(
        prestige=prestige,
        market=market,
        previous_season_wins=previous_wins,
        championship=championship,
        rng=rng,
    )
    return CoachingSalaryPool(team_name=team_name, annual_budget=budget)


# ──────────────────────────────────────────────
# ATTRIBUTE & CLASSIFICATION GENERATION
# ──────────────────────────────────────────────

# Classification tendencies: which attribute tends to be highest for each type.
# When generating a coach of a given classification, we boost the "primary" attr.
_CLASSIFICATION_PRIMARY_ATTR = {
    "scheme_master":   "instincts",
    "gameday_manager": "composure",
    "motivator":       "leadership",
    "players_coach":   "development",
    "disciplinarian":  "rotations",
}

# Weights for random classification selection (flat by default).
_DEFAULT_CLASSIFICATION_WEIGHTS = {c: 1.0 for c in CLASSIFICATIONS}


def _clamp_attr(val: int) -> int:
    return max(ATTR_MIN, min(ATTR_MAX, val))


def _generate_attributes(
    classification: str,
    prestige: int = 50,
    role: str = "head_coach",
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """
    Generate 6 coaching attributes for a new coach.

    Higher-prestige teams tend to attract better coaches (higher floor).
    The classification's primary attribute gets a +5-12 bonus.
    """
    if rng is None:
        rng = random.Random()

    # Base range shifts with prestige:  prestige 0 → 30-65, prestige 100 → 50-90
    base_lo = 30 + int(prestige * 0.20)
    base_hi = 65 + int(prestige * 0.25)

    # HC tends to be slightly better overall; coordinators slightly more specialized
    if role == "head_coach":
        base_lo += 3
        base_hi += 3

    attrs = {}
    for attr_name in ("instincts", "leadership", "composure", "rotations",
                       "development", "recruiting"):
        val = rng.randint(base_lo, base_hi)
        attrs[attr_name] = _clamp_attr(val)

    # Primary attribute bonus for classification
    primary = _CLASSIFICATION_PRIMARY_ATTR.get(classification)
    if primary and primary in attrs:
        bonus = rng.randint(5, 12)
        attrs[primary] = _clamp_attr(attrs[primary] + bonus)

    return attrs


def _pick_classification(
    rng: Optional[random.Random] = None,
    weights: Optional[Dict[str, float]] = None,
) -> str:
    """Pick a classification using weighted random selection."""
    if rng is None:
        rng = random.Random()
    w = weights or _DEFAULT_CLASSIFICATION_WEIGHTS
    choices = list(w.keys())
    wts = [w[c] for c in choices]
    return rng.choices(choices, weights=wts, k=1)[0]


def calculate_coach_salary(
    card: CoachCard,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Determine a coach's market salary based on visible attributes and record.

    Instincts is intentionally excluded — teams can't see it, so it doesn't
    drive salary.  This means a Scheme Master with hidden-high instincts
    can be a bargain hire.

    Returns annual salary in dollars.
    """
    if rng is None:
        rng = random.Random()

    # Base from visible score (25-95 range → ~$50k-$300k base)
    vs = card.visible_score
    base = int(vs * 2500 + 20_000)

    # Career record multiplier
    wp = card.win_percentage
    if card.seasons_coached >= 3:
        # Proven coaches with winning records command more
        base = int(base * (0.8 + wp * 0.4))  # 0.8x (0% wp) to 1.2x (100% wp)

    # Championship premium
    base += card.championships * 25_000

    # HC premium
    if card.role == "head_coach":
        base = int(base * 1.25)

    # Noise ±8%
    noise = rng.uniform(0.92, 1.08)
    return int(base * noise)


# ──────────────────────────────────────────────
# COACH GENERATION
# ──────────────────────────────────────────────

# Re-use name pools from scripts.generate_coach_names (imported lazily to avoid
# circular deps when used from engine/).
_FEMALE_FIRST = [
    "Jennifer", "Michelle", "Lisa", "Amy", "Angela", "Melissa", "Kimberly",
    "Jessica", "Elizabeth", "Sarah", "Amanda", "Nicole", "Stephanie", "Rebecca",
    "Katherine", "Laura", "Christine", "Rachel", "Heather", "Kelly",
    "Catherine", "Patricia", "Margaret", "Susan", "Carol", "Diane", "Janet",
    "Courtney", "Kristen", "Megan", "Shannon", "Tracy", "Stacy", "Wendy",
    "Kristin", "Andrea", "Danielle", "Monica", "Erica", "Alicia",
]

_MALE_FIRST = [
    "Michael", "David", "James", "John", "Robert", "William", "Richard",
    "Thomas", "Mark", "Steven", "Daniel", "Paul", "Brian", "Kevin",
    "Christopher", "Matthew", "Andrew", "Joseph", "Timothy", "Scott", "Jeffrey",
    "Kenneth", "Eric", "Gregory", "Ronald", "Donald", "Gary", "Anthony",
    "Ryan", "Jason", "Justin", "Brandon", "Derek", "Travis", "Chad", "Brett",
    "Shawn", "Todd", "Kyle", "Craig", "Sean", "Nathan", "Aaron", "Adam",
]

_NEUTRAL_FIRST = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
    "Avery", "Quinn", "Cameron", "Dakota", "Drew", "Charlie",
    "Sage", "River", "Phoenix", "Skyler", "Rowan", "Parker",
    "Emerson", "Finley", "Logan", "Blake", "Peyton", "Reese", "Harley",
]

_SURNAMES = [
    "O'Brien", "McCarthy", "Sullivan", "Murphy", "Kelly", "Ryan", "Brennan",
    "Donnelly", "Callahan", "Flanagan", "MacLeod", "Campbell",
    "Ferguson", "Morrison", "Robertson", "MacDonald", "Fraser",
    "Rossi", "Marino", "Romano", "Rizzo", "Conti", "Battaglia", "Ferrara",
    "Lombardi", "Antonelli", "Costello", "DeLuca", "DiMarco", "Gallo",
    "Schmidt", "Mueller", "Wagner", "Weber", "Becker", "Hoffman", "Schneider",
    "Fischer", "Zimmerman", "Schultz", "Van Doren",
    "Anderson", "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Lewis",
    "Kowalski", "Nowak", "Lewandowski", "Jankowski",
    "Washington", "Jefferson", "Coleman", "Richardson", "Brooks", "Sanders",
    "Kim", "Lee", "Chen", "Patel", "Nguyen", "Rodriguez", "Hernandez",
]

_COACHING_BACKGROUNDS = [
    "Former college assistant promoted to head coach",
    "Veteran high school coach transitioning to college",
    "Long-time coordinator stepping into head role",
    "Rising star assistant with innovative schemes",
    "Former college player returning to alma mater",
    "Experienced coach hired from rival program",
    "First-time head coach with strong pedigree",
    "Turnaround specialist known for rebuilding programs",
    "Defense-minded tactician",
    "Offensive innovator",
]

_PHILOSOPHIES = [
    "Ground-based power attack using all 6 downs",
    "Multiple lateral chains and perimeter speed",
    "Snap kick-heavy air raid with the foot",
    "Conservative, mistake-free football",
    "Pre-snap chaos and Viper misdirection",
    "Defense-first, punt early and pin deep",
    "Maximum laterals, maximum chaos",
    "Single-wing misdirection with direct snaps",
    "Fast-paced, high-risk offensive tempo",
    "Balanced approach adapting to opponent",
    "Defensive stability and ball control",
    "Field position battle with strategic kicking",
]

_PERSONALITIES = [
    "demanding but fair", "players-first mentor", "tactical genius",
    "motivational leader", "detail-oriented strategist", "intense competitor",
    "calm under pressure", "innovative thinker", "disciplinarian",
    "relationship builder", "analytics-driven", "old-school fundamentalist",
]

_COACHING_STYLES = [
    "aggressive", "conservative", "balanced", "innovative",
    "traditional", "analytical", "player-focused", "risk-taking",
    "methodical", "adaptive",
]


def generate_coach_card(
    role: str = "head_coach",
    team_name: str = "",
    prestige: int = 50,
    gender: str = "random",
    classification: Optional[str] = None,
    year: int = 2026,
    rng: Optional[random.Random] = None,
) -> CoachCard:
    """
    Generate a complete CoachCard with random attributes, classification,
    and biographical details.

    Args:
        role: "head_coach" | "oc" | "dc" | "stc"
        team_name: school name (empty for free agents)
        prestige: 0-100, influences attribute floor
        gender: "male" | "female" | "neutral" | "random"
        classification: force a specific classification, or None for random
        year: current dynasty year (for contract dating)
        rng: optional seeded Random

    Returns:
        A fully populated CoachCard.
    """
    if rng is None:
        rng = random.Random()

    # ── gender / name ─────────────────────────
    if gender == "random":
        gender = rng.choices(
            ["female", "male", "neutral"],
            weights=[0.45, 0.45, 0.10],
            k=1,
        )[0]

    if gender == "female":
        first = rng.choice(_FEMALE_FIRST)
    elif gender == "male":
        first = rng.choice(_MALE_FIRST)
    else:
        first = rng.choice(_NEUTRAL_FIRST)

    last = rng.choice(_SURNAMES)

    # ── age / experience ──────────────────────
    if role == "head_coach":
        age = rng.randint(40, 65)
    else:
        age = rng.randint(32, 58)
    years_exp = max(1, age - 25 - rng.randint(0, 5))
    seasons = max(0, years_exp - rng.randint(2, 6))

    # ── classification ────────────────────────
    cls_ = classification or _pick_classification(rng=rng)

    # ── attributes ────────────────────────────
    attrs = _generate_attributes(
        classification=cls_,
        prestige=prestige,
        role=role,
        rng=rng,
    )

    # ── career record ─────────────────────────
    if seasons > 0:
        avg_wins = rng.randint(5, 10)
        total_wins = seasons * avg_wins + rng.randint(-3, 3)
        total_wins = max(0, total_wins)
        total_games = seasons * 12
        total_losses = max(0, total_games - total_wins)
        champs = max(0, seasons // 4 - rng.randint(0, 2))
    else:
        total_wins = 0
        total_losses = 0
        champs = 0

    # ── coach ID ──────────────────────────────
    coach_id = f"coach_{first.lower()}_{last.lower().replace(' ', '_')}_{rng.randint(100, 999)}"

    # ── contract ──────────────────────────────
    contract_years = rng.randint(2, 5) if team_name else 0
    salary = 0
    buyout = 0

    card = CoachCard(
        coach_id=coach_id,
        first_name=first,
        last_name=last,
        gender=gender,
        age=age,
        role=role,
        classification=cls_,
        instincts=attrs["instincts"],
        leadership=attrs["leadership"],
        composure=attrs["composure"],
        rotations=attrs["rotations"],
        development=attrs["development"],
        recruiting=attrs["recruiting"],
        team_name=team_name,
        career_wins=total_wins,
        career_losses=total_losses,
        championships=champs,
        seasons_coached=seasons,
        year_signed=year,
        philosophy=rng.choice(_PHILOSOPHIES),
        coaching_style=rng.choice(_COACHING_STYLES),
        personality=rng.choice(_PERSONALITIES),
        background=rng.choice(_COACHING_BACKGROUNDS),
    )

    # Set salary after card exists so calculate_coach_salary can use it
    salary = calculate_coach_salary(card, rng=rng)
    card.contract_salary = salary
    card.contract_years_remaining = contract_years
    card.contract_buyout = int(salary * contract_years * 0.5) if contract_years > 0 else 0

    return card


def generate_coaching_staff(
    team_name: str = "",
    prestige: int = 50,
    year: int = 2026,
    rng: Optional[random.Random] = None,
) -> Dict[str, CoachCard]:
    """
    Generate a full 4-person coaching staff: HC, OC, DC, STC.

    Returns:
        Dict mapping role -> CoachCard.
    """
    if rng is None:
        rng = random.Random()

    staff: Dict[str, CoachCard] = {}
    for role in ROLES:
        card = generate_coach_card(
            role=role,
            team_name=team_name,
            prestige=prestige,
            year=year,
            rng=rng,
        )
        staff[role] = card

    return staff


# ──────────────────────────────────────────────
# COACH MARKETPLACE
# ──────────────────────────────────────────────

@dataclass
class CoachMarketplace:
    """
    Offseason coaching marketplace.

    Contains free-agent coaches, poaching targets (employed coaches other teams
    can bid on), and retired-player-turned-coach entries.
    """
    year: int
    available_coaches: List[CoachCard] = field(default_factory=list)
    poaching_targets: List[CoachCard] = field(default_factory=list)
    retired_players: List[CoachCard] = field(default_factory=list)

    def generate_free_agents(
        self,
        num_coaches: int = 40,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Populate the marketplace with randomly generated free-agent coaches."""
        if rng is None:
            rng = random.Random()

        for _ in range(num_coaches):
            role = rng.choice(ROLES)
            card = generate_coach_card(
                role=role,
                team_name="",
                prestige=rng.randint(20, 70),
                year=self.year,
                rng=rng,
            )
            self.available_coaches.append(card)

    def add_poaching_targets(
        self,
        coaching_staffs: Dict[str, Dict[str, CoachCard]],
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        Identify employed coaches that other teams can attempt to poach.

        Coordinators with high overall ratings and expiring contracts are
        prime poaching targets.
        """
        if rng is None:
            rng = random.Random()

        for team_name, staff in coaching_staffs.items():
            for role, card in staff.items():
                # Only coordinators and STC are poachable (not HC)
                if role == "head_coach":
                    continue
                # High-overall coordinators with <=1 year left
                if card.overall >= 70 and card.contract_years_remaining <= 1:
                    if rng.random() < 0.40:
                        self.poaching_targets.append(card)

    def hire_coach(
        self,
        team_name: str,
        coach_id: str,
        role: str,
        salary: int,
        years: int,
        year: int,
    ) -> Optional[CoachContract]:
        """
        Hire a coach from the marketplace.

        Removes them from available lists and creates a contract.
        Returns the contract or None if coach_id not found.
        """
        # Search across all lists
        for pool in (self.available_coaches, self.retired_players):
            for i, card in enumerate(pool):
                if card.coach_id == coach_id:
                    card.team_name = team_name
                    card.role = role
                    card.contract_salary = salary
                    card.contract_years_remaining = years
                    card.contract_buyout = int(salary * years * 0.5)
                    card.year_signed = year
                    pool.pop(i)
                    return CoachContract(
                        coach_id=coach_id,
                        role=role,
                        team_name=team_name,
                        annual_salary=salary,
                        years_total=years,
                        years_remaining=years,
                        buyout=card.contract_buyout,
                        year_signed=year,
                    )
        return None

    def poach_coach(
        self,
        hiring_team: str,
        coach_id: str,
        new_role: str,
        offer_salary: int,
        offer_years: int,
        year: int,
        rng: Optional[random.Random] = None,
    ) -> Optional[CoachContract]:
        """
        Attempt to poach a coach from another team.

        Success probability depends on salary increase and role promotion.
        Returns the new contract on success, or None on failure.
        """
        if rng is None:
            rng = random.Random()

        for i, card in enumerate(self.poaching_targets):
            if card.coach_id == coach_id:
                # Salary raise factor
                current_salary = card.contract_salary or 1
                raise_pct = (offer_salary - current_salary) / current_salary

                # Base accept chance: 30%
                accept_chance = 0.30
                # +20% if salary increase >= 30%
                if raise_pct >= 0.30:
                    accept_chance += 0.20
                # +25% if promoted to HC
                if new_role == "head_coach" and card.role != "head_coach":
                    accept_chance += 0.25
                # +10% if longer contract
                if offer_years > card.contract_years_remaining:
                    accept_chance += 0.10

                accept_chance = min(0.90, accept_chance)

                if rng.random() < accept_chance:
                    card.team_name = hiring_team
                    card.role = new_role
                    card.contract_salary = offer_salary
                    card.contract_years_remaining = offer_years
                    card.contract_buyout = int(offer_salary * offer_years * 0.5)
                    card.year_signed = year
                    self.poaching_targets.pop(i)
                    return CoachContract(
                        coach_id=coach_id,
                        role=new_role,
                        team_name=hiring_team,
                        annual_salary=offer_salary,
                        years_total=offer_years,
                        years_remaining=offer_years,
                        buyout=card.contract_buyout,
                        year_signed=year,
                    )
                return None  # Rejected
        return None  # Not found

    def get_summary(self) -> dict:
        return {
            "year": self.year,
            "free_agents": len(self.available_coaches),
            "poaching_targets": len(self.poaching_targets),
            "retired_players": len(self.retired_players),
            "top_free_agents": [
                {"name": c.full_name, "role": c.role, "overall": c.overall,
                 "classification": c.classification_label}
                for c in sorted(self.available_coaches,
                                key=lambda c: c.overall, reverse=True)[:5]
            ],
        }


# ──────────────────────────────────────────────
# AI COACHING DECISIONS (offseason)
# ──────────────────────────────────────────────

def evaluate_coaching_staff(
    staff: Dict[str, CoachCard],
    team_wins: int,
    team_losses: int,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    CPU team evaluates its coaching staff.  Returns list of roles to fire.

    Firing criteria:
    - HC: fired if winning pct < 0.35 and coached >= 3 seasons, or
          if winning pct < 0.50 and coached >= 5 seasons (with 30% chance)
    - Coordinators: fired if relevant attribute is bottom-quartile (<40) and
          team record is losing, with 25% chance
    - STC: almost never fired (10% chance if record is terrible)
    """
    if rng is None:
        rng = random.Random()

    total = team_wins + team_losses
    wp = team_wins / total if total > 0 else 0.5
    fire_list = []

    hc = staff.get("head_coach")
    if hc:
        if wp < 0.35 and hc.seasons_coached >= 3:
            fire_list.append("head_coach")
        elif wp < 0.50 and hc.seasons_coached >= 5 and rng.random() < 0.30:
            fire_list.append("head_coach")

    for role, attr in [("oc", "development"), ("dc", "rotations")]:
        card = staff.get(role)
        if card and getattr(card, attr) < 40 and wp < 0.50:
            if rng.random() < 0.25:
                fire_list.append(role)

    stc = staff.get("stc")
    if stc and wp < 0.25 and rng.random() < 0.10:
        fire_list.append("stc")

    return fire_list


def ai_fill_vacancies(
    staff: Dict[str, CoachCard],
    vacancies: List[str],
    marketplace: CoachMarketplace,
    salary_pool: CoachingSalaryPool,
    team_name: str,
    year: int,
    rng: Optional[random.Random] = None,
) -> Dict[str, CoachCard]:
    """
    CPU team fills coaching vacancies from the marketplace.

    For each vacancy, find the best affordable coach for that role.
    Returns the updated staff dict.
    """
    if rng is None:
        rng = random.Random()

    for role in vacancies:
        # Remove fired coach from staff
        if role in staff:
            del staff[role]

        # Find candidates for this role
        candidates = [
            c for c in marketplace.available_coaches
            if c.role == role or role != "head_coach"
        ]
        # Sort by overall
        candidates.sort(key=lambda c: c.overall, reverse=True)

        hired = False
        for candidate in candidates[:10]:  # Check top 10
            salary = calculate_coach_salary(candidate, rng=rng)
            contract_years = rng.randint(2, 4)

            if salary_pool.can_afford(salary):
                contract = marketplace.hire_coach(
                    team_name=team_name,
                    coach_id=candidate.coach_id,
                    role=role,
                    salary=salary,
                    years=contract_years,
                    year=year,
                )
                if contract:
                    salary_pool.add_contract(contract)
                    candidate.role = role
                    staff[role] = candidate
                    hired = True
                    break

        # If nobody affordable, generate a cheap fill-in
        if not hired:
            fill = generate_coach_card(
                role=role,
                team_name=team_name,
                prestige=30,
                year=year,
                rng=rng,
            )
            fill.contract_salary = max(50_000, salary_pool.available // 2)
            fill.contract_years_remaining = 1
            fill.contract_buyout = 0
            staff[role] = fill

    return staff


# ──────────────────────────────────────────────
# PLAYER-TO-COACH CONVERSION
# ──────────────────────────────────────────────

def derive_coach_attributes_from_player(
    player_card,
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """
    Derive coaching attributes from a PlayerCard's playing attributes.

    Mapping:
    - instincts:   (awareness + lateral_skill) / 2
    - leadership:  (awareness + power) / 2 + captain/games bonus
    - composure:   random-weighted (no strong playing correlate)
    - rotations:   (stamina + awareness) / 2
    - development: potential-star influence (high-potential players who grew)
    - recruiting:  (hands + awareness) / 2 — the "people person" stats
    """
    if rng is None:
        rng = random.Random()

    awareness = getattr(player_card, "awareness", 70)
    lateral = getattr(player_card, "lateral_skill", 70)
    power = getattr(player_card, "power", 70)
    stamina = getattr(player_card, "stamina", 75)
    hands = getattr(player_card, "hands", 70)
    potential = getattr(player_card, "potential", 3)
    games = getattr(player_card, "career_games", 30)

    # Games bonus (experience): +1 per 10 games played, max +5
    games_bonus = min(5, games // 10)

    # Potential-to-development: higher potential as a player → understands growth
    potential_bonus = (potential - 1) * 3  # 0/3/6/9/12 for 1-5 star

    instincts = _clamp_attr(int((awareness + lateral) / 2) + rng.randint(-5, 5))
    leadership = _clamp_attr(int((awareness + power) / 2) + games_bonus + rng.randint(-3, 3))
    composure = _clamp_attr(rng.randint(35, 80) + rng.randint(-5, 5))
    rotations_ = _clamp_attr(int((stamina + awareness) / 2) + rng.randint(-5, 5))
    development_ = _clamp_attr(50 + potential_bonus + rng.randint(-5, 5))
    recruiting_ = _clamp_attr(int((hands + awareness) / 2) + rng.randint(-3, 5))

    return {
        "instincts": instincts,
        "leadership": leadership,
        "composure": composure,
        "rotations": rotations_,
        "development": development_,
        "recruiting": recruiting_,
    }


def derive_classification_from_player(
    player_card,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Pick a coaching classification based on the player's profile.

    Not deterministic — uses weighted probabilities based on playing attributes.
    """
    if rng is None:
        rng = random.Random()

    awareness = getattr(player_card, "awareness", 70)
    tackling = getattr(player_card, "tackling", 70)
    potential = getattr(player_card, "potential", 3)
    lateral = getattr(player_card, "lateral_skill", 70)

    weights = {c: 1.0 for c in CLASSIFICATIONS}

    # High awareness → Scheme Master / Gameday Manager
    if awareness >= 80:
        weights["scheme_master"] += 2.0
        weights["gameday_manager"] += 1.5

    # High tackling + consistent → Disciplinarian
    if tackling >= 80:
        weights["disciplinarian"] += 2.5

    # High potential → Players' Coach (understands development)
    if potential >= 4:
        weights["players_coach"] += 2.0

    # High lateral → innovative → Motivator
    if lateral >= 85:
        weights["motivator"] += 1.5

    return _pick_classification(rng=rng, weights=weights)


def convert_player_to_coach(
    player_card,
    team_name: str = "",
    role: str = "head_coach",
    year: int = 2026,
    years_after_graduation: int = 6,
    rng: Optional[random.Random] = None,
) -> CoachCard:
    """
    Convert a PlayerCard into a CoachCard.

    Preserves the player's name and links back to their player_id.
    Derives coaching attributes and classification from their playing profile.

    Args:
        player_card: a PlayerCard dataclass instance
        team_name: school hiring them (empty for free agent)
        role: coaching role
        year: current dynasty year
        years_after_graduation: how many years since they graduated
        rng: optional seeded Random

    Returns:
        A CoachCard with attributes derived from playing career.
    """
    if rng is None:
        rng = random.Random()

    attrs = derive_coach_attributes_from_player(player_card, rng=rng)
    cls_ = derive_classification_from_player(player_card, rng=rng)

    first = getattr(player_card, "first_name", "Unknown")
    last = getattr(player_card, "last_name", "Coach")
    gender_guess = "neutral"  # We don't store gender on PlayerCard; default neutral
    age = 22 + years_after_graduation

    coach_id = f"coach_{first.lower()}_{last.lower()}_{rng.randint(100, 999)}"
    player_id = getattr(player_card, "player_id", None)

    card = CoachCard(
        coach_id=coach_id,
        first_name=first,
        last_name=last,
        gender=gender_guess,
        age=age,
        role=role,
        classification=cls_,
        instincts=attrs["instincts"],
        leadership=attrs["leadership"],
        composure=attrs["composure"],
        rotations=attrs["rotations"],
        development=attrs["development"],
        recruiting=attrs["recruiting"],
        team_name=team_name,
        is_former_player=True,
        former_player_id=player_id,
        year_signed=year,
        background="Former college player returning to coaching",
        philosophy=rng.choice(_PHILOSOPHIES),
        coaching_style=rng.choice(_COACHING_STYLES),
        personality=rng.choice(_PERSONALITIES),
    )

    # Lower salary for unproven coaches
    salary = int(calculate_coach_salary(card, rng=rng) * 0.70)
    card.contract_salary = salary
    card.contract_years_remaining = 1  # Prove-it deal
    card.contract_buyout = 0

    return card


# ──────────────────────────────────────────────
# GAMEDAY EFFECT CALCULATORS
# ──────────────────────────────────────────────

def get_classification_effects(
    card: CoachCard,
    rng: Optional[random.Random] = None,
) -> Dict[str, float]:
    """
    Compute the actual effect magnitudes for a coach's classification.

    Effects scale linearly within their range based on the coach's primary
    attribute for that classification.

    Returns a dict of effect_name -> magnitude.
    """
    if rng is None:
        rng = random.Random()

    cls_ = card.classification
    ranges = CLASSIFICATION_EFFECTS.get(cls_, {})
    primary_attr_name = _CLASSIFICATION_PRIMARY_ATTR.get(cls_, "instincts")
    primary_val = getattr(card, primary_attr_name, 50)

    # Normalize primary to 0-1 within ATTR_MIN-ATTR_MAX range
    t = (primary_val - ATTR_MIN) / (ATTR_MAX - ATTR_MIN)
    t = max(0.0, min(1.0, t))

    effects = {}
    for name, (lo, hi) in ranges.items():
        effects[name] = lo + t * (hi - lo)

    return effects


def compute_dev_boost(
    coaching_staff: Dict[str, CoachCard],
) -> float:
    """
    Compute the development boost from coaching staff.

    Maps the HC's development attribute (25-95) to a 0-8 scale
    that feeds directly into apply_offseason_development(dev_boost=...).

    A 95-development coach gives max boost (8.0), same as max DraftyQueenz.
    A 25-development coach gives 0 boost.
    """
    hc = coaching_staff.get("head_coach")
    if hc is None:
        return 0.0
    dev_rating = hc.development
    return (dev_rating - ATTR_MIN) / (ATTR_MAX - ATTR_MIN) * 8.0


def compute_recruiting_bonus(
    coaching_staff: Dict[str, CoachCard],
) -> float:
    """
    Compute the recruiting appeal bonus from coaching staff.

    Returns a 0-1 normalized score that can be used as a weight in
    recruit decision formulas.  HC recruiting attribute is primary.
    """
    hc = coaching_staff.get("head_coach")
    if hc is None:
        return 0.0
    return hc.recruiting / ATTR_MAX


def compute_scouting_error(
    coaching_staff: Dict[str, CoachCard],
) -> int:
    """
    Compute scouting noise based on HC recruiting attribute.

    High recruiting = accurate scouting (error 0-2).
    Low recruiting = noisy scouting (error 5-7).

    Returns max scouting error in attribute points.
    """
    hc = coaching_staff.get("head_coach")
    if hc is None:
        return 5
    return max(0, int((100 - hc.recruiting) / 10))


def compute_gameday_modifiers(
    coaching_staff: Dict[str, CoachCard],
    rng: Optional[random.Random] = None,
) -> Dict[str, float]:
    """
    Compute aggregate gameday modifiers from the full coaching staff.

    Used by game_engine.py to apply coaching effects during simulation.

    Returns dict with keys:
    - instincts_factor: 0.0-1.0 (affects adaptation speed)
    - leadership_factor: 0.0-1.0 (affects momentum recovery)
    - composure_value: raw composure value (interpreted non-linearly by engine)
    - fatigue_resistance_mod: modifier to fatigue accumulation
    - classification_effects: dict of effect_name -> magnitude (from HC)
    """
    if rng is None:
        rng = random.Random()

    hc = coaching_staff.get("head_coach")
    oc = coaching_staff.get("oc")
    dc = coaching_staff.get("dc")

    # Blend HC and coordinator attributes
    def _blend(attr: str, hc_wt: float = 0.4) -> float:
        hc_val = getattr(hc, attr, 50) if hc else 50
        # Use relevant coordinator
        coord = oc if attr in ("development", "recruiting") else dc
        coord_val = getattr(coord, attr, 50) if coord else 50
        return hc_val * hc_wt + coord_val * (1.0 - hc_wt)

    instincts_raw = _blend("instincts")
    leadership_raw = _blend("leadership")
    composure_raw = hc.composure if hc else 50
    rotations_raw = _blend("rotations", hc_wt=0.3)

    # Normalize to 0-1
    norm = lambda v: (v - ATTR_MIN) / (ATTR_MAX - ATTR_MIN)

    # Fatigue resistance: rotations 50 → 0.0 mod, 95 → +0.045
    fatigue_mod = (rotations_raw - 50) / 1000.0

    # Classification effects from HC
    cls_effects = get_classification_effects(hc, rng=rng) if hc else {}

    return {
        "instincts_factor": norm(instincts_raw),
        "leadership_factor": norm(leadership_raw),
        "composure_value": composure_raw,
        "fatigue_resistance_mod": fatigue_mod,
        "classification_effects": cls_effects,
        "hc_classification": hc.classification if hc else "scheme_master",
    }
