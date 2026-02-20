#!/usr/bin/env python3
"""
NCAA Women's Sports Name Harvester

Scrapes publicly available roster pages from NCAA women's athletics websites
to expand the Viperball player name pools. Extracts first names and surnames
from multiple schools across multiple sports.

Usage:
    python scripts/harvest_ncaa_names.py
"""

import json
import re
import time
import random
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Set, Tuple
from html.parser import HTMLParser


DATA_DIR = Path(__file__).parent.parent / 'data' / 'name_pools'

ROSTER_URLS = {
    "goheels.com": [
        "https://goheels.com/sports/womens-basketball/roster/2024-25",
        "https://goheels.com/sports/womens-soccer/roster/2024",
        "https://goheels.com/sports/softball/roster/2025",
        "https://goheels.com/sports/volleyball/roster/2024",
        "https://goheels.com/sports/womens-lacrosse/roster/2025",
    ],
    "goduke.com": [
        "https://goduke.com/sports/womens-basketball/roster",
        "https://goduke.com/sports/womens-soccer/roster",
        "https://goduke.com/sports/softball/roster",
        "https://goduke.com/sports/volleyball/roster",
    ],
    "gopack.com": [
        "https://gopack.com/sports/womens-basketball/roster",
        "https://gopack.com/sports/womens-soccer/roster",
        "https://gopack.com/sports/softball/roster",
    ],
    "rolltide.com": [
        "https://rolltide.com/sports/womens-basketball/roster",
        "https://rolltide.com/sports/softball/roster",
        "https://rolltide.com/sports/womens-soccer/roster",
        "https://rolltide.com/sports/volleyball/roster",
    ],
    "texassports.com": [
        "https://texassports.com/sports/womens-basketball/roster",
        "https://texassports.com/sports/softball/roster",
        "https://texassports.com/sports/volleyball/roster",
        "https://texassports.com/sports/womens-soccer/roster",
    ],
    "uclabruins.com": [
        "https://uclabruins.com/sports/womens-basketball/roster",
        "https://uclabruins.com/sports/softball/roster",
        "https://uclabruins.com/sports/womens-soccer/roster",
    ],
    "ohiostatebuckeyes.com": [
        "https://ohiostatebuckeyes.com/sports/womens-basketball/roster",
        "https://ohiostatebuckeyes.com/sports/womens-soccer/roster",
        "https://ohiostatebuckeyes.com/sports/volleyball/roster",
    ],
    "gostanford.com": [
        "https://gostanford.com/sports/womens-basketball/roster",
        "https://gostanford.com/sports/womens-soccer/roster",
        "https://gostanford.com/sports/softball/roster",
    ],
    "uconnhuskies.com": [
        "https://uconnhuskies.com/sports/womens-basketball/roster",
        "https://uconnhuskies.com/sports/womens-soccer/roster",
        "https://uconnhuskies.com/sports/softball/roster",
    ],
    "lsusports.net": [
        "https://lsusports.net/sports/womens-basketball/roster",
        "https://lsusports.net/sports/softball/roster",
        "https://lsusports.net/sports/womens-soccer/roster",
    ],
    "hawkeyesports.com": [
        "https://hawkeyesports.com/sports/womens-basketball/roster",
        "https://hawkeyesports.com/sports/softball/roster",
    ],
    "gocards.com": [
        "https://gocards.com/sports/womens-basketball/roster",
        "https://gocards.com/sports/softball/roster",
    ],
    "seminoles.com": [
        "https://seminoles.com/sports/womens-basketball/roster",
        "https://seminoles.com/sports/softball/roster",
        "https://seminoles.com/sports/womens-soccer/roster",
    ],
    "oregonducks.com": [
        "https://oregonducks.com/sports/womens-basketball/roster",
        "https://oregonducks.com/sports/softball/roster",
    ],
    "osubeavers.com": [
        "https://osubeavers.com/sports/womens-basketball/roster",
        "https://osubeavers.com/sports/softball/roster",
    ],
    "gopsusports.com": [
        "https://gopsusports.com/sports/womens-basketball/roster",
        "https://gopsusports.com/sports/womens-soccer/roster",
        "https://gopsusports.com/sports/volleyball/roster",
    ],
    "mgoblue.com": [
        "https://mgoblue.com/sports/womens-basketball/roster",
        "https://mgoblue.com/sports/softball/roster",
    ],
    "huskers.com": [
        "https://huskers.com/sports/womens-basketball/roster",
        "https://huskers.com/sports/volleyball/roster",
    ],
    "gofrogs.com": [
        "https://gofrogs.com/sports/womens-basketball/roster",
        "https://gofrogs.com/sports/volleyball/roster",
    ],
    "scarletknights.com": [
        "https://scarletknights.com/sports/womens-basketball/roster",
        "https://scarletknights.com/sports/womens-soccer/roster",
    ],
    "cuse.com": [
        "https://cuse.com/sports/womens-basketball/roster",
        "https://cuse.com/sports/womens-lacrosse/roster",
    ],
    "nmstatesports.com": [
        "https://nmstatesports.com/sports/womens-basketball/roster",
        "https://nmstatesports.com/sports/softball/roster",
    ],
    "govols.com": [
        "https://govols.com/sports/womens-basketball/roster",
        "https://govols.com/sports/softball/roster",
    ],
    "arkansasrazorbacks.com": [
        "https://arkansasrazorbacks.com/sports/womens-basketball/roster",
        "https://arkansasrazorbacks.com/sports/softball/roster",
    ],
    "outerheels.com": [
        "https://goterps.com/sports/womens-basketball/roster",
        "https://goterps.com/sports/womens-lacrosse/roster",
    ],
}

