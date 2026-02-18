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
        "talent_offset": -12,         # big penalty to all base rolls
        "floor_adjust": -8,           # lower the stat floor too
        "hidden_gem_count": (1, 2),   # 1-2 players get a big boost
        "hidden_gem_boost": (10, 18), # those players get +10 to +18
        "potential_weights": {         # mostly low-potential players
            "freshman": [20, 10, 2, 28, 40],    # [5,4,3,2,1]-star weights
            "sophomore": [15, 8, 2, 30, 45],
            "junior": [8, 5, 0, 35, 52],
            "senior": [0, 5, 30, 30, 35],
        },
        "dev_weights": [50, 10, 30, 10],  # normal, quick, slow, late_bloomer
        "prestige_range": (10, 25),
    },
    "underdog": {
        "label": "Underdogs",
        "description": "Below average but scrappy. A few solid players make them competitive on any given day.",
        "talent_offset": -7,
        "floor_adjust": -4,
        "hidden_gem_count": (2, 3),
        "hidden_gem_boost": (8, 14),
        "potential_weights": {
            "freshman": [25, 18, 5, 25, 27],
            "sophomore": [20, 15, 5, 28, 32],
            "junior": [12, 10, 3, 30, 45],
            "senior": [0, 10, 30, 30, 30],
        },
        "dev_weights": [55, 15, 20, 10],
        "prestige_range": (22, 40),
    },
    "punching_above": {
        "label": "Punching Above Their Weight",
        "description": "Mid-tier program with surprising talent. Well-coached and greater than the sum of their parts.",
        "talent_offset": -3,
        "floor_adjust": -2,
        "hidden_gem_count": (2, 4),
        "hidden_gem_boost": (6, 12),
        "potential_weights": {
            "freshman": [30, 25, 10, 20, 15],
            "sophomore": [25, 22, 8, 25, 20],
            "junior": [18, 18, 5, 30, 29],
            "senior": [0, 15, 35, 30, 20],
        },
        "dev_weights": [55, 22, 13, 10],
        "prestige_range": (38, 55),
    },
    "regional_power": {
        "label": "Regional Power",
        "description": "Strong program that dominates their region. Solid roster top to bottom.",
        "talent_offset": 0,
        "floor_adjust": 0,
        "hidden_gem_count": (3, 5),
        "hidden_gem_boost": (5, 10),
        "potential_weights": {
            "freshman": [35, 30, 15, 15, 5],
            "sophomore": [30, 28, 10, 20, 12],
            "junior": [25, 25, 8, 25, 17],
            "senior": [0, 20, 35, 30, 15],
        },
        "dev_weights": [60, 20, 12, 8],
        "prestige_range": (52, 72),
    },
    "national_power": {
        "label": "National Power",
        "description": "Top-tier program that competes for championships. Deep roster with multiple stars.",
        "talent_offset": 5,
        "floor_adjust": 3,
        "hidden_gem_count": (4, 6),
        "hidden_gem_boost": (4, 8),
        "potential_weights": {
            "freshman": [40, 32, 18, 8, 2],
            "sophomore": [35, 30, 15, 15, 5],
            "junior": [28, 28, 12, 22, 10],
            "senior": [0, 25, 40, 25, 10],
        },
        "dev_weights": [55, 28, 10, 7],
        "prestige_range": (68, 85),
    },
    "blue_blood": {
        "label": "Blue Blood",
        "description": "Elite program. Loaded with talent across every position. The standard everyone else chases.",
        "talent_offset": 10,
        "floor_adjust": 5,
        "hidden_gem_count": (5, 8),
        "hidden_gem_boost": (3, 7),
        "potential_weights": {
            "freshman": [45, 35, 15, 4, 1],
            "sophomore": [40, 32, 18, 8, 2],
            "junior": [32, 30, 15, 18, 5],
            "senior": [0, 30, 40, 22, 8],
        },
        "dev_weights": [50, 32, 10, 8],
        "prestige_range": (82, 99),
    },
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
    elif any(p in position for p in ["Halfback", "Wingback", "Shiftback", "Wing"]):
        if spd >= 93:
            return "speed_flanker"
        elif tck >= 80 and stam >= 88:
            return "power_flanker"
        elif lat >= 88 and spd >= 85:
            return "elusive_flanker"
        else:
            return "reliable_flanker"
    elif any(p in position for p in ["Safety", "Keeper", "Corner"]):
        if spd >= 90 and spd > tck:
            return "return_keeper"
        elif lat >= 85 and stam >= 85:
            return "sure_hands_keeper"
        else:
            return "tackle_keeper"
    return "none"


