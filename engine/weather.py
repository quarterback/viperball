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
# WEA-02: weather as readings
# ---------------------------------------------------------------------------
# A game's weather is a set of readings for each period (temperature,
# precipitation and its strength, wind speed and direction, humidity) plus the
# venue (roof, surface, altitude) and the state of the field, which builds up
# as rain or snow keeps falling.  The six labels above still pick the day's
# broad weather from the climate tables, so how often each place sees rain or
# snow is unchanged; the readings decide how much it matters, period by period.

import hashlib
import math
from dataclasses import dataclass, field as _field

# Canadian provinces used by pro teams.
STATE_CLIMATE.update({
    'AB': 'mountain', 'BC': 'pacific_northwest', 'ON': 'midwest_north',
    'QC': 'new_england', 'AK': 'midwest_north', 'HI': 'southeast',
})

# Altitude in feet by US state or province (where most venues sit).
STATE_ALTITUDE: Dict[str, int] = {
    'CO': 5300, 'WY': 7200, 'UT': 4500, 'NM': 4800, 'MT': 3800, 'ID': 2700,
    'NV': 3500, 'AZ': 1500, 'AB': 3400, 'NE': 1100, 'KS': 1000, 'SD': 1500,
    'ND': 1200, 'TX': 600, 'OK': 1100, 'WV': 900, 'AK': 100,
}

