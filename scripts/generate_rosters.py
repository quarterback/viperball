#!/usr/bin/env python3
"""
Viperball Roster Generator

Generates 36-player rosters for all teams using the name generator
and team recruiting pipelines.

Usage:
    python scripts/generate_rosters.py [--schools SCHOOL_IDS] [--all]

Examples:
    python scripts/generate_rosters.py --schools gonzaga,villanova,vcu
    python scripts/generate_rosters.py --all  # Generate all rosters (takes time)
"""

import json
import random
import argparse
from pathlib import Path
import sys

# Add parent directory to path to import generate_names
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_names import generate_player_name, build_geo_pipeline
from scripts.generate_coach_names import generate_coach_name


# ── Program Archetype System ──
# Each archetype defines a talent_offset applied to ALL base attribute rolls,
# plus a hidden_gem_chance (probability that a randomly-selected player on the
# roster gets a large stat boost — ensuring every program can have a star).
# star_distribution tweaks how potential stars are distributed.

PROGRAM_ARCHETYPES = {
    "doormat": {
        "label": "Doormat",
        "description": "Bottom-tier program. Talent is scarce but a hidden gem or two keeps hope alive.",
        "stat_center": 15,             # floor-level — pure project players
        "stat_spread": 38,             # wide — individual stats swing wildly
        "hidden_gem_count": (1, 2),    # 1-2 legit players — portal bait
        "hidden_gem_boost": (20, 30),  # 15+25=40 → gem is merely competent, not a star
        "hidden_gem_stats": (3, 5),    # boost across some stats
        "potential_weights": {
            "freshman": [1, 3, 8, 35, 53],
            "sophomore": [0, 2, 6, 34, 58],
            "junior": [0, 1, 4, 35, 60],
            "senior": [0, 0, 5, 33, 62],
        },
        "dev_weights": [30, 2, 50, 18],
        "prestige_range": (1, 12),
    },
    "underdog": {
        "label": "Underdogs",
        "description": "Below average but scrappy. A few solid players make them competitive on any given day.",
        "stat_center": 20,             # very raw — need multipliers to compete
        "stat_spread": 38,
        "hidden_gem_count": (1, 3),    # 1-3 legit players — portal targets
        "hidden_gem_boost": (18, 25),  # 20+22=42 → gem has upside through development
        "hidden_gem_stats": (3, 5),    # boost across some stats
        "potential_weights": {
            "freshman": [4, 7, 14, 36, 39],
            "sophomore": [2, 5, 10, 36, 47],
            "junior": [1, 3, 7, 38, 51],
            "senior": [0, 2, 10, 38, 50],
        },
        "dev_weights": [38, 6, 40, 16],
        "prestige_range": (10, 28),
    },
    "punching_above": {
        "label": "Punching Above Their Weight",
        "description": "Upper mid-major. Well-coached and greater than the sum of their parts.",
        "stat_center": 35,             # below average base — coaching matters
        "stat_spread": 38,
        "hidden_gem_count": (2, 3),    # 2-3 standouts
        "hidden_gem_boost": (12, 18),  # 35+15=50 → gem has real tools to work with
        "hidden_gem_stats": (3, 5),
        "potential_weights": {
            "freshman": [10, 16, 24, 28, 22],
            "sophomore": [7, 13, 20, 32, 28],
            "junior": [4, 10, 16, 36, 34],
            "senior": [0, 7, 22, 38, 33],
        },
        "dev_weights": [46, 14, 28, 12],
        "prestige_range": (24, 48),
    },
    "regional_power": {
        "label": "Regional Power",
        "description": "Strong program that dominates their region. Solid roster top to bottom.",
        "stat_center": 44,             # decent base — multipliers push them into contention
        "stat_spread": 38,
        "hidden_gem_count": (3, 5),    # 3-5 standouts
        "hidden_gem_boost": (8, 14),   # 44+11=55 → gem is a legit starter
        "hidden_gem_stats": (3, 5),
        "potential_weights": {
            "freshman": [22, 26, 22, 18, 12],
            "sophomore": [18, 22, 20, 22, 18],
            "junior": [12, 20, 18, 28, 22],
            "senior": [0, 14, 30, 32, 24],
        },
        "dev_weights": [50, 22, 18, 10],
        "prestige_range": (45, 68),
    },
    "national_power": {
        "label": "National Power",
        "description": "Top-tier program that competes for championships. Deep roster with multiple stars.",
        "stat_center": 52,             # solid base — multipliers create stars
        "stat_spread": 38,
        "hidden_gem_count": (3, 5),    # deep bench of potential
        "hidden_gem_boost": (6, 10),   # 52+8=60 → gem is a cornerstone player
        "hidden_gem_stats": (3, 5),
        "potential_weights": {
            "freshman": [38, 30, 16, 11, 5],
            "sophomore": [32, 28, 18, 14, 8],
            "junior": [26, 26, 16, 20, 12],
            "senior": [0, 24, 36, 26, 14],
        },
        "dev_weights": [46, 30, 14, 10],
        "prestige_range": (65, 85),
    },
    "blue_blood": {
        "label": "Blue Blood",
        "description": "Elite program. Loaded with talent across every position. The standard everyone else chases.",
        "stat_center": 64,             # best base in the game — but still needs development
        "stat_spread": 38,             # wide — elite in one stat, average in another
        "hidden_gem_count": (4, 6),    # stacked — stars everywhere
        "hidden_gem_boost": (5, 9),    # 57+7=64 → gems have highest ceiling for multipliers
        "hidden_gem_stats": (3, 5),
        "potential_weights": {
            "freshman": [50, 30, 12, 6, 2],
            "sophomore": [45, 28, 15, 8, 4],
            "junior": [35, 28, 18, 12, 7],
            "senior": [0, 32, 38, 20, 10],
        },
        "dev_weights": [40, 36, 14, 10],
        "prestige_range": (82, 99),
    },
}

