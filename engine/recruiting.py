"""
Viperball Recruiting System

Generates high-school recruit classes, manages scouting, offers, and
commitments for dynasty mode.  Also provides a lighter "quick recruit"
path used by one-off season mode (transfer portal only).

Key concepts:
- Each offseason a national recruit pool is generated (configurable size).
- Recruits have revealed / hidden attributes — scouting uncovers hidden ones.
- Teams extend offers from a limited scholarship budget.
- Recruits decide based on team prestige, program fit, geography, and NIL.
- Signing day resolves all uncommitted recruits.

Usage (dynasty):
    from engine.recruiting import (
        generate_recruit_class, RecruitingBoard, Scout, Recruit
    )

    pool = generate_recruit_class(year=2027, size=300, rng=rng)
    board = RecruitingBoard(team_name="Gonzaga", scholarships=8)
    board.scout(pool[0], level="full")
    board.offer(pool[0])
    board.simulate_decisions(team_prestige=75, nil_budget=500_000, rng=rng)
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.player_card import PlayerCard, _get_position_weights


# ──────────────────────────────────────────────
# POSITIONS / ARCHETYPES (mirrors generate_rosters)
# ──────────────────────────────────────────────

POSITIONS = [
    "Zeroback",
    "Halfback",
    "Wingback",
    "Slotback",
    "Viper",
    "Keeper",
    "Offensive Line",
    "Defensive Line",
]

# Position distribution for a recruit class (roughly mirrors roster needs)
_POSITION_WEIGHTS_POOL: List[Tuple[str, float]] = [
    ("Offensive Line", 0.22),
    ("Defensive Line", 0.19),
    ("Halfback", 0.11),
    ("Wingback", 0.11),
    ("Slotback", 0.11),
    ("Zeroback", 0.08),
    ("Viper", 0.08),
    ("Keeper", 0.10),
]

_REGIONS = [
    "northeast", "mid_atlantic", "south", "midwest",
    "west_coast", "texas_southwest",
]

_INTL_REGIONS = [
    "australian", "canadian_english", "canadian_french",
    "new_zealand", "uk_european", "latin_american", "african",
    "nordic", "caribbean",
]


def _pick_position(rng: random.Random) -> str:
    positions, weights = zip(*_POSITION_WEIGHTS_POOL)
    return rng.choices(positions, weights=weights, k=1)[0]


def _pick_region(rng: random.Random) -> str:
    """70 % domestic, 30 % international."""
    if rng.random() < 0.70:
        return rng.choice(_REGIONS)
    return rng.choice(_INTL_REGIONS)


# ──────────────────────────────────────────────
# RECRUIT
# ──────────────────────────────────────────────

@dataclass
class Recruit:
    """A high-school (or junior-college) prospect."""

    # Identity
    recruit_id: str
    first_name: str
    last_name: str
    position: str
    region: str           # geographic pipeline key
    hometown: str         # "City, ST" or "City, Country"
    high_school: str

    height: str
    weight: int

    # Star rating (1-5) — this is always visible
    stars: int

    # True attributes (hidden until scouted)
    true_speed: int
    true_stamina: int
    true_agility: int
    true_power: int
    true_awareness: int
    true_hands: int
    true_kicking: int
    true_kick_power: int
    true_kick_accuracy: int
    true_lateral_skill: int
    true_tackling: int

    true_potential: int     # 1-5
    true_development: str   # normal / quick / slow / late_bloomer

    # Scouted attributes — None means "not yet scouted"
    scouted_attrs: Dict[str, int] = field(default_factory=dict)
    scout_level: str = "none"  # none / basic / full

    # Recruiting state
    interest: Dict[str, int] = field(default_factory=dict)   # team_name -> 0-100
    offers: List[str] = field(default_factory=list)           # team_names that offered
    committed_to: Optional[str] = None
    signed: bool = False

    # Preferences (affect decision weights)
    prefers_prestige: float = 0.5    # 0-1: how much prestige matters
    prefers_geography: float = 0.3   # 0-1: how much being close to home matters
    prefers_nil: float = 0.2         # 0-1: how much NIL money matters
    prefers_coaching: float = 0.15   # 0-1: how much coaching quality matters
    prefers_facilities: float = 0.15 # 0-1: how much facilities/campus/location matters
    prefers_playing_time: float = 0.1  # 0-1: how much starting opportunity matters
    prefers_program_success: float = 0.3  # 0-1: how much recent W/L success matters

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def overall_estimate(self) -> int:
        """Rough overall based on star rating (what everyone can see)."""
        # 5-star → ~85-92, 4-star → ~78-84, 3-star → ~70-77, etc.
        return min(99, max(50, 55 + self.stars * 7 + (self.stars - 3) * 2))

    @property
    def true_overall(self) -> int:
        """Actual overall (only visible after full scout or after signing)."""
        w = _get_position_weights(self.position)
        total_weight = sum(w.values())
        raw = (
            self.true_speed * w["speed"]
            + self.true_stamina * w["stamina"]
            + self.true_kicking * w["kicking"]
            + self.true_lateral_skill * w["lateral_skill"]
            + self.true_tackling * w["tackling"]
            + self.true_agility * w["agility"]
            + self.true_power * w["power"]
            + self.true_awareness * w["awareness"]
            + self.true_hands * w["hands"]
            + self.true_kick_power * w["kick_power"]
            + self.true_kick_accuracy * w["kick_accuracy"]
        ) / total_weight
        return min(99, max(10, int(raw)))

    def get_visible_attrs(self) -> Dict[str, object]:
        """Return what the user can see (depends on scout level)."""
        base = {
            "name": self.full_name,
            "position": self.position,
            "stars": self.stars,
            "region": self.region,
            "hometown": self.hometown,
            "high_school": self.high_school,
            "height": self.height,
            "weight": self.weight,
        }
        if self.scout_level == "basic":
            # Reveal top-3 attributes + potential range
            base["scouted"] = dict(self.scouted_attrs)
            base["potential_range"] = _potential_range(self.true_potential)
        elif self.scout_level == "full":
            base["scouted"] = {
                "speed": self.true_speed,
                "stamina": self.true_stamina,
                "agility": self.true_agility,
                "power": self.true_power,
                "awareness": self.true_awareness,
                "hands": self.true_hands,
                "kicking": self.true_kicking,
                "kick_power": self.true_kick_power,
                "kick_accuracy": self.true_kick_accuracy,
                "lateral_skill": self.true_lateral_skill,
                "tackling": self.true_tackling,
            }
            base["potential"] = self.true_potential
            base["development"] = self.true_development
            base["true_overall"] = self.true_overall
        return base

    def to_player_card(self, team_name: str) -> PlayerCard:
        """Convert a signed recruit into a PlayerCard (Freshman)."""
        return PlayerCard(
            player_id=self.recruit_id,
            first_name=self.first_name,
            last_name=self.last_name,
            number=0,  # assigned later by roster manager
            position=self.position,
            archetype="none",  # computed later
            nationality=_region_to_nationality(self.region),
            hometown_city=self.hometown.split(",")[0].strip(),
            hometown_state=self.hometown.split(",")[-1].strip() if "," in self.hometown else "",
            hometown_country="USA" if self.region in _REGIONS else self.region.replace("_", " ").title(),
            high_school=self.high_school,
            height=self.height,
            weight=self.weight,
            year="Freshman",
            speed=self.true_speed,
            stamina=self.true_stamina,
            agility=self.true_agility,
            power=self.true_power,
            awareness=self.true_awareness,
            hands=self.true_hands,
            kicking=self.true_kicking,
            kick_power=self.true_kick_power,
            kick_accuracy=self.true_kick_accuracy,
            lateral_skill=self.true_lateral_skill,
            tackling=self.true_tackling,
            potential=self.true_potential,
            development=self.true_development,
            current_team=team_name,
            original_stars=self.stars,
            loyalty=self.prefers_geography * 0.5 + (1.0 - self.prefers_prestige) * 0.3 + 0.1,
        )

    def to_dict(self) -> dict:
        return {
            "recruit_id": self.recruit_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "region": self.region,
            "hometown": self.hometown,
            "high_school": self.high_school,
            "height": self.height,
            "weight": self.weight,
            "stars": self.stars,
            "true_overall": self.true_overall,
            "true_potential": self.true_potential,
            "true_development": self.true_development,
            "scout_level": self.scout_level,
            "committed_to": self.committed_to,
            "signed": self.signed,
            "offers": list(self.offers),
        }


def _potential_range(true_pot: int) -> str:
    """Fuzzy potential range shown after basic scouting."""
    if true_pot >= 4:
        return "High (4-5★)"
    elif true_pot >= 3:
        return "Medium (3-4★)"
    elif true_pot >= 2:
        return "Low-Medium (2-3★)"
    return "Low (1-2★)"


def _region_to_nationality(region: str) -> str:
    mapping = {
        "northeast": "American", "mid_atlantic": "American",
        "south": "American", "midwest": "American",
        "west_coast": "American", "texas_southwest": "American",
        "australian": "Australian", "canadian_english": "Canadian",
        "canadian_french": "Canadian", "new_zealand": "New Zealander",
        "uk_european": "British", "latin_american": "Mexican",
        "african": "Nigerian", "caribbean": "Jamaican",
        "nordic": "Nordic",
    }
    return mapping.get(region, "American")


# ──────────────────────────────────────────────
# RECRUIT GENERATION
# ──────────────────────────────────────────────

# Star distribution for a national class
_STAR_DISTRIBUTION = {
    5: 0.03,   # ~3% five-star
    4: 0.12,   # ~12% four-star
    3: 0.35,   # ~35% three-star
    2: 0.35,   # ~35% two-star
    1: 0.15,   # ~15% one-star (walk-on caliber)
}

# Stat generation by star tier — wide gaps prevent talent compression
_STAT_RANGES: Dict[int, Tuple[int, int]] = {
    5: (49, 63),
    4: (37, 54),
    3: (25, 45),
    2: (15, 35),
    1: (15, 25),
}

# Development trait probabilities by star tier
# "bust" = player regresses / never reaches potential (~25% of 4-5 stars combined)
# Hidden gems come from 1-3 star "quick"/"late_bloomer" traits
_DEV_BY_STARS: Dict[int, List[Tuple[str, float]]] = {
    5: [("quick", 0.30), ("normal", 0.30), ("late_bloomer", 0.10), ("slow", 0.10), ("bust", 0.20)],
    4: [("quick", 0.20), ("normal", 0.30), ("late_bloomer", 0.15), ("slow", 0.10), ("bust", 0.25)],
    3: [("normal", 0.40), ("quick", 0.15), ("late_bloomer", 0.20), ("slow", 0.15), ("bust", 0.10)],
    2: [("normal", 0.35), ("slow", 0.20), ("late_bloomer", 0.25), ("quick", 0.15), ("bust", 0.05)],
    1: [("slow", 0.25), ("normal", 0.30), ("late_bloomer", 0.30), ("quick", 0.10), ("bust", 0.05)],
}

# Simple first/last name pools for recruit generation (no external file dependency)
_FIRST_NAMES = [
    "Aaliyah", "Abby", "Ada", "Alex", "Aliyah", "Alyssa", "Amara", "Amelia",
    "Andrea", "Angel", "Anna", "Aria", "Ariana", "Ashley", "Autumn", "Avery",
    "Bailey", "Bella", "Blake", "Brielle", "Brianna", "Brooklyn", "Callie",
    "Cameron", "Carmen", "Casey", "Charlie", "Chelsea", "Claire", "Cora",
    "Dakota", "Dani", "Danica", "Delaney", "Destiny", "Diana", "Drew",
    "Elena", "Eliana", "Ella", "Emily", "Emma", "Eva", "Evelyn", "Faith",
    "Finley", "Gabriella", "Gianna", "Grace", "Hailey", "Hannah", "Harper",
    "Haven", "Hayden", "Isabella", "Ivy", "Jade", "Jamie", "Jasmine", "Jenna",
    "Jordan", "Julia", "Kai", "Kaia", "Kayla", "Kendall", "Kennedy", "Kira",
    "Layla", "Leah", "Lila", "Lily", "Logan", "Luna", "Mackenzie", "Madison",
    "Malia", "Maya", "Mia", "Morgan", "Nadia", "Natalie", "Nia", "Nicole",
    "Nora", "Olivia", "Paige", "Parker", "Peyton", "Piper", "Quinn", "Raven",
    "Reagan", "Reese", "Riley", "Sage", "Samantha", "Sara", "Savannah",
    "Sienna", "Skylar", "Sloane", "Sofia", "Sydney", "Tatum", "Taylor",
    "Tessa", "Trinity", "Valentina", "Victoria", "Vivian", "Willow", "Zara",
    "Zoe", "Maeve", "Kai", "Emery", "Rowan", "Phoenix", "Harley", "Remi",
]

_LAST_NAMES = [
    "Adams", "Allen", "Anderson", "Baker", "Barnes", "Bell", "Bennett",
    "Brooks", "Brown", "Bryant", "Burke", "Burns", "Butler", "Campbell",
    "Carter", "Chen", "Clark", "Cole", "Coleman", "Collins", "Cook", "Cooper",
    "Cox", "Cruz", "Davis", "Diaz", "Dixon", "Edwards", "Evans", "Fisher",
    "Flores", "Ford", "Foster", "Garcia", "Gibson", "Gonzalez", "Graham",
    "Gray", "Green", "Griffin", "Hall", "Hamilton", "Harris", "Hayes",
    "Henderson", "Henry", "Hernandez", "Hill", "Howard", "Hughes", "Hunter",
    "Jackson", "James", "Jenkins", "Johnson", "Jones", "Jordan", "Kelly",
    "Kennedy", "Kim", "King", "Lee", "Lewis", "Long", "Lopez", "Marshall",
    "Martin", "Martinez", "Mason", "Matthews", "McDonald", "Miller",
    "Mitchell", "Moore", "Morgan", "Morris", "Murphy", "Murray", "Nelson",
    "Nguyen", "Owens", "Parker", "Patterson", "Perez", "Perry", "Peterson",
    "Phillips", "Porter", "Powell", "Price", "Quinn", "Reed", "Reynolds",
    "Richardson", "Rivera", "Roberts", "Robinson", "Rodriguez", "Rogers",
    "Ross", "Russell", "Sanders", "Scott", "Shaw", "Simmons", "Smith",
    "Spencer", "Stewart", "Sullivan", "Taylor", "Thomas", "Thompson",
    "Torres", "Turner", "Walker", "Wallace", "Ward", "Washington", "Watson",
    "Webb", "West", "White", "Williams", "Wilson", "Wood", "Wright", "Young",
    "O'Brien", "O'Connor", "O'Neill", "McBride", "McCoy", "McLean",
    "Nakamura", "Okafor", "Patel", "Singh", "Tanaka", "Tremblay", "Volkov",
    "Wagner", "Weber", "Zhao",
]

_HOMETOWN_BY_REGION = {
    "northeast": [
        "Boston, MA", "Hartford, CT", "Portland, ME", "Burlington, VT",
        "Providence, RI", "Worcester, MA", "Bridgeport, CT", "Albany, NY",
    ],
    "mid_atlantic": [
        "Philadelphia, PA", "Baltimore, MD", "Washington, DC", "Newark, NJ",
        "Pittsburgh, PA", "Richmond, VA", "Virginia Beach, VA", "Trenton, NJ",
    ],
    "south": [
        "Atlanta, GA", "Charlotte, NC", "Nashville, TN", "Raleigh, NC",
        "Jacksonville, FL", "Tampa, FL", "New Orleans, LA", "Memphis, TN",
    ],
    "midwest": [
        "Chicago, IL", "Indianapolis, IN", "Columbus, OH", "Detroit, MI",
        "Milwaukee, WI", "Minneapolis, MN", "Kansas City, MO", "Cincinnati, OH",
    ],
    "west_coast": [
        "Los Angeles, CA", "San Francisco, CA", "Seattle, WA", "Portland, OR",
        "San Diego, CA", "Sacramento, CA", "Oakland, CA", "Spokane, WA",
    ],
    "texas_southwest": [
        "Houston, TX", "Dallas, TX", "San Antonio, TX", "Austin, TX",
        "Phoenix, AZ", "Tucson, AZ", "El Paso, TX", "Albuquerque, NM",
    ],
    "australian": [
        "Sydney, AUS", "Melbourne, AUS", "Brisbane, AUS", "Perth, AUS",
    ],
    "canadian_english": [
        "Toronto, CAN", "Vancouver, CAN", "Calgary, CAN", "Edmonton, CAN",
    ],
    "canadian_french": [
        "Montreal, CAN", "Quebec City, CAN", "Ottawa, CAN", "Laval, CAN",
    ],
    "new_zealand": [
        "Auckland, NZL", "Wellington, NZL", "Christchurch, NZL",
    ],
    "uk_european": [
        "London, GBR", "Manchester, GBR", "Dublin, IRL", "Berlin, GER",
    ],
    "latin_american": [
        "Mexico City, MEX", "Guadalajara, MEX", "São Paulo, BRA", "Buenos Aires, ARG",
    ],
    "african": [
        "Lagos, NGA", "Nairobi, KEN", "Accra, GHA", "Johannesburg, RSA",
    ],
    "nordic": [
        "Helsinki, FIN", "Stockholm, SWE", "Oslo, NOR", "Tampere, FIN",
        "Gothenburg, SWE", "Bergen, NOR", "Malmö, SWE", "Trondheim, NOR",
    ],
    "caribbean": [
        "Kingston, JAM", "Port of Spain, TTO", "Bridgetown, BRB", "Nassau, BAH",
        "Port-au-Prince, HAI", "Santo Domingo, DOM", "San Juan, PRI", "Georgetown, GUY",
    ],
}

_HS_SUFFIXES = [
    "High School", "Academy", "Prep", "Central High School",
    "Regional High School", "Christian Academy", "Catholic High School",
]


def _generate_recruit_name(region: str, rng: random.Random) -> Tuple[str, str]:
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    return first, last


def _generate_hometown(region: str, rng: random.Random) -> str:
    towns = _HOMETOWN_BY_REGION.get(region, _HOMETOWN_BY_REGION["midwest"])
    return rng.choice(towns)


def _generate_high_school(hometown: str, rng: random.Random) -> str:
    city = hometown.split(",")[0].strip()
    suffix = rng.choice(_HS_SUFFIXES)
    return f"{city} {suffix}"


def generate_single_recruit(
    recruit_id: str,
    position: Optional[str] = None,
    stars: Optional[int] = None,
    region: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Recruit:
    """Generate a single recruit with randomised attributes."""
    if rng is None:
        rng = random.Random()

    if position is None:
        position = _pick_position(rng)
    if region is None:
        region = _pick_region(rng)

    # Star rating
    if stars is None:
        star_vals = list(_STAR_DISTRIBUTION.keys())
        star_wts = list(_STAR_DISTRIBUTION.values())
        stars = rng.choices(star_vals, weights=star_wts, k=1)[0]

    lo, hi = _STAT_RANGES[stars]
    first, last = _generate_recruit_name(region, rng)
    hometown = _generate_hometown(region, rng)
    hs = _generate_high_school(hometown, rng)

    # Generate base stats in the star range
    def _stat() -> int:
        return rng.randint(lo, hi)

    # Position-specific boosts
    speed = _stat()
    stamina = _stat()
    agility = _stat()
    power = _stat()
    awareness = _stat()
    hands = _stat()
    kicking = _stat()
    kick_power = _stat()
    kick_accuracy = _stat()
    lateral_skill = _stat()
    tackling = _stat()

    if position in ("Viper", "Halfback", "Wingback", "Slotback"):
        speed = min(85, speed + rng.randint(2, 6))
        lateral_skill = min(85, lateral_skill + rng.randint(2, 5))
        agility = min(85, agility + rng.randint(1, 4))
    elif position in ("Offensive Line", "Defensive Line"):
        tackling = min(85, tackling + rng.randint(3, 7))
        power = min(85, power + rng.randint(3, 7))
        speed = max(55, speed - rng.randint(2, 5))
    elif position == "Zeroback":
        awareness = min(85, awareness + rng.randint(3, 6))
        kick_power = min(85, kick_power + rng.randint(2, 5))
        kick_accuracy = min(85, kick_accuracy + rng.randint(2, 5))
    elif position == "Keeper":
        speed = min(85, speed + rng.randint(2, 6))
        tackling = min(85, tackling + rng.randint(3, 7))
        awareness = min(85, awareness + rng.randint(2, 5))
        hands = min(85, hands + rng.randint(2, 5))

    # Potential and development
    true_potential = rng.randint(max(1, stars - 1), min(5, stars + 1))
    dev_options, dev_weights = zip(*_DEV_BY_STARS[stars])
    true_dev = rng.choices(dev_options, weights=dev_weights, k=1)[0]

    # Height / weight
    if position in ("Offensive Line", "Defensive Line"):
        ht_in = rng.randint(69, 75)
        wt = rng.randint(185, 215)
    elif position == "Viper":
        ht_in = rng.randint(65, 72)
        wt = rng.randint(155, 185)
    else:
        ht_in = rng.randint(66, 73)
        wt = rng.randint(160, 200)
    height = f"{ht_in // 12}-{ht_in % 12}"

    # Decision preferences (randomised personality)
    pres = rng.uniform(0.2, 0.6)
    geo = rng.uniform(0.1, 0.4)
    nil_pref = rng.uniform(0.01, 0.08)
    prog_success = rng.uniform(0.15, 0.45)
    fac = rng.uniform(0.05, 0.25)
    # Lower-star recruits care more about playing time opportunity
    pt_base = 0.05 if stars >= 4 else (0.15 if stars >= 3 else 0.25)
    pt = rng.uniform(pt_base * 0.5, pt_base * 1.5)

    return Recruit(
        recruit_id=recruit_id,
        first_name=first,
        last_name=last,
        position=position,
        region=region,
        hometown=hometown,
        high_school=hs,
        height=height,
        weight=wt,
        stars=stars,
        true_speed=speed,
        true_stamina=stamina,
        true_agility=agility,
        true_power=power,
        true_awareness=awareness,
        true_hands=hands,
        true_kicking=kicking,
        true_kick_power=kick_power,
        true_kick_accuracy=kick_accuracy,
        true_lateral_skill=lateral_skill,
        true_tackling=tackling,
        true_potential=true_potential,
        true_development=true_dev,
        prefers_prestige=pres,
        prefers_geography=geo,
        prefers_nil=nil_pref,
        prefers_facilities=fac,
        prefers_playing_time=pt,
        prefers_program_success=prog_success,
    )


def generate_recruit_class(
    year: int,
    size: int = 300,
    rng: Optional[random.Random] = None,
) -> List[Recruit]:
    """
    Generate a full national recruiting class.

    Args:
        year: The recruiting year (e.g. 2027).
        size: Number of recruits in the pool.
        rng:  Seeded Random for reproducibility.

    Returns:
        List of Recruit objects sorted by star rating (descending).
    """
    if rng is None:
        rng = random.Random(year)

    pool: List[Recruit] = []
    for i in range(size):
        rid = f"REC-{year}-{i:04d}"
        recruit = generate_single_recruit(recruit_id=rid, rng=rng)
        pool.append(recruit)

    pool.sort(key=lambda r: (-r.stars, -r.true_overall))
    return pool


# ──────────────────────────────────────────────
# SCOUTING
# ──────────────────────────────────────────────

def scout_recruit(
    recruit: Recruit,
    level: str = "basic",
    rng: Optional[random.Random] = None,
    scouting_error: int = 3,
) -> Dict[str, object]:
    """
    Scout a recruit and reveal attributes.

    Args:
        recruit: The Recruit to scout.
        level:   "basic" → top-3 attributes + fuzzy potential.
                 "full"  → all attributes + exact potential + development trait.
        rng:     Random instance for noise on basic scout.

    Returns:
        The visible attributes dict after scouting.
    """
    if rng is None:
        rng = random.Random()

    if level == "full" or recruit.scout_level == "full":
        recruit.scout_level = "full"
        recruit.scouted_attrs = {
            "speed": recruit.true_speed,
            "stamina": recruit.true_stamina,
            "agility": recruit.true_agility,
            "power": recruit.true_power,
            "awareness": recruit.true_awareness,
            "hands": recruit.true_hands,
            "kicking": recruit.true_kicking,
            "kick_power": recruit.true_kick_power,
            "kick_accuracy": recruit.true_kick_accuracy,
            "lateral_skill": recruit.true_lateral_skill,
            "tackling": recruit.true_tackling,
        }
    elif level == "basic":
        if recruit.scout_level == "none":
            recruit.scout_level = "basic"
        # Reveal top 3 attributes with slight noise (±3)
        all_attrs = {
            "speed": recruit.true_speed,
            "stamina": recruit.true_stamina,
            "agility": recruit.true_agility,
            "power": recruit.true_power,
            "awareness": recruit.true_awareness,
            "hands": recruit.true_hands,
            "kicking": recruit.true_kicking,
            "kick_power": recruit.true_kick_power,
            "kick_accuracy": recruit.true_kick_accuracy,
            "lateral_skill": recruit.true_lateral_skill,
            "tackling": recruit.true_tackling,
        }
        top3 = sorted(all_attrs.items(), key=lambda x: x[1], reverse=True)[:3]
        for attr_name, true_val in top3:
            noise = rng.randint(-scouting_error, scouting_error)
            recruit.scouted_attrs[attr_name] = max(10, min(99, true_val + noise))

    return recruit.get_visible_attrs()


# ──────────────────────────────────────────────
# RECRUITING BOARD
# ──────────────────────────────────────────────

@dataclass
class RecruitingBoard:
    """
    A team's recruiting board for one offseason.

    Manages scholarship offers, scouting budget, and commitment tracking.
    """
    team_name: str
    scholarships_available: int = 8        # open roster spots
    scouting_points: int = 30              # spend 1 per basic scout, 3 per full scout
    max_offers: int = 15                   # can't offer more than this

    # State
    watchlist: List[str] = field(default_factory=list)     # recruit_ids
    offered: List[str] = field(default_factory=list)       # recruit_ids we offered
    committed: List[str] = field(default_factory=list)     # recruit_ids committed to us
    signed: List[str] = field(default_factory=list)        # recruit_ids who signed

    def can_scout(self, level: str = "basic") -> bool:
        cost = 1 if level == "basic" else 3
        return self.scouting_points >= cost

    def scout(
        self,
        recruit: Recruit,
        level: str = "basic",
        rng: Optional[random.Random] = None,
        scouting_error: int = 3,
    ) -> Optional[Dict[str, object]]:
        """Scout a recruit, spending scouting points."""
        cost = 1 if level == "basic" else 3
        if self.scouting_points < cost:
            return None
        self.scouting_points -= cost
        if recruit.recruit_id not in self.watchlist:
            self.watchlist.append(recruit.recruit_id)
        return scout_recruit(recruit, level=level, rng=rng, scouting_error=scouting_error)

    def offer(self, recruit: Recruit) -> bool:
        """
        Extend a scholarship offer to a recruit.
        Returns True if offer was made, False if at limit.
        """
        if len(self.offered) >= self.max_offers:
            return False
        if recruit.recruit_id in self.offered:
            return False  # already offered
        if recruit.committed_to is not None:
            return False  # already committed elsewhere

        self.offered.append(recruit.recruit_id)
        recruit.offers.append(self.team_name)
        return True

    def withdraw_offer(self, recruit: Recruit) -> bool:
        """Withdraw an offer to a recruit."""
        if recruit.recruit_id not in self.offered:
            return False
        self.offered.remove(recruit.recruit_id)
        if self.team_name in recruit.offers:
            recruit.offers.remove(self.team_name)
        return True

    def get_committed_count(self) -> int:
        return len(self.committed)

    def has_room(self) -> bool:
        return len(self.committed) < self.scholarships_available

    def to_dict(self) -> dict:
        return {
            "team_name": self.team_name,
            "scholarships_available": self.scholarships_available,
            "scouting_points": self.scouting_points,
            "max_offers": self.max_offers,
            "watchlist": list(self.watchlist),
            "offered": list(self.offered),
            "committed": list(self.committed),
            "signed": list(self.signed),
        }


# ──────────────────────────────────────────────
# RECRUIT DECISION SIMULATION
# ──────────────────────────────────────────────

def _compute_team_score(
    recruit: Recruit,
    team_name: str,
    team_prestige: int,
    team_region: str,
    nil_offer: float,
    max_nil_in_class: float,
    rng: random.Random,
    coaching_score: float = 0.0,
    infrastructure: Optional[Dict[str, int]] = None,
    position_depth: int = 0,
    program_success: int = 0,
) -> float:
    """
    Compute how attractive a team is to a recruit.

    Args:
        infrastructure: Dict with keys facilities, campus_life, location,
                        coaching_development, nil_program (each 1-10).
        position_depth: How many players at recruit's position are already
                        committed/rostered.  Higher = less playing time.

    Returns a score 0-100.
    """
    # Prestige component (0-100)
    prestige_score = team_prestige

    # Geography component (0-100)
    if team_region == recruit.region:
        geo_score = 100.0
    elif team_region in _REGIONS and recruit.region in _REGIONS:
        geo_score = 50.0   # same country, different region
    else:
        geo_score = 20.0   # international mismatch

    # NIL component (0-100)
    if max_nil_in_class > 0:
        nil_score = (nil_offer / max_nil_in_class) * 100.0
    else:
        nil_score = 50.0

    # Coaching component (0-100): HC recruiting attribute normalized
    coach_score = coaching_score * 100.0  # coaching_score is 0-1

    # Infrastructure component (0-100): average of facilities, campus_life, location
    infra = infrastructure or {}
    if infra:
        infra_avg = (
            infra.get("facilities", 5)
            + infra.get("campus_life", 5)
            + infra.get("location", 5)
        ) / 3.0
        infra_score = infra_avg * 10.0  # 1-10 → 10-100
    else:
        infra_score = 50.0

    # Playing time component (0-100): fewer players at position = more opportunity
    # position_depth 0-1 = wide open (100), 2-3 = normal (60-80), 4+ = crowded (20-40)
    if position_depth <= 1:
        playing_time_score = 100.0
    elif position_depth == 2:
        playing_time_score = 80.0
    elif position_depth == 3:
        playing_time_score = 60.0
    elif position_depth == 4:
        playing_time_score = 40.0
    else:
        playing_time_score = max(10.0, 100.0 - position_depth * 18.0)

    # Program success component (0-100): recent W/L success, distinct from brand prestige
    program_success_score = min(100, team_prestige * 0.6 + rng.uniform(10, 30))

    # Random factor (personality noise)
    noise = rng.uniform(-8, 8)

    score = (
        recruit.prefers_prestige * prestige_score
        + recruit.prefers_geography * geo_score
        + recruit.prefers_nil * nil_score
        + recruit.prefers_coaching * coach_score
        + recruit.prefers_facilities * infra_score
        + recruit.prefers_playing_time * playing_time_score
        + recruit.prefers_program_success * program_success_score
        + noise
    )
    return max(0.0, min(100.0, score))


def simulate_recruit_decisions(
    pool: List[Recruit],
    team_boards: Dict[str, RecruitingBoard],
    team_prestige: Dict[str, int],
    team_regions: Dict[str, str],
    nil_offers: Dict[str, Dict[str, float]],
    rng: Optional[random.Random] = None,
    team_coaching_scores: Optional[Dict[str, float]] = None,
    coaching_prestige_bonus: Optional[Dict[str, int]] = None,
    team_infrastructure: Optional[Dict[str, Dict[str, int]]] = None,
    team_rosters: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, List[Recruit]]:
    """
    Simulate all recruits making their decisions.

    Processes recruits from highest-star to lowest. Each recruit picks
    the offering team with the best score (if any offers exist).

    Roster-aware: recruits consider position depth when deciding. If a
    team already has many players at the recruit's position, the recruit
    sees less playing time opportunity and may choose a program where
    they can start.

    Args:
        pool:                Full recruit pool.
        team_boards:         Dict of team_name -> RecruitingBoard.
        team_prestige:       Dict of team_name -> prestige (0-100).
        team_regions:        Dict of team_name -> region key.
        nil_offers:          Dict of team_name -> { recruit_id: dollar_amount }.
        rng:                 Seeded Random.
        team_infrastructure: Dict of team_name -> {facilities, campus_life, ...}.
        team_rosters:        Dict of team_name -> list of player dicts with 'position' key.

    Returns:
        Dict of team_name -> list of signed Recruit objects.
    """
    if rng is None:
        rng = random.Random()

    # Find max NIL offer across the whole class for normalisation
    max_nil = 1.0
    for team_nil in nil_offers.values():
        for amt in team_nil.values():
            if amt > max_nil:
                max_nil = amt

    signed_by_team: Dict[str, List[Recruit]] = {tn: [] for tn in team_boards}

    # Build position depth counts per team (existing roster + already committed)
    position_counts: Dict[str, Dict[str, int]] = {}
    for tn in team_boards:
        counts: Dict[str, int] = {}
        # Count existing roster players by position
        if team_rosters and tn in team_rosters:
            for p in team_rosters[tn]:
                pos = p.get("position", "")
                counts[pos] = counts.get(pos, 0) + 1
        position_counts[tn] = counts

    infra = team_infrastructure or {}

    # Process by star rating (top recruits commit first)
    sorted_pool = sorted(pool, key=lambda r: (-r.stars, -r.true_overall))

    for recruit in sorted_pool:
        if recruit.committed_to is not None:
            continue
        if not recruit.offers:
            continue

        best_score = -1.0
        best_team = None

        for team_name in recruit.offers:
            board = team_boards.get(team_name)
            if board is None or not board.has_room():
                continue

            nil_amt = nil_offers.get(team_name, {}).get(recruit.recruit_id, 0.0)
            cs = (team_coaching_scores or {}).get(team_name, 0.0)
            p_bonus = (coaching_prestige_bonus or {}).get(team_name, 0)
            pos_depth = position_counts.get(team_name, {}).get(recruit.position, 0)
            score = _compute_team_score(
                recruit=recruit,
                team_name=team_name,
                team_prestige=min(100, team_prestige.get(team_name, 50) + p_bonus),
                team_region=team_regions.get(team_name, "midwest"),
                nil_offer=nil_amt,
                max_nil_in_class=max_nil,
                rng=rng,
                coaching_score=cs,
                infrastructure=infra.get(team_name),
                position_depth=pos_depth,
                program_success=team_prestige.get(team_name, 50),
            )
            if score > best_score:
                best_score = score
                best_team = team_name

        if best_team is not None:
            recruit.committed_to = best_team
            recruit.signed = True
            board = team_boards[best_team]
            board.committed.append(recruit.recruit_id)
            board.signed.append(recruit.recruit_id)
            signed_by_team[best_team].append(recruit)
            # Update position depth so next recruit sees accurate counts
            pos_counts = position_counts.get(best_team, {})
            pos_counts[recruit.position] = pos_counts.get(recruit.position, 0) + 1
            position_counts[best_team] = pos_counts

    return signed_by_team


# ──────────────────────────────────────────────
# AI RECRUITING (for CPU-controlled teams)
# ──────────────────────────────────────────────

def auto_recruit_team(
    team_name: str,
    pool: List[Recruit],
    team_prestige: int,
    team_region: str,
    scholarships: int = 8,
    nil_budget: float = 500_000.0,
    rng: Optional[random.Random] = None,
    current_roster: Optional[List[Dict]] = None,
) -> Tuple[RecruitingBoard, Dict[str, float]]:
    """
    Auto-recruit for a CPU team. Returns the board and NIL offers dict.

    Strategy:
    - Prioritise recruits from home region
    - Higher-prestige teams target higher-star recruits
    - Deprioritise positions where the team is already deep
    - Spread NIL budget across top targets
    """
    if rng is None:
        rng = random.Random()

    board = RecruitingBoard(
        team_name=team_name,
        scholarships_available=scholarships,
        scouting_points=100,  # AI gets enough to scout freely
    )

    nil_offers: Dict[str, float] = {}

    # Count existing roster depth by position
    pos_depth: Dict[str, int] = {}
    if current_roster:
        for p in current_roster:
            pos = p.get("position", "")
            pos_depth[pos] = pos_depth.get(pos, 0) + 1

    # Filter available recruits (not yet committed)
    available = [r for r in pool if r.committed_to is None and not r.signed]

    # Score each recruit for this team
    scored: List[Tuple[float, Recruit]] = []
    for recruit in available:
        # Prestige-based targeting: higher prestige teams aim higher
        star_match = 1.0
        if team_prestige >= 80 and recruit.stars >= 4:
            star_match = 1.5
        elif team_prestige >= 60 and recruit.stars >= 3:
            star_match = 1.3
        elif team_prestige < 40 and recruit.stars <= 3:
            star_match = 1.2

        # Geography bonus
        geo = 1.4 if recruit.region == team_region else 1.0

        # Position need: deprioritise positions we're already stacked at
        depth = pos_depth.get(recruit.position, 0)
        if depth >= 5:
            need_mult = 0.6   # way overstocked — barely interested
        elif depth >= 4:
            need_mult = 0.75  # full — mild interest
        elif depth >= 3:
            need_mult = 0.9   # adequate — slight discount
        else:
            need_mult = 1.1   # real need — bonus interest

        # Overall desirability
        base = recruit.stars * 20 + recruit.true_overall * 0.3
        score = base * star_match * geo * need_mult + rng.uniform(-5, 5)
        scored.append((score, recruit))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Offer to top N candidates (up to max_offers)
    offer_count = min(board.max_offers, len(scored))
    for i in range(offer_count):
        _, recruit = scored[i]
        board.offer(recruit)

        # Allocate NIL: top target gets ~30%, then decreasing
        if i < scholarships:
            share = nil_budget * (0.30 if i == 0 else 0.15 / max(1, i))
            nil_offers[recruit.recruit_id] = share

    return board, nil_offers


def run_full_recruiting_cycle(
    year: int,
    team_names: List[str],
    human_team: str,
    human_board: Optional[RecruitingBoard],
    human_nil_offers: Optional[Dict[str, float]],
    team_prestige: Dict[str, int],
    team_regions: Dict[str, str],
    scholarships_per_team: Dict[str, int],
    nil_budgets: Dict[str, float],
    pool_size: int = 300,
    rng: Optional[random.Random] = None,
    team_coaching_scores: Optional[Dict[str, float]] = None,
    coaching_prestige_bonus: Optional[Dict[str, int]] = None,
    team_infrastructure: Optional[Dict[str, Dict[str, int]]] = None,
    team_rosters: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, object]:
    """
    Run a complete recruiting cycle (for use by Dynasty.advance_season).

    Args:
        team_infrastructure: Dict of team_name -> {facilities, campus_life, ...}.
        team_rosters:        Dict of team_name -> list of player dicts for depth calc.

    Returns:
        {
            "pool": List[Recruit],
            "signed": { team_name: [Recruit, ...] },
            "boards": { team_name: RecruitingBoard },
            "class_rankings": [(team_name, avg_stars, count), ...],
        }
    """
    if rng is None:
        rng = random.Random(year)

    pool = generate_recruit_class(year=year, size=pool_size, rng=rng)

    boards: Dict[str, RecruitingBoard] = {}
    all_nil: Dict[str, Dict[str, float]] = {}

    for team in team_names:
        if team == human_team and human_board is not None:
            boards[team] = human_board
            all_nil[team] = human_nil_offers or {}
        else:
            roster = (team_rosters or {}).get(team)
            board, nil = auto_recruit_team(
                team_name=team,
                pool=pool,
                team_prestige=team_prestige.get(team, 50),
                team_region=team_regions.get(team, "midwest"),
                scholarships=scholarships_per_team.get(team, 8),
                nil_budget=nil_budgets.get(team, 500_000.0),
                rng=rng,
                current_roster=roster,
            )
            boards[team] = board
            all_nil[team] = nil

    signed = simulate_recruit_decisions(
        pool=pool,
        team_boards=boards,
        team_prestige=team_prestige,
        team_regions=team_regions,
        nil_offers=all_nil,
        rng=rng,
        team_coaching_scores=team_coaching_scores,
        coaching_prestige_bonus=coaching_prestige_bonus,
        team_infrastructure=team_infrastructure,
        team_rosters=team_rosters,
    )

    # Class rankings
    rankings: List[Tuple[str, float, int]] = []
    for team, recruits in signed.items():
        if recruits:
            avg = sum(r.stars for r in recruits) / len(recruits)
            rankings.append((team, round(avg, 2), len(recruits)))
    rankings.sort(key=lambda x: (-x[1], -x[2]))

    return {
        "pool": pool,
        "signed": signed,
        "boards": boards,
        "class_rankings": rankings,
    }


# ──────────────────────────────────────────────
# HIGH SCHOOL RECRUITING PIPELINE
# ──────────────────────────────────────────────

_HS_GRADES = ["9th", "10th", "11th", "12th"]

# Star visibility by grade — younger players have less reliable scouting
_SCOUTING_NOISE_BY_GRADE: Dict[str, int] = {
    "9th": 8,   # huge uncertainty
    "10th": 5,
    "11th": 3,
    "12th": 1,  # nearly accurate
}

# What fraction of true attributes are visible per grade
_ATTRS_VISIBLE_BY_GRADE: Dict[str, int] = {
    "9th": 2,    # only top-2 attrs visible
    "10th": 4,   # top-4
    "11th": 7,   # top-7
    "12th": 11,  # all 11
}

# Chance of a star "miss" (underrated or overrated) by grade
_STAR_MISS_CHANCE: Dict[str, float] = {
    "9th": 0.40,   # 40% chance star rating is off by 1-2
    "10th": 0.30,
    "11th": 0.15,
    "12th": 0.05,
}


@dataclass
class HSProspect:
    """A high school prospect tracked across multiple years.

    Unlike a Recruit (which exists for one recruiting cycle), an HSProspect
    persists across 4 HS years. Their scouted_stars and visible attributes
    become more accurate as they age from 9th to 12th grade.
    """
    recruit: Recruit
    grade: str                   # "9th", "10th", "11th", "12th"
    scouted_stars: int           # what evaluators *think* stars are (may differ from true)
    national_rank: int = 0       # rank within national class
    position_rank: int = 0       # rank within position group
    regional_rank: int = 0       # rank within region
    watched_by: List[str] = field(default_factory=list)   # team names tracking this player
    development_notes: List[str] = field(default_factory=list)
    breakout: bool = False       # flagged as potential breakout (sleeper)

    @property
    def is_alpha(self) -> bool:
        """An 'alpha' prospect: scouted as 4-5 star OR true overall 80+."""
        return self.scouted_stars >= 4 or self.recruit.true_overall >= 80

    @property
    def is_sleeper(self) -> bool:
        """Underrated: scouted low but true talent is much higher."""
        return (self.scouted_stars <= 2 and self.recruit.true_overall >= 75) or self.breakout

    def to_dict(self) -> dict:
        d = self.recruit.to_dict()
        d["grade"] = self.grade
        d["scouted_stars"] = self.scouted_stars
        d["national_rank"] = self.national_rank
        d["position_rank"] = self.position_rank
        d["regional_rank"] = self.regional_rank
        d["watched_by"] = list(self.watched_by)
        d["is_alpha"] = self.is_alpha
        d["is_sleeper"] = self.is_sleeper
        d["development_notes"] = list(self.development_notes)
        d["breakout"] = self.breakout
        return d


def _apply_scouting_noise(true_stars: int, grade: str, rng: random.Random) -> int:
    """Determine what evaluators think the star rating is for this grade level."""
    miss_chance = _STAR_MISS_CHANCE.get(grade, 0.05)
    if rng.random() < miss_chance:
        # Misrate: shift by ±1 or ±2
        shift = rng.choice([-2, -1, 1, 2])
        # Overrating is slightly more common for younger players
        if grade in ("9th", "10th") and rng.random() < 0.3:
            shift = abs(shift)  # bias toward overrating
        return max(1, min(5, true_stars + shift))
    return true_stars


def _apply_hs_development(
    prospect: HSProspect,
    rng: random.Random,
) -> List[str]:
    """Simulate one year of HS development — attributes may shift.

    Returns list of development note strings.
    """
    recruit = prospect.recruit
    notes: List[str] = []
    dev_trait = recruit.true_development

    # Base improvement chance by development trait
    improve_chance = {
        "quick": 0.70,
        "normal": 0.50,
        "slow": 0.30,
        "late_bloomer": 0.25 if prospect.grade in ("9th", "10th") else 0.65,
    }.get(dev_trait, 0.50)

    # How much attributes can change (younger = more volatile)
    max_gain = {"9th": 5, "10th": 4, "11th": 3, "12th": 2}.get(prospect.grade, 2)
    max_loss = {"9th": 3, "10th": 2, "11th": 1, "12th": 0}.get(prospect.grade, 1)

    attrs = [
        "true_speed", "true_stamina", "true_agility", "true_power",
        "true_awareness", "true_hands", "true_kicking", "true_kick_power",
        "true_kick_accuracy", "true_lateral_skill", "true_tackling",
    ]

    improved_any = False
    for attr in attrs:
        current = getattr(recruit, attr)
        if rng.random() < improve_chance:
            gain = rng.randint(1, max_gain)
            new_val = min(99, current + gain)
            setattr(recruit, attr, new_val)
            if gain >= 3:
                improved_any = True
        elif rng.random() < 0.10 and max_loss > 0:
            # Small regression chance (injury, laziness, etc.)
            loss = rng.randint(1, max_loss)
            setattr(recruit, attr, max(10, current - loss))

    if improved_any:
        notes.append(f"Notable improvement during {prospect.grade} grade year")

    # Breakout detection: late_bloomer or slow developer suddenly jumps
    if dev_trait in ("late_bloomer", "slow") and prospect.grade in ("11th", "12th"):
        if recruit.true_overall >= 78 and prospect.scouted_stars <= 3:
            prospect.breakout = True
            notes.append("BREAKOUT: True talent emerging — potential hidden gem")

    # Potential can shift slightly for younger players
    if prospect.grade in ("9th", "10th") and rng.random() < 0.15:
        shift = rng.choice([-1, 1])
        recruit.true_potential = max(1, min(5, recruit.true_potential + shift))
        if shift > 0:
            notes.append("Potential ceiling raised")

    return notes


def generate_hs_class(
    grade: str,
    size: int = 300,
    rng: Optional[random.Random] = None,
    seed: Optional[int] = None,
) -> List[HSProspect]:
    """Generate a high school class at a specific grade level.

    Args:
        grade: "9th", "10th", "11th", or "12th".
        size: Number of prospects in the class.
        rng: Seeded Random for reproducibility.
        seed: Alternative to rng — creates Random(seed).

    Returns:
        List of HSProspect objects sorted by scouted_stars descending.
    """
    if rng is None:
        rng = random.Random(seed if seed is not None else hash(grade))

    prospects: List[HSProspect] = []
    for i in range(size):
        rid = f"HS-{grade}-{i:04d}"
        recruit = generate_single_recruit(recruit_id=rid, rng=rng)
        scouted = _apply_scouting_noise(recruit.stars, grade, rng)
        prospect = HSProspect(recruit=recruit, grade=grade, scouted_stars=scouted)
        prospects.append(prospect)

    # Rank nationally, by position, and by region
    _rank_hs_class(prospects)

    return prospects


def _rank_hs_class(prospects: List[HSProspect]) -> None:
    """Assign national, position, and regional ranks based on scouted_stars.

    Modifies prospects in-place and sorts by national rank.
    """
    # National ranking: scouted_stars desc, then recruit.overall_estimate desc
    prospects.sort(key=lambda p: (-p.scouted_stars, -p.recruit.overall_estimate))
    for i, p in enumerate(prospects):
        p.national_rank = i + 1

    # Position ranking
    by_pos: Dict[str, List[HSProspect]] = {}
    for p in prospects:
        by_pos.setdefault(p.recruit.position, []).append(p)
    for pos_list in by_pos.values():
        pos_list.sort(key=lambda p: (-p.scouted_stars, -p.recruit.overall_estimate))
        for i, p in enumerate(pos_list):
            p.position_rank = i + 1

    # Regional ranking
    by_region: Dict[str, List[HSProspect]] = {}
    for p in prospects:
        by_region.setdefault(p.recruit.region, []).append(p)
    for region_list in by_region.values():
        region_list.sort(key=lambda p: (-p.scouted_stars, -p.recruit.overall_estimate))
        for i, p in enumerate(region_list):
            p.regional_rank = i + 1


@dataclass
class HSRecruitingPipeline:
    """Four-year high school recruiting pipeline.

    Pre-generates classes for 9th through 12th grade so dynasty mode
    can display upcoming talent and track prospects over time.  Each
    offseason, classes advance one grade (9th→10th→...→12th→eligible)
    and a new 9th grade class is generated.
    """
    classes: Dict[str, List[HSProspect]] = field(default_factory=dict)

    def generate_initial_pipeline(
        self,
        base_seed: int = 0,
        size_per_class: int = 300,
    ) -> None:
        """Generate all four HS grade classes from scratch."""
        for i, grade in enumerate(_HS_GRADES):
            rng = random.Random(base_seed + i * 1000)
            self.classes[grade] = generate_hs_class(
                grade=grade, size=size_per_class, rng=rng,
            )

    def advance_year(
        self,
        new_9th_seed: int = 0,
        size: int = 300,
        rng: Optional[random.Random] = None,
    ) -> List[HSProspect]:
        """Advance all classes by one year.

        - 12th graders graduate → returned as the eligible recruiting class
        - 11th → 12th, 10th → 11th, 9th → 10th (with development applied)
        - A fresh 9th grade class is generated

        Returns:
            The graduated 12th-grade class (ready for college recruiting).
        """
        if rng is None:
            rng = random.Random(new_9th_seed)

        # Graduate 12th graders
        graduates = self.classes.pop("12th", [])

        # Advance each class
        grade_progression = [("11th", "12th"), ("10th", "11th"), ("9th", "10th")]
        for old_grade, new_grade in grade_progression:
            prospects = self.classes.pop(old_grade, [])
            for p in prospects:
                p.grade = new_grade
                # Apply development and update scouted stars
                notes = _apply_hs_development(p, rng)
                p.development_notes.extend(notes)
                # Re-scout: star accuracy improves with grade
                p.scouted_stars = _apply_scouting_noise(
                    p.recruit.stars, new_grade, rng,
                )
            _rank_hs_class(prospects)
            self.classes[new_grade] = prospects

        # Generate fresh 9th graders
        self.classes["9th"] = generate_hs_class(
            grade="9th", size=size, rng=random.Random(new_9th_seed),
        )

        return graduates

    def get_top_prospects(
        self,
        n: int = 25,
        grade: Optional[str] = None,
        position: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[HSProspect]:
        """Get top-ranked prospects with optional filters.

        Args:
            n: Number of prospects to return.
            grade: Filter to a specific grade ("9th", "10th", etc.).
            position: Filter to a specific position.
            region: Filter to a specific region.

        Returns:
            Top N prospects matching filters, sorted by scouted stars/rank.
        """
        candidates: List[HSProspect] = []
        grades = [grade] if grade else _HS_GRADES
        for g in grades:
            candidates.extend(self.classes.get(g, []))

        if position:
            candidates = [p for p in candidates if p.recruit.position == position]
        if region:
            candidates = [p for p in candidates if p.recruit.region == region]

        candidates.sort(key=lambda p: (-p.scouted_stars, -p.recruit.overall_estimate))
        return candidates[:n]

    def get_alpha_prospects(self, grade: Optional[str] = None) -> List[HSProspect]:
        """Get all alpha-rated prospects (4-5 star or 80+ true overall)."""
        return [
            p for p in self.get_top_prospects(n=9999, grade=grade)
            if p.is_alpha
        ]

    def get_sleepers(self, grade: Optional[str] = None) -> List[HSProspect]:
        """Get potential sleeper prospects (underrated talent)."""
        candidates: List[HSProspect] = []
        grades = [grade] if grade else _HS_GRADES
        for g in grades:
            candidates.extend(self.classes.get(g, []))
        return [p for p in candidates if p.is_sleeper]

    def get_rankings_board(self, grade: str, top_n: int = 50) -> List[dict]:
        """Get a rankings board for display — like a top-50 list.

        Returns list of dicts with visible scouting information appropriate
        for the grade level (more hidden for younger players).
        """
        prospects = self.get_top_prospects(n=top_n, grade=grade)
        noise = _SCOUTING_NOISE_BY_GRADE.get(grade, 3)
        n_visible = _ATTRS_VISIBLE_BY_GRADE.get(grade, 11)
        board: List[dict] = []

        for p in prospects:
            entry: dict = {
                "rank": p.national_rank,
                "name": p.recruit.full_name,
                "position": p.recruit.position,
                "scouted_stars": p.scouted_stars,
                "grade": p.grade,
                "hometown": p.recruit.hometown,
                "high_school": p.recruit.high_school,
                "region": p.recruit.region,
                "height": p.recruit.height,
                "weight": p.recruit.weight,
                "position_rank": p.position_rank,
                "regional_rank": p.regional_rank,
                "is_alpha": p.is_alpha,
            }
            # Show limited attributes based on grade level
            all_attrs = {
                "speed": p.recruit.true_speed,
                "stamina": p.recruit.true_stamina,
                "agility": p.recruit.true_agility,
                "power": p.recruit.true_power,
                "awareness": p.recruit.true_awareness,
                "hands": p.recruit.true_hands,
                "kicking": p.recruit.true_kicking,
                "kick_power": p.recruit.true_kick_power,
                "kick_accuracy": p.recruit.true_kick_accuracy,
                "lateral_skill": p.recruit.true_lateral_skill,
                "tackling": p.recruit.true_tackling,
            }
            sorted_attrs = sorted(all_attrs.items(), key=lambda x: x[1], reverse=True)
            visible: Dict[str, int] = {}
            for attr_name, true_val in sorted_attrs[:n_visible]:
                # Add grade-appropriate noise
                noisy = true_val + random.randint(-noise, noise)
                visible[attr_name] = max(10, min(99, noisy))
            entry["visible_attributes"] = visible

            if p.breakout:
                entry["flag"] = "BREAKOUT"
            board.append(entry)

        return board

    def to_dict(self) -> dict:
        return {
            grade: [p.to_dict() for p in prospects]
            for grade, prospects in self.classes.items()
        }

    def pipeline_summary(self) -> dict:
        """Summary stats for each grade in the pipeline."""
        summary: dict = {}
        for grade in _HS_GRADES:
            prospects = self.classes.get(grade, [])
            if not prospects:
                summary[grade] = {"count": 0}
                continue
            avg_stars = sum(p.scouted_stars for p in prospects) / len(prospects)
            five_stars = sum(1 for p in prospects if p.scouted_stars == 5)
            four_stars = sum(1 for p in prospects if p.scouted_stars == 4)
            alphas = sum(1 for p in prospects if p.is_alpha)
            sleepers = sum(1 for p in prospects if p.is_sleeper)
            summary[grade] = {
                "count": len(prospects),
                "avg_scouted_stars": round(avg_stars, 2),
                "five_star": five_stars,
                "four_star": four_stars,
                "alpha_count": alphas,
                "sleeper_count": sleepers,
            }
        return summary
