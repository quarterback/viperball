"""
Viperball Weather System

Generates realistic, location-aware weather conditions for game day simulation.
Weather is determined by the home team's state and the week of the season.

The Viperball season runs approximately September through January:
  Weeks 1-4:   early fall (September)
  Weeks 5-10:  late fall (October–November)
  Weeks 11-13: early winter (December)
  Weeks 14+:   winter (January / bowl season)

Usage:
    from engine.weather import generate_game_weather, get_weather_description

    weather_key = generate_game_weather(state='WI', week=11)
    # → 'snow'

    info = get_weather_description(weather_key)
    # → {'label': 'Snow', 'description': '...', 'temp_range': '20–32°F', ...}
"""

import random
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Climate zone definitions
# ---------------------------------------------------------------------------

# US state → climate zone
STATE_CLIMATE: Dict[str, str] = {
    # New England (cold, snowy)
    'VT': 'new_england', 'ME': 'new_england', 'NH': 'new_england',
    'MA': 'new_england', 'RI': 'new_england', 'CT': 'new_england',
    # Mid-Atlantic (moderate, some snow)
    'NY': 'mid_atlantic', 'NJ': 'mid_atlantic', 'PA': 'mid_atlantic',
    'DC': 'mid_atlantic', 'MD': 'mid_atlantic', 'VA': 'mid_atlantic',
    'DE': 'mid_atlantic', 'WV': 'mid_atlantic',
    # Southeast (warm, humid, occasional rain)
    'NC': 'southeast', 'SC': 'southeast', 'GA': 'southeast', 'FL': 'southeast',
    # Deep South / Gulf (hot, thunderstorm-prone)
    'AL': 'deep_south', 'MS': 'deep_south', 'LA': 'deep_south',
    'AR': 'deep_south', 'OK': 'deep_south',
    # Appalachian / Upper South
    'TN': 'appalachian', 'KY': 'appalachian',
    # Northern Midwest (very cold winters)
    'MN': 'midwest_north', 'WI': 'midwest_north', 'MI': 'midwest_north',
    'ND': 'midwest_north', 'SD': 'midwest_north',
    # Central Midwest (cold/variable)
    'OH': 'midwest_central', 'IN': 'midwest_central', 'IL': 'midwest_central',
    'IA': 'midwest_central', 'MO': 'midwest_central', 'NE': 'midwest_central',
    'KS': 'midwest_central',
    # Texas / Arid Southwest (hot, dry)
    'TX': 'texas_arid', 'NM': 'texas_arid', 'AZ': 'texas_arid',
    'NV': 'texas_arid',
    # Mountain West (heavy snow, cold)
    'CO': 'mountain', 'UT': 'mountain', 'WY': 'mountain',
    'ID': 'mountain', 'MT': 'mountain',
    # Pacific Northwest (rainy, mild)
    'WA': 'pacific_northwest', 'OR': 'pacific_northwest',
    # California (mild, mostly dry)
    'CA': 'california',
}

# ---------------------------------------------------------------------------
# Weather probability tables
# ---------------------------------------------------------------------------
# Format: {climate_zone: {season_period: [clear, rain, snow, sleet, heat, wind]}}
# Weights do NOT need to sum to 100 (they will be normalized)