# Weighted distribution for assigning archetypes to AI teams.
# Creates a realistic league: mostly average teams, fewer elite, a cadre of doormats.
# ~60% below regional power, ~22% regional, ~18% national/blue blood.
AI_ARCHETYPE_WEIGHTS = {
    "doormat": 12,
    "underdog": 24,
    "punching_above": 28,
    "regional_power": 22,
    "national_power": 10,
    "blue_blood": 4,
}

# Conference strength floors: minimum effective stat_center for teams in each
# conference.  The floor constrains the bottom — even the worst team in a strong
# conference can't generate below the threshold.  Max potential is unconstrained.
# Format: "Conference Name" -> minimum stat_center (after archetype + jitter).
# Conferences not listed have no floor (teams can be as bad as their archetype allows).
CONFERENCE_FLOORS = {
    "SEC": 25,           # range ~57-25 — worst SEC team still has a base to build on
    "Big Ten": 20,       # range ~54-20
    "ACC": 32,           # range ~50-32 — tight, consistently decent base
    "Big East": 18,      # range ~46-18
    "Yankee Conference": 28,  # range ~50-28 — high floor
    "Pac-12": 28,        # range ~52-28
    "Pac-16": 28,        # alias — Pac-12 may be renamed Pac-16
}

# Default archetype (matches existing generation behavior)
DEFAULT_ARCHETYPE = "regional_power"


