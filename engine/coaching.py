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

# ──────────────────────────────────────────────
# HC AFFINITY — every HC has a side-of-ball identity
# ──────────────────────────────────────────────
# When coordinators become head coaches (or any HC), this field determines
# which phase of the game they amplify.  A defensive_mind HC stacks with
# their DC's gameplan to create elite defensive programs.

HC_AFFINITIES = (
    "defensive_mind",
    "offensive_mind",
    "special_teams_guru",
    "balanced",
)

HC_AFFINITY_LABELS = {
    "defensive_mind":     "Defensive Mind",
    "offensive_mind":     "Offensive Mind",
    "special_teams_guru": "Special Teams Guru",
    "balanced":           "Balanced",
}

HC_AFFINITY_DESCRIPTIONS = {
    "defensive_mind":     "Program identity built around defense. Amplifies DC gameplan effectiveness.",
    "offensive_mind":     "Program identity built around offense. Amplifies OC scheme and yard production.",
    "special_teams_guru": "Program identity built around special teams. Amplifies return, coverage, and kicking.",
    "balanced":           "No side-of-ball amplification. Slight all-around consistency bonus.",
}

# How HC affinity modifies the DC gameplan roll and offensive/ST output.
# defensive_mind: tightens DC roll variance AND shifts center (better suppression)
# offensive_mind: direct yard center multiplier when on offense
# special_teams_guru: muff reduction, return bonus, kick accuracy
# balanced: small variance compression on both sides
HC_AFFINITY_EFFECTS = {
    "defensive_mind": {
        "dc_gameplan_center_shift": -0.04,     # DC roll center shifted 4% toward suppression
        "dc_gameplan_variance_mult": 0.80,     # DC roll variance narrowed 20% (more consistent)
        "offensive_yard_bonus": 0.0,
        "st_muff_mult": 1.0,
        "st_return_bonus": 0.0,
    },
    "offensive_mind": {
        "dc_gameplan_center_shift": 0.0,
        "dc_gameplan_variance_mult": 1.0,
        "offensive_yard_bonus": 0.03,          # +3% yard center when on offense
        "st_muff_mult": 1.0,
        "st_return_bonus": 0.0,
    },
    "special_teams_guru": {
        "dc_gameplan_center_shift": 0.0,
        "dc_gameplan_variance_mult": 1.0,
        "offensive_yard_bonus": 0.0,
        "st_muff_mult": 0.85,                 # 15% muff reduction
        "st_return_bonus": 3.0,               # +3 yards on returns
    },
    "balanced": {
        "dc_gameplan_center_shift": -0.01,     # tiny DC help
        "dc_gameplan_variance_mult": 0.95,     # slight consistency
        "offensive_yard_bonus": 0.01,          # tiny offense help
        "st_muff_mult": 0.97,
        "st_return_bonus": 0.5,
    },
}

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
        "int_chance_reduction":         (0.95, 0.85),  # multiplier on INT chance (lower = better)
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
# V2.2 SUB-ARCHETYPES
# ──────────────────────────────────────────────

SUB_ARCHETYPES = {
    "disciplinarian": {
        "enforcer": {
            "muff_reduction_multiplier": 0.95,
            "gap_discipline_multiplier": 1.05,
        },
        "technician": {
            "hands_bonus": 2,
            "tackle_bonus": 2,
        },
        "stoic": {
            "tilt_resistance": 0.90,
            "composure_floor_bonus": 3,
        },
    },
    "scheme_master": {
        "tactician": {
            "gameplan_adaptation_multiplier": 1.10,
            "defensive_read_bonus": 0.02,
        },
        "innovator": {
            "trick_play_weight_multiplier": 1.25,
            "kick_pass_weight_multiplier": 1.05,
        },
        "analyst": {
            "q3_boost_multiplier": 1.10,
            "slow_start_penalty": 0.97,
        },
    },
    "gameday_manager": {
        "clock_surgeon": {
            "timeout_efficiency": 1.20,
            "late_game_fg_bias": 1.10,
        },
        "economist": {
            "take_points_bias": 1.15,
            "early_fg_bias": 1.10,
        },
        "adjuster": {
            "halftime_adjustment_multiplier": 1.20,
            "situational_amplification_multiplier": 1.10,
        },
    },
    "motivator": {
        "firestarter": {
            "trailing_halftime_boost_multiplier": 1.15,
            "q4_explosive_play_bias": 1.10,
        },
        "believer": {
            "collapse_resistance": 0.90,
            "surge_probability_bonus": 0.05,
        },
        "emotional": {
            "variance_multiplier": 1.10,
            "tilt_sensitivity": 1.10,
        },
    },
    "players_coach": {
        "mentor": {
            "development_bonus_multiplier": 1.10,
            "chemistry_bonus_multiplier": 1.10,
        },
        "recruiter": {
            "recruiting_appeal_multiplier": 1.15,
            "prestige_bonus": 2,
        },
        "stabilizer": {
            "retention_bonus_multiplier": 1.20,
            "portal_suppression_bonus": 0.02,
        },
    },
}

SUB_ARCHETYPE_LABELS = {
    "enforcer": "Enforcer",
    "technician": "Technician",
    "stoic": "Stoic",
    "tactician": "Tactician",
    "innovator": "Innovator",
    "analyst": "Analyst",
    "clock_surgeon": "Clock Surgeon",
    "economist": "Economist",
    "adjuster": "Adjuster",
    "firestarter": "Firestarter",
    "believer": "Believer",
    "emotional": "Emotional",
    "mentor": "Mentor",
    "recruiter": "Recruiter",
    "stabilizer": "Stabilizer",
}

# ──────────────────────────────────────────────
# V2.2 PERSONALITY SLIDERS
# ──────────────────────────────────────────────