WEATHER_TABLE: Dict[str, Dict[str, list]] = {
    'new_england': {
        'early_fall':   [55, 20,  0,  0,  5, 20],
        'late_fall':    [38, 25,  9,  3,  0, 25],
        'early_winter': [32, 18, 22, 10,  0, 18],
        'winter':       [28, 15, 30, 15,  0, 12],
    },
    'mid_atlantic': {
        'early_fall':   [58, 20,  0,  0,  5, 17],
        'late_fall':    [44, 25,  6,  1,  0, 24],
        'early_winter': [38, 22, 17,  6,  0, 17],
        'winter':       [36, 20, 22, 10,  0, 12],
    },
    'southeast': {
        'early_fall':   [48, 32,  0,  0, 12,  8],
        'late_fall':    [58, 27,  0,  0,  2,  8],
        'early_winter': [62, 25,  1,  0,  0,  9],
        'winter':       [62, 27,  2,  0,  0,  8],
    },
    'deep_south': {
        'early_fall':   [42, 35,  0,  0, 14,  6],
        'late_fall':    [55, 30,  0,  0,  3,  8],
        'early_winter': [58, 28,  0,  0,  0,  9],
        'winter':       [58, 29,  2,  0,  0,  8],
    },
    'appalachian': {
        'early_fall':   [50, 22,  0,  0,  8, 20],
        'late_fall':    [40, 24,  8,  2,  2, 24],
        'early_winter': [36, 22, 20,  7,  0, 15],
        'winter':       [33, 20, 24,  9,  0, 14],
    },
    'midwest_north': {
        'early_fall':   [48, 20,  2,  0,  5, 25],
        'late_fall':    [38, 20, 16,  6,  0, 20],
        'early_winter': [28, 14, 32, 12,  0, 14],
        'winter':       [25, 10, 38, 17,  0, 10],
    },
    'midwest_central': {
        'early_fall':   [50, 22,  0,  0,  5, 23],
        'late_fall':    [42, 24, 11,  3,  0, 20],
        'early_winter': [33, 20, 24,  9,  0, 14],
        'winter':       [30, 18, 29, 12,  0, 11],
    },
    'texas_arid': {
        'early_fall':   [38, 15,  0,  0, 35,  7],
        'late_fall':    [58, 18,  0,  0,  4, 12],
        'early_winter': [64, 18,  1,  0,  0, 12],
        'winter':       [58, 20,  5,  1,  0, 11],
    },
    'mountain': {
        'early_fall':   [48, 15,  5,  0,  8, 24],
        'late_fall':    [38, 15, 22,  5,  0, 20],
        'early_winter': [28, 12, 38,  8,  0, 14],
        'winter':       [22,  9, 44, 13,  0, 12],
    },
    'pacific_northwest': {
        'early_fall':   [32, 42,  2,  0,  2, 22],
        'late_fall':    [24, 48,  5,  0,  0, 23],
        'early_winter': [20, 50,  9,  1,  0, 20],
        'winter':       [18, 48, 14,  2,  0, 18],
    },
    'california': {
        'early_fall':   [62, 15,  0,  0,  8, 12],
        'late_fall':    [60, 22,  0,  0,  1, 15],
        'early_winter': [54, 30,  0,  0,  0, 16],
        'winter':       [50, 34,  0,  0,  0, 15],
    },
    'default': {
        'early_fall':   [52, 20,  2,  0,  6, 20],
        'late_fall':    [46, 22,  9,  2,  1, 20],
        'early_winter': [38, 22, 16,  6,  0, 18],
        'winter':       [35, 20, 20,  8,  0, 17],
    },
}

WEATHER_KEYS = ['clear', 'rain', 'snow', 'sleet', 'heat', 'wind']

# ---------------------------------------------------------------------------
# Overseas Classic — international neutral-site game locations
# ---------------------------------------------------------------------------
# Each entry: (city, country, climate_zone)
# These map to existing climate zones for weather generation.