def assign_archetype(position: str, speed: int, stamina: int,
                     kicking: int, lateral_skill: int, tackling: int) -> str:
    """Assign a gameplay archetype based on position and stats."""
    spd, kick, lat, stam, tck = speed, kicking, lateral_skill, stamina, tackling

    if "Zeroback" in position:
        if kick >= 80 and kick >= spd:
            return "kicking_zb"
        elif spd >= 90 and spd > kick + 5:
            return "running_zb"
        elif lat >= 85 and lat >= spd and lat >= kick:
            return "distributor_zb"
        else:
            return "dual_threat_zb"
    elif "Viper" in position:
        if lat >= 90 and spd >= 90:
            return "receiving_viper"
        elif tck >= 80 and stam >= 85:
            return "power_viper"
        elif spd >= 93 and lat < 85:
            return "decoy_viper"
        else:
            return "hybrid_viper"
    elif any(p in position for p in ["Halfback", "Wingback", "Slotback"]):
        if spd >= 93:
            return "speed_flanker"
        elif tck >= 80 and stam >= 88:
            return "power_flanker"
        elif lat >= 88 and spd >= 85:
            return "elusive_flanker"
        else:
            return "reliable_flanker"
    elif "Keeper" in position:
        if spd >= 90 and spd > tck:
            return "return_keeper"
        elif lat >= 85 and stam >= 85:
            return "sure_hands_keeper"
        else:
            return "tackle_keeper"
    return "none"


DATA_DIR = Path(__file__).parent.parent / 'data'

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

def _stat_roll(center, std):
    """Generate a single stat using gaussian distribution, clamped 10-85.

    Ceiling is 85 — in single-season mode this IS the final product, so no
    stat should feel elite at generation.  In dynasty mode, development
    pushes players past 85 over multiple seasons.
    """
    return max(10, min(85, int(round(random.gauss(center, std)))))


# Position-specific center offsets (added to archetype stat_center)
_POSITION_OFFSETS = {
    "Viper":          {'speed': 3, 'agility': 3, 'lateral_skill': 3, 'hands': 2},
    "Halfback":       {'speed': 3, 'agility': 3, 'lateral_skill': 3, 'hands': 2},
    "Wingback":       {'speed': 3, 'agility': 3, 'lateral_skill': 3, 'hands': 2},
    "Slotback":       {'speed': 3, 'agility': 3, 'lateral_skill': 3, 'hands': 2},
    "Offensive Line": {'power': 5, 'tackling': 4, 'stamina': 2,
                       'speed': -4, 'agility': -3, 'lateral_skill': -4,
                       'hands': -3, 'kicking': -4, 'kick_power': -3, 'kick_accuracy': -3},
    "Defensive Line": {'power': 5, 'tackling': 4, 'stamina': 2,
                       'speed': -4, 'agility': -3, 'lateral_skill': -4,
                       'hands': -3, 'kicking': -4, 'kick_power': -3, 'kick_accuracy': -3},
    "Zeroback":       {'awareness': 4, 'kicking': 5, 'kick_power': 4, 'kick_accuracy': 4},
    "Keeper":         {'tackling': 4, 'awareness': 3, 'hands': 2, 'speed': 1, 'power': 2},
}

# Philosophy-specific center offsets
_PHILOSOPHY_OFFSETS = {
    "kick_heavy":       {'kicking': 3, 'kick_power': 2, 'kick_accuracy': 2},
    "lateral_heavy":    {'lateral_skill': 3, 'agility': 2},
    "ground_and_pound": {'tackling': 2, 'stamina': 2, 'power': 2},
}

# All stat keys that are numeric ratings
_STAT_KEYS = [
    'speed', 'stamina', 'kicking', 'lateral_skill', 'tackling',
    'agility', 'power', 'awareness', 'hands', 'kick_power', 'kick_accuracy',
]


