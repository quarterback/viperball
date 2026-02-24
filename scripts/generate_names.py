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

# Default pipeline: 66% domestic (US), 34% international
DEFAULT_PIPELINE = {
    # Domestic US (66%)
    'northeast': 0.12,
    'mid_atlantic': 0.10,
    'south': 0.12,
    'midwest': 0.12,
    'west_coast': 0.10,
    'texas_southwest': 0.10,
    # International (34%)
    'australian': 0.062,
    'canadian_english': 0.021,
    'canadian_french': 0.021,
    'new_zealand': 0.014,
    'pacific_islander': 0.004,
    'uk_european': 0.035,
    'latin_american': 0.012,
    'african': 0.019,
    'nordic': 0.100,
    'caribbean': 0.050,
    'other_intl': 0.003,
}

# International baseline (sums to 0.34) — applied on top of any school's domestic pipeline
INTERNATIONAL_BASELINE = {
    'australian': 0.062,
    'canadian_english': 0.021,
    'canadian_french': 0.021,
    'new_zealand': 0.014,
    'pacific_islander': 0.004,
    'uk_european': 0.035,
    'latin_american': 0.012,
    'african': 0.019,
    'nordic': 0.100,
    'caribbean': 0.050,
    'other_intl': 0.003,
}

# Keys considered domestic (US) regions
DOMESTIC_KEYS = {'northeast', 'mid_atlantic', 'south', 'midwest', 'west_coast', 'texas_southwest'}

# Map region -> (origin, nationality)
REGION_TO_ORIGIN = {
    'northeast': ('american', 'American'),
    'mid_atlantic': ('american', 'American'),
    'south': ('american', 'American'),
    'midwest': ('american', 'American'),
    'west_coast': ('american', 'American'),
    'texas_southwest': ('american', 'American'),
    'australian': ('australian', 'Australian'),
    'canadian_english': ('canadian_english', 'Canadian'),
    'canadian_french': ('canadian_french', 'Canadian'),
    'new_zealand': ('new_zealand', 'New Zealander'),
    'pacific_islander': ('pacific_islander', 'Pacific Islander'),
    'uk_european': ('uk_european', 'European'),
    'latin_american': ('latin_american', 'Latin American'),
    'african': ('african', 'African'),
    'caribbean': ('caribbean', 'Caribbean'),
    'nordic': ('nordic', 'Nordic'),
    'other_intl': ('irish_european', 'European'),
}

# Map US state abbreviations to primary recruiting region
STATE_TO_REGION: Dict[str, str] = {
    # Northeast
    'VT': 'northeast', 'ME': 'northeast', 'NH': 'northeast', 'MA': 'northeast',
    'RI': 'northeast', 'CT': 'northeast', 'NY': 'northeast', 'NJ': 'northeast',
    'PA': 'northeast',
    # Mid-Atlantic
    'DC': 'mid_atlantic', 'MD': 'mid_atlantic', 'VA': 'mid_atlantic',
    'DE': 'mid_atlantic', 'WV': 'mid_atlantic',
    # South
    'NC': 'south', 'SC': 'south', 'TN': 'south', 'GA': 'south', 'FL': 'south',
    'AL': 'south', 'MS': 'south', 'AR': 'south', 'KY': 'south', 'OK': 'south',
    'LA': 'south',
    # Midwest
    'OH': 'midwest', 'IN': 'midwest', 'IL': 'midwest', 'WI': 'midwest',
    'MI': 'midwest', 'MN': 'midwest', 'IA': 'midwest', 'MO': 'midwest',
    'ND': 'midwest', 'SD': 'midwest', 'NE': 'midwest', 'KS': 'midwest',
    # West Coast
    'CA': 'west_coast', 'OR': 'west_coast', 'WA': 'west_coast',
    'ID': 'west_coast', 'MT': 'west_coast',
    # Texas / Southwest
    'TX': 'texas_southwest', 'AZ': 'texas_southwest', 'NM': 'texas_southwest',
    'CO': 'texas_southwest', 'UT': 'texas_southwest', 'NV': 'texas_southwest',
    'WY': 'texas_southwest',
}