OVERSEAS_CLASSIC_LOCATIONS: List[Dict[str, str]] = [
    # Europe
    {"city": "London", "country": "England", "climate_zone": "pacific_northwest"},
    {"city": "Dublin", "country": "Ireland", "climate_zone": "pacific_northwest"},
    {"city": "Paris", "country": "France", "climate_zone": "mid_atlantic"},
    {"city": "Berlin", "country": "Germany", "climate_zone": "midwest_central"},
    {"city": "Munich", "country": "Germany", "climate_zone": "appalachian"},
    {"city": "Madrid", "country": "Spain", "climate_zone": "california"},
    {"city": "Rome", "country": "Italy", "climate_zone": "california"},
    {"city": "Barcelona", "country": "Spain", "climate_zone": "california"},
    {"city": "Amsterdam", "country": "Netherlands", "climate_zone": "pacific_northwest"},
    # Nordics
    {"city": "Stockholm", "country": "Sweden", "climate_zone": "midwest_north"},
    {"city": "Helsinki", "country": "Finland", "climate_zone": "midwest_north"},
    {"city": "Copenhagen", "country": "Denmark", "climate_zone": "pacific_northwest"},
    {"city": "Oslo", "country": "Norway", "climate_zone": "midwest_north"},
    # Eastern Europe
    {"city": "Kyiv", "country": "Ukraine", "climate_zone": "midwest_central"},
    {"city": "Warsaw", "country": "Poland", "climate_zone": "midwest_central"},
    # East Asia
    {"city": "Tokyo", "country": "Japan", "climate_zone": "mid_atlantic"},
    {"city": "Seoul", "country": "South Korea", "climate_zone": "mid_atlantic"},
    {"city": "Shanghai", "country": "China", "climate_zone": "mid_atlantic"},
    {"city": "Taipei", "country": "Taiwan", "climate_zone": "southeast"},
    # Southeast Asia & South Asia
    {"city": "Singapore", "country": "Singapore", "climate_zone": "deep_south"},
    {"city": "Bangkok", "country": "Thailand", "climate_zone": "deep_south"},
    {"city": "Mumbai", "country": "India", "climate_zone": "deep_south"},
    {"city": "Manila", "country": "Philippines", "climate_zone": "deep_south"},
    # Middle East
    {"city": "Abu Dhabi", "country": "UAE", "climate_zone": "texas_arid"},
    {"city": "Riyadh", "country": "Saudi Arabia", "climate_zone": "texas_arid"},
    # Africa
    {"city": "Lagos", "country": "Nigeria", "climate_zone": "deep_south"},
    {"city": "Nairobi", "country": "Kenya", "climate_zone": "california"},
    {"city": "Cape Town", "country": "South Africa", "climate_zone": "california"},
    {"city": "Johannesburg", "country": "South Africa", "climate_zone": "appalachian"},
    {"city": "Accra", "country": "Ghana", "climate_zone": "deep_south"},
    {"city": "Cairo", "country": "Egypt", "climate_zone": "texas_arid"},
    {"city": "Dar es Salaam", "country": "Tanzania", "climate_zone": "deep_south"},
    {"city": "Casablanca", "country": "Morocco", "climate_zone": "california"},
    # South America
    {"city": "Rio de Janeiro", "country": "Brazil", "climate_zone": "deep_south"},
    {"city": "Sao Paulo", "country": "Brazil", "climate_zone": "southeast"},
    {"city": "Buenos Aires", "country": "Argentina", "climate_zone": "mid_atlantic"},
    {"city": "Bogota", "country": "Colombia", "climate_zone": "appalachian"},
    {"city": "Lima", "country": "Peru", "climate_zone": "california"},
    {"city": "Santiago", "country": "Chile", "climate_zone": "california"},
    # Central America & Caribbean
    {"city": "Mexico City", "country": "Mexico", "climate_zone": "california"},
    {"city": "San Juan", "country": "Puerto Rico", "climate_zone": "southeast"},
    # Oceania
    {"city": "Sydney", "country": "Australia", "climate_zone": "california"},
    {"city": "Melbourne", "country": "Australia", "climate_zone": "pacific_northwest"},
    {"city": "Auckland", "country": "New Zealand", "climate_zone": "pacific_northwest"},
    # North America (non-US)
    {"city": "Toronto", "country": "Canada", "climate_zone": "midwest_north"},
    {"city": "Vancouver", "country": "Canada", "climate_zone": "pacific_northwest"},
]


def pick_overseas_classics(n: int = 5) -> List[Dict[str, str]]:
    """Pick *n* unique random overseas classic locations."""
    return random.sample(OVERSEAS_CLASSIC_LOCATIONS, min(n, len(OVERSEAS_CLASSIC_LOCATIONS)))

# ---------------------------------------------------------------------------
# Realistic temperature ranges by climate zone and season period
# ---------------------------------------------------------------------------
# Each entry is (low, high) in °F for the base temperature range.
# Weather type adjustments are applied on top of these.