def generate_player_attributes(position, team_philosophy, year, is_viper=False,
                               program_archetype=None, team_center_offset=0):
    """Generate player stats using gaussian distribution shaped by program archetype.

    Each stat is rolled as gauss(center, spread) where center depends on the
    program's archetype (doormat→42, blue_blood→84) plus position, philosophy,
    viper, and class-year offsets.  All stats clamped to 15-99.

    Args:
        team_center_offset: Per-team jitter added to the archetype center so
            teams within the same tier aren't all identical OVR.  Rolled once
            per team in generate_team_on_the_fly().
    """
    archetype_data = PROGRAM_ARCHETYPES.get(program_archetype or DEFAULT_ARCHETYPE,
                                             PROGRAM_ARCHETYPES[DEFAULT_ARCHETYPE])
    center = archetype_data["stat_center"] + team_center_offset
    std = archetype_data["stat_spread"]

    # Gather all offsets
    pos_off = _POSITION_OFFSETS.get(position, {})
    phil_off = _PHILOSOPHY_OFFSETS.get(team_philosophy, {})
    viper_off = {'speed': 3, 'lateral_skill': 3, 'kicking': 2,
                 'agility': 2, 'awareness': 3} if is_viper else {}
    year_mod = {'freshman': -4, 'sophomore': -2, 'junior': 0, 'senior': 2}.get(year, 0)

    # Roll each stat
    results = {}
    for stat in _STAT_KEYS:
        stat_center = (center
                       + pos_off.get(stat, 0)
                       + phil_off.get(stat, 0)
                       + viper_off.get(stat, 0)
                       + year_mod)
        results[stat] = _stat_roll(stat_center, std)

    # ── Stat budget enforcement ──
    # Prevent "all 99s" players by capping the total stat points a player can
    # have.  The budget scales with archetype center so elite programs still
    # produce better players — but no one is elite at *everything*.
    # Budget = center * 11 + 44 (gives ~4 points of headroom per stat).
    # Example: blue_blood center 87 → budget 87*11+44 = 1001 → avg stat ~91.
    # A player who rolls 96 speed needs to sacrifice elsewhere.
    stat_budget = center * len(_STAT_KEYS) + 44
    stat_total = sum(results[s] for s in _STAT_KEYS)
    if stat_total > stat_budget:
        excess = stat_total - stat_budget
        # Shave excess from the highest stats first (preserves player profile —
        # their best stat stays best, it just gets trimmed)
        ranked = sorted(_STAT_KEYS, key=lambda s: results[s], reverse=True)
        for stat_key in ranked:
            if excess <= 0:
                break
            # Don't reduce any stat below the archetype center
            headroom = results[stat_key] - max(center, 15)
            trim = min(excess, headroom)
            if trim > 0:
                results[stat_key] -= trim
                excess -= trim

    # Height and weight
    if position in ("Offensive Line", "Defensive Line"):
        height_inches = random.randint(69, 75)  # 5'9" to 6'3"
        weight = random.randint(185, 215)
    elif position in ("Viper", "Halfback", "Wingback", "Slotback", "Keeper"):
        height_inches = random.randint(65, 72)  # 5'5" to 6'0"
        weight = random.randint(160, 190)
    else:
        height_inches = random.randint(67, 73)  # 5'7" to 6'1"
        weight = random.randint(170, 200)

    feet = height_inches // 12
    inches = height_inches % 12
    results['height'] = f"{feet}-{inches}"
    results['weight'] = weight

    # Potential (1-5 stars) — distribution driven by program archetype
    pot_weights = archetype_data["potential_weights"]
    year_key = year if year in pot_weights else "senior"
    year_weights = pot_weights[year_key]
    if len(year_weights) == 5:
        results['potential'] = random.choices([5, 4, 3, 2, 1], weights=year_weights)[0]
    elif len(year_weights) == 4:
        results['potential'] = random.choices([4, 3, 2, 1], weights=year_weights)[0]
    else:
        results['potential'] = random.choices([3, 4, 5, 2, 1], weights=[35, 30, 15, 15, 5])[0]

    # Development trait
    dev_weights = archetype_data.get("dev_weights", [60, 20, 12, 8])
    results['development'] = random.choices(
        ['normal', 'quick', 'slow', 'late_bloomer'],
        weights=dev_weights,
    )[0]

    return results

def assign_program_archetype(school_id):
    """Deterministically assign a program archetype from AI_ARCHETYPE_WEIGHTS.

    Uses a simple hash of school_id so the same school always gets the same
    archetype across regenerations (unless weights change).
    """
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(school_id))
    rng = random.Random(seed)
    archetypes = list(AI_ARCHETYPE_WEIGHTS.keys())
    weights = list(AI_ARCHETYPE_WEIGHTS.values())
    return rng.choices(archetypes, weights=weights, k=1)[0]