# Country code -> (climate zone, hemisphere, altitude in feet of the main venue).
# Hemisphere: N (northern seasons), S (southern seasons, flipped), T (tropical:
# warm all year), H (tropical highland: mild all year, high up).
COUNTRY_CLIMATE: Dict[str, Tuple[str, str, int]] = {
    'USA': ('default', 'N', 300), 'CAN': ('midwest_north', 'N', 300),
    # Europe
    'ENG': ('pacific_northwest', 'N', 100), 'GBR': ('pacific_northwest', 'N', 100),
    'SCO': ('pacific_northwest', 'N', 100), 'WAL': ('pacific_northwest', 'N', 100),
    'IRL': ('pacific_northwest', 'N', 100), 'NED': ('pacific_northwest', 'N', 0),
    'NET': ('pacific_northwest', 'N', 0), 'BEL': ('pacific_northwest', 'N', 200),
    'DEN': ('pacific_northwest', 'N', 50), 'GER': ('midwest_central', 'N', 400),
    'CZE': ('midwest_central', 'N', 800), 'POL': ('midwest_central', 'N', 300),
    'UKR': ('midwest_central', 'N', 600), 'CHE': ('midwest_central', 'N', 1350),
    'FRA': ('mid_atlantic', 'N', 200), 'SWE': ('midwest_north', 'N', 100),
    'NOR': ('midwest_north', 'N', 100), 'FIN': ('midwest_north', 'N', 100),
    'RUS': ('midwest_north', 'N', 500), 'ESP': ('california', 'N', 1500),
    'SPA': ('california', 'N', 1500), 'POR': ('california', 'N', 300),
    'ITA': ('california', 'N', 300), 'GRE': ('california', 'N', 100),
    'TUR': ('mid_atlantic', 'N', 200),
    # Asia
    'JPN': ('mid_atlantic', 'N', 50), 'KOR': ('mid_atlantic', 'N', 100),
    'CHN': ('mid_atlantic', 'N', 200), 'TWN': ('southeast', 'N', 50),
    'IND': ('deep_south', 'T', 500), 'KAZ': ('midwest_north', 'N', 1500),
    'UZB': ('texas_arid', 'N', 1500), 'MGL': ('mountain', 'N', 4400),
    'THA': ('deep_south', 'T', 30), 'VNM': ('deep_south', 'T', 30),
    'LAO': ('deep_south', 'T', 600), 'KHM': ('deep_south', 'T', 30),
    'MYS': ('deep_south', 'T', 100), 'SGP': ('deep_south', 'T', 50),
    'PHL': ('deep_south', 'T', 50), 'PHI': ('deep_south', 'T', 50),
    'IDN': ('deep_south', 'T', 30), 'INA': ('deep_south', 'T', 30),
    # Middle East
    'KSA': ('texas_arid', 'N', 2000), 'UAE': ('texas_arid', 'N', 30),
    'EGY': ('texas_arid', 'N', 100), 'IRN': ('texas_arid', 'N', 3900),
    'ISR': ('california', 'N', 300), 'YEM': ('texas_arid', 'N', 7200),
    # Africa
    'NGA': ('deep_south', 'T', 600), 'GHA': ('deep_south', 'T', 200),
    'CIV': ('deep_south', 'T', 100), 'SEN': ('deep_south', 'T', 50),
    'CMR': ('deep_south', 'T', 2400), 'TOG': ('deep_south', 'T', 100),
    'GIN': ('deep_south', 'T', 100), 'CAF': ('deep_south', 'T', 1200),
    'COD': ('deep_south', 'T', 1000), 'TZA': ('deep_south', 'T', 100),
    'TAN': ('deep_south', 'T', 100), 'AGO': ('deep_south', 'T', 200),
    'ETH': ('california', 'H', 7700), 'KEN': ('california', 'H', 5900),
    'UGA': ('california', 'H', 3900), 'RWA': ('california', 'H', 5000),
    'MWI': ('california', 'H', 3600), 'MDG': ('california', 'H', 4200),
    'ZAF': ('appalachian', 'S', 5750), 'RSA': ('appalachian', 'S', 5750),
    'MAR': ('california', 'N', 200),
    # Americas
    'MEX': ('california', 'H', 7350), 'COL': ('california', 'H', 8660),
    'ECU': ('california', 'H', 9350), 'BOL': ('california', 'H', 11900),
    'VEN': ('deep_south', 'T', 3000), 'PER': ('california', 'S', 500),
    'CHI': ('california', 'S', 1700), 'ARG': ('mid_atlantic', 'S', 100),
    'URU': ('mid_atlantic', 'S', 100), 'PAR': ('southeast', 'S', 400),
    'BRA': ('southeast', 'S', 2600), 'CUB': ('deep_south', 'T', 200),
    'DOM': ('deep_south', 'T', 100), 'PRI': ('deep_south', 'T', 50),
    'JAM': ('deep_south', 'T', 100), 'TTO': ('deep_south', 'T', 50),
    'HAI': ('deep_south', 'T', 100), 'CRC': ('california', 'H', 3800),
    'GUA': ('california', 'H', 4900), 'PAN': ('deep_south', 'T', 100),
    'HON': ('deep_south', 'T', 3300), 'NIC': ('deep_south', 'T', 300),
    'SLV': ('deep_south', 'T', 2200),
    # Oceania
    'AUS': ('california', 'S', 100), 'NZL': ('pacific_northwest', 'S', 100),
    'FIJ': ('deep_south', 'T', 50), 'SAM': ('deep_south', 'T', 50),
    'PNG': ('deep_south', 'T', 300),
}