PERSONALITY_SLIDER_NAMES = (
    "aggression",
    "risk_tolerance",
    "chaos_appetite",
    "tempo_preference",
    "composure_tendency",
    "adaptability",
    "stubbornness",
    "player_trust",
    "variance_tolerance",
)

# ──────────────────────────────────────────────
# V2.2 HIDDEN TRAITS
# ──────────────────────────────────────────────

HIDDEN_TRAIT_EFFECTS = {
    "red_zone_gambler":       {"go_for_it_redzone_multiplier": 1.20},
    "chaos_merchant":         {"lateral_weight_multiplier": 1.20},
    "wind_whisperer":         {"weather_kick_penalty_multiplier": 0.80},
    "clock_melter":           {"tempo_multiplier": 0.85},
    "star_whisperer":         {"star_touch_bias": 1.25},
    "punt_hater":             {"punt_weight_multiplier": 0.50},
    "field_position_purist":  {"punt_weight_multiplier": 1.50},
    "trick_play_enjoyer":     {"trick_play_weight_multiplier": 1.30},
    "late_game_ice":          {"q4_composure_bonus": 10},
    "early_game_slow":        {"q1_yards_multiplier": 0.95},
    "weatherproof":           {"weather_penalty_multiplier": 0.70},
    "lateral_enthusiast":     {"lateral_weight_multiplier": 1.15},
    "snapkick_specialist":    {"dk_ev_multiplier": 1.15},
    "fg_conservative":        {"take_points_bias": 1.25},
    "fg_aggressive":          {"take_points_bias": 0.75},
    "hero_ball_addict":       {"star_touch_bias": 1.40},
    "anti_hero_ball":         {"star_touch_bias": 0.70},
    "timeout_hoarder":        {},
    "timeout_sprinter":       {},
    "momentum_rider":         {"momentum_recovery_multiplier": 1.30},
    "ball_security_obsessed": {
        "lateral_weight_multiplier": 0.70,
        "kick_pass_weight_multiplier": 0.80,
        "trick_play_weight_multiplier": 0.60,
    },
    "turnover_gambler":       {
        "lateral_weight_multiplier": 1.40,
        "kick_pass_weight_multiplier": 1.30,
        "trick_play_weight_multiplier": 1.50,
    },
    "bonus_possession_aware": {
        "lateral_weight_multiplier": 1.15,
        "int_acceptance_trailing": 0.90,
    },
}

HIDDEN_TRAIT_LABELS = {
    "red_zone_gambler":      "Red Zone Gambler",
    "chaos_merchant":        "Chaos Merchant",
    "wind_whisperer":        "Wind Whisperer",
    "clock_melter":          "Clock Melter",
    "star_whisperer":        "Star Whisperer",
    "punt_hater":            "Punt Hater",
    "field_position_purist": "Field Position Purist",
    "trick_play_enjoyer":    "Trick Play Enjoyer",
    "late_game_ice":         "Late Game Ice",
    "early_game_slow":       "Slow Starter",
    "weatherproof":          "Weatherproof",
    "lateral_enthusiast":    "Lateral Enthusiast",
    "snapkick_specialist":   "Snapkick Specialist",
    "fg_conservative":       "FG Conservative",
    "fg_aggressive":         "FG Aggressive",
    "hero_ball_addict":      "Hero Ball Addict",
    "anti_hero_ball":        "Anti Hero Ball",
    "timeout_hoarder":       "Timeout Hoarder",
    "timeout_sprinter":      "Timeout Sprinter",
    "momentum_rider":        "Momentum Rider",
    "ball_security_obsessed": "Ball Security Obsessed",
    "turnover_gambler":      "Turnover Gambler",
    "bonus_possession_aware": "Bonus Possession Aware",
}


# ──────────────────────────────────────────────
# V2.7 LEAD MANAGEMENT COUNTERMEASURES
# ──────────────────────────────────────────────
# Each HC gets a normalized 5-tendency blend that shapes how the
# coaching AI adjusts offense (and defense) based on score differential.
# The profile is bidirectional — it modulates behavior when leading AND
# trailing.  Derived entirely from existing coach attributes at game init.

COUNTERMEASURE_NAMES = (
    "avalanche",
    "thermostat",
    "vault",
    "counterpunch",
    "slow_drip",
)

COUNTERMEASURE_LABELS = {
    "avalanche":    "Avalanche",
    "thermostat":   "Thermostat",
    "vault":        "Vault",
    "counterpunch": "Counterpunch",
    "slow_drip":    "Slow Drip",
}

COUNTERMEASURE_DESCRIPTIONS = {
    "avalanche":    "Keep scoring aggressively regardless of lead; accept Delta Yards penalty.",
    "thermostat":   "Modulate offense to maintain lead within a target band; throttle up or down.",
    "vault":        "Possess the ball, grind clock, and deny opponent touches.",
    "counterpunch": "Accept opponent scores to reset Delta Yards; re-attack from better field position.",
    "slow_drip":    "Score with FGs and snap kicks only; avoid TDs to keep Delta penalty manageable.",
}

# Classification → base tendency boosts (before personality blending).
# Values are in 0-1 scale, multiplied by 100 when applied to raw scores.
CLASSIFICATION_COUNTERMEASURE_BIAS = {
    "motivator":       {"avalanche": 0.15, "counterpunch": 0.15},
    "gameday_manager": {"thermostat": 0.25},
    "disciplinarian":  {"vault": 0.20, "slow_drip": 0.05},
    "scheme_master":   {"slow_drip": 0.20, "thermostat": 0.05},
    "players_coach":   {"counterpunch": 0.10, "thermostat": 0.10},
}

