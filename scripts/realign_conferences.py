#!/usr/bin/env python3
"""One-shot script to implement the full conference realignment.

Target: 200 teams, 17 conferences.
"""
import json
import os
import shutil

TEAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
CONF_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conferences.json")

# ── Target conference structure ──
# After applying BOTH the big table AND subsequent swaps:
#   Seattle→Illinois State, Belmont→UMass, Knox→Western Illinois, Bowdoin→Buffalo,
#   Caltech→Cal Poly, UC Santa Cruz→UC Davis
TARGET = {
    "ACC": [
        "boston_college", "clemson", "duke", "florida_state", "georgia_tech",
        "nc_state", "maryland", "miami", "north_carolina", "virginia",
        "virginia_tech", "wake_forest",
    ],
    "Big 12": [
        "baylor", "byu", "iowa_state", "kansas_state", "oklahoma_state",
        "tcu", "texas_tech", "ucf", "cincinnati", "houston", "kansas",
        "west_virginia",
    ],
    "Big East": [
        "creighton", "georgetown", "marquette", "providence", "syracuse",
        "louisville", "pitt", "villanova", "butler", "nyu",
    ],
    "Big Ten": [
        "indiana", "michigan_state", "northwestern", "ohio_state", "purdue",
        "illinois", "iowa", "michigan", "minnesota", "nebraska", "notre_dame",
        "wisconsin", "rutgers", "penn_state",
    ],
    "Border Conference": [
        "rice", "illinois_state", "smu", "texas_state", "tulane",
        "little_rock", "unlv", "north_texas", "utep", "ut_san_antonio",
    ],
    "Galactic League": [
        "carnegie_mellon", "davidson", "duquesne", "georgia_state", "fgcu",
        "johns_hopkins", "rhode_island", "dayton", "delaware", "north_florida",
    ],
    "Heritage League": [
        "alabama_state", "bethune_cookman", "delaware_state", "florida_am",
        "kentucky_state", "mississippi_valley_state", "jackson_state",
        "texas_southern", "grambling", "south_carolina_state", "howard",
        "hampton", "north_carolina_central",
    ],
    "Ivy League": [
        "brown", "columbia", "cornell", "dartmouth", "harvard", "penn",
        "princeton", "yale", "army", "navy",
    ],
    "Midwest States": [
        "umass", "bradley", "drake", "indiana_state", "missouri_state",
        "lafayette", "southern_illinois", "nebraska_omaha", "northern_iowa",
        "wichita_state",
    ],
    "Moonshine League": [
        "boise_state", "montana_state", "air_force", "denver", "montana",
        "northern_colorado", "uwrf", "weber_state", "south_dakota",
        "sacramento_state",
    ],
    "Mountain West": [
        "cal_poly", "colorado_state", "east_texas_am", "fresno_state",
        "loyola_marymount", "nw_missouri_state", "san_diego_state",
        "san_jose_state", "uc_davis", "san_diego", "colorado_mines",
    ],
    "Northern Shield": [
        "middlebury", "oswego", "plattsburgh", "ndsu", "sdsu",
        "boston_university", "brandeis", "holy_cross", "haverford",
        "quinnipiac", "swarthmore", "coast_guard",
    ],
    "Pac-16": [
        "arizona_state", "cal", "oregon_state", "stanford", "ucla", "usc",
        "alaska_anchorage", "arizona", "colorado", "nevada", "oregon", "utah",
        "washington", "washington_state", "idaho", "wyoming",
    ],
    "Prairie Athletic Union": [
        "ferris_state", "grand_valley_state", "greenville", "grinnell",
        "western_illinois", "lake_forest", "lawrence", "monmouth_il",
        "oberlin", "uchicago", "st_thomas", "wash_u",
    ],
    "SEC": [
        "auburn", "lsu", "mississippi_state", "texas_am", "alabama",
        "arkansas", "florida", "georgia", "kentucky", "ole_miss",
        "south_carolina", "tennessee", "texas", "oklahoma", "missouri",
        "vanderbilt",
    ],
    "West Coast Conference": [
        "gonzaga", "linfield", "portland_state", "santa_clara", "saint_marys",
        "hawaii", "portland", "san_francisco", "pacific", "southern_oregon",
        "western_washington",
    ],
    "Yankee Fourteen": [
        "ithaca", "njit", "rpi", "merchant_marine", "umbc", "buffalo",
        "colgate", "rochester", "new_hampshire", "vermont", "maine",
    ],
}