# Cities whose altitude or climate differs from their country or state default.
CITY_CLIMATE: Dict[str, Dict] = {
    'Calgary': {'alt': 3440}, 'Albuquerque': {'alt': 5310}, 'Boise': {'alt': 2730},
    'Spokane': {'alt': 1840}, 'Denver': {'alt': 5280}, 'Boulder': {'alt': 5330},
    'Fort Collins': {'alt': 5000}, 'Colorado Springs': {'alt': 6800},
    'Laramie': {'alt': 7220}, 'Provo': {'alt': 4550}, 'Logan': {'alt': 4530},
    'Salt Lake City': {'alt': 4300}, 'Reno': {'alt': 4500}, 'Las Vegas': {'alt': 2000},
    'Flagstaff': {'alt': 6900}, 'Tucson': {'alt': 2400}, 'Tempe': {'alt': 1150},
    'El Paso': {'alt': 3740}, 'Lubbock': {'alt': 3250}, 'Bozeman': {'alt': 4820},
    'Missoula': {'alt': 3200}, 'Las Cruces': {'alt': 3900},
    'Addis Ababa': {'alt': 7726}, 'Nairobi': {'alt': 5889}, 'Kampala': {'alt': 3900},
    'Johannesburg': {'alt': 5751}, 'Abuja': {'alt': 1180}, 'Mexico City': {'alt': 7350},
    'Bogotá': {'alt': 8660}, 'Bogota': {'alt': 8660}, 'São Paulo': {'alt': 2600},
    'Zurich': {'alt': 1340}, 'Munich': {'alt': 1700}, 'Madrid': {'alt': 2190},
    'Istanbul': {'zone': 'mid_atlantic'}, 'Cairo': {'zone': 'texas_arid'},
    'Casablanca': {'zone': 'california'}, 'Dar es Salaam': {'zone': 'deep_south'},
    'Lima': {'zone': 'california', 'hemi': 'S', 'alt': 500},
    'Santiago': {'zone': 'california', 'hemi': 'S', 'alt': 1700},
    'Buenos Aires': {'zone': 'mid_atlantic', 'hemi': 'S', 'alt': 80},
    'Montevideo': {'zone': 'mid_atlantic', 'hemi': 'S', 'alt': 100},
    'Havana': {'zone': 'deep_south', 'hemi': 'T', 'alt': 200},
    'Santo Domingo': {'zone': 'deep_south', 'hemi': 'T', 'alt': 50},
    'San Juan': {'zone': 'deep_south', 'hemi': 'T', 'alt': 50},
    'Seville': {'zone': 'texas_arid'}, 'Bodø': {'zone': 'midwest_north'},
    'Lapua': {'zone': 'midwest_north'}, 'Vimpeli': {'zone': 'midwest_north'},
    'Portland': {'zone': 'pacific_northwest'},
}

# A school or team name that sits well above its state's usual altitude.
NAME_ALTITUDE: Dict[str, int] = {
    'Air Force': 7258, 'UTEP': 3740, 'Texas Tech': 3250, 'Northern Arizona': 6900,
    'Wyoming': 7220, 'Colorado': 5330, 'Colorado State': 5000, 'New Mexico': 5310,
    'BYU': 4550, 'Utah State': 4530, 'Nevada': 4500, 'UNLV': 2000,
    'Montana State': 4820, 'Montana': 3200, 'New Mexico State': 3900,
}

PRECIP_KINDS = ('rain', 'snow', 'sleet')
# Precipitation strength: about 0.25 is light, 0.55 moderate, 0.85 heavy.
_INTENSITY_LEVELS = ((0.25, 0.45), (0.55, 0.38), (0.85, 0.17))


def resolve_location(state: Optional[str] = None, city: Optional[str] = None,
                     climate_zone: Optional[str] = None) -> Tuple[str, str, int]:
    """(climate zone, hemisphere, altitude) for a state or country code and city."""
    code = (state or '').upper()
    if code in COUNTRY_CLIMATE and code not in STATE_CLIMATE:
        zone, hemi, alt = COUNTRY_CLIMATE[code]
    else:
        zone = STATE_CLIMATE.get(code, 'default')
        hemi = 'N'
        alt = STATE_ALTITUDE.get(code, 300)
    c = CITY_CLIMATE.get(city or '', {})
    zone = c.get('zone', zone)
    hemi = c.get('hemi', hemi)
    alt = c.get('alt', alt)
    if climate_zone:
        zone = climate_zone
    return zone, hemi, alt


_MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
# Northern hemisphere climate period for each month.
_MONTH_PERIOD = ('winter', 'winter', 'early_winter', 'late_fall', 'early_fall', 'summer',
                 'summer', 'summer', 'early_fall', 'late_fall', 'late_fall', 'early_winter')


def month_index(month: str) -> int:
    return _MONTHS.index(month.strip().lower()[:3])


