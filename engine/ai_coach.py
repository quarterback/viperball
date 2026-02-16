"""
AI Coach System for Viperball

Auto-assigns offense and defense styles to teams based on:
- Team roster stats (speed, kicking, lateral proficiency, defensive strength)
- Team identity (philosophy, style, tempo)
- Some randomization for variety

Used by Season Simulator and Dynasty Mode to avoid manual configuration
of every non-human team.
"""

import random
import json
import os
from typing import Dict, Optional, Tuple


PHILOSOPHY_TO_OFFENSE = {
    "kick_heavy": ["territorial", "balanced"],
    "lateral_heavy": ["lateral_spread", "option_spread"],
    "ground_and_pound": ["power_option", "balanced"],
    "hybrid": ["balanced", "option_spread", "power_option"],
}

IDENTITY_STYLE_TO_DEFENSE = {
    "aggressive": ["pressure_defense", "run_stop_defense"],
    "balanced": ["base_defense", "contain_defense", "coverage_defense"],
    "conservative": ["contain_defense", "coverage_defense", "base_defense"],
}


def assign_ai_scheme(team_stats: Dict, identity: Dict, seed: Optional[int] = None) -> Dict[str, str]:
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    philosophy = identity.get("philosophy", "hybrid")
    style = identity.get("style", "balanced")
    kicking = team_stats.get("kicking_strength", 70)
    lateral = team_stats.get("lateral_proficiency", 80)
    speed = team_stats.get("avg_speed", 85)
    defense = team_stats.get("defensive_strength", 76)

    offense_candidates = list(PHILOSOPHY_TO_OFFENSE.get(philosophy, ["balanced"]))

    if kicking >= 77 and "territorial" not in offense_candidates:
        offense_candidates.append("territorial")
    if lateral >= 87 and "lateral_spread" not in offense_candidates:
        offense_candidates.append("lateral_spread")
    if speed >= 87 and "option_spread" not in offense_candidates:
        offense_candidates.append("option_spread")

    weights = []
    for c in offense_candidates:
        w = 1.0
        if c == "territorial" and kicking >= 77:
            w += (kicking - 70) * 0.15
        elif c == "lateral_spread" and lateral >= 85:
            w += (lateral - 80) * 0.12
        elif c == "option_spread" and speed >= 86:
            w += (speed - 84) * 0.2
        elif c == "power_option" and defense >= 78:
            w += (defense - 75) * 0.1
        elif c == "balanced":
            w += 0.3
        weights.append(max(0.1, w))

    offense_style = rng.choices(offense_candidates, weights=weights)[0]

    defense_candidates = list(IDENTITY_STYLE_TO_DEFENSE.get(style, ["base_defense"]))

    if defense >= 80 and "run_stop_defense" not in defense_candidates:
        defense_candidates.append("run_stop_defense")
    if kicking >= 77 and "coverage_defense" not in defense_candidates:
        defense_candidates.append("coverage_defense")

    def_weights = []
    for c in defense_candidates:
        w = 1.0
        if c == "pressure_defense":
            w += max(0, speed - 85) * 0.15
        elif c == "run_stop_defense":
            w += max(0, defense - 76) * 0.2
        elif c == "coverage_defense":
            w += max(0, kicking - 72) * 0.1
        elif c == "contain_defense":
            w += 0.2
        elif c == "base_defense":
            w += 0.3
        def_weights.append(max(0.1, w))

    defense_style = rng.choices(defense_candidates, weights=def_weights)[0]

    return {"offense_style": offense_style, "defense_style": defense_style}


def get_scheme_label(offense: str, defense: str) -> str:
    offense_labels = {
        "power_option": "Ground & Pound",
        "lateral_spread": "Chain Attack",
        "territorial": "Field Position",
        "option_spread": "Speed Option",
        "balanced": "Balanced",
    }
    defense_labels = {
        "base_defense": "Base",
        "pressure_defense": "Pressure",
        "contain_defense": "Contain",
        "run_stop_defense": "Run-Stop",
        "coverage_defense": "Coverage",
    }
    off_label = offense_labels.get(offense, offense)
    def_label = defense_labels.get(defense, defense)
    return f"{off_label} / {def_label}"


def auto_assign_all_teams(
    teams_dir: str,
    human_teams: list = None,
    human_configs: Dict[str, Dict[str, str]] = None,
    seed: Optional[int] = None,
) -> Dict[str, Dict[str, str]]:
    if human_teams is None:
        human_teams = []
    if human_configs is None:
        human_configs = {}

    configs = {}
    rng_base = seed if seed is not None else random.randint(0, 999999)

    for f in sorted(os.listdir(teams_dir)):
        if not f.endswith(".json"):
            continue
        filepath = os.path.join(teams_dir, f)
        with open(filepath) as fh:
            data = json.load(fh)

        team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")

        if team_name in human_teams:
            configs[team_name] = human_configs.get(team_name, {"offense_style": "balanced", "defense_style": "base_defense"})
            continue

        team_stats = data.get("team_stats", {})
        identity = data.get("identity", {})
        team_seed = hash(team_name) + rng_base
        configs[team_name] = assign_ai_scheme(team_stats, identity, seed=team_seed)

    return configs


def load_team_identity(teams_dir: str) -> Dict[str, Dict]:
    identities = {}
    for f in sorted(os.listdir(teams_dir)):
        if not f.endswith(".json"):
            continue
        filepath = os.path.join(teams_dir, f)
        with open(filepath) as fh:
            data = json.load(fh)
        team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")
        identities[team_name] = {
            "identity": data.get("identity", {}),
            "team_stats": data.get("team_stats", {}),
            "coaching": data.get("coaching", {}),
            "conference": data["team_info"].get("conference", ""),
            "mascot": data["team_info"].get("mascot", ""),
            "colors": data["team_info"].get("colors", []),
            "city": data["team_info"].get("city", ""),
            "state": data["team_info"].get("state", ""),
        }
    return identities
