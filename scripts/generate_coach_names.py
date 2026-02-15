#!/usr/bin/env python3
"""
Viperball Coach Name Generator

Generates realistic coach names (male, female, or gender-neutral)
with coaching backgrounds and philosophies.

Separate from player names - coaches are typically older (35-65 years old)
and have different name trends from current college players.

Usage:
    from scripts.generate_coach_names import generate_coach_name

    coach = generate_coach_name(
        gender='female',  # 'male', 'female', 'neutral', or 'random'
        age_range=(40, 55),
        former_player=False
    )
"""

import json
import random
from pathlib import Path
from typing import Dict, Optional, Tuple, Literal

# Coach-specific name pools (older generation names)
FEMALE_FIRST_NAMES = [
    # Classic/traditional (born 1970s-1980s)
    "Jennifer", "Michelle", "Lisa", "Amy", "Angela", "Melissa", "Kimberly",
    "Jessica", "Elizabeth", "Sarah", "Amanda", "Nicole", "Stephanie", "Rebecca",
    "Katherine", "Laura", "Christine", "Rachel", "Heather", "Kelly",

    # Professional sounding
    "Catherine", "Patricia", "Margaret", "Susan", "Carol", "Diane", "Janet",
    "Barbara", "Karen", "Nancy", "Linda", "Donna", "Sandra", "Sharon",

    # Modern but established
    "Courtney", "Kristen", "Megan", "Shannon", "Tracy", "Stacy", "Wendy",
    "Tiffany", "Kristin", "Andrea", "Danielle", "Monica", "Erica", "Alicia"
]

MALE_FIRST_NAMES = [
    # Classic coaching names
    "Michael", "David", "James", "John", "Robert", "William", "Richard",
    "Thomas", "Mark", "Steven", "Daniel", "Paul", "Brian", "Kevin",

    # Professional/authoritative
    "Christopher", "Matthew", "Andrew", "Joseph", "Timothy", "Scott", "Jeffrey",
    "Kenneth", "Eric", "Gregory", "Ronald", "Donald", "Gary", "Anthony",

    # Modern but established
    "Ryan", "Jason", "Justin", "Brandon", "Derek", "Travis", "Chad", "Brett",
    "Shawn", "Todd", "Kyle", "Craig", "Sean", "Nathan", "Aaron", "Adam"
]

NEUTRAL_FIRST_NAMES = [
    # Names that work across genders
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
    "Avery", "Quinn", "Cameron", "Dakota", "Drew", "Ryan", "Charlie",
    "Sage", "River", "Phoenix", "Skyler", "Ash", "Rowan", "Parker",
    "Emerson", "Finley", "Logan", "Blake", "Peyton", "Reese", "Harley"
]

# Surnames (coaching profession tends toward certain ethnic backgrounds)
COACHING_SURNAMES = [
    # Irish/Scottish (very common in coaching)
    "O'Brien", "McCarthy", "Sullivan", "Murphy", "Kelly", "Ryan", "Brennan",
    "Donnelly", "Callahan", "Flanagan", "MacLeod", "MacKenzie", "Campbell",
    "Ferguson", "Morrison", "Robertson", "MacDonald", "Fraser",

    # Italian (common in athletics)
    "Rossi", "Marino", "Romano", "Rizzo", "Conti", "Battaglia", "Ferrara",
    "Lombardi", "Antonelli", "Costello", "DeLuca", "DiMarco", "Gallo",

    # German/Dutch
    "Schmidt", "Mueller", "Wagner", "Weber", "Becker", "Hoffman", "Schneider",
    "Fischer", "Zimmerman", "Schultz", "Van Doren", "Van Dyke",

    # English/Anglo
    "Anderson", "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Lewis",

    # Polish/Eastern European
    "Kowalski", "Nowak", "Lewandowski", "Jankowski", "Wojcik", "Kaminski",
    "Petrov", "Ivanov", "Sokolov",

    # Diverse
    "Washington", "Jefferson", "Coleman", "Richardson", "Brooks", "Sanders",
    "Kim", "Lee", "Chen", "Patel", "Nguyen", "Rodriguez", "Hernandez"
]

# Coaching background templates
COACHING_BACKGROUNDS = [
    "Former college assistant promoted to head coach",
    "Veteran high school coach transitioning to college",
    "Professional athlete turned coach",
    "Long-time coordinator stepping into head role",
    "Rising star assistant with innovative schemes",
    "Former college player returning to alma mater",
    "Experienced coach hired from rival program",
    "First-time head coach with strong pedigree",
    "Turnaround specialist known for rebuilding programs",
    "Defense-minded tactician",
    "Offensive innovator"
]

# Coaching philosophies (these will match team identities)
PHILOSOPHIES = {
    'power_option': "Ground-based option attack with physical play",
    'lateral_spread': "Multiple lateral chains and perimeter speed",
    'territorial': "Field position battle with strategic kicking",
    'tempo_chaos': "Fast-paced, high-risk offensive tempo",
    'hybrid': "Balanced approach adapting to opponent",
    'defensive_first': "Defensive stability and ball control"
}

# Personality traits
PERSONALITY_TRAITS = [
    "demanding but fair", "players-first mentor", "tactical genius",
    "motivational leader", "detail-oriented strategist", "intense competitor",
    "calm under pressure", "innovative thinker", "disciplinarian",
    "relationship builder", "analytics-driven", "old-school fundamentalist"
]


