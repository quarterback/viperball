#!/usr/bin/env python3
"""
Viperball Women's Player Name Generator

Generates realistic women's player names with hometowns, high schools,
and origin tagging to support recruiting pipelines.

Usage:
    from scripts.generate_names import generate_player_name

    player = generate_player_name(
        origin='american',
        region='northeast',
        school_recruiting_pipeline={'northeast': 0.5, 'mid_atlantic': 0.3}
    )
"""

import json
import random
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Constants
DATA_DIR = Path(__file__).parent.parent / 'data'
NAME_POOLS_DIR = DATA_DIR / 'name_pools'

# Load name pools (cached at module level)
_name_pools_cache = {}

def load_name_pools():
    """Load all name pool data files."""
    global _name_pools_cache

    if _name_pools_cache:
        return _name_pools_cache

    with open(NAME_POOLS_DIR / 'first_names.json') as f:
        first_names = json.load(f)

    with open(NAME_POOLS_DIR / 'surnames.json') as f:
        surnames = json.load(f)

    with open(NAME_POOLS_DIR / 'cities.json') as f:
        cities = json.load(f)

    with open(NAME_POOLS_DIR / 'high_schools.json') as f:
        high_schools = json.load(f)

    _name_pools_cache = {
        'first_names': first_names,
        'surnames': surnames,
        'cities': cities,
        'high_schools': high_schools
    }

    return _name_pools_cache

def select_origin(recruiting_pipeline: Optional[Dict[str, float]] = None) -> Tuple[str, str]:
    """
    Select origin and region based on recruiting pipeline weights.

    Args:
        recruiting_pipeline: Dictionary of region weights (e.g., {'northeast': 0.4, 'australian': 0.15})

    Returns:
        Tuple of (origin, region)
    """
    if not recruiting_pipeline:
        # Default weights: 75% American, 15% Australian, 10% other
        recruiting_pipeline = {
            'northeast': 0.15,
            'mid_atlantic': 0.15,
            'south': 0.15,
            'midwest': 0.15,
            'west_coast': 0.10,
            'texas_southwest': 0.05,
            'australian': 0.15,
            'pacific_islander': 0.05,
            'irish_european': 0.05
        }

    # Normalize weights
    total = sum(recruiting_pipeline.values())
    normalized = {k: v/total for k, v in recruiting_pipeline.items()}

    # Select region
    rand = random.random()
    cumulative = 0
    selected_region = None

    for region, weight in normalized.items():
        cumulative += weight
        if rand <= cumulative:
            selected_region = region
            break

    if not selected_region:
        selected_region = list(normalized.keys())[0]

    # Map region to origin
    american_regions = ['northeast', 'mid_atlantic', 'south', 'midwest', 'west_coast', 'texas_southwest']

    if selected_region in american_regions:
        origin = 'american'
    elif selected_region == 'australian':
        origin = 'australian'
    elif selected_region == 'pacific_islander':
        origin = 'pacific_islander'
    elif selected_region == 'irish_european':
        origin = 'irish_european'
    else:
        origin = 'american'
        selected_region = 'midwest'

    return origin, selected_region

def select_first_name(origin: str, region: str, pools: Dict) -> str:
    """Select a first name based on origin and region."""
    first_names = pools['first_names']

    # Map regions to name pools
    if origin == 'american':
        if region == 'northeast':
            pool_key = 'american_northeast'
        elif region == 'mid_atlantic':
            pool_key = 'american_northeast'  # Similar naming patterns
        elif region == 'south':
            pool_key = 'american_south'
        elif region == 'midwest':
            pool_key = 'american_midwest'
        elif region in ['west_coast', 'texas_southwest']:
            pool_key = 'american_west'
        else:
            pool_key = 'american_midwest'
    elif origin == 'australian':
        pool_key = 'australian'
    elif origin == 'pacific_islander':
        pool_key = 'pacific_islander'
    elif origin == 'irish_european':
        pool_key = 'irish_european'
    else:
        pool_key = 'american_midwest'

    # Select from appropriate pool
    if pool_key in first_names:
        return random.choice(first_names[pool_key])
    else:
        return random.choice(first_names['american_midwest'])

