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

def generate_player_attributes(position, team_philosophy, year, is_viper=False):
    """Generate player stats based on position and team needs."""

    # Base ranges (core stats)
    base_speed = random.randint(75, 92)
    base_stamina = random.randint(80, 90)
    base_kicking = random.randint(60, 85)
    base_lateral_skill = random.randint(65, 90)
    base_tackling = random.randint(65, 88)

    # Extended attributes base ranges
    base_agility = random.randint(68, 90)
    base_power = random.randint(65, 88)
    base_awareness = random.randint(65, 88)
    base_hands = random.randint(65, 88)
    base_kick_power = random.randint(60, 85)
    base_kick_accuracy = random.randint(60, 85)

    # Adjust for position
    if position in ("Viper", "Halfback", "Wingback", "Slotback"):
        base_speed += random.randint(3, 8)
        base_lateral_skill += random.randint(3, 8)
        base_agility += random.randint(3, 8)
        base_hands += random.randint(3, 7)
    elif position in ("Offensive Line", "Defensive Line"):
        base_tackling += random.randint(3, 8)
        base_stamina += random.randint(2, 5)
        base_power += random.randint(5, 10)
        base_speed -= random.randint(3, 7)
        base_agility -= random.randint(2, 5)
    elif "Zeroback" in position:
        base_awareness += random.randint(4, 8)
        base_kick_power += random.randint(3, 7)
        base_kick_accuracy += random.randint(3, 7)
    elif position == "Keeper":
        base_speed += random.randint(2, 6)
        base_tackling += random.randint(5, 10)
        base_awareness += random.randint(3, 7)
        base_power += random.randint(2, 5)
        base_hands += random.randint(3, 7)

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

    # Apply modifier and cap at 100
    speed = min(100, max(60, base_speed + modifier))
    stamina = min(100, max(70, base_stamina + modifier))
    kicking = min(100, max(50, base_kicking + modifier))
    lateral_skill = min(100, max(55, base_lateral_skill + modifier))
    tackling = min(100, max(55, base_tackling + modifier))
    agility = min(100, max(55, base_agility + modifier))
    power = min(100, max(55, base_power + modifier))
    awareness = min(100, max(55, base_awareness + modifier))
    hands = min(100, max(55, base_hands + modifier))
    kick_power = min(100, max(50, base_kick_power + modifier))
    kick_accuracy = min(100, max(50, base_kick_accuracy + modifier))

    # Generate height and weight (women's athletes)
    if position in ("Offensive Line", "Defensive Line"):
        height_inches = random.randint(69, 75)  # 5'9" to 6'3"
        weight = random.randint(185, 215)
    elif position in ("Viper", "Halfback", "Wingback", "Slotback", "Keeper"):
        height_inches = random.randint(65, 72)  # 5'5" to 6'0"
        weight = random.randint(160, 190)
    else:
        height_inches = random.randint(67, 73)  # 5'7" to 6'1"
        weight = random.randint(170, 200)

    # Convert height to feet-inches
    feet = height_inches // 12
    inches = height_inches % 12
    height = f"{feet}-{inches}"

    # Generate potential (1-5 stars) — seniors rarely have 5-star potential
    if year == 'freshman':
        potential = random.choices([3, 4, 5, 2, 1], weights=[35, 30, 15, 15, 5])[0]
    elif year == 'sophomore':
        potential = random.choices([3, 4, 5, 2, 1], weights=[35, 28, 10, 20, 7])[0]
    elif year == 'junior':
        potential = random.choices([3, 4, 2, 5, 1], weights=[35, 25, 20, 8, 12])[0]
    else:  # senior
        potential = random.choices([3, 2, 4, 1], weights=[35, 30, 20, 15])[0]

    # Generate development trait
    development = random.choices(
        ['normal', 'quick', 'slow', 'late_bloomer'],
        weights=[60, 20, 12, 8]
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