ZONE_TEMPS: Dict[str, Dict[str, Tuple[int, int]]] = {
    'new_england': {
        'early_fall': (58, 78), 'late_fall': (38, 58),
        'early_winter': (25, 40), 'winter': (18, 35),
    },
    'mid_atlantic': {
        'early_fall': (62, 82), 'late_fall': (42, 62),
        'early_winter': (30, 48), 'winter': (25, 40),
    },
    'southeast': {
        'early_fall': (75, 90), 'late_fall': (58, 78),
        'early_winter': (45, 65), 'winter': (40, 60),
    },
    'deep_south': {
        'early_fall': (78, 95), 'late_fall': (60, 80),
        'early_winter': (48, 68), 'winter': (42, 62),
    },
    'appalachian': {
        'early_fall': (62, 82), 'late_fall': (42, 60),
        'early_winter': (30, 48), 'winter': (25, 42),
    },
    'midwest_north': {
        'early_fall': (55, 75), 'late_fall': (35, 55),
        'early_winter': (18, 35), 'winter': (10, 28),
    },
    'midwest_central': {
        'early_fall': (60, 80), 'late_fall': (40, 60),
        'early_winter': (25, 42), 'winter': (20, 38),
    },
    'texas_arid': {
        'early_fall': (78, 98), 'late_fall': (58, 80),
        'early_winter': (45, 68), 'winter': (40, 62),
    },
    'mountain': {
        'early_fall': (55, 78), 'late_fall': (32, 55),
        'early_winter': (18, 38), 'winter': (12, 32),
    },
    'pacific_northwest': {
        'early_fall': (58, 75), 'late_fall': (42, 58),
        'early_winter': (35, 48), 'winter': (32, 45),
    },
    'california': {
        'early_fall': (65, 88), 'late_fall': (55, 75),
        'early_winter': (48, 65), 'winter': (45, 62),
    },
    'default': {
        'early_fall': (60, 80), 'late_fall': (42, 62),
        'early_winter': (30, 48), 'winter': (25, 42),
    },
}

# Temperature adjustments by weather type (added to base temp)
_WEATHER_TEMP_ADJUST: Dict[str, Tuple[int, int]] = {
    'clear': (0, 5),
    'rain': (-5, 0),
    'snow': (-10, -5),
    'sleet': (-8, -3),
    'heat': (5, 10),
    'wind': (-3, 3),
}

# ---------------------------------------------------------------------------
# Season period mapping
# ---------------------------------------------------------------------------

def week_to_period(week: int, total_weeks: int = 18) -> str:
    """Map a season week number to a season period label."""
    if total_weeks <= 0:
        total_weeks = 18
    # Normalize week to [0, 1]
    pct = (week - 1) / max(total_weeks - 1, 1)
    if pct < 0.22:   # first ~4 weeks of 18
        return 'early_fall'
    elif pct < 0.56:  # weeks 5–10
        return 'late_fall'
    elif pct < 0.75:  # weeks 11–13
        return 'early_winter'
    else:             # weeks 14+
        return 'winter'

# ---------------------------------------------------------------------------
# Temperature generation
# ---------------------------------------------------------------------------

def generate_temperature(
    weather: str,
    climate_zone: str = 'default',
    period: str = 'early_fall',
) -> int:
    """Generate a realistic game-day temperature in °F.

    Based on the climate zone, season period, and weather type.
    """
    zone_table = ZONE_TEMPS.get(climate_zone, ZONE_TEMPS['default'])
    base_low, base_high = zone_table.get(period, (55, 75))
    adj_low, adj_high = _WEATHER_TEMP_ADJUST.get(weather, (0, 0))
    temp_low = base_low + adj_low
    temp_high = base_high + adj_high
    return random.randint(temp_low, temp_high)

# ---------------------------------------------------------------------------
# Human-readable weather descriptions
# ---------------------------------------------------------------------------