# Offensive style → tendency boosts
STYLE_COUNTERMEASURE_BIAS = {
    "chain_gang":      {"avalanche": 0.15, "counterpunch": 0.10},
    "lateral_spread":  {"avalanche": 0.15, "counterpunch": 0.10},
    "ghost":           {"avalanche": 0.10, "counterpunch": 0.05},
    "shock_and_awe":   {"avalanche": 0.20},
    "ground_pound":    {"vault": 0.20, "slow_drip": 0.05},
    "ball_control":    {"vault": 0.10, "thermostat": 0.15},
    "boot_raid":       {"slow_drip": 0.25},
    "stampede":        {"avalanche": 0.10, "vault": 0.05},
    "slick_n_slide":   {"thermostat": 0.15},
    "east_coast":      {"thermostat": 0.10, "slow_drip": 0.10},
    "balanced":        {"thermostat": 0.15},
}

# Thermostat target band defaults (points of lead)
DEFAULT_THERMOSTAT_BAND = (10, 18)


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

    # V2.2 Personality System ─────────────────
    sub_archetype: str = ""
    personality_sliders: Dict[str, int] = field(default_factory=dict)
    hidden_traits: List[str] = field(default_factory=list)

    # V2.3 HC Affinity ──────────────────────
    hc_affinity: str = "balanced"        # one of HC_AFFINITIES

    # V2.4 Coaching Portal ────────────────
    wants_hc: bool = False               # assistant coaches who aspire to be HC
    alma_mater: str = ""                 # school name — alumni bonus in portal matching

    # V2.5 HC Ambition & Coaching Tree ──
    conference_titles: int = 0           # career conference championships won
    playoff_appearances: int = 0         # career playoff berths
    playoff_wins: int = 0               # career individual playoff game wins
    championship_appearances: int = 0    # career finals reached
    # coaching_tree: every HC this coach worked under as an assistant
    # Each entry: {"coach_name", "coach_id", "team_name", "year_start", "year_end"}
    coaching_tree: List[dict] = field(default_factory=list)

    # V2.5 HC Readiness Meter (assistants only) ──
    # 0-100 meter that fills over time. When it crosses 75, the coach
    # flips wants_hc=True and actively seeks HC positions.  At 90+
    # they're a "hot name" that gets ranking boosts in portal matching.
    hc_meter: int = 0

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
    def sub_archetype_label(self) -> str:
        return SUB_ARCHETYPE_LABELS.get(self.sub_archetype, self.sub_archetype)

    @property
    def hc_affinity_label(self) -> str:
        return HC_AFFINITY_LABELS.get(self.hc_affinity, self.hc_affinity)

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
            "sub_archetype": self.sub_archetype,
            "personality_sliders": self.personality_sliders,
            "hidden_traits": self.hidden_traits,
            "hc_affinity": self.hc_affinity,
            "wants_hc": self.wants_hc,
            "alma_mater": self.alma_mater,
            "conference_titles": self.conference_titles,
            "playoff_appearances": self.playoff_appearances,
            "playoff_wins": self.playoff_wins,
            "championship_appearances": self.championship_appearances,
            "coaching_tree": list(self.coaching_tree),
            "hc_meter": self.hc_meter,
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
            sub_archetype=d.get("sub_archetype", ""),
            personality_sliders=d.get("personality_sliders", {}),
            hidden_traits=d.get("hidden_traits", []),
            hc_affinity=d.get("hc_affinity", "balanced"),
            wants_hc=d.get("wants_hc", False),
            alma_mater=d.get("alma_mater", ""),
            conference_titles=d.get("conference_titles", 0),
            playoff_appearances=d.get("playoff_appearances", 0),
            playoff_wins=d.get("playoff_wins", 0),
            championship_appearances=d.get("championship_appearances", 0),
            coaching_tree=d.get("coaching_tree", []),
            hc_meter=d.get("hc_meter", 0),
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

    # ── V2.2: sub-archetype, personality sliders, hidden traits ──
    sub_choices = list(SUB_ARCHETYPES.get(cls_, {}).keys())
    sub_arch = rng.choice(sub_choices) if sub_choices else ""

    sliders = {
        name: max(0, min(100, int(rng.gauss(50, 15))))
        for name in PERSONALITY_SLIDER_NAMES
    }

    traits = []
    for trait_name in HIDDEN_TRAIT_EFFECTS:
        if len(traits) >= 2:
            break
        if rng.random() < 0.05:
            traits.append(trait_name)

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

    # ── contract (staggered: offset by role so not all expire at once) ──
    _role_year_ranges = {"head_coach": (3, 5), "oc": (2, 4), "dc": (2, 4), "stc": (1, 3)}
    yr_lo, yr_hi = _role_year_ranges.get(role, (2, 4))
    contract_years = rng.randint(yr_lo, yr_hi) if team_name else 0
    # Stagger remaining years so existing staffs have different expiry dates
    if team_name and contract_years > 1:
        contract_years_remaining_init = rng.randint(1, contract_years)
    else:
        contract_years_remaining_init = contract_years
    salary = 0
    buyout = 0

    # ── wants_hc flag (assistants only) ──
    wants_hc_flag = False
    if role != "head_coach":
        hc_aspiration_chance = 0.15
        if attrs.get("leadership", 50) >= 70:
            hc_aspiration_chance += 0.15
        if age <= 45:
            hc_aspiration_chance += 0.15
        wants_hc_flag = rng.random() < hc_aspiration_chance

    # ── alma mater (assigned later from full league list if available) ──
    alma = ""

    # ── HC affinity (all coaches get one, but only HC's matters in-game) ──
    # Weighted toward balanced; classification biases the roll:
    #   disciplinarian → defensive_mind more likely
    #   scheme_master  → offensive_mind more likely
    #   others         → balanced/mixed
    _affinity_weights = {
        "disciplinarian": [0.50, 0.10, 0.05, 0.35],  # def, off, st, bal
        "scheme_master":  [0.15, 0.45, 0.05, 0.35],
        "gameday_manager": [0.15, 0.15, 0.15, 0.55],
        "motivator":      [0.15, 0.20, 0.10, 0.55],
        "players_coach":  [0.15, 0.15, 0.10, 0.60],
    }
    aff_w = _affinity_weights.get(cls_, [0.15, 0.15, 0.10, 0.60])
    hc_aff = rng.choices(list(HC_AFFINITIES), weights=aff_w, k=1)[0]

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
        sub_archetype=sub_arch,
        personality_sliders=sliders,
        hidden_traits=traits,
        hc_affinity=hc_aff,
        wants_hc=wants_hc_flag,
        alma_mater=alma,
    )

    # Set salary after card exists so calculate_coach_salary can use it
    salary = calculate_coach_salary(card, rng=rng)
    card.contract_salary = salary
    card.contract_years_remaining = contract_years_remaining_init
    card.contract_buyout = int(salary * contract_years * 0.5) if contract_years > 0 else 0

    return card


