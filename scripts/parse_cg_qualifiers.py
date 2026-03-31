#!/usr/bin/env python3
"""
Parse OCR text from OSAA tennis PDFs to extract Catlin Gabel state qualifiers.
"""

import os
import re
import csv

TEXT_DIR = "/tmp/osaa_text"
OUTPUT_CSV = "/home/user/viperball/data/catlin_gabel_tennis_state_qualifiers.csv"
OUTPUT_TXT = "/home/user/viperball/data/catlin_gabel_tennis_state_qualifiers.txt"

CG_YEARS = [1962, 1963, 1964, 1966, 1967, 1969, 1970, 1971, 1972,
            1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980,
            1982, 1983, 1984, 1985, 1986, 1987, 1988,
            1989, 1990, 1991, 1992,
            1993, 1994, 1995, 1996, 1997, 1998, 1999,
            2000, 2001, 2002, 2003, 2004, 2005, 2006,
            2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014,
            2015, 2016, 2017, 2018, 2019,
            2022, 2023, 2024, 2025]

# Regex for Catlin Gabel (including truncated OCR like "Catlin …" or "Catlin G...")
CG_PATTERN = re.compile(r'Catlin[\s-]+Gabel|Catlin\s+G\b|Catlin\s*[…]|Catlin\s*\.\.\.|Catlin Gab\b', re.IGNORECASE)


def extract_tennis_section(text):
    text_upper = text.upper()
    idx = text_upper.find("TENNIS")
    if idx == -1:
        return text
    # Look for next sport section header - must be standalone word on its own line
    # or preceded by newline/whitespace (not embedded in a name like "Wustrack")
    next_sports = ["TRACK", "BASEBALL", "SOFTBALL", "GOLF", "SWIMMING",
                   "WRESTLING", "BASKETBALL", "FOOTBALL", "VOLLEYBALL",
                   "SOCCER", "CROSS COUNTRY", "WATER POLO"]
    end_idx = len(text)
    for sport in next_sports:
        # Search for standalone sport header (word boundary)
        for m in re.finditer(r'(?:^|\n)\s*' + sport + r'\s*(?:\n|$)', text_upper):
            pos = m.start()
            if pos > idx + 10 and pos < end_idx:
                end_idx = pos
    return text[idx:end_idx]


def is_team_standing_line(line):
    """Check if this is just a team standings/points line."""
    l = line.strip().lower()
    # "Catlin Gabel" alone on a line (section header in modern format)
    if re.match(r'^\s*catlin[\s-]+gabel\s*$', l):
        return True
    # Lines like "5. Catlin Gabel, 8;" - numbered team ranking
    if re.search(r'\d+\.\s+.*catlin[\s-]+gabel', l):
        return True
    # Team standings: "School N, School N, ... Catlin Gabel N, ..."
    # Key indicator: multiple "word(s) N," patterns with no match result indicators
    if " d " not in l and "-" not in l:
        # No match results (no "d" for defeated, no scores like "6-3")
        if re.search(r'catlin[\s-]+gabel[,\s]+\d+\.?\d*[;.,\s]', l):
            return True
    return False


