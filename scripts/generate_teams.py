#!/usr/bin/env python3
"""
Viperball Team Profile Generator

Assigns play styles, recruiting pipelines, and identities to each school.

Usage:
    python scripts/generate_teams.py
"""

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

def generate_team_identity(school_data):
    """Generate team identity based on school characteristics."""

    # Determine style based on region and culture
    styles = ['aggressive', 'conservative', 'balanced']
    philosophies = ['kick_heavy', 'lateral_heavy', 'ground_and_pound', 'hybrid']
    tempos = ['fast', 'slow', 'variable']
    two_way_emphasis = ['high', 'moderate', 'low']

    # Bias based on athletic culture
    if school_data['athletic_culture'] == 'basketball_first':
        style = random.choices(styles, weights=[0.4, 0.2, 0.4])[0]
        philosophy = random.choices(philosophies, weights=[0.3, 0.4, 0.1, 0.2])[0]
        tempo = random.choices(tempos, weights=[0.5, 0.2, 0.3])[0]
        emphasis = random.choices(two_way_emphasis, weights=[0.3, 0.5, 0.2])[0]
    elif school_data['athletic_culture'] == 'hockey_first':
        style = random.choices(styles, weights=[0.5, 0.2, 0.3])[0]
        philosophy = random.choices(philosophies, weights=[0.2, 0.3, 0.3, 0.2])[0]
        tempo = random.choices(tempos, weights=[0.6, 0.1, 0.3])[0]
        emphasis = random.choices(two_way_emphasis, weights=[0.6, 0.3, 0.1])[0]
    elif school_data['athletic_culture'] == 'soccer_strong':
        style = random.choices(styles, weights=[0.3, 0.3, 0.4])[0]
        philosophy = random.choices(philosophies, weights=[0.3, 0.5, 0.1, 0.1])[0]
        tempo = random.choices(tempos, weights=[0.5, 0.2, 0.3])[0]
        emphasis = random.choices(two_way_emphasis, weights=[0.5, 0.4, 0.1])[0]
    else:  # multi_sport, lacrosse_strong, etc.
        style = random.choice(styles)
        philosophy = random.choice(philosophies)
        tempo = random.choice(tempos)
        emphasis = random.choice(two_way_emphasis)

    return {
        'style': style,
        'philosophy': philosophy,
        'tempo': tempo,
        'two_way_emphasis': emphasis
    }

def generate_recruiting_pipeline(school_data):
    """Generate recruiting pipeline weights based on school location and region."""

    region = school_data['region']
    state = school_data['state']

    # Base pipeline
    pipeline = {}

    # Local/regional recruiting (primary focus)
    if region == 'northeast':
        pipeline['northeast'] = 0.50
        pipeline['mid_atlantic'] = 0.15
        pipeline['midwest'] = 0.10
        pipeline['australian'] = 0.15
        pipeline['pacific_islander'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'mid_atlantic':
        pipeline['mid_atlantic'] = 0.50
        pipeline['northeast'] = 0.15
        pipeline['south'] = 0.10
        pipeline['australian'] = 0.15
        pipeline['midwest'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'south':
        pipeline['south'] = 0.50
        pipeline['mid_atlantic'] = 0.15
        pipeline['midwest'] = 0.10
        pipeline['australian'] = 0.15
        pipeline['pacific_islander'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'midwest':
        pipeline['midwest'] = 0.50
        pipeline['northeast'] = 0.10
        pipeline['south'] = 0.10
        pipeline['australian'] = 0.20
        pipeline['pacific_islander'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'west_coast':
        pipeline['west_coast'] = 0.45
        pipeline['australian'] = 0.25
        pipeline['pacific_islander'] = 0.15
        pipeline['midwest'] = 0.05
        pipeline['texas_southwest'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'texas_southwest':
        pipeline['texas_southwest'] = 0.50
        pipeline['south'] = 0.15
        pipeline['west_coast'] = 0.10
        pipeline['australian'] = 0.15
        pipeline['midwest'] = 0.05
        pipeline['other'] = 0.05
    elif region == 'mountain_west':
        pipeline['mountain_west'] = 0.40
        pipeline['west_coast'] = 0.20
        pipeline['australian'] = 0.20
        pipeline['midwest'] = 0.10
        pipeline['pacific_islander'] = 0.05
        pipeline['other'] = 0.05
    else:
        # Default balanced pipeline
        pipeline['midwest'] = 0.30
        pipeline['northeast'] = 0.20
        pipeline['australian'] = 0.20
        pipeline['south'] = 0.15
        pipeline['west_coast'] = 0.10
        pipeline['other'] = 0.05

    # Normalize to ensure sum = 1.0
    total = sum(pipeline.values())
    pipeline = {k: v/total for k, v in pipeline.items()}

    return pipeline

def main():
    """Generate team profiles for all schools."""

    # Load schools database
    with open(DATA_DIR / 'schools' / 'd1_non_football.json') as f:
        schools_data = json.load(f)

    print(f"Generating team profiles for {schools_data['total_schools']} schools...")

    # Process each school
    for school in schools_data['schools']:
        school_id = school['school_id']

        # Generate identity
        identity = generate_team_identity(school)

        # Generate recruiting pipeline
        recruiting_pipeline = generate_recruiting_pipeline(school)

        # Add to school data
        school['identity'] = identity
        school['recruiting_pipeline'] = recruiting_pipeline

        print(f"  ✓ {school['school_name']}: {identity['style']}/{identity['philosophy']}")

    # Save updated schools database
    output_path = DATA_DIR / 'schools' / 'd1_non_football.json'
    with open(output_path, 'w') as f:
        json.dump(schools_data, f, indent=2)

    print(f"\n✅ Team profiles saved to {output_path}")
    print(f"   Total schools: {schools_data['total_schools']}")

if __name__ == "__main__":
    main()