def season_period(week: int, total_weeks: int, hemi: str = 'N',
                  month: Optional[str] = None) -> str:
    """Season period for the climate tables. With a month (pro calendars, the
    June FIV window) the month decides; otherwise the college calendar,
    September through January. Southern places get the season six months
    on; tropical places are warm all year and tropical highlands mild."""
    if hemi == 'T':
        return 'early_fall'
    if hemi == 'H':
        return 'late_fall'
    if month:
        m = month_index(month)
        if hemi == 'S':
            m = (m + 6) % 12
        return _MONTH_PERIOD[m]
    north = week_to_period(week, total_weeks)
    if hemi == 'S':
        return {'early_fall': 'late_fall', 'late_fall': 'early_fall',
                'early_winter': 'summer', 'winter': 'summer'}[north]
    return north


def calendar_month(week: int, total_weeks: int, start: str, end: str) -> str:
    """The month a week falls in for a season running from start to end."""
    a, b = month_index(start), month_index(end)
    span = (b - a) % 12 + 1
    frac = (max(1, week) - 1) / max(1, total_weeks - 1) if total_weeks > 1 else 0.0
    return _MONTHS[(a + min(span - 1, int(frac * span))) % 12]


# The climate tables give snow and sleet about twice as often as games
# really see them. Days with measurable snow in December and January run
# about 25 to 30% in Minneapolis, 20% in Chicago, 10 to 15% in Boston, under
# 10% in New York, and a few percent in Knoxville or Seattle, and a game only
# covers part of a day. These shares bring each zone close to that.
_FROZEN_SHARE = {
    'midwest_north': 0.6, 'mountain': 0.55, 'midwest_central': 0.55,
    'new_england': 0.5, 'mid_atlantic': 0.4, 'appalachian': 0.25,
    'pacific_northwest': 0.25, 'texas_arid': 0.3, 'default': 0.5,
    'southeast': 0.0, 'deep_south': 0.0, 'california': 0.0,
}


def _period_weights(zone: str, period: str) -> list:
    table = WEATHER_TABLE.get(zone, WEATHER_TABLE['default'])
    if period == 'summer':
        w = list(table['early_fall'])
        w[2] = w[3] = 0          # no snow or sleet
        w[4] = w[4] * 1.8 + 4    # more heat
        return w
    w = list(table.get(period, table['early_fall']))
    k = _FROZEN_SHARE.get(zone, 0.5)
    moved = (w[2] + w[3]) * (1 - k)
    w[2] *= k
    w[3] *= k
    w[0] += moved * 0.6          # most of it becomes a dry cold day
    w[1] += moved * 0.4          # some of it falls as rain
    return w


def _period_temps(zone: str, period: str) -> Tuple[int, int]:
    zt = ZONE_TEMPS.get(zone, ZONE_TEMPS['default'])
    if period == 'summer':
        lo, hi = zt['early_fall']
        return lo + 6, hi + 6
    return zt.get(period, (55, 75))


@dataclass
class Venue:
    roof: str = 'open'          # open, dome, retractable
    surface: str = 'grass'      # grass, turf
    altitude_ft: int = 300
    retractable: bool = False

    def to_dict(self) -> Dict:
        return {'roof': self.roof, 'surface': self.surface,
                'altitude_ft': self.altitude_ft, 'retractable': self.retractable}


# Share of venues with a dome, a retractable roof and turf, by league.
_VENUE_RATES = {
    'college': (0.04, 0.02, 0.55),
    'pro': (0.10, 0.12, 0.40),
    'wvl': (0.0, 0.03, 0.12),
    'fiv': (0.05, 0.06, 0.25),
    'high_school': (0.0, 0.0, 0.50),
}
_COLD_ZONES = ('midwest_north', 'midwest_central', 'new_england', 'mountain')