DATA_DIR = Path(__file__).parent.parent / 'data'

POSITIONS = [
    "Zeroback/Back",
    "Halfback/Back",
    "Wingback/End",
    "Shiftback/Back",
    "Viper/Back",
    "Lineman",
    "Back/Safety",
    "Back/Corner",
    "Wedge/Line",
    "Wing/End"
]

def generate_player_attributes(position, team_philosophy, year, is_viper=False,
                               program_archetype=None):
    """Generate player stats based on position, team needs, and program archetype.

    Args:
        position: Player position string.
        team_philosophy: Team's playing philosophy (kick_heavy, lateral_heavy, etc.).
        year: Class year (freshman, sophomore, junior, senior).
        is_viper: Whether this is the team's Viper player.
        program_archetype: Optional program archetype key from PROGRAM_ARCHETYPES.
                          Affects base talent level and stat floors.
    """
    archetype_data = PROGRAM_ARCHETYPES.get(program_archetype or DEFAULT_ARCHETYPE,
                                             PROGRAM_ARCHETYPES[DEFAULT_ARCHETYPE])
    talent_offset = archetype_data["talent_offset"]
    floor_adj = archetype_data["floor_adjust"]

    # Base ranges (core stats) adjusted by archetype talent offset
    base_speed = random.randint(75, 92) + talent_offset
    base_stamina = random.randint(80, 90) + talent_offset
    base_kicking = random.randint(60, 85) + talent_offset
    base_lateral_skill = random.randint(65, 90) + talent_offset
    base_tackling = random.randint(65, 88) + talent_offset

    # Extended attributes base ranges
    base_agility = random.randint(68, 90) + talent_offset
    base_power = random.randint(65, 88) + talent_offset
    base_awareness = random.randint(65, 88) + talent_offset
    base_hands = random.randint(65, 88) + talent_offset
    base_kick_power = random.randint(60, 85) + talent_offset
    base_kick_accuracy = random.randint(60, 85) + talent_offset

    # Adjust for position
    if "Viper" in position or "Back" in position:
        base_speed += random.randint(3, 8)
        base_lateral_skill += random.randint(3, 8)
        base_agility += random.randint(3, 8)
        base_hands += random.randint(3, 7)
    elif "Lineman" in position or "Wedge" in position:
        base_tackling += random.randint(3, 8)
        base_stamina += random.randint(2, 5)
        base_power += random.randint(5, 10)
        base_speed -= random.randint(3, 7)
        base_agility -= random.randint(2, 5)
    elif "Wing" in position:
        base_speed += random.randint(2, 5)
        base_lateral_skill += random.randint(2, 5)
        base_agility += random.randint(2, 5)
    elif "Zeroback" in position:
        base_awareness += random.randint(4, 8)
        base_kick_power += random.randint(3, 7)
        base_kick_accuracy += random.randint(3, 7)
    elif any(p in position for p in ["Safety", "Keeper", "Corner"]):
        base_awareness += random.randint(3, 7)
        base_tackling += random.randint(2, 6)

    # Adjust for team philosophy
    if team_philosophy == 'kick_heavy':
        base_kicking += random.randint(5, 10)
        base_kick_power += random.randint(3, 7)
        base_kick_accuracy += random.randint(3, 7)
    elif team_philosophy == 'lateral_heavy':
        base_lateral_skill += random.randint(5, 10)
        base_agility += random.randint(3, 6)
    elif team_philosophy == 'ground_and_pound':
        base_tackling += random.randint(3, 7)
        base_stamina += random.randint(3, 7)
        base_power += random.randint(3, 6)

    # Viper gets boosted stats
    if is_viper:
        base_speed += random.randint(2, 5)
        base_lateral_skill += random.randint(3, 6)
        base_kicking += random.randint(2, 5)
        base_agility += random.randint(2, 4)
        base_awareness += random.randint(3, 6)

    # Class year modifiers
    if year == 'freshman':
        modifier = -5
    elif year == 'sophomore':
        modifier = -2
    elif year == 'junior':
        modifier = 0
    elif year == 'senior':
        modifier = +3
    else:
        modifier = 0

    # Apply modifier and cap — floors adjusted by archetype
    speed = min(100, max(60 + floor_adj, base_speed + modifier))
    stamina = min(100, max(70 + floor_adj, base_stamina + modifier))
    kicking = min(100, max(50 + floor_adj, base_kicking + modifier))
    lateral_skill = min(100, max(55 + floor_adj, base_lateral_skill + modifier))
    tackling = min(100, max(55 + floor_adj, base_tackling + modifier))
    agility = min(100, max(55 + floor_adj, base_agility + modifier))
    power = min(100, max(55 + floor_adj, base_power + modifier))
    awareness = min(100, max(55 + floor_adj, base_awareness + modifier))
    hands = min(100, max(55 + floor_adj, base_hands + modifier))
    kick_power = min(100, max(50 + floor_adj, base_kick_power + modifier))
    kick_accuracy = min(100, max(50 + floor_adj, base_kick_accuracy + modifier))

    # Generate height and weight (women's athletes)
    if "Lineman" in position or "Wedge" in position:
        height_inches = random.randint(69, 75)  # 5'9" to 6'3"
        weight = random.randint(185, 215)
    elif "Viper" in position or "Back" in position:
        height_inches = random.randint(65, 72)  # 5'5" to 6'0"
        weight = random.randint(160, 190)
    else:
        height_inches = random.randint(67, 73)  # 5'7" to 6'1"
        weight = random.randint(170, 200)

    # Convert height to feet-inches
    feet = height_inches // 12
    inches = height_inches % 12
    height = f"{feet}-{inches}"

    # Generate potential (1-5 stars) — distribution driven by program archetype
    pot_weights = archetype_data["potential_weights"]
    year_key = year if year in pot_weights else "senior"
    year_weights = pot_weights[year_key]  # [5-star, 4-star, 3-star, 2-star, 1-star]
    if len(year_weights) == 5:
        potential = random.choices([5, 4, 3, 2, 1], weights=year_weights)[0]
    elif len(year_weights) == 4:
        potential = random.choices([4, 3, 2, 1], weights=year_weights)[0]
    else:
        potential = random.choices([3, 4, 5, 2, 1], weights=[35, 30, 15, 15, 5])[0]

    # Generate development trait — archetype-driven distribution
    dev_weights = archetype_data.get("dev_weights", [60, 20, 12, 8])
    development = random.choices(
        ['normal', 'quick', 'slow', 'late_bloomer'],
        weights=dev_weights,
    )[0]

    return {
        'speed': speed,
        'stamina': stamina,
        'kicking': kicking,
        'lateral_skill': lateral_skill,
        'tackling': tackling,
        'agility': agility,
        'power': power,
        'awareness': awareness,
        'hands': hands,
        'kick_power': kick_power,
        'kick_accuracy': kick_accuracy,
        'height': height,
        'weight': weight,
        'potential': potential,
        'development': development,
    }

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

    print(f"  Generating roster for {school_name}...")

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

    for i in range(36):
        # Assign position
        if i < 5:
            position = "Lineman"
        elif i < 10:
            position = random.choice(["Back/Safety", "Back/Corner"])
        elif i < 15:
            position = random.choice(["Wingback/End", "Wing/End"])
        elif i < 20:
            position = random.choice(["Halfback/Back", "Shiftback/Back"])
        elif i < 25:
            position = random.choice(["Zeroback/Back", "Viper/Back"])
        else:
            position = random.choice(POSITIONS)

        # Special handling for Viper (jersey #1 or low number)
        is_viper = (i == 0)  # First player is Viper
        if is_viper:
            position = "Viper/Back"
            number = 1
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
        attributes = generate_player_attributes(position, philosophy, year, is_viper)

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
