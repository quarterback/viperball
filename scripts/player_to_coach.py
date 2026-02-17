#!/usr/bin/env python3
"""
Viperball Player-to-Coach Conversion System

Converts graduating senior players into coaches, preserving their
complete playing history and deriving coaching tendencies from
their playing style and attributes.

This creates continuity in the dynasty mode - your star players
can return as coaches later in their careers.

Usage:
    from scripts.player_to_coach import convert_player_to_coach

    # Load a graduating senior
    senior_player = {...}  # Player data from roster

    # Convert to coach (happens 4-8 years after graduation)
    coach = convert_player_to_coach(
        player_data=senior_player,
        years_after_graduation=6,
        coaching_path='head_coach'  # or 'coordinator', 'position_coach'
    )
"""

import json
import random
from pathlib import Path
from typing import Dict, Optional, Literal
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / 'data'


def derive_coaching_style_from_position(position: str) -> Dict[str, any]:
    """
    Derive coaching philosophy and style from playing position.

    Different positions translate to different coaching strengths:
    - Zerobacks → Offensive minds, decision-making focus
    - Halfbacks → Running game specialists
    - Vipers → Big-picture thinkers, special teams focus
    - Linemen → Fundamentals, toughness, defense
    - Defensive backs → Coverage schemes, situational awareness
    """

    position_lower = position.lower()

    if 'zeroback' in position_lower:
        return {
            'offensive_specialty': 'Decision-making and option execution',
            'coaching_strength': 'Play calling and game management',
            'philosophy_tendency': 'ground_pound',
            'risk_tolerance': 'medium',
            'teaching_focus': 'Reads and decision trees'
        }

    elif 'halfback' in position_lower:
        return {
            'offensive_specialty': 'Running game and ball carrying',
            'coaching_strength': 'Physical play and toughness',
            'philosophy_tendency': 'ground_pound',
            'risk_tolerance': 'conservative',
            'teaching_focus': 'Fundamentals and physicality'
        }

    elif 'viper' in position_lower:
        return {
            'offensive_specialty': 'Explosiveness and special teams',
            'coaching_strength': 'Creating big plays and innovation',
            'philosophy_tendency': 'lateral_spread',
            'risk_tolerance': 'aggressive',
            'teaching_focus': 'Speed and special situations'
        }

    elif 'wingback' in position_lower or 'wing' in position_lower:
        return {
            'offensive_specialty': 'Perimeter attack and lateral game',
            'coaching_strength': 'Wide formations and pitch plays',
            'philosophy_tendency': 'lateral_spread',
            'risk_tolerance': 'aggressive',
            'teaching_focus': 'Spacing and perimeter execution'
        }

    elif 'shiftback' in position_lower:
        return {
            'offensive_specialty': 'Versatility and adaptability',
            'coaching_strength': 'Multiple formations and schemes',
            'philosophy_tendency': 'hybrid',
            'risk_tolerance': 'medium',
            'teaching_focus': 'Versatility and situational awareness'
        }

    elif 'lineman' in position_lower or 'wedge' in position_lower:
        return {
            'offensive_specialty': 'Line play and physicality',
            'coaching_strength': 'Toughness and fundamentals',
            'philosophy_tendency': 'ball_control',
            'risk_tolerance': 'conservative',
            'teaching_focus': 'Blocking and defensive fundamentals'
        }

    elif 'back' in position_lower or 'safety' in position_lower or 'corner' in position_lower:
        return {
            'offensive_specialty': 'Defensive schemes and coverage',
            'coaching_strength': 'Defensive strategy and positioning',
            'philosophy_tendency': 'defensive_first',
            'risk_tolerance': 'conservative',
            'teaching_focus': 'Defensive reads and tackling'
        }

    else:
        # Default
        return {
            'offensive_specialty': 'General offensive strategy',
            'coaching_strength': 'Player development',
            'philosophy_tendency': 'hybrid',
            'risk_tolerance': 'medium',
            'teaching_focus': 'Fundamentals and teamwork'
        }