def venue_for(name: str, state: Optional[str] = None, city: Optional[str] = None,
              league: str = 'college') -> Venue:
    """The home venue for a team. Built from a hash of the team's name, so the
    same team plays in the same building every season."""
    zone, _hemi, alt = resolve_location(state, city)
    alt = NAME_ALTITUDE.get(name, alt)
    dome, retract, turf = _VENUE_RATES.get(league, _VENUE_RATES['college'])
    if zone in _COLD_ZONES or zone == 'texas_arid':
        dome *= 1.8          # cold and very hot cities build roofs
        retract *= 1.8
    h = int(hashlib.sha256(f"venue:{league}:{name}".encode()).hexdigest(), 16)
    r1 = (h % 10000) / 10000.0
    r2 = ((h >> 20) % 10000) / 10000.0
    roof = 'dome' if r1 < dome else ('retractable' if r1 < dome + retract else 'open')
    surface = 'turf' if (roof == 'dome' or r2 < turf) else 'grass'
    return Venue(roof=roof, surface=surface, altitude_ft=int(alt))


@dataclass
class Reading:
    """Conditions for one period."""
    temp_f: int = 65
    precip: str = 'none'        # none, rain, snow, sleet
    intensity: float = 0.0      # 0 none, 0.25 light, 0.55 moderate, 0.85 heavy
    wind_mph: float = 0.0
    wind_dir: float = 0.0       # degrees; 0 blows toward the north end
    humidity: float = 0.5

    @property
    def wind_along(self) -> float:
        """Wind toward the north end (negative: toward the south end)."""
        return self.wind_mph * math.cos(math.radians(self.wind_dir))

    @property
    def wind_cross(self) -> float:
        return abs(self.wind_mph * math.sin(math.radians(self.wind_dir)))

    @property
    def heat_index(self) -> float:
        if self.temp_f < 80:
            return float(self.temp_f)
        return self.temp_f + max(0.0, self.humidity - 0.40) * self.temp_f * 0.35

    def to_dict(self) -> Dict:
        return {'temp_f': self.temp_f, 'precip': self.precip,
                'intensity': round(self.intensity, 2), 'wind_mph': round(self.wind_mph, 1),
                'wind_dir': round(self.wind_dir % 360), 'humidity': round(self.humidity, 2)}


@dataclass
class FieldState:
    wetness: float = 0.0        # 0 dry to 1 soaked (grass soaked is mud)
    snow_cover: float = 0.0     # 0 to 1
    frozen: bool = False

    def to_dict(self) -> Dict:
        return {'wetness': round(self.wetness, 2), 'snow_cover': round(self.snow_cover, 2),
                'frozen': self.frozen}


def _intensity_word(x: float) -> str:
    return 'light' if x < 0.4 else ('heavy' if x >= 0.75 else 'steady')


def _wind_word(along: float, cross: float, mph: float) -> str:
    if mph < 8:
        return ''
    mph5 = max(5, int(round(mph / 5.0)) * 5)
    if abs(along) >= cross:
        end = 'north' if along > 0 else 'south'
        return f"wind {mph5} mph toward the {end} end"
    return f"crosswind {mph5} mph"


