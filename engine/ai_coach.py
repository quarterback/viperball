"""
AI Coach System for Viperball

Auto-assigns offense and defense styles to teams based on:
- Team roster stats (speed, kicking, lateral proficiency, defensive strength)
- Team identity (philosophy, style, tempo)
- Some randomization for variety

Used by Season Simulator and Dynasty Mode to avoid manual configuration
of every non-human team.

Also provides in-game defensive play-calling via choose_defensive_call(),
which returns a DefensivePackage with situational modifiers that affect
game-engine outcome probabilities.
"""

import random
import json
import os
from dataclasses import dataclass
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


# ──────────────────────────────────────────────────────────
# DEFENSIVE PLAY-CALLING
# ──────────────────────────────────────────────────────────

@dataclass
class DefensivePackage:
    """
    Situational defensive call with performance modifiers.

    Modifiers are multiplicative adjustments applied to offensive outcomes:
        yards_allowed_mod  : < 1.0 = defense gives up fewer yards per play
        big_play_mod       : < 1.0 = defense suppresses long gains / TDs
        fumble_forced_mod  : > 1.0 = defense creates more fumbles
        lateral_deny_mod   : < 1.0 = lateral chains less effective vs this D
        kick_block_mod     : > 1.0 = elevated chance of blocked kicks/punts
    """
    scheme: str                  # "blitz" | "coverage" | "run_stop" | "contain" | "base"
    aggression: float            # 0.0 (conservative) to 1.0 (all-out)
    viper_spy: bool              # assigns a dedicated defender to the Viper

    yards_allowed_mod: float = 1.0
    big_play_mod: float = 1.0
    fumble_forced_mod: float = 1.0
    lateral_deny_mod: float = 1.0
    kick_block_mod: float = 1.0

    def to_dict(self) -> dict:
        return {
            "scheme": self.scheme,
            "aggression": round(self.aggression, 2),
            "viper_spy": self.viper_spy,
            "yards_allowed_mod": round(self.yards_allowed_mod, 3),
            "big_play_mod": round(self.big_play_mod, 3),
            "fumble_forced_mod": round(self.fumble_forced_mod, 3),
            "lateral_deny_mod": round(self.lateral_deny_mod, 3),
            "kick_block_mod": round(self.kick_block_mod, 3),
        }


# How each defensive style responds by game situation
_DEFENSE_STYLE_TENDENCIES = {
    "pressure_defense": {
        "base_aggression": 0.80,
        "blitz_threshold": 0.35,   # blitz when behind by this fraction of current score
        "viper_spy_chance": 0.40,
        "yards_mod_range": (0.90, 1.05),
        "big_play_mod_range": (1.05, 1.20),   # gives up more big plays
        "fumble_forced_range": (1.10, 1.30),
        "lateral_deny_range": (0.88, 0.98),
        "kick_block_range": (1.05, 1.20),
    },
    "run_stop_defense": {
        "base_aggression": 0.55,
        "blitz_threshold": 0.50,
        "viper_spy_chance": 0.20,
        "yards_mod_range": (0.82, 0.95),
        "big_play_mod_range": (0.95, 1.05),
        "fumble_forced_range": (1.00, 1.12),
        "lateral_deny_range": (0.90, 1.00),
        "kick_block_range": (0.95, 1.05),
    },
    "coverage_defense": {
        "base_aggression": 0.40,
        "blitz_threshold": 0.65,
        "viper_spy_chance": 0.60,
        "yards_mod_range": (0.87, 1.00),
        "big_play_mod_range": (0.80, 0.92),   # suppresses big plays
        "fumble_forced_range": (0.95, 1.05),
        "lateral_deny_range": (0.80, 0.92),   # best at stopping lateral chains
        "kick_block_range": (0.90, 1.00),
    },
    "contain_defense": {
        "base_aggression": 0.45,
        "blitz_threshold": 0.55,
        "viper_spy_chance": 0.35,
        "yards_mod_range": (0.88, 0.97),
        "big_play_mod_range": (0.90, 1.00),
        "fumble_forced_range": (0.98, 1.08),
        "lateral_deny_range": (0.88, 0.98),
        "kick_block_range": (0.95, 1.05),
    },
    "base_defense": {
        "base_aggression": 0.50,
        "blitz_threshold": 0.50,
        "viper_spy_chance": 0.25,
        "yards_mod_range": (0.90, 1.00),
        "big_play_mod_range": (0.92, 1.02),
        "fumble_forced_range": (0.98, 1.08),
        "lateral_deny_range": (0.90, 1.00),
        "kick_block_range": (0.95, 1.05),
    },
}