# Adjacent/neighboring regions for spillover recruiting
REGION_NEIGHBORS: Dict[str, List[str]] = {
    'northeast':       ['mid_atlantic', 'midwest'],
    'mid_atlantic':    ['northeast', 'south', 'midwest'],
    'south':           ['mid_atlantic', 'midwest', 'texas_southwest'],
    'midwest':         ['northeast', 'mid_atlantic', 'south', 'west_coast', 'texas_southwest'],
    'west_coast':      ['midwest', 'texas_southwest'],
    'texas_southwest': ['south', 'midwest', 'west_coast'],
}

def build_geo_pipeline(state: str) -> Dict[str, float]:
    """
    Build a domestic recruiting pipeline for a school based on its US state.

    Priority:
      - Home region: 50%
      - 1st neighbor: 20%
      - 2nd neighbor: 15%
      - Remaining regions split remaining 15%

    The international baseline is added automatically in select_origin().
    Returns only domestic region weights (will be normalized to 66% in select_origin).
    """
    home = STATE_TO_REGION.get(state, 'midwest')
    neighbors = REGION_NEIGHBORS.get(home, [])
    all_domestic = list(DOMESTIC_KEYS)
    others = [r for r in all_domestic if r != home and r not in neighbors]

    pipeline: Dict[str, float] = {home: 0.50}
    if neighbors:
        pipeline[neighbors[0]] = 0.20
        if len(neighbors) > 1:
            pipeline[neighbors[1]] = 0.15
        # Distribute remaining among further neighbors + others
        remaining = 0.15
        far = neighbors[2:] + others
        if far:
            per = remaining / len(far)
            for r in far:
                pipeline[r] = per
    else:
        # No neighbors — split evenly among others
        if others:
            per = 0.50 / len(others)
            for r in others:
                pipeline[r] = per
    return pipeline

def select_origin(recruiting_pipeline: Optional[Dict[str, float]] = None) -> Tuple[str, str]:
    """
    Select origin and region based on recruiting pipeline weights.

    When a school-specific pipeline is provided, its domestic region weights are
    normalized to 66% of the total, and the global international baseline (34%) is
    always blended in so every team reflects the league's international composition.

    Args:
        recruiting_pipeline: Dictionary of region weights

    Returns:
        Tuple of (origin, region)
    """
    if not recruiting_pipeline:
        pipeline = DEFAULT_PIPELINE
    else:
        # Separate domestic keys from any legacy international keys
        domestic = {k: v for k, v in recruiting_pipeline.items() if k in DOMESTIC_KEYS}
        if domestic:
            # Normalize domestic portion to 66% of total
            dom_total = sum(domestic.values())
            domestic_norm = {k: v / dom_total * 0.66 for k, v in domestic.items()}
        else:
            # Fallback: use default domestic distribution at 66%
            default_dom = {k: v for k, v in DEFAULT_PIPELINE.items() if k in DOMESTIC_KEYS}
            dom_total = sum(default_dom.values())
            domestic_norm = {k: v / dom_total * 0.66 for k, v in default_dom.items()}
        # Always use the global international baseline (34%)
        pipeline = {**domestic_norm, **INTERNATIONAL_BASELINE}

    # Normalize weights
    total = sum(pipeline.values())
    normalized = {k: v/total for k, v in pipeline.items()}

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

    # Map to origin
    if selected_region in REGION_TO_ORIGIN:
        origin, _ = REGION_TO_ORIGIN[selected_region]
    else:
        # Unknown region — default to american midwest
        origin = 'american'
        selected_region = 'midwest'

    return origin, selected_region

def select_first_name(origin: str, region: str, pools: Dict) -> str:
    """Select a first name based on origin and region."""
    first_names = pools['first_names']

    pool_key_map = {
        'american': {
            'northeast': 'american_northeast',
            'mid_atlantic': 'american_northeast',
            'south': 'american_south',
            'midwest': 'american_midwest',
            'west_coast': 'american_west',
            'texas_southwest': 'american_texas_southwest',
        },
        'australian': 'australian',
        'canadian_english': 'canadian_english',
        'canadian_french': 'canadian_french',
        'new_zealand': 'new_zealand',
        'pacific_islander': 'pacific_islander',
        'uk_european': 'uk_european',
        'latin_american': 'latin_american',
        'african': 'african',
        'caribbean': 'caribbean',
        'nordic': 'nordic',
        'irish_european': 'irish_european',
    }

    if origin == 'american':
        pool_key = pool_key_map['american'].get(region, 'american_midwest')
    elif origin in pool_key_map:
        pool_key = pool_key_map[origin]
    else:
        pool_key = 'american_midwest'

    if pool_key in first_names:
        return random.choice(first_names[pool_key])
    return random.choice(first_names['american_midwest'])

