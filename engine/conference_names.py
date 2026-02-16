"""
Conference Name Generator for Viperball

Generates thematic conference names for Season and Dynasty modes.
Uses word pools inspired by geography, mythology, weather, and Viperball lore.
"""

import random
from typing import List, Optional

PREFIXES = [
    "Viper", "Iron", "Storm", "Thunder", "Horizon", "Summit",
    "Frontier", "Pacific", "Atlantic", "Great Lakes", "Prairie",
    "Coastal", "Mountain", "Valley", "Delta", "Northern",
    "Southern", "Eastern", "Western", "Golden", "Silver",
    "Crimson", "Midnight", "Eclipse", "Pinnacle", "Crossroads",
    "Capital", "Liberty", "Heritage", "Pioneer", "Apex",
    "Forge", "Skyline", "Tidewater", "Heartland", "Cascade",
    "Ember", "Granite", "Colonial", "Trident", "Falcon",
    "Wildfire", "Obsidian", "Cobalt", "Redwood", "Canyon",
    "Bayou", "Highland", "Lakeshore", "Metro", "Sun Belt",
]

SUFFIXES = [
    "Conference", "League", "Union", "Athletic Conference",
    "Division", "Federation", "Alliance", "Circuit",
    "Association", "Collective",
]

FULL_NAMES = [
    "Viper Coast Conference", "Iron Belt League", "Storm Front Division",
    "Thunder Plains Conference", "Horizon Athletic Union", "Summit League",
    "Pacific Rim Conference", "Atlantic Seaboard League", "Great Lakes Union",
    "Prairie Fire Conference", "Coastal Empire League", "Mountain West Union",
    "Delta Conference", "Northern Frontier League", "Southern Cross Conference",
    "Golden Gate League", "Silver Shield Conference", "Crimson Tide League",
    "Midnight Sun Conference", "Eclipse Athletic League", "Pinnacle Conference",
    "Crossroads League", "Capital District Conference", "Liberty Bell League",
    "Heritage Conference", "Pioneer Athletic League", "Apex Conference",
    "Forge Conference", "Skyline Athletic League", "Tidewater Conference",
    "Heartland League", "Cascade Conference", "Ember Athletic Union",
    "Granite Shield Conference", "Colonial Athletic League", "Trident Conference",
    "Falcon Crest League", "Wildfire Conference", "Obsidian League",
    "Cobalt Conference", "Redwood Athletic League", "Canyon Conference",
    "Bayou Conference", "Highland Athletic League", "Lakeshore Conference",
    "Metro Athletic Conference", "Sun Country League", "Gateway League",
    "Yankee Conference", "Patriot League", "Territorial Conference",
    "Frontier Athletic Union", "Copper Belt League", "Steel City Conference",
    "Blue Ridge League", "Gulf Stream Conference", "Timberline League",
    "Rio Grande Conference", "Panhandle Athletic League", "Flatlands Conference",
    "Archipelago League", "Borealis Conference", "Solstice Athletic Union",
    "Thunderhead Conference", "Dustbowl League", "Ridgeline Conference",
]


def generate_conference_names(
    count: int = 2,
    seed: Optional[int] = None,
    exclude: Optional[List[str]] = None,
) -> List[str]:
    """Generate unique conference names.

    Args:
        count: Number of names to generate (1-8).
        seed: Optional random seed for reproducibility.
        exclude: Names to avoid duplicating.

    Returns:
        List of generated conference name strings.
    """
    count = max(1, min(8, count))
    exclude_set = set(exclude or [])

    rng = random.Random(seed)

    pool = [n for n in FULL_NAMES if n not in exclude_set]
    rng.shuffle(pool)

    if len(pool) >= count:
        return pool[:count]

    names: List[str] = list(pool)
    available_prefixes = list(PREFIXES)
    available_suffixes = list(SUFFIXES)
    rng.shuffle(available_prefixes)

    while len(names) < count:
        prefix = available_prefixes[len(names) % len(available_prefixes)]
        suffix = rng.choice(available_suffixes)
        candidate = f"{prefix} {suffix}"
        if candidate not in exclude_set and candidate not in names:
            names.append(candidate)

    return names


def generate_single_name(
    seed: Optional[int] = None,
    exclude: Optional[List[str]] = None,
) -> str:
    """Generate a single conference name."""
    return generate_conference_names(count=1, seed=seed, exclude=exclude)[0]