_STYLE_TO_SCHEME = {
    "pressure_defense": "blitz",
    "run_stop_defense": "run_stop",
    "coverage_defense": "coverage",
    "contain_defense": "contain",
    "base_defense": "base",
}


def choose_defensive_call(
    defense_style: str,
    down: int,
    yards_to_go: int,
    field_pos: int,       # 0-100, distance from own end zone
    score_diff: int,      # defensive team's score minus offensive team's score
    time_remaining: int,  # seconds remaining in game
    rng: Optional[random.Random] = None,
) -> DefensivePackage:
    """
    Choose a situational defensive package.

    Args:
        defense_style:  one of the 5 defense styles (e.g. "pressure_defense")
        down:           current down (1-5 in Viperball)
        yards_to_go:    yards needed for new set of downs
        field_pos:      0-100 (own end zone = 0, opposing end zone = 100)
        score_diff:     defensive team score - offensive team score
        time_remaining: seconds left in game
        rng:            optional seeded Random for reproducibility

    Returns:
        DefensivePackage with situational modifiers
    """
    if rng is None:
        rng = random.Random()

    t = _DEFENSE_STYLE_TENDENCIES.get(defense_style, _DEFENSE_STYLE_TENDENCIES["base_defense"])
    scheme = _STYLE_TO_SCHEME.get(defense_style, "base")

    # Compute situational aggression
    aggression = t["base_aggression"]

    # Blitz more when losing and late in game
    if score_diff < 0 and time_remaining < 300:
        aggression = min(1.0, aggression + 0.20)
    # Back off when protecting a lead with little time
    if score_diff > 0 and time_remaining < 120:
        aggression = max(0.15, aggression - 0.20)
    # Critical downs (4th/5th) – increase aggression
    if down >= 4:
        aggression = min(1.0, aggression + 0.15)
    # Short yardage – pressure defense goes all-in
    if yards_to_go <= 4 and defense_style == "pressure_defense":
        aggression = min(1.0, aggression + 0.15)
    # Red zone (opponent inside our 25) – everyone gets more aggressive
    if field_pos >= 75:
        aggression = min(1.0, aggression + 0.10)

    # Viper spy: more likely on passing/lateral-heavy situations
    base_spy = t["viper_spy_chance"]
    if yards_to_go >= 12:
        base_spy = min(1.0, base_spy + 0.20)
    viper_spy = rng.random() < base_spy

    # Sample modifiers from ranges, skewed by aggression
    def _sample(lo: float, hi: float) -> float:
        return round(rng.uniform(lo, hi), 3)

    yards_mod = _sample(*t["yards_mod_range"])
    big_play_mod = _sample(*t["big_play_mod_range"])
    fumble_mod = _sample(*t["fumble_forced_range"])
    lateral_mod = _sample(*t["lateral_deny_range"])
    kick_block_mod = _sample(*t["kick_block_range"])

    # Blitz bonus: increases fumble forcing and kick blocking, but worsens big play risk
    if aggression > 0.7:
        fumble_mod = round(fumble_mod * (1.0 + (aggression - 0.7) * 0.3), 3)
        kick_block_mod = round(kick_block_mod * (1.0 + (aggression - 0.7) * 0.2), 3)
        big_play_mod = round(big_play_mod * (1.0 + (aggression - 0.7) * 0.2), 3)

    # If in prevent mode (protecting lead, little time), suppress big plays heavily
    if score_diff > 0 and time_remaining < 120:
        big_play_mod = min(big_play_mod, 0.80)
        lateral_mod = min(lateral_mod, 0.80)

    return DefensivePackage(
        scheme=scheme,
        aggression=round(aggression, 2),
        viper_spy=viper_spy,
        yards_allowed_mod=yards_mod,
        big_play_mod=big_play_mod,
        fumble_forced_mod=fumble_mod,
        lateral_deny_mod=lateral_mod,
        kick_block_mod=kick_block_mod,
    )


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
