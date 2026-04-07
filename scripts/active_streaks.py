#!/usr/bin/env python3
"""
Analyze active streaks of schools qualifying at least one player to state tennis.
Uses the OSAA detail file, focusing on modern era (2007+) where individual entries are listed.
"""

import re
import sys
from collections import defaultdict

def parse_detail_file(filepath):
    """Parse the detail file and extract school names by year."""
    with open(filepath) as f:
        text = f.read()

    year_sections = re.split(r'#{5,}\n# YEAR: (\d{4})\n#{5,}', text)

    year_data = {}
    for i in range(1, len(year_sections), 2):
        year = int(year_sections[i])
        content = year_sections[i+1]
        year_data[year] = content

    return year_data


# Known school name mappings for normalization
SCHOOL_ALIASES = {
    'OES': 'Oregon Episcopal',
    'Oregon Episcopal School': 'Oregon Episcopal',
    'Catlin-Gabel': 'Catlin Gabel',
    'Catlin Gabel School': 'Catlin Gabel',
    'La Salle Prep': 'La Salle',
    'La Salle Catholic': 'La Salle',
    'Ida B. Wells': 'Wells',
    'Wilson': 'Wells',  # Renamed
    'Marist Catholic': 'Marist',
    'St. Mary\'s': 'St. Marys',
    "St. Mary's": 'St. Marys',
    "St. Mary's, Medford": 'St. Marys',
    'St. Marys, Medford': 'St. Marys',
    'Hood River Valley': 'Hood River',
    'Baker / Powder Valley': 'Baker',
    'Ione / Heppner': 'Ione',
    'Stanfield / Echo': 'Stanfield',
    'Weston-McEwen / Griswold': 'Weston-McEwen',
    'Riverdale': 'Riverdale',
    'Four Rivers': 'Four Rivers',
}


def normalize_school(name):
    """Normalize school name."""
    name = name.strip(' .,;:')

    # Remove truncation artifacts (ellipsis, trailing dots)
    name = re.sub(r'[\u2026…]+$', '', name)
    name = re.sub(r'\.{2,}$', '', name)
    name = name.strip()

    # Remove parenthetical numbers like "( 3)" which are point totals
    name = re.sub(r'\s*\(\s*\d+\s*\)$', '', name)

    # Apply aliases
    if name in SCHOOL_ALIASES:
        return SCHOOL_ALIASES[name]

    return name


def extract_schools_modern(content, year):
    """
    Extract schools from modern format (2007+) individual draw entries.
    Format: "(seed) FirstName LastName Grade, School"
    or doubles: "(seed) Name1 Grade / Name2 Grade, School"
    """
    schools = set()

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip non-entry lines
        if len(line) < 5:
            continue

        # Match: optional seed, name(s), grade, comma, school
        # Singles: "(1) Zareh Gonzalvo 11, Catlin Gabel"
        # Doubles: "(1) A. Smith 10 / B. Jones 11, School Name"
        # Also: "Zareh Gonzalvo 11, Catlin Gabel"

        # Try doubles first
        m = re.match(
            r'(?:\([\d/]+\)\s*)?'  # optional seed
            r'.+?\s+\d{1,2}\s*/\s*.+?\s+\d{1,2}'  # name grade / name grade
            r'\s*,\s*'  # comma
            r'(.+?)$',  # school
            line
        )
        if not m:
            # Try singles
            m = re.match(
                r'(?:\([\d/]+\)\s*)?'  # optional seed
                r'[A-Z][a-zA-Z\.\s\'-]+?'  # name
                r'\s+(\d{1,2})'  # grade
                r'\s*,\s*'  # comma
                r'(.+?)$',  # school
                line
            )
            if m:
                grade = m.group(1)
                school_raw = m.group(2)
            else:
                continue
        else:
            school_raw = m.group(1)
            grade = None

        if not m:
            continue

        school_raw = school_raw if grade is None else school_raw

        school = normalize_school(school_raw)

        # Filter junk
        if not school or len(school) < 2:
            continue
        if re.match(r'^\d', school):
            continue
        if re.match(r'^(Round|May|Friday|Saturday|Sunday|Final|Semifinal|Quarterfinal|Championship|Consolation|State|BYE|bye|def|default)', school, re.IGNORECASE):
            continue
        # Skip if it's just truncated to 1-2 chars
        if len(school) <= 2:
            continue

        schools.add(school)

    return schools