def select_surname(origin: str, region: str, pools: Dict) -> str:
    """Select a surname based on origin and region."""
    surnames = pools['surnames']

    # Determine surname pool based on origin
    if origin == 'american':
        # Mix of general American with some ethnic diversity
        weights = {
            'american_general': 0.50,
            'irish': 0.10,
            'italian': 0.08,
            'german': 0.07,
            'latino_hispanic': 0.10,
            'black_american': 0.08,
            'chinese': 0.02,
            'korean': 0.02,
            'vietnamese': 0.02,
            'filipino': 0.01
        }

        # Adjust weights based on region
        if region == 'northeast':
            weights['irish'] = 0.15
            weights['italian'] = 0.12
        elif region == 'south':
            weights['black_american'] = 0.15
            weights['latino_hispanic'] = 0.12
        elif region == 'texas_southwest':
            weights['latino_hispanic'] = 0.25
        elif region == 'west_coast':
            weights['latino_hispanic'] = 0.15
            weights['chinese'] = 0.05
            weights['filipino'] = 0.03

        # Normalize
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}

        # Select pool
        rand = random.random()
        cumulative = 0
        selected_pool = None

        for pool, weight in weights.items():
            cumulative += weight
            if rand <= cumulative:
                selected_pool = pool
                break

        if not selected_pool or selected_pool not in surnames:
            selected_pool = 'american_general'

    elif origin == 'australian':
        selected_pool = 'australian'
    elif origin == 'pacific_islander':
        selected_pool = 'pacific_islander'
    elif origin == 'irish_european':
        selected_pool = 'irish'
    else:
        selected_pool = 'american_general'

    return random.choice(surnames[selected_pool])

def select_hometown(origin: str, region: str, pools: Dict) -> Dict[str, str]:
    """Select a hometown based on origin and region."""
    cities = pools['cities']

    if origin == 'australian':
        city_pool = cities['australia']['major'] + cities['australia']['secondary']
        city_full = random.choice(city_pool)

        # Parse Australian city format "Melbourne VIC"
        parts = city_full.split()
        city = parts[0]
        state = parts[1] if len(parts) > 1 else 'VIC'

        return {
            'city': city,
            'state': state,
            'country': 'Australia',
            'region': 'australian'
        }

    elif origin == 'pacific_islander':
        city = random.choice(cities['pacific_islands'])
        # Parse format
        if ' HI' in city:
            return {
                'city': city.replace(' HI', ''),
                'state': 'HI',
                'country': 'USA',
                'region': 'pacific_islander'
            }
        else:
            return {
                'city': city,
                'state': '',
                'country': 'Pacific Islands',
                'region': 'pacific_islander'
            }

    else:  # American
        if region == 'northeast':
            city_pool = cities['northeast']['major'] + cities['northeast']['secondary']
        elif region == 'mid_atlantic':
            city_pool = cities['mid_atlantic']['major'] + cities['mid_atlantic']['secondary']
        elif region == 'south':
            city_pool = cities['south']['major'] + cities['south']['secondary']
        elif region == 'midwest':
            city_pool = cities['midwest']['major'] + cities['midwest']['secondary']
        elif region == 'west_coast':
            city_pool = cities['west_coast_california'] + cities['west_coast_northwest']
        elif region == 'texas_southwest':
            city_pool = cities['texas_southwest']['major'] + cities['texas_southwest']['secondary']
        else:
            city_pool = cities['midwest']['major']

        city_full = random.choice(city_pool)

        # Parse American city format "Atlanta GA"
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        state = parts[1] if len(parts) > 1 else ''

        return {
            'city': city,
            'state': state,
            'country': 'USA',
            'region': region
        }