def select_surname(origin: str, region: str, pools: Dict) -> str:
    """Select a surname based on origin and region."""
    surnames = pools['surnames']

    if origin == 'american':
        # Mix of ethnic surnames weighted by region
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
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        rand = random.random()
        cumulative = 0
        selected_pool = 'american_general'
        for pool, weight in weights.items():
            cumulative += weight
            if rand <= cumulative:
                selected_pool = pool
                break
        if selected_pool not in surnames:
            selected_pool = 'american_general'

    elif origin == 'australian':
        selected_pool = 'australian'
    elif origin in ('canadian_english', 'canadian_french'):
        if origin == 'canadian_french':
            selected_pool = 'canadian_french'
        else:
            # English Canadian — mix of British + American surnames
            if random.random() < 0.4:
                selected_pool = random.choice(['irish', 'australian'])
            else:
                selected_pool = 'american_general'
    elif origin == 'new_zealand':
        selected_pool = 'new_zealand'
    elif origin == 'pacific_islander':
        selected_pool = 'pacific_islander'
    elif origin == 'uk_european':
        selected_pool = 'uk_european'
    elif origin == 'latin_american':
        selected_pool = 'latin_american'
    elif origin == 'african':
        selected_pool = 'african'
    elif origin == 'caribbean':
        selected_pool = 'caribbean'
    elif origin == 'nordic':
        selected_pool = 'nordic' if 'nordic' in surnames else 'scandinavian'
    elif origin == 'irish_european':
        selected_pool = 'irish'
    else:
        selected_pool = 'american_general'

    if selected_pool in surnames:
        return random.choice(surnames[selected_pool])
    return random.choice(surnames['american_general'])