def generate_roster(school_data):
    """Generate a 36-player roster for a team."""

    school_id = school_data['school_id']
    school_name = school_data['school_name']
    state = school_data.get('state', '')
    identity = school_data.get('identity', {})
    philosophy = identity.get('philosophy', 'hybrid')

    # Build geo-based domestic pipeline from school location.
    # Any school-level overrides can supplement (not replace) the geo pipeline.
    geo_pipeline = build_geo_pipeline(state)
    stored_pipeline = school_data.get('recruiting_pipeline', {})
    if stored_pipeline:
        # Blend: use geo pipeline as base but amplify any regions explicitly boosted
        # by the school's stored pipeline (e.g. australian for Pacific schools)
        from scripts.generate_names import DOMESTIC_KEYS
        for key, val in stored_pipeline.items():
            if key not in DOMESTIC_KEYS:
                # Preserve international boosts from stored pipeline (they'll be
                # overridden by INTERNATIONAL_BASELINE in select_origin anyway,
                # but we keep the dict around for reference)
                pass
        # Use geo pipeline as the effective domestic pipeline
    recruiting_pipeline = geo_pipeline

    # Assign program archetype (determines talent level)
    program_arch = school_data.get('program_archetype') or assign_program_archetype(school_id)
    archetype_data = PROGRAM_ARCHETYPES.get(program_arch, PROGRAM_ARCHETYPES[DEFAULT_ARCHETYPE])
    print(f"  Generating roster for {school_name} [{archetype_data['label']}]...")

    roster = []
    used_numbers = set()

    # Distribute class years (roughly 9 per year)
    class_distribution = (
        ['freshman'] * 9 +
        ['sophomore'] * 9 +
        ['junior'] * 9 +
        ['senior'] * 9
    )
    random.shuffle(class_distribution)

    # Generate current year from class year
    current_year = 2027
    year_to_recruiting_class = {
        'senior': current_year - 3,
        'junior': current_year - 2,
        'sophomore': current_year - 1,
        'freshman': current_year
    }

    ROSTER_TEMPLATE = [
        ("Viper", True), ("Viper", False), ("Viper", False),
        ("Zeroback", False), ("Zeroback", False), ("Zeroback", False),
        ("Halfback", False), ("Halfback", False),
        ("Halfback", False), ("Halfback", False),
        ("Wingback", False), ("Wingback", False),
        ("Wingback", False), ("Wingback", False),
        ("Slotback", False), ("Slotback", False),
        ("Slotback", False), ("Slotback", False),
        ("Keeper", False), ("Keeper", False), ("Keeper", False),
        ("Offensive Line", False), ("Offensive Line", False),
        ("Offensive Line", False), ("Offensive Line", False),
        ("Offensive Line", False), ("Offensive Line", False),
        ("Offensive Line", False), ("Offensive Line", False),
        ("Defensive Line", False), ("Defensive Line", False),
        ("Defensive Line", False), ("Defensive Line", False),
        ("Defensive Line", False), ("Defensive Line", False),
        ("Defensive Line", False),
    ]

    for i, (position, is_viper) in enumerate(ROSTER_TEMPLATE):
        # Special handling for Viper (jersey #1 or low number)
        if is_viper and i == 0:
            number = 1
            used_numbers.add(number)
        else:
            # Generate jersey number
            while True:
                number = random.randint(2, 99)
                if number not in used_numbers:
                    used_numbers.add(number)
                    break

        # Get class year
        year = class_distribution[i]
        recruiting_class = year_to_recruiting_class[year]

        # Generate name
        player_name_data = generate_player_name(
            school_recruiting_pipeline=recruiting_pipeline,
            recruiting_class=recruiting_class,
            year=year
        )

        # Generate attributes
        attributes = generate_player_attributes(position, philosophy, year, is_viper,
                                                program_archetype=program_arch)

        # Compute archetype from position and stats
        archetype = assign_archetype(
            position,
            attributes['speed'],
            attributes['stamina'],
            attributes['kicking'],
            attributes['lateral_skill'],
            attributes['tackling']
        )

        # Build player data
        player = {
            'number': number,
            'name': player_name_data['full_name'],
            'position': position,
            'height': attributes['height'],
            'weight': attributes['weight'],
            'year': year.capitalize(),
            'hometown': player_name_data['hometown'],
            'high_school': player_name_data['high_school'],
            'nationality': player_name_data.get('nationality', 'American'),
            'archetype': archetype,
            'potential': attributes['potential'],
            'development': attributes['development'],
            'stats': {
                'speed': attributes['speed'],
                'stamina': attributes['stamina'],
                'kicking': attributes['kicking'],
                'lateral_skill': attributes['lateral_skill'],
                'tackling': attributes['tackling'],
                'agility': attributes['agility'],
                'power': attributes['power'],
                'awareness': attributes['awareness'],
                'hands': attributes['hands'],
                'kick_power': attributes['kick_power'],
                'kick_accuracy': attributes['kick_accuracy'],
            }
        }

        roster.append(player)

    # ── Hidden Gems ──
    # Every program has a few players who overperform their recruiting class.
    # For doormats this is critical — it's the one star player who gives them a shot.
    gem_count = random.randint(*archetype_data["hidden_gem_count"])
    gem_indices = random.sample(range(len(roster)), min(gem_count, len(roster)))
    for idx in gem_indices:
        player = roster[idx]
        boost = random.randint(*archetype_data["hidden_gem_boost"])
        n_stats = random.randint(*archetype_data["hidden_gem_stats"])
        boosted_stats = random.sample(_STAT_KEYS, min(n_stats, len(_STAT_KEYS)))
        for stat_key in boosted_stats:
            player['stats'][stat_key] = min(85, player['stats'][stat_key] + boost)

    # ── Program Icons ──
    # Doormats and underdogs get 1-2 players who can develop WAY beyond the
    # team's talent level.  These aren't stat-boosted today — they have elite
    # *ceiling* (potential 5, quick development).  They're the face of the
    # program: the player who makes a doormat worth watching.
    if program_arch in ("doormat", "underdog"):
        icon_count = 1
        if program_arch == "doormat":
            # Doormats always get 1, 40% chance of a second
            icon_count = 2 if random.random() < 0.40 else 1
        else:
            # Underdogs get 1 icon 60% of the time
            icon_count = 1 if random.random() < 0.60 else 0

        if icon_count > 0:
            # Pick non-lineman positions for icons (they should be visible stars)
            icon_eligible = [
                i for i, p in enumerate(roster)
                if p['position'] not in ('Offensive Line', 'Defensive Line')
            ]
            icon_indices = random.sample(
                icon_eligible, min(icon_count, len(icon_eligible))
            )
            for idx in icon_indices:
                player = roster[idx]
                player['potential'] = 5
                player['development'] = 'quick'
                player['program_icon'] = True

    # Sort by jersey number
    roster.sort(key=lambda p: p['number'])

    # Calculate team aggregate stats
    avg_speed = sum(p['stats']['speed'] for p in roster) // len(roster)
    avg_weight = sum(p['weight'] for p in roster) // len(roster)
    avg_stamina = sum(p['stats']['stamina'] for p in roster) // len(roster)
    kicking_strength = sum(p['stats']['kicking'] for p in roster) // len(roster)
    lateral_proficiency = sum(p['stats']['lateral_skill'] for p in roster) // len(roster)
    defensive_strength = sum(p['stats']['tackling'] for p in roster) // len(roster)

    # Generate head coach using the dedicated coach name generator
    # Coaches can be men or women (gender='random' picks ~45/45/10 female/male/neutral)
    coach_data = generate_coach_name(
        gender='random',
        age_range=(35, 62),
        team_philosophy=identity.get('philosophy', None),
        school_name=school_name
    )

    # ── Program Infrastructure ──
    # 5 attributes (1-10) that influence recruiting attractiveness.
    # Initialized from archetype; can be upgraded via dynasty investment.
    _INFRA_BY_ARCHETYPE = {
        "blue_blood":     {"facilities": (8, 10), "campus_life": (8, 10), "location": (7, 10), "coaching_development": (8, 10), "nil_program": (8, 10)},
        "national_power": {"facilities": (7, 9),  "campus_life": (7, 9),  "location": (6, 9),  "coaching_development": (7, 9),  "nil_program": (7, 9)},
        "regional_power": {"facilities": (5, 7),  "campus_life": (5, 7),  "location": (5, 8),  "coaching_development": (5, 7),  "nil_program": (5, 7)},
        "punching_above": {"facilities": (3, 6),  "campus_life": (4, 7),  "location": (3, 7),  "coaching_development": (3, 6),  "nil_program": (3, 5)},
        "underdog":       {"facilities": (2, 4),  "campus_life": (3, 6),  "location": (2, 6),  "coaching_development": (2, 4),  "nil_program": (2, 4)},
        "doormat":        {"facilities": (1, 3),  "campus_life": (2, 5),  "location": (1, 5),  "coaching_development": (1, 3),  "nil_program": (1, 2)},
    }
    infra_ranges = _INFRA_BY_ARCHETYPE.get(program_arch, _INFRA_BY_ARCHETYPE["regional_power"])
    program_infrastructure = {
        key: random.randint(*rng)
        for key, rng in infra_ranges.items()
    }

    return {
        'team_info': {
            'school_id': school_id,
            'school_name': school_name,
            'abbreviation': school_data['abbreviation'],
            'mascot': school_data['mascot'],
            'conference': school_data.get('conference_planned', 'Independent'),
            'city': school_data['city'],
            'state': school_data['state'],
            'colors': school_data['colors']
        },
        'program_archetype': program_arch,
        'program_infrastructure': program_infrastructure,
        'identity': identity,
        'recruiting_pipeline': recruiting_pipeline,
        'roster': {
            'size': 36,
            'players': roster
        },
        'team_stats': {
            'avg_speed': avg_speed,
            'avg_weight': avg_weight,
            'avg_stamina': avg_stamina,
            'kicking_strength': kicking_strength,
            'lateral_proficiency': lateral_proficiency,
            'defensive_strength': defensive_strength
        },
        'coaching': {
            'head_coach': coach_data['full_name'],
            'head_coach_gender': coach_data['gender'],
            'philosophy': coach_data['philosophy'],
            'coaching_style': coach_data['coaching_style'],
            'experience': f"{coach_data['years_experience']} years",
            'background': coach_data['background']
        }
    }