def generate_coaching_staff(
    team_name: str = "",
    prestige: int = 50,
    year: int = 2026,
    rng: Optional[random.Random] = None,
    all_team_names: Optional[List[str]] = None,
) -> Dict[str, CoachCard]:
    """
    Generate a full 4-person coaching staff: HC, OC, DC, STC.

    Args:
        all_team_names: If provided, coaches get a random alma_mater
                        from this list (~35% chance per coach).

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
        # Assign alma mater from the league's school list
        if all_team_names and rng.random() < 0.35:
            card.alma_mater = rng.choice(all_team_names)
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

    # V2.2: sub-archetype, personality sliders, hidden traits
    sub_choices = list(SUB_ARCHETYPES.get(cls_, {}).keys())
    sub_arch = rng.choice(sub_choices) if sub_choices else ""
    sliders = {
        name: max(0, min(100, int(rng.gauss(50, 15))))
        for name in PERSONALITY_SLIDER_NAMES
    }
    traits = []
    for trait_name in HIDDEN_TRAIT_EFFECTS:
        if len(traits) >= 2:
            break
        if rng.random() < 0.05:
            traits.append(trait_name)

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
        sub_archetype=sub_arch,
        personality_sliders=sliders,
        hidden_traits=traits,
    )

    # Lower salary for unproven coaches
    salary = int(calculate_coach_salary(card, rng=rng) * 0.70)
    card.contract_salary = salary
    card.contract_years_remaining = 1  # Prove-it deal
    card.contract_buyout = 0

    return card


# ──────────────────────────────────────────────
# V2.5 HC READINESS METER + COACH DEVELOPMENT
# ──────────────────────────────────────────────
# Assistants accumulate "HC Meter" points each offseason based on:
#   - Coaching a top-tier player (+5-10 if best player in their area is 85+ ovr)
#   - Team winning record (+3-8 based on wins above .500)
#   - Working for a successful HC (+2-6 based on HC win% and postseason)
#   - Pure tenure (+2 per year as a coordinator)
#   - Their own overall rating (+1-3 if 75+ overall)
#
# At meter >= 75 the coach flips wants_hc = True.
# At meter >= 90 they're a "hot name" with portal ranking boosts.
#
# Coaches also develop their attributes each offseason (like players),
# though gains are smaller: 0-2 points per attribute.

def advance_hc_meter(
    card: CoachCard,
    team_wins: int,
    team_losses: int,
    hc_card: Optional[CoachCard] = None,
    best_player_ovr_in_area: int = 0,
    made_playoff: bool = False,
    won_conference: bool = False,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Advance an assistant coach's HC readiness meter for one offseason.

    Args:
        card:                    The assistant coach.
        team_wins:               Team's wins this season.
        team_losses:             Team's losses this season.
        hc_card:                 The HC they worked under (for success bonus).
        best_player_ovr_in_area: Highest overall among players in their area.
        made_playoff:            Whether the team made the playoffs.
        won_conference:          Whether the team won the conference.
        rng:                     Seeded Random.

    Returns:
        The meter gain this year.
    """
    if rng is None:
        rng = random.Random()

    if card.role == "head_coach":
        return 0  # HCs don't need the meter

    gain = 0

    # 1. Tenure: +2 per year as a coordinator
    gain += 2

    # 2. Coaching a star player: +5-10 if best player in area is 85+ ovr
    if best_player_ovr_in_area >= 90:
        gain += rng.randint(7, 10)
    elif best_player_ovr_in_area >= 85:
        gain += rng.randint(5, 7)
    elif best_player_ovr_in_area >= 80:
        gain += rng.randint(2, 4)

    # 3. Team winning: +3-8 based on wins above .500
    total = team_wins + team_losses
    if total > 0:
        wp = team_wins / total
        if wp >= 0.75:
            gain += rng.randint(6, 8)
        elif wp >= 0.60:
            gain += rng.randint(4, 6)
        elif wp >= 0.50:
            gain += rng.randint(2, 4)

    # 4. Postseason: bonus for playoff / conference championship
    if made_playoff:
        gain += rng.randint(3, 5)
    if won_conference:
        gain += rng.randint(2, 4)

    # 5. HC success: working for a great HC rubs off
    if hc_card:
        hc_wp = hc_card.win_percentage
        if hc_wp >= 0.70:
            gain += rng.randint(4, 6)
        elif hc_wp >= 0.55:
            gain += rng.randint(2, 4)
        # Bonus if HC has championships
        if hc_card.championships > 0:
            gain += rng.randint(1, 3)

    # 6. Own quality: already-good coaches learn faster
    if card.overall >= 80:
        gain += rng.randint(2, 3)
    elif card.overall >= 75:
        gain += rng.randint(1, 2)

    # Apply
    old_meter = card.hc_meter
    card.hc_meter = min(100, card.hc_meter + gain)

    # Flip wants_hc when meter crosses 75
    if card.hc_meter >= 75 and not card.wants_hc:
        card.wants_hc = True

    return gain