@dataclass
class GameWeather:
    periods: List[Reading]
    venue: Venue = _field(default_factory=Venue)
    zone: str = 'default'
    season: str = 'early_fall'
    fields: List[FieldState] = _field(default_factory=list)

    def __post_init__(self):
        if not self.fields:
            self.fields = _field_states(self.periods, self.venue)

    @property
    def indoor(self) -> bool:
        return self.venue.roof in ('dome', 'closed')

    def reading(self, quarter: int) -> Reading:
        return self.periods[max(0, min(len(self.periods), quarter) - 1)]

    def field_state(self, quarter: int) -> FieldState:
        return self.fields[max(0, min(len(self.fields), quarter) - 1)]

    def label(self, quarter: int = 1) -> str:
        return label_for(self.reading(quarter))

    def describe(self, quarter: int = 1) -> str:
        """Short text for one period, e.g. 'Heavy rain, 44°F, wind 18 mph toward the north end'."""
        r = self.reading(quarter)
        if self.indoor:
            return f"Indoors, {r.temp_f}°F"
        parts = []
        if r.precip != 'none' and r.intensity >= 0.15:
            parts.append(f"{_intensity_word(r.intensity).capitalize()} {r.precip}")
        parts.append(f"{r.temp_f}°F")
        w = _wind_word(r.wind_along, r.wind_cross, r.wind_mph)
        if w:
            parts.append(w)
        f = self.field_state(quarter)
        if f.snow_cover >= 0.3:
            parts.append('snow on the field')
        elif f.frozen:
            parts.append('frozen field')
        elif f.wetness >= 0.45:
            parts.append('muddy field' if self.venue.surface == 'grass' else 'wet turf')
        return ', '.join(parts)

    def summary(self) -> Dict:
        return {
            'venue': self.venue.to_dict(),
            'periods': [dict(r.to_dict(), label=label_for(r), field=f.to_dict(),
                             text=self.describe(i + 1))
                        for i, (r, f) in enumerate(zip(self.periods, self.fields))],
        }

    def effects(self, quarter: int) -> Dict:
        return weather_effects(self.reading(quarter), self.field_state(quarter), self.venue)

    @classmethod
    def from_label(cls, label: str, temp_f: Optional[int] = None) -> 'GameWeather':
        """Fixed conditions for callers that pass only a label (tools, matched
        studies). The same reading holds all game, so a study's conditions
        stay controlled. Wind sits at 45 degrees so each team gets the same
        share of help and hindrance."""
        base = {
            'clear': Reading(temp_f=65, wind_mph=0.0),
            'rain': Reading(temp_f=52, precip='rain', intensity=0.55, wind_mph=8.0,
                            wind_dir=45.0, humidity=0.92),
            'snow': Reading(temp_f=28, precip='snow', intensity=0.55, wind_mph=8.0,
                            wind_dir=45.0, humidity=0.85),
            'sleet': Reading(temp_f=31, precip='sleet', intensity=0.55, wind_mph=10.0,
                             wind_dir=45.0, humidity=0.9),
            'heat': Reading(temp_f=94, wind_mph=4.0, wind_dir=45.0, humidity=0.65),
            'wind': Reading(temp_f=55, wind_mph=22.0, wind_dir=45.0, humidity=0.5),
        }.get(label, Reading(temp_f=65))
        if temp_f is not None and label in ('clear', 'wind', 'rain'):
            base.temp_f = int(temp_f)
        periods = [Reading(**vars(base)) for _ in range(4)]
        # Start a wet game on a field that is already wet.
        return cls(periods=periods)


def label_for(r: Reading) -> str:
    if r.precip in PRECIP_KINDS and r.intensity >= 0.15:
        return r.precip
    if r.heat_index >= 88:
        return 'heat'
    if r.wind_mph >= 16:
        return 'wind'
    return 'clear'


def _field_states(periods: List[Reading], venue: Venue) -> List[FieldState]:
    """Field state at the start of each period. Rain soaks the field and it
    stays wet after the rain stops; grass holds water longer than turf."""
    out: List[FieldState] = []
    if venue.roof in ('dome', 'closed'):
        return [FieldState() for _ in periods]
    keep, add = (0.75, 0.35) if venue.surface == 'grass' else (0.55, 0.25)
    first = periods[0]
    wet = first.intensity * 0.5 if first.precip in ('rain', 'sleet') else 0.0
    snow = first.intensity * 0.4 if first.precip == 'snow' else 0.0
    for i, r in enumerate(periods):
        out.append(FieldState(wetness=min(1.0, wet), snow_cover=min(1.0, snow),
                              frozen=r.temp_f <= 28 and wet >= 0.3))
        if r.precip in ('rain', 'sleet'):
            wet = wet * keep + r.intensity * add
        else:
            wet = wet * keep
        if r.precip == 'snow':
            snow = snow * 0.9 + r.intensity * 0.45
            wet = wet + r.intensity * 0.05
        elif r.temp_f > 34:
            wet = min(1.0, wet + snow * 0.3)
            snow *= 0.6
    return out


