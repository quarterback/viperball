"""
Geographic Conference Assignment for Viperball

Reads canonical conference assignments from team JSON files (team_info.conference).
Falls back to geographic clustering only if teams lack conference assignments.
"""

import json
import os
from typing import Dict, List, Optional


REGION_MAP = {
    "Pacific West": ["CA", "OR", "WA", "HI", "AK"],
    "Mountain West": ["CO", "UT", "MT", "WY", "ID", "NM", "AZ", "NV"],
    "Great Plains": ["ND", "SD", "NE", "KS", "IA", "MN"],
    "Texas & South Central": ["TX", "OK", "AR", "LA"],
    "Great Lakes": ["IL", "IN", "OH", "MI", "WI"],
    "Southeast": ["NC", "SC", "TN", "KY", "VA", "WV"],
    "Deep South": ["AL", "GA", "FL", "MS"],
    "Mid-Atlantic": ["NY", "NJ", "PA", "DE"],
    "Capital Region": ["MD", "DC", "VA"],
    "New England": ["MA", "CT", "RI", "NH", "VT", "ME"],
    "Upper Midwest": ["MO", "MN", "IA", "WI"],
}

STATE_TO_BASE_REGION = {}
for region, states in REGION_MAP.items():
    for state in states:
        if state not in STATE_TO_BASE_REGION:
            STATE_TO_BASE_REGION[state] = region

REGION_MERGE_PRIORITY = [
    ("Pacific West", "Mountain West"),
    ("Great Plains", "Upper Midwest"),
    ("Deep South", "Southeast"),
    ("Capital Region", "Mid-Atlantic"),
    ("Texas & South Central", "Deep South"),
    ("Great Lakes", "Upper Midwest"),
    ("New England", "Mid-Atlantic"),
    ("Mountain West", "Great Plains"),
    ("Southeast", "Capital Region"),
]

REGION_DEFAULT_NAMES = {
    "Pacific West": "Pacific Conference",
    "Mountain West": "Mountain West Conference",
    "Great Plains": "Plains Athletic Conference",
    "Texas & South Central": "Southwest Conference",
    "Great Lakes": "Great Lakes Conference",
    "Southeast": "Southeast Conference",
    "Deep South": "Southern Athletic Conference",
    "Mid-Atlantic": "Mid-Atlantic Conference",
    "Capital Region": "Capital Conference",
    "New England": "Northeast Conference",
    "Upper Midwest": "Heartland Conference",
}


def get_team_state(team_data: dict) -> str:
    return team_data.get("team_info", {}).get("state", "")


def load_team_data(teams_dir: str) -> Dict[str, dict]:
    result = {}
    for fname in os.listdir(teams_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(teams_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
                ti = data.get("team_info", {})
                name = ti.get("school_name", fname.replace(".json", ""))
                result[name] = {
                    "state": ti.get("state", ""),
                    "conference": ti.get("conference", ""),
                    "school_id": fname.replace(".json", ""),
                }
        except (json.JSONDecodeError, KeyError):
            continue
    return result


def load_team_states(teams_dir: str) -> Dict[str, str]:
    data = load_team_data(teams_dir)
    return {name: info["state"] for name, info in data.items()}


def read_conferences_from_team_files(
    teams_dir: str, team_names: List[str]
) -> Optional[Dict[str, List[str]]]:
    team_data = load_team_data(teams_dir)

    name_to_conf = {}
    for name, info in team_data.items():
        if info["conference"]:
            name_to_conf[name] = info["conference"]

    if not name_to_conf:
        return None

    assigned = {t for t in team_names if t in name_to_conf}
    if len(assigned) < len(team_names) * 0.5:
        return None

    confs: Dict[str, List[str]] = {}
    unassigned = []
    for t in team_names:
        conf = name_to_conf.get(t, "")
        if conf:
            confs.setdefault(conf, []).append(t)
        else:
            unassigned.append(t)

    if unassigned and confs:
        smallest = min(confs, key=lambda k: len(confs[k]))
        confs[smallest].extend(unassigned)

    return confs


def cluster_teams_by_geography(
    team_names: List[str],
    team_states: Dict[str, str],
    num_conferences: int,
    min_per_conf: int = 4,
) -> Dict[str, List[str]]:
    region_teams: Dict[str, List[str]] = {}
    unassigned = []

    for tname in team_names:
        state = team_states.get(tname, "")
        region = STATE_TO_BASE_REGION.get(state)
        if region:
            region_teams.setdefault(region, []).append(tname)
        else:
            unassigned.append(tname)

    active_regions = {k: v for k, v in region_teams.items() if v}

    while len(active_regions) > num_conferences:
        smallest = min(active_regions, key=lambda k: len(active_regions[k]))
        merged = False
        for r1, r2 in REGION_MERGE_PRIORITY:
            if r1 == smallest and r2 in active_regions:
                active_regions[r2].extend(active_regions.pop(r1))
                merged = True
                break
            elif r2 == smallest and r1 in active_regions:
                active_regions[r1].extend(active_regions.pop(r2))
                merged = True
                break
        if not merged:
            other = min(
                (k for k in active_regions if k != smallest),
                key=lambda k: len(active_regions[k]),
                default=None,
            )
            if other:
                active_regions[other].extend(active_regions.pop(smallest))
            else:
                break

    while len(active_regions) < num_conferences:
        largest_key = max(active_regions, key=lambda k: len(active_regions[k]))
        largest = active_regions[largest_key]
        if len(largest) < 2 * min_per_conf:
            break
        mid = len(largest) // 2
        largest.sort()
        new_key = f"{largest_key} East" if "West" not in largest_key else f"{largest_key} II"
        active_regions[new_key] = largest[mid:]
        active_regions[largest_key] = largest[:mid]

    if unassigned:
        smallest_key = min(active_regions, key=lambda k: len(active_regions[k]))
        active_regions[smallest_key].extend(unassigned)

    result = {}
    for region_name, members in active_regions.items():
        conf_name = REGION_DEFAULT_NAMES.get(region_name, f"{region_name} Conference")
        result[conf_name] = sorted(members)

    return result


def get_geographic_conference_defaults(
    teams_dir: str,
    team_names: List[str],
    num_conferences: int,
) -> Dict[str, List[str]]:
    file_confs = read_conferences_from_team_files(teams_dir, team_names)
    if file_confs:
        return file_confs

    team_states = load_team_states(teams_dir)
    return cluster_teams_by_geography(team_names, team_states, num_conferences)