def parse_year(text, year):
    """Extract all Catlin Gabel player entries from tennis section."""
    lines = text.split("\n")
    qualifiers = []
    current_gender = "Unknown"
    current_event = "Unknown"
    seen = set()

    # For classic format (pre-2007), split long lines by semicolons
    # so each match result is its own "line" for parsing.
    # Also join lines where "Catlin Gabel" appears at start of a line
    # (continuation from previous line).
    joined_lines = []
    for line in lines:
        stripped_check = line.strip()
        if (joined_lines and
            re.match(r'^Catlin[\s-]+Gabel\b', stripped_check, re.IGNORECASE) and
            not re.match(r'^Catlin[\s-]+Gabel\s*$', stripped_check, re.IGNORECASE)):
            # Join with previous line
            joined_lines[-1] = joined_lines[-1].rstrip() + " " + stripped_check
        else:
            joined_lines.append(line)

    expanded_lines = []
    for line in joined_lines:
        if ";" in line and year < 2007:
            parts = line.split(";")
            expanded_lines.extend(parts)
        else:
            expanded_lines.append(line)

    for i, line in enumerate(expanded_lines):
        lu = line.upper().strip()

        # Track section headers
        if "GIRL" in lu:
            current_gender = "Girls"
        if "BOY" in lu:
            current_gender = "Boys"
        if "SINGLE" in lu:
            current_event = "Singles"
        if "DOUBLE" in lu:
            current_event = "Doubles"

        if not CG_PATTERN.search(line):
            continue
        if is_team_standing_line(line):
            continue

        stripped = line.strip()

        # CHECK DOUBLES FIRST (before singles, since singles regex can
        # partially match doubles lines like "Schrott 12 / McClanan 12, Catlin…")

        # Pattern 2 (modern doubles): "Name Gr / Name Gr, Catlin Gabel"
        # e.g. "N. Chen 12 / R. Nordhoff 11, Catlin Gabel"
        # e.g. "(1) Schrott 11 / McClanan 11, Catlin …"
        m = re.search(
            r'(?:\(\d+\)\s+)?([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*)\s+(\d{1,2})\s*/\s*([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*)\s+(\d{1,2}),\s*Catlin',
            stripped
        )
        if m:
            name1 = m.group(1).strip()
            grade1 = m.group(2)
            name2 = m.group(3).strip()
            grade2 = m.group(4)
            player = f"{name1} / {name2}"
            key = (year, current_gender, current_event, player)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": player,
                    "grade": f"{grade1}/{grade2}", "raw": stripped
                })
            continue

        # Pattern 7: "Name, Gr/Name, Gr, Catlin Gabel" (2007 doubles)
        m = re.search(
            r'([A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)+),\s*(\d{1,2})/([A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)+),\s*(\d{1,2}),\s*Catlin',
            stripped
        )
        if m:
            name1 = m.group(1).strip()
            grade1 = m.group(2)
            name2 = m.group(3).strip()
            grade2 = m.group(4)
            player = f"{name1} / {name2}"
            key = (year, current_gender, current_event, player)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": player,
                    "grade": f"{grade1}/{grade2}", "raw": stripped
                })
            continue

        # Modern format patterns (2005+) - these have structured draws with numeric grades
        if year >= 2005:
            # Skip lines with "/" if they weren't caught by doubles patterns above
            # (they're bracket progression duplicates with partial names)
            if "/" in stripped and re.search(r'\w+\s+\d{1,2}\s*/\s*\w+\s+\d{1,2}', stripped):
                continue

            # Pattern 1 (modern singles): "(Seed) FirstName LastName Grade, Catlin Gabel"
            m = re.search(
                r'(?:\(\d+\)\s+)?([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*)\s+(\d{1,2}),\s*Catlin',
                stripped
            )
            if m and "/" not in m.group(0):
                name = m.group(1).strip()
                grade = m.group(2)
                if len(name) > 2 and not name.isdigit():
                    key = (year, current_gender, current_event, name)
                    if key not in seen:
                        seen.add(key)
                        qualifiers.append({
                            "year": year, "gender": current_gender,
                            "event": current_event, "player": name,
                            "grade": grade, "raw": stripped
                        })
                    continue

            # Pattern 6: "FirstName LastName, Grade, Catlin Gabel" (2007 era)
            m = re.search(
                r'([A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)+),\s*(\d{1,2}),\s*Catlin[\s-]+Gabel',
                stripped
            )
            if m:
                name = m.group(1).strip()
                grade = m.group(2)
                key = (year, current_gender, current_event, name)
                if key not in seen:
                    seen.add(key)
                    qualifiers.append({
                        "year": year, "gender": current_gender,
                        "event": current_event, "player": name,
                        "grade": grade, "raw": stripped
                    })
                continue

        # 2001-2006 format: "(#N) Name - Class - Catlin Gabel" or "(N) Name, Class, Catlin Gabel"
        # Also: "Name - Class - Catlin Gabel" without seed
        # Class: Fr, So, Jr, Sr (Freshman, Sophomore, Junior, Senior)
        CLASS_MAP = {"fr": "9", "so": "10", "jr": "11", "sr": "12"}

        # Singles: "(#3) Aitor Maiz - So - Catlin Gabel" or "(2) Aitor Maiz, Jr, Catlin Gabel"
        m = re.search(
            r'(?:\(#?\d+\)\s+)?([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)+)\s*[-,]\s*(Fr|So|Jr|Sr)\s*[-,]\s*Catlin[\s-]+Gabel',
            stripped, re.IGNORECASE
        )
        if m and "/" not in m.group(0):
            name = m.group(1).strip()
            cls = m.group(2).strip().lower()
            grade = CLASS_MAP.get(cls, "")
            key = (year, current_gender, current_event, name)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": name,
                    "grade": grade, "raw": stripped
                })
            continue

        # Doubles: "(#1) Name, Class/Name, Class - Catlin Gabel" or "Name, Class/Name, Class-Catlin Gabel"
        m = re.search(
            r'(?:\(#?\d+\)\s+)?([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*),\s*(Fr|So|Jr|Sr)\s*/\s*([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*),\s*(Fr|So|Jr|Sr)\s*[-,]\s*Catlin',
            stripped, re.IGNORECASE
        )
        if m:
            name1 = m.group(1).strip()
            cls1 = m.group(2).strip().lower()
            name2 = m.group(3).strip()
            cls2 = m.group(4).strip().lower()
            player = f"{name1} / {name2}"
            grade = f"{CLASS_MAP.get(cls1, '')}/{CLASS_MAP.get(cls2, '')}"
            key = (year, current_gender, current_event, player)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": player,
                    "grade": grade, "raw": stripped
                })
            continue

        # Classic format patterns (pre-2007) - match results with "d" for defeated
        # Pattern 5 (classic doubles): "Name-Name, Catlin Gabel" (check before singles)
        m = re.search(
            r'([A-Z0-9][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*)-([A-Z0-9][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)*),\s*Catlin[\s-]+Gabel',
            stripped
        )
        if m:
            name1 = m.group(1).strip()
            name2 = m.group(2).strip()
            player = f"{name1} / {name2}"
            key = (year, current_gender, current_event, player)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": player,
                    "grade": "", "raw": stripped
                })
            continue

        # Pattern 3 (classic match result): "Name, Catlin Gabel, d Name, School"
        m = re.search(
            r'([A-Z][A-Za-z\'\-\.]+(?:\s+[A-Za-z\'\-\.]+)+),\s*Catlin[\s-]+Gabel,?\s+d\b',
            stripped
        )
        if m:
            name = m.group(1).strip()
            key = (year, current_gender, current_event, name)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": name,
                    "grade": "", "raw": stripped
                })
            continue

        # Pattern 4 (classic loss): "d Name, Catlin Gabel" or "d Name-Name, Catlin Gabel"
        m = re.search(
            r'd\s+([A-Z0-9][A-Za-z\'\-\.]+(?:[\s-]+[A-Za-z0-9\'\-\.]+)*),\s*\n?\s*Catlin[\s-]+Gabel',
            stripped
        )
        if m:
            name = m.group(1).strip()
            key = (year, current_gender, current_event, name)
            if key not in seen:
                seen.add(key)
                qualifiers.append({
                    "year": year, "gender": current_gender,
                    "event": current_event, "player": name.replace("-", " / "),
                    "grade": "", "raw": stripped
                })
            continue

    return qualifiers