def weather_effects(r: Reading, f: FieldState, venue: Venue) -> Dict:
    """What the conditions do to play. Every effect is driven by a reading,
    so a drizzle costs less than a downpour. Directional wind is applied by
    the engine for the team kicking (wind_along is toward the north end)."""
    p = r.intensity if r.precip in PRECIP_KINDS else 0.0
    wet_rate = {'rain': 0.40, 'snow': 0.35, 'sleet': 0.55}.get(r.precip, 0.0)
    cold = max(0.0, 35 - r.temp_f)
    handling = (1.0 + wet_rate * p + 0.10 * f.wetness + 0.004 * cold
                + (0.05 if f.frozen else 0.0))
    hi = r.heat_index
    heat = max(0.0, min(1.5, (hi - 80) / 15.0))
    mud = 1.4 if venue.surface == 'grass' else 0.8
    speed_mod = -(0.035 * f.wetness * mud + 0.015 * p + 0.05 * f.snow_cover
                  + (0.02 if f.frozen else 0.0) + 0.02 * heat)
    stamina = 0.22 * heat + 0.10 * f.wetness + 0.003 * max(0.0, 40 - r.temp_f) + 0.05 * p
    kick_acc = -({'rain': 0.12, 'snow': 0.16, 'sleet': 0.20}.get(r.precip, 0.0) * p
                 + 0.005 * max(0.0, r.wind_cross - 4) + 0.0015 * r.wind_mph)
    # Yards added to kick range before the wind's direction: a cold ball and a
    # wet ball travel shorter, thin air carries farther.
    range_base = (max(-4.0, min(2.0, (r.temp_f - 60) * 0.08)) - 2.5 * p
                  + venue.altitude_ft / 1000.0 * 0.5)
    punt_base = (-0.08 * p - 0.002 * max(0.0, 50 - r.temp_f)
                 + 0.012 * venue.altitude_ft / 1000.0)
    wet_play = min(1.5, (p + 0.4 * f.wetness + 0.5 * f.snow_cover) / 0.55)
    label = label_for(r)
    return {
        'label': WEATHER_DETAILS.get(label, WEATHER_DETAILS['clear'])['label'],
        'key': label,
        'temp_f': r.temp_f,
        'precip': r.precip,
        'intensity': p,
        'wind_mph': r.wind_mph,
        'wind_along': r.wind_along,
        'wind_cross': r.wind_cross,
        'heat_index': hi,
        'heat_factor': heat,
        'wetness': f.wetness,
        'snow_cover': f.snow_cover,
        'frozen': f.frozen,
        'fumble_mult': handling,
        'lateral_fumble_mult': handling,
        'muff_mult': 1.0 + 2.0 * (handling - 1.0) + 0.006 * r.wind_mph,
        'speed_modifier': speed_mod,
        'stamina_drain_modifier': stamina,
        'kick_accuracy_modifier': kick_acc,
        'kick_range_base': range_base,
        'punt_base': punt_base,
        'kick_pass_wet': 0.10 * p,
        'wet_play': wet_play,
        'bad_weather_frac': min(1.0, (p + 0.5 * f.wetness) / 0.6),
    }