NAME_PATTERN = re.compile(r'\*\*([A-Z][a-zA-Z\'\-]+(?:\s+(?:\"[^\"]+\"\s+)?[A-Z][a-zA-Z\'\-]+)+)\*\*')

SKIP_NAMES = {
    "Head Coach", "Assistant Coach", "Associate Head Coach",
    "Director of", "Coaching Staff", "Support Staff",
    "Full Bio", "View Card", "Table View", "List View",
    "Print Roster", "Jump to", "Skip Ad", "Skip to",
    "Buy Tickets", "Buy Now", "Live Audio", "Live Video",
    "Live Stats", "Story Recap", "Boxscore",
}

INVALID_FIRST_NAMES = {
    "Head", "Assistant", "Associate", "Director", "Coaching", "Support",
    "Full", "View", "Table", "List", "Print", "Jump", "Skip", "Buy",
    "Live", "Story", "Jersey", "Position", "Class", "Hometown", "Height",
    "Phone", "Major", "Academic", "Season", "Forward", "Guard", "Center",
}

def fetch_page(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ViperballNameHarvester/1.0)',
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"    FAILED: {e}")
        return ""


def extract_names_from_html(html: str) -> List[str]:
    names = []
    bold_pattern = re.compile(r'<b>([^<]+)</b>|<strong>([^<]+)</strong>')
    for m in bold_pattern.finditer(html):
        text = m.group(1) or m.group(2)
        text = text.strip()
        if text and len(text.split()) >= 2:
            names.append(text)

    link_name = re.compile(r'roster/[a-z\-]+/\d+[^"]*"[^>]*>\s*([A-Z][^<]+)</a>', re.IGNORECASE)
    for m in link_name.finditer(html):
        text = m.group(1).strip()
        if text and len(text.split()) >= 2:
            names.append(text)

    aria_label = re.compile(r'aria-label="[^"]*(?:Bio|bio)[^"]*for\s+([A-Z][^"]+)"', re.IGNORECASE)
    for m in aria_label.finditer(html):
        text = m.group(1).strip()
        if text and len(text.split()) >= 2:
            names.append(text)

    return names