# ── New teams to create ──
# (file_id, school_name, abbreviation, mascot, city, state, colors, template_file)
NEW_TEAMS = [
    ("butler", "Butler", "BUT", "Bulldogs", "Indianapolis", "IN", ["Navy", "White"], "villanova"),
    ("ndsu", "North Dakota State", "NDSU", "Bison", "Fargo", "ND", ["Green", "Gold"], "montana_state"),
    ("sdsu", "South Dakota State", "SDSU", "Jackrabbits", "Brookings", "SD", ["Blue", "Gold"], "south_dakota"),
    ("brown", "Brown", "BRWN", "Bears", "Providence", "RI", ["Brown", "Red", "White"], "harvard"),
    ("dartmouth", "Dartmouth", "DART", "Big Green", "Hanover", "NH", ["Dartmouth Green", "White"], "harvard"),
    ("colorado_mines", "Colorado Mines", "MINES", "Orediggers", "Golden", "CO", ["Silver", "Blue"], "colorado_state"),
    ("rhode_island", "Rhode Island", "URI", "Rams", "Kingston", "RI", ["Blue", "White"], "delaware"),
    ("southern_oregon", "Southern Oregon", "SOU", "Raiders", "Ashland", "OR", ["Red", "Black"], "portland_state"),
    ("western_washington", "Western Washington", "WWU", "Vikings", "Bellingham", "WA", ["Blue", "White"], "portland_state"),
    ("maine", "Maine", "ME", "Black Bears", "Orono", "ME", ["Blue", "White"], "new_hampshire"),
    ("grambling", "Grambling", "GRAM", "Tigers", "Grambling", "LA", ["Black", "Gold"], "alabama_state"),
    ("south_carolina_state", "South Carolina State", "SCSU", "Bulldogs", "Orangeburg", "SC", ["Garnet", "Blue"], "bethune_cookman"),
    ("georgia_state", "Georgia State", "GSU", "Panthers", "Atlanta", "GA", ["Blue", "White"], "davidson"),
    ("howard", "Howard", "HOW", "Bison", "Washington", "DC", ["Blue", "White", "Red"], "delaware_state"),
    ("jackson_state", "Jackson State", "JKST", "Tigers", "Jackson", "MS", ["Blue", "White"], "alabama_state"),
    ("hampton", "Hampton", "HAMP", "Pirates", "Hampton", "VA", ["Blue", "White"], "bethune_cookman"),
    ("sacramento_state", "Sacramento State", "SACST", "Hornets", "Sacramento", "CA", ["Green", "Gold"], "fresno_state"),
    ("cal_poly", "Cal Poly", "CPOLY", "Mustangs", "San Luis Obispo", "CA", ["Green", "Gold"], "fresno_state"),
    ("uc_davis", "UC Davis", "UCD", "Aggies", "Davis", "CA", ["Blue", "Gold"], "san_jose_state"),
    ("north_carolina_central", "North Carolina Central", "NCCU", "Eagles", "Durham", "NC", ["Maroon", "Gray"], "bethune_cookman"),
    ("lafayette", "Lafayette", "LAF", "Leopards", "Easton", "PA", ["Maroon", "White"], "bradley"),
]

# ── Teams to delete ──
DELETE_TEAMS = [
    "alberta", "ubc", "calgary", "claremont_mckenna", "bryn_mawr",
    "wellesley", "space_force", "marine_corps", "xavier", "st_johns",
    "new_orleans", "seton_hall", "emory", "spelman", "lipscomb",
    "valparaiso", "caltech", "uc_santa_cruz",
    "pepperdine", "saint_louis",
]

# Build target lookup: file_id → conference
target_lookup = {}
for conf, members in TARGET.items():
    for fid in members:
        target_lookup[fid] = conf

total = sum(len(m) for m in TARGET.values())
print(f"Target: {total} teams across {len(TARGET)} conferences")