def select_hometown(origin: str, region: str, pools: Dict) -> Dict[str, str]:
    """Select a hometown based on origin and region."""
    cities = pools['cities']

    if origin == 'australian':
        city_pool = cities['australia']['major'] + cities['australia']['secondary']
        city_full = random.choice(city_pool)
        parts = city_full.split()
        city = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
        state = parts[-1] if len(parts) > 1 else 'VIC'
        return {'city': city, 'state': state, 'country': 'Australia', 'region': 'australian'}

    elif origin == 'pacific_islander':
        city = random.choice(cities['pacific_islands'])
        if ' HI' in city:
            return {'city': city.replace(' HI', ''), 'state': 'HI', 'country': 'USA', 'region': 'pacific_islander'}
        else:
            return {'city': city, 'state': '', 'country': 'Pacific Islands', 'region': 'pacific_islander'}

    elif origin in ('canadian_english', 'canadian_french'):
        canada = cities['canada']
        city_pool = canada['major'] + canada['secondary'] + canada['small']
        city_full = random.choice(city_pool)
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        province = parts[1] if len(parts) > 1 else 'ON'
        return {'city': city, 'state': province, 'country': 'Canada', 'region': origin}

    elif origin == 'new_zealand':
        city = random.choice(cities['new_zealand'])
        return {'city': city, 'state': '', 'country': 'New Zealand', 'region': 'new_zealand'}

    elif origin == 'uk_european':
        uke = cities['uk_europe']
        all_cities = []
        for sub in uke.values():
            all_cities.extend(sub)
        city_full = random.choice(all_cities)
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        country_code = parts[1] if len(parts) > 1 else 'ENG'
        country_map = {
            'ENG': 'England', 'SCO': 'Scotland', 'WAL': 'Wales', 'NIR': 'Northern Ireland',
            'FRA': 'France', 'GER': 'Germany', 'ESP': 'Spain', 'NED': 'Netherlands',
            'BEL': 'Belgium', 'POR': 'Portugal', 'ITA': 'Italy',
            'SWE': 'Sweden', 'NOR': 'Norway', 'DEN': 'Denmark'
        }
        country = country_map.get(country_code, 'Europe')
        return {'city': city, 'state': country_code, 'country': country, 'region': 'uk_european'}

    elif origin == 'latin_american':
        la = cities['latin_america']
        all_cities = []
        for sub in la.values():
            all_cities.extend(sub)
        city_full = random.choice(all_cities)
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        country_code = parts[1] if len(parts) > 1 else 'BRA'
        country_map = {
            'BRA': 'Brazil', 'ARG': 'Argentina', 'COL': 'Colombia',
            'PER': 'Peru', 'CHI': 'Chile', 'MEX': 'Mexico',
            'VEN': 'Venezuela', 'URU': 'Uruguay', 'PAR': 'Paraguay',
            'ECU': 'Ecuador', 'CRC': 'Costa Rica', 'GTM': 'Guatemala', 'PAN': 'Panama'
        }
        country = country_map.get(country_code, 'Latin America')
        return {'city': city, 'state': country_code, 'country': country, 'region': 'latin_american'}

    elif origin == 'african':
        af = cities['africa']
        all_cities = []
        for sub in af.values():
            all_cities.extend(sub)
        city_full = random.choice(all_cities)
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        country_code = parts[1] if len(parts) > 1 else 'NGA'
        country_map = {
            'NGA': 'Nigeria', 'GHA': 'Ghana', 'SEN': 'Senegal', 'CIV': "Côte d'Ivoire",
            'GIN': 'Guinea', 'MLI': 'Mali', 'TOG': 'Togo',
            'KEN': 'Kenya', 'UGA': 'Uganda', 'TZA': 'Tanzania',
            'ETH': 'Ethiopia', 'RWA': 'Rwanda',
            'ZAF': 'South Africa', 'ZWE': 'Zimbabwe', 'ZMB': 'Zambia', 'BWA': 'Botswana'
        }
        country = country_map.get(country_code, 'Africa')
        return {'city': city, 'state': country_code, 'country': country, 'region': 'african'}

    elif origin == 'nordic':
        nrd = cities['nordic']
        all_cities = []
        for sub in nrd.values():
            all_cities.extend(sub)
        city_full = random.choice(all_cities)
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        country_code = parts[1] if len(parts) > 1 else 'FIN'
        country_map = {
            'FIN': 'Finland', 'SWE': 'Sweden', 'NOR': 'Norway'
        }
        country = country_map.get(country_code, 'Nordic')
        return {'city': city, 'state': country_code, 'country': country, 'region': 'nordic'}

    elif origin == 'caribbean':
        city_full = random.choice(cities['caribbean'])
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        country_code = parts[1] if len(parts) > 1 else 'JAM'
        country_map = {
            'JAM': 'Jamaica', 'TTO': 'Trinidad and Tobago', 'BRB': 'Barbados',
            'BAH': 'Bahamas', 'HAI': 'Haiti', 'DOM': 'Dominican Republic',
            'PRI': 'Puerto Rico', 'GUY': 'Guyana', 'SUR': 'Suriname',
            'LCA': 'Saint Lucia', 'DMA': 'Dominica', 'SKN': 'Saint Kitts',
            'GRN': 'Grenada', 'BEL': 'Belize'
        }
        country = country_map.get(country_code, 'Caribbean')
        return {'city': city, 'state': country_code, 'country': country, 'region': 'caribbean'}

    elif origin == 'irish_european':
        # Treat as UK/European
        uke = cities['uk_europe']
        eng_cities = uke.get('england', []) + uke.get('other_uk', [])
        city_full = random.choice(eng_cities) if eng_cities else 'London ENG'
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        return {'city': city, 'state': 'ENG', 'country': 'United Kingdom', 'region': 'uk_european'}

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
        parts = city_full.rsplit(' ', 1)
        city = parts[0]
        state = parts[1] if len(parts) > 1 else ''
        return {'city': city, 'state': state, 'country': 'USA', 'region': region}