def is_valid_name(full_name: str) -> bool:
    if any(skip in full_name for skip in SKIP_NAMES):
        return False
    parts = full_name.split()
    if len(parts) < 2 or len(parts) > 4:
        return False
    first = parts[0].strip('"')
    if first in INVALID_FIRST_NAMES:
        return False
    for p in parts:
        clean = p.strip('"').strip("'")
        if not clean:
            continue
        if not clean[0].isupper():
            return False
        if len(clean) < 2:
            return False
        if any(c.isdigit() for c in clean):
            return False
    return True


def split_name(full_name: str) -> Tuple[str, str]:
    full_name = re.sub(r'"[^"]*"\s*', '', full_name).strip()
    parts = full_name.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 3:
        return parts[0], parts[-1]
    elif len(parts) >= 4:
        return parts[0], parts[-1]
    return parts[0], parts[-1] if len(parts) > 1 else ""


def harvest_all() -> Tuple[Set[str], Set[str]]:
    all_first = set()
    all_last = set()
    total_urls = sum(len(urls) for urls in ROSTER_URLS.values())

    print(f"Harvesting names from {total_urls} roster pages across {len(ROSTER_URLS)} schools...")
    print()

    fetched = 0
    for school, urls in ROSTER_URLS.items():
        print(f"  [{school}]")
        for url in urls:
            fetched += 1
            sport = url.split("/sports/")[1].split("/")[0] if "/sports/" in url else "unknown"
            print(f"    ({fetched}/{total_urls}) {sport}...", end=" ", flush=True)

            html = fetch_page(url)
            if not html:
                continue

            names = extract_names_from_html(html)
            valid = 0
            for name in names:
                if is_valid_name(name):
                    first, last = split_name(name)
                    if first and last and len(first) >= 2 and len(last) >= 2:
                        all_first.add(first)
                        all_last.add(last)
                        valid += 1
            print(f"{valid} names")

            time.sleep(random.uniform(0.5, 1.5))

    return all_first, all_last