def build_game_weather(state: Optional[str] = None, city: Optional[str] = None,
                       week: int = 5, total_weeks: int = 18,
                       climate_zone: Optional[str] = None,
                       venue: Optional[Venue] = None,
                       month: Optional[str] = None,
                       rng=None) -> GameWeather:
    """Weather for one game at a real place and time of year."""
    rng = rng or random
    zone, hemi, alt = resolve_location(state, city, climate_zone)
    venue = venue or Venue(altitude_ft=alt)
    period = season_period(week, total_weeks, hemi, month)
    label = rng.choices(WEATHER_KEYS, weights=_period_weights(zone, period), k=1)[0]
    lo, hi = _period_temps(zone, period)
    if label in ('snow', 'sleet') and lo > 36:
        label = 'rain'   # too warm here at this time of year for anything frozen
    adj_lo, adj_hi = _WEATHER_TEMP_ADJUST.get(label, (0, 0))
    temp = rng.randint(lo + adj_lo, hi + adj_hi)
    if label == 'snow':
        temp = min(temp, rng.randint(22, 33))
    elif label == 'sleet':
        temp = max(27, min(temp, rng.randint(29, 35)))
    elif label == 'rain':
        temp = max(temp, 34 + rng.randint(0, 4))
    elif label == 'heat':
        temp = max(temp, rng.randint(86, 98))
    humid_zone = zone in ('southeast', 'deep_south', 'appalachian') or hemi == 'T'
    if label in PRECIP_KINDS:
        humidity = rng.uniform(0.82, 0.97)
    elif label == 'heat':
        humidity = rng.uniform(0.60, 0.80) if humid_zone else rng.uniform(0.20, 0.40)
    else:
        humidity = rng.uniform(0.55, 0.80) if humid_zone else rng.uniform(0.30, 0.65)
    wind = rng.uniform(17, 30) if label == 'wind' else rng.random() ** 1.6 * 14
    wind_dir = rng.uniform(0, 360)
    intensity = 0.0
    precip = 'none'
    if label in PRECIP_KINDS:
        precip = label
        levels = [lv for lv, _ in _INTENSITY_LEVELS]
        weights = [w for _, w in _INTENSITY_LEVELS]
        intensity = max(0.15, min(1.0, rng.choices(levels, weights=weights)[0]
                                  + rng.gauss(0, 0.06)))
    w = _period_weights(zone, period)
    wet_share = (w[1] + w[2] + w[3]) / max(1, sum(w))
    periods = []
    for q in range(4):
        if q > 0:
            temp += round(rng.gauss(-1.0, 1.5))
            wind = max(0.0, min(40.0, wind + rng.gauss(0, 2.5)))
            wind_dir += rng.gauss(0, 12)
            if precip != 'none':
                if rng.random() < 0.15:
                    precip, intensity = 'none', 0.0
                else:
                    intensity = max(0.12, min(1.0, intensity + rng.gauss(0, 0.12)))
            elif rng.random() < 0.10 * wet_share:
                precip = 'rain' if temp >= 34 else ('snow' if temp <= 30 else 'sleet')
                intensity = rng.uniform(0.2, 0.5)
        if precip != 'none':
            precip = 'rain' if temp >= 35 else ('snow' if temp <= 30 else precip)
        periods.append(Reading(temp_f=int(temp), precip=precip, intensity=intensity,
                               wind_mph=wind, wind_dir=wind_dir, humidity=humidity))
    if venue.roof == 'retractable':
        first = periods[0]
        closed = first.precip != 'none' or first.temp_f < 45 or first.heat_index > 90
        venue = Venue(roof='closed' if closed else 'open', surface=venue.surface,
                      altitude_ft=venue.altitude_ft, retractable=True)
    if venue.roof in ('dome', 'closed'):
        periods = [Reading(temp_f=70, humidity=0.45) for _ in periods]
    return GameWeather(periods=periods, venue=venue, zone=zone, season=period)


def weather_for_team(team, week: int = 5, total_weeks: int = 18, league: str = 'college',
                     neutral_state: Optional[str] = None, neutral_city: Optional[str] = None,
                     climate_zone: Optional[str] = None, month: Optional[str] = None,
                     rng=None) -> GameWeather:
    """Weather at a home team's venue, or at a neutral site."""
    if neutral_state or neutral_city or climate_zone:
        venue = venue_for(f"neutral:{neutral_city or neutral_state}", neutral_state,
                          neutral_city, league)
        return build_game_weather(neutral_state, neutral_city, week, total_weeks,
                                  climate_zone=climate_zone, venue=venue, month=month, rng=rng)
    state = getattr(team, 'state', '') or ''
    city = getattr(team, 'city', '') or ''
    venue = venue_for(getattr(team, 'name', ''), state, city, league)
    return build_game_weather(state, city, week, total_weeks, venue=venue, month=month, rng=rng)


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