def extract_schools_from_standings(content):
    """Extract school names from team standings sections."""
    schools = set()
    lines = content.split('\n')

    in_standings = False
    for line in lines:
        stripped = line.strip()

        if re.match(r'(?:TEAM\s+(?:STANDINGS|TOTALS|SCORES)|Final\s+Team\s+Standings)', stripped, re.IGNORECASE):
            in_standings = True
            continue

        if in_standings:
            if not stripped or re.match(r'^#{3,}', stripped):
                in_standings = False
                continue
            if re.match(r'^(BOYS|GIRLS|SINGLES|DOUBLES)\s*$', stripped, re.IGNORECASE):
                in_standings = True  # Still in standings, just a section header
                continue

            # Format: "1. School Name, points; ..." or "School points, School points"
            # Modern: "1. Oregon Episcopal School, 23; 2. Cascade Christian, 8"
            # Old: "Roseburg 16 Wilson 13 Beaverton 11"

            # Try modern numbered format
            matches = re.findall(r'(?:\d+\.\s+)?([A-Z][A-Za-z\s\'\.\-/\(\)]+?)(?:\s*,\s*|\s+)(\d+(?:\.\d+)?)\s*(?:;|$|points?)', stripped)
            for school_name, _points in matches:
                school = normalize_school(school_name.strip())
                if school and len(school) > 2:
                    schools.add(school)

            # Try old format: "School Points School Points"
            if not matches:
                matches = re.findall(r'([A-Z][A-Za-z\s\'\.\-]+?)\s+(\d+)', stripped)
                for school_name, _points in matches:
                    school = normalize_school(school_name.strip())
                    if school and len(school) > 2:
                        schools.add(school)

    return schools


def main():
    filepath = '/home/user/viperball/data/catlin_gabel_tennis_detail.txt'
    year_data = parse_detail_file(filepath)

    print(f"Found {len(year_data)} years of data: {min(year_data.keys())}-{max(year_data.keys())}")

    # We only have certain years in the file - list them
    available_years = sorted(year_data.keys())
    print(f"Available years: {available_years}")
    print()

    schools_by_year = {}

    for year in sorted(year_data.keys()):
        content = year_data[year]
        schools = set()

        if year >= 2007:
            schools = extract_schools_modern(content, year)

        # Always try standings too (works for all eras)
        standing_schools = extract_schools_from_standings(content)
        schools.update(standing_schools)

        # Filter out obvious junk
        cleaned = set()
        for s in schools:
            if len(s) <= 2:
                continue
            if s.endswith('…') or '…' in s:
                continue
            if re.search(r'[…\u2026]', s):
                continue
            # Skip if name is too short (truncated OCR)
            if len(s) <= 3 and not s.isupper():
                continue
            cleaned.add(s)

        schools_by_year[year] = cleaned

    # Data quality check
    print("Schools per year (recent):")
    for year in range(2015, 2026):
        s = schools_by_year.get(year, set())
        print(f"  {year}: {len(s)} schools")
    print()

    # Show 2025 schools for validation
    print("2025 schools:")
    for s in sorted(schools_by_year.get(2025, set())):
        print(f"  {s}")
    print()

    # Find all years we have data for (excluding 2020 COVID)
    # The file only has years where CG was mentioned, but team standings
    # give us ALL schools for those years.
    # For a proper streak analysis, we need continuous year coverage.
    # Let's check which years we have:
    modern_years = [y for y in available_years if y >= 2007]
    print(f"Modern years with data: {modern_years}")
    print()

    # Calculate active streaks ending in 2025
    # A streak breaks if a school is absent in a year we have data for
    # Skip 2020 (COVID, no tournament) and 2021 (some classifications had state, some didn't)
    streak_years = [y for y in modern_years if y not in (2020,)]

    all_schools = set()
    for y in streak_years:
        all_schools.update(schools_by_year.get(y, set()))

    active_streaks = {}

    for school in sorted(all_schools):
        if school not in schools_by_year.get(2025, set()):
            continue

        streak = 0
        for year in reversed(streak_years):
            if school in schools_by_year.get(year, set()):
                streak += 1
            else:
                break

        start_year = streak_years[len(streak_years) - streak] if streak > 0 else 2025
        active_streaks[school] = (streak, start_year)

    # Sort by streak length
    sorted_streaks = sorted(active_streaks.items(), key=lambda x: (-x[1][0], x[0]))

    print("=" * 70)
    print("ACTIVE STREAKS - Consecutive years with state qualifier(s) through 2025")
    print("(2020 excluded - COVID, no tournament)")
    print(f"Years tracked: {streak_years}")
    print("=" * 70)
    print()

    max_possible = len(streak_years)
    print(f"Maximum possible streak: {max_possible} years")
    print()

    # Print in tiers
    for min_streak in [max_possible, 10, 5, 3]:
        tier = [(s, info) for s, info in sorted_streaks if info[0] >= min_streak]
        if min_streak == max_possible:
            label = f"PERFECT STREAKS ({max_possible} years - never missed)"
        else:
            label = f"{min_streak}+ YEAR STREAKS"

        print(f"--- {label} ---")
        if not tier:
            print("  (none)")
        for school, (streak, start) in tier:
            if streak >= min_streak and (min_streak == max_possible or streak < (10 if min_streak == 5 else (max_possible if min_streak == 10 else 5))):
                print(f"  {streak:2d} years  ({start}-2025)  {school}")
        print()


if __name__ == '__main__':
    main()