def main():
    """Generate rosters for specified schools or all schools."""

    parser = argparse.ArgumentParser(description='Generate Viperball team rosters')
    parser.add_argument('--schools', help='Comma-separated list of school IDs')
    parser.add_argument('--all', action='store_true', help='Generate rosters for all schools')
    args = parser.parse_args()

    # Load schools database
    with open(DATA_DIR / 'schools' / 'd1_non_football.json') as f:
        schools_data = json.load(f)

    # Determine which schools to process
    if args.all:
        schools_to_process = schools_data['schools']
    elif args.schools:
        school_ids = [s.strip() for s in args.schools.split(',')]
        schools_to_process = [s for s in schools_data['schools'] if s['school_id'] in school_ids]
    else:
        # Default: generate a few sample rosters
        sample_ids = ['gonzaga', 'villanova', 'vcu', 'marquette', 'ut_arlington']
        schools_to_process = [s for s in schools_data['schools'] if s['school_id'] in sample_ids]

    print(f"Generating rosters for {len(schools_to_process)} schools...\n")

    # Generate rosters
    for school in schools_to_process:
        roster_data = generate_roster(school)

        # Save to file
        output_path = DATA_DIR / 'teams' / f"{school['school_id']}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(roster_data, f, indent=2)

        print(f"    ✓ Saved to {output_path}")

    print(f"\n✅ Generated {len(schools_to_process)} team rosters")

if __name__ == "__main__":
    main()