def select_high_school(origin: str, hometown: Dict, pools: Dict) -> str:
    """Select a high school based on origin and hometown."""
    high_schools = pools['high_schools']

    if origin == 'australian':
        # Use AFLW academies or Australian schools
        if random.random() < 0.3:  # 30% chance of AFLW academy
            return random.choice(high_schools['aflw_academies'])
        else:
            city = hometown['city'].lower()
            if city in high_schools['australian_real_schools']:
                return random.choice(high_schools['australian_real_schools'][city])
            else:
                # Use template
                template = random.choice(high_schools['australian_schools'])
                return template.replace('{City}', hometown['city'])

    elif origin == 'pacific_islander':
        # Use simple high school name
        return f"{hometown['city']} High School"

    else:  # American
        city = hometown['city'].lower().replace(' ', '_')

        # Check if we have real schools for this city
        if city in high_schools['real_schools']:
            return random.choice(high_schools['real_schools'][city])
        else:
            # Use template
            template = random.choice(high_schools['templates'])
            return template.replace('{City}', hometown['city'])

def generate_player_name(
    origin: Optional[str] = None,
    region: Optional[str] = None,
    school_recruiting_pipeline: Optional[Dict[str, float]] = None,
    recruiting_class: int = 2024,
    year: str = 'freshman'
) -> Dict:
    """
    Generate a women's player name with hometown and background.

    Args:
        origin: Specific origin ('american', 'australian', 'pacific_islander')
        region: Geographic region ('northeast', 'south', 'midwest', 'west_coast', etc.)
        school_recruiting_pipeline: School's recruiting territories (weighted dict)
        recruiting_class: Year the player was recruited (default 2024)
        year: Current class year (freshman/sophomore/junior/senior)

    Returns:
        Dictionary containing:
            - first_name
            - last_name
            - display_name
            - full_name
            - hometown (dict)
            - high_school
            - origin_tags (list)
            - recruiting_class
            - year
            - player_id (unique identifier)
    """
    # Load name pools
    pools = load_name_pools()

    # Select origin and region if not provided
    if not origin or not region:
        origin, region = select_origin(school_recruiting_pipeline)

    # Generate name components
    first_name = select_first_name(origin, region, pools)
    last_name = select_surname(origin, region, pools)

    # Create display name (first initial + last name)
    display_name = f"{first_name[0]}. {last_name}"
    full_name = f"{first_name} {last_name}"

    # Generate hometown
    hometown = select_hometown(origin, region, pools)

    # Select high school
    high_school = select_high_school(origin, hometown, pools)

    # Create origin tags
    origin_tags = [origin, region]
    if origin == 'american':
        origin_tags.append(hometown['region'])

    # Generate unique player ID
    player_id = f"{first_name.lower()}_{last_name.lower()}_{random.randint(1000, 9999)}"

    return {
        'player_id': player_id,
        'first_name': first_name,
        'last_name': last_name,
        'display_name': display_name,
        'full_name': full_name,
        'hometown': hometown,
        'high_school': high_school,
        'origin_tags': origin_tags,
        'recruiting_class': recruiting_class,
        'year': year
    }

if __name__ == "__main__":
    # Test the name generator
    print("Testing Women's Name Generator for Viperball\n")

    print("1. American Northeast player:")
    player1 = generate_player_name(origin='american', region='northeast')
    print(json.dumps(player1, indent=2))

    print("\n2. Australian player:")
    player2 = generate_player_name(origin='australian', region='australian')
    print(json.dumps(player2, indent=2))

    print("\n3. Pacific Islander player:")
    player3 = generate_player_name(origin='pacific_islander', region='pacific_islander')
    print(json.dumps(player3, indent=2))

    print("\n4. Random player with custom recruiting pipeline:")
    pipeline = {
        'west_coast': 0.40,
        'australian': 0.30,
        'pacific_islander': 0.20,
        'midwest': 0.10
    }
    player4 = generate_player_name(school_recruiting_pipeline=pipeline)
    print(json.dumps(player4, indent=2))