def select_high_school(origin: str, hometown: Dict, pools: Dict) -> str:
    """Select a high school based on origin and hometown."""
    high_schools = pools['high_schools']

    if origin == 'australian':
        if random.random() < 0.3:
            return random.choice(high_schools['aflw_academies'])
        city = hometown['city'].lower()
        if city in high_schools['australian_real_schools']:
            return random.choice(high_schools['australian_real_schools'][city])
        template = random.choice(high_schools['australian_schools'])
        return template.replace('{City}', hometown['city'])

    elif origin == 'pacific_islander':
        return f"{hometown['city']} High School"

    elif origin in ('canadian_english', 'canadian_french'):
        return f"{hometown['city']} Secondary School"

    elif origin == 'new_zealand':
        return f"{hometown['city']} Girls' High School"

    elif origin in ('uk_european', 'irish_european'):
        return f"{hometown['city']} Academy"

    elif origin == 'latin_american':
        return f"Colegio {hometown['city']}"

    elif origin == 'african':
        return f"{hometown['city']} Secondary School"

    elif origin == 'caribbean':
        return f"{hometown['city']} High School"

    elif origin == 'nordic':
        country_code = hometown.get('state', 'FIN')
        if country_code == 'FIN':
            return f"{hometown['city']} lukio"
        elif country_code == 'SWE':
            return f"{hometown['city']} gymnasium"
        else:
            return f"{hometown['city']} videregående skole"

    else:  # American
        city = hometown['city'].lower().replace(' ', '_')
        if city in high_schools['real_schools']:
            return random.choice(high_schools['real_schools'][city])
        # Only use templates that have {City} and no other unresolved placeholders
        city_templates = [t for t in high_schools['templates'] if '{City}' in t and '{Name}' not in t and '{Mascot}' not in t]
        template = random.choice(city_templates if city_templates else ['{City} High School'])
        return template.replace('{City}', hometown['city'])

def get_nationality(origin: str, region: str) -> str:
    """Get nationality string from origin/region."""
    if origin == 'american':
        return 'American'
    key = region if region in REGION_TO_ORIGIN else origin
    _, nationality = REGION_TO_ORIGIN.get(key, ('american', 'American'))
    return nationality

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
        origin: Specific origin ('american', 'australian', 'canadian_english', etc.)
        region: Geographic region ('northeast', 'south', 'australian', 'canadian_french', etc.)
        school_recruiting_pipeline: School's recruiting territories (weighted dict)
        recruiting_class: Year the player was recruited
        year: Current class year (freshman/sophomore/junior/senior)

    Returns:
        Dictionary with player_id, first_name, last_name, display_name, full_name,
        hometown, high_school, origin_tags, nationality, recruiting_class, year
    """
    pools = load_name_pools()

    if not origin or not region:
        origin, region = select_origin(school_recruiting_pipeline)

    first_name = select_first_name(origin, region, pools)
    last_name = select_surname(origin, region, pools)

    display_name = f"{first_name[0]}. {last_name}"
    full_name = f"{first_name} {last_name}"

    hometown = select_hometown(origin, region, pools)
    high_school = select_high_school(origin, hometown, pools)

    origin_tags = [origin, region]
    nationality = get_nationality(origin, region)

    player_id = f"{first_name.lower().replace(' ', '_')}_{last_name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"

    return {
        'player_id': player_id,
        'first_name': first_name,
        'last_name': last_name,
        'display_name': display_name,
        'full_name': full_name,
        'hometown': hometown,
        'high_school': high_school,
        'origin_tags': origin_tags,
        'nationality': nationality,
        'recruiting_class': recruiting_class,
        'year': year
    }

if __name__ == "__main__":
    print("Testing Women's Name Generator for Viperball\n")

    print("1. American Northeast player:")
    player1 = generate_player_name(origin='american', region='northeast')
    print(json.dumps(player1, indent=2, ensure_ascii=False))

    print("\n2. Australian player:")
    player2 = generate_player_name(origin='australian', region='australian')
    print(json.dumps(player2, indent=2, ensure_ascii=False))

    print("\n3. Canadian French player:")
    player3 = generate_player_name(origin='canadian_french', region='canadian_french')
    print(json.dumps(player3, indent=2, ensure_ascii=False))

    print("\n4. African player:")
    player4 = generate_player_name(origin='african', region='african')
    print(json.dumps(player4, indent=2, ensure_ascii=False))

    print("\n5. Default pipeline (66/34 split):")
    counts = {}
    for _ in range(1000):
        _, region = select_origin()
        _, nat = REGION_TO_ORIGIN.get(region, ('american', 'American'))
        counts[nat] = counts.get(nat, 0) + 1
    for nat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {nat}: {count/10:.1f}%")