# ── Step 1: Create new team files ──
created = 0
for fid, school_name, abbrev, mascot, city, state, colors, template in NEW_TEAMS:
    target_file = os.path.join(TEAMS_DIR, f"{fid}.json")
    template_file = os.path.join(TEAMS_DIR, f"{template}.json")

    if os.path.exists(target_file):
        print(f"  EXISTS: {fid}.json (updating team_info)")
        with open(target_file) as f:
            data = json.load(f)
    else:
        print(f"  CREATE: {fid}.json from {template}.json")
        with open(template_file) as f:
            data = json.load(f)
        created += 1

    # Update team_info
    ti = data["team_info"]
    # Remove old 'school' key if present
    ti.pop("school", None)
    ti["school_id"] = fid
    ti["school_name"] = school_name
    ti["abbreviation"] = abbrev
    ti["mascot"] = mascot
    ti["conference"] = target_lookup[fid]
    ti["city"] = city
    ti["state"] = state
    ti["colors"] = colors

    with open(target_file, "w") as f:
        json.dump(data, f, indent=2)

print(f"Created {created} new team files")

# ── Step 2: Delete removed team files ──
deleted = 0
for fid in DELETE_TEAMS:
    fpath = os.path.join(TEAMS_DIR, f"{fid}.json")
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"  DELETE: {fid}.json")
        deleted += 1
    else:
        print(f"  SKIP: {fid}.json (already gone)")
print(f"Deleted {deleted} team files")

# ── Step 3: Update conference field in all remaining team files ──
updated = 0
for fid, target_conf in target_lookup.items():
    fpath = os.path.join(TEAMS_DIR, f"{fid}.json")
    if not os.path.exists(fpath):
        continue
    with open(fpath) as f:
        data = json.load(f)
    current_conf = data["team_info"].get("conference", "")
    if current_conf != target_conf:
        old = current_conf
        data["team_info"]["conference"] = target_conf
        # Also fix the conference name for Midwest States (shortened)
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  MOVE: {fid} ({old} → {target_conf})")
        updated += 1
print(f"Updated {updated} team conference assignments")

# ── Step 4: Fix Penn's school_name ──
penn_path = os.path.join(TEAMS_DIR, "penn.json")
if os.path.exists(penn_path):
    with open(penn_path) as f:
        data = json.load(f)
    if data["team_info"].get("school_name") == "Pennsylvania":
        data["team_info"]["school_name"] = "Penn"
        with open(penn_path, "w") as f:
            json.dump(data, f, indent=2)
        print("  FIX: Penn school_name Pennsylvania → Penn")

# ── Step 5: Rebuild conferences.json ──
conf_json = {}
for conf_name in sorted(TARGET.keys()):
    members = []
    for fid in sorted(TARGET[conf_name]):
        fpath = os.path.join(TEAMS_DIR, f"{fid}.json")
        if os.path.exists(fpath):
            with open(fpath) as f:
                ti = json.load(f)["team_info"]
            name = ti.get("school_name") or ti.get("school", fid)
            members.append({"id": fid, "name": name})
        else:
            print(f"  WARNING: {fid}.json missing!")
    conf_json[conf_name] = members

with open(CONF_JSON, "w") as f:
    json.dump(conf_json, f, indent=2)
print(f"\nRebuilt conferences.json with {len(conf_json)} conferences")

# ── Verify ──
total_final = sum(len(os.listdir(TEAMS_DIR)))
json_count = len([f for f in os.listdir(TEAMS_DIR) if f.endswith(".json")])
target_count = sum(len(m) for m in TARGET.values())
print(f"\nFinal: {json_count} team files, target was {target_count}")

# Check for orphans (team files not in any conference)
all_target_ids = set(target_lookup.keys())
all_file_ids = {f.replace(".json", "") for f in os.listdir(TEAMS_DIR) if f.endswith(".json")}
orphans = all_file_ids - all_target_ids
if orphans:
    print(f"ORPHAN FILES (not in any conference): {sorted(orphans)}")
missing = all_target_ids - all_file_ids
if missing:
    print(f"MISSING FILES (in target but no file): {sorted(missing)}")