def derive_coaching_tendencies_from_stats(player_stats: Dict) -> Dict:
    """
    Derive coaching tendencies from player's statistical profile.

    High-speed players → Prefer tempo offense
    High-kicking players → More territorial approach
    High-lateral players → Spread and lateral chains
    High-tackling players → Defensive-minded
    """

    speed = player_stats.get('speed', 75)
    kicking = player_stats.get('kicking', 70)
    lateral_skill = player_stats.get('lateral_skill', 70)
    tackling = player_stats.get('tackling', 70)
    stamina = player_stats.get('stamina', 80)

    # Determine primary tendency based on highest stat
    stats_map = {
        'speed': speed,
        'kicking': kicking,
        'lateral_skill': lateral_skill,
        'tackling': tackling
    }

    max_stat = max(stats_map, key=stats_map.get)
    max_value = stats_map[max_stat]

    # Derive coaching style
    if max_stat == 'speed' and speed >= 85:
        style = 'tempo_chaos'
        description = "Fast-paced, high-tempo offensive attack"
    elif max_stat == 'kicking' and kicking >= 80:
        style = 'boot_raid'
        description = "Field position battle with strategic kicking"
    elif max_stat == 'lateral_skill' and lateral_skill >= 85:
        style = 'lateral_spread'
        description = "Multiple lateral chains and perimeter speed"
    elif max_stat == 'tackling' and tackling >= 80:
        style = 'defensive_first'
        description = "Defensive stability and ball control"
    else:
        style = 'hybrid'
        description = "Balanced approach adapting to opponent"

    # Calculate coaching attribute modifiers
    offensive_rating = int((speed + lateral_skill) / 2)
    defensive_rating = int((tackling + stamina) / 2)
    special_teams_rating = int((kicking + speed) / 2)

    return {
        'preferred_style': style,
        'style_description': description,
        'offensive_rating': offensive_rating,
        'defensive_rating': defensive_rating,
        'special_teams_rating': special_teams_rating,
        'tempo_preference': min(100, speed + random.randint(-5, 5)),
        'risk_tolerance': min(100, lateral_skill + random.randint(-10, 10)),
        'defensive_focus': min(100, tackling + random.randint(-5, 5))
    }


def generate_coaching_career_path(
    graduation_year: int,
    years_after_graduation: int,
    coaching_path: Literal['position_coach', 'coordinator', 'head_coach'] = 'head_coach'
) -> list:
    """
    Generate a realistic coaching career progression.

    Most coaches:
    1. Graduate as player (year X)
    2. Position coach at small school (X+1 to X+3)
    3. Coordinator at mid-major (X+4 to X+7)
    4. Head coach at major program (X+8+)

    Accelerated path:
    1. Graduate (year X)
    2. Graduate assistant (X+1)
    3. Position coach (X+2 to X+4)
    4. Coordinator (X+5 to X+6)
    5. Head coach (X+7+)
    """

    career_stops = []
    current_year = graduation_year

    # Always start as grad assistant or position coach
    current_year += 1
    career_stops.append({
        'year': current_year,
        'role': 'Graduate Assistant',
        'school': 'Various',
        'duration': '1 year'
    })

    # Position coach (2-4 years)
    current_year += 1
    duration = random.randint(2, 4)
    career_stops.append({
        'year': current_year,
        'role': random.choice([
            'Running Backs Coach',
            'Defensive Backs Coach',
            'Special Teams Coordinator',
            'Offensive Assistant'
        ]),
        'school': random.choice([
            'Mid-major program',
            'Small college',
            'Assistant at alma mater'
        ]),
        'duration': f'{duration} years'
    })

    current_year += duration

    # If coordinator path, add coordinator role
    if coaching_path in ['coordinator', 'head_coach']:
        duration = random.randint(2, 4)
        career_stops.append({
            'year': current_year,
            'role': random.choice([
                'Offensive Coordinator',
                'Defensive Coordinator'
            ]),
            'school': random.choice([
                'Conference rival',
                'Rising program',
                'Alma mater'
            ]),
            'duration': f'{duration} years'
        })
        current_year += duration

    # If head coach, add current role
    if coaching_path == 'head_coach':
        current_year = graduation_year + years_after_graduation
        career_stops.append({
            'year': current_year,
            'role': 'Head Coach',
            'school': 'Current position',
            'duration': f'{datetime.now().year - current_year} years (current)'
        })

    return career_stops


