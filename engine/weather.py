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
from typing import Dict, Optional, Tuple

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
        'early_fall':   [55, 20,  0,  0, 10, 15],
        'late_fall':    [44, 25,  6,  1,  2, 22],
        'early_winter': [38, 22, 17,  6,  0, 17],
        'winter':       [36, 20, 22, 10,  0, 12],
    },
    'southeast': {
        'early_fall':   [40, 32,  0,  0, 22,  6],
        'late_fall':    [55, 27,  0,  0, 13,  5],
        'early_winter': [60, 25,  1,  0,  5,  9],
        'winter':       [60, 27,  2,  0,  3,  8],
    },
    'deep_south': {
        'early_fall':   [38, 35,  0,  0, 22,  5],
        'late_fall':    [50, 30,  0,  0, 14,  6],
        'early_winter': [54, 28,  0,  0,  9,  9],
        'winter':       [56, 29,  2,  0,  5,  8],
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
        'early_fall':   [48, 22,  0,  0,  8, 22],
        'late_fall':    [40, 24, 11,  3,  2, 20],
        'early_winter': [33, 20, 24,  9,  0, 14],
        'winter':       [30, 18, 29, 12,  0, 11],
    },
    'texas_arid': {
        'early_fall':   [32, 15,  0,  0, 48,  5],
        'late_fall':    [54, 18,  0,  0, 18, 10],
        'early_winter': [64, 18,  1,  0,  8,  9],
        'winter':       [58, 20,  5,  1,  5, 11],
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
        'early_fall':   [62, 15,  0,  0, 13, 10],
        'late_fall':    [58, 22,  0,  0,  5, 15],
        'early_winter': [52, 30,  0,  0,  2, 16],
        'winter':       [50, 34,  0,  0,  1, 15],
    },
    'default': {
        'early_fall':   [50, 20,  2,  0,  8, 20],
        'late_fall':    [44, 22,  9,  2,  3, 20],
        'early_winter': [38, 22, 16,  6,  0, 18],
        'winter':       [35, 20, 20,  8,  0, 17],
    },
}

WEATHER_KEYS = ['clear', 'rain', 'snow', 'sleet', 'heat', 'wind']

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
# Human-readable weather descriptions
# ---------------------------------------------------------------------------

WEATHER_DETAILS: Dict[str, Dict] = {
    'clear': {
        'label': 'Clear',
        'icon': '☀️',
        'temp_range': '55–75°F',
        'description': 'Perfect conditions. No weather impact.',
        'game_note': 'Ideal playing conditions.',
    },
    'rain': {
        'label': 'Rain',
        'icon': '🌧️',
        'temp_range': '45–60°F',
        'description': 'Wet field and slippery ball. Increased fumbles and muffs; reduced kick accuracy.',
        'game_note': 'Ball security becomes critical.',
    },
    'snow': {
        'label': 'Snow',
        'icon': '❄️',
        'temp_range': '22–34°F',
        'description': 'Cold and snowy. Major kick accuracy loss; moderately higher fumble risk; slower play.',
        'game_note': 'Kicking game severely impacted. Ground game preferred.',
    },
    'sleet': {
        'label': 'Sleet / Ice',
        'icon': '🌨️',
        'temp_range': '28–35°F',
        'description': 'The worst conditions. Extreme fumble risk, terrible kicking, mentally and physically exhausting.',
        'game_note': 'All ball-handling stats degraded. Penalties increase.',
    },
    'heat': {
        'label': 'Extreme Heat',
        'icon': '🌡️',
        'temp_range': '95–108°F',
        'description': 'Oppressive heat causes rapid stamina drain and sweaty hands.',
        'game_note': 'Stamina management critical. Fourth-quarter performance drops.',
    },
    'wind': {
        'label': 'Heavy Wind',
        'icon': '💨',
        'temp_range': '45–65°F',
        'description': 'Strong gusts impact kicks and punts heavily; additional variance in distance.',
        'game_note': 'Kicking game unpredictable. Field position matters more.',
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

def describe_conditions(weather_key: str) -> str:
    """
    Return a short human-readable string for display in game logs.
    E.g. 'Snow (22–34°F)' or 'Clear'
    """
    info = get_weather_description(weather_key)
    if weather_key == 'clear':
        return info['label']
    return f"{info['label']} ({info['temp_range']})"

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
        w = generate_game_weather(state=state, week=week)
        print(f"  {label}: {describe_conditions(w)}")

    print('\n--- Distribution (WI, week 12, 5000 samples) ---')
    counts = Counter(generate_game_weather(state='WI', week=12) for _ in range(5000))
    for k in WEATHER_KEYS:
        bar = '█' * (counts[k] // 50)
        print(f"  {k:6s}: {counts[k]:4d}  {bar}")