def main():
    all_qualifiers = []
    team_only_years = []

    for year in CG_YEARS:
        text_path = os.path.join(TEXT_DIR, f"{year}.txt")
        if not os.path.exists(text_path):
            continue
        with open(text_path) as f:
            text = f.read()
        tennis = extract_tennis_section(text)
        qualifiers = parse_year(tennis, year)
        if qualifiers:
            all_qualifiers.extend(qualifiers)
            print(f"{year}: {len(qualifiers)} qualifier entries")
        else:
            if CG_PATTERN.search(tennis):
                team_only_years.append(year)
                print(f"{year}: Team points only")

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "gender", "event", "player", "grade", "raw"])
        writer.writeheader()
        for q in all_qualifiers:
            writer.writerow(q)

    # Write formatted text
    with open(OUTPUT_TXT, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("CATLIN GABEL SCHOOL - TENNIS STATE QUALIFIERS\n")
        f.write("Extracted from OSAA State Championship Records\n")
        f.write("=" * 70 + "\n\n")

        by_year = {}
        for q in all_qualifiers:
            by_year.setdefault(q["year"], []).append(q)

        for year in sorted(by_year.keys()):
            f.write(f"\n{'─' * 70}\n")
            f.write(f"  {year}\n")
            f.write(f"{'─' * 70}\n")
            entries = by_year[year]
            for gender in ["Boys", "Girls", "Unknown"]:
                ge = [e for e in entries if e["gender"] == gender]
                if not ge:
                    continue
                f.write(f"\n  {gender}:\n")
                for event in ["Singles", "Doubles", "Unknown"]:
                    ee = [e for e in ge if e["event"] == event]
                    if not ee:
                        continue
                    f.write(f"    {event}:\n")
                    for e in ee:
                        gr = f" (Gr. {e['grade']})" if e["grade"] else ""
                        f.write(f"      - {e['player']}{gr}\n")

        f.write(f"\n\n{'=' * 70}\n")
        f.write("YEARS WITH TEAM POINTS ONLY (no individual names in OCR):\n")
        f.write(f"  {', '.join(str(y) for y in team_only_years)}\n")
        f.write("\nNote: Catlin Gabel appeared in team standings at state but\n")
        f.write("individual player names could not be extracted from OCR.\n")
        f.write("These years need manual verification from the PDF.\n")
        f.write(f"{'=' * 70}\n")

    print(f"\nTotal: {len(all_qualifiers)} entries")
    print(f"Team-points-only years: {team_only_years}")
    print(f"\nSaved: {OUTPUT_CSV}")
    print(f"Saved: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