def convert_player_to_coach(
    player_data: Dict,
    graduation_year: int = 2027,
    years_after_graduation: int = 6,
    coaching_path: Literal['position_coach', 'coordinator', 'head_coach'] = 'head_coach',
    hired_by_school: Optional[str] = None
) -> Dict:
    """
    Convert a graduating senior player into a coach profile.

    Preserves:
    - Complete player history (stats, awards, bio)
    - Playing career records
    - Position played
    - All biographical information

    Adds:
    - Coaching career path
    - Coaching tendencies (derived from playing style)
    - Coaching philosophy (based on player archetype)
    - Win-loss record as coach
    - Coaching personality

    Args:
        player_data: Full player data dictionary from roster
        graduation_year: Year the player graduated
        years_after_graduation: How many years later they're hired as coach (typically 4-10)
        coaching_path: What level they've reached ('position_coach', 'coordinator', 'head_coach')
        hired_by_school: Which school hired them (None = alma mater)

    Returns:
        Complete coach profile with preserved player history
    """

    # Extract player information
    player_name = player_data.get('name', 'Unknown Player')
    player_position = player_data.get('position', 'Back')
    player_number = player_data.get('number', 0)
    player_stats = player_data.get('stats', {})
    player_hometown = player_data.get('hometown', {})
    player_high_school = player_data.get('high_school', '')
    player_year = player_data.get('year', 'Senior')

    # Calculate current age (graduated ~22 years old, now X years later)
    current_age = 22 + years_after_graduation

    # Derive coaching style from position
    position_style = derive_coaching_style_from_position(player_position)

    # Derive coaching tendencies from stats
    stat_tendencies = derive_coaching_tendencies_from_stats(player_stats)

    # Generate coaching career path
    career_path = generate_coaching_career_path(
        graduation_year,
        years_after_graduation,
        coaching_path
    )

    # Determine coaching role title
    if coaching_path == 'head_coach':
        current_role = 'Head Coach'
    elif coaching_path == 'coordinator':
        current_role = random.choice(['Offensive Coordinator', 'Defensive Coordinator'])
    else:
        current_role = random.choice([
            'Running Backs Coach',
            'Defensive Backs Coach',
            'Special Teams Coordinator'
        ])

    # Calculate years of coaching experience
    years_coaching_experience = years_after_graduation - 1

    # Generate coaching personality (influenced by playing style)
    if player_stats.get('speed', 75) >= 85:
        personality = random.choice(['intense competitor', 'motivational leader', 'demanding but fair'])
    elif player_stats.get('tackling', 70) >= 80:
        personality = random.choice(['disciplinarian', 'detail-oriented strategist', 'old-school fundamentalist'])
    else:
        personality = random.choice(['players-first mentor', 'tactical genius', 'relationship builder'])

    # Generate coaching record (if head coach)
    if coaching_path == 'head_coach':
        seasons_as_hc = max(1, years_after_graduation - 6)
        avg_wins_per_season = random.randint(6, 10)
        total_wins = seasons_as_hc * avg_wins_per_season + random.randint(-3, 3)
        total_games = seasons_as_hc * 12
        total_losses = total_games - total_wins
        championships = max(0, seasons_as_hc // 3 - random.randint(0, 2))
    else:
        total_wins = 0
        total_losses = 0
        championships = 0

    # Create coach ID (preserves player name)
    coach_id = f"coach_{player_name.lower().replace(' ', '_')}_{random.randint(100, 999)}"

    # Build complete coach profile
    coach_profile = {
        # Current coach information
        'coach_id': coach_id,
        'name': player_name,  # SAME NAME as player
        'current_role': current_role,
        'current_team': hired_by_school or 'Alma mater',
        'age': current_age,
        'years_coaching_experience': years_coaching_experience,

        # Coaching philosophy (derived from playing career)
        'coaching_philosophy': {
            'preferred_style': stat_tendencies['preferred_style'],
            'style_description': stat_tendencies['style_description'],
            'offensive_rating': stat_tendencies['offensive_rating'],
            'defensive_rating': stat_tendencies['defensive_rating'],
            'special_teams_rating': stat_tendencies['special_teams_rating'],
            'tempo_preference': stat_tendencies['tempo_preference'],
            'risk_tolerance': stat_tendencies['risk_tolerance'],
            'defensive_focus': stat_tendencies['defensive_focus'],
            'specialty': position_style['offensive_specialty'],
            'strength': position_style['coaching_strength'],
            'teaching_focus': position_style['teaching_focus']
        },

        # Coaching personality
        'personality': personality,
        'coaching_style': random.choice(['aggressive', 'balanced', 'conservative', 'innovative']),

        # Coaching career path
        'coaching_career': {
            'career_path': career_path,
            'hired_year': graduation_year + years_after_graduation,
            'total_experience': years_coaching_experience
        },

        # Coaching record
        'career_record': {
            'wins': total_wins,
            'losses': total_losses,
            'win_percentage': round(total_wins / max(1, total_wins + total_losses), 3),
            'championships': championships,
            'seasons_as_head_coach': max(0, years_after_graduation - 6) if coaching_path == 'head_coach' else 0
        },

        # ========================================
        # PRESERVED PLAYING CAREER (FULL HISTORY)
        # ========================================
        'playing_career': {
            'position': player_position,
            'jersey_number': player_number,
            'years_played': [
                graduation_year - 3,
                graduation_year - 2,
                graduation_year - 1,
                graduation_year
            ],
            'playing_stats': player_stats,
            'hometown': player_hometown,
            'high_school': player_high_school,
            'class_year': player_year,

            # Placeholder for career stats (would be populated from game history)
            'career_totals': {
                'games_played': random.randint(36, 48),
                'rushing_yards': random.randint(500, 3000),
                'touchdowns': random.randint(5, 30),
                'tackles': random.randint(50, 200) if 'back' in player_position.lower() else 0,
                'kicks': random.randint(10, 100) if player_stats.get('kicking', 0) >= 75 else 0
            },

            # Awards and honors (generated based on stats)
            'awards': generate_player_awards(player_stats, graduation_year),

            # Complete player card preserved
            'full_player_data': player_data
        },

        # Biographical info (from playing days)
        'hometown': player_hometown,
        'high_school': player_high_school,
        'alma_mater': hired_by_school or 'Former program',

        # Metadata
        'is_former_player': True,
        'converted_from_player': True,
        'conversion_date': f"{graduation_year + years_after_graduation}"
    }

    return coach_profile


def generate_player_awards(player_stats: Dict, graduation_year: int) -> list:
    """Generate realistic awards based on player stats."""

    awards = []

    # All-Conference honors (most good players get this)
    if player_stats.get('speed', 75) >= 80 or player_stats.get('tackling', 70) >= 75:
        num_all_conf = random.randint(1, 3)
        for year_offset in range(num_all_conf):
            awards.append(f"All-Conference ({graduation_year - (3 - year_offset)})")

    # All-American (elite players only)
    if player_stats.get('speed', 75) >= 90 or player_stats.get('lateral_skill', 70) >= 88:
        if random.random() < 0.3:  # 30% chance
            awards.append(f"All-American ({graduation_year})")

    # Conference Player of the Year
    total_rating = sum(player_stats.values()) / len(player_stats)
    if total_rating >= 85 and random.random() < 0.15:
        awards.append(f"Conference Player of the Year ({graduation_year})")

    # Academic honors
    if random.random() < 0.4:
        awards.append(f"Academic All-Conference ({graduation_year - 1})")

    # Team captain
    awards.append(f"Team Captain ({graduation_year})")

    return awards if awards else ['Letter Winner']


if __name__ == "__main__":
    print("Testing Player-to-Coach Conversion System\n")
    print("=" * 70)

    # Example: Create a sample graduating senior
    sample_player = {
        'number': 1,
        'name': 'Sarah Martinez',
        'position': 'Viper/Back',
        'height': '5-9',
        'weight': 175,
        'year': 'Senior',
        'hometown': {
            'city': 'Seattle',
            'state': 'WA',
            'country': 'USA',
            'region': 'west_coast'
        },
        'high_school': 'Garfield High School',
        'stats': {
            'speed': 92,
            'stamina': 85,
            'kicking': 78,
            'lateral_skill': 90,
            'tackling': 72
        }
    }

    print("\n1. Original Player Profile:")
    print(json.dumps(sample_player, indent=2))

    print("\n" + "=" * 70)
    print("\n2. Convert to Head Coach (6 years after graduation):")
    coach = convert_player_to_coach(
        player_data=sample_player,
        graduation_year=2027,
        years_after_graduation=6,
        coaching_path='head_coach',
        hired_by_school='Gonzaga University'
    )
    print(json.dumps(coach, indent=2))

    print("\n" + "=" * 70)
    print("\n3. Convert to Coordinator (4 years after graduation):")
    coordinator = convert_player_to_coach(
        player_data=sample_player,
        graduation_year=2027,
        years_after_graduation=4,
        coaching_path='coordinator',
        hired_by_school='Villanova University'
    )
    print(json.dumps(coordinator, indent=2))

    print("\n" + "=" * 70)
    print("✅ Player-to-Coach conversion test complete!")
    print("\nKey features demonstrated:")
    print("  • Full player history preserved")
    print("  • Coaching tendencies derived from playing stats")
    print("  • Realistic career progression")
    print("  • Awards and honors tracked")
    print("  • Same name maintained across careers")