def apply_coach_development(
    card: CoachCard,
    team_wins: int = 6,
    team_losses: int = 6,
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """
    Apply offseason attribute development to a coach.

    Coaches improve slowly over time (0-2 per attribute per year),
    with a small boost for winning and a decline for old age.

    Args:
        card:         The coach to develop.
        team_wins:    Team wins this season (winning breeds improvement).
        team_losses:  Team losses.
        rng:          Seeded Random.

    Returns:
        Dict of attribute_name -> change amount.
    """
    if rng is None:
        rng = random.Random()

    changes: Dict[str, int] = {}
    total = team_wins + team_losses
    wp = team_wins / total if total > 0 else 0.5

    # Winning coaches improve more
    if wp >= 0.65:
        gain_range = (0, 2)
    elif wp >= 0.50:
        gain_range = (0, 1)
    else:
        gain_range = (-1, 1)

    # Age decline: coaches over 60 start losing a step
    age_penalty = 0
    if card.age >= 65:
        age_penalty = -2
    elif card.age >= 60:
        age_penalty = -1

    for attr_name in ("instincts", "leadership", "composure", "rotations",
                       "development", "recruiting"):
        base_change = rng.randint(*gain_range) + age_penalty
        old_val = getattr(card, attr_name)
        new_val = _clamp_attr(old_val + base_change)
        delta = new_val - old_val
        if delta != 0:
            setattr(card, attr_name, new_val)
            changes[attr_name] = delta

    return changes


# ──────────────────────────────────────────────
# V2.5 ROLE FLUIDITY: HC ↔ COORDINATOR
# ──────────────────────────────────────────────
# Head coaches can accept coordinator roles (demotions) and
# coordinators can be promoted to HC.  When a coach changes roles,
# their attributes and classification stay the same but their
# contract/salary adjusts.

def get_acceptable_roles(card: CoachCard) -> List[str]:
    """
    Return all roles a coach would consider accepting.

    Every coach can move between HC and coordinator roles — it's not
    a permanent designation.  A fired HC might take a coordinator
    job to stay in the game; a coordinator with high HC meter
    wants an HC gig.

    Rules:
    - HCs accept: head_coach + their original coordinator role
      (inferred from hc_affinity) + any role if desperate (fired).
    - Coordinators accept: their current role, head_coach (if
      wants_hc), and adjacent coordinator roles (30% each).
    """
    roles = [card.role]

    if card.role == "head_coach":
        # Former HCs can take coordinator roles
        # Their hc_affinity hints at where they'd fit best
        if card.hc_affinity == "defensive_mind":
            if "dc" not in roles:
                roles.append("dc")
        elif card.hc_affinity == "offensive_mind":
            if "oc" not in roles:
                roles.append("oc")
        elif card.hc_affinity == "special_teams_guru":
            if "stc" not in roles:
                roles.append("stc")
        else:
            # Balanced: pick one coordinator role
            for r in ("oc", "dc"):
                if r not in roles:
                    roles.append(r)
                    break
    else:
        # Coordinators
        if card.wants_hc or card.hc_meter >= 75:
            if "head_coach" not in roles:
                roles.append("head_coach")

    return roles


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


# ──────────────────────────────────────────────
# V2.2 PERSONALITY HELPERS
# ──────────────────────────────────────────────

def personality_factor(sliders: Dict[str, int], attr: str) -> float:
    """F(p) = 1 + (p - 50) / 200.  Range: 0.75 (p=0) to 1.25 (p=100)."""
    return 1.0 + (sliders.get(attr, 50) - 50) / 200.0


def get_sub_archetype_effects(card: CoachCard) -> Dict:
    """Return micro-effect dict for this coach's sub-archetype."""
    return SUB_ARCHETYPES.get(card.classification, {}).get(card.sub_archetype, {})


def compute_hidden_trait_effects(card: CoachCard) -> Dict[str, float]:
    """Aggregate all hidden trait multipliers into a single dict."""
    combined: Dict[str, float] = {}
    for trait in card.hidden_traits:
        for key, val in HIDDEN_TRAIT_EFFECTS.get(trait, {}).items():
            if key in combined:
                combined[key] *= val  # multiplicative stacking
            else:
                combined[key] = val
    return combined


def coaching_modifier_chain(
    base: float, personality_val: float, sub_mult: float, trait_mult: float
) -> float:
    """Apply the V2.2 3-layer multiplicative chain, clamped [0.5, 1.5]."""
    return max(0.5, min(1.5, base * personality_val * sub_mult * trait_mult))


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


def compute_hc_ambition(coach: CoachCard) -> int:
    """
    Compute the prestige level an HC believes they deserve.

    An HC's ambition is built from their career win percentage plus
    bonuses from postseason success.  This drives whether the HC seeks
    a move to a higher-prestige program when their contract expires.

    Formula:
        base  = win_percentage * 80                            (0-80)
        + conference_titles * 5                                (up to ~25)
        + playoff_appearances * 3                              (up to ~15)
        + playoff_wins * 4          (deeper runs = more wins)  (up to ~20)
        + championship_appearances * 5                         (up to ~10)
        + championships * 8                                    (up to ~24)

    Returns:
        int in [10, 99] — the prestige level this HC expects.
    """
    wp = coach.win_percentage
    base = int(wp * 80)

    base += coach.conference_titles * 5
    base += coach.playoff_appearances * 3
    base += coach.playoff_wins * 4
    base += coach.championship_appearances * 5
    base += coach.championships * 8

    return max(10, min(99, base))


def try_hc_contract_extension(
    coach: CoachCard,
    team_prestige: int,
    team_wins: int,
    team_losses: int,
    year: int,
    rng: Optional[random.Random] = None,
) -> bool:
    """
    Attempt to give a successful HC a contract extension (parlay).

    A head coach whose contract just expired can parlay their success
    into a new deal at their current school instead of entering the
    portal.  This happens when:
    1. The HC's ambition <= current team prestige + 10
       (they're not reaching for something significantly better)
    2. They had a winning record in the most recent season

    If extended, the coach gets:
    - 3-5 new contract years
    - A salary bump (re-calculated from current attributes + record)

    Args:
        coach:         The HC whose contract expired.
        team_prestige: Current prestige of the team.
        team_wins:     Most recent season wins.
        team_losses:   Most recent season losses.
        year:          Current dynasty year.
        rng:           Seeded Random.

    Returns:
        True if the coach extended (stays), False if they want out.
    """
    if rng is None:
        rng = random.Random()

    ambition = compute_hc_ambition(coach)

    # If their ambition exceeds team prestige by more than 10 points,
    # they feel they've outgrown the program
    if ambition > team_prestige + 10:
        return False

    # Need at least a .500 record to feel good about staying
    total = team_wins + team_losses
    if total > 0 and team_wins / total < 0.50:
        return False

    # Extension: 3-5 years, re-calculated salary
    new_years = rng.randint(3, 5)
    new_salary = calculate_coach_salary(coach, rng=rng)
    # Loyalty bump: +10% salary for staying
    new_salary = int(new_salary * 1.10)

    coach.contract_years_remaining = new_years
    coach.contract_salary = new_salary
    coach.contract_buyout = int(new_salary * new_years * 0.5)
    coach.year_signed = year

    return True


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
    offense_style: str = "balanced",
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

    # V2.2: Sub-archetype, personality, and hidden-trait effects
    sub_effects = get_sub_archetype_effects(hc) if hc else {}
    p_factors = (
        {attr: personality_factor(hc.personality_sliders, attr)
         for attr in PERSONALITY_SLIDER_NAMES}
        if hc else {}
    )
    h_trait_effects = compute_hidden_trait_effects(hc) if hc else {}

    # V2.3: Pre-compute HC affinity effects so the engine doesn't need to import constants
    hc_aff = hc.hc_affinity if hc else "balanced"
    aff_fx = HC_AFFINITY_EFFECTS.get(hc_aff, HC_AFFINITY_EFFECTS["balanced"])

    return {
        "instincts_factor": norm(instincts_raw),
        "leadership_factor": norm(leadership_raw),
        "composure_value": composure_raw,
        "fatigue_resistance_mod": fatigue_mod,
        "classification_effects": cls_effects,
        "hc_classification": hc.classification if hc else "scheme_master",
        "hc_affinity": hc_aff,
        "hc_affinity_effects": aff_fx,
        # V2.2
        "sub_archetype": hc.sub_archetype if hc else "",
        "sub_archetype_effects": sub_effects,
        "personality_factors": p_factors,
        "hidden_trait_effects": h_trait_effects,
        # V2.4 — coaching dev aura (in-game rolling stat boost)
        "dev_aura": compute_dev_aura(coaching_staff),
        # V2.7 — lead management countermeasure profile
        "lead_management": compute_lead_management_profile(coaching_staff, offense_style),
    }


# ──────────────────────────────────────────────
# V2.7: LEAD MANAGEMENT PROFILE
# ──────────────────────────────────────────────


def _norm95(val: float) -> float:
    """Normalize a 25-95 attribute to 0-100 scale."""
    return max(0.0, min(100.0, (val - 25) / 70.0 * 100.0))


def _default_lead_profile() -> Dict:
    """Fallback lead management profile when no HC is available."""
    return {
        "tendencies": {
            "avalanche": 0.15, "thermostat": 0.30, "vault": 0.25,
            "counterpunch": 0.10, "slow_drip": 0.20,
        },
        "primary": "thermostat",
        "sensitivity_offset": 7.0,
        "sensitivity_range": 10.0,
        "thermostat_band": DEFAULT_THERMOSTAT_BAND,
    }


def compute_lead_management_profile(
    coaching_staff: Dict[str, CoachCard],
    offense_style: str = "balanced",
) -> Dict:
    """
    Compute lead management countermeasure profile from coaching staff.

    Called once at game init.  Returns a dict consumed by the game engine
    to modulate play selection, tempo, formations, and kick decisions
    based on score differential.

    The profile is bidirectional — it affects behavior when leading AND
    trailing.  Each coach's 5-tendency blend is unique, derived from
    personality sliders, classification, and offensive style.

    Sensitivity controls how early and how strongly the coach reacts:
    - High-reactivity coaches (aggressive, chaotic): offset ~1, range ~6
    - Stoic coaches (stubborn, composed): offset ~11, range ~14

    Returns:
        {
            "tendencies": {name: 0.0-1.0 for 5 countermeasures},
            "primary": str (highest-weighted tendency),
            "sensitivity_offset": float (1-12, when effects begin),
            "sensitivity_range": float (6-15, points to full effect),
            "thermostat_band": (lo, hi) target lead range,
        }
    """
    hc = coaching_staff.get("head_coach")
    if hc is None:
        return _default_lead_profile()

    sliders = hc.personality_sliders or {}
    agg = sliders.get("aggression", 50)
    risk = sliders.get("risk_tolerance", 50)
    chaos = sliders.get("chaos_appetite", 50)
    composure = sliders.get("composure_tendency", 50)
    adapt = sliders.get("adaptability", 50)
    stubborn = sliders.get("stubbornness", 50)
    trust = sliders.get("player_trust", 50)
    var_tol = sliders.get("variance_tolerance", 50)
    tempo_pref = sliders.get("tempo_preference", 50)

    inst = getattr(hc, "instincts", 60)   # hidden, 25-95
    rot = getattr(hc, "rotations", 60)    # 25-95

    # ── Raw tendency scores (weighted slider sums, 0-100 scale) ──

    # Avalanche: aggression + risk + chaos + variance_tolerance + tempo
    t_avalanche = (agg * 0.30 + risk * 0.25 + chaos * 0.20
                   + var_tol * 0.15 + tempo_pref * 0.10)

    # Thermostat: composure + adaptability - stubbornness - chaos
    t_thermostat = (composure * 0.30 + adapt * 0.30
                    + (100 - stubborn) * 0.25 + (100 - chaos) * 0.15)

    # Vault: inverse risk + rotations + inverse chaos + inverse variance
    t_vault = ((100 - risk) * 0.25 + _norm95(rot) * 0.30
               + (100 - chaos) * 0.20 + (100 - var_tol) * 0.15
               + (100 - tempo_pref) * 0.10)

    # Counterpunch: player_trust + variance + risk + chaos + adaptability
    t_counterpunch = (trust * 0.30 + var_tol * 0.25 + risk * 0.20
                      + chaos * 0.15 + adapt * 0.10)

    # Slow Drip: instincts + inverse aggression + composure + adaptability
    t_slow_drip = (_norm95(inst) * 0.30 + (100 - agg) * 0.25
                   + composure * 0.20 + adapt * 0.15
                   + (100 - var_tol) * 0.10)

    tendencies = {
        "avalanche": t_avalanche,
        "thermostat": t_thermostat,
        "vault": t_vault,
        "counterpunch": t_counterpunch,
        "slow_drip": t_slow_drip,
    }

    # ── Apply classification bias ──
    cls_bias = CLASSIFICATION_COUNTERMEASURE_BIAS.get(hc.classification, {})
    for k, bonus in cls_bias.items():
        tendencies[k] += bonus * 100  # scale to 0-100 space

    # ── Apply offensive style bias ──
    style_bias = STYLE_COUNTERMEASURE_BIAS.get(offense_style, {})
    for k, bonus in style_bias.items():
        tendencies[k] += bonus * 100

    # ── Normalize to sum to 1.0 ──
    total = sum(max(0.01, v) for v in tendencies.values())
    tendencies = {k: max(0.01, v) / total for k, v in tendencies.items()}

    primary = max(tendencies, key=tendencies.get)

    # ── Sensitivity: how early and fast the coach reacts ──
    # Reactive coaches (high agg, high chaos, low stubborn): low offset, short range
    # Stoic coaches (low agg, high stubborn, high composure): high offset, long range
    reactivity = (agg * 0.30 + chaos * 0.25 + (100 - stubborn) * 0.25
                  + (100 - composure) * 0.20)
    # reactivity 0-100 → offset 12 down to 1
    sensitivity_offset = max(1.0, 12.0 - reactivity * 0.11)
    # reactivity 0-100 → range 15 down to 6
    sensitivity_range = max(6.0, 15.0 - reactivity * 0.09)

    # ── Thermostat band: derived from risk tolerance and composure ──
    band_lo = max(5, int(8 + (100 - risk) / 25))
    band_hi = max(band_lo + 5, int(16 + risk / 20))

    return {
        "tendencies": tendencies,
        "primary": primary,
        "sensitivity_offset": round(sensitivity_offset, 1),
        "sensitivity_range": round(sensitivity_range, 1),
        "thermostat_band": (band_lo, band_hi),
    }


# ──────────────────────────────────────────────
# V2.3: DC GAMEPLAN ROLL
# ──────────────────────────────────────────────
# At game init, each team's DC (blended with HC) rolls per-play-type
# suppression values.  These multiply against opponent yard center
# and completion probability.  The roll creates hot/neutral/cold
# defensive games that vary week to week.
#
# Play types for suppression:
#   run      — dive, speed, sweep, power, counter, draw, viper_jet
#   lateral  — lateral_spread
#   kick_pass — kick_pass
#   trick    — trick_play
#
# The DC's instincts set the center, classification skews specific
# categories, and HC affinity amplifies the whole roll.

DC_GAMEPLAN_PLAY_TYPES = ("run", "lateral", "kick_pass", "trick")

# Classification → which play types the DC is especially good at suppressing
# Values are additional center shifts (negative = more suppression)
DC_CLASSIFICATION_BIAS = {
    "disciplinarian": {"run": -0.04, "lateral": -0.01, "kick_pass": 0.0,  "trick": -0.01},
    "scheme_master":  {"run": 0.0,   "lateral": -0.02, "kick_pass": -0.03, "trick": -0.04},
    "gameday_manager": {"run": -0.01, "lateral": -0.01, "kick_pass": -0.01, "trick": -0.01},
    "motivator":      {"run": -0.01, "lateral": 0.0,   "kick_pass": 0.0,  "trick": 0.0},
    "players_coach":  {"run": 0.0,   "lateral": 0.0,   "kick_pass": 0.0,  "trick": 0.0},
}


def roll_dc_gameplan(
    coaching_staff: Dict[str, CoachCard],
    rng: Optional[random.Random] = None,
) -> Dict[str, float]:
    """
    Roll the DC's per-game defensive gameplan effectiveness.

    Called once at game init.  Returns a dict of play_type → suppression
    multiplier.  Values < 1.0 mean the defense suppresses that play type;
    values > 1.0 mean the offense exploits a weakness.

    The roll is high-variance: a good DC might roll 0.80 (cold) or 1.05
    (offense figured them out).  This creates emergent hot/neutral/cold
    defensive games.

    Returns:
        {
            "run": 0.92,          # 8% yard suppression vs runs
            "lateral": 0.78,      # 22% vs laterals (DC was ready)
            "kick_pass": 1.03,    # offense has slight edge
            "trick": 0.85,        # DC sniffed out the tricks
            "game_temperature": "cold",  # label for display
        }
    """
    if rng is None:
        rng = random.Random()

    hc = coaching_staff.get("head_coach")
    dc = coaching_staff.get("dc")

    # DC instincts drive the base center.
    # instincts 25 → center 1.02 (bad DC, slight offense advantage)
    # instincts 60 → center 0.96 (average DC)
    # instincts 95 → center 0.90 (elite DC, 10% suppression baseline)
    dc_inst = getattr(dc, "instincts", 50) if dc else 50
    hc_inst = getattr(hc, "instincts", 50) if hc else 50
    # Blend: DC 70% weight, HC 30% (DC drives the scheme, HC sets the tone)
    blended_instincts = dc_inst * 0.70 + hc_inst * 0.30

    # Map instincts to center: 25 → 1.02, 60 → 0.96, 95 → 0.90
    base_center = 1.02 - (blended_instincts - ATTR_MIN) / (ATTR_MAX - ATTR_MIN) * 0.12

    # HC affinity shifts the center and narrows variance
    hc_aff = getattr(hc, "hc_affinity", "balanced") if hc else "balanced"
    aff_effects = HC_AFFINITY_EFFECTS.get(hc_aff, HC_AFFINITY_EFFECTS["balanced"])
    center_shift = aff_effects["dc_gameplan_center_shift"]
    var_mult = aff_effects["dc_gameplan_variance_mult"]

    # Classification bias per play type
    dc_cls = getattr(dc, "classification", "scheme_master") if dc else "scheme_master"
    cls_bias = DC_CLASSIFICATION_BIAS.get(dc_cls, {})

    # Roll variance: base 0.08, modified by HC affinity
    # This means ±1 std dev is ~8% swing, ±2 std dev is ~16%
    base_variance = 0.08 * var_mult

    result = {}
    for pt in DC_GAMEPLAN_PLAY_TYPES:
        pt_center = base_center + center_shift + cls_bias.get(pt, 0.0)
        roll = rng.gauss(pt_center, base_variance)
        # Clamp: 0.75 (dominant defense) to 1.12 (offense exploits)
        result[pt] = max(0.75, min(1.12, round(roll, 3)))

    # Determine game temperature label from average suppression
    avg = sum(result[pt] for pt in DC_GAMEPLAN_PLAY_TYPES) / len(DC_GAMEPLAN_PLAY_TYPES)
    if avg <= 0.90:
        result["game_temperature"] = "cold"
    elif avg >= 1.02:
        result["game_temperature"] = "hot"
    else:
        result["game_temperature"] = "neutral"

    return result


# ──────────────────────────────────────────────
# V2.4 COACHING DEV AURA (IN-GAME ROLLING BOOST)
# ──────────────────────────────────────────────
# Each coach's ``development`` attribute creates a per-game aura.
# Players on the roster receive a small, cumulative stat multiplier
# for every game played under that staff.  The aura travels with
# the coaching staff — if they leave, the boost disappears.
#
# Formula:  effective_stat = base_stat * (1 + aura * games_played / season_length)
#
# With a max aura of ~0.08 and 12-game season the peak boost is ~8%.
# This makes high-development coaching staffs meaningfully overperform
# their roster ratings, exactly as described.

def compute_dev_aura(
    coaching_staff: Dict[str, CoachCard],
) -> float:
    """
    Compute the in-game development aura from a coaching staff.

    Blends HC (40%), OC (30%), DC (20%), STC (10%) development ratings
    and maps the result to a 0.0-0.08 aura multiplier.

    Returns:
        Float in [0.0, 0.08] — the per-game-fraction stat boost.
    """
    weights = {"head_coach": 0.40, "oc": 0.30, "dc": 0.20, "stc": 0.10}
    total_dev = 0.0
    total_weight = 0.0
    for role, wt in weights.items():
        card = coaching_staff.get(role)
        if card:
            total_dev += card.development * wt
            total_weight += wt

    if total_weight == 0:
        return 0.0

    blended = total_dev / total_weight
    # Map 25-95 → 0.0-0.08
    return max(0.0, (blended - ATTR_MIN) / (ATTR_MAX - ATTR_MIN) * 0.08)


def apply_dev_aura_to_stats(
    base_stats: Dict[str, int],
    aura: float,
    games_played: int,
    season_length: int = 13,
) -> Dict[str, int]:
    """
    Apply the coaching dev aura to a player's stats for a single game.

    The boost scales linearly with games played under this staff,
    reaching its maximum at the end of the season.

    Args:
        base_stats:    Dict of stat_name -> base value.
        aura:          Result of compute_dev_aura().
        games_played:  How many games this player has played this season.
        season_length: Total games in the season (for scaling).

    Returns:
        Dict of stat_name -> boosted value (ints, capped at 99).
    """
    if aura <= 0 or games_played <= 0:
        return dict(base_stats)

    progress = min(1.0, games_played / max(1, season_length))
    multiplier = 1.0 + aura * progress

    return {k: min(99, int(v * multiplier)) for k, v in base_stats.items()}