def merge_into_pools(first_names: Set[str], last_names: Set[str]):
    first_path = DATA_DIR / 'first_names.json'
    surname_path = DATA_DIR / 'surnames.json'

    with open(first_path) as f:
        existing_first = json.load(f)
    with open(surname_path) as f:
        existing_surnames = json.load(f)

    existing_first_all = set()
    for names in existing_first.values():
        existing_first_all.update(names)
    existing_last_all = set()
    for names in existing_surnames.values():
        existing_last_all.update(names)

    new_first = first_names - existing_first_all
    new_last = last_names - existing_last_all

    print(f"\n=== MERGE RESULTS ===")
    print(f"  Harvested first names: {len(first_names)} total, {len(new_first)} new")
    print(f"  Harvested last names:  {len(last_names)} total, {len(new_last)} new")

    target_categories_first = [
        'american_northeast', 'american_south', 'american_midwest',
        'american_west', 'american_texas_southwest',
    ]
    target_categories_last = [
        'american_general',
    ]

    new_first_list = sorted(new_first)
    chunk_size = max(1, len(new_first_list) // len(target_categories_first))
    for i, cat in enumerate(target_categories_first):
        start = i * chunk_size
        end = start + chunk_size if i < len(target_categories_first) - 1 else len(new_first_list)
        batch = new_first_list[start:end]
        existing_first[cat] = sorted(set(existing_first.get(cat, []) + batch))
        print(f"  Added {len(batch)} first names to '{cat}' (now {len(existing_first[cat])})")

    new_last_list = sorted(new_last)
    for cat in target_categories_last:
        existing_surnames[cat] = sorted(set(existing_surnames.get(cat, []) + new_last_list))
        print(f"  Added {len(new_last_list)} surnames to '{cat}' (now {len(existing_surnames[cat])})")

    for cat in list(existing_surnames.keys()):
        if cat != 'american_general':
            extras = [n for n in new_last_list if _surname_matches_category(n, cat)]
            if extras:
                existing_surnames[cat] = sorted(set(existing_surnames[cat] + extras))

    with open(first_path, 'w') as f:
        json.dump(existing_first, f, indent=2, ensure_ascii=False)
    with open(surname_path, 'w') as f:
        json.dump(existing_surnames, f, indent=2, ensure_ascii=False)

    total_first = sum(len(v) for v in existing_first.values())
    total_last = sum(len(v) for v in existing_surnames.values())
    print(f"\n  Final totals: {total_first} first names, {total_last} surnames")


SURNAME_HINTS = {
    'latino_hispanic': [
        'Garcia', 'Rodriguez', 'Martinez', 'Lopez', 'Hernandez', 'Gonzalez',
        'Perez', 'Sanchez', 'Ramirez', 'Torres', 'Flores', 'Rivera',
        'Gomez', 'Diaz', 'Reyes', 'Cruz', 'Morales', 'Ortiz', 'Gutierrez',
        'Chavez', 'Ramos', 'Vargas', 'Castillo', 'Mendoza', 'Ruiz',
        'Alvarez', 'Romero', 'Herrera', 'Medina', 'Aguilar', 'Vega',
        'Castro', 'Vasquez', 'Soto', 'Delgado', 'Rios', 'Salazar',
    ],
    'irish': [
        "O'Brien", "O'Connor", "O'Neill", "O'Sullivan", "O'Malley",
        'Murphy', 'Kelly', 'Walsh', 'Ryan', 'Sullivan', 'Brennan',
        'Fitzgerald', 'McCarthy', 'Gallagher', 'Quinn', 'Doyle',
        'Connolly', 'Flanagan', 'Callahan', 'Donnelly', 'Nolan',
    ],
    'italian': [
        'Rossi', 'Russo', 'Ferrari', 'Romano', 'Colombo', 'Ricci',
        'Marino', 'Greco', 'Bruno', 'Gallo', 'Conti', 'Costa',
        'De Luca', 'Esposito', 'Mancini', 'Lombardi',
    ],
    'german': [
        'Mueller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer',
        'Wagner', 'Becker', 'Schulz', 'Hoffmann', 'Koch', 'Bauer',
        'Richter', 'Klein', 'Schroeder', 'Neumann', 'Zimmerman',
    ],
    'chinese': [
        'Wang', 'Li', 'Zhang', 'Liu', 'Chen', 'Yang', 'Huang', 'Wu',
        'Zhou', 'Xu', 'Sun', 'Zhao', 'Lin', 'Zhu', 'Luo', 'Guo',
    ],
    'korean': [
        'Kim', 'Lee', 'Park', 'Choi', 'Jung', 'Kang', 'Cho', 'Yoon',
        'Jang', 'Lim', 'Han', 'Oh', 'Seo', 'Shin', 'Kwon', 'Hwang',
    ],
    'japanese': [
        'Sato', 'Suzuki', 'Takahashi', 'Tanaka', 'Watanabe', 'Ito',
        'Yamamoto', 'Nakamura', 'Kobayashi', 'Kato', 'Yoshida',
        'Yamada', 'Sasaki', 'Yamaguchi', 'Matsumoto', 'Inoue',
    ],
}

def _surname_matches_category(surname: str, category: str) -> bool:
    hints = SURNAME_HINTS.get(category, [])
    if not hints:
        return False
    for hint in hints:
        if surname.lower() == hint.lower():
            return True
        if surname.lower().startswith(hint.lower()[:3]):
            return True
    return False


if __name__ == "__main__":
    first_names, last_names = harvest_all()

    if first_names or last_names:
        merge_into_pools(first_names, last_names)
    else:
        print("\nNo names harvested. Check network connectivity or URL availability.")