def generate_coach_name(
    gender: Literal['male', 'female', 'neutral', 'random'] = 'random',
    age_range: Tuple[int, int] = (35, 65),
    former_player: bool = False,
    team_philosophy: Optional[str] = None,
    school_name: Optional[str] = None
) -> Dict:
    """
    Generate a coach profile with name, background, and philosophy.

    Args:
        gender: 'male', 'female', 'neutral', or 'random'
        age_range: Tuple of (min_age, max_age)
        former_player: If True, includes former player background
        team_philosophy: Team's offensive/defensive identity
        school_name: School where coach is employed

    Returns:
        Dictionary containing:
            - first_name
            - last_name
            - full_name
            - display_name (first initial + last name)
            - gender
            - age
            - years_experience
            - background
            - philosophy
            - personality
            - coaching_style
            - former_player (boolean)
    """

    # Select gender
    if gender == 'random':
        gender = random.choices(
            ['female', 'male', 'neutral'],
            weights=[0.45, 0.45, 0.10],  # Roughly equal with some neutral
            k=1
        )[0]

    # Select first name based on gender
    if gender == 'female':
        first_name = random.choice(FEMALE_FIRST_NAMES)
    elif gender == 'male':
        first_name = random.choice(MALE_FIRST_NAMES)
    else:  # neutral
        first_name = random.choice(NEUTRAL_FIRST_NAMES)

    # Select surname
    last_name = random.choice(COACHING_SURNAMES)

    # Generate age
    age = random.randint(age_range[0], age_range[1])

    # Calculate years of experience (typically age - 25 for when they started coaching)
    years_experience = max(1, age - 25 - random.randint(0, 5))

    # Create names
    full_name = f"{first_name} {last_name}"
    display_name = f"{first_name[0]}. {last_name}"

    # Generate coaching background
    if former_player:
        background = random.choice([
            "Former college player returning to alma mater",
            "Professional athlete turned coach",
            "Former All-American stepping into coaching"
        ])
    else:
        background = random.choice(COACHING_BACKGROUNDS)

    # Select philosophy (align with team or random)
    if team_philosophy and team_philosophy in PHILOSOPHIES:
        philosophy = PHILOSOPHIES[team_philosophy]
    else:
        philosophy = random.choice(list(PHILOSOPHIES.values()))

    # Determine coaching style based on philosophy
    if team_philosophy:
        if 'power' in team_philosophy or 'territorial' in team_philosophy:
            coaching_style = random.choice(['conservative', 'physical', 'methodical'])
        elif 'lateral' in team_philosophy or 'tempo' in team_philosophy:
            coaching_style = random.choice(['aggressive', 'innovative', 'risk-taking'])
        else:
            coaching_style = random.choice(['balanced', 'adaptive', 'flexible'])
    else:
        coaching_style = random.choice([
            'aggressive', 'conservative', 'balanced', 'innovative',
            'traditional', 'analytical', 'player-focused'
        ])

    # Select personality trait
    personality = random.choice(PERSONALITY_TRAITS)

    # Generate coach ID
    coach_id = f"coach_{first_name.lower()}_{last_name.lower()}_{random.randint(100, 999)}"

    return {
        'coach_id': coach_id,
        'first_name': first_name,
        'last_name': last_name,
        'full_name': full_name,
        'display_name': display_name,
        'gender': gender,
        'age': age,
        'years_experience': years_experience,
        'background': background,
        'philosophy': philosophy,
        'coaching_style': coaching_style,
        'personality': personality,
        'former_player': former_player,
        'school_name': school_name or 'Unassigned',
        'career_record': {
            'wins': 0,
            'losses': 0,
            'championships': 0
        }
    }


def generate_coaching_staff(
    head_coach_gender: str = 'random',
    team_philosophy: Optional[str] = None,
    school_name: Optional[str] = None
) -> Dict:
    """
    Generate a complete coaching staff (head coach + coordinators).

    Returns:
        Dictionary with head_coach, offensive_coordinator, defensive_coordinator
    """

    # Generate head coach
    head_coach = generate_coach_name(
        gender=head_coach_gender,
        age_range=(40, 65),
        team_philosophy=team_philosophy,
        school_name=school_name
    )

    # Generate coordinators (slightly younger)
    offensive_coordinator = generate_coach_name(
        gender='random',
        age_range=(32, 55),
        school_name=school_name
    )

    defensive_coordinator = generate_coach_name(
        gender='random',
        age_range=(32, 55),
        school_name=school_name
    )

    return {
        'head_coach': head_coach,
        'offensive_coordinator': offensive_coordinator,
        'defensive_coordinator': defensive_coordinator
    }


if __name__ == "__main__":
    print("Testing Viperball Coach Name Generator\n")
    print("=" * 60)

    print("\n1. Female head coach:")
    coach1 = generate_coach_name(gender='female', team_philosophy='power_option')
    print(json.dumps(coach1, indent=2))

    print("\n2. Male head coach:")
    coach2 = generate_coach_name(gender='male', team_philosophy='lateral_spread')
    print(json.dumps(coach2, indent=2))

    print("\n3. Gender-neutral coach:")
    coach3 = generate_coach_name(gender='neutral', team_philosophy='territorial')
    print(json.dumps(coach3, indent=2))

    print("\n4. Random coach (former player):")
    coach4 = generate_coach_name(
        gender='random',
        former_player=True,
        school_name='Villanova University'
    )
    print(json.dumps(coach4, indent=2))

    print("\n5. Full coaching staff:")
    staff = generate_coaching_staff(
        head_coach_gender='female',
        team_philosophy='tempo_chaos',
        school_name='Gonzaga University'
    )
    print(json.dumps(staff, indent=2))

    print("\n" + "=" * 60)
    print("✅ Coach name generator test complete!")