WEATHER_DETAILS: Dict[str, Dict] = {
    'clear': {
        'label': 'Clear',
        'icon': '☀️',
    },
    'rain': {
        'label': 'Rain',
        'icon': '🌧️',
    },
    'snow': {
        'label': 'Snow',
        'icon': '❄️',
    },
    'sleet': {
        'label': 'Sleet',
        'icon': '🌨️',
    },
    'heat': {
        'label': 'Hot',
        'icon': '🌡️',
    },
    'wind': {
        'label': 'Windy',
        'icon': '💨',
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_climate_zone(state: str) -> str:
    """Return the climate zone for a US state abbreviation."""
    return STATE_CLIMATE.get(state.upper() if state else '', 'default')

def generate_game_weather(
    state: Optional[str] = None,
    week: int = 5,
    total_weeks: int = 18,
    climate_zone: Optional[str] = None,
) -> str:
    """
    Generate a weather condition for a game.

    Args:
        state: Home team's US state abbreviation (e.g. 'WI', 'FL', 'TX').
               International locations default to 'default' climate.
        week: Season week number (1-based).
        total_weeks: Total number of regular season weeks (used to scale timing).
        climate_zone: Override climate zone directly (skips state lookup).

    Returns:
        A weather key string: 'clear', 'rain', 'snow', 'sleet', 'heat', or 'wind'.
    """
    zone = climate_zone or get_climate_zone(state or '')
    period = week_to_period(week, total_weeks)

    table = WEATHER_TABLE.get(zone, WEATHER_TABLE['default'])
    weights = table.get(period, table['early_fall'])

    return random.choices(WEATHER_KEYS, weights=weights, k=1)[0]

def generate_game_weather_full(
    state: Optional[str] = None,
    week: int = 5,
    total_weeks: int = 18,
    climate_zone: Optional[str] = None,
) -> Tuple[str, int]:
    """Generate weather condition AND a realistic temperature.

    Returns:
        (weather_key, temperature_f) — e.g. ('rain', 52)
    """
    zone = climate_zone or get_climate_zone(state or '')
    period = week_to_period(week, total_weeks)
    table = WEATHER_TABLE.get(zone, WEATHER_TABLE['default'])
    weights = table.get(period, table['early_fall'])
    weather = random.choices(WEATHER_KEYS, weights=weights, k=1)[0]
    temp = generate_temperature(weather, zone, period)
    return weather, temp

def generate_bowl_weather(state: Optional[str] = None) -> str:
    """
    Generate weather for bowl/postseason games (played in December–January).
    Bowl games are often in warm-weather states; if state not provided, skews clear.
    """
    return generate_game_weather(state=state, week=16, total_weeks=18)

def get_weather_description(weather_key: str) -> Dict:
    """
    Return a dict of human-readable info for a weather key.
    Safe to call with any string — returns clear fallback if key unknown.
    """
    return WEATHER_DETAILS.get(weather_key, WEATHER_DETAILS['clear'])

def generate_season_weather_map(
    schedule_weeks: list,
    home_state: Optional[str] = None,
    total_weeks: int = 18,
) -> Dict[int, str]:
    """
    Pre-generate weather for every game week in a season.

    Args:
        schedule_weeks: List of week numbers (ints) to generate weather for.
        home_state: Home team's state.
        total_weeks: Total season weeks for timing calibration.

    Returns:
        Dict mapping week → weather key.
    """
    return {
        week: generate_game_weather(state=home_state, week=week, total_weeks=total_weeks)
        for week in schedule_weeks
    }

def describe_conditions(weather_key: str, temp: Optional[int] = None) -> str:
    """
    Return a short human-readable string for display in game logs.
    E.g. 'Rain, 52°F' or '72°F'
    """
    info = get_weather_description(weather_key)
    temp_str = f"{temp}°F" if temp is not None else ""
    if weather_key == 'clear':
        return temp_str or info['label']
    if temp_str:
        return f"{info['label']}, {temp_str}"
    return info['label']

# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from collections import Counter

    print("=== Viperball Weather System ===\n")

    test_cases = [
        ('WI', 'Wisconsin — early season (week 2)'),
        ('WI', 'Wisconsin — late season (week 14)'),
        ('FL', 'Florida — early season (week 2)'),
        ('FL', 'Florida — late season (week 14)'),
        ('CA', 'California — mid-season (week 8)'),
        ('CO', 'Colorado — bowl season (week 16)'),
        ('TX', 'Texas — early season (week 2)'),
        (None, 'Unknown/International — mid-season (week 8)'),
    ]

    for state, label in test_cases:
        week = int(label.split('week ')[1].rstrip(')'))
        w, temp = generate_game_weather_full(state=state, week=week)
        print(f"  {label}: {describe_conditions(w, temp)}")

    print('\n--- Distribution (WI, week 12, 5000 samples) ---')
    counts = Counter(generate_game_weather(state='WI', week=12) for _ in range(5000))
    for k in WEATHER_KEYS:
        bar = '█' * (counts[k] // 50)
        print(f"  {k:6s}: {counts[k]:4d}  {bar}")
