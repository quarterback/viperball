"""
Collegiate Viperball Simulation Engine
Core game simulation logic for CVL games

V2 Architecture: Halo Model, Power Ratios, Composure, Star Designation,
Hero Ball, Fatigue Tiers, R/E/C Archetypes, Prestige-Driven Decision Matrix.
"""

import math
import random
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy


# ═══════════════════════════════════════════════════════════════
# V2 ENGINE CONFIGURATION
# Feature flags for A/B testing during migration.
# Set V2_ENGINE_CONFIG before constructing ViperballEngine to
# control which systems are active.
# ═══════════════════════════════════════════════════════════════

V2_ENGINE_CONFIG = {
    # Contest resolution: "v1_sigmoid" (legacy) or "v2_power_ratio" (spec)
    "contest_model": "v2_power_ratio",
    # Halo model: use team-level prestige halo for non-star plays
    "halo_enabled": True,
    # Fatigue tiers: Elite/Standard/Low based on talent rating
    "fatigue_tiers_enabled": True,
    # R/E/C variance archetypes: Reliable, Explosive, Clutch
    "rec_archetypes_enabled": True,
    # Star override: designated stars get performance floor
    "star_override_enabled": True,
    # Hero Ball: force-feed star players, defensive keying counter
    "hero_ball_enabled": True,
    # Composure: dynamic per-game composure with tilt/surge
    "composure_enabled": True,
    # Prestige decision matrix: prestige-driven play-calling
    "prestige_decisions_enabled": True,
    # Prestige decay: per-game asymmetric adjustments
    "prestige_decay_enabled": True,
    # Narrative generation: YAR, headlines, composure graph
    "narrative_enabled": True,
    # Power ratio exponent: tune between 1.5 (mild) and 2.0 (spec)
    "power_ratio_exponent": 1.8,
}


class VarianceArchetype(Enum):
    """R/E/C variance model — orthogonal to position archetypes.

    Every player has BOTH a position archetype (what they do: kicking_zb,
    speed_flanker, etc.) AND a variance archetype (how consistently they
    do it: Reliable, Explosive, or Clutch).
    """
    RELIABLE = "reliable"      # Clamp roll to rating ± 10
    EXPLOSIVE = "explosive"    # Full 0-100 roll range, no floor
    CLUTCH = "clutch"          # Standard variance + 15% boost in pressure


class FatigueTier(Enum):
    """Talent-based fatigue classification."""
    ELITE = "elite"        # 0.8x drain, 0.5 stat loss per fatigue point
    STANDARD = "standard"  # 1.0x drain, 1.0 stat loss per fatigue point
    LOW = "low"            # 1.5x drain, 1.5 stat loss per fatigue point


# ═══════════════════════════════════════════════════════════════
# HALO MODEL — Prestige-to-Engine Derivation Table
# Maps prestige (0-99) to team halo offense/defense ratings.
# The halo is the baseline for 90% of plays; individual player
# ratings only matter for Star-designated players at CCPs.
# ═══════════════════════════════════════════════════════════════

PRESTIGE_TO_HALO = {
    # prestige_floor: (halo_offense, halo_defense)
    # Higher prestige = higher baseline halo
    90: (88, 86),   # Elite programs
    80: (83, 81),   # Strong programs
    70: (78, 76),   # Above average
    60: (73, 72),   # Mid-tier
    50: (68, 67),   # Below average
    40: (63, 62),   # Weak
    30: (58, 57),   # Rebuilding
    20: (53, 52),   # Bottom tier
    10: (48, 47),   # Doormat
    0:  (43, 42),   # Absolute bottom
}


def derive_halo(prestige: int) -> Tuple[float, float]:
    """Derive team halo (offense, defense) from prestige rating.

    Uses linear interpolation between prestige tier breakpoints.
    Returns (halo_offense, halo_defense) as floats in 0-100 range.
    """
    prestige = max(0, min(99, prestige))

    # Find the two closest breakpoints
    tiers = sorted(PRESTIGE_TO_HALO.keys())
    lower_tier = 0
    upper_tier = tiers[-1]
    for t in tiers:
        if t <= prestige:
            lower_tier = t
        if t > prestige:
            upper_tier = t
            break
    else:
        upper_tier = lower_tier

    if lower_tier == upper_tier:
        return PRESTIGE_TO_HALO[lower_tier]

    lo_off, lo_def = PRESTIGE_TO_HALO[lower_tier]
    hi_off, hi_def = PRESTIGE_TO_HALO[upper_tier]
    frac = (prestige - lower_tier) / max(1, upper_tier - lower_tier)
    return (
        lo_off + (hi_off - lo_off) * frac,
        lo_def + (hi_def - lo_def) * frac,
    )


# ═══════════════════════════════════════════════════════════════
# COMPOSURE SYSTEM — Dynamic per-game composure
# ═══════════════════════════════════════════════════════════════

COMPOSURE_EVENTS = {
    "turnover_committed": -8,
    "turnover_forced": +5,
    "touchdown_scored": +6,
    "touchdown_allowed": -4,
    "failed_conversion": -10,
    "successful_conversion_late": +8,
    "sack": -3,
    "big_play_allowed": -5,     # 20+ yard play allowed
    "big_play_scored": +4,      # 20+ yard play scored
    "penalty_committed": -2,
    "blocked_kick": -6,
}

COMPOSURE_PREGAME = {
    "rivalry": 0.15,        # +15% variance (both teams)
    "playoff": 0.25,        # +25% variance
    "trap_game_favorite": -0.15,   # Favorite starts lower composure
    "trap_game_underdog": +0.15,   # Underdog gets composure boost
}

COMPOSURE_TILT_THRESHOLD = 70      # Below this: team is tilted
COMPOSURE_TILT_EXIT = 75           # Must recover above this to exit tilt (hysteresis)
COMPOSURE_BASE = 100               # Starting composure (range 60-140)
COMPOSURE_MIN = 60
COMPOSURE_MAX = 140



class PlayType(Enum):
    RUN = "run"
    LATERAL_CHAIN = "lateral_chain"
    KICK_PASS = "kick_pass"
    TRICK_PLAY = "trick_play"
    PUNT = "punt"
    DROP_KICK = "drop_kick"
    PLACE_KICK = "place_kick"


class PlayFamily(Enum):
    DIVE_OPTION = "dive_option"
    SPEED_OPTION = "speed_option"
    SWEEP_OPTION = "sweep_option"
    LATERAL_SPREAD = "lateral_spread"
    KICK_PASS = "kick_pass"
    TRICK_PLAY = "trick_play"
    TERRITORY_KICK = "territory_kick"
    POWER = "power"
    COUNTER = "counter"
    DRAW = "draw"
    VIPER_JET = "viper_jet"


class PlayResult(Enum):
    GAIN = "gain"
    FIRST_DOWN = "first_down"
    TOUCHDOWN = "touchdown"
    FUMBLE = "fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    SUCCESSFUL_KICK = "successful_kick"
    MISSED_KICK = "missed_kick"
    SAFETY = "safety"
    PINDOWN = "pindown"
    PUNT_RETURN_TD = "punt_return_td"
    CHAOS_RECOVERY = "chaos_recovery"
    BLOCKED_PUNT = "blocked_punt"
    MUFFED_PUNT = "muffed_punt"
    BLOCKED_KICK = "blocked_kick"
    SNAP_KICK_RECOVERY = "snap_kick_recovery"
    KICK_PASS_COMPLETE = "kick_pass_complete"
    KICK_PASS_INCOMPLETE = "kick_pass_incomplete"
    KICK_PASS_INTERCEPTED = "kick_pass_intercepted"
    INT_RETURN_TD = "int_return_td"
    LATERAL_INTERCEPTED = "lateral_intercepted"


PLAY_FAMILY_TO_TYPE = {
    PlayFamily.DIVE_OPTION: PlayType.RUN,
    PlayFamily.SPEED_OPTION: PlayType.RUN,
    PlayFamily.SWEEP_OPTION: PlayType.RUN,
    PlayFamily.POWER: PlayType.RUN,
    PlayFamily.COUNTER: PlayType.RUN,
    PlayFamily.DRAW: PlayType.RUN,
    PlayFamily.VIPER_JET: PlayType.RUN,
    PlayFamily.LATERAL_SPREAD: PlayType.LATERAL_CHAIN,
    PlayFamily.KICK_PASS: PlayType.KICK_PASS,
    PlayFamily.TRICK_PLAY: PlayType.TRICK_PLAY,
    PlayFamily.TERRITORY_KICK: PlayType.PUNT,
}

RUN_PLAY_CONFIG = {
    PlayFamily.DIVE_OPTION: {
        'base_yards': (2.0, 3.5),
        'variance': 1.2,
        'fumble_rate': 0.006,
        'primary_positions': ['HB', 'SB', 'ZB'],
        'carrier_weights': [0.45, 0.35, 0.20],
        'archetype_bonus': {'power_flanker': 1.3, 'reliable_flanker': 1.2},
        'action': 'dive',
    },
    PlayFamily.POWER: {
        'base_yards': (2.0, 3.5),
        'variance': 1.2,
        'fumble_rate': 0.007,
        'primary_positions': ['HB', 'SB'],
        'carrier_weights': [0.60, 0.40],
        'archetype_bonus': {'power_flanker': 1.4},
        'action': 'power',
    },
    PlayFamily.SWEEP_OPTION: {
        'base_yards': (2.0, 4.0),
        'variance': 1.4,
        'fumble_rate': 0.008,
        'primary_positions': ['WB', 'HB', 'SB'],
        'carrier_weights': [0.40, 0.35, 0.25],
        'archetype_bonus': {'speed_flanker': 1.4, 'elusive_flanker': 1.3},
        'action': 'sweep',
    },
    PlayFamily.SPEED_OPTION: {
        'base_yards': (2.0, 4.0),
        'variance': 1.4,
        'fumble_rate': 0.008,
        'primary_positions': ['ZB', 'WB', 'SB'],
        'carrier_weights': [0.35, 0.35, 0.30],
        'archetype_bonus': {'running_zb': 1.3, 'dual_threat_zb': 1.2},
        'action': 'pitch',
    },
    PlayFamily.COUNTER: {
        'base_yards': (2.0, 4.0),
        'variance': 1.4,
        'fumble_rate': 0.007,
        'primary_positions': ['WB', 'HB', 'VP'],
        'carrier_weights': [0.35, 0.35, 0.30],
        'archetype_bonus': {'elusive_flanker': 1.3, 'hybrid_viper': 1.2},
        'action': 'counter',
    },
    PlayFamily.DRAW: {
        'base_yards': (2.0, 3.5),
        'variance': 1.2,
        'fumble_rate': 0.007,
        'primary_positions': ['HB', 'ZB'],
        'carrier_weights': [0.55, 0.45],
        'archetype_bonus': {'running_zb': 1.2},
        'action': 'draw',
    },
    PlayFamily.VIPER_JET: {
        'base_yards': (2.5, 4.5),
        'variance': 1.5,
        'fumble_rate': 0.011,
        'primary_positions': ['VP'],
        'carrier_weights': [1.0],
        'archetype_bonus': {'receiving_viper': 1.3, 'hybrid_viper': 1.4},
        'action': 'jet',
    },
}

DEFENSE_ALIGNMENT_MAP = {
    "Swarm Defense": "spread",
    "Blitz Pack": "aggressive",
    "Shadow Defense": "balanced",
    "Fortress": "stacked",
    "Predator Defense": "aggressive",
    "Drift Defense": "spread",
    "Chaos Defense": "aggressive",
    "Lockdown": "spread",
    # Legacy mappings (backward compatibility)
    "Base Defense": "balanced",
    "Pressure Defense": "aggressive",
    "Contain Defense": "spread",
    "Run-Stop Defense": "stacked",
    "Coverage Defense": "spread",
}

PLAY_DIRECTION = {
    "dive_option": "center",
    "power": "strong",
    "sweep_option": "edge",
    "speed_option": "edge",
    "counter": "weak",
    "draw": "center",
    "viper_jet": "edge",
    "trick_play": "weak",
}

ALIGNMENT_VS_PLAY = {
    ('spread', 'dive_option'): 0.20,
    ('spread', 'power'): 0.15,
    ('spread', 'sweep_option'): -0.08,
    ('spread', 'speed_option'): -0.05,
    ('spread', 'counter'): 0.05,
    ('spread', 'draw'): 0.08,
    ('spread', 'viper_jet'): -0.03,
    ('spread', 'lateral_spread'): -0.12,
    ('stacked', 'dive_option'): -0.18,
    ('stacked', 'power'): -0.12,
    ('stacked', 'sweep_option'): 0.18,
    ('stacked', 'speed_option'): 0.12,
    ('stacked', 'counter'): 0.10,
    ('stacked', 'draw'): 0.05,
    ('stacked', 'viper_jet'): 0.15,
    ('stacked', 'lateral_spread'): 0.20,
    ('aggressive', 'dive_option'): 0.05,
    ('aggressive', 'power'): 0.05,
    ('aggressive', 'sweep_option'): 0.10,
    ('aggressive', 'speed_option'): 0.10,
    ('aggressive', 'counter'): 0.25,
    ('aggressive', 'draw'): 0.30,
    ('aggressive', 'viper_jet'): 0.10,
    ('aggressive', 'lateral_spread'): 0.05,
    ('balanced', 'dive_option'): 0.0,
    ('balanced', 'power'): 0.0,
    ('balanced', 'sweep_option'): 0.0,
    ('balanced', 'speed_option'): 0.0,
    ('balanced', 'counter'): 0.0,
    ('balanced', 'draw'): 0.0,
    ('balanced', 'viper_jet'): 0.0,
    ('balanced', 'lateral_spread'): 0.0,
    ('spread', 'trick_play'): 0.10,
    ('stacked', 'trick_play'): 0.20,
    ('aggressive', 'trick_play'): 0.15,
    ('balanced', 'trick_play'): 0.08,
}

EXPLOSIVE_CHANCE = {
    'dive_option': 0.05,
    'power': 0.06,
    'sweep_option': 0.10,
    'speed_option': 0.09,
    'counter': 0.12,
    'draw': 0.07,
    'viper_jet': 0.15,
    'lateral_spread': 0.12,
    'trick_play': 0.18,
}

VIPER_ALIGNMENT_BONUS = {
    ('left', 'right'): 0.18,
    ('right', 'left'): 0.18,
    ('left', 'center'): 0.05,
    ('right', 'center'): 0.05,
    ('center', 'left'): 0.12,
    ('center', 'right'): 0.12,
    ('left', 'left'): -0.05,
    ('right', 'right'): -0.05,
    ('center', 'center'): -0.03,
}

POSITION_TAGS = {
    "Zeroback": "ZB",
    "Viper": "VP",
    "Halfback": "HB",
    "Wingback": "WB",
    "Slotback": "SB",
    "Keeper": "KP",
    "Offensive Line": "OL",
    "Defensive Line": "DL",
}

WEATHER_CONDITIONS = {
    "clear": {
        "label": "Clear",
        "description": "Perfect conditions — no weather impact",
        "fumble_modifier": 0.0,
        "kick_accuracy_modifier": 0.0,
        "stamina_drain_modifier": 0.0,
        "muff_modifier": 0.0,
        "lateral_fumble_modifier": 0.0,
        "punt_distance_modifier": 0.0,
        "speed_modifier": 0.0,
    },
    "rain": {
        "label": "Rain",
        "description": "Wet ball, slippery field — increased fumbles and muffs, reduced kick accuracy",
        "fumble_modifier": 0.025,
        "kick_accuracy_modifier": -0.08,
        "stamina_drain_modifier": 0.10,
        "muff_modifier": 0.03,
        "lateral_fumble_modifier": 0.015,
        "punt_distance_modifier": -0.05,
        "speed_modifier": -0.03,
    },
    "snow": {
        "label": "Snow",
        "description": "Cold and slippery — major kick accuracy loss, moderate fumble increase, slower play",
        "fumble_modifier": 0.020,
        "kick_accuracy_modifier": -0.12,
        "stamina_drain_modifier": 0.15,
        "muff_modifier": 0.025,
        "lateral_fumble_modifier": 0.020,
        "punt_distance_modifier": -0.10,
        "speed_modifier": -0.05,
    },
    "sleet": {
        "label": "Sleet",
        "description": "Worst conditions — extreme fumble risk, terrible kicking, exhausting",
        "fumble_modifier": 0.035,
        "kick_accuracy_modifier": -0.15,
        "stamina_drain_modifier": 0.20,
        "muff_modifier": 0.04,
        "lateral_fumble_modifier": 0.025,
        "punt_distance_modifier": -0.12,
        "speed_modifier": -0.06,
    },
    "heat": {
        "label": "Extreme Heat",
        "description": "100°F+ — rapid stamina drain, slight fumble increase from sweaty hands",
        "fumble_modifier": 0.010,
        "kick_accuracy_modifier": -0.02,
        "stamina_drain_modifier": 0.30,
        "muff_modifier": 0.015,
        "lateral_fumble_modifier": 0.010,
        "punt_distance_modifier": 0.0,
        "speed_modifier": -0.02,
    },
    "wind": {
        "label": "Heavy Wind",
        "description": "Strong gusts — kick accuracy heavily impacted, longer punts with variance",
        "fumble_modifier": 0.005,
        "kick_accuracy_modifier": -0.10,
        "stamina_drain_modifier": 0.05,
        "muff_modifier": 0.02,
        "lateral_fumble_modifier": 0.005,
        "punt_distance_modifier": 0.08,
        "speed_modifier": -0.01,
    },
}

POSITION_ARCHETYPES = {
    "zeroback": {
        "kicking_zb": {
            "label": "Kicking ZB",
            "description": "Snapkick threat from anywhere past midfield",
            "kick_accuracy_bonus": 0.12,
            "run_yards_modifier": 0.90,
            "lateral_throw_bonus": 0.05,
            "snapkick_trigger_boost": 0.25,
            "td_rate_modifier": 0.85,
            "touches_target": (12, 16),
        },
        "running_zb": {
            "label": "Running ZB",
            "description": "Elusive runner, TD machine, forces box-stacking",
            "kick_accuracy_bonus": -0.05,
            "run_yards_modifier": 1.20,
            "lateral_throw_bonus": -0.05,
            "snapkick_trigger_boost": -0.15,
            "td_rate_modifier": 1.25,
            "touches_target": (18, 25),
        },
        "distributor_zb": {
            "label": "Distributor ZB",
            "description": "Gets playmakers the ball in space via lateral chains",
            "kick_accuracy_bonus": 0.0,
            "run_yards_modifier": 0.85,
            "lateral_throw_bonus": 0.15,
            "snapkick_trigger_boost": -0.10,
            "td_rate_modifier": 0.80,
            "touches_target": (8, 12),
        },
        "dual_threat_zb": {
            "label": "Dual-Threat ZB",
            "description": "Balanced run/kick — no clear defensive answer",
            "kick_accuracy_bonus": 0.06,
            "run_yards_modifier": 1.05,
            "lateral_throw_bonus": 0.05,
            "snapkick_trigger_boost": 0.10,
            "td_rate_modifier": 1.05,
            "touches_target": (14, 18),
        },
    },
    "viper": {
        "receiving_viper": {
            "label": "Receiving Viper",
            "description": "Chain target in space — mismatches against slower defenders",
            "yards_per_touch_modifier": 1.20,
            "chain_target_bonus": 0.20,
            "run_yards_modifier": 0.90,
            "td_rate_modifier": 1.15,
            "decoy_rate": 0.20,
        },
        "power_viper": {
            "label": "Power Viper",
            "description": "Short-yardage conversions, lead blocking battering ram",
            "yards_per_touch_modifier": 0.85,
            "chain_target_bonus": -0.10,
            "run_yards_modifier": 1.15,
            "td_rate_modifier": 1.10,
            "decoy_rate": 0.12,
            "short_yardage_bonus": 0.25,
        },
        "decoy_viper": {
            "label": "Decoy Viper",
            "description": "Draws coverage, creates space for others",
            "yards_per_touch_modifier": 1.30,
            "chain_target_bonus": -0.15,
            "run_yards_modifier": 0.85,
            "td_rate_modifier": 0.80,
            "decoy_rate": 0.55,
            "team_yards_bonus": 0.08,
        },
        "hybrid_viper": {
            "label": "Hybrid Viper",
            "description": "B+ at everything, defensive nightmare",
            "yards_per_touch_modifier": 1.05,
            "chain_target_bonus": 0.05,
            "run_yards_modifier": 1.05,
            "td_rate_modifier": 1.05,
            "decoy_rate": 0.30,
        },
    },
    "flanker": {
        "speed_flanker": {
            "label": "Speed Flanker",
            "description": "Breakaway threat on perimeter plays",
            "yards_per_touch_modifier": 1.25,
            "breakaway_bonus": 0.10,
            "fumble_modifier": 1.10,
            "td_rate_modifier": 1.15,
            "touches_target": (5, 8),
        },
        "power_flanker": {
            "label": "Power Flanker",
            "description": "Yards after contact, inside runs and chain extensions",
            "yards_per_touch_modifier": 0.90,
            "breakaway_bonus": 0.0,
            "fumble_modifier": 0.80,
            "td_rate_modifier": 1.0,
            "touches_target": (6, 10),
            "yac_bonus": 0.15,
        },
        "elusive_flanker": {
            "label": "Elusive Flanker",
            "description": "Missed tackle generator in open field",
            "yards_per_touch_modifier": 1.30,
            "breakaway_bonus": 0.08,
            "fumble_modifier": 1.15,
            "td_rate_modifier": 1.20,
            "touches_target": (5, 8),
        },
        "reliable_flanker": {
            "label": "Reliable Flanker",
            "description": "Low fumble rate, high-volume clock control",
            "yards_per_touch_modifier": 0.90,
            "breakaway_bonus": 0.0,
            "fumble_modifier": 0.60,
            "td_rate_modifier": 0.85,
            "touches_target": (8, 12),
        },
    },
    "keeper": {
        "return_keeper": {
            "label": "Return Keeper",
            "description": "Speed, open-field running — missed FGs become scoring chances",
            "return_yards_modifier": 1.30,
            "deflection_bonus": 0.0,
            "tackle_bonus": 0.0,
            "muff_rate": 0.15,
        },
        "sure_hands_keeper": {
            "label": "Sure-Hands Keeper",
            "description": "No mistakes, secures possession reliably",
            "return_yards_modifier": 0.85,
            "deflection_bonus": 0.05,
            "tackle_bonus": 0.0,
            "muff_rate": 0.03,
        },
        "tackle_keeper": {
            "label": "Tackle Keeper",
            "description": "Closing speed, last-ditch stops on breakaways",
            "return_yards_modifier": 1.0,
            "deflection_bonus": 0.08,
            "tackle_bonus": 0.15,
            "muff_rate": 0.12,
        },
    },
}


def assign_archetype(player) -> str:
    pos = player.position
    spd = player.speed
    kick = player.kicking
    lat = player.lateral_skill
    stam = player.stamina
    tck = player.tackling

    if "Zeroback" in pos:
        if kick >= 80 and kick >= spd:
            return "kicking_zb"
        elif spd >= 90 and spd > kick + 5:
            return "running_zb"
        elif lat >= 85 and lat >= spd and lat >= kick:
            return "distributor_zb"
        else:
            return "dual_threat_zb"
    elif "Viper" in pos:
        if lat >= 90 and spd >= 90:
            return "receiving_viper"
        elif tck >= 80 and stam >= 85:
            return "power_viper"
        elif spd >= 93 and lat < 85:
            return "decoy_viper"
        else:
            return "hybrid_viper"
    elif any(p in pos for p in ["Halfback", "Wingback", "Slotback"]):
        if spd >= 93:
            return "speed_flanker"
        elif tck >= 80 and stam >= 88:
            return "power_flanker"
        elif lat >= 88 and spd >= 85:
            return "elusive_flanker"
        else:
            return "reliable_flanker"
    elif "Keeper" in pos:
        if spd >= 90 and spd > tck:
            return "return_keeper"
        elif lat >= 85 and stam >= 85:
            return "sure_hands_keeper"
        else:
            return "tackle_keeper"
    return "none"


def assign_variance_archetype(player) -> str:
    """Assign R/E/C variance archetype based on player attributes.

    This is ORTHOGONAL to position archetypes.  A speed_flanker can be
    Reliable (consistent gains), Explosive (boom/bust), or Clutch
    (elevates in pressure).

    Heuristic:
    - High awareness + high stamina → Reliable (consistency)
    - High speed + low awareness → Explosive (raw athleticism, volatile)
    - High power + high awareness → Clutch (rises under pressure)
    """
    awareness = getattr(player, 'awareness', 75)
    stamina = player.stamina
    speed = player.speed
    power = getattr(player, 'power', 75)

    # Score each archetype
    reliable_score = awareness * 0.5 + stamina * 0.3 + power * 0.2
    explosive_score = speed * 0.5 + getattr(player, 'agility', 75) * 0.3 + (100 - awareness) * 0.2
    clutch_score = power * 0.3 + awareness * 0.4 + stamina * 0.3

    # Highest score wins
    scores = {
        "reliable": reliable_score,
        "explosive": explosive_score,
        "clutch": clutch_score,
    }
    return max(scores, key=scores.get)


def designate_stars(players: List, max_stars: int = 3) -> List[str]:
    """Pregame star designation — pick up to max_stars best players.

    Stars get performance floor (max(roll, rating - 10)) and are
    eligible for Hero Ball force-feeding.  Explosive players keep
    full variance even when starred.

    Returns list of player names designated as stars.
    """
    # Sort by overall descending, take top max_stars
    eligible = sorted(players, key=lambda p: p.overall, reverse=True)
    stars = []
    for p in eligible[:max_stars]:
        if p.overall >= 75:  # Minimum threshold to be a star
            p.star_designated = True
            stars.append(p.name)
    return stars


def get_archetype_info(archetype: str) -> dict:
    for category, archetypes in POSITION_ARCHETYPES.items():
        if archetype in archetypes:
            return archetypes[archetype]
    return {}


def player_tag(player) -> str:
    pos = player.position
    tag = POSITION_TAGS.get(pos, pos[:2].upper())
    return f"{tag}{player.number}"


def player_label(player) -> str:
    tag = player_tag(player)
    return f"{tag} {player.name}"


@dataclass
class GameState:
    quarter: int = 1
    time_remaining: int = 900
    home_score: float = 0.0
    away_score: float = 0.0
    possession: str = "home"
    field_position: int = 20
    down: int = 1
    yards_to_go: int = 20
    play_number: int = 0
    home_stamina: float = 100.0
    away_stamina: float = 100.0
    home_sacrifice_yards: int = 0
    away_sacrifice_yards: int = 0
    home_sacrifice_drives: int = 0
    away_sacrifice_drives: int = 0
    home_sacrifice_scores: int = 0
    away_sacrifice_scores: int = 0
    # Timeout tracking: 3 per half per team
    home_timeouts: int = 3
    away_timeouts: int = 3

    # --- V2: Composure System ---
    home_composure: float = 100.0    # Dynamic: 60-140 range
    away_composure: float = 100.0
    home_is_tilted: bool = False     # Tilt state with hysteresis
    away_is_tilted: bool = False

    # --- V2: Hero Ball tracking ---
    home_hero_ball_target: str = ""       # Player name of hero ball target
    away_hero_ball_target: str = ""
    home_consecutive_star_touches: int = 0
    away_consecutive_star_touches: int = 0

    # --- V2: Star designations (set pregame, max 3 per team) ---
    home_stars: List[str] = field(default_factory=list)
    away_stars: List[str] = field(default_factory=list)

    # --- V2: Composure timeline for post-game narrative ---
    home_composure_timeline: List[float] = field(default_factory=list)
    away_composure_timeline: List[float] = field(default_factory=list)


@dataclass
class Player:
    # --- Core identity ---
    number: int
    name: str
    position: str

    # --- Core gameplay stats (0-100) ---
    speed: int
    stamina: int
    kicking: int
    lateral_skill: int
    tackling: int

    # --- Extended gameplay attributes (0-100, default 75) ---
    agility: int = 75        # quickness / change of direction
    power: int = 75          # strength in contact situations
    awareness: int = 75      # football IQ, reading plays
    hands: int = 75          # catching, lateral security
    kick_power: int = 75     # kick distance potential
    kick_accuracy: int = 75  # kick precision

    # --- Bio (populated by generator) ---
    player_id: str = ""
    nationality: str = "American"
    hometown_city: str = ""
    hometown_state: str = ""
    hometown_country: str = "USA"
    high_school: str = ""
    height: str = "5-10"
    weight: int = 170
    year: str = "Sophomore"

    # --- Dynasty attributes ---
    potential: int = 3        # 1–5 stars
    development: str = "normal"  # normal / quick / slow / late_bloomer
    redshirt: bool = False       # if True, player doesn't advance class year this season
    redshirt_used: bool = False  # if True, player has already used their one-time redshirt
    season_games_played: int = 0 # games played this season (for redshirt eligibility)

    # --- V2: Variance archetype (R/E/C) — orthogonal to position archetype ---
    variance_archetype: str = "reliable"  # "reliable" | "explosive" | "clutch"

    # --- V2: Star designation (pregame, max 3 per team) ---
    star_designated: bool = False

    # --- Fatigue / game state ---
    current_stamina: float = 100.0
    archetype: str = "none"
    injured_in_game: bool = False     # set True if injured during this game
    is_dtd: bool = False              # day-to-day: playing through minor injury

    # --- Per-game stat counters (reset each game) ---
    game_touches: int = 0
    game_yards: int = 0
    game_rushing_yards: int = 0
    game_lateral_yards: int = 0
    game_tds: int = 0
    game_rushing_tds: int = 0
    game_fumbles: int = 0
    game_laterals_thrown: int = 0
    game_kick_attempts: int = 0
    game_kick_makes: int = 0
    game_pk_attempts: int = 0
    game_pk_makes: int = 0
    game_dk_attempts: int = 0
    game_dk_makes: int = 0
    game_kick_deflections: int = 0
    game_keeper_bells: int = 0
    game_coverage_snaps: int = 0
    game_fake_td_allowed: int = 0
    game_keeper_tackles: int = 0
    game_keeper_return_yards: int = 0
    game_lateral_receptions: int = 0
    game_lateral_assists: int = 0
    game_lateral_tds: int = 0
    game_kick_passes_thrown: int = 0
    game_kick_passes_completed: int = 0
    game_kick_pass_yards: int = 0
    game_kick_pass_tds: int = 0
    game_kick_pass_receptions: int = 0
    game_kick_pass_interceptions: int = 0
    game_lateral_interceptions: int = 0
    game_kick_returns: int = 0
    game_kick_return_yards: int = 0
    game_kick_return_tds: int = 0
    game_punt_returns: int = 0
    game_punt_return_yards: int = 0
    game_punt_return_tds: int = 0
    game_muffs: int = 0
    game_st_tackles: int = 0
    game_tackles: int = 0
    game_tfl: int = 0
    game_sacks: int = 0
    game_hurries: int = 0
    game_kick_pass_ints: int = 0
    # VPA (Viperball Points Added) attribution
    game_vpa: float = 0.0             # total VPA attributed to this player
    game_plays_involved: int = 0      # number of plays this player was involved in
    # Per-player in-game fatigue: starts at 100, drains with usage
    game_energy: float = 100.0
    # Rhythm tracking: plays since last touch (for ball hunger/cold penalty)
    plays_since_last_touch: int = 0
    # Hot streak: consecutive successful contests (positive yards or completions)
    consecutive_successes: int = 0

    @property
    def overall(self) -> int:
        """Weighted overall rating based on all core and extended attributes."""
        return int((
            self.speed * 1.2 + self.stamina * 1.0 + self.kicking * 0.8 +
            self.lateral_skill * 1.1 + self.tackling * 0.9 +
            self.agility * 1.0 + self.power * 0.8 + self.awareness * 1.1 +
            self.hands * 0.9 + self.kick_power * 0.6 + self.kick_accuracy * 0.6
        ) / 10.0)

    # ── V2: Canonical 4-stat derivation ──
    # The 6 extended stats feed into the 4 canonical ratings used by
    # power-ratio contest resolution.  Granularity preserved for
    # recruiting/development; contest resolution stays clean.

    @property
    def canon_speed(self) -> float:
        """Canonical Speed: speed (60%) + agility (40%)."""
        return self.speed * 0.6 + self.agility * 0.4

    @property
    def canon_kicking(self) -> float:
        """Canonical Kicking: kick_power (45%) + kick_accuracy (45%) + kicking (10%)."""
        return self.kick_power * 0.45 + self.kick_accuracy * 0.45 + self.kicking * 0.10

    @property
    def canon_lateral(self) -> float:
        """Canonical Lateral: lateral_skill (50%) + hands (30%) + awareness (20%)."""
        return self.lateral_skill * 0.50 + self.hands * 0.30 + self.awareness * 0.20

    @property
    def canon_tackling(self) -> float:
        """Canonical Tackling: tackling (50%) + power (25%) + awareness (25%)."""
        return self.tackling * 0.50 + self.power * 0.25 + self.awareness * 0.25

    @property
    def fatigue_tier(self) -> str:
        """Derive fatigue tier from overall talent.
        Elite (overall >= 82): 0.8x drain, 0.5 stat loss/point
        Standard (62-81): 1.0x drain, 1.0 stat loss/point
        Low (< 62): 1.5x drain, 1.5 stat loss/point
        """
        ovr = self.overall
        if ovr >= 82:
            return FatigueTier.ELITE.value
        elif ovr >= 62:
            return FatigueTier.STANDARD.value
        return FatigueTier.LOW.value

    @property
    def first_name(self) -> str:
        parts = self.name.split()
        return parts[0] if parts else self.name

    @property
    def last_name(self) -> str:
        parts = self.name.split()
        return parts[-1] if len(parts) > 1 else self.name


@dataclass
class Team:
    name: str
    abbreviation: str
    mascot: str
    players: List[Player]
    avg_speed: int
    avg_stamina: int
    kicking_strength: int
    lateral_proficiency: int
    defensive_strength: int
    offense_style: str = "balanced"
    defense_style: str = "swarm"
    st_scheme: str = "aces"
    # --- V2: Prestige and Halo ---
    prestige: int = 50               # 0-99, drives halo derivation
    halo_offense: float = 68.0       # Derived from prestige via derive_halo()
    halo_defense: float = 67.0       # Derived from prestige via derive_halo()


@dataclass
class Penalty:
    name: str
    yards: int
    on_team: str
    player: str = ""
    declined: bool = False
    phase: str = "pre_snap"

PENALTY_CATALOG = {
    "pre_snap": [
        {"name": "False Start", "yards": 5, "on": "offense", "prob": 0.014},
        {"name": "Offsides", "yards": 5, "on": "defense", "prob": 0.012},
        {"name": "Delay of Game", "yards": 5, "on": "offense", "prob": 0.005},
        {"name": "Illegal Formation", "yards": 5, "on": "offense", "prob": 0.004},
        {"name": "Encroachment", "yards": 5, "on": "defense", "prob": 0.005},
        {"name": "Too Many Men on Field", "yards": 5, "on": "either", "prob": 0.004},
        {"name": "Illegal Substitution", "yards": 5, "on": "either", "prob": 0.002},
        {"name": "Illegal Viper Alignment", "yards": 5, "on": "offense", "prob": 0.003},
    ],
    "during_play_run": [
        {"name": "Holding", "yards": 10, "on": "offense", "prob": 0.018},
        {"name": "Illegal Block", "yards": 10, "on": "offense", "prob": 0.005},
        {"name": "Clipping", "yards": 15, "on": "offense", "prob": 0.003},
        {"name": "Chop Block", "yards": 15, "on": "offense", "prob": 0.002},
        {"name": "Defensive Holding", "yards": 5, "on": "defense", "prob": 0.008, "auto_first": True},
        {"name": "Facemask", "yards": 15, "on": "defense", "prob": 0.005, "auto_first": True},
        {"name": "Unnecessary Roughness", "yards": 15, "on": "either", "prob": 0.004},
        {"name": "Horse Collar", "yards": 15, "on": "defense", "prob": 0.003, "auto_first": True},
        {"name": "Personal Foul", "yards": 15, "on": "either", "prob": 0.003},
        {"name": "Tripping", "yards": 10, "on": "either", "prob": 0.002},
    ],
    "during_play_lateral": [
        {"name": "Holding", "yards": 10, "on": "offense", "prob": 0.016},
        {"name": "Illegal Forward Lateral", "yards": 5, "on": "offense", "prob": 0.007, "loss_of_down": True},
        {"name": "Illegal Block in Back", "yards": 10, "on": "offense", "prob": 0.005},
        {"name": "Lateral Interference", "yards": 10, "on": "defense", "prob": 0.007, "auto_first": True},
        {"name": "Illegal Contact", "yards": 5, "on": "defense", "prob": 0.005, "auto_first": True},
        {"name": "Defensive Holding", "yards": 5, "on": "defense", "prob": 0.008, "auto_first": True},
        {"name": "Facemask", "yards": 15, "on": "defense", "prob": 0.004, "auto_first": True},
        {"name": "Clipping", "yards": 15, "on": "offense", "prob": 0.003},
        {"name": "Illegal Screen", "yards": 10, "on": "offense", "prob": 0.003},
        {"name": "Illegal Viper Contact", "yards": 10, "on": "defense", "prob": 0.004, "auto_first": True},
        {"name": "Unnecessary Roughness", "yards": 15, "on": "either", "prob": 0.003},
        {"name": "Personal Foul", "yards": 15, "on": "either", "prob": 0.003},
    ],
    "during_play_kick": [
        {"name": "Roughing the Kicker", "yards": 15, "on": "defense", "prob": 0.008, "auto_first": True},
        {"name": "Running Into Kicker", "yards": 5, "on": "defense", "prob": 0.010},
        {"name": "Fair Catch Interference", "yards": 15, "on": "defense", "prob": 0.004},
        {"name": "Kick Catch Interference", "yards": 15, "on": "defense", "prob": 0.003},
        {"name": "Illegal Kick", "yards": 10, "on": "offense", "prob": 0.002},
        {"name": "Holding", "yards": 10, "on": "offense", "prob": 0.010},
        {"name": "Illegal Block in Back", "yards": 10, "on": "either", "prob": 0.005},
    ],
    "post_play": [
        {"name": "Taunting", "yards": 15, "on": "either", "prob": 0.004},
        {"name": "Unsportsmanlike Conduct", "yards": 15, "on": "either", "prob": 0.003},
        {"name": "Late Hit", "yards": 15, "on": "defense", "prob": 0.004},
        {"name": "Excessive Celebration", "yards": 15, "on": "offense", "prob": 0.002},
        {"name": "Sideline Interference", "yards": 15, "on": "either", "prob": 0.001},
    ],
}


@dataclass
class Play:
    play_number: int
    quarter: int
    time: int
    possession: str
    field_position: int
    down: int
    yards_to_go: int
    play_type: str
    play_family: str
    players_involved: List[str]
    yards_gained: int
    result: str
    description: str
    fatigue: float = 100.0
    laterals: int = 0
    fumble: bool = False
    penalty: Optional[Penalty] = None
    play_signature: str = ""


OFFENSE_STYLES = {
    "ground_pound": {
        "label": "Ground & Pound",
        "description": "Grind 20 yards, punch it in. Old-school power football using all 6 downs.",
        "weights": {
            "dive_option": 0.12,
            "power": 0.11,
            "sweep_option": 0.07,
            "speed_option": 0.03,
            "counter": 0.03,
            "draw": 0.02,
            "viper_jet": 0.02,
            "lateral_spread": 0.20,
            "kick_pass": 0.30,
            "trick_play": 0.05,
            "territory_kick": 0.05,
        },
        "tempo": 0.4,
        "lateral_risk": 0.6,
        "kick_rate": 0.18,
        "option_rate": 0.55,
        "run_bonus": 0.06,
        "fatigue_resistance": 0.08,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.0,
        "run_vs_lateral": 0.70,
        "early_down_aggression": 0.70,
        "red_zone_run_pct": 0.85,
    },
    "lateral_spread": {
        "label": "Lateral Spread",
        "description": "Stretch the defense horizontally with 2-4 lateral chains. High-variance, big-play offense.",
        "weights": {
            "dive_option": 0.01,
            "power": 0.01,
            "sweep_option": 0.02,
            "speed_option": 0.02,
            "counter": 0.02,
            "draw": 0.02,
            "viper_jet": 0.02,
            "lateral_spread": 0.42,
            "kick_pass": 0.38,
            "trick_play": 0.03,
            "territory_kick": 0.05,
        },
        "tempo": 0.7,
        "lateral_risk": 1.4,
        "kick_rate": 0.22,
        "option_rate": 0.25,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.20,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.0,
        "lateral_success_bonus": 0.10,
        "tired_def_yardage_bonus": 0.05,
        "run_vs_lateral": 0.30,
        "early_down_aggression": 0.85,
        "red_zone_run_pct": 0.55,
        "kick_pass_bonus": 0.06,
    },
    "boot_raid": {
        "label": "Boot Raid",
        "description": "Air Raid with the foot. Get to the Launch Pad (opp 40-45), then fire snap kicks.",
        "weights": {
            "dive_option": 0.04,
            "power": 0.03,
            "sweep_option": 0.03,
            "speed_option": 0.02,
            "counter": 0.01,
            "draw": 0.01,
            "viper_jet": 0.02,
            "lateral_spread": 0.15,
            "kick_pass": 0.55,
            "trick_play": 0.04,
            "territory_kick": 0.10,
        },
        "weights_attack": {
            "kick_pass": 0.55,
            "territory_kick": 0.15,
            "lateral_spread": 0.15,
            "speed_option": 0.10,
            "dive_option": 0.05,
        },
        "tempo": 0.6,
        "lateral_risk": 0.9,
        "kick_rate": 0.55,
        "option_rate": 0.30,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.08,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.10,
        "snap_kick_aggression": 1.5,
        "launch_pad_threshold": 55,
        "kick_pass_bonus": 0.12,
    },
    "ball_control": {
        "label": "Ball Control",
        "description": "Conservative, mistake-free football. Take the points when available. Win 24-21.",
        "weights": {
            "dive_option": 0.12,
            "power": 0.09,
            "sweep_option": 0.07,
            "speed_option": 0.04,
            "counter": 0.02,
            "draw": 0.02,
            "viper_jet": 0.01,
            "lateral_spread": 0.18,
            "kick_pass": 0.35,
            "trick_play": 0.03,
            "territory_kick": 0.07,
        },
        "tempo": 0.3,
        "lateral_risk": 0.5,
        "kick_rate": 0.20,
        "option_rate": 0.30,
        "run_bonus": 0.04,
        "fatigue_resistance": 0.05,
        "kick_accuracy_bonus": 0.05,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.08,
        "snap_kick_aggression": 1.3,
        "run_vs_lateral": 0.75,
        "early_down_aggression": 0.50,
        "clock_burn_multiplier": 1.3,
    },
    "ghost": {
        "label": "Ghost Formation",
        "description": "Viper chaos and pre-snap confusion. The defense never knows where the playmaker is.",
        "weights": {
            "dive_option": 0.02,
            "power": 0.01,
            "sweep_option": 0.03,
            "speed_option": 0.02,
            "counter": 0.04,
            "draw": 0.02,
            "viper_jet": 0.04,
            "lateral_spread": 0.30,
            "kick_pass": 0.40,
            "trick_play": 0.07,
            "territory_kick": 0.05,
        },
        "tempo": 0.65,
        "lateral_risk": 1.1,
        "kick_rate": 0.20,
        "option_rate": 0.40,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.08,
        "option_read_bonus": 0.05,
        "broken_play_bonus": 0.10,
        "pindown_bonus": 0.0,
        "viper_touch_rate": 0.35,
        "pre_snap_motion": 0.80,
        "misdirection_bonus": 1.3,
        "kick_pass_bonus": 0.08,
    },
    "rouge_hunt": {
        "label": "Rouge Hunt",
        "description": "Defense-first offense. Punt early, pin deep, force mistakes. Score Pindowns, Bells, Safeties.",
        "weights": {
            "dive_option": 0.09,
            "power": 0.07,
            "sweep_option": 0.04,
            "speed_option": 0.03,
            "counter": 0.02,
            "draw": 0.01,
            "viper_jet": 0.01,
            "lateral_spread": 0.20,
            "kick_pass": 0.25,
            "trick_play": 0.03,
            "territory_kick": 0.25,
        },
        "tempo": 0.35,
        "lateral_risk": 0.6,
        "kick_rate": 0.50,
        "option_rate": 0.25,
        "run_bonus": 0.03,
        "fatigue_resistance": 0.05,
        "kick_accuracy_bonus": 0.05,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.20,
        "snap_kick_aggression": 1.4,
        "early_punt_threshold": 3,
        "pindown_priority": 1.5,
    },
    "chain_gang": {
        "label": "Chain Gang",
        "description": "Maximum laterals, maximum chaos. Every play is a 4-5 lateral chain. Showtime Viperball.",
        "weights": {
            "dive_option": 0.01,
            "power": 0.01,
            "sweep_option": 0.01,
            "speed_option": 0.01,
            "counter": 0.01,
            "draw": 0.01,
            "viper_jet": 0.01,
            "lateral_spread": 0.50,
            "kick_pass": 0.35,
            "trick_play": 0.03,
            "territory_kick": 0.05,
        },
        "tempo": 0.8,
        "lateral_risk": 1.6,
        "kick_rate": 0.16,
        "option_rate": 0.25,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.25,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.12,
        "pindown_bonus": 0.0,
        "lateral_success_bonus": 0.15,
        "run_vs_lateral": 0.15,
        "chain_length_preference": 4,
        "risk_tolerance": 0.90,
        "kick_pass_bonus": 0.06,
    },
    "triple_threat": {
        "label": "Triple Threat",
        "description": "Single-wing misdirection. Power Flankers take direct snaps. No one knows who has the ball.",
        "weights": {
            "dive_option": 0.04,
            "power": 0.05,
            "sweep_option": 0.04,
            "speed_option": 0.04,
            "counter": 0.04,
            "draw": 0.04,
            "viper_jet": 0.03,
            "lateral_spread": 0.25,
            "kick_pass": 0.35,
            "trick_play": 0.07,
            "territory_kick": 0.05,
        },
        "tempo": 0.45,
        "lateral_risk": 0.7,
        "kick_rate": 0.20,
        "option_rate": 0.45,
        "run_bonus": 0.03,
        "fatigue_resistance": 0.04,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.05,
        "broken_play_bonus": 0.05,
        "pindown_bonus": 0.0,
        "direct_snap_rate": 0.25,
        "misdirection_bonus": 1.2,
    },
    "balanced": {
        "label": "Balanced",
        "description": "No strong tendency, adapts to situation. Multiple threats, adaptable gameplan.",
        "weights": {
            "dive_option": 0.04,
            "speed_option": 0.03,
            "sweep_option": 0.03,
            "power": 0.04,
            "counter": 0.04,
            "draw": 0.04,
            "viper_jet": 0.03,
            "lateral_spread": 0.25,
            "kick_pass": 0.40,
            "trick_play": 0.05,
            "territory_kick": 0.05,
        },
        "tempo": 0.5,
        "lateral_risk": 1.0,
        "kick_rate": 0.35,
        "option_rate": 0.40,
        "run_bonus": 0.03,
        "fatigue_resistance": 0.025,
        "kick_accuracy_bonus": 0.05,
        "explosive_lateral_bonus": 0.05,
        "option_read_bonus": 0.05,
        "broken_play_bonus": 0.05,
        "pindown_bonus": 0.05,
        "snap_kick_aggression": 1.1,
    },
}

STYLE_MIGRATION = {
    "power_option": "ground_pound",
    "territorial": "boot_raid",
    "option_spread": "ghost",
}

# Migration map: old 5 defense styles → new 8 schemes
DEFENSE_STYLE_MIGRATION = {
    "base_defense": "swarm",
    "pressure_defense": "blitz_pack",
    "contain_defense": "shadow",
    "run_stop_defense": "fortress",
    "coverage_defense": "lockdown",
}

# ========================================
# OFFENSE vs DEFENSE MATCHUP MATRIX
# ========================================
# Each entry is a multiplier applied to overall defensive effectiveness.
# < 1.0 = defense has advantage (reduces offensive output)
# > 1.0 = offense has advantage (boosts offensive output)
# 1.0 = neutral matchup
#
# This creates rock/paper/scissors dynamics — no single defense is best,
# and a smart DC can exploit an opponent's offensive tendencies.
OFFENSE_VS_DEFENSE_MATCHUP = {
    # Swarm crushes lateral-heavy offenses but kick pass carves its zones
    ("ground_pound", "swarm"): 0.95,
    ("lateral_spread", "swarm"): 0.82,
    ("boot_raid", "swarm"): 1.12,
    ("ball_control", "swarm"): 0.98,
    ("ghost", "swarm"): 0.90,
    ("rouge_hunt", "swarm"): 1.00,
    ("chain_gang", "swarm"): 0.78,
    ("triple_threat", "swarm"): 0.92,
    ("balanced", "swarm"): 0.95,
    # Blitz Pack pressures everything but counters/draws exploit vacated gaps
    ("ground_pound", "blitz_pack"): 0.88,
    ("lateral_spread", "blitz_pack"): 1.08,
    ("boot_raid", "blitz_pack"): 0.90,
    ("ball_control", "blitz_pack"): 0.85,
    ("ghost", "blitz_pack"): 1.15,
    ("rouge_hunt", "blitz_pack"): 0.92,
    ("chain_gang", "blitz_pack"): 1.10,
    ("triple_threat", "blitz_pack"): 1.12,
    ("balanced", "blitz_pack"): 1.00,
    # Shadow shuts down viper-based schemes but power run eats it alive
    ("ground_pound", "shadow"): 1.12,
    ("lateral_spread", "shadow"): 0.90,
    ("boot_raid", "shadow"): 0.95,
    ("ball_control", "shadow"): 1.08,
    ("ghost", "shadow"): 0.80,
    ("rouge_hunt", "shadow"): 1.00,
    ("chain_gang", "shadow"): 0.88,
    ("triple_threat", "shadow"): 0.85,
    ("balanced", "shadow"): 0.98,
    # Fortress walls off the run game but lateral/kick pass go around
    ("ground_pound", "fortress"): 0.78,
    ("lateral_spread", "fortress"): 1.15,
    ("boot_raid", "fortress"): 1.18,
    ("ball_control", "fortress"): 0.82,
    ("ghost", "fortress"): 1.05,
    ("rouge_hunt", "fortress"): 0.95,
    ("chain_gang", "fortress"): 1.20,
    ("triple_threat", "fortress"): 0.95,
    ("balanced", "fortress"): 1.02,
    # Predator gambles — great vs predictable offenses, burned by chaos
    ("ground_pound", "predator"): 0.90,
    ("lateral_spread", "predator"): 0.95,
    ("boot_raid", "predator"): 0.88,
    ("ball_control", "predator"): 0.85,
    ("ghost", "predator"): 1.10,
    ("rouge_hunt", "predator"): 0.92,
    ("chain_gang", "predator"): 1.05,
    ("triple_threat", "predator"): 1.08,
    ("balanced", "predator"): 0.95,
    # Drift bends but doesn't break — dies to patient ball control
    ("ground_pound", "drift"): 1.05,
    ("lateral_spread", "drift"): 0.92,
    ("boot_raid", "drift"): 0.88,
    ("ball_control", "drift"): 1.15,
    ("ghost", "drift"): 0.95,
    ("rouge_hunt", "drift"): 0.85,
    ("chain_gang", "drift"): 0.90,
    ("triple_threat", "drift"): 1.00,
    ("balanced", "drift"): 0.98,
    # Chaos wrecks predictable teams, but experienced/balanced offenses adapt
    ("ground_pound", "chaos"): 0.88,
    ("lateral_spread", "chaos"): 0.95,
    ("boot_raid", "chaos"): 0.90,
    ("ball_control", "chaos"): 0.92,
    ("ghost", "chaos"): 1.05,
    ("rouge_hunt", "chaos"): 0.90,
    ("chain_gang", "chaos"): 0.98,
    ("triple_threat", "chaos"): 1.00,
    ("balanced", "chaos"): 1.08,
    # Lockdown denies kick pass but ground game bulldozes the light box
    ("ground_pound", "lockdown"): 1.15,
    ("lateral_spread", "lockdown"): 0.92,
    ("boot_raid", "lockdown"): 0.80,
    ("ball_control", "lockdown"): 1.10,
    ("ghost", "lockdown"): 0.95,
    ("rouge_hunt", "lockdown"): 0.88,
    ("chain_gang", "lockdown"): 0.90,
    ("triple_threat", "lockdown"): 1.05,
    ("balanced", "lockdown"): 0.95,
}

# ========================================
# DEFENSIVE ARCHETYPES
# ========================================
# Each defensive style modifies play outcomes through:
# - Run yardage multipliers
# - Lateral success rates
# - Fumble probability
# - Explosive play suppression
# - Kick accuracy effects
# - Turnover generation

DEFENSE_STYLES = {
    # ================================================================
    # SWARM DEFENSE — Tampa 2 analog
    # Everyone flows to the ball. Zone responsibility, rally to contact.
    # Elite vs laterals (multiple defenders converge on each handoff).
    # Vulnerable to kick pass down the seam (gaps between zone drops).
    # ================================================================
    "swarm": {
        "label": "Swarm Defense",
        "description": "Zone-based rally defense. Everyone flows to the ball — elite vs laterals, vulnerable to kick pass seams.",
        "play_family_modifiers": {
            "dive_option": 0.88,
            "speed_option": 0.85,
            "sweep_option": 0.82,
            "power": 0.90,
            "counter": 0.80,
            "draw": 0.90,
            "viper_jet": 0.78,
            "lateral_spread": 0.55,
            "kick_pass": 1.15,
            "trick_play": 0.75,
            "territory_kick": 0.95,
        },
        "read_success_rate": 0.40,
        "pressure_factor": 0.35,
        "turnover_bonus": 0.15,
        "explosive_suppression": 0.70,
        "kick_suppression": 0.95,
        "kick_pass_coverage": 0.06,
        "pindown_defense": 0.95,
        "fatigue_resistance": 0.06,
        "gap_breakdown_bonus": 0.02,
        "gameplan_bias": {
            "dive_option": 0.03,
            "speed_option": 0.05,
            "sweep_option": 0.05,
            "power": 0.03,
            "counter": 0.06,
            "draw": 0.03,
            "viper_jet": 0.08,
            "lateral_spread": 0.12,
            "kick_pass": 0.02,
            "trick_play": 0.08,
            "territory_kick": 0.03,
        },
        "personnel_weights": {
            "tackling": 0.30, "speed": 0.30, "awareness": 0.25, "agility": 0.15,
        },
        "situational": {
            "red_zone_read_boost": 0.10,
            "short_yardage_modifier": 0.90,
            "long_yardage_modifier": 1.10,
            "trailing_aggression": 0.05,
            "leading_conserve": 0.08,
        },
    },

    # ================================================================
    # BLITZ PACK — 46 Defense analog
    # Relentless pressure. Send extra rushers on every play.
    # Great at TFLs and forcing fumbles in the backfield.
    # Burned by counters, draws, and trick plays that exploit vacated gaps.
    # ================================================================
    "blitz_pack": {
        "label": "Blitz Pack",
        "description": "Relentless pressure — extra rushers every play. Elite TFLs, but counters and draws carve empty gaps.",
        "play_family_modifiers": {
            "dive_option": 0.80,
            "speed_option": 0.70,
            "sweep_option": 0.78,
            "power": 0.75,
            "counter": 1.20,
            "draw": 1.25,
            "viper_jet": 0.72,
            "lateral_spread": 1.15,
            "kick_pass": 0.82,
            "trick_play": 1.20,
            "territory_kick": 0.90,
        },
        "read_success_rate": 0.45,
        "pressure_factor": 1.10,
        "turnover_bonus": 0.30,
        "explosive_suppression": 1.15,
        "kick_suppression": 1.05,
        "kick_pass_coverage": 0.04,
        "pindown_defense": 0.90,
        "fatigue_resistance": -0.06,
        "gap_breakdown_bonus": 0.08,
        "gameplan_bias": {
            "dive_option": 0.06,
            "speed_option": 0.10,
            "sweep_option": 0.06,
            "power": 0.06,
            "counter": 0.02,
            "draw": 0.01,
            "viper_jet": 0.08,
            "lateral_spread": 0.08,
            "kick_pass": 0.05,
            "trick_play": 0.02,
            "territory_kick": 0.00,
        },
        "personnel_weights": {
            "speed": 0.35, "tackling": 0.30, "power": 0.25, "agility": 0.10,
        },
        "situational": {
            "red_zone_read_boost": 0.08,
            "short_yardage_modifier": 0.80,
            "long_yardage_modifier": 1.20,
            "trailing_aggression": 0.12,
            "leading_conserve": 0.00,
        },
    },

    # ================================================================
    # SHADOW DEFENSE — Spy / Mirror analog
    # Assigns a defender to shadow the Viper at all times.
    # Shuts down viper_jet and ghost-style misdirection.
    # Vulnerable to straight-ahead power run game (one less box defender).
    # ================================================================
    "shadow": {
        "label": "Shadow Defense",
        "description": "Assigns a defender to mirror the Viper. Shuts down jet sweeps and ghost schemes, but power runs exploit the undermanned box.",
        "play_family_modifiers": {
            "dive_option": 1.10,
            "speed_option": 0.85,
            "sweep_option": 0.95,
            "power": 1.12,
            "counter": 0.80,
            "draw": 1.00,
            "viper_jet": 0.55,
            "lateral_spread": 0.85,
            "kick_pass": 0.90,
            "trick_play": 0.65,
            "territory_kick": 1.00,
        },
        "read_success_rate": 0.42,
        "pressure_factor": 0.40,
        "turnover_bonus": 0.18,
        "explosive_suppression": 0.72,
        "kick_suppression": 0.95,
        "kick_pass_coverage": 0.12,
        "pindown_defense": 1.00,
        "fatigue_resistance": 0.02,
        "gap_breakdown_bonus": 0.03,
        "gameplan_bias": {
            "dive_option": 0.02,
            "speed_option": 0.05,
            "sweep_option": 0.03,
            "power": 0.02,
            "counter": 0.06,
            "draw": 0.03,
            "viper_jet": 0.15,
            "lateral_spread": 0.06,
            "kick_pass": 0.05,
            "trick_play": 0.10,
            "territory_kick": 0.02,
        },
        "personnel_weights": {
            "awareness": 0.35, "speed": 0.30, "agility": 0.20, "tackling": 0.15,
        },
        "situational": {
            "red_zone_read_boost": 0.06,
            "short_yardage_modifier": 1.08,
            "long_yardage_modifier": 0.92,
            "trailing_aggression": 0.04,
            "leading_conserve": 0.06,
        },
    },

    # ================================================================
    # FORTRESS — Goal Line / Box-Stacking analog
    # Loads the box with bodies. Dominates inside runs and short yardage.
    # Gets carved by kick pass and laterals that stretch outside.
    # ================================================================
    "fortress": {
        "label": "Fortress",
        "description": "Stack the box, own the line of scrimmage. Dominates inside runs — but kick pass and laterals stretch the vacated edges.",
        "play_family_modifiers": {
            "dive_option": 0.58,
            "speed_option": 0.72,
            "sweep_option": 0.68,
            "power": 0.62,
            "counter": 0.75,
            "draw": 0.78,
            "viper_jet": 0.80,
            "lateral_spread": 1.18,
            "kick_pass": 1.20,
            "trick_play": 1.25,
            "territory_kick": 1.00,
        },
        "read_success_rate": 0.45,
        "pressure_factor": 0.35,
        "turnover_bonus": 0.12,
        "explosive_suppression": 0.75,
        "kick_suppression": 1.00,
        "kick_pass_coverage": 0.03,
        "pindown_defense": 1.00,
        "fatigue_resistance": 0.03,
        "gap_breakdown_bonus": 0.10,
        "gameplan_bias": {
            "dive_option": 0.12,
            "speed_option": 0.10,
            "sweep_option": 0.10,
            "power": 0.10,
            "counter": 0.06,
            "draw": 0.05,
            "viper_jet": 0.05,
            "lateral_spread": 0.00,
            "kick_pass": 0.00,
            "trick_play": 0.00,
            "territory_kick": 0.00,
        },
        "personnel_weights": {
            "tackling": 0.35, "power": 0.30, "awareness": 0.20, "speed": 0.15,
        },
        "situational": {
            "red_zone_read_boost": 0.12,
            "short_yardage_modifier": 0.70,
            "long_yardage_modifier": 1.25,
            "trailing_aggression": 0.02,
            "leading_conserve": 0.10,
        },
    },

    # ================================================================
    # PREDATOR — Aggressive man coverage / Turnover-hunting analog
    # Gambles for interceptions on kick pass. Creates turnovers constantly.
    # High risk: when the gamble fails, gives up explosives.
    # ================================================================
    "predator": {
        "label": "Predator Defense",
        "description": "Gamble for turnovers — jump kick pass routes, force fumbles. When you guess right, it's a takeaway. When wrong, it's a touchdown.",
        "play_family_modifiers": {
            "dive_option": 0.92,
            "speed_option": 0.88,
            "sweep_option": 0.90,
            "power": 0.95,
            "counter": 1.08,
            "draw": 1.05,
            "viper_jet": 0.85,
            "lateral_spread": 0.92,
            "kick_pass": 0.78,
            "trick_play": 0.80,
            "territory_kick": 0.92,
        },
        "read_success_rate": 0.48,
        "pressure_factor": 0.60,
        "turnover_bonus": 0.35,
        "explosive_suppression": 1.20,
        "kick_suppression": 0.88,
        "kick_pass_coverage": 0.20,
        "pindown_defense": 0.90,
        "fatigue_resistance": 0.00,
        "gap_breakdown_bonus": 0.04,
        "gameplan_bias": {
            "dive_option": 0.04,
            "speed_option": 0.06,
            "sweep_option": 0.04,
            "power": 0.03,
            "counter": 0.03,
            "draw": 0.03,
            "viper_jet": 0.06,
            "lateral_spread": 0.06,
            "kick_pass": 0.10,
            "trick_play": 0.08,
            "territory_kick": 0.05,
        },
        "personnel_weights": {
            "awareness": 0.35, "speed": 0.25, "hands": 0.25, "agility": 0.15,
        },
        "situational": {
            "red_zone_read_boost": 0.05,
            "short_yardage_modifier": 0.95,
            "long_yardage_modifier": 0.90,
            "trailing_aggression": 0.10,
            "leading_conserve": 0.05,
        },
    },

    # ================================================================
    # DRIFT — Cover 3 / Soft Zone analog
    # Prevent explosives at all costs. Bend but don't break.
    # Gives up short yardage consistently — death by a thousand cuts.
    # ================================================================
    "drift": {
        "label": "Drift Defense",
        "description": "Soft zone — bend don't break. Prevents explosives and big plays, but gives up 4-5 yards on every carry. Death by paper cuts.",
        "play_family_modifiers": {
            "dive_option": 1.05,
            "speed_option": 1.00,
            "sweep_option": 1.02,
            "power": 1.05,
            "counter": 1.00,
            "draw": 1.00,
            "viper_jet": 0.95,
            "lateral_spread": 0.88,
            "kick_pass": 0.82,
            "trick_play": 0.90,
            "territory_kick": 0.90,
        },
        "read_success_rate": 0.38,
        "pressure_factor": 0.20,
        "turnover_bonus": 0.08,
        "explosive_suppression": 0.55,
        "kick_suppression": 0.90,
        "kick_pass_coverage": 0.14,
        "pindown_defense": 0.85,
        "fatigue_resistance": 0.08,
        "gap_breakdown_bonus": 0.02,
        "gameplan_bias": {
            "dive_option": 0.02,
            "speed_option": 0.02,
            "sweep_option": 0.02,
            "power": 0.02,
            "counter": 0.03,
            "draw": 0.03,
            "viper_jet": 0.04,
            "lateral_spread": 0.05,
            "kick_pass": 0.06,
            "trick_play": 0.04,
            "territory_kick": 0.05,
        },
        "personnel_weights": {
            "awareness": 0.30, "tackling": 0.25, "speed": 0.25, "agility": 0.20,
        },
        "situational": {
            "red_zone_read_boost": 0.08,
            "short_yardage_modifier": 1.10,
            "long_yardage_modifier": 0.80,
            "trailing_aggression": 0.00,
            "leading_conserve": 0.12,
        },
    },

    # ================================================================
    # CHAOS DEFENSE — Go-Go / Disguise analog
    # Stunts, line shifts, pre-snap disguises every play.
    # Messes up the offense's blocking assignments and pre-snap reads.
    # High variance: sometimes dominates, sometimes gives up huge plays.
    # ================================================================
    "chaos": {
        "label": "Chaos Defense",
        "description": "Stunts, disguises, and line shifts every snap. Wrecks blocking assignments — but when the offense adjusts, it's wide open.",
        "play_family_modifiers": {
            "dive_option": 0.82,
            "speed_option": 0.80,
            "sweep_option": 0.78,
            "power": 0.85,
            "counter": 0.88,
            "draw": 1.10,
            "viper_jet": 0.80,
            "lateral_spread": 0.90,
            "kick_pass": 0.90,
            "trick_play": 0.85,
            "territory_kick": 1.00,
        },
        "read_success_rate": 0.42,
        "pressure_factor": 0.70,
        "turnover_bonus": 0.22,
        "explosive_suppression": 1.10,
        "kick_suppression": 1.00,
        "kick_pass_coverage": 0.08,
        "pindown_defense": 0.95,
        "fatigue_resistance": -0.03,
        "gap_breakdown_bonus": 0.06,
        "gameplan_bias": {
            "dive_option": 0.05,
            "speed_option": 0.06,
            "sweep_option": 0.06,
            "power": 0.05,
            "counter": 0.04,
            "draw": 0.02,
            "viper_jet": 0.06,
            "lateral_spread": 0.06,
            "kick_pass": 0.05,
            "trick_play": 0.06,
            "territory_kick": 0.03,
        },
        "personnel_weights": {
            "agility": 0.30, "speed": 0.30, "awareness": 0.25, "tackling": 0.15,
        },
        "situational": {
            "red_zone_read_boost": 0.06,
            "short_yardage_modifier": 0.85,
            "long_yardage_modifier": 1.05,
            "trailing_aggression": 0.15,
            "leading_conserve": 0.00,
        },
    },

    # ================================================================
    # LOCKDOWN — Shutdown Coverage analog
    # Best kick pass defense in the game. Blankets receivers, denies completions.
    # Worst vs power run game — light boxes get bulldozed.
    # Forces the offense to grind on the ground.
    # ================================================================
    "lockdown": {
        "label": "Lockdown",
        "description": "Shutdown kick pass coverage — blankets receivers and denies completions. Forces you to grind on the ground through heavy boxes.",
        "play_family_modifiers": {
            "dive_option": 1.10,
            "speed_option": 1.05,
            "sweep_option": 1.05,
            "power": 1.15,
            "counter": 1.08,
            "draw": 1.05,
            "viper_jet": 0.88,
            "lateral_spread": 0.85,
            "kick_pass": 0.60,
            "trick_play": 0.85,
            "territory_kick": 0.82,
        },
        "read_success_rate": 0.38,
        "pressure_factor": 0.30,
        "turnover_bonus": 0.22,
        "explosive_suppression": 0.78,
        "kick_suppression": 0.80,
        "kick_pass_coverage": 0.22,
        "pindown_defense": 0.80,
        "fatigue_resistance": 0.04,
        "gap_breakdown_bonus": 0.02,
        "gameplan_bias": {
            "dive_option": 0.00,
            "speed_option": 0.00,
            "sweep_option": 0.00,
            "power": 0.00,
            "counter": 0.02,
            "draw": 0.02,
            "viper_jet": 0.04,
            "lateral_spread": 0.04,
            "kick_pass": 0.12,
            "trick_play": 0.04,
            "territory_kick": 0.08,
        },
        "personnel_weights": {
            "awareness": 0.30, "speed": 0.30, "hands": 0.20, "tackling": 0.20,
        },
        "situational": {
            "red_zone_read_boost": 0.10,
            "short_yardage_modifier": 1.12,
            "long_yardage_modifier": 0.85,
            "trailing_aggression": 0.02,
            "leading_conserve": 0.10,
        },
    },
}

# ========================================
# SPECIAL TEAMS CHAOS PROBABILITIES
# ========================================
# Base probabilities for blocked/muffed kicks
# These are modulated by offensive and defensive styles

BASE_BLOCK_PUNT = 0.03   # 3% base chance of blocked punt
BASE_BLOCK_KICK = 0.04   # 4% base chance of blocked FG/snapkick
BASE_MUFF_PUNT = 0.05    # 5% base chance of muffed punt return

# Offensive style modifiers for blocks (lower = better special teams)
OFFENSE_BLOCK_MODIFIERS = {
    "boot_raid": 0.8,
    "ball_control": 0.85,
    "rouge_hunt": 0.85,
    "balanced": 1.0,
    "triple_threat": 1.05,
    "ground_pound": 1.1,
    "ghost": 1.15,
    "lateral_spread": 1.2,
    "chain_gang": 1.2,
}

# Defensive style modifiers for blocks/muffs (higher = better special teams pressure)
DEFENSE_BLOCK_MODIFIERS = {
    "blitz_pack": 1.5,         # Elite at blocking kicks — extra rushers
    "chaos": 1.3,              # Stunts create confusion on kick protection
    "predator": 1.2,           # Aggressive — gets after kicks
    "fortress": 1.1,           # Big bodies push the pocket
    "swarm": 1.0,              # Average
    "shadow": 1.0,             # Average
    "drift": 0.9,              # Soft zone = less rush
    "lockdown": 0.8,           # Drops back, doesn't rush kicks
    # Legacy (backward compatibility)
    "pressure_defense": 1.5,
    "coverage_defense": 1.0,
    "contain_defense": 1.0,
    "run_stop_defense": 1.0,
    "base_defense": 1.0,
}

DEFENSE_MUFF_MODIFIERS = {
    "lockdown": 1.35,          # Best coverage = best gunners on punt team
    "predator": 1.25,          # Aggressive coverage, forces mistakes
    "swarm": 1.15,             # Flows to ball — good special teams
    "chaos": 1.10,             # Unpredictable coverage
    "blitz_pack": 1.05,        # Aggressive
    "shadow": 1.00,            # Average
    "drift": 0.95,             # Soft coverage, less pressure on returner
    "fortress": 0.90,          # Slow to get downfield
    # Legacy (backward compatibility)
    "coverage_defense": 1.3,
    "pressure_defense": 1.1,
    "contain_defense": 1.0,
    "run_stop_defense": 1.0,
    "base_defense": 1.0,
}

# ── Special Teams Schemes ────────────────────────────────────────────────
# The third strategic dimension. Offense → Defense → Special Teams.
# Each team selects an ST philosophy that governs coverage, returns,
# kick blocking, and trick-play tendencies on punts and kicks.

ST_SCHEMES = {
    "iron_curtain": {
        "label": "Iron Curtain",
        "description": "Elite coverage unit. Best gunners force muffs and pin returners. "
                       "Your own return game is conservative — secure the ball, take the field position.",
        "coverage_modifier": 1.35,       # Opponents get far fewer return yards
        "muff_bonus": 1.30,              # Gunners force muffs
        "return_yards_modifier": 0.70,   # Your returns are short, safe
        "return_td_modifier": 0.50,      # Rarely break one
        "block_rush_modifier": 0.90,     # Don't rush kicks much
        "fake_play_rate": 0.01,          # Almost never fake
        "returner_muff_rate": 0.80,      # Your returner rarely muffs (safe hands focus)
    },
    "lightning_returns": {
        "label": "Lightning Returns",
        "description": "Built around explosive returners. Keeper and Viper get maximum return touches. "
                       "Accept thin coverage for game-breaking return yardage.",
        "coverage_modifier": 0.80,       # Opponents get more return yards
        "muff_bonus": 0.85,              # Less pressure on returners
        "return_yards_modifier": 1.40,   # Your returns go further
        "return_td_modifier": 1.60,      # Much higher return TD chance
        "block_rush_modifier": 0.90,     # Normal
        "fake_play_rate": 0.02,          # Occasional fake
        "returner_muff_rate": 1.10,      # Slightly higher muff risk (aggressive catches)
    },
    "block_party": {
        "label": "Block Party",
        "description": "Rush the kicker every time. Highest block rate in the game. "
                       "But the coverage behind is thin — if the kick gets off, you're exposed.",
        "coverage_modifier": 0.70,       # Worst coverage — everyone rushed
        "muff_bonus": 0.75,              # No gunners downfield
        "return_yards_modifier": 1.00,   # Normal returns
        "return_td_modifier": 1.00,      # Normal
        "block_rush_modifier": 1.50,     # Elite block rate
        "fake_play_rate": 0.01,          # Disciplined
        "returner_muff_rate": 1.00,      # Normal
    },
    "chaos_unit": {
        "label": "Chaos Unit",
        "description": "Fake punts, trick returns, surprise plays. The opponent never knows what's coming. "
                       "High variance — sometimes genius, sometimes disaster.",
        "coverage_modifier": 1.00,       # Normal coverage
        "muff_bonus": 1.05,              # Slight confusion factor
        "return_yards_modifier": 1.15,   # Slightly better (creative returns)
        "return_td_modifier": 1.25,      # Better (trick return schemes)
        "block_rush_modifier": 1.15,     # Some rush disguises
        "fake_play_rate": 0.12,          # 12% of punts are fakes!
        "returner_muff_rate": 1.15,      # More aggressive = more risk
    },
    "aces": {
        "label": "Aces",
        "description": "Well-rounded special teams. Slight bonus across the board, no weakness. "
                       "The safe pick for teams without a special teams identity.",
        "coverage_modifier": 1.10,       # Slightly better coverage
        "muff_bonus": 1.10,              # Slightly better gunners
        "return_yards_modifier": 1.10,   # Slightly better returns
        "return_td_modifier": 1.10,      # Slightly better
        "block_rush_modifier": 1.10,     # Slightly better
        "fake_play_rate": 0.03,          # Occasional fake
        "returner_muff_rate": 0.95,      # Slightly safer
    },
}

ST_SCHEME_MIGRATION = {
    "base": "aces",
}


class ViperballEngine:

    RIVALRY_UNDERDOG_BOOST = {
        10: 2,
        20: 5,
        30: 7,
        999: 9,
    }

    def __init__(self, home_team: Team, away_team: Team, seed: Optional[int] = None,
                 style_overrides: Optional[Dict[str, str]] = None,
                 weather: str = "clear",
                 is_rivalry: bool = False,
                 neutral_site: bool = False,
                 injury_tracker=None,
                 game_week: int = 1,
                 unavailable_home: Optional[set] = None,
                 unavailable_away: Optional[set] = None,
                 dtd_home: Optional[set] = None,
                 dtd_away: Optional[set] = None,
                 home_dq_boosts: Optional[Dict] = None,
                 away_dq_boosts: Optional[Dict] = None,
                 home_coaching: Optional[Dict] = None,
                 away_coaching: Optional[Dict] = None,
                 # V2: Prestige and game context
                 home_prestige: int = 50,
                 away_prestige: int = 50,
                 is_playoff: bool = False,
                 is_trap_game: bool = False):
        self.home_team = deepcopy(home_team)
        self.away_team = deepcopy(away_team)
        self.is_rivalry = is_rivalry
        self.neutral_site = neutral_site
        self.home_dq_boosts = home_dq_boosts or {}
        self.away_dq_boosts = away_dq_boosts or {}
        self.state = GameState()
        self.play_log: List[Play] = []
        self.drive_log: List[Dict] = []
        self.viper_position = "free"
        self.seed = seed
        self.drive_play_count = 0
        self._drive_chain_positive = 0  # Consecutive positive-yard plays this drive
        self._current_drive_sacrifice = False
        self.weather = weather if weather in WEATHER_CONDITIONS else "clear"
        self.weather_info = WEATHER_CONDITIONS[self.weather]

        # --- Injury / substitution state ---
        self.injury_tracker = injury_tracker
        self.game_week = game_week
        self.in_game_injuries: List = []       # InGameInjuryEvent objects
        self._home_injured_in_game: set = set()
        self._away_injured_in_game: set = set()

        # Filter out unavailable players (weekly injuries) and mark DTD
        _unavailable_home = unavailable_home or set()
        _unavailable_away = unavailable_away or set()
        _dtd_home = dtd_home or set()
        _dtd_away = dtd_away or set()

        if _unavailable_home:
            self.home_team.players = [p for p in self.home_team.players
                                      if p.name not in _unavailable_home]
        if _unavailable_away:
            self.away_team.players = [p for p in self.away_team.players
                                      if p.name not in _unavailable_away]
        for p in self.home_team.players:
            if p.name in _dtd_home:
                p.is_dtd = True
        for p in self.away_team.players:
            if p.name in _dtd_away:
                p.is_dtd = True

        for p in self.home_team.players:
            p.archetype = assign_archetype(p)
        for p in self.away_team.players:
            p.archetype = assign_archetype(p)

        # ── V2: Assign variance archetypes (R/E/C) ──
        if V2_ENGINE_CONFIG.get("rec_archetypes_enabled", False):
            for p in self.home_team.players:
                p.variance_archetype = assign_variance_archetype(p)
            for p in self.away_team.players:
                p.variance_archetype = assign_variance_archetype(p)

        # ── V2: Wire prestige into engine ──
        self.home_team.prestige = home_prestige
        self.away_team.prestige = away_prestige
        self._is_playoff = is_playoff
        self._is_trap_game = is_trap_game

        # ── V2: Derive halo from prestige ──
        if V2_ENGINE_CONFIG.get("halo_enabled", False):
            h_off, h_def = derive_halo(home_prestige)
            self.home_team.halo_offense = h_off
            self.home_team.halo_defense = h_def
            a_off, a_def = derive_halo(away_prestige)
            self.away_team.halo_offense = a_off
            self.away_team.halo_defense = a_def

        # ── V2: Pregame star designation (max 3 per team) ──
        if V2_ENGINE_CONFIG.get("star_override_enabled", False):
            self.state.home_stars = designate_stars(self.home_team.players, max_stars=3)
            self.state.away_stars = designate_stars(self.away_team.players, max_stars=3)

        if seed is not None:
            random.seed(seed)

        if style_overrides:
            for team_key, style in style_overrides.items():
                # Check if this is a defense style override (e.g., "gonzaga_defense")
                is_defense = "_defense" in team_key.lower() or "_def" in team_key.lower()
                base_key = team_key.lower().replace("_defense", "").replace("_def", "")

                if is_defense and style in DEFENSE_STYLES:
                    # Apply defensive style
                    if base_key in [self.home_team.name.lower(), self.home_team.abbreviation.lower()]:
                        self.home_team.defense_style = style
                    elif base_key in [self.away_team.name.lower(), self.away_team.abbreviation.lower()]:
                        self.away_team.defense_style = style
                    else:
                        for t in [self.home_team, self.away_team]:
                            clean_key = base_key.replace(" ", "_").replace("-", "_")
                            clean_name = t.name.lower().replace(" ", "_").replace("-", "_")
                            if clean_key in clean_name or clean_name in clean_key:
                                t.defense_style = style
                                break
                elif "_st" in team_key.lower() and style in ST_SCHEMES:
                    # Apply special teams scheme (e.g., "gonzaga_st")
                    st_base = base_key.replace("_st", "")
                    if st_base in [self.home_team.name.lower(), self.home_team.abbreviation.lower()]:
                        self.home_team.st_scheme = style
                    elif st_base in [self.away_team.name.lower(), self.away_team.abbreviation.lower()]:
                        self.away_team.st_scheme = style
                    else:
                        for t in [self.home_team, self.away_team]:
                            clean_key = st_base.replace(" ", "_").replace("-", "_")
                            clean_name = t.name.lower().replace(" ", "_").replace("-", "_")
                            if clean_key in clean_name or clean_name in clean_key:
                                t.st_scheme = style
                                break
                elif style in OFFENSE_STYLES:
                    # Apply offensive style (existing logic)
                    if team_key.lower() in [self.home_team.name.lower(), self.home_team.abbreviation.lower()]:
                        self.home_team.offense_style = style
                    elif team_key.lower() in [self.away_team.name.lower(), self.away_team.abbreviation.lower()]:
                        self.away_team.offense_style = style
                    else:
                        for t in [self.home_team, self.away_team]:
                            clean_key = team_key.lower().replace(" ", "_").replace("-", "_")
                            clean_name = t.name.lower().replace(" ", "_").replace("-", "_")
                            if clean_key in clean_name or clean_name in clean_key:
                                t.offense_style = style
                                break

        home_off = STYLE_MIGRATION.get(self.home_team.offense_style, self.home_team.offense_style)
        away_off = STYLE_MIGRATION.get(self.away_team.offense_style, self.away_team.offense_style)
        self.home_team.offense_style = home_off
        self.away_team.offense_style = away_off
        self.home_style = OFFENSE_STYLES.get(home_off, OFFENSE_STYLES["balanced"])
        self.away_style = OFFENSE_STYLES.get(away_off, OFFENSE_STYLES["balanced"])
        # Migrate old defense style names to new scheme names
        home_def = DEFENSE_STYLE_MIGRATION.get(self.home_team.defense_style, self.home_team.defense_style)
        away_def = DEFENSE_STYLE_MIGRATION.get(self.away_team.defense_style, self.away_team.defense_style)
        self.home_team.defense_style = home_def
        self.away_team.defense_style = away_def
        self.home_defense = DEFENSE_STYLES.get(home_def, DEFENSE_STYLES["swarm"])
        self.away_defense = DEFENSE_STYLES.get(away_def, DEFENSE_STYLES["swarm"])
        # Migrate and load special teams schemes
        home_st = ST_SCHEME_MIGRATION.get(self.home_team.st_scheme, self.home_team.st_scheme)
        away_st = ST_SCHEME_MIGRATION.get(self.away_team.st_scheme, self.away_team.st_scheme)
        self.home_team.st_scheme = home_st
        self.away_team.st_scheme = away_st
        self.home_st = ST_SCHEMES.get(home_st, ST_SCHEMES["aces"])
        self.away_st = ST_SCHEMES.get(away_st, ST_SCHEMES["aces"])

        # ── Coaching staff modifiers (must init before rhythm) ──
        self.home_coaching_mods: Dict = {}
        self.away_coaching_mods: Dict = {}
        if home_coaching or away_coaching:
            from engine.coaching import compute_gameday_modifiers
            if home_coaching:
                self.home_coaching_mods = compute_gameday_modifiers(home_coaching)
            if away_coaching:
                self.away_coaching_mods = compute_gameday_modifiers(away_coaching)

        self.home_game_rhythm = random.gauss(1.0, 0.15)
        self.away_game_rhythm = random.gauss(1.0, 0.15)
        self.home_game_rhythm = max(0.65, min(1.35, self.home_game_rhythm))
        self.away_game_rhythm = max(0.65, min(1.35, self.away_game_rhythm))
        self.home_def_intensity = random.gauss(1.0, 0.12)
        self.away_def_intensity = random.gauss(1.0, 0.12)
        self.home_def_intensity = max(0.70, min(1.30, self.home_def_intensity))
        self.away_def_intensity = max(0.70, min(1.30, self.away_def_intensity))

        # Coaching: leadership narrows rhythm variance toward 1.0 (prevents bad games)
        home_lead = self.home_coaching_mods.get("leadership_factor", 0.0)
        away_lead = self.away_coaching_mods.get("leadership_factor", 0.0)
        if home_lead > 0:
            self.home_game_rhythm = 1.0 + (self.home_game_rhythm - 1.0) * (1.0 - home_lead * 0.3)
        if away_lead > 0:
            self.away_game_rhythm = 1.0 + (self.away_game_rhythm - 1.0) * (1.0 - away_lead * 0.3)

        self._home_halftime_score = 0
        self._away_halftime_score = 0

        for side_label, mods in [("home", self.home_coaching_mods), ("away", self.away_coaching_mods)]:
            if mods.get("hc_classification") == "motivator":
                cls_fx = mods.get("classification_effects", {})
                comp_amp = cls_fx.get("composure_amplification", 1.0)
                if comp_amp > 1.0:
                    if side_label == "home":
                        self.home_game_rhythm = 1.0 + (self.home_game_rhythm - 1.0) / comp_amp
                    else:
                        self.away_game_rhythm = 1.0 + (self.away_game_rhythm - 1.0) / comp_amp

        for side_label, mods in [("home", self.home_coaching_mods), ("away", self.away_coaching_mods)]:
            if mods.get("hc_classification") == "players_coach":
                cls_fx = mods.get("classification_effects", {})
                chem = cls_fx.get("chemistry_bonus_per_game", 0.0)
                if chem > 0:
                    cumulative = chem * self.game_week
                    if side_label == "home":
                        self.home_game_rhythm = min(1.35, self.home_game_rhythm + cumulative)
                    else:
                        self.away_game_rhythm = min(1.35, self.away_game_rhythm + cumulative)

        self._home_momentum_plays = 0
        self._away_momentum_plays = 0

        if not self.neutral_site:
            self._apply_home_field_boost()

        if self.is_rivalry:
            self._apply_rivalry_boost()

        self._apply_dq_boosts()

    def _coaching_mods(self) -> Dict:
        """Return coaching modifiers for the team currently on offense."""
        if self.state.possession == "home":
            return self.home_coaching_mods
        return self.away_coaching_mods

    def _def_coaching_mods(self) -> Dict:
        """Return coaching modifiers for the team currently on defense."""
        if self.state.possession == "home":
            return self.away_coaching_mods
        return self.home_coaching_mods

    def _apply_dq_boosts(self):
        for boosts, team in [(self.home_dq_boosts, self.home_team),
                             (self.away_dq_boosts, self.away_team)]:
            if not boosts:
                continue
            dev_boost = boosts.get("development", 0)
            facilities_boost = boosts.get("facilities", 0)
            combined = int((dev_boost + facilities_boost) / 4)
            if combined > 0:
                for p in team.players:
                    p.awareness = min(99, p.awareness + min(combined, 3))
                    p.stamina = min(99, p.stamina + min(combined, 2))

    def _apply_home_field_boost(self):
        """Temporary ratings boost for the home team.

        Represents crowd energy, field familiarity, comfort of home.
        Inverse scaling: lower-rated players get a bigger boost.
        A 45-rated player gets +6, a 75→+3, 85+→+1.
        This helps bad/average teams playing at home compete.
        """
        for p in self.home_team.players:
            for attr in ('speed', 'power', 'stamina', 'awareness', 'agility', 'tackling'):
                val = getattr(p, attr, 60)
                # Inverse scale: lower ratings get bigger boosts, 85+ gets +1
                boost = max(1, min(6, 6 - (val - 40) // 10))
                setattr(p, attr, min(99, val + boost))

    def _apply_rivalry_boost(self):
        home_avg = sum(p.overall for p in self.home_team.players) / max(1, len(self.home_team.players))
        away_avg = sum(p.overall for p in self.away_team.players) / max(1, len(self.away_team.players))
        gap = abs(home_avg - away_avg)

        underdog_boost = 2
        for threshold, boost in sorted(self.RIVALRY_UNDERDOG_BOOST.items()):
            if gap <= threshold:
                underdog_boost = boost
                break

        intensity_boost = 2
        underdog_team = self.away_team if home_avg > away_avg else self.home_team
        favorite_team = self.home_team if home_avg > away_avg else self.away_team

        for p in favorite_team.players:
            p.speed = min(99, p.speed + intensity_boost)
            p.stamina = min(99, p.stamina + intensity_boost)
            p.awareness = min(99, p.awareness + intensity_boost)

        total_boost = intensity_boost + underdog_boost
        for p in underdog_team.players:
            p.speed = min(99, p.speed + total_boost)
            p.stamina = min(99, p.stamina + total_boost)
            p.awareness = min(99, p.awareness + total_boost)
            p.tackling = min(99, p.tackling + intensity_boost)

    def _offense_skill(self, team):
        """Return offensive skill-position players (ball carriers, receivers)."""
        skill = [p for p in team.players if p.position in
                 ("Zeroback", "Halfback", "Wingback", "Slotback", "Viper")]
        return skill if skill else team.players[:8]

    def _offense_all(self, team):
        """Return all offensive players including OL."""
        off = [p for p in team.players if p.position not in ("Defensive Line", "Keeper")]
        return off if off else team.players[:8]

    def _defense_players(self, team):
        """Return defensive players (Keepers and DL)."""
        defs = [p for p in team.players if p.position in ("Keeper", "Defensive Line")]
        return defs if defs else team.players[:5]

    def _kicker_candidates(self, team):
        """Return best kicker candidates: ZBs first, then VPs, then SBs."""
        zbs = [p for p in team.players if p.position == "Zeroback"]
        if zbs:
            return zbs
        vps = [p for p in team.players if p.position == "Viper"]
        if vps:
            return vps
        sbs = [p for p in team.players if p.position == "Slotback"]
        if sbs:
            return sbs
        return self._offense_skill(team)

    def simulate_game(self) -> Dict:
        # V2: Apply pregame composure modifiers
        self._apply_pregame_composure()

        self.kickoff("away")

        for quarter in range(1, 5):
            self.state.quarter = quarter
            self.state.time_remaining = 900

            if quarter == 3:
                self._apply_halftime_coaching_adjustments()
                self.recover_energy_halftime()
                # Reset timeouts for second half
                self.state.home_timeouts = 3
                self.state.away_timeouts = 3

            while self.state.time_remaining > 0:
                self.simulate_drive()
                if self.state.time_remaining <= 0:
                    break
                # V2: Underdog surge check each drive
                self._check_underdog_surge()

            if quarter == 2:
                self._home_halftime_score = self.state.home_score
                self._away_halftime_score = self.state.away_score

        return self.generate_game_summary()

    def _apply_halftime_coaching_adjustments(self):
        for side in ("home", "away"):
            mods = self.home_coaching_mods if side == "home" else self.away_coaching_mods
            cls = mods.get("hc_classification", "")
            cls_fx = mods.get("classification_effects", {})

            # V2.2: Personality modifiers for halftime adjustments
            pf = mods.get("personality_factors", {})
            sub_fx = mods.get("sub_archetype_effects", {})
            adapt_f = pf.get("adaptability", 1.0)
            stub_f = pf.get("stubbornness", 1.0)

            if cls == "gameday_manager":
                adj = cls_fx.get("halftime_adjustment_bonus", 0.0)
                # V2.2: Adaptability + adjuster sub-archetype scale halftime adjustment
                adj *= adapt_f * (2.0 - stub_f) * sub_fx.get("halftime_adjustment_multiplier", 1.0)
                if adj > 0:
                    if side == "home":
                        self.home_game_rhythm = 1.0 + (self.home_game_rhythm - 1.0) * (1.0 - adj)
                    else:
                        self.away_game_rhythm = 1.0 + (self.away_game_rhythm - 1.0) * (1.0 - adj)

            if cls == "motivator":
                boost = cls_fx.get("trailing_halftime_boost", 0.0)
                # V2.2: Firestarter sub-archetype amplifies trailing boost
                boost *= sub_fx.get("trailing_halftime_boost_multiplier", 1.0)
                if boost > 0:
                    my_half = self._home_halftime_score if side == "home" else self._away_halftime_score
                    opp_half = self._away_halftime_score if side == "home" else self._home_halftime_score
                    if my_half < opp_half:
                        if side == "home":
                            self.home_game_rhythm = min(1.35, self.home_game_rhythm + boost)
                        else:
                            self.away_game_rhythm = min(1.35, self.away_game_rhythm + boost)

    def _check_rouge_pindown(self, receiving_team_obj, kicking_possession: str) -> bool:
        return_speed = receiving_team_obj.avg_speed
        pindown_bonus = self._current_style().get("pindown_bonus", 0.0)
        receiving_defense = self.away_defense if kicking_possession == "home" else self.home_defense
        pindown_defense_factor = receiving_defense.get("pindown_defense", 1.0)
        return_chance = (return_speed / 200) * (1.0 - pindown_bonus) / pindown_defense_factor
        return_chance = max(0.0, return_chance)
        can_return_out = random.random() < return_chance
        return not can_return_out

    def _apply_rouge_pindown(self, kicking_possession: str, receiving_possession: str):
        self.state.possession = kicking_possession
        self.add_score(1)
        self.state.possession = receiving_possession
        self.state.field_position = 25
        self.state.down = 1
        self.state.yards_to_go = 20

    def kickoff(self, receiving_team: str):
        """Dynamic field position system — no traditional kickoff.

        Possession alternates, but starting field position is based on
        score differential: start at the 20 +/- however many points you
        lead or trail. Clamped to the 1 yard line minimum.

        Down 14 → start at 34. Up 21 → start at 1. Tied → start at 20.
        """
        self.state.possession = receiving_team

        # Calculate score differential from receiving team's perspective
        if receiving_team == "home":
            their_score = self.state.home_score
            opp_score = self.state.away_score
        else:
            their_score = self.state.away_score
            opp_score = self.state.home_score

        point_differential = their_score - opp_score  # positive = leading
        start_position = max(1, int(20 - point_differential))

        # Track sacrifice yards — the penalty for leading
        # Sacrifice = how many yards behind the 20 you start (positive when leading)
        sacrifice = 20 - start_position  # positive = gave up yards, negative = got bonus yards
        if receiving_team == "home":
            self.state.home_sacrifice_yards += sacrifice
            if sacrifice > 0:
                self.state.home_sacrifice_drives += 1
        else:
            self.state.away_sacrifice_yards += sacrifice
            if sacrifice > 0:
                self.state.away_sacrifice_drives += 1

        # Flag for the upcoming drive — did it start under sacrifice?
        self._current_drive_sacrifice = sacrifice > 0

        self.state.field_position = start_position
        self.state.down = 1
        self.state.yards_to_go = 20

    def simulate_drive(self):
        style = self._current_style()
        tempo = style["tempo"]
        max_plays = int(20 + tempo * 15)
        self.drive_play_count = 0
        self._drive_chain_positive = 0

        if self.state.possession == "home" and self._home_momentum_plays > 0:
            self.home_game_rhythm = min(1.35, self.home_game_rhythm + 0.04 * self._home_momentum_plays)
            self._home_momentum_plays = 0
        elif self.state.possession == "away" and self._away_momentum_plays > 0:
            self.away_game_rhythm = min(1.35, self.away_game_rhythm + 0.04 * self._away_momentum_plays)
            self._away_momentum_plays = 0

        drive_team = self.state.possession
        drive_start = self.state.field_position
        drive_quarter = self.state.quarter
        drive_sacrifice = self._current_drive_sacrifice
        self._current_drive_sacrifice = False  # Reset for next drive
        drive_plays = 0
        drive_yards = 0
        drive_result = "stall"

        # Between-drive recovery: players get a brief rest
        self.recover_energy_between_drives()

        while self.drive_play_count < max_plays and self.state.time_remaining > 0:
            self.drive_play_count += 1
            play = self.simulate_play()
            self.play_log.append(play)
            drive_plays += 1
            if play.yards_gained > 0 and play.play_type not in ["punt"]:
                drive_yards += play.yards_gained
                self._drive_chain_positive += 1
            else:
                self._drive_chain_positive = 0

            # Play clock: tempo-driven pace differentiation
            # Ball Control/Rouge Hunt grind ~140-160 plays/game
            # Balanced teams play ~170-180 plays/game
            # Chain Gang/Lateral Spread sprint ~210-220 plays/game
            base_time = random.randint(14, 30)
            tempo_mult = 1.40 - tempo * 0.75

            # ── Two-minute drill clock management ──
            is_two_min = (self.state.quarter in (2, 4) and
                          self.state.time_remaining < 120)
            if is_two_min:
                score_diff = self._get_score_diff()
                if score_diff < 0:
                    # Trailing: hurry-up, cut clock to 1/3
                    tempo_mult *= 0.33
                elif score_diff > 0:
                    # Leading: burn clock at full speed
                    tempo_mult *= 1.2

            time_elapsed = int(base_time * tempo_mult)
            self.state.time_remaining = max(0, self.state.time_remaining - time_elapsed)

            # Coaching AI considers calling a timeout after this play
            if self.call_timeout():
                # Timeout called — clock stops (no additional time drain)
                pass

            # Increment plays_since_last_touch for all non-involved players
            team_on_off = self.get_offensive_team()
            involved_names = set(play.players_involved) if play.players_involved else set()
            for p in team_on_off.players:
                if player_label(p) not in involved_names:
                    p.plays_since_last_touch += 1

            if play.result == "snap_kick_recovery":
                drive_result = "snap_kick_recovery"
                continue

            if play.result in ["touchdown", "turnover_on_downs", "fumble", "successful_kick", "missed_kick", "punt", "pindown", "punt_return_td", "int_return_td", "chaos_recovery", "safety", "lateral_intercepted", "kick_pass_intercepted"]:
                drive_result = play.result

                # ── V2: Composure events ──
                off_team = drive_team
                def_team_side = "away" if drive_team == "home" else "home"
                if play.result == "touchdown":
                    self._adjust_composure(off_team, "touchdown_scored")
                    self._adjust_composure(def_team_side, "touchdown_allowed")
                elif play.result in ("fumble", "lateral_intercepted", "kick_pass_intercepted"):
                    self._adjust_composure(off_team, "turnover_committed")
                    self._adjust_composure(def_team_side, "turnover_forced")
                elif play.result == "turnover_on_downs":
                    self._adjust_composure(off_team, "failed_conversion")
                elif play.result in ("punt_return_td", "int_return_td"):
                    self._adjust_composure(def_team_side, "touchdown_scored")
                    self._adjust_composure(off_team, "touchdown_allowed")
                elif play.result == "successful_kick":
                    self._adjust_composure(off_team, "successful_conversion_late")

                # Big play tracking (20+ yards)
                if play.yards_gained >= 20:
                    self._adjust_composure(off_team, "big_play_scored")
                    self._adjust_composure(def_team_side, "big_play_allowed")

                # ── V2: Hero ball tracking ──
                if play.players_involved:
                    primary_player = play.players_involved[0] if play.players_involved else ""
                    is_success = play.result in ("touchdown", "first_down", "gain", "successful_kick") and play.yards_gained > 0
                    # Extract player name from label (e.g. "ZB6 Jane Smith" -> "Jane Smith")
                    parts = primary_player.split(" ", 1)
                    pname = parts[1] if len(parts) > 1 else primary_player
                    self._update_hero_ball(off_team, pname, is_success)

                if play.result in ("fumble", "turnover_on_downs"):
                    new_pos = self.state.possession
                    new_mods = self.home_coaching_mods if new_pos == "home" else self.away_coaching_mods
                    if new_mods.get("hc_classification") == "motivator":
                        mom_plays = int(new_mods.get("classification_effects", {}).get("momentum_recovery_plays", 0))
                        if new_pos == "home":
                            self._home_momentum_plays = mom_plays
                        else:
                            self._away_momentum_plays = mom_plays
                if play.result == "touchdown":
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "successful_kick":
                    kicking_team = self.state.possession
                    receiving = "away" if kicking_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "punt_return_td":
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "int_return_td":
                    # Pick-six: intercepting team scored, kickoff to other team
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "safety":
                    scored_team = "away" if drive_team == "home" else "home"
                    self.state.possession = drive_team
                    self.state.field_position = 20
                    self.state.down = 1
                    self.state.yards_to_go = 20
                break

        # Track compelled efficiency: did a sacrifice drive end in a score?
        is_score = drive_result in ("touchdown", "successful_kick", "punt_return_td", "int_return_td")
        if drive_sacrifice and is_score:
            if drive_team == "home":
                self.state.home_sacrifice_scores += 1
            else:
                self.state.away_sacrifice_scores += 1

        self.drive_log.append({
            "team": drive_team,
            "quarter": drive_quarter,
            "start_yard_line": drive_start,
            "plays": drive_plays,
            "yards": drive_yards,
            "result": drive_result,
            "sacrifice_drive": drive_sacrifice,
        })

    FIELD_POSITION_VALUE = [
        (10, 0.3), (20, 0.6), (35, 1.0), (50, 1.5),
        (65, 2.2), (80, 3.0), (90, 4.5), (100, 6.5),
    ]

    CONVERSION_RATES = {
        4: {3: 0.88, 6: 0.76, 10: 0.62, 15: 0.48, 20: 0.38},
        5: {3: 0.84, 6: 0.72, 10: 0.58, 15: 0.44, 20: 0.34},
        6: {3: 0.80, 6: 0.68, 10: 0.52, 15: 0.40, 20: 0.30},
    }

    def _fp_value(self, fp: int) -> float:
        for threshold, val in self.FIELD_POSITION_VALUE:
            if fp <= threshold:
                return val
        return 6.5

    def _conversion_rate(self, down: int, ytg: int) -> float:
        rates = self.CONVERSION_RATES.get(down, self.CONVERSION_RATES[6])
        if ytg <= 3:
            rate = rates[3]
        elif ytg <= 6:
            rate = rates[6]
        elif ytg <= 10:
            rate = rates[10]
        elif ytg <= 15:
            rate = rates[15]
        else:
            rate = rates[20]

        off_mods = self._coaching_mods()
        if off_mods.get("hc_classification") == "gameday_manager":
            cls_fx = off_mods.get("classification_effects", {})
            rate += cls_fx.get("fourth_down_accuracy", 0.0)
            rate = min(0.95, rate)

        return rate

    def _place_kick_success(self, distance: int, kicker_skill: int = 75) -> float:
        """Field goal accuracy — kicker-range model.

        In a sport that evolved around kicking (no forward pass), kickers
        are far more developed than NFL kickers.  50-yard FGs are routine.
        60-70 yarders are competitive.  The kicker's skill determines
        their COMFORTABLE RANGE — within it, makes are near-automatic.
        Beyond it, success drops off steeply.

        60-skill → comfortable to ~45 yards
        75-skill → comfortable to ~58 yards
        85-skill → comfortable to ~67 yards
        95-skill → comfortable to ~76 yards
        """
        comfortable_range = 45 + (kicker_skill - 60) * 0.9

        if distance <= 20:
            return 0.99  # Chip shot
        elif distance <= comfortable_range:
            frac = (distance - 20) / max(1, comfortable_range - 20)
            return 0.98 - frac * 0.10  # 0.98 close → 0.88 at edge
        elif distance <= comfortable_range + 10:
            over = distance - comfortable_range
            return max(0.10, 0.85 - over * 0.05)
        elif distance <= comfortable_range + 20:
            over = distance - comfortable_range - 10
            return max(0.05, 0.30 - over * 0.02)
        else:
            return max(0.03, 0.08 - (distance - comfortable_range - 20) * 0.01)

    def _drop_kick_success(self, distance: int, kicker_skill: int) -> float:
        """Drop kick accuracy — kicker-range model.

        Drop kicks are worth 5 points (vs 3 for FGs) and have recovery
        potential on misses.  Harder than a place kick — the ball must
        bounce off the ground first — so the comfortable range is
        shorter, but the payoff is bigger.

        60-skill → comfortable to ~30 yards
        75-skill → comfortable to ~41 yards
        85-skill → comfortable to ~49 yards
        95-skill → comfortable to ~56 yards
        """
        comfortable_range = 30 + (kicker_skill - 60) * 0.75

        if distance <= 15:
            return 0.98  # Point-blank
        elif distance <= comfortable_range:
            frac = (distance - 15) / max(1, comfortable_range - 15)
            return 0.96 - frac * 0.10  # 0.96 close → 0.86 at edge
        elif distance <= comfortable_range + 10:
            over = distance - comfortable_range
            return max(0.08, 0.80 - over * 0.06)
        elif distance <= comfortable_range + 15:
            over = distance - comfortable_range - 10
            return max(0.05, 0.20 - over * 0.02)
        else:
            return max(0.03, 0.06 - (distance - comfortable_range - 15) * 0.01)

    POSSESSION_VALUE = 3.0

    GO_FOR_IT_MATRIX = {
        # Down 4 values don't matter (always go for it on 4th).
        # Down 5 = the real decision point.  Down 6 = last chance.
        # Values = max ytg to go for it; above this → kick if available.
        # Kicker skill adjusts: elite kickers (90+) reduce by up to 3,
        # meaning they kick even on shorter ytg.
        # NOTE: select_kick_decision() also has a ytg <= 3 hard bypass,
        # so down 5 always goes for it on 5th-and-3 or less regardless.
        15:  {4: 20, 5: 3, 6: 2},
        30:  {4: 20, 5: 4, 6: 2},
        45:  {4: 20, 5: 5, 6: 3},
        50:  {4: 20, 5: 6, 6: 3},
        60:  {4: 20, 5: 5, 6: 3},
        75:  {4: 20, 5: 4, 6: 2},
        100: {4: 20, 5: 3, 6: 2},
    }

    def _go_for_it_threshold(self, fp: int, down: int) -> int:
        for threshold in sorted(self.GO_FOR_IT_MATRIX.keys()):
            if fp <= threshold:
                return self.GO_FOR_IT_MATRIX[threshold].get(down, 20)
        return 20

    def _expected_points_from_position(self, fp: int) -> float:
        from engine.epa import calculate_ep
        return calculate_ep(fp, 1)

    def select_kick_decision(self) -> PlayType:
        """Coaching decision chart — priority: TD > snap kick > FG > punt > TOD.

        A turnover on downs is the **worst** outcome.  The coaching AI
        will always prefer kicking (snap kick for 5 pts, FG for 3) over
        risking a TOD.  Punting is preferred over TOD when no kick is
        available.  The only time we "go for it" is when the conversion
        looks probable (short ytg) or we're in the red zone chasing 9.
        """
        fp = self.state.field_position
        down = self.state.down
        ytg = self.state.yards_to_go

        fg_distance = (100 - fp) + 10  # Match simulate_drop_kick / simulate_place_kick

        team = self.get_offensive_team()
        kicker = max(self._kicker_candidates(team), key=lambda p: p.kicking)
        kicker_skill = kicker.kicking

        dk_success = self._drop_kick_success(fg_distance, kicker_skill)
        pk_success = self._place_kick_success(fg_distance, kicker_skill)

        # ── Red zone (fp >= 90): always chase the TD ──
        if fp >= 90:
            # Only bail to a kick on 6th down with long ytg
            if down == 6 and ytg >= 8:
                if dk_success >= 0.40:
                    return PlayType.DROP_KICK
                if pk_success >= 0.50:
                    return PlayType.PLACE_KICK
            return None

        # ── Downs 1-3: keep driving ──
        if down <= 3:
            return None

        # ── Determine kick comfort zone (used by all remaining down logic) ──
        snap_kick_agg = self._current_style().get("snap_kick_aggression", 1.0)
        dk_comfort = 30.0 + (kicker_skill - 60) * 0.75
        dk_comfort *= snap_kick_agg

        # ── Down 4: THE decisive down ──
        # With Finnish baseball retention, snap kicks on 4th down are free
        # shots.  If you miss, you keep the ball on 5th down.  If you make
        # it, 5 points.  Only attempt when in snap kick range and kicker
        # is decent.  Short ytg → go for the first down instead.
        if down == 4:
            if dk_success >= 0.35 and fg_distance <= dk_comfort:
                if ytg <= 4:
                    return None
                return PlayType.DROP_KICK
            return None

        # ── Determine best available kick ──

        best_kick = None
        best_kick_ev = 0.0
        # Drop kick: only within the coaching comfort zone
        if fg_distance <= dk_comfort and dk_success >= 0.30:
            best_kick = PlayType.DROP_KICK
            best_kick_ev = dk_success * 5.0
        # Place kick (FG): available at any viable distance
        if pk_success >= 0.20:
            fg_ev = pk_success * 3.0
            if fg_ev > best_kick_ev:
                best_kick = PlayType.PLACE_KICK
                best_kick_ev = fg_ev

        # ── Down 5: THE key decision point (like 4th down in NFL) ──
        # The kicker determines how aggressive the team is about kicking.
        # Elite kickers (90+) lower the "go for it" threshold so the team
        # takes the points.  Weak kickers raise it so the team converts.
        if down == 5:
            go_threshold = self._go_for_it_threshold(fp, 5)
            # Kicker skill adjusts: 90 kicker → -3, 75 → 0, 60 → +3
            kicker_adj = (75 - kicker_skill) // 5
            go_threshold = max(1, go_threshold + kicker_adj)

            # V2.2: Aggression lowers go-for-it threshold (more aggressive = go more often)
            off_mods = self._coaching_mods()
            pf = off_mods.get("personality_factors", {})
            trait_fx = off_mods.get("hidden_trait_effects", {})
            agg = pf.get("aggression", 1.0)
            go_threshold = max(1, int(go_threshold / agg))

            # V2.2: Red zone gambler trait
            if fp >= 80:
                rz_mult = trait_fx.get("go_for_it_redzone_multiplier", 1.0)
                go_threshold = max(1, int(go_threshold / rz_mult))

            # Very short yardage: always go for it
            if ytg <= 2:
                return None
            if ytg <= go_threshold:
                return None
            if best_kick:
                return best_kick
            # No kick available — try to convert (punt on 6th if needed)
            return None

        # ── Down 6: LAST CHANCE — kick > punt > go for it ──
        if down == 6:
            # Go for it on very short ytg (elite kickers lower this)
            go_ytg = max(1, 3 - (kicker_skill - 75) // 10)
            if ytg <= go_ytg:
                return None
            # Any kick available? Take it — always prefer points.
            if best_kick:
                return best_kick
            # No kick available — punt to avoid TOD (field position)
            if fp < 65:
                return PlayType.PUNT
            # Deep in opponent territory but no kick — go for it
            if ytg <= 5:
                return None
            return PlayType.PUNT

        return None

    def _get_score_diff(self) -> float:
        if self.state.possession == "home":
            return self.state.home_score - self.state.away_score
        return self.state.away_score - self.state.home_score

    def _resolve_kick_type(self) -> PlayType:
        result = self.select_kick_decision()
        return result if result is not None else PlayType.PUNT

    def _check_penalties(self, phase: str, play_type: str = "run") -> Optional[Penalty]:
        if phase == "during_play":
            if play_type in ("lateral_chain",):
                catalog_key = "during_play_lateral"
            elif play_type in ("punt", "drop_kick", "place_kick"):
                catalog_key = "during_play_kick"
            else:
                catalog_key = "during_play_run"
        else:
            catalog_key = phase

        penalties = PENALTY_CATALOG.get(catalog_key, [])

        weather_penalty_boost = 0.0
        if self.weather in ("rain", "snow", "sleet"):
            weather_penalty_boost = 0.003
        if self.weather == "heat":
            weather_penalty_boost = 0.002

        for pen_def in penalties:
            prob = pen_def["prob"] + weather_penalty_boost
            if self.state.quarter == 4 and self.state.time_remaining < 300:
                prob *= 1.15

            if random.random() < prob:
                on_side = pen_def["on"]
                if on_side == "offense":
                    team_name = self.state.possession
                elif on_side == "defense":
                    team_name = "away" if self.state.possession == "home" else "home"
                else:
                    team_name = random.choice(["home", "away"])

                team_obj = self.home_team if team_name == "home" else self.away_team
                if on_side == "offense":
                    pen_pool = self._offense_all(team_obj)
                elif on_side == "defense":
                    pen_pool = self._defense_players(team_obj)
                else:
                    pen_pool = team_obj.players[:10]
                player = random.choice(pen_pool)
                ptag = player_tag(player)

                return Penalty(
                    name=pen_def["name"],
                    yards=pen_def["yards"],
                    on_team=team_name,
                    player=ptag,
                    phase=phase,
                )
        return None

    def _should_decline_penalty(self, penalty: Penalty, play: Play) -> bool:
        on_offense = (penalty.on_team == self.state.possession)

        if on_offense:
            if play.result in ("touchdown", "successful_kick"):
                return True
            if play.yards_gained > penalty.yards:
                return True
        else:
            if play.result in ("fumble", "turnover_on_downs"):
                return True
            if play.yards_gained <= -(penalty.yards):
                return True

        return False

    def _apply_pre_snap_penalty(self, penalty: Penalty) -> Play:
        on_offense = (penalty.on_team == self.state.possession)
        if on_offense:
            self.state.field_position = max(1, self.state.field_position - penalty.yards)
        else:
            self.state.field_position = min(99, self.state.field_position + penalty.yards)
            if penalty.yards >= self.state.yards_to_go:
                self.state.down = 1
                self.state.yards_to_go = 20

        team_label = "OFFENSE" if on_offense else "DEFENSE"
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="penalty",
            play_family="none",
            players_involved=[penalty.player],
            yards_gained=0,
            result="penalty",
            description=f"PENALTY: {penalty.name} on {team_label} ({penalty.player}) — {penalty.yards} yards",
            fatigue=round(stamina, 1),
            penalty=penalty,
        )

    def _apply_during_play_penalty(self, penalty: Penalty, play: Play) -> Play:
        if self._should_decline_penalty(penalty, play):
            penalty.declined = True
            play.penalty = penalty
            play.description += f" [DECLINED: {penalty.name}]"
            return play

        on_offense = (penalty.on_team == self.state.possession)
        if on_offense:
            if play.yards_gained > 0:
                self.state.field_position = max(1, self.state.field_position - play.yards_gained)
            self.state.field_position = max(1, self.state.field_position - penalty.yards)
            play.yards_gained = 0
            play.result = "penalty"
        else:
            all_during = PENALTY_CATALOG.get("during_play_run", []) + PENALTY_CATALOG.get("during_play_lateral", []) + PENALTY_CATALOG.get("during_play_kick", [])
            penalty_def = next((p for p in all_during if p["name"] == penalty.name), None)
            auto_first = penalty_def.get("auto_first", False) if penalty_def else False
            self.state.field_position = min(99, self.state.field_position + penalty.yards)
            if auto_first or penalty.yards >= self.state.yards_to_go:
                self.state.down = 1
                self.state.yards_to_go = 20
            play.yards_gained = penalty.yards

        play.field_position = self.state.field_position
        play.down = self.state.down
        play.yards_to_go = self.state.yards_to_go
        play.penalty = penalty
        team_label = "OFFENSE" if on_offense else "DEFENSE"
        play.description += f" | PENALTY: {penalty.name} on {team_label} ({penalty.player}) — {penalty.yards} yds"

        return play

    def _apply_post_play_penalty(self, penalty: Penalty, play: Play) -> Play:
        if self._should_decline_penalty(penalty, play):
            penalty.declined = True
            play.penalty = penalty
            play.description += f" [DECLINED: {penalty.name}]"
            return play

        on_offense = (penalty.on_team == play.possession)
        if on_offense:
            self.state.field_position = max(1, self.state.field_position - penalty.yards)
        else:
            self.state.field_position = min(99, self.state.field_position + penalty.yards)

        play.field_position = self.state.field_position
        play.penalty = penalty
        team_label = "OFFENSE" if on_offense else "DEFENSE"
        play.description += f" | POST-PLAY PENALTY: {penalty.name} on {team_label} ({penalty.player}) — {penalty.yards} yds"

        return play

    def _check_snap_kick_shot_play(self) -> Optional[PlayType]:
        """Snap kick: context-dependent drop kick attempt.

        Snap kicks are the SIGNATURE scoring play of Viperball — the
        equivalent of the three-pointer in basketball.  They should be
        attempted opportunistically throughout a drive, not just as a
        last resort.

        Downs 2-3: "Pull-up three" — opportunistic snap kick, frequency
                   driven by the KICKER'S skill and coaching style.
        Down 4:    Decisive down — free shot with Finnish baseball retention.
                   Missed kicks retain possession, so any kicker can attempt.
        Down 5:    Secondary chance after select_kick_decision says go.
                   The kicker's skill determines how often this fires.
        Down 6:    Handled by select_kick_decision, not this function.
        """
        if self.state.down > 5 or self.state.down < 2:
            return None
        fp = self.state.field_position
        fg_distance = (100 - fp) + 10
        if fg_distance > 55:
            return None  # Beyond viable snap kick range

        team = self.get_offensive_team()
        kicker = max(self._kicker_candidates(team), key=lambda p: p.kicking)

        is_specialist = kicker.archetype == "kicking_zb" or kicker.kicking >= 82
        down = self.state.down
        ytg = self.state.yards_to_go

        # Coaching style snap kick aggression (boot_raid=1.5, ball_control=1.2, etc.)
        snap_kick_agg = self._current_style().get("snap_kick_aggression", 1.0)

        # Kicker skill multiplier: elite kickers (90+) fire 50% more often,
        # weak kickers (60) fire 60% less often.
        kicker_mult = max(0.4, (kicker.kicking - 60) / 20.0)  # 0.4 at 68, 1.0 at 80, 1.5 at 90

        # ── Down 2-3: Pull-up three — opportunistic shot (reduced ~40%) ──
        if down <= 3:
            if fg_distance <= 20:
                shot_chance = 0.14
            elif fg_distance <= 25:
                shot_chance = 0.10
            elif fg_distance <= 30:
                shot_chance = 0.07
            elif fg_distance <= 40:
                shot_chance = 0.05
            elif fg_distance <= 50:
                shot_chance = 0.03
            else:
                shot_chance = 0.02
            if is_specialist:
                shot_chance *= 1.6
            shot_chance *= snap_kick_agg * kicker_mult
            if random.random() < shot_chance:
                return PlayType.DROP_KICK
            return None

        # ── Down 4: Decisive down — free shot with Finnish baseball retention ──
        # Missed snap kicks on 4th down retain possession, so the risk is low.
        # Attempt when in range and ytg is long enough that a first down isn't easy.
        if down == 4:
            if ytg <= 4:
                return None  # Short ytg — go for the first down
            if fg_distance <= 20:
                shot_chance = 0.30
            elif fg_distance <= 25:
                shot_chance = 0.22
            elif fg_distance <= 30:
                shot_chance = 0.15
            elif fg_distance <= 40:
                shot_chance = 0.10
            elif fg_distance <= 50:
                shot_chance = 0.05
            else:
                return None
            if is_specialist:
                shot_chance *= 1.4
            shot_chance *= snap_kick_agg * kicker_mult
            if random.random() < shot_chance:
                return PlayType.DROP_KICK
            return None

        # ── Down 5: Secondary chance (after select_kick_decision) ──
        # The kicker's skill and style drive the frequency.
        if down == 5:
            if ytg < 4:
                return None  # Very short — go for it
            if fg_distance <= 25:
                shot_chance = 0.50
            elif fg_distance <= 35:
                shot_chance = 0.35
            elif fg_distance <= 45:
                shot_chance = 0.25
            elif fg_distance <= 55:
                shot_chance = 0.12
            else:
                return None
            shot_chance *= snap_kick_agg * kicker_mult
            if random.random() < shot_chance:
                return PlayType.DROP_KICK

        return None

    def simulate_play(self) -> Play:
        self.state.play_number += 1

        # Kick pass "floor-spacing": a successful kick pass spreads the
        # defense thin, reducing tackle effectiveness on the NEXT play only.
        # Transfer the "next play" flag into the "active" flag for this play.
        self._spread_thin_active = getattr(self, '_spread_thin_next_play', False)
        self._spread_thin_next_play = False

        pre_snap_pen = self._check_penalties("pre_snap")
        if pre_snap_pen:
            return self._apply_pre_snap_penalty(pre_snap_pen)

        # ── Kick decision: evaluate on down 4+ ──
        # The coaching decision chart considers field position, down,
        # yards-to-go, and game state to determine whether to kick.
        if self.state.down >= 4:
            kick_decision = self.select_kick_decision()
            if kick_decision is not None:
                family = PlayFamily.TERRITORY_KICK
                if kick_decision == PlayType.PUNT:
                    play = self.simulate_punt(family)
                elif kick_decision == PlayType.DROP_KICK:
                    play = self.simulate_drop_kick(family)
                elif kick_decision == PlayType.PLACE_KICK:
                    play = self.simulate_place_kick(family)
                else:
                    play = self.simulate_punt(family)

                post_pen = self._check_penalties("post_play", play_type=play.play_type)
                if post_pen:
                    play = self._apply_post_play_penalty(post_pen, play)
                return play

        # Snap kick shot play — only for specialists in close range
        if self.state.down <= 5:
            shot_play = self._check_snap_kick_shot_play()
            if shot_play == PlayType.DROP_KICK:
                family = PlayFamily.TERRITORY_KICK
                play = self.simulate_drop_kick(family)
                post_pen = self._check_penalties("post_play", play_type=play.play_type)
                if post_pen:
                    play = self._apply_post_play_penalty(post_pen, play)
                return play

        play_family = self.select_play_family()
        play_type = PLAY_FAMILY_TO_TYPE.get(play_family, PlayType.RUN)

        if play_type == PlayType.PUNT:
            if self.state.down == 6:
                play_type = self._resolve_kick_type()
            else:
                play_type = PlayType.RUN
                play_family = PlayFamily.DIVE_OPTION
            play_family = PlayFamily.TERRITORY_KICK if play_type != PlayType.RUN else play_family

        if play_type == PlayType.RUN:
            play = self.simulate_run(play_family)
        elif play_type == PlayType.LATERAL_CHAIN:
            play = self.simulate_lateral_chain(play_family)
        elif play_type == PlayType.KICK_PASS:
            play = self.simulate_kick_pass(play_family)
        elif play_type == PlayType.TRICK_PLAY:
            play = self.simulate_trick_play(play_family)
        elif play_type == PlayType.PUNT:
            play = self.simulate_punt(play_family)
        elif play_type == PlayType.DROP_KICK:
            play = self.simulate_drop_kick(play_family)
        elif play_type == PlayType.PLACE_KICK:
            play = self.simulate_place_kick(play_family)
        else:
            play = self.simulate_run(play_family)

        actual_type = play.play_type if play else "run"
        during_pen = self._check_penalties("during_play", play_type=actual_type)
        if during_pen:
            play = self._apply_during_play_penalty(during_pen, play)
        else:
            post_pen = self._check_penalties("post_play", play_type=actual_type)
            if post_pen:
                play = self._apply_post_play_penalty(post_pen, play)

        return play

    def select_play_family(self) -> PlayFamily:
        style = self._current_style()
        weights = dict(style["weights"])

        down = self.state.down
        ytg = self.state.yards_to_go
        fp = self.state.field_position

        weights["territory_kick"] = max(0.01, weights.get("territory_kick", 0.2) * 0.05)

        kick_pass_base = weights.get("kick_pass", 0.05)
        weights["kick_pass"] = kick_pass_base * 1.4

        for rk in ("dive_option", "power", "sweep_option", "speed_option", "counter", "draw"):
            weights[rk] = weights.get(rk, 0.1) * 2.2

        weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3

        if ytg <= 3:
            weights["dive_option"] = weights.get("dive_option", 0.1) * 2.2
            weights["power"] = weights.get("power", 0.1) * 2.2
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.5
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.3
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.4
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 0.5
            weights["counter"] = weights.get("counter", 0.05) * 0.8
            weights["draw"] = weights.get("draw", 0.05) * 0.6
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 0.8
            weights["trick_play"] = weights.get("trick_play", 0.05) * 0.3
        elif ytg <= 10:
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.3
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.3
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.4
            weights["counter"] = weights.get("counter", 0.05) * 1.2
            weights["draw"] = weights.get("draw", 0.05) * 1.1
            weights["trick_play"] = weights.get("trick_play", 0.05) * 1.2
        else:
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.8
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.4
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.4
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.2
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.3
            weights["trick_play"] = weights.get("trick_play", 0.05) * 1.6
            weights["dive_option"] = weights.get("dive_option", 0.1) * 0.7
            weights["power"] = weights.get("power", 0.1) * 0.7

        # ── "2nd & Short" aggression ──
        # With down 2 and < 5 to go, the offense has 4 downs of cushion.
        # Go-like aggression: hunt the 9-point TD with big-play calls.
        if down == 2 and ytg < 5:
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.8
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 2.2
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 2.0
            weights["trick_play"] = weights.get("trick_play", 0.05) * 1.8
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.5
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.4
            # Dial back conservative grinds — we can afford to miss
            weights["dive_option"] = weights.get("dive_option", 0.1) * 0.5
            weights["power"] = weights.get("power", 0.1) * 0.5

        # ── Scoring gravity zones ──
        if fp >= 85:
            # Deep red zone: TD hunting — boost all run families, suppress passing
            for rk in ("dive_option", "power", "sweep_option", "speed_option"):
                weights[rk] = weights.get(rk, 0.05) * 2.5
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.5
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3
            weights["trick_play"] = weights.get("trick_play", 0.05) * 0.3
            weights["territory_kick"] = 0.0
        elif fp >= 75:
            # Snap kick prime zone — runs stay strong, kick_pass drops
            for rk in ("dive_option", "power", "sweep_option", "speed_option"):
                weights[rk] = weights.get(rk, 0.05) * 1.8
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 0.8
            weights["territory_kick"] = 0.0
        elif fp >= 65:
            # FG/snap kick range — balanced but territory_kick suppressed
            weights["territory_kick"] = 0.0

        if down >= 5 and ytg >= 10:
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.5
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.3
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.3
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.3

        score_diff = self._get_score_diff()
        quarter = self.state.quarter
        time_left = self.state.time_remaining
        if quarter >= 3 and score_diff > 10:
            weights["dive_option"] = weights.get("dive_option", 0.1) * 1.6
            weights["power"] = weights.get("power", 0.1) * 1.4
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.2
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.5
            weights["draw"] = weights.get("draw", 0.05) * 0.6
            weights["trick_play"] = weights.get("trick_play", 0.05) * 0.3
        elif quarter == 4 and time_left <= 300 and score_diff < -7:
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.5
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.6
            weights["kick_pass"] = weights.get("kick_pass", 0.05) * 1.5
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.4
            weights["trick_play"] = weights.get("trick_play", 0.05) * 1.8
            weights["dive_option"] = weights.get("dive_option", 0.1) * 0.5
            weights["power"] = weights.get("power", 0.1) * 0.5

        # ── Two-minute drill play selection ──
        if (quarter in (2, 4) and time_left < 120):
            if score_diff < 0:
                # Trailing: maximum aggression, big-play attempts
                weights["kick_pass"] = weights.get("kick_pass", 0.05) * 2.0
                weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.5
                weights["speed_option"] = weights.get("speed_option", 0.1) * 1.3
                weights["territory_kick"] = weights.get("territory_kick", 0.05) * 0.2
                weights["dive_option"] = weights.get("dive_option", 0.1) * 0.5
                weights["power"] = weights.get("power", 0.1) * 0.4
            elif score_diff > 0:
                # Leading: conservative, burn clock
                weights["dive_option"] = weights.get("dive_option", 0.1) * 2.0
                weights["power"] = weights.get("power", 0.1) * 1.5
                weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3
                weights["kick_pass"] = weights.get("kick_pass", 0.05) * 0.4
                weights["trick_play"] = weights.get("trick_play", 0.05) * 0.2

        style_name = self._current_style_name()
        self._apply_style_situational(weights, style_name, down, ytg, fp, score_diff, quarter, time_left)

        kp_weight = weights.get("kick_pass", 0.05)
        kp_bonus = style.get("kick_pass_bonus", 0.0)
        if kp_weight >= 0.10 or kp_bonus >= 0.06:
            spacing_factor = 1.0 + min(0.15, kp_weight * 0.5 + kp_bonus)
            weights["dive_option"] = weights.get("dive_option", 0.1) * spacing_factor
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * spacing_factor
            weights["speed_option"] = weights.get("speed_option", 0.1) * spacing_factor
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * (1.0 + min(0.10, kp_bonus * 0.8))

        # ── V2.2: Coaching personality modulates play family weights ──
        off_mods = self._coaching_mods()
        pf = off_mods.get("personality_factors", {})
        sub_fx = off_mods.get("sub_archetype_effects", {})
        trait_fx = off_mods.get("hidden_trait_effects", {})

        # Aggression → kick_pass weight
        agg = pf.get("aggression", 1.0)
        weights["kick_pass"] = weights.get("kick_pass", 0.05) * agg

        # Risk tolerance → trick_play weight
        risk = pf.get("risk_tolerance", 1.0)
        trick_mult = sub_fx.get("trick_play_weight_multiplier", 1.0) * trait_fx.get("trick_play_weight_multiplier", 1.0)
        weights["trick_play"] = weights.get("trick_play", 0.05) * risk * trick_mult

        # Chaos appetite → lateral_spread weight
        chaos = pf.get("chaos_appetite", 1.0)
        lat_mult = trait_fx.get("lateral_weight_multiplier", 1.0)
        weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * chaos * lat_mult

        # Tempo preference → kick_pass boost (tempo coaches love the air game)
        tempo = pf.get("tempo_preference", 1.0)
        kp_sub = sub_fx.get("kick_pass_weight_multiplier", 1.0)
        weights["kick_pass"] = weights.get("kick_pass", 0.05) * tempo * kp_sub

        # Variance tolerance → explosive play families
        var_tol = pf.get("variance_tolerance", 1.0)
        for fam in ("speed_option", "viper_jet", "lateral_spread"):
            weights[fam] = weights.get(fam, 0.05) * var_tol

        # Punt hater / field position purist
        punt_mult = trait_fx.get("punt_weight_multiplier", 1.0)
        weights["territory_kick"] = weights.get("territory_kick", 0.05) * punt_mult

        families = list(PlayFamily)
        w = [max(0.01, weights.get(f.value, 0.05)) for f in families]
        return random.choices(families, weights=w)[0]

    def _current_style(self) -> Dict:
        if self.state.possession == "home":
            return self.home_style
        return self.away_style

    def _current_style_name(self) -> str:
        if self.state.possession == "home":
            return self.home_team.offense_style
        return self.away_team.offense_style

    def _current_defense(self) -> Dict:
        if self.state.possession == "home":
            return self.away_defense
        return self.home_defense

    def _apply_style_situational(self, weights: Dict, style_name: str, down: int, ytg: int, fp: int, score_diff: int, quarter: int, time_left: int):
        if style_name == "ground_pound":
            if down <= 3:
                weights["dive_option"] = weights.get("dive_option", 0.1) * 1.3
                weights["power"] = weights.get("power", 0.1) * 1.3
            if fp >= 80:
                weights["dive_option"] = weights.get("dive_option", 0.1) * 1.4
                weights["power"] = weights.get("power", 0.1) * 1.4
                weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3

        elif style_name == "boot_raid":
            launch_pad = self._current_style().get("launch_pad_threshold", 55)
            if fp >= launch_pad and fp < 85:
                attack_weights = self._current_style().get("weights_attack", {})
                for k, v in attack_weights.items():
                    weights[k] = v
            elif fp < 40:
                weights["dive_option"] = weights.get("dive_option", 0.1) * 1.3
                weights["power"] = weights.get("power", 0.1) * 1.2

        elif style_name == "ball_control":
            if quarter >= 3 and score_diff > 0:
                weights["dive_option"] = weights.get("dive_option", 0.1) * 1.5
                weights["power"] = weights.get("power", 0.1) * 1.5
                weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.3
                weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3
                weights["viper_jet"] = weights.get("viper_jet", 0.05) * 0.3

        elif style_name == "ghost":
            weights["counter"] = weights.get("counter", 0.05) * 1.4
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.3
            if down <= 2:
                weights["draw"] = weights.get("draw", 0.05) * 1.5

        elif style_name == "rouge_hunt":
            early_punt = self._current_style().get("early_punt_threshold", 3)
            if down >= early_punt and fp < 50 and ytg >= 10:
                weights["territory_kick"] = weights.get("territory_kick", 0.2) * 3.0

        elif style_name == "chain_gang":
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.3
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.4
            if quarter == 4 and abs(score_diff) <= 7:
                weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.5

        elif style_name == "triple_threat":
            if down <= 2:
                weights["counter"] = weights.get("counter", 0.05) * 1.5
                weights["draw"] = weights.get("draw", 0.05) * 1.3
            if fp >= 70:
                weights["speed_option"] = weights.get("speed_option", 0.1) * 1.3
                weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.3

    def calculate_block_probability(self, kick_type: str = "punt") -> float:
        """
        Calculate probability of blocked kick based on offensive style,
        defensive style, and both teams' ST schemes.
        """
        base_prob = BASE_BLOCK_PUNT if kick_type == "punt" else BASE_BLOCK_KICK

        # Offensive style modifier (kicking team protection)
        offense_style_name = self.home_team.offense_style if self.state.possession == "home" else self.away_team.offense_style
        offense_modifier = OFFENSE_BLOCK_MODIFIERS.get(offense_style_name, 1.0)

        # Defensive style modifier (rush team aggression)
        defense_style_name = self.away_team.defense_style if self.state.possession == "home" else self.home_team.defense_style
        defense_modifier = DEFENSE_BLOCK_MODIFIERS.get(defense_style_name, 1.0)

        # ST scheme modifier (rushing team's block specialization)
        rushing_st = self.away_st if self.state.possession == "home" else self.home_st
        st_modifier = rushing_st.get("block_rush_modifier", 1.0)

        block_prob = base_prob * offense_modifier * defense_modifier * st_modifier

        return max(0.0, block_prob)

    def calculate_muff_probability(self) -> float:
        """
        Calculate probability of muffed punt return based on defensive style,
        ST schemes, and returner's Keeper archetype.
        """
        # Kicking team's defensive style (their coverage quality)
        kicking_defense_name = self.home_team.defense_style if self.state.possession == "home" else self.away_team.defense_style
        coverage_modifier = DEFENSE_MUFF_MODIFIERS.get(kicking_defense_name, 1.0)

        # Kicking team's ST scheme (gunner quality)
        kicking_st = self.home_st if self.state.possession == "home" else self.away_st
        st_muff_bonus = kicking_st.get("muff_bonus", 1.0)

        # Receiving team's ST scheme (returner ball security)
        receiving_st = self.away_st if self.state.possession == "home" else self.home_st
        returner_muff_rate = receiving_st.get("returner_muff_rate", 1.0)

        # Returner's keeper archetype muff rate (sure_hands = 0.03, return = 0.15)
        receiving_team = self.get_defensive_team()
        returner = self._pick_returner(receiving_team)
        keeper_muff_mod = 1.0
        if returner and returner.position == "Keeper" and returner.archetype != "none":
            arch_info = get_archetype_info(returner.archetype)
            # Lower muff_rate = safer hands. Normalize around 0.10 baseline
            arch_muff = arch_info.get("muff_rate", 0.10)
            keeper_muff_mod = arch_muff / 0.10  # sure_hands: 0.3, return: 1.5, tackle: 1.2

        muff_prob = BASE_MUFF_PUNT * coverage_modifier * st_muff_bonus * returner_muff_rate * keeper_muff_mod
        muff_prob += self.weather_info.get("muff_modifier", 0.0)

        receiving_side = "away" if self.state.possession == "home" else "home"
        recv_mods = self.home_coaching_mods if receiving_side == "home" else self.away_coaching_mods
        if recv_mods.get("hc_classification") == "disciplinarian":
            cls_fx = recv_mods.get("classification_effects", {})
            muff_prob *= cls_fx.get("muff_reduction", 1.0)

        return max(0.0, muff_prob)

    def get_defensive_read(self, play_family: PlayFamily) -> bool:
        """
        Determines if the defense successfully 'reads' the play.
        A successful read reduces play effectiveness.

        The read rate is built from:
        1. Base scheme read_success_rate
        2. Gameplan bias for specific play families
        3. Situational modifiers (red zone, short yardage, score, etc.)
        4. Personnel quality (weighted by scheme's personnel_weights)
        """
        defense = self._current_defense()
        base_read_rate = defense.get("read_success_rate", 0.35)

        # Gameplan bias for specific play families
        gameplan_bias = defense.get("gameplan_bias", {}).get(play_family.value, 0.0)

        # Coaching: Scheme Master gameplan adaptation — gameplan reads improve in 2nd half
        def_mods = self._def_coaching_mods()
        cls_effects = def_mods.get("classification_effects", {})
        if def_mods.get("hc_classification") == "scheme_master" and self.state.quarter >= 3:
            adapt = cls_effects.get("gameplan_adaptation_bonus", 0.0)
            gameplan_bias += adapt

        # V2.2: Adaptability personality boosts defensive reads in late game
        def_pf = def_mods.get("personality_factors", {})
        adapt_f = def_pf.get("adaptability", 1.0)
        stub_f = def_pf.get("stubbornness", 1.0)
        effective_adapt = adapt_f * (2.0 - stub_f)  # stubbornness counters adaptability
        if self.state.quarter >= 3:
            gameplan_bias *= effective_adapt

        # V2.2: Tactician sub-archetype: extra read bonus
        def_sub_fx = def_mods.get("sub_archetype_effects", {})
        tactician_bonus = def_sub_fx.get("defensive_read_bonus", 0.0)

        # Situational modifiers from scheme
        situational_boost = self._get_defense_situational_boost(defense)

        # Personnel quality boost — good defenders improve read rate
        personnel_boost = self._get_defense_personnel_boost(defense)

        # Coaching: instincts improve defensive reads
        instincts_factor = def_mods.get("instincts_factor", 0.0)
        coaching_read_boost = instincts_factor * 0.06 + tactician_bonus

        total_read_rate = base_read_rate + gameplan_bias + situational_boost + personnel_boost + coaching_read_boost
        total_read_rate = max(0.10, min(0.65, total_read_rate))

        return random.random() < total_read_rate

    def _get_defense_situational_boost(self, defense: Dict) -> float:
        """
        Returns a read rate adjustment based on game situation and scheme tendencies.
        Each scheme reacts differently to down/distance/score/field position.
        """
        sit = defense.get("situational", {})
        boost = 0.0

        fp = self.state.field_position
        down = self.state.down
        ytg = self.state.yards_to_go
        score_diff = self._get_score_diff()
        quarter = self.state.quarter

        # Red zone — defenses tighten
        if fp >= 80:
            boost += sit.get("red_zone_read_boost", 0.05)

        # Short yardage — some schemes excel, others struggle
        # modifier < 1.0 means the scheme is BETTER (reduces yards)
        # We convert to a read boost: lower modifier = higher read rate
        if ytg <= 3:
            short_mod = sit.get("short_yardage_modifier", 1.0)
            boost += (1.0 - short_mod) * 0.15  # e.g. 0.70 → +0.045 read rate

        # Long yardage — opposite dynamics
        elif ytg > 10:
            long_mod = sit.get("long_yardage_modifier", 1.0)
            boost += (1.0 - long_mod) * 0.10

        # Score-based aggression
        if quarter >= 3:
            if score_diff < -7:
                boost += sit.get("leading_conserve", 0.05)
            elif score_diff > 7:
                boost += sit.get("trailing_aggression", 0.05)

        def_mods = self._def_coaching_mods()
        if def_mods.get("hc_classification") == "gameday_manager":
            cls_fx = def_mods.get("classification_effects", {})
            boost *= (1.0 + cls_fx.get("situational_amplification", 0.0))

        return boost

    def _get_defense_personnel_boost(self, defense: Dict) -> float:
        """
        Returns a read rate boost based on how well the defensive personnel
        matches the scheme's needs. Each scheme weights different stats.

        A Blitz Pack needs speed and power. A Shadow needs awareness and agility.
        A Predator needs awareness and hands. Better personnel = better reads.
        """
        def_team = self.get_defensive_team()
        pw = defense.get("personnel_weights", {})
        if not pw:
            return 0.0

        # Average the weighted stats across starting defenders
        defenders = self._defense_players(def_team)

        total_score = 0.0
        for p in defenders:
            player_score = 0.0
            player_score += pw.get("tackling", 0.0) * p.tackling
            player_score += pw.get("speed", 0.0) * p.speed
            player_score += pw.get("awareness", 0.0) * getattr(p, 'awareness', 75)
            player_score += pw.get("agility", 0.0) * getattr(p, 'agility', 75)
            player_score += pw.get("power", 0.0) * getattr(p, 'power', 75)
            player_score += pw.get("hands", 0.0) * getattr(p, 'hands', 75)
            total_score += player_score

        avg_score = total_score / max(1, len(defenders))
        # Normalize: 75 is average (0 boost), 90+ is elite (+0.05), 60- is bad (-0.05)
        return (avg_score - 75) / 300  # 15 point swing = ±0.05

    def _current_defense_name(self) -> str:
        """Returns the defense style name string for the team currently on defense."""
        if self.state.possession == "home":
            return self.away_team.defense_style
        return self.home_team.defense_style

    def _kicking_team_st(self) -> Dict:
        """Returns the ST scheme dict for the team currently punting/kicking."""
        if self.state.possession == "home":
            return self.home_st
        return self.away_st

    def _returning_team_st(self) -> Dict:
        """Returns the ST scheme dict for the team receiving the punt/kick."""
        if self.state.possession == "home":
            return self.away_st
        return self.home_st

    def _defensive_fatigue_factor(self) -> float:
        """
        Returns defensive fatigue multiplier (>1.0 = tired defense, helps offense)
        Defensive style's fatigue_resistance slows down fatigue accumulation
        """
        # Base fatigue levels
        if self.drive_play_count >= 12:
            base_fatigue = 1.25
        elif self.drive_play_count >= 8:
            base_fatigue = 1.15
        elif self.drive_play_count >= 5:
            base_fatigue = 1.05
        else:
            base_fatigue = 1.0

        # DEFENSIVE SYSTEM: Apply defensive fatigue resistance
        defense = self._current_defense()
        fatigue_resistance = defense.get("fatigue_resistance", 0.0)

        # Coaching: rotations attribute adds extra fatigue resistance
        def_mods = self._def_coaching_mods()
        fatigue_resistance += def_mods.get("fatigue_resistance_mod", 0.0)

        # Fatigue resistance reduces the fatigue penalty
        # fatigue_resistance of 0.05 reduces fatigue bonus by 5%
        # fatigue_resistance of -0.05 INCREASES fatigue penalty by 5%
        adjusted_fatigue = 1.0 + (base_fatigue - 1.0) * (1.0 - fatigue_resistance)

        # V2.2: Opponent tempo pressure (offensive tempo pref → defense tires faster)
        off_mods = self._coaching_mods()
        off_pf = off_mods.get("personality_factors", {})
        tempo_pref = off_pf.get("tempo_preference", 1.0)
        if tempo_pref > 1.0:
            adjusted_fatigue *= 1.0 + (tempo_pref - 1.0) * 0.5  # subtle extra tire

        return max(1.0, adjusted_fatigue)

    def _red_zone_td_check(self, new_position: int, yards_gained: int, team: Team) -> bool:
        """TD check — contest-influenced goal-line scoring.

        TDs are earned by physically reaching field_position >= 100.
        Inside the 5-yard line (fp >= 95), there's a realistic chance
        of punching it in — the closer you are, the higher the chance.
        """
        if yards_gained < 1:
            return False
        # Ball crosses the goal line — automatic TD
        if new_position >= 100:
            return True
        # Goal-line situations — proximity increases TD probability
        if new_position >= 98:
            return random.random() < 0.55
        if new_position >= 96:
            return random.random() < 0.35
        if new_position >= 95:
            return random.random() < 0.20
        return False

    def _breakaway_check(self, yards_gained: int, team: Team, family=None) -> int:
        """Breakaway system — big gains can extend into bigger plays.

        Requires 8+ yards to trigger (not 5). Base chance from
        EXPLOSIVE_CHANCE (per play family). Capped at 25 extra yards —
        no automatic house calls. Speed gap still matters.
        """
        if yards_gained >= 8:
            # Use play-family explosive base from EXPLOSIVE_CHANCE
            base = EXPLOSIVE_CHANCE.get(family.value, 0.06) if family else 0.06
            speed_gap = (team.avg_speed - 85) / 100
            def_fatigue_bonus = (self._defensive_fatigue_factor() - 1.0)
            breakaway_chance = base + speed_gap + def_fatigue_bonus

            # Bigger initial gains = more likely to break free
            if yards_gained >= 12:
                breakaway_chance += 0.10

            if random.random() < breakaway_chance:
                if yards_gained >= 12:
                    extra = random.randint(8, 25)
                else:
                    extra = random.randint(5, 18)
                return yards_gained + extra
        return yards_gained

    def _run_fumble_check(self, family: PlayFamily, yards_gained: int, carrier=None) -> bool:
        config = RUN_PLAY_CONFIG.get(family, RUN_PLAY_CONFIG[PlayFamily.DIVE_OPTION])
        base_fumble = config['fumble_rate']

        if yards_gained <= 0:
            base_fumble += 0.012

        if carrier:
            ball_security = getattr(carrier, 'hands', getattr(carrier, 'power', 75))
            if ball_security >= 85:
                base_fumble *= 0.70
            elif ball_security < 60:
                base_fumble *= 1.15

        if self.weather in ['rain', 'snow', 'sleet']:
            base_fumble *= 1.20
        else:
            base_fumble += self.weather_info.get("fumble_modifier", 0.0)

        if carrier and carrier.archetype != "none":
            arch_info = get_archetype_info(carrier.archetype)
            fumble_mod = arch_info.get("fumble_modifier", 1.0)
            if isinstance(fumble_mod, float) and fumble_mod != 1.0:
                base_fumble *= fumble_mod

        # Coaching: Disciplinarian reduces fumble rate
        off_mods = self._coaching_mods()
        if off_mods.get("hc_classification") == "disciplinarian":
            cls_fx = off_mods.get("classification_effects", {})
            base_fumble *= cls_fx.get("fumble_reduction", 1.0)

        # V2.2: Composure personality affects pressure fumbles
        off_pf = off_mods.get("personality_factors", {})
        comp_f = off_pf.get("composure_tendency", 1.0)
        # High composure (factor > 1.0) reduces fumbles; low increases
        base_fumble *= (2.0 - comp_f)  # comp=1.25 → 0.75x; comp=0.75 → 1.25x

        return random.random() < base_fumble

    def _pick_returner(self, team):
        """Skill-weighted returner selection — speed and hands matter."""
        eligible = [p for p in team.players if p.position in
                    ("Halfback", "Wingback", "Slotback", "Viper", "Keeper")]
        if not eligible:
            eligible = [p for p in team.players if p.position not in ("Offensive Line", "Defensive Line")]
        if not eligible:
            return None
        # Weight by return ability: speed dominant, hands for ball security
        weights = []
        for p in eligible:
            w = p.speed * 0.55 + getattr(p, 'agility', 75) * 0.25 + getattr(p, 'hands', 75) * 0.20
            # Keeper return_keeper archetype gets a big boost
            if p.position == "Keeper" and p.archetype == "return_keeper":
                w *= 1.40
            weights.append(max(1.0, w))
        return random.choices(eligible, weights=weights, k=1)[0]

    def _pick_coverage_tackler(self, team):
        """Skill-weighted coverage tackler — tackling and speed matter."""
        eligible = [p for p in team.players if p.position in
                    ("Keeper", "Defensive Line")]
        if not eligible:
            eligible = team.players
        if not eligible:
            return None
        weights = []
        for p in eligible:
            w = p.tackling * 0.40 + p.speed * 0.35 + getattr(p, 'awareness', 75) * 0.25
            # Tackle keeper archetype excels on coverage
            if p.position == "Keeper" and p.archetype == "tackle_keeper":
                w *= 1.30
            weights.append(max(1.0, w))
        return random.choices(eligible, weights=weights, k=1)[0]

    def _pick_tackler(self, team):
        eligible = [p for p in team.players if p.position in
                    ("Keeper", "Defensive Line")]
        if not eligible:
            eligible = team.players
        return random.choice(eligible) if eligible else None

    def _calculate_punt_return_yards(self, returner, returning_team, punting_team) -> int:
        """Skill-based punt return yardage. Returner attributes, keeper archetype,
        and both teams' ST schemes all factor in."""
        base_return = max(0, int(random.gauss(12, 8)))

        # Returner skill factor (speed + agility)
        speed_factor = returner.speed / 80.0
        agility_factor = getattr(returner, 'agility', 75) / 80.0
        returner_modifier = speed_factor * 0.60 + agility_factor * 0.40

        # Keeper archetype: return_keeper gets the archetype's return_yards_modifier
        archetype_info = get_archetype_info(returner.archetype) if returner.archetype != "none" else {}
        return_yards_mod = archetype_info.get("return_yards_modifier", 1.0)
        returner_modifier *= return_yards_mod

        # Returning team's ST scheme bonus
        ret_st = ST_SCHEMES.get(returning_team.st_scheme, ST_SCHEMES["aces"])
        returner_modifier *= ret_st["return_yards_modifier"]

        # Punting team's ST scheme coverage quality reduces return yards
        punt_st = ST_SCHEMES.get(punting_team.st_scheme, ST_SCHEMES["aces"])
        returner_modifier /= punt_st["coverage_modifier"]

        return max(0, int(base_return * returner_modifier))

    def _pick_def_tackler(self, def_team, yards_gained: int):
        dl = [p for p in def_team.players if p.position == "Defensive Line"]
        kp = [p for p in def_team.players if p.position == "Keeper"]
        if yards_gained <= 0:
            pool = dl * 4 + kp
        elif yards_gained <= 4:
            pool = dl * 3 + kp * 2
        elif yards_gained <= 10:
            pool = dl * 2 + kp * 3
        else:
            pool = dl + kp * 4
        if not pool:
            pool = def_team.players
        weights = []
        for p in pool:
            w = p.tackling * 0.5 + p.speed * 0.3 + getattr(p, 'awareness', 75) * 0.2
            stamina_pct = getattr(p, 'current_stamina', 100.0) / 100.0
            w *= max(0.5, stamina_pct)
            weights.append(max(1.0, w))
        return random.choices(pool, weights=weights, k=1)[0]

    def _resolve_fumble_recovery(self, fumble_spot, fumbling_player=None):
        off_team = self.get_offensive_team()
        def_team = self.get_defensive_team()
        def _recovery_score(player, is_nearby=True):
            base = getattr(player, 'awareness', 75) * 0.35 + player.speed * 0.25 + getattr(player, 'power', 75) * 0.20
            base += random.uniform(0, 20)
            if is_nearby:
                base += random.uniform(5, 15)
            return base
        off_scores = [_recovery_score(p, p == fumbling_player) for p in off_team.players[:6]]
        def_scores = [_recovery_score(p) for p in def_team.players[:6]]
        best_off = max(off_scores, default=30)
        best_def = max(def_scores, default=30)
        total = best_off + best_def
        if total <= 0:
            total = 1
        off_chance = best_off / total
        defense = self._current_defense()
        pressure = defense.get("pressure_factor", 0.50)
        off_chance -= pressure * 0.05
        turnover_bonus = defense.get("turnover_bonus", 0.0)
        off_chance -= turnover_bonus * 0.10
        off_chance = max(0.0, off_chance)
        if random.random() >= off_chance:
            return 'defense', True
        else:
            return 'offense', False

    def _determine_viper_alignment(self):
        return random.choice(['left', 'right', 'center'])

    def _determine_defense_alignment(self):
        defense = self._current_defense()
        style_label = defense.get("label", "Base Defense")
        return DEFENSE_ALIGNMENT_MAP.get(style_label, "balanced")

    # ── Dynamic Stochastic Resolution ──────────────────────────
    #
    # V2: Dual-mode contest resolution.
    #
    # v1_sigmoid (legacy): additive delta + sigmoid center
    # v2_power_ratio (spec): multiplicative (carrier/tackler)**exp
    #
    # The feature flag V2_ENGINE_CONFIG["contest_model"] controls
    # which path is taken.  When halo_enabled=True, non-star plays
    # use team halo instead of individual ratings.
    # ─────────────────────────────────────────────────────────────

    def _get_offensive_rating(self, carrier, use_halo: bool = False) -> float:
        """Get the offensive rating for contest resolution.

        V2 Halo: if use_halo is True (non-star play), use team halo_offense.
        Otherwise use individual canonical stats.
        """
        if use_halo:
            team = self.get_offensive_team()
            return team.halo_offense * self.player_fatigue_modifier(carrier)

        # Individual: canonical speed (weighted blend of speed + agility)
        off_skill = carrier.canon_speed * 0.4 + getattr(carrier, 'power', 75) * 0.3 + getattr(carrier, 'agility', 75) * 0.3
        return off_skill * self.player_fatigue_modifier(carrier)

    def _get_defensive_rating(self, tackler, use_halo: bool = False) -> float:
        """Get the defensive rating for contest resolution.

        V2 Halo: if use_halo is True, use team halo_defense.
        Otherwise use individual canonical stats.
        """
        if use_halo:
            team = self.get_defensive_team()
            return team.halo_defense * self.player_fatigue_modifier(tackler)

        # Individual: canonical tackling (weighted blend of tackling + power + awareness)
        def_skill = tackler.canon_tackling * 0.5 + getattr(tackler, 'awareness', 70) * 0.25 + tackler.speed * 0.25
        return def_skill * self.player_fatigue_modifier(tackler)

    def _apply_variance_archetype(self, raw_yards: float, player) -> float:
        """Apply R/E/C variance modification to contest result.

        Reliable: clamp to rating ± 10 (tight band, consistent)
        Explosive: full range, no floor (boom/bust)
        Clutch: standard + 15% boost in pressure situations
        """
        if not V2_ENGINE_CONFIG.get("rec_archetypes_enabled", False):
            return raw_yards

        va = player.variance_archetype

        if va == "reliable":
            # Reliable: compress toward the expected center.
            # Pull extreme results back toward a reasonable band.
            # The "center" is approximated as the midpoint between
            # raw and a moderate baseline.  This removes boom/bust
            # without the hard clamp that killed late-down conversions.
            moderate = max(3.0, raw_yards * 0.85 + 0.7)
            return (raw_yards + moderate) / 2.0  # Blend toward moderate

        elif va == "explosive":
            # Full range: add extra variance (can boom or bust)
            explosive_noise = random.gauss(0, 1.5)
            return raw_yards + explosive_noise

        elif va == "clutch":
            # Boost in pressure: Q4 within 1 possession, or composure < 80
            is_pressure = False
            if self.state.quarter == 4:
                score_diff = abs(self._get_score_diff())
                if score_diff <= 9:  # Within 1 possession (TD = 9 pts)
                    is_pressure = True
            # Check composure state
            if self.state.possession == "home":
                if self.state.home_composure < 80:
                    is_pressure = True
            else:
                if self.state.away_composure < 80:
                    is_pressure = True

            if is_pressure:
                return raw_yards * 1.15  # +15% in clutch situations
            return raw_yards

        return raw_yards

    def _apply_star_override(self, raw_yards: float, player) -> float:
        """Star Override: designated stars get a performance floor.

        floor = max(roll, player_rating_scaled - 1.0)
        Explosive stars keep full variance (no floor).
        """
        if not V2_ENGINE_CONFIG.get("star_override_enabled", False):
            return raw_yards
        if not player.star_designated:
            return raw_yards
        if player.variance_archetype == "explosive":
            return raw_yards  # Explosive keeps full variance even when starred

        # Performance floor: scale overall to yardage (overall 90 → floor ~4.0)
        floor = max(0.0, (player.overall - 50) / 10.0)
        return max(raw_yards, floor)

    def _should_use_halo(self, carrier) -> bool:
        """Determine if this play uses team halo or individual ratings.

        V2 Rule: 90% of plays use halo.  Star-designated players at
        Critical Contest Points always use individual ratings.
        """
        if not V2_ENGINE_CONFIG.get("halo_enabled", False):
            return False
        if carrier.star_designated:
            return False  # Stars always use individual ratings
        # 90% halo, 10% individual (for non-star plays)
        return random.random() < 0.90

    def _contest_run_yards(self, carrier, tackler, play_config) -> float:
        """Contest-based stochastic resolution for run plays.

        V2 supports dual-mode:
        - v1_sigmoid: legacy additive delta + sigmoid center
        - v2_power_ratio: multiplicative (carrier/tackler)**exp

        With halo enabled, non-star plays use team-level ratings.
        R/E/C variance and star override are applied post-roll.
        """
        contest_model = V2_ENGINE_CONFIG.get("contest_model", "v1_sigmoid")
        use_halo = self._should_use_halo(carrier)

        # ── Get ratings (halo or individual) ──
        off_skill = self._get_offensive_rating(carrier, use_halo)
        def_skill = self._get_defensive_rating(tackler, use_halo)

        if contest_model == "v2_power_ratio":
            # ═══ V2: POWER RATIO ═══
            # success_chance = (carrier_rating / tackler_rating) ** exponent
            # This produces a MULTIPLICATIVE relationship where ratios matter,
            # not absolute differences.  A 90 vs 60 (1.5 ratio) produces very
            # different results from a 60 vs 30 (2.0 ratio).
            exponent = V2_ENGINE_CONFIG.get("power_ratio_exponent", 1.8)

            # Prevent division by zero; floor at 30
            off_eff = max(30.0, off_skill)
            def_eff = max(30.0, def_skill)

            # Power ratio: > 1.0 = offense advantage, < 1.0 = defense wins
            ratio = off_eff / def_eff
            power = ratio ** exponent

            # Convert power ratio to expected yards
            # power 1.0 → ~4.5 yards (even matchup)
            # power 1.5 → ~6.75 yards (offense dominates)
            # power 0.67 → ~2.0 yards (defense dominates)
            base_yards = 4.5 * power

            # Play-type shift
            base_low, base_high = play_config['base_yards']
            play_shift = ((base_low + base_high) / 2.0) - 3.0
            center = base_yards + play_shift

            # Variance: closer matchups = more volatile
            ratio_distance = abs(ratio - 1.0)
            proximity = 1.0 - min(1.0, ratio_distance / 0.5)
            variance = 0.8 + proximity * 1.4

            if self.state.down >= 4:
                # Late-down urgency: anchor toward yards-to-go
                ytg = self.state.yards_to_go
                talent_edge = (power - 1.0) * 2.0  # map power to edge
                buffer = 3.0 + min(3.0, max(-3.0, talent_edge * 3.0))
                urgency = {4: 1.0, 5: 0.82, 6: 0.65}.get(self.state.down, 0.65)
                center = ytg + buffer * urgency + play_shift

        else:
            # ═══ V1: LEGACY SIGMOID ═══
            delta = off_skill - def_skill

            if self.state.down >= 4:
                ytg = self.state.yards_to_go
                off_norm = max(0.0, (off_skill - 50) / 49.0)
                def_norm = max(0.0, (def_skill - 50) / 49.0)
                talent_edge = off_norm - def_norm
                buffer = 3.0 + talent_edge * 3.0
                urgency = {4: 1.0, 5: 0.82, 6: 0.65}.get(self.state.down, 0.65)
                center = ytg + buffer * urgency
            else:
                center = 5.0 + 2.5 * (2.0 / (1.0 + math.exp(-delta / 12.0)) - 1.0)

            base_low, base_high = play_config['base_yards']
            play_shift = ((base_low + base_high) / 2.0) - 3.0
            center += play_shift

            proximity = 1.0 - min(1.0, abs(delta) / 35.0)
            variance = 0.8 + proximity * 1.4

        # ── Coaching gravity adjustments ──
        off_mods = self._coaching_mods()
        def_mods = self._def_coaching_mods()
        hc_cls = off_mods.get("hc_classification", "")
        def_cls = def_mods.get("hc_classification", "")
        cls_fx = off_mods.get("classification_effects", {})
        def_fx = def_mods.get("classification_effects", {})

        if hc_cls == "scheme_master":
            center *= 1.0 + cls_fx.get("scheme_amplification", 0.0)
        elif hc_cls == "motivator":
            variance *= cls_fx.get("composure_amplification", 1.0)
        if def_cls == "disciplinarian":
            variance *= def_fx.get("variance_compression", 1.0)
            center *= (1.0 - def_fx.get("gap_discipline_bonus", 0.0))
        elif def_cls == "scheme_master":
            center *= 1.0 - def_fx.get("scheme_amplification", 0.0) * 0.5

        # ── V2.2: Personality variance modifiers ──
        off_mods_pf = off_mods.get("personality_factors", {})
        var_tol = off_mods_pf.get("variance_tolerance", 1.0)
        variance *= var_tol  # high variance_tolerance = more boom/bust

        # Sub-archetype: emotional motivator increases variance
        sub_fx = off_mods.get("sub_archetype_effects", {})
        variance *= sub_fx.get("variance_multiplier", 1.0)

        # Analyst sub-archetype: slow start Q1 penalty
        if self.state.quarter == 1:
            center *= sub_fx.get("slow_start_penalty", 1.0)

        # ── V2: Composure modifier ──
        if V2_ENGINE_CONFIG.get("composure_enabled", False):
            composure = self._get_current_composure()
            if composure < COMPOSURE_TILT_THRESHOLD:
                # Tilted: awareness drops, variance expands
                center *= 0.85
                variance *= 1.3
            elif composure > 120:
                # Surging: tighter variance, slight boost
                center *= 1.05
                variance *= 0.85

        # ── Drive chain momentum ──
        chain = getattr(self, '_drive_chain_positive', 0)
        if chain >= 3:
            center += min(1.5, chain * 0.3)

        # ── Spread thin (kick-pass floor-spacing) ──
        if getattr(self, '_spread_thin_active', False):
            center += 1.0
            variance *= 0.85

        # ── Hot streak: variance narrows toward high end ──
        streak_bonus, streak_var = self._hot_streak_modifier(carrier)
        center += streak_bonus
        variance *= streak_var

        # ── Weather ──
        center += self.weather_info.get("speed_modifier", 0.0) * 2

        # ── Game rhythm — all coaching rhythm effects flow through here ──
        rhythm = self.home_game_rhythm if self.state.possession == "home" else self.away_game_rhythm
        center *= rhythm

        # ── Roll the dice ──
        yards = random.gauss(center, variance)

        # ── V2: Apply R/E/C variance archetype ──
        yards = self._apply_variance_archetype(yards, carrier)

        # ── V2: Apply star override (performance floor) ──
        yards = self._apply_star_override(yards, carrier)

        return max(-2.0, round(yards, 1))

    def _contest_kick_pass_prob(self, kicker, receiver, def_team) -> float:
        """Contest-based completion probability for kick passes.

        V2: Supports halo mode (team-level resolution for non-stars)
        and power ratio contest model.
        """
        use_halo = self._should_use_halo(kicker)

        if use_halo:
            off_skill = self.get_offensive_team().halo_offense
            off_skill *= self.player_fatigue_modifier(kicker) * 0.5 + 0.5
        else:
            off_skill = kicker.kick_accuracy * 0.6 + receiver.hands * 0.4
            off_skill *= self.player_fatigue_modifier(kicker) * 0.5 + 0.5

        # Average defensive coverage quality
        if use_halo:
            def_coverage = def_team.halo_defense
        else:
            def_players = [p for p in def_team.players
                           if p.position in ("Keeper", "Defensive Line")]
            if not def_players:
                def_players = def_team.players[:5]
            def_coverage = sum(getattr(p, 'awareness', 70) for p in def_players[:5]) / max(1, min(5, len(def_players)))
        # Pick a representative defender for fatigue check
        def_players_list = [p for p in def_team.players if p.position in ("Keeper", "Defensive Line")]
        if not def_players_list:
            def_players_list = def_team.players[:5]
        rep_def = def_players_list[0] if def_players_list else None
        if rep_def:
            def_coverage *= self.player_fatigue_modifier(rep_def) * 0.5 + 0.5

        # Game rhythm — coaching rhythm effects apply to passing too
        rhythm = self.home_game_rhythm if self.state.possession == "home" else self.away_game_rhythm
        off_skill *= rhythm

        contest_model = V2_ENGINE_CONFIG.get("contest_model", "v1_sigmoid")

        if contest_model == "v2_power_ratio":
            # Power ratio for completion probability
            off_eff = max(30.0, off_skill)
            def_eff = max(30.0, def_coverage)
            ratio = off_eff / def_eff
            # Map ratio to probability: ratio 1.0 → ~55%, ratio 1.3 → ~72%
            base_prob = min(0.92, max(0.08, 0.55 * ratio))
        else:
            delta = off_skill - def_coverage
            base_prob = 1.0 / (1.0 + math.exp(-(delta + 5) / 15.0))

        # ── Late-down conversion urgency ──
        # Target ceteris paribus: 4th ~80%, 5th ~73%, 6th ~66%
        # In viperball's 6-down system, offenses focus harder on
        # critical downs.  The urgency boost represents sharper
        # route-running, more decisive kicking, and receiver
        # commitment.  This is the primary lever for hit-rate targets.
        if self.state.down >= 4:
            off_talent = max(0.0, (off_skill - 50) / 49.0)
            # Aggressive urgency: boost completion from ~55% to target
            # 4th: +25% → ~80%, 5th: +18% → ~73%, 6th: +11% → ~66%
            urgency = {4: 0.35, 5: 0.26, 6: 0.18}.get(self.state.down, 0.18)
            base_prob = min(0.92, base_prob + urgency * (0.5 + off_talent * 0.5))

        # ── V2: Composure modifier ──
        if V2_ENGINE_CONFIG.get("composure_enabled", False):
            composure = self._get_current_composure()
            if composure < COMPOSURE_TILT_THRESHOLD:
                base_prob *= 0.85  # Tilted: less accurate
            elif composure > 120:
                base_prob = min(0.92, base_prob * 1.05)

        # Hot streak
        streak_bonus, streak_var = self._hot_streak_modifier(kicker)
        base_prob = min(0.92, base_prob + streak_bonus * 0.05)
        noise_spread = 0.10 * streak_var

        prob = random.gauss(base_prob, noise_spread)
        return max(0.08, min(0.92, prob))

    def _player_skill_roll(self, player, play_type: str = "run") -> float:
        """Skill-weighted dice roll — used for kick pass distance and
        lateral plays where there is no direct attacker-vs-defender
        contest (run plays now use _contest_run_yards instead).
        """
        if play_type == "kick_pass":
            primary = player.kick_accuracy
            secondary = player.kicking
        elif play_type == "lateral":
            primary = player.lateral_skill
            secondary = player.speed
        else:
            primary = player.speed
            secondary = 75

        skill = max(0.0, min(1.0, (primary - 30) / 69))
        support = max(0.0, min(1.0, (secondary - 30) / 69))
        combined = skill * 0.7 + support * 0.3

        center = combined * 3.0
        spread = 0.8 + combined * 0.8

        fatigue_mod = self.player_fatigue_modifier(player)
        center *= fatigue_mod

        roll = random.gauss(center, spread)
        return max(-2.0, round(roll, 1))

    def _tackle_reduction(self, tackler, yards_gained: int) -> float:
        """Tackling skill reduces yards gained on contact.

        Reduction is drawn from a uniform range of 0.56–0.88, scaled
        by the tackler's normalised skill (0.0–1.0).  A 99-rated
        defender shaves 0.56–0.88 yards; a 50-rated one 0.16–0.26.

        If the offense just completed a kick pass ('spread thin'),
        tackle effectiveness is reduced by 30% for one play.
        """
        if yards_gained <= 0:
            return 0.0
        tackle_skill = max(0.0, min(1.0, (tackler.tackling - 30) / 69))
        reduction = random.uniform(0.56, 0.88) * tackle_skill
        # Kick pass floor-spacing: defense spread thin after a completion
        # Widened lanes → tacklers arrive late, weaker angles
        if getattr(self, '_spread_thin_active', False):
            reduction *= 0.55
        # Floor at 0 — tackling can't add yards
        return max(0.0, round(reduction, 1))

    def _calculate_viper_advantage(self, viper_alignment, play_direction):
        dir_map = {'edge': 'right', 'strong': 'left', 'center': 'center', 'weak': 'right'}
        mapped_dir = dir_map.get(play_direction, 'center')
        bonus = VIPER_ALIGNMENT_BONUS.get((viper_alignment, mapped_dir), 0.0)
        bonus += random.uniform(-0.02, 0.02)
        return bonus

    def simulate_run(self, family: PlayFamily = PlayFamily.DIVE_OPTION) -> Play:
        team = self.get_offensive_team()
        config = RUN_PLAY_CONFIG.get(family, RUN_PLAY_CONFIG[PlayFamily.DIVE_OPTION])

        primary_positions = config['primary_positions']
        carrier_weights = config.get('carrier_weights', [])
        archetype_bonus = config.get('archetype_bonus', {})
        skill_pool = self._offense_skill(team)
        eligible = []
        weights = []
        for i, pos in enumerate(primary_positions):
            pos_weight = carrier_weights[i] if i < len(carrier_weights) else 0.3
            for p in skill_pool:
                ptag_check = player_tag(p)
                if pos in ptag_check:
                    w = pos_weight
                    if p.archetype in archetype_bonus:
                        w *= archetype_bonus[p.archetype]
                    # Per-player fatigue: prefer fresh players
                    # Below 40% is the fatigue cliff — AI avoids using them
                    energy_pct = p.game_energy / 100.0
                    if energy_pct < 0.2:
                        w *= 0.10  # Emergency zone — almost never used
                    elif energy_pct < 0.3:
                        w *= 0.25  # Deep cliff — strongly avoid
                    elif energy_pct < 0.4:
                        w *= 0.40  # Cliff zone — significant penalty
                    elif energy_pct < 0.5:
                        w *= 0.60
                    elif energy_pct < 0.7:
                        w *= 0.80
                    if p not in eligible:
                        eligible.append(p)
                        weights.append(max(0.05, w))
        if not eligible:
            eligible = skill_pool[:5]
            weights = [1.0] * len(eligible)

        # ── V2: Hero Ball force-feed ──
        # If hero ball is active, massively boost the star's selection weight
        team_side = self.state.possession
        hero_target = self._check_hero_ball(team_side)
        if hero_target:
            # V2.2: Player trust personality boosts star targeting
            off_mods = self._coaching_mods()
            trust = off_mods.get("personality_factors", {}).get("player_trust", 1.0)
            star_mult = off_mods.get("hidden_trait_effects", {}).get("star_touch_bias", 1.0)
            hero_weight = 5.0 * trust * star_mult
            for i, p in enumerate(eligible):
                if p.name == hero_target:
                    weights[i] *= hero_weight
                    break

        player = random.choices(eligible, weights=weights, k=1)[0]
        plabel = player_label(player)
        ptag = player_tag(player)
        player.game_touches += 1
        action = config['action']

        viper_align = self._determine_viper_alignment()
        play_dir = PLAY_DIRECTION.get(family.value, "center")
        viper_bonus = self._calculate_viper_advantage(viper_align, play_dir)

        def_align = self._determine_defense_alignment()
        def_align_mod = ALIGNMENT_VS_PLAY.get((def_align, family.value), 0.0)

        fp = self.state.field_position

        # Safety check — pinned deep in own territory
        safety_chance = 0.0
        if self.state.field_position <= 2:
            safety_chance = 0.10
        elif self.state.field_position <= 5:
            safety_chance = 0.06
        elif self.state.field_position <= 10:
            safety_chance = 0.03
        elif self.state.field_position <= 15:
            safety_chance = 0.015
        if safety_chance > 0 and random.random() < safety_chance:
            self.change_possession()
            self.add_score(2)
            self.change_possession()
            self.apply_stamina_drain(3)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            self.state.field_position = 20
            self.state.down = 1
            self.state.yards_to_go = 20
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=self.state.down,
                yards_to_go=self.state.yards_to_go,
                play_type="run",
                play_family=family.value,
                players_involved=[plabel],
                yards_gained=-self.state.field_position,
                result=PlayResult.SAFETY.value,
                description=f"{ptag} {action} → swarmed in own end zone — SAFETY! (+2 defensive) [VP {viper_align}, DEF {def_align}]",
                fatigue=round(stamina, 1),
            )

        # ── Contest-based stochastic resolution ──
        # Carrier vs Tackler — their attributes COMPETE, dice decide
        def_team_for_tackle = self.get_defensive_team()
        tackler = self._pick_def_tackler(def_team_for_tackle, 3)  # pick before knowing yards
        tackler.game_tackles += 1

        yards_gained = int(self._contest_run_yards(player, tackler, config))
        yards_gained = max(-5, yards_gained)

        # ── V2: Defensive keying penalty ──
        key_mod = self._apply_defensive_keying(player, team_side)
        if key_mod < 1.0:
            yards_gained = int(yards_gained * key_mod)

        if yards_gained <= 0:
            tackler.game_tfl += 1

        keeper_detail = ""
        sig_detail = ""
        was_explosive = False

        # Breakaway check — good plays can become great plays
        yards_gained = self._breakaway_check(yards_gained, team, family=family)

        # Update hot streak: positive yards = successful contest
        self._update_player_streak(player, yards_gained > 0)
        self._update_player_streak(tackler, yards_gained <= 0)

        # Drain energy from ball carrier and tackler
        self.drain_player_energy(player, "carrier")
        self.drain_player_energy(tackler, "tackler")

        fumble_family = family
        if family == PlayFamily.VIPER_JET:
            vj_config = dict(config)
            vj_config['fumble_rate'] = config['fumble_rate'] * 1.40

        if self._run_fumble_check(family, yards_gained, carrier=player):
            fumble_yards = random.randint(-3, max(1, yards_gained))
            old_pos = self.state.field_position
            fumble_spot = max(1, old_pos + fumble_yards)
            player.game_fumbles += 1
            recovered_by, is_bell = self._resolve_fumble_recovery(fumble_spot, player)

            desc_parts = [f"VP {viper_align}"]
            if def_align != "balanced":
                desc_parts.append(f"DEF {def_align}")
            if sig_detail:
                desc_parts.append(sig_detail)
            mech_tag = f" [{', '.join(desc_parts)}]" if desc_parts else ""
            weather_tag = f" [{self.weather_info['label']}]" if self.weather != "clear" else ""

            if recovered_by == 'defense':
                self.change_possession()
                self.state.field_position = max(1, 100 - fumble_spot)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.add_score(0.5)
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1, yards_to_go=20,
                    play_type="run", play_family=family.value,
                    players_involved=[plabel],
                    yards_gained=fumble_yards,
                    result=PlayResult.FUMBLE.value,
                    description=f"{ptag} {action} → {fumble_yards} — FUMBLE! Defense recovers — BELL (+½){mech_tag}{weather_tag}",
                    fatigue=round(stamina, 1),
                    fumble=True,
                )
            else:
                self.state.field_position = max(1, fumble_spot)
                self.state.down += 1
                self.state.yards_to_go = max(1, self.state.yards_to_go - max(0, fumble_yards))
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                if self.state.down > 6:
                    self.change_possession()
                    self.state.field_position = 100 - self.state.field_position
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1, yards_to_go=20,
                        play_type="run", play_family=family.value,
                        players_involved=[plabel],
                        yards_gained=fumble_yards,
                        result=PlayResult.TURNOVER_ON_DOWNS.value,
                        description=f"{ptag} {action} → FUMBLE recovered by offense but TURNOVER ON DOWNS{mech_tag}",
                        fatigue=round(stamina, 1),
                        fumble=True,
                    )
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=self.state.down, yards_to_go=self.state.yards_to_go,
                    play_type="run", play_family=family.value,
                    players_involved=[plabel],
                    yards_gained=max(0, fumble_yards),
                    result=PlayResult.GAIN.value,
                    description=f"{ptag} {action} → FUMBLE recovered by offense at {self.state.field_position}{mech_tag}",
                    fatigue=round(stamina, 1),
                    fumble=True,
                )

        new_position = min(100, self.state.field_position + yards_gained)

        desc_parts = []
        if viper_bonus >= 0.08:
            desc_parts.append(f"VP {viper_align} pulls D")
        if def_align != "balanced":
            desc_parts.append(f"vs {def_align} D")
        if sig_detail:
            desc_parts.append(sig_detail)
        if keeper_detail:
            desc_parts.append(keeper_detail)
        if was_explosive:
            desc_parts.append("EXPLOSIVE")
        mech_tag = f" [{', '.join(desc_parts)}]" if desc_parts else ""

        if new_position <= 0:
            self.change_possession()
            self.add_score(2)
            self.change_possession()
            self.apply_stamina_drain(3)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            self.state.field_position = 20
            self.state.down = 1
            self.state.yards_to_go = 20
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=self.state.down,
                yards_to_go=self.state.yards_to_go,
                play_type="run",
                play_family=family.value,
                players_involved=[plabel],
                yards_gained=yards_gained,
                result=PlayResult.SAFETY.value,
                description=f"{ptag} {action} → tackled in end zone — SAFETY! (+2 defensive){mech_tag}",
                fatigue=round(stamina, 1),
            )

        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            player.game_tds += 1
            player.game_rushing_tds += 1
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained} — TOUCHDOWN!{mech_tag}"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained} — FIRST DOWN{mech_tag}"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained}{mech_tag}"
            if self.state.down > 6:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

        # In-game injury checks on ball carrier and tackler
        injury_note = ""
        carrier_inj = self.check_in_game_injury(player, play_type="run")
        if carrier_inj:
            injury_note += f" | {carrier_inj.narrative}"
        tackler_inj = self.check_defender_injury(tackler, play_type="tackle")
        if tackler_inj:
            injury_note += f" | {tackler_inj.narrative}"

        self.apply_stamina_drain(3)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="run",
            play_family=family.value,
            players_involved=[plabel],
            yards_gained=yards_gained,
            result=result.value,
            description=description + injury_note,
            fatigue=round(stamina, 1),
            play_signature=sig_detail,
        )

    def simulate_trick_play(self, family: PlayFamily = PlayFamily.TRICK_PLAY) -> Play:
        """Simulate a trick play — high-risk/high-reward misdirection.

        Trick plays disguise the true ball carrier or play direction. They include:
        - Halfback kick (HB takes handoff then kicks downfield)
        - Viper reverse (ball handed off, reversed to Viper going opposite way)
        - Flea flicker (handoff → pitch back to ZB who kicks)
        - Double reverse (two direction changes before the runner goes)
        - Statue of Liberty (fake kick setup, trailing back takes it)

        Integration: Called from simulate_play() when PlayFamily.TRICK_PLAY is selected.
        The play family weight is set in OFFENSE_STYLES (3-7% depending on style).
        Defense counters via play_family_modifiers["trick_play"] in DEFENSE_STYLES.
        """
        team = self.get_offensive_team()
        style = self._current_style()

        # Pick the trick play variant
        trick_variants = [
            {"name": "halfback_kick", "action": "HB kick", "positions": ["HB", "SB"], "fumble_rate": 0.015, "base_yards": (2.0, 4.0), "variance": 1.4},
            {"name": "viper_reverse", "action": "viper reverse", "positions": ["VP", "WB"], "fumble_rate": 0.018, "base_yards": (2.0, 4.5), "variance": 1.5},
            {"name": "flea_flicker", "action": "flea flicker", "positions": ["ZB", "HB"], "fumble_rate": 0.018, "base_yards": (2.0, 4.0), "variance": 1.4},
            {"name": "double_reverse", "action": "double reverse", "positions": ["WB", "HB", "VP"], "fumble_rate": 0.020, "base_yards": (2.5, 5.0), "variance": 1.6},
            {"name": "statue_of_liberty", "action": "statue of liberty", "positions": ["HB", "SB", "ZB"], "fumble_rate": 0.015, "base_yards": (2.0, 4.0), "variance": 1.4},
        ]
        variant = random.choice(trick_variants)

        # Select primary ball carrier from eligible positions
        skill_pool = self._offense_skill(team)
        eligible = []
        for p in skill_pool:
            ptag_check = player_tag(p)
            if any(pos in ptag_check for pos in variant["positions"]):
                eligible.append(p)
        if not eligible:
            eligible = skill_pool[:5]
        carrier = random.choice(eligible)
        plabel = player_label(carrier)
        ptag = player_tag(carrier)
        carrier.game_touches += 1

        # Pick a secondary player involved in the trick
        secondary_pool = [p for p in skill_pool if p != carrier]
        secondary = random.choice(secondary_pool) if secondary_pool else carrier
        sec_tag = player_tag(secondary)

        # Base yardage calculation
        base_min, base_max = variant["base_yards"]
        base_center = random.uniform(base_min, base_max)
        base_yards = random.gauss(base_center, variant["variance"])

        # Carrier skill roll
        skill_bonus = self._player_skill_roll(carrier, play_type="run")
        base_yards += skill_bonus

        # Defensive read check — if defense reads the trick, it's a disaster
        defense = self._current_defense()
        read_rate = defense.get("read_success_rate", 0.35)
        trick_read_bonus = defense.get("gameplan_bias", {}).get("trick_play", 0.05)
        defense_read = random.random() < (read_rate + trick_read_bonus)

        if defense_read:
            # Defense blew it up — big loss
            base_yards = random.uniform(-8.0, -2.0)

        yards_gained = int(base_yards)
        yards_gained = max(-10, yards_gained)

        # Breakaway check on trick plays (only if defense didn't read it)
        if not defense_read:
            yards_gained = self._breakaway_check(yards_gained, team, family=family)

        was_explosive = False

        # Fumble check — trick plays involve extra ball handling
        fumble_rate = variant["fumble_rate"]
        fumble_rate += self.weather_info.get("fumble_modifier", 0.0)
        if defense_read:
            fumble_rate *= 1.5  # more likely to fumble when defense reads it

        fp = self.state.field_position

        if random.random() < fumble_rate:
            fumble_yards = random.randint(-3, max(1, yards_gained))
            fumble_spot = max(1, fp + fumble_yards)
            carrier.game_fumbles += 1
            recovered_by, is_bell = self._resolve_fumble_recovery(fumble_spot, carrier)

            if recovered_by == 'defense':
                self.change_possession()
                self.state.field_position = max(1, 100 - fumble_spot)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.add_score(0.5)
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1, yards_to_go=20,
                    play_type="trick_play", play_family=family.value,
                    players_involved=[plabel, player_label(secondary)],
                    yards_gained=fumble_yards,
                    result=PlayResult.FUMBLE.value,
                    description=f"{ptag} {variant['action']} via {sec_tag} → {fumble_yards} — FUMBLE! Defense recovers — BELL (+½)",
                    fatigue=round(stamina, 1),
                    fumble=True,
                )
            else:
                self.state.field_position = max(1, fumble_spot)
                self.state.down += 1
                self.state.yards_to_go = max(1, self.state.yards_to_go - max(0, fumble_yards))
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                if self.state.down > 6:
                    self.change_possession()
                    self.state.field_position = 100 - self.state.field_position
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1, yards_to_go=20,
                        play_type="trick_play", play_family=family.value,
                        players_involved=[plabel, player_label(secondary)],
                        yards_gained=fumble_yards,
                        result=PlayResult.TURNOVER_ON_DOWNS.value,
                        description=f"{ptag} {variant['action']} via {sec_tag} → FUMBLE recovered by offense but TURNOVER ON DOWNS",
                        fatigue=round(stamina, 1),
                        fumble=True,
                    )
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=self.state.down, yards_to_go=self.state.yards_to_go,
                    play_type="trick_play", play_family=family.value,
                    players_involved=[plabel, player_label(secondary)],
                    yards_gained=max(0, fumble_yards),
                    result=PlayResult.GAIN.value,
                    description=f"{ptag} {variant['action']} via {sec_tag} → FUMBLE recovered by offense at {self.state.field_position}",
                    fatigue=round(stamina, 1),
                    fumble=True,
                )

        # Normal outcome resolution
        new_position = min(100, fp + yards_gained)

        desc_parts = []
        if defense_read:
            desc_parts.append("DEFENSE READ")
        if was_explosive:
            desc_parts.append("EXPLOSIVE")
        mech_tag = f" [{', '.join(desc_parts)}]" if desc_parts else ""

        # Safety check
        if new_position <= 0:
            self.change_possession()
            self.add_score(2)
            self.change_possession()
            self.apply_stamina_drain(3)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            self.state.field_position = 20
            self.state.down = 1
            self.state.yards_to_go = 20
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=self.state.down, yards_to_go=self.state.yards_to_go,
                play_type="trick_play", play_family=family.value,
                players_involved=[plabel, player_label(secondary)],
                yards_gained=yards_gained,
                result=PlayResult.SAFETY.value,
                description=f"{ptag} {variant['action']} via {sec_tag} → tackled in end zone — SAFETY! (+2 defensive){mech_tag}",
                fatigue=round(stamina, 1),
            )

        # Touchdown / first down / gain resolution
        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - fp
            self.add_score(9)
            carrier.game_tds += 1
            carrier.game_rushing_tds += 1
            carrier.game_yards += yards_gained
            carrier.game_rushing_yards += yards_gained
            description = f"{ptag} {variant['action']} via {sec_tag} → {yards_gained} — TOUCHDOWN!{mech_tag}"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            carrier.game_yards += yards_gained
            carrier.game_rushing_yards += yards_gained
            description = f"{ptag} {variant['action']} via {sec_tag} → {yards_gained} — FIRST DOWN{mech_tag}"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            carrier.game_yards += yards_gained
            carrier.game_rushing_yards += yards_gained
            description = f"{ptag} {variant['action']} via {sec_tag} → {yards_gained}{mech_tag}"
            if self.state.down > 6:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

        # Tackling and injury
        def_team = self.get_defensive_team()
        tackler = self._pick_def_tackler(def_team, yards_gained)
        tackler.game_tackles += 1

        # Tackling reduces trick play yards
        trick_tackle_red = self._tackle_reduction(tackler, yards_gained)
        yards_gained = max(-5, int(yards_gained - trick_tackle_red))

        if yards_gained <= 0:
            tackler.game_tfl += 1

        injury_note = ""
        carrier_inj = self.check_in_game_injury(carrier, play_type="run")
        if carrier_inj:
            injury_note += f" | {carrier_inj.narrative}"
        tackler_inj = self.check_defender_injury(tackler, play_type="tackle")
        if tackler_inj:
            injury_note += f" | {tackler_inj.narrative}"

        self.apply_stamina_drain(3)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="trick_play",
            play_family=family.value,
            players_involved=[plabel, player_label(secondary)],
            yards_gained=yards_gained,
            result=result.value,
            description=description + injury_note,
            fatigue=round(stamina, 1),
        )

    def simulate_lateral_chain(self, family: PlayFamily = PlayFamily.LATERAL_SPREAD) -> Play:
        team = self.get_offensive_team()
        style = self._current_style()

        chain_length = random.randint(2, 5)
        skill_pool = self._offense_skill(team)
        players_involved = random.sample(skill_pool, min(chain_length, len(skill_pool)))
        chain_tags = " → ".join(player_tag(p) for p in players_involved)
        chain_labels = [player_label(p) for p in players_involved]

        # ── Lateral interception check ──
        # Defenders can read the lateral and pick it off.
        # 3% base per lateral in the chain, modified by defender awareness
        # vs thrower lateral skill. Conservative start to avoid "lateral extinction."
        def_team = self.get_defensive_team()
        avg_def_awareness = sum(getattr(p, 'awareness', 70) for p in def_team.players[:6]) / 6
        for lat_idx in range(chain_length):
            thrower = players_involved[lat_idx] if lat_idx < len(players_involved) else players_involved[-1]
            thrower_skill = getattr(thrower, 'lateral_skill', 70)
            int_chance = 0.005 * (1 + (avg_def_awareness - 70) / 100) * (1 - (thrower_skill - 70) / 200)
            int_chance = max(0.001, min(0.015, int_chance))
            if random.random() < int_chance:
                # Lateral intercepted — turnover at the interception spot
                int_spot = self.state.field_position + random.randint(0, 3)
                self.change_possession()
                raw_fp = max(1, 100 - int_spot)

                # Pick the interceptor
                int_candidates = def_team.players[:6]
                int_weights = [getattr(p, 'awareness', 70) + p.speed for p in int_candidates]
                interceptor = random.choices(int_candidates, weights=int_weights, k=1)[0]
                interceptor.game_lateral_interceptions += 1
                int_tag = player_tag(interceptor)

                # Explosive INT return — laterals intercepted in the open
                # field often lead to big returns or pick-sixes.
                int_speed = interceptor.speed
                int_agility = getattr(interceptor, 'agility', 75)
                return_talent = (int_speed * 0.6 + int_agility * 0.4 - 60) / 40
                return_yards = max(0, int(random.gauss(30 + return_talent * 20, 12)))
                new_fp = min(100, raw_fp + return_yards)

                self.apply_stamina_drain(4)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                if new_fp >= 100:
                    # Pick-six from lateral interception
                    self.state.field_position = 25
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.add_score(9)
                    interceptor.game_tds += 1
                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1,
                        yards_to_go=20,
                        play_type="lateral_chain",
                        play_family=family.value,
                        players_involved=chain_labels,
                        yards_gained=0,
                        result=PlayResult.INT_RETURN_TD.value,
                        description=f"{chain_tags} lateral — INTERCEPTED by {int_tag}! Returned {return_yards} for TOUCHDOWN!",
                        fatigue=round(stamina, 1),
                        laterals=chain_length,
                    )
                else:
                    self.state.field_position = new_fp
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1,
                        yards_to_go=20,
                        play_type="lateral_chain",
                        play_family=family.value,
                        players_involved=chain_labels,
                        yards_gained=0,
                        result=PlayResult.LATERAL_INTERCEPTED.value,
                        description=f"{chain_tags} lateral — INTERCEPTED by {int_tag}! Returned {return_yards} yds to the {new_fp}",
                        fatigue=round(stamina, 1),
                        laterals=chain_length,
                    )

        # ── Lateral fumble check ──
        base_lateral_fumble = 0.08
        fumble_prob = base_lateral_fumble + (chain_length - 2) * 0.04
        fumble_prob += self.weather_info.get("lateral_fumble_modifier", 0.0)

        lateral_success_bonus = style.get("lateral_success_bonus", 0.0)
        fumble_prob *= (1 - lateral_success_bonus)
        fumble_prob *= style.get("lateral_risk", 1.0)
        fumble_prob = max(0.05, min(0.40, fumble_prob))

        if random.random() < fumble_prob:
            yards_gained = random.randint(-5, 8)
            old_pos = self.state.field_position

            fumbler = random.choice(players_involved)
            fumbler.game_fumbles += 1

            recovered_by, is_bell = self._resolve_fumble_recovery(self.state.field_position, fumbler)

            if recovered_by == 'defense':
                self.change_possession()
                self.state.field_position = max(1, 100 - old_pos)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.add_score(0.5)

                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1,
                    yards_to_go=20,
                    play_type="lateral_chain",
                    play_family=family.value,
                    players_involved=chain_labels,
                    yards_gained=yards_gained,
                    result=PlayResult.FUMBLE.value,
                    description=f"{chain_tags} lateral → FUMBLE by {player_tag(fumbler)}! Defense recovers — BELL (+½)",
                    fatigue=round(stamina, 1),
                    laterals=chain_length,
                    fumble=True,
                )
            else:
                recovery_yds = random.randint(-2, max(0, yards_gained))
                fumble_spot = max(1, old_pos + recovery_yds)
                self.state.field_position = fumble_spot
                self.state.down += 1
                self.state.yards_to_go = max(1, self.state.yards_to_go - max(0, recovery_yds))

                if self.state.down > 6:
                    self.change_possession()
                    self.state.field_position = 100 - self.state.field_position
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1, yards_to_go=20,
                        play_type="lateral_chain",
                        play_family=family.value,
                        players_involved=chain_labels,
                        yards_gained=0,
                        result=PlayResult.TURNOVER_ON_DOWNS.value,
                        description=f"{chain_tags} lateral → FUMBLE recovered by offense but TURNOVER ON DOWNS",
                        fatigue=round(stamina, 1),
                        laterals=chain_length,
                        fumble=True,
                    )

                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=self.state.down,
                    yards_to_go=self.state.yards_to_go,
                    play_type="lateral_chain",
                    play_family=family.value,
                    players_involved=chain_labels,
                    yards_gained=max(0, recovery_yds),
                    result=PlayResult.GAIN.value,
                    description=f"{chain_tags} lateral → FUMBLE recovered by offense at {self.state.field_position}",
                    fatigue=round(stamina, 1),
                    laterals=chain_length,
                    fumble=True,
                )

        # Drain energy from all lateral participants
        for p in players_involved:
            self.drain_player_energy(p, "lateral")

        base_yards = random.gauss(2.5, 1.2)
        lateral_bonus = chain_length * 0.8

        # Skill roll from the final ball carrier (lateral skill matters)
        ball_carrier_for_roll = players_involved[-1] if players_involved else None
        if ball_carrier_for_roll:
            skill_bonus = self._player_skill_roll(ball_carrier_for_roll, play_type="lateral")
            base_yards += skill_bonus

        # Late-down urgency: lateral chains target what the team needs
        if self.state.down >= 4:
            ytg = self.state.yards_to_go
            urgency_boost = {4: 2.5, 5: 1.8, 6: 1.2}.get(self.state.down, 1.2)
            base_yards += urgency_boost

        yards_gained = int(base_yards + lateral_bonus)
        yards_gained = max(-5, yards_gained)

        lat_def_team = self.get_defensive_team()
        lat_tackler = self._pick_def_tackler(lat_def_team, yards_gained)
        lat_tackler.game_tackles += 1

        # Tackling reduces lateral chain yards
        lat_tackle_red = self._tackle_reduction(lat_tackler, yards_gained)
        yards_gained = max(-5, int(yards_gained - lat_tackle_red))

        if yards_gained <= 0:
            lat_tackler.game_tfl += 1

        # Breakaway check on lateral chains
        yards_gained = self._breakaway_check(yards_gained, team)

        new_position = min(100, self.state.field_position + yards_gained)

        for p in players_involved:
            p.game_touches += 1
        for i, p in enumerate(players_involved):
            if i < len(players_involved) - 1:
                p.game_laterals_thrown += 1
                p.game_lateral_assists += 1
            if i > 0:
                p.game_lateral_receptions += 1
        ball_carrier = players_involved[-1]

        is_td = new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team)
        if is_td:
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            ball_carrier.game_tds += 1
            ball_carrier.game_lateral_tds += 1
            ball_carrier.game_yards += yards_gained
            ball_carrier.game_lateral_yards += yards_gained
            description = f"{chain_tags} lateral → {yards_gained} — TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            ball_carrier.game_yards += yards_gained
            ball_carrier.game_lateral_yards += yards_gained
            description = f"{chain_tags} lateral → {yards_gained} — FIRST DOWN"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            ball_carrier.game_yards += yards_gained
            ball_carrier.game_lateral_yards += yards_gained
            description = f"{chain_tags} lateral → {yards_gained}"

            if self.state.down > 6:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

        # In-game injury check on ball carrier and tackler
        injury_note = ""
        carrier_inj = self.check_in_game_injury(ball_carrier, play_type="lateral")
        if carrier_inj:
            injury_note += f" | {carrier_inj.narrative}"
        tackler_inj = self.check_defender_injury(lat_tackler, play_type="tackle")
        if tackler_inj:
            injury_note += f" | {tackler_inj.narrative}"

        self.apply_stamina_drain(5)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="lateral_chain",
            play_family=family.value,
            players_involved=chain_labels,
            yards_gained=yards_gained,
            result=result.value,
            description=description + injury_note,
            fatigue=round(stamina, 1),
            laterals=chain_length,
        )

    def simulate_kick_pass(self, family: PlayFamily = PlayFamily.KICK_PASS) -> Play:
        team = self.get_offensive_team()
        style = self._current_style()

        kicker_pool = self._kicker_candidates(team)
        kicker = max(kicker_pool, key=lambda p: p.kick_accuracy)
        skill = self._offense_skill(team)
        eligible_receivers = [p for p in skill if p != kicker]
        if not eligible_receivers:
            eligible_receivers = [p for p in skill]
        receiver = max(eligible_receivers, key=lambda p: p.hands + p.speed)

        kicker_tag = player_tag(kicker)
        receiver_tag = player_tag(receiver)
        kicker_lbl = player_label(kicker)
        receiver_lbl = player_label(receiver)

        # Kick distance: base 5-14 + kicker skill roll
        # Kick passes are the engine of drive progression — short, medium,
        # and long-range completions all create opportunities.
        #
        # On late downs (4-6), kickers target what the team needs.
        # The distance biases toward yards_to_go so completions convert.
        if self.state.down >= 4:
            ytg = self.state.yards_to_go
            # Target distance is ~ytg (receiver will add YAC on top)
            target = max(5, min(14, ytg - 2))  # aim short of ytg, YAC covers rest
            kick_distance = random.randint(max(5, target - 2), min(14, target + 3))
        else:
            kick_distance = random.randint(5, 14)
        kick_skill_bonus = self._player_skill_roll(kicker, play_type="kick_pass")
        kick_distance = max(1, int(kick_distance + kick_skill_bonus))

        # ── Contest-based completion probability ──
        # Kicker accuracy + receiver hands vs defensive coverage.
        # Distance penalises longer kicks (harder to place accurately).
        def_team = self.get_defensive_team()
        contest_prob = self._contest_kick_pass_prob(kicker, receiver, def_team)
        # Distance penalty: longer kicks are harder to complete
        distance_penalty = max(0.0, (kick_distance - 8) * 0.02)
        completion_prob = max(0.08, min(0.92, contest_prob - distance_penalty))

        kicker.game_kick_passes_thrown += 1
        kicker.game_touches += 1

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        roll = random.random()
        if roll < completion_prob:
            # Hot streak: kicker completed → streak continues
            self._update_player_streak(kicker, True)
            kicker.game_kick_passes_completed += 1
            receiver.game_kick_pass_receptions += 1
            receiver.game_touches += 1

            # Yards after catch — inversely proportional to air distance
            # Short kicks = lots of space to run (like screen passes)
            # Long kicks = receiver corralled quickly
            # Elite receivers generate breakaway YAC
            receiver_skill = max(0.0, (receiver.speed + getattr(receiver, 'agility', 75)) / 2 - 60) / 40  # 0.0–1.0
            if kick_distance <= 8:
                yac = random.randint(3, 7) + int(receiver_skill * random.randint(1, 5))
            elif kick_distance <= 15:
                yac = random.randint(2, 5) + int(receiver_skill * random.randint(0, 4))
            else:
                yac = random.randint(0, 3) + int(receiver_skill * random.randint(0, 2))

            fumble_on_catch = 0.008
            fumble_on_catch -= (receiver.hands / 100) * 0.004
            fumble_on_catch = max(0.002, fumble_on_catch)

            total_yards = kick_distance + yac

            if random.random() < fumble_on_catch:
                # Fumble on the catch
                receiver.game_fumbles += 1
                fumble_spot = min(99, self.state.field_position + kick_distance)
                recovered_by, is_bell = self._resolve_fumble_recovery(fumble_spot, receiver)

                if recovered_by == 'defense':
                    self.change_possession()
                    self.state.field_position = max(1, 100 - fumble_spot)
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.add_score(0.5)

                    self.apply_stamina_drain(4)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=1,
                        yards_to_go=20,
                        play_type="kick_pass",
                        play_family=family.value,
                        players_involved=[kicker_lbl, receiver_lbl],
                        yards_gained=kick_distance,
                        result=PlayResult.FUMBLE.value,
                        description=f"{kicker_tag} kick pass to {receiver_tag} for {kick_distance} → FUMBLE on catch! Defense recovers — BELL (+½)",
                        fatigue=round(stamina, 1),
                        fumble=True,
                    )
                else:
                    # Offense recovers fumble
                    self.state.field_position = min(99, fumble_spot)
                    self.state.down += 1
                    self.state.yards_to_go = max(1, self.state.yards_to_go - kick_distance)
                    kicker.game_kick_pass_yards += kick_distance

                    if self.state.down > 6:
                        self.change_possession()
                        self.state.field_position = 100 - self.state.field_position
                        self.state.down = 1
                        self.state.yards_to_go = 20

                        self.apply_stamina_drain(4)
                        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                        return Play(
                            play_number=self.state.play_number,
                            quarter=self.state.quarter,
                            time=self.state.time_remaining,
                            possession=self.state.possession,
                            field_position=self.state.field_position,
                            down=1, yards_to_go=20,
                            play_type="kick_pass",
                            play_family=family.value,
                            players_involved=[kicker_lbl, receiver_lbl],
                            yards_gained=kick_distance,
                            result=PlayResult.TURNOVER_ON_DOWNS.value,
                            description=f"{kicker_tag} kick pass to {receiver_tag} → FUMBLE recovered by offense but TURNOVER ON DOWNS",
                            fatigue=round(stamina, 1),
                            fumble=True,
                        )

                    self.apply_stamina_drain(4)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                    return Play(
                        play_number=self.state.play_number,
                        quarter=self.state.quarter,
                        time=self.state.time_remaining,
                        possession=self.state.possession,
                        field_position=self.state.field_position,
                        down=self.state.down,
                        yards_to_go=self.state.yards_to_go,
                        play_type="kick_pass",
                        play_family=family.value,
                        players_involved=[kicker_lbl, receiver_lbl],
                        yards_gained=kick_distance,
                        result=PlayResult.GAIN.value,
                        description=f"{kicker_tag} kick pass to {receiver_tag} for {kick_distance} → FUMBLE recovered by offense",
                        fatigue=round(stamina, 1),
                        fumble=True,
                    )

            # Clean completion — tackling limits YAC
            # Kick pass "floor-spacing": successful completion spreads
            # the defense thin, reducing tackle effectiveness next play
            self._spread_thin_next_play = True
            kp_def_team = self.get_defensive_team()
            kp_tackler = self._pick_def_tackler(kp_def_team, total_yards)
            kp_tackler.game_tackles += 1
            kp_tackle_red = self._tackle_reduction(kp_tackler, total_yards)
            yards_gained = max(1, int(total_yards - kp_tackle_red))
            if yards_gained <= 0:
                kp_tackler.game_tfl += 1

            new_position = min(100, self.state.field_position + yards_gained)
            kicker.game_kick_pass_yards += yards_gained
            receiver.game_yards += yards_gained

            is_td = new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team)
            if is_td:
                result = PlayResult.TOUCHDOWN
                yards_gained = 100 - self.state.field_position
                self.add_score(9)
                receiver.game_tds += 1
                receiver.game_kick_pass_tds = getattr(receiver, 'game_kick_pass_tds', 0) + 1
                kicker.game_kick_pass_tds += 1
                kicker.game_kick_pass_yards += (yards_gained - total_yards)  # adjust for TD
                receiver.game_yards += (yards_gained - total_yards)
                description = f"{kicker_tag} kick pass to {receiver_tag} → {yards_gained} — TOUCHDOWN!"
            elif yards_gained >= self.state.yards_to_go:
                result = PlayResult.FIRST_DOWN
                self.state.field_position = new_position
                self.state.down = 1
                self.state.yards_to_go = 20
                description = f"{kicker_tag} kick pass to {receiver_tag} → {yards_gained} — FIRST DOWN"
            else:
                result = PlayResult.GAIN
                self.state.field_position = new_position
                self.state.down += 1
                self.state.yards_to_go -= yards_gained
                description = f"{kicker_tag} kick pass to {receiver_tag} → {yards_gained}"

                if self.state.down > 6:
                    result = PlayResult.TURNOVER_ON_DOWNS
                    self.change_possession()
                    self.state.field_position = 100 - self.state.field_position
                    description += " — TURNOVER ON DOWNS"

            # In-game injury check on receiver after catch
            injury_note = ""
            recv_inj = self.check_in_game_injury(receiver, play_type="kick_pass")
            if recv_inj:
                injury_note += f" | {recv_inj.narrative}"

            self.apply_stamina_drain(4)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=self.state.down,
                yards_to_go=self.state.yards_to_go,
                play_type="kick_pass",
                play_family=family.value,
                players_involved=[kicker_lbl, receiver_lbl],
                yards_gained=yards_gained,
                result=result.value,
                description=description + injury_note,
                fatigue=round(stamina, 1),
            )

        # Hot streak: kicker missed → streak broken
        self._update_player_streak(kicker, False)

        # Interception: checked on incomplete kicks only.
        # Rare but explosive — when it happens, the defender has open
        # field and a high chance of housing it (pick-six) or getting
        # major return yards.  INTs are high-burst, high-velocity plays.
        # Global rate ≈ P(incomplete) × int_chance ≈ 0.37 × 0.01 ≈ 0.37%.
        int_chance = 0.01

        if random.random() < int_chance:
            kicker.game_kick_pass_interceptions += 1
            int_spot = min(99, self.state.field_position + kick_distance)
            self.change_possession()
            # Field position from the intercepting team's perspective
            raw_fp = max(1, 100 - int_spot)

            def_team = self.get_defensive_team()
            def_candidates = def_team.players[:6]
            int_weights = [p.awareness + p.hands for p in def_candidates]
            interceptor = random.choices(def_candidates, weights=int_weights)[0]
            interceptor.game_kick_pass_ints += 1
            int_tag = player_tag(interceptor)

            # ── Explosive INT return ──
            # Interceptors have open field.  Speed + agility determine
            # return distance.  >60% of INTs should produce a score.
            int_speed = interceptor.speed
            int_agility = getattr(interceptor, 'agility', 75)
            return_talent = (int_speed * 0.6 + int_agility * 0.4 - 60) / 40  # 0–1
            return_yards = max(0, int(random.gauss(30 + return_talent * 20, 12)))
            new_fp = min(100, raw_fp + return_yards)

            if new_fp >= 100:
                # Pick-six!  Interceptor returns it all the way.
                self.state.field_position = 25  # kickoff position after TD
                self.state.down = 1
                self.state.yards_to_go = 20
                self.add_score(9)  # TD for intercepting team
                interceptor.game_tds += 1

                self.apply_stamina_drain(4)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1,
                    yards_to_go=20,
                    play_type="kick_pass",
                    play_family=family.value,
                    players_involved=[kicker_lbl, receiver_lbl],
                    yards_gained=0,
                    result=PlayResult.INT_RETURN_TD.value,
                    description=f"{kicker_tag} kick pass — INTERCEPTED by {int_tag}! Returned {return_yards} yards for a TOUCHDOWN!",
                    fatigue=round(stamina, 1),
                )
            else:
                # INT with return yards — great field position
                self.state.field_position = new_fp
                self.state.down = 1
                self.state.yards_to_go = 20

                self.apply_stamina_drain(4)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1,
                    yards_to_go=20,
                    play_type="kick_pass",
                    play_family=family.value,
                    players_involved=[kicker_lbl, receiver_lbl],
                    yards_gained=0,
                    result=PlayResult.KICK_PASS_INTERCEPTED.value,
                    description=f"{kicker_tag} kick pass — INTERCEPTED by {int_tag}! Returned {return_yards} yards to the {new_fp}",
                    fatigue=round(stamina, 1),
                )

        self.state.down += 1

        description = f"{kicker_tag} kick pass intended for {receiver_tag} — INCOMPLETE"

        if self.state.down > 6:
            result = PlayResult.TURNOVER_ON_DOWNS
            self.change_possession()
            self.state.field_position = 100 - self.state.field_position
            self.state.down = 1
            self.state.yards_to_go = 20
            description += " — TURNOVER ON DOWNS"
        else:
            result = PlayResult.KICK_PASS_INCOMPLETE

        self.apply_stamina_drain(3)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="kick_pass",
            play_family=family.value,
            players_involved=[kicker_lbl, receiver_lbl],
            yards_gained=0,
            result=result.value,
            description=description,
            fatigue=round(stamina, 1),
        )

    def simulate_punt(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        punter = max(self._kicker_candidates(team), key=lambda p: p.kicking)
        ptag = player_tag(punter)

        # ── Fake Punt Check ──────────────────────────────────────────
        # ST scheme determines fake tendency. Chaos Unit fakes 12% of punts.
        kicking_st = self.home_st if self.state.possession == "home" else self.away_st
        fake_rate = kicking_st.get("fake_play_rate", 0.03)
        # Don't fake from your own end zone — too risky
        if self.state.field_position > 15 and random.random() < fake_rate:
            # Fake punt — runner or passer from punt formation
            playmaker = max(team.players[:6],
                            key=lambda p: p.speed * 0.5 + getattr(p, 'agility', 75) * 0.3 + getattr(p, 'hands', 75) * 0.2)
            ftag = player_tag(playmaker)
            # 45% chance of success (first down), 55% turnover on downs
            success_roll = random.random()
            # Offensive style bonus: ghost/chain_gang get small boost
            style_name = self._current_style_name()
            if style_name in ("ghost", "chain_gang", "lateral_spread"):
                success_roll -= 0.08  # Lower = better
            self.apply_stamina_drain(3)
            if success_roll < 0.45:
                # Fake works! Gain 8-22 yards
                fake_gain = random.randint(8, 22)
                self.state.field_position = min(99, self.state.field_position + fake_gain)
                playmaker.game_touches += 1
                playmaker.game_yards += fake_gain
                # Check for TD
                if self.state.field_position >= 100:
                    self.state.field_position = 100
                    playmaker.game_tds += 1
                    self.add_score(9)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="fake_punt", play_family=family.value,
                        players_involved=[player_label(punter), player_label(playmaker)],
                        yards_gained=fake_gain,
                        result="touchdown",
                        description=f"FAKE PUNT! {ftag} takes it {fake_gain} yards — TOUCHDOWN! +9",
                        fatigue=round(stamina, 1),
                    )
                self.state.down = 1
                self.state.yards_to_go = 20
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="fake_punt", play_family=family.value,
                    players_involved=[player_label(punter), player_label(playmaker)],
                    yards_gained=fake_gain,
                    result="first_down",
                    description=f"FAKE PUNT! {ftag} takes it {fake_gain} yards — FIRST DOWN!",
                    fatigue=round(stamina, 1),
                )
            else:
                # Fake fails — turnover on downs
                fake_loss = random.randint(-3, 2)
                self.state.field_position = max(1, self.state.field_position + fake_loss)
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                self.state.down = 1
                self.state.yards_to_go = 20
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="fake_punt", play_family=family.value,
                    players_involved=[player_label(punter), player_label(playmaker)],
                    yards_gained=fake_loss,
                    result="turnover_on_downs",
                    description=f"FAKE PUNT! {ftag} stuffed — TURNOVER ON DOWNS!",
                    fatigue=round(stamina, 1),
                )

        # SPECIAL TEAMS CHAOS: Check for blocked punt FIRST
        block_prob = self.calculate_block_probability(kick_type="punt")
        if random.random() < block_prob:
            # BLOCKED PUNT!
            kicking_team = self.state.possession
            block_distance = random.randint(-8, -2)  # Negative = loss

            # 60% dead at spot, 40% live ball
            if random.random() < 0.60:
                # Dead at spot - defense takes over
                self.change_possession()
                self.state.field_position = max(1, min(99, self.state.field_position + block_distance))
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                def_team = self.get_defensive_team()
                blocker = max(self._defense_players(def_team), key=lambda p: p.speed)
                btag = player_tag(blocker)

                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter), player_label(blocker)],
                    yards_gained=block_distance,
                    result=PlayResult.BLOCKED_PUNT.value,
                    description=f"{ptag} punt BLOCKED by {btag}! Dead at {self.state.field_position}",
                    fatigue=round(stamina, 1),
                )
            else:
                # Live ball - 60% defense, 40% offense recovery
                if random.random() < 0.60:
                    # Defense recovers + bell
                    self.change_possession()
                    self.add_score(0.5)  # Bell for recovery
                    self.state.field_position = max(1, min(99, self.state.field_position + block_distance + random.randint(0, 5)))
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                    def_team = self.get_defensive_team()
                    blocker = max(self._defense_players(def_team), key=lambda p: p.speed)
                    btag = player_tag(blocker)

                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="punt", play_family=family.value,
                        players_involved=[player_label(punter), player_label(blocker)],
                        yards_gained=block_distance,
                        result=PlayResult.BLOCKED_PUNT.value,
                        description=f"{ptag} punt BLOCKED by {btag}! Defense recovers at {self.state.field_position}! (+½)",
                        fatigue=round(stamina, 1),
                    )
                else:
                    # Offense recovers (disaster - terrible field position, no conversion)
                    self.state.field_position = max(1, min(99, self.state.field_position + block_distance))
                    self.change_possession()  # Turnover on downs
                    self.state.field_position = 100 - self.state.field_position  # Flip field
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="punt", play_family=family.value,
                        players_involved=[player_label(punter)],
                        yards_gained=block_distance,
                        result=PlayResult.BLOCKED_PUNT.value,
                        description=f"{ptag} punt BLOCKED! Kicking team recovers but turnover on downs!",
                        fatigue=round(stamina, 1),
                    )

        punt_weather_mod = 1.0 + self.weather_info.get("punt_distance_modifier", 0.0)
        fp = self.state.field_position
        ideal_punt = max(25, min(80, (100 - fp) - random.randint(0, 5)))
        yards_to_endzone = 100 - fp
        if fp <= 20:
            base_distance = random.gauss(62, 12) * punt_weather_mod
        elif fp <= 35:
            base_distance = random.gauss(55, 10) * punt_weather_mod
        elif fp <= 55:
            base_distance = random.gauss(ideal_punt, 6) * punt_weather_mod
        else:
            base_distance = random.gauss(ideal_punt, 8) * punt_weather_mod
        kicking_factor = punter.kicking / 80

        defense = self._current_defense()
        kick_suppression = defense.get("kick_suppression", 1.0)

        distance = int(base_distance * kicking_factor * kick_suppression)
        distance = max(5, distance)

        if random.random() < 0.04:
            tipped_distance = random.randint(5, 15)
            kicking_team_pos = self.state.possession
            self.change_possession()
            self.state.field_position = min(99, self.state.field_position + tipped_distance)
            self.state.down = 1
            self.state.yards_to_go = 20

            if random.random() < 0.12:
                self.change_possession()
                self.state.field_position = min(99, self.state.field_position)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=tipped_distance,
                    result=PlayResult.CHAOS_RECOVERY.value,
                    description=f"{ptag} punt TIPPED! Kicking team recovers at {self.state.field_position}!",
                    fatigue=round(stamina, 1),
                )

            self.apply_stamina_drain(2)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number, quarter=self.state.quarter,
                time=self.state.time_remaining, possession=self.state.possession,
                field_position=self.state.field_position, down=1, yards_to_go=20,
                play_type="punt", play_family=family.value,
                players_involved=[player_label(punter)], yards_gained=tipped_distance,
                result="punt",
                description=f"{ptag} punt TIPPED! {tipped_distance} yards, recovered by defense",
                fatigue=round(stamina, 1),
            )

        if random.random() < 0.07:
            bounce_extra = random.choice([-15, -10, 10, 15, 20, 25])
            distance = max(10, min(distance + bounce_extra, 80))

        landing_position = self.state.field_position + distance

        if landing_position >= 100:
            receiving_team_obj = self.get_defensive_team()
            kicking_team = self.state.possession
            receiving = "away" if kicking_team == "home" else "home"

            is_pindown = self._check_rouge_pindown(receiving_team_obj, kicking_team)

            if not is_pindown:
                self.change_possession()
                self.state.field_position = random.randint(15, 25)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=-distance,
                    result="punt",
                    description=f"{ptag} punt → {distance} yards into end zone, returned out to {self.state.field_position}",
                    fatigue=round(stamina, 1),
                )
            else:
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                play = Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=kicking_team,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=-distance,
                    result=PlayResult.PINDOWN.value,
                    description=f"{ptag} punt → {distance} yards into end zone — PINDOWN! +1",
                    fatigue=round(stamina, 1),
                )
                self._apply_rouge_pindown(kicking_team, receiving)
                return play

        # SPECIAL TEAMS CHAOS: Check for muffed punt return
        muff_prob = self.calculate_muff_probability()
        if random.random() < muff_prob:
            # MUFFED PUNT!
            kicking_team = self.state.possession
            def_team = self.get_defensive_team()
            returner = max(self._offense_skill(def_team), key=lambda p: p.speed * 0.6 + getattr(p, 'hands', 75) * 0.4)
            rtag = player_tag(returner)
            returner.game_muffs += 1
            returner.game_punt_returns += 1

            landing_spot = min(99, self.state.field_position + distance)

            if random.random() < 0.55:
                # Return team recovers but bad field position
                self.change_possession()
                recover_spot = 100 - max(1, landing_spot - random.randint(5, 15))  # Lose yards on muff
                self.state.field_position = max(1, min(99, recover_spot))
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter), player_label(returner)],
                    yards_gained=-distance,
                    result=PlayResult.MUFFED_PUNT.value,
                    description=f"{ptag} punt → {rtag} MUFFED! Returner recovers at {self.state.field_position}",
                    fatigue=round(stamina, 1),
                )
            else:
                # Kicking team recovers! Bell + short field
                # Kicking team gets the ball back
                self.add_score(0.5)  # Bell for recovery
                # Keep possession (don't change), set field position to landing spot
                recover_spot = max(1, min(99, landing_spot + random.randint(0, 5)))
                self.state.field_position = recover_spot
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                # Get kicking team player
                kicker_recoverer = max(self._offense_skill(team), key=lambda p: p.speed)
                ktag = player_tag(kicker_recoverer)

                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter), player_label(kicker_recoverer)],
                    yards_gained=distance,
                    result=PlayResult.MUFFED_PUNT.value,
                    description=f"{ptag} punt → MUFFED! {ktag} recovers for kicking team at {self.state.field_position}! (+½)",
                    fatigue=round(stamina, 1),
                )

        # ── Punt Return TD check — skill-based ─────────────────────
        def_team = self.get_defensive_team()
        punt_team = self.get_offensive_team()
        td_returner = self._pick_returner(def_team)
        base_td_rate = 0.03
        if td_returner:
            # Returner speed bonus: elite speedsters break more
            speed_bonus = 1.0
            if td_returner.speed >= 92:
                speed_bonus = 1.40
            elif td_returner.speed >= 85:
                speed_bonus = 1.20
            # Keeper return_keeper archetype bonus
            archetype_info = get_archetype_info(td_returner.archetype) if td_returner.archetype != "none" else {}
            arch_mod = archetype_info.get("return_yards_modifier", 1.0)
            # ST scheme modifiers
            ret_st = ST_SCHEMES.get(def_team.st_scheme, ST_SCHEMES["aces"])
            punt_st = ST_SCHEMES.get(punt_team.st_scheme, ST_SCHEMES["aces"])
            td_rate = base_td_rate * speed_bonus * arch_mod
            td_rate *= ret_st["return_td_modifier"]
            td_rate /= punt_st["coverage_modifier"]
        else:
            td_rate = base_td_rate

        if random.random() < td_rate and td_returner:
            rtag = player_tag(td_returner)
            td_returner.game_punt_returns += 1
            td_returner.game_punt_return_tds += 1
            new_pos = 100 - min(99, self.state.field_position + distance)
            td_returner.game_punt_return_yards += new_pos
            self.change_possession()
            self.add_score(9)
            self.apply_stamina_drain(2)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number, quarter=self.state.quarter,
                time=self.state.time_remaining, possession=self.state.possession,
                field_position=self.state.field_position, down=1, yards_to_go=20,
                play_type="punt", play_family=family.value,
                players_involved=[player_label(punter), player_label(td_returner)],
                yards_gained=new_pos,
                result=PlayResult.PUNT_RETURN_TD.value,
                description=f"{ptag} punt → {rtag} RETURNS IT ALL THE WAY — TOUCHDOWN! +9",
                fatigue=round(stamina, 1),
            )

        if landing_position >= 93 and landing_position < 100:
            endzone_bounce_prob = 0.35 + (landing_position - 93) * 0.08
            if random.random() < endzone_bounce_prob:
                receiving_team_obj = self.get_defensive_team()
                kicking_team = self.state.possession
                receiving = "away" if kicking_team == "home" else "home"

                is_pindown = self._check_rouge_pindown(receiving_team_obj, kicking_team)

                if not is_pindown:
                    self.change_possession()
                    self.state.field_position = random.randint(15, 25)
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="punt", play_family=family.value,
                        players_involved=[player_label(punter)], yards_gained=-distance,
                        result="punt",
                        description=f"{ptag} punt → {distance} yards, bounces into end zone, returned out to {self.state.field_position}",
                        fatigue=round(stamina, 1),
                    )
                else:
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                    play = Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=kicking_team,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="punt", play_family=family.value,
                        players_involved=[player_label(punter)], yards_gained=-distance,
                        result=PlayResult.PINDOWN.value,
                        description=f"{ptag} punt → {distance} yards — bounces into end zone — PINDOWN! +1",
                        fatigue=round(stamina, 1),
                    )
                    self._apply_rouge_pindown(kicking_team, receiving)
                    return play

        landing_spot = 100 - min(99, self.state.field_position + distance)

        # ── Punt Return Phase ────────────────────────────────────────
        punt_coverage_team = self.get_offensive_team()
        returning_team = self.get_defensive_team()

        returner = self._pick_returner(returning_team)
        return_yards = 0
        returner_desc = ""

        if returner and landing_spot > 5:
            return_yards = self._calculate_punt_return_yards(
                returner, returning_team, punt_coverage_team
            )
            # Can't return past midfield+ without it being a TD (handled above)
            # Ensure we don't go past our own territory unrealistically
            final_position = max(1, landing_spot - return_yards)
            returner.game_punt_returns += 1
            returner.game_punt_return_yards += return_yards
            rtag = player_tag(returner)
            if return_yards > 0:
                returner_desc = f", {rtag} returns {return_yards} yards"
        else:
            final_position = max(1, landing_spot)

        # Coverage unit tackles the returner
        tackler = self._pick_coverage_tackler(punt_coverage_team)
        if tackler and return_yards > 0:
            tackler.game_st_tackles += 1
            tackler.game_coverage_snaps += 1
        # Additional coverage snap for another unit member
        punt_cov_eligible = [p for p in punt_coverage_team.players
                             if p.position in ("Keeper", "Defensive Line") and p != tackler]
        if punt_cov_eligible:
            cov1 = random.choice(punt_cov_eligible)
            cov1.game_coverage_snaps += 1

        self.change_possession()
        self.state.field_position = max(1, final_position)
        self.state.down = 1
        self.state.yards_to_go = 20

        self.apply_stamina_drain(2)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        involved = [player_label(punter)]
        if returner and return_yards > 0:
            involved.append(player_label(returner))

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="punt",
            play_family=family.value,
            players_involved=involved,
            yards_gained=-distance,
            result="punt",
            description=f"{ptag} punt → {distance} yards{returner_desc}",
            fatigue=round(stamina, 1),
        )

    def get_defensive_team(self) -> Team:
        return self.away_team if self.state.possession == "home" else self.home_team

    def simulate_drop_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(self._kicker_candidates(team), key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        # SPECIAL TEAMS CHAOS: Check for blocked kick FIRST
        block_prob = self.calculate_block_probability(kick_type="kick")
        if random.random() < block_prob:
            # BLOCKED KICK!
            def_team = self.get_defensive_team()
            blocker = max(self._defense_players(def_team), key=lambda p: p.speed)
            btag = player_tag(blocker)

            # 70% defense recovers, 30% offense recovers
            if random.random() < 0.70:
                # Defense recovers - chance for return TD or short field
                self.change_possession()
                # Ball is behind LOS
                block_spot = max(1, min(99, self.state.field_position - random.randint(3, 10)))
                self.state.field_position = 100 - block_spot  # Flip for receiving team
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                # 15% chance of return TD
                if random.random() < 0.15:
                    self.add_score(9)
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="drop_kick", play_family=family.value,
                        players_involved=[player_label(kicker), player_label(blocker)],
                        yards_gained=-block_spot,
                        result=PlayResult.BLOCKED_KICK.value,
                        description=f"{ptag} snap kick BLOCKED by {btag}! RETURNED FOR TOUCHDOWN! +9",
                        fatigue=round(stamina, 1),
                    )
                else:
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="drop_kick", play_family=family.value,
                        players_involved=[player_label(kicker), player_label(blocker)],
                        yards_gained=-block_spot,
                        result=PlayResult.BLOCKED_KICK.value,
                        description=f"{ptag} snap kick BLOCKED by {btag}! Defense recovers at {self.state.field_position}",
                        fatigue=round(stamina, 1),
                    )
            else:
                # Offense recovers - treated like failed 4th down
                self.change_possession()
                self.state.field_position = 100 - max(1, self.state.field_position - random.randint(3, 10))
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="drop_kick", play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=0,
                    result=PlayResult.BLOCKED_KICK.value,
                    description=f"{ptag} snap kick BLOCKED! Kicking team recovers but turnover on downs!",
                    fatigue=round(stamina, 1),
                )

        def_team = self.get_defensive_team()
        keeper = None
        for p in def_team.players:
            if p.position == "Keeper":
                keeper = p
                break
        if keeper is None:
            keeper = max(def_team.players[-3:], key=lambda p: p.speed)

        keeper.game_coverage_snaps += 1

        keeper_arch = get_archetype_info(keeper.archetype)
        deflection_base = 0.05
        deflection_base += keeper_arch.get("deflection_bonus", 0.0)
        if keeper.speed >= 90:
            deflection_base += 0.03
        if keeper.tackling >= 80:
            deflection_base += 0.02

        keeper_stamina = keeper.current_stamina if hasattr(keeper, 'current_stamina') else 100.0
        if keeper_stamina < 70:
            deflection_base *= 0.75

        weather_mod = self.weather_info.get("kick_accuracy_modifier", 0.0)
        if weather_mod < -0.05:
            deflection_base += 0.03

        if random.random() < deflection_base:
            keeper.game_kick_deflections += 1
            ktag = player_tag(keeper)
            self.change_possession()
            recover_spot = max(1, min(99, 100 - self.state.field_position + random.randint(-5, 5)))
            self.state.field_position = recover_spot
            self.state.down = 1
            self.state.yards_to_go = 20
            self.add_score(0.5)
            keeper.game_keeper_bells += 1
            self.apply_stamina_drain(3)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            weather_tag = f" [{self.weather_info['label']}]" if self.weather != "clear" else ""
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1, yards_to_go=20,
                play_type="drop_kick",
                play_family=family.value,
                players_involved=[player_label(kicker), player_label(keeper)],
                yards_gained=0,
                result=PlayResult.BLOCKED_KICK.value,
                description=f"{ptag} snap kick — DEFLECTED by Keeper {ktag}! Defense recovers (+½){weather_tag}",
                fatigue=round(stamina, 1),
            )

        distance = 100 - self.state.field_position + 10

        # ── Kicker-range success model ──
        # Uses the same model as _drop_kick_success: the kicker determines
        # a comfortable range.  Within range, kicks are very reliable.
        # Beyond range, success drops off.
        success_prob = self._drop_kick_success(distance, kicker.kicking)

        # Style, archetype, and weather modifiers (secondary adjustments)
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)
        arch_info = get_archetype_info(kicker.archetype)
        kick_arch_bonus = arch_info.get("kick_accuracy_bonus", 0.0)
        weather_kick_mod = self.weather_info.get("kick_accuracy_modifier", 0.0)
        success_prob *= (1.0 + kick_acc + kick_arch_bonus + weather_kick_mod)
        success_prob = max(0.05, min(0.98, success_prob))
        kicker.game_kick_attempts += 1
        kicker.game_dk_attempts += 1

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(5)
            kicker.game_kick_makes += 1
            kicker.game_dk_makes += 1
            weather_tag = f" [{self.weather_info['label']}]" if self.weather != "clear" else ""

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="drop_kick",
                play_family=family.value,
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{ptag} snap kick {distance}yd — GOOD! +5{weather_tag}",
                fatigue=round(stamina, 1),
            )
        else:
            landing_offset = random.randint(5, 15)
            ball_landing = self.state.field_position + landing_offset
            kicking_team = self.state.possession
            receiving = "away" if kicking_team == "home" else "home"

            # ── Finnish baseball rule: missed kick on downs 4-5 retains possession ──
            # The kicking team keeps the ball and advances to the next down.
            # This makes snap kick attempts on 4th/5th essentially risk-free.
            if self.state.down <= 5:
                original_ytg = self.state.yards_to_go
                if ball_landing >= 100:
                    # Ball went past end zone — retain at current position
                    landing_spot = self.state.field_position
                    yards_forward = 0
                else:
                    landing_spot = min(99, ball_landing)
                    yards_forward = max(0, landing_spot - self.state.field_position)
                self.state.field_position = landing_spot
                if yards_forward >= original_ytg:
                    self.state.down = 1
                    self.state.yards_to_go = 20
                else:
                    self.state.down += 1
                    self.state.yards_to_go = max(1, original_ytg - yards_forward)
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=self.state.down,
                    yards_to_go=self.state.yards_to_go,
                    play_type="drop_kick",
                    play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=yards_forward,
                    result=PlayResult.SNAP_KICK_RECOVERY.value,
                    description=f"{ptag} snap kick {distance}yd — NO GOOD → retained possession (down {self.state.down})",
                    fatigue=round(stamina, 1),
                )

            # ── Down 6: traditional miss logic (possession at risk) ──
            recovery_chance = 0.35
            if kicker.archetype == "kicking_zb":
                recovery_chance = 0.40

            if ball_landing >= 100:
                receiving_team_obj = self.get_defensive_team()
                is_pindown = self._check_rouge_pindown(receiving_team_obj, kicking_team)

                if is_pindown:
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                    play = Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=kicking_team,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="drop_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.PINDOWN.value,
                        description=f"{ptag} snap kick {distance}yd — NO GOOD, into the end zone — PINDOWN! +1",
                        fatigue=round(stamina, 1),
                    )
                    self._apply_rouge_pindown(kicking_team, receiving)
                    return play
                else:
                    self.change_possession()
                    self.state.field_position = random.randint(15, 25)
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="drop_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.MISSED_KICK.value,
                        description=f"{ptag} snap kick {distance}yd — NO GOOD, returned out of end zone to {self.state.field_position}",
                        fatigue=round(stamina, 1),
                    )

            if random.random() < recovery_chance:
                landing_spot = min(99, ball_landing)
                self.state.field_position = landing_spot
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(3)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1,
                    yards_to_go=20,
                    play_type="drop_kick",
                    play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=landing_offset,
                    result=PlayResult.SNAP_KICK_RECOVERY.value,
                    description=f"{ptag} snap kick {distance}yd — NO GOOD → LIVE BALL! Kicking team recovers at {landing_spot}!",
                    fatigue=round(stamina, 1),
                )
            else:
                self.change_possession()
                self.add_score(0.5)
                landing_spot = max(1, ball_landing)
                self.state.field_position = max(1, 100 - landing_spot)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=1,
                    yards_to_go=20,
                    play_type="drop_kick",
                    play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=0,
                    result=PlayResult.MISSED_KICK.value,
                    description=f"{ptag} snap kick {distance}yd — NO GOOD → LIVE BALL! Defense recovers (+½)",
                    fatigue=round(stamina, 1),
                )

    def simulate_place_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(self._kicker_candidates(team), key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        # SPECIAL TEAMS CHAOS: Check for blocked kick FIRST
        block_prob = self.calculate_block_probability(kick_type="kick")
        if random.random() < block_prob:
            # BLOCKED KICK!
            def_team = self.get_defensive_team()
            blocker = max(self._defense_players(def_team), key=lambda p: p.speed)
            btag = player_tag(blocker)

            # 70% defense recovers, 30% offense recovers
            if random.random() < 0.70:
                # Defense recovers - chance for return TD or short field
                self.change_possession()
                # Ball is behind LOS
                block_spot = max(1, min(99, self.state.field_position - random.randint(3, 10)))
                self.state.field_position = 100 - block_spot  # Flip for receiving team
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                # 15% chance of return TD
                if random.random() < 0.15:
                    self.add_score(9)
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="place_kick", play_family=family.value,
                        players_involved=[player_label(kicker), player_label(blocker)],
                        yards_gained=-block_spot,
                        result=PlayResult.BLOCKED_KICK.value,
                        description=f"{ptag} place kick BLOCKED by {btag}! RETURNED FOR TOUCHDOWN! +9",
                        fatigue=round(stamina, 1),
                    )
                else:
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="place_kick", play_family=family.value,
                        players_involved=[player_label(kicker), player_label(blocker)],
                        yards_gained=-block_spot,
                        result=PlayResult.BLOCKED_KICK.value,
                        description=f"{ptag} place kick BLOCKED by {btag}! Defense recovers at {self.state.field_position}",
                        fatigue=round(stamina, 1),
                    )
            else:
                # Offense recovers - treated like failed 4th down
                self.change_possession()
                self.state.field_position = 100 - max(1, self.state.field_position - random.randint(3, 10))
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="place_kick", play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=0,
                    result=PlayResult.BLOCKED_KICK.value,
                    description=f"{ptag} place kick BLOCKED! Kicking team recovers but turnover on downs!",
                    fatigue=round(stamina, 1),
                )

        distance = 100 - self.state.field_position + 10

        # ── Kicker-range success model ──
        # Uses the same model as _place_kick_success: the kicker determines
        # a comfortable range.  Within range, kicks are near-automatic.
        # Beyond range, success drops off.
        success_prob = self._place_kick_success(distance, kicker.kicking)

        # Style, archetype, and weather modifiers (secondary adjustments)
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)
        arch_info = get_archetype_info(kicker.archetype)
        kick_arch_bonus = arch_info.get("kick_accuracy_bonus", 0.0)
        weather_kick_mod = self.weather_info.get("kick_accuracy_modifier", 0.0)
        success_prob *= (1.0 + kick_acc + kick_arch_bonus + weather_kick_mod)
        success_prob = max(0.10, min(0.98, success_prob))
        kicker.game_kick_attempts += 1
        kicker.game_pk_attempts += 1

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(3)
            kicker.game_kick_makes += 1
            kicker.game_pk_makes += 1
            weather_tag = f" [{self.weather_info['label']}]" if self.weather != "clear" else ""

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="place_kick",
                play_family=family.value,
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{ptag} field goal {distance}yd — GOOD! +3{weather_tag}",
                fatigue=round(stamina, 1),
            )
        else:
            kicking_team = self.state.possession
            receiving = "away" if kicking_team == "home" else "home"
            ball_landing = self.state.field_position + distance + random.randint(-5, 10)

            # ── Finnish baseball rule: missed field goal on downs 4-5 retains possession ──
            if self.state.down <= 5:
                self.state.down += 1
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number,
                    quarter=self.state.quarter,
                    time=self.state.time_remaining,
                    possession=self.state.possession,
                    field_position=self.state.field_position,
                    down=self.state.down,
                    yards_to_go=self.state.yards_to_go,
                    play_type="place_kick",
                    play_family=family.value,
                    players_involved=[player_label(kicker)],
                    yards_gained=0,
                    result=PlayResult.SNAP_KICK_RECOVERY.value,
                    description=f"{ptag} field goal {distance}yd — NO GOOD → retained possession (down {self.state.down})",
                    fatigue=round(stamina, 1),
                )

            # ── Down 6: traditional miss logic (possession at risk) ──
            if ball_landing >= 100:
                receiving_team_obj = self.get_defensive_team()
                is_pindown = self._check_rouge_pindown(receiving_team_obj, kicking_team)

                if is_pindown:
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                    play = Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=kicking_team,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="place_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.PINDOWN.value,
                        description=f"{ptag} field goal {distance}yd — NO GOOD, through the end zone — PINDOWN! +1",
                        fatigue=round(stamina, 1),
                    )
                    self._apply_rouge_pindown(kicking_team, receiving)
                    return play
                else:
                    self.change_possession()
                    self.state.field_position = random.randint(15, 25)
                    self.state.down = 1
                    self.state.yards_to_go = 20
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                    return Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=self.state.possession,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="place_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.MISSED_KICK.value,
                        description=f"{ptag} field goal {distance}yd — NO GOOD, returned out of end zone to {self.state.field_position}",
                        fatigue=round(stamina, 1),
                    )

            self.change_possession()
            self.state.field_position = max(1, 100 - ball_landing)
            self.state.down = 1
            self.state.yards_to_go = 20

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="place_kick",
                play_family=family.value,
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{ptag} field goal {distance}yd — NO GOOD",
                fatigue=round(stamina, 1),
            )

    def simulate_single_play(self, style: str = "balanced", field_position: int = 40,
                              down: int = 1, yards_to_go: int = 20) -> Dict:
        self.state.field_position = field_position
        self.state.down = down
        self.state.yards_to_go = yards_to_go
        self.state.possession = "home"

        old_style = self.home_team.offense_style
        self.home_team.offense_style = style
        self.home_style = OFFENSE_STYLES.get(style, OFFENSE_STYLES["balanced"])

        play = self.simulate_play()

        self.home_team.offense_style = old_style
        self.home_style = OFFENSE_STYLES.get(old_style, OFFENSE_STYLES["balanced"])

        return self.play_to_dict(play)

    def get_offensive_team(self) -> Team:
        return self.home_team if self.state.possession == "home" else self.away_team

    def add_score(self, points: float):
        if self.state.possession == "home":
            self.state.home_score += points
        else:
            self.state.away_score += points

    def change_possession(self):
        self.state.possession = "away" if self.state.possession == "home" else "home"

    def get_available_players(self, team: Team, top_n: int = 8) -> List:
        """Return top_n players from team who are not injured in this game."""
        injured = (self._home_injured_in_game if team == self.home_team
                   else self._away_injured_in_game)
        available = [p for p in team.players if p.name not in injured]
        return available[:top_n]

    def check_in_game_injury(self, player, play_type: str = "default") -> Optional[dict]:
        """
        Roll for an in-game injury on a player after a play.

        Uses the "structural strain" model: fatigue increases injury risk.
        Plus a 0.2% "freak injury" chaos factor on any play.

        Returns an injury event dict if injured, None otherwise.
        Marks the player as injured and finds a substitute.
        """
        if self.injury_tracker is None:
            return None
        if player.injured_in_game:
            return None

        # Freak injury chaos factor: 0.2% on any play regardless of fatigue
        if random.random() < 0.002:
            play_type = "run"  # Force a check with normal rates

        team = self.get_offensive_team()
        team_name = team.name
        is_home = (team == self.home_team)

        # Apply fatigue-driven injury multiplier to the player's stamina
        # before rolling (lower current_stamina = higher injury chance in
        # the injury tracker's roll_in_game_injury)
        original_stamina = getattr(player, 'current_stamina', 100.0)
        fatigue_mult = self.fatigue_injury_multiplier(player)
        if fatigue_mult > 1.0:
            # Temporarily reduce current_stamina to amplify injury chance
            player.current_stamina = max(10.0, original_stamina / fatigue_mult)

        injury = self.injury_tracker.roll_in_game_injury(
            player, team_name, self.game_week, play_type
        )

        # Restore original stamina
        if fatigue_mult > 1.0:
            player.current_stamina = original_stamina
        if injury is None:
            return None

        # Mark player as out for the rest of this game
        player.injured_in_game = True
        if is_home:
            self._home_injured_in_game.add(player.name)
        else:
            self._away_injured_in_game.add(player.name)

        # Find a substitute
        from engine.injuries import find_substitute, InGameInjuryEvent
        injured_set = (self._home_injured_in_game if is_home
                       else self._away_injured_in_game)
        sub, is_oop = find_substitute(
            team.players, player, set(), injured_set
        )

        event = InGameInjuryEvent(
            player_name=player.name,
            position=player.position,
            description=injury.description,
            tier=injury.tier,
            category=injury.category,
            is_season_ending=injury.is_season_ending,
            substitute_name=sub.name if sub else None,
            substitute_position=sub.position if sub else None,
            is_out_of_position=is_oop,
        )
        self.in_game_injuries.append(event)
        return event

    def check_defender_injury(self, player, play_type: str = "tackle") -> Optional[dict]:
        """Roll for in-game injury on a defensive player."""
        if self.injury_tracker is None:
            return None
        if player.injured_in_game:
            return None

        team = self.get_defensive_team()
        team_name = team.name
        is_home = (team == self.home_team)

        injury = self.injury_tracker.roll_in_game_injury(
            player, team_name, self.game_week, play_type
        )
        if injury is None:
            return None

        player.injured_in_game = True
        if is_home:
            self._home_injured_in_game.add(player.name)
        else:
            self._away_injured_in_game.add(player.name)

        from engine.injuries import find_substitute, InGameInjuryEvent
        injured_set = (self._home_injured_in_game if is_home
                       else self._away_injured_in_game)
        sub, is_oop = find_substitute(
            team.players, player, set(), injured_set
        )

        event = InGameInjuryEvent(
            player_name=player.name,
            position=player.position,
            description=injury.description,
            tier=injury.tier,
            category=injury.category,
            is_season_ending=injury.is_season_ending,
            substitute_name=sub.name if sub else None,
            substitute_position=sub.position if sub else None,
            is_out_of_position=is_oop,
        )
        self.in_game_injuries.append(event)
        return event

    def get_fatigue_factor(self) -> float:
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
        if stamina >= 70:
            return 1.0
        else:
            return 0.7 + (stamina / 70) * 0.3

    def apply_stamina_drain(self, amount: float):
        weather_drain = 1.0 + self.weather_info.get("stamina_drain_modifier", 0.0)
        adjusted = amount * weather_drain
        if self.state.possession == "home":
            self.state.home_stamina = max(40, self.state.home_stamina - adjusted)
        else:
            self.state.away_stamina = max(40, self.state.away_stamina - adjusted)

    # ── Per-player fatigue system ──

    def drain_player_energy(self, player, play_type: str = "run"):
        """Drain a player's game_energy based on involvement type.

        V2 Fatigue Tiers: drain rate depends on player's talent tier.
        Elite (overall >= 82): 0.8x drain rate
        Standard (62-81): 1.0x drain rate
        Low (< 62): 1.5x drain rate

        Drain is also **progressive** — small in Q1/Q2, ramps up in Q3/Q4.
        """
        drain_map = {
            "carrier": 1.8,
            "lateral": 1.5,
            "kick_pass": 1.2,
            "tackler": 1.2,
            "lineman": 0.6,
            "run": 1.8,
        }
        # Progressive multiplier: Q1 0.6×, Q2 0.8×, Q3 1.1×, Q4 1.4×
        quarter = self.state.quarter
        quarter_mult = {1: 0.6, 2: 0.8, 3: 1.1, 4: 1.4}.get(quarter, 1.0)
        base_drain = drain_map.get(play_type, 1.2)
        weather_mult = 1.0 + self.weather_info.get("stamina_drain_modifier", 0.0)

        # V2: Fatigue tier multiplier
        tier_mult = 1.0
        if V2_ENGINE_CONFIG.get("fatigue_tiers_enabled", False):
            tier = player.fatigue_tier
            if tier == FatigueTier.ELITE.value:
                tier_mult = 0.8   # Elite players drain slower
            elif tier == FatigueTier.LOW.value:
                tier_mult = 1.5   # Low-tier players drain faster

        player.game_energy = max(0.0, player.game_energy - base_drain * quarter_mult * weather_mult * tier_mult)

        # Track touch for rhythm
        if play_type in ("carrier", "run", "lateral", "kick_pass"):
            player.plays_since_last_touch = 0

    def player_fatigue_modifier(self, player) -> float:
        """Returns a multiplier (0.40 to 1.0) based on player's current energy.

        V2 Fatigue Tiers modify the severity of stat loss:
        Elite: 0.5x stat loss per energy point (more resilient)
        Standard: 1.0x stat loss (baseline)
        Low: 1.5x stat loss (degrades faster)

        The "fatigue cliff" remains — below 40% energy, performance
        degrades sharply.  But elite players handle it better.
        """
        energy = player.game_energy

        # V2: Tier-based stat loss multiplier
        stat_loss_mult = 1.0
        if V2_ENGINE_CONFIG.get("fatigue_tiers_enabled", False):
            tier = player.fatigue_tier
            if tier == FatigueTier.ELITE.value:
                stat_loss_mult = 0.5   # Elite feels fatigue half as much
            elif tier == FatigueTier.LOW.value:
                stat_loss_mult = 1.5   # Low-tier feels it 50% more

        if energy >= 80:
            return 1.0
        elif energy >= 60:
            penalty = 0.05 * stat_loss_mult
            return max(0.85, 1.0 - penalty)
        elif energy >= 40:
            penalty = 0.15 * stat_loss_mult
            return max(0.70, 1.0 - penalty)
        elif energy >= 20:
            # The cliff: linear ramp
            base_penalty = 0.15 + (40 - energy) / 20 * 0.30
            penalty = base_penalty * stat_loss_mult
            return max(0.40, 1.0 - penalty)
        else:
            # Emergency zone
            penalty = 0.60 * stat_loss_mult
            return max(0.25, 1.0 - penalty)

    def fatigue_injury_multiplier(self, player) -> float:
        """Fatigued players are more injury-prone.

        Uses the "structural strain" model: injury chance scales with
        fatigue. The cliff below 40% makes continued use dangerous.
        """
        energy = player.game_energy
        if energy >= 80:
            return 1.0
        elif energy >= 60:
            return 1.0
        elif energy >= 40:
            return 1.5  # +50% injury risk
        elif energy >= 20:
            return 2.5  # +150% injury risk — body breaking down
        else:
            return 4.0  # +300% injury risk — reckless to keep playing

    def recover_energy_between_drives(self):
        """Between drives, involved players recover a small amount of energy."""
        team = self.get_offensive_team()
        for p in team.players:
            p.game_energy = min(100.0, p.game_energy + 5.0)
            p.plays_since_last_touch += 1

    def recover_energy_halftime(self):
        """At halftime, all players recover 30 energy."""
        for p in self.home_team.players:
            p.game_energy = min(100.0, p.game_energy + 30.0)
        for p in self.away_team.players:
            p.game_energy = min(100.0, p.game_energy + 30.0)

    def call_timeout(self) -> bool:
        """Coaching AI decides whether to call a timeout.

        Considers: star player fatigue, clock management, momentum.
        Returns True if timeout was called.
        """
        if self.state.possession == "home":
            timeouts = self.state.home_timeouts
        else:
            timeouts = self.state.away_timeouts

        if timeouts <= 0:
            return False

        team = self.get_offensive_team()
        quarter = self.state.quarter
        time_left = self.state.time_remaining

        # Check star player fatigue (any skill player below 50% energy)
        skill_players = self._offense_skill(team)
        fatigued_stars = [p for p in skill_players
                         if p.game_energy < 50 and p.overall >= 75]

        should_call = False

        # Star player critically fatigued on a crucial drive
        if fatigued_stars and self.state.field_position >= 50:
            should_call = random.random() < 0.40

        # Last 2 minutes of half — clock management
        if quarter in (2, 4) and time_left < 120:
            score_diff = self._get_score_diff()
            if score_diff < 0:
                # Trailing: use timeouts to stop the clock
                should_call = random.random() < 0.60
            elif score_diff > 0 and time_left < 30:
                # Leading with very little time: defensive timeout
                should_call = random.random() < 0.30

        if should_call:
            # Call the timeout
            if self.state.possession == "home":
                self.state.home_timeouts -= 1
            else:
                self.state.away_timeouts -= 1

            # Recover energy for all players on the field
            for p in team.players:
                p.game_energy = min(100.0, p.game_energy + 15.0)

            return True

        return False

    def _apply_rhythm_decay(self, player) -> float:
        """Ball hunger penalty: players who haven't touched the ball
        in 15+ plays get a 'cold' debuff to their performance.

        Returns a multiplier (0.85 to 1.0).
        """
        touches_gap = player.plays_since_last_touch
        if touches_gap >= 20:
            return 0.85
        elif touches_gap >= 15:
            return 0.92
        return 1.0

    # ═══════════════════════════════════════════════════════════
    # V2: COMPOSURE SYSTEM
    # Dynamic per-game composure with tilt/surge and hysteresis.
    # ═══════════════════════════════════════════════════════════

    def _get_current_composure(self) -> float:
        """Get composure for the team currently on offense."""
        if self.state.possession == "home":
            return self.state.home_composure
        return self.state.away_composure

    def _get_opponent_composure(self) -> float:
        """Get composure for the team currently on defense."""
        if self.state.possession == "home":
            return self.state.away_composure
        return self.state.home_composure

    def _adjust_composure(self, team: str, event: str):
        """Adjust a team's composure based on a game event.

        Applies the composure delta from COMPOSURE_EVENTS, clamps
        to [COMPOSURE_MIN, COMPOSURE_MAX], and checks tilt/exit.
        """
        if not V2_ENGINE_CONFIG.get("composure_enabled", False):
            return

        delta = COMPOSURE_EVENTS.get(event, 0)
        if delta == 0:
            return

        if team == "home":
            self.state.home_composure = max(COMPOSURE_MIN, min(COMPOSURE_MAX,
                self.state.home_composure + delta))
            # Tilt check with hysteresis
            if not self.state.home_is_tilted and self.state.home_composure < COMPOSURE_TILT_THRESHOLD:
                self.state.home_is_tilted = True
            elif self.state.home_is_tilted and self.state.home_composure >= COMPOSURE_TILT_EXIT:
                self.state.home_is_tilted = False
            # Record timeline
            self.state.home_composure_timeline.append(round(self.state.home_composure, 1))
        else:
            self.state.away_composure = max(COMPOSURE_MIN, min(COMPOSURE_MAX,
                self.state.away_composure + delta))
            if not self.state.away_is_tilted and self.state.away_composure < COMPOSURE_TILT_THRESHOLD:
                self.state.away_is_tilted = True
            elif self.state.away_is_tilted and self.state.away_composure >= COMPOSURE_TILT_EXIT:
                self.state.away_is_tilted = False
            self.state.away_composure_timeline.append(round(self.state.away_composure, 1))

    def _apply_pregame_composure(self):
        """Apply pregame composure modifiers based on game context.

        Rivalry: +15% variance (both teams start with slightly volatile composure)
        Playoff: +25% variance
        Trap game: favorite starts lower, underdog starts higher
        """
        if not V2_ENGINE_CONFIG.get("composure_enabled", False):
            return

        base = COMPOSURE_BASE

        if self.is_rivalry:
            # Rivalry: both teams get composure variance
            variance = base * COMPOSURE_PREGAME["rivalry"]
            self.state.home_composure = base + random.gauss(0, variance * 0.5)
            self.state.away_composure = base + random.gauss(0, variance * 0.5)

        if getattr(self, '_is_playoff', False):
            variance = base * COMPOSURE_PREGAME["playoff"]
            self.state.home_composure += random.gauss(0, variance * 0.5)
            self.state.away_composure += random.gauss(0, variance * 0.5)

        if getattr(self, '_is_trap_game', False):
            # Determine favorite/underdog by prestige
            if self.home_team.prestige > self.away_team.prestige:
                self.state.home_composure += base * COMPOSURE_PREGAME["trap_game_favorite"]
                self.state.away_composure += base * COMPOSURE_PREGAME["trap_game_underdog"]
            else:
                self.state.away_composure += base * COMPOSURE_PREGAME["trap_game_favorite"]
                self.state.home_composure += base * COMPOSURE_PREGAME["trap_game_underdog"]

        # Clamp
        self.state.home_composure = max(COMPOSURE_MIN, min(COMPOSURE_MAX, self.state.home_composure))
        self.state.away_composure = max(COMPOSURE_MIN, min(COMPOSURE_MAX, self.state.away_composure))

    def _check_underdog_surge(self):
        """Underdog Surge: if the underdog is leading in Q4, reduce their
        fatigue drain by 15% (crowd energy, adrenaline).
        """
        if not V2_ENGINE_CONFIG.get("composure_enabled", False):
            return
        if self.state.quarter != 4:
            return

        home_prestige = self.home_team.prestige
        away_prestige = self.away_team.prestige
        score_diff = self.state.home_score - self.state.away_score

        # Home is underdog and leading
        if home_prestige < away_prestige - 10 and score_diff > 0:
            self.state.home_composure = min(COMPOSURE_MAX,
                self.state.home_composure + 2)  # Steady composure boost
        # Away is underdog and leading
        elif away_prestige < home_prestige - 10 and score_diff < 0:
            self.state.away_composure = min(COMPOSURE_MAX,
                self.state.away_composure + 2)

    # ═══════════════════════════════════════════════════════════
    # V2: HERO BALL + DEFENSIVE KEYING
    # ═══════════════════════════════════════════════════════════

    def _check_hero_ball(self, team_side: str) -> Optional[str]:
        """Check if hero ball should activate for the offensive team.

        Hero Ball: when a star player has 3+ consecutive touches with
        positive results, the offense force-feeds them.  Returns the
        star player's name if hero ball is active, None otherwise.
        """
        if not V2_ENGINE_CONFIG.get("hero_ball_enabled", False):
            return None

        if team_side == "home":
            target = self.state.home_hero_ball_target
            touches = self.state.home_consecutive_star_touches
        else:
            target = self.state.away_hero_ball_target
            touches = self.state.away_consecutive_star_touches

        if target and touches >= 3:
            return target
        return None

    def _update_hero_ball(self, team_side: str, player_name: str, success: bool):
        """Update hero ball tracking after a play.

        If a star player had a successful touch, increment their
        consecutive count.  If they failed or it was a non-star,
        reset the hero ball target.
        """
        if not V2_ENGINE_CONFIG.get("hero_ball_enabled", False):
            return

        team = self.home_team if team_side == "home" else self.away_team
        stars = self.state.home_stars if team_side == "home" else self.state.away_stars

        if player_name in stars and success:
            if team_side == "home":
                if self.state.home_hero_ball_target == player_name:
                    self.state.home_consecutive_star_touches += 1
                else:
                    self.state.home_hero_ball_target = player_name
                    self.state.home_consecutive_star_touches = 1
            else:
                if self.state.away_hero_ball_target == player_name:
                    self.state.away_consecutive_star_touches += 1
                else:
                    self.state.away_hero_ball_target = player_name
                    self.state.away_consecutive_star_touches = 1
        else:
            # Reset on failure or non-star touch
            if team_side == "home":
                self.state.home_hero_ball_target = ""
                self.state.home_consecutive_star_touches = 0
            else:
                self.state.away_hero_ball_target = ""
                self.state.away_consecutive_star_touches = 0

    def _apply_defensive_keying(self, carrier, team_side: str) -> float:
        """Defensive Keying: if the defense identifies the hero ball target,
        they key on that player, reducing their effectiveness.

        Returns a yards modifier (< 1.0 = keying is working).
        """
        if not V2_ENGINE_CONFIG.get("hero_ball_enabled", False):
            return 1.0

        # Defense keys on hero ball after 4+ consecutive star touches
        if team_side == "home":
            target = self.state.home_hero_ball_target
            touches = self.state.home_consecutive_star_touches
        else:
            target = self.state.away_hero_ball_target
            touches = self.state.away_consecutive_star_touches

        if carrier.name == target and touches >= 4:
            # Defense is keying: effectiveness drops with each touch
            key_penalty = min(0.30, (touches - 3) * 0.08)
            return 1.0 - key_penalty

        return 1.0

    def _hot_streak_modifier(self, player) -> Tuple[float, float]:
        """Hot streak: after 3+ consecutive successful contests,
        a player's variance narrows toward the high end.

        Returns (center_bonus, variance_multiplier).
        3 successes: +0.4 center, 0.80× variance (tighter, upward)
        4 successes: +0.6 center, 0.70× variance
        5+ successes: +0.8 center, 0.60× variance (locked in)
        """
        streak = player.consecutive_successes
        if streak >= 5:
            return (0.8, 0.60)
        elif streak >= 4:
            return (0.6, 0.70)
        elif streak >= 3:
            return (0.4, 0.80)
        return (0.0, 1.0)

    def _update_player_streak(self, player, success: bool):
        """Update a player's consecutive success counter after a contest."""
        if success:
            player.consecutive_successes += 1
        else:
            player.consecutive_successes = 0

    def _garbage_time_check(self) -> bool:
        """In garbage time (lead > 27 or Q4 win prob > 95%),
        coaching AI should sub in depth players."""
        score_diff = abs(self._get_score_diff())
        if score_diff > 27:
            return True
        if self.state.quarter == 4 and score_diff > 18 and self.state.time_remaining < 300:
            return True
        return False

    def calculate_viper_impact(self) -> float:
        positions = ["free", "left", "right", "deep"]
        self.viper_position = random.choice(positions)
        impacts = {
            "free": 0.85,
            "left": 0.95,
            "right": 1.05,
            "deep": 1.10,
        }
        return impacts.get(self.viper_position, 1.0)

    def generate_game_summary(self) -> Dict:
        home_plays = [p for p in self.play_log if p.possession == "home"]
        away_plays = [p for p in self.play_log if p.possession == "away"]

        home_stats = self.calculate_team_stats(home_plays)
        away_stats = self.calculate_team_stats(away_plays)

        away_turnovers = len([p for p in away_plays if p.fumble and p.result == "fumble"])
        home_turnovers = len([p for p in home_plays if p.fumble and p.result == "fumble"])
        home_stats["fumble_recoveries"] = away_turnovers
        away_stats["fumble_recoveries"] = home_turnovers
        home_stats["fumble_recovery_points"] = away_turnovers * 0.5
        away_stats["fumble_recovery_points"] = home_turnovers * 0.5
        home_stats["bells"] = away_turnovers
        away_stats["bells"] = home_turnovers

        # Sacrifice yards and adjusted yardage (AdjY)
        home_stats["sacrifice_yards"] = self.state.home_sacrifice_yards
        away_stats["sacrifice_yards"] = self.state.away_sacrifice_yards
        home_stats["adjusted_yards"] = home_stats["total_yards"] + self.state.home_sacrifice_yards
        away_stats["adjusted_yards"] = away_stats["total_yards"] + self.state.away_sacrifice_yards

        # Fake punt stats
        home_fake_punts = [p for p in home_plays if p.play_type == "fake_punt"]
        away_fake_punts = [p for p in away_plays if p.play_type == "fake_punt"]
        home_stats["fake_punts_attempted"] = len(home_fake_punts)
        home_stats["fake_punts_converted"] = len([p for p in home_fake_punts if p.result in ("first_down", "touchdown")])
        away_stats["fake_punts_attempted"] = len(away_fake_punts)
        away_stats["fake_punts_converted"] = len([p for p in away_fake_punts if p.result in ("first_down", "touchdown")])

        # Compelled Efficiency — scoring rate when starting under sacrifice
        home_stats["sacrifice_drives"] = self.state.home_sacrifice_drives
        home_stats["sacrifice_scores"] = self.state.home_sacrifice_scores
        home_stats["compelled_efficiency"] = round(
            self.state.home_sacrifice_scores / max(1, self.state.home_sacrifice_drives) * 100, 1
        ) if self.state.home_sacrifice_drives > 0 else None
        away_stats["sacrifice_drives"] = self.state.away_sacrifice_drives
        away_stats["sacrifice_scores"] = self.state.away_sacrifice_scores
        away_stats["compelled_efficiency"] = round(
            self.state.away_sacrifice_scores / max(1, self.state.away_sacrifice_drives) * 100, 1
        ) if self.state.away_sacrifice_drives > 0 else None

        for stats, team_obj in [(home_stats, self.home_team), (away_stats, self.away_team)]:
            keeper_deflections = sum(p.game_kick_deflections for p in team_obj.players)
            keeper_bells = sum(p.game_keeper_bells for p in team_obj.players)
            keeper_tackles = sum(p.game_keeper_tackles for p in team_obj.players)
            keeper_fake_tds = sum(p.game_fake_td_allowed for p in team_obj.players)
            stats["keeper_deflections"] = keeper_deflections
            stats["keeper_bells_generated"] = keeper_bells
            stats["keeper_tackles"] = keeper_tackles
            stats["keeper_fake_tds_allowed"] = keeper_fake_tds

        for stats, plays in [(home_stats, home_plays), (away_stats, away_plays)]:
            plays_by_q = {q: 0 for q in range(1, 5)}
            for p in plays:
                if p.quarter in plays_by_q:
                    plays_by_q[p.quarter] += 1
            stats["plays_per_quarter"] = plays_by_q

        from .epa import calculate_ep, calculate_epa, calculate_game_epa
        from .viperball_metrics import (
            calculate_comprehensive_rating,
            calculate_overall_performance_index,
            calculate_fpv
        )

        play_dicts = []
        for i, p in enumerate(self.play_log):
            pd = self.play_to_dict(p)
            ep_before = calculate_ep(p.field_position, p.down)

            if i + 1 < len(self.play_log):
                next_p = self.play_log[i + 1]
                if next_p.possession == p.possession:
                    ep_after = calculate_ep(next_p.field_position, next_p.down)
                else:
                    ep_after = 0
            else:
                ep_after = 0

            is_chaos = p.result in ("chaos_recovery", "punt_return_td")
            fp_after = self.play_log[i + 1].field_position if i + 1 < len(self.play_log) else p.field_position
            epa_data = {
                "ep_before": ep_before,
                "ep_after": ep_after,
                "result": p.result,
                "play_type": p.play_type,
                "laterals": p.laterals,
                "chaos_event": is_chaos,
                "field_position_after": fp_after,
            }
            epa_val = calculate_epa(epa_data)
            pd["ep_before"] = ep_before
            pd["epa"] = epa_val
            pd["chaos_event"] = is_chaos
            play_dicts.append(pd)

        home_epa = calculate_game_epa(play_dicts, "home")
        away_epa = calculate_game_epa(play_dicts, "away")
        home_stats["epa"] = home_epa
        away_stats["epa"] = away_epa

        # -- Per-player VPA attribution ----------------------------------------
        # Build lookup from player label -> Player object for both teams.
        _player_lookup: Dict[str, "Player"] = {}
        for _p in self.home_team.players:
            _player_lookup[player_label(_p)] = _p
        for _p in self.away_team.players:
            _player_lookup[player_label(_p)] = _p

        for pd in play_dicts:
            epa_val = pd.get("epa", 0)
            involved = pd.get("players", [])
            if not involved:
                continue
            # Last player in the list is the ball carrier / primary actor
            # Split VPA: primary gets 60%, others split 40% evenly
            primary_label = involved[-1]
            assist_labels = involved[:-1]

            primary_share = epa_val if len(involved) == 1 else epa_val * 0.6
            assist_share = (epa_val * 0.4 / len(assist_labels)) if assist_labels else 0

            primary_player = _player_lookup.get(primary_label)
            if primary_player:
                primary_player.game_vpa += primary_share
                primary_player.game_plays_involved += 1

            for al in assist_labels:
                assist_player = _player_lookup.get(al)
                if assist_player:
                    assist_player.game_vpa += assist_share
                    assist_player.game_plays_involved += 1

        # VIPERBALL SABERMETRICS (Positive metrics, no negative numbers)
        home_metrics = calculate_comprehensive_rating(play_dicts, self.drive_log, "home")
        away_metrics = calculate_comprehensive_rating(play_dicts, self.drive_log, "away")
        home_opi = calculate_overall_performance_index(home_metrics)
        away_opi = calculate_overall_performance_index(away_metrics)

        home_stats["viperball_metrics"] = home_metrics
        home_stats["viperball_metrics"]["overall_performance_index"] = home_opi
        away_stats["viperball_metrics"] = away_metrics
        away_stats["viperball_metrics"]["overall_performance_index"] = away_opi

        def collect_player_stats(team):
            stats = []
            for p in team.players:
                has_activity = (p.game_touches > 0 or p.game_kick_attempts > 0 or
                               p.game_kick_deflections > 0 or p.game_coverage_snaps > 0 or
                               p.game_punt_returns > 0 or p.game_kick_returns > 0 or
                               p.game_st_tackles > 0 or p.game_tackles > 0 or
                               p.game_sacks > 0 or p.game_hurries > 0 or
                               p.game_kick_pass_ints > 0 or p.game_kick_passes_thrown > 0 or
                               p.game_kick_pass_receptions > 0 or
                               p.game_plays_involved > 0)
                if has_activity:
                    stat_entry = {
                        "tag": player_tag(p),
                        "name": p.name,
                        "archetype": get_archetype_info(p.archetype).get("label", p.archetype) if p.archetype != "none" else "—",
                        "touches": p.game_touches,
                        "yards": p.game_yards,
                        "rushing_yards": p.game_rushing_yards,
                        "rushing_tds": p.game_rushing_tds,
                        "lateral_yards": p.game_lateral_yards,
                        "tds": p.game_tds,
                        "all_purpose_yards": p.game_rushing_yards + p.game_lateral_yards + p.game_kick_return_yards + p.game_punt_return_yards + p.game_kick_pass_yards,
                        "fumbles": p.game_fumbles,
                        "laterals_thrown": p.game_laterals_thrown,
                        "lateral_receptions": p.game_lateral_receptions,
                        "lateral_assists": p.game_lateral_assists,
                        "lateral_tds": p.game_lateral_tds,
                        "kick_att": p.game_kick_attempts,
                        "kick_made": p.game_kick_makes,
                        "pk_att": p.game_pk_attempts,
                        "pk_made": p.game_pk_makes,
                        "dk_att": p.game_dk_attempts,
                        "dk_made": p.game_dk_makes,
                        "kick_deflections": p.game_kick_deflections,
                        "keeper_bells": p.game_keeper_bells,
                        "coverage_snaps": p.game_coverage_snaps,
                        "keeper_tackles": p.game_keeper_tackles,
                        "keeper_return_yards": p.game_keeper_return_yards,
                        "kick_returns": p.game_kick_returns,
                        "kick_return_yards": p.game_kick_return_yards,
                        "kick_return_tds": p.game_kick_return_tds,
                        "punt_returns": p.game_punt_returns,
                        "punt_return_yards": p.game_punt_return_yards,
                        "punt_return_tds": p.game_punt_return_tds,
                        "muffs": p.game_muffs,
                        "st_tackles": p.game_st_tackles,
                        "kick_passes_thrown": p.game_kick_passes_thrown,
                        "kick_passes_completed": p.game_kick_passes_completed,
                        "kick_pass_yards": p.game_kick_pass_yards,
                        "kick_pass_tds": p.game_kick_pass_tds,
                        "kick_pass_receptions": p.game_kick_pass_receptions,
                        "kick_pass_interceptions_thrown": p.game_kick_pass_interceptions,
                        "tackles": p.game_tackles,
                        "tfl": p.game_tfl,
                        "sacks": p.game_sacks,
                        "hurries": p.game_hurries,
                        "kick_pass_ints": p.game_kick_pass_ints,
                        "vpa": round(p.game_vpa, 2),
                        "plays_involved": p.game_plays_involved,
                        "vpa_per_play": round(p.game_vpa / max(1, p.game_plays_involved), 3),
                    }
                    stats.append(stat_entry)
            return sorted(stats, key=lambda x: x["touches"] + x["kick_att"] + x["tackles"], reverse=True)

        home_player_stats = collect_player_stats(self.home_team)
        away_player_stats = collect_player_stats(self.away_team)

        summary = {
            "final_score": {
                "home": {
                    "team": self.home_team.name,
                    "score": self.state.home_score,
                },
                "away": {
                    "team": self.away_team.name,
                    "score": self.state.away_score,
                },
            },
            "home_style": self.home_team.offense_style,
            "away_style": self.away_team.offense_style,
            "home_defense_style": self.home_team.defense_style,
            "away_defense_style": self.away_team.defense_style,
            "home_st_scheme": self.home_team.st_scheme,
            "away_st_scheme": self.away_team.st_scheme,
            "sacrifice_yards": {
                "home": self.state.home_sacrifice_yards,
                "away": self.state.away_sacrifice_yards,
            },
            "weather": self.weather,
            "weather_label": self.weather_info["label"],
            "weather_description": self.weather_info["description"],
            "seed": self.seed,
            "stats": {
                "home": home_stats,
                "away": away_stats,
            },
            "player_stats": {
                "home": home_player_stats,
                "away": away_player_stats,
            },
            "drive_summary": self.drive_log,
            "play_by_play": play_dicts,
            "in_game_injuries": [
                {
                    "player": e.player_name,
                    "position": e.position,
                    "description": e.description,
                    "tier": e.tier,
                    "category": e.category,
                    "season_ending": e.is_season_ending,
                    "substitute": e.substitute_name,
                    "sub_position": e.substitute_position,
                    "out_of_position": e.is_out_of_position,
                }
                for e in self.in_game_injuries
            ],
            # ── V2: Engine metadata ──
            "v2_engine": {
                "contest_model": V2_ENGINE_CONFIG.get("contest_model", "v1_sigmoid"),
                "halo_enabled": V2_ENGINE_CONFIG.get("halo_enabled", False),
                "composure_enabled": V2_ENGINE_CONFIG.get("composure_enabled", False),
                "home_prestige": self.home_team.prestige,
                "away_prestige": self.away_team.prestige,
                "home_halo": {"offense": round(self.home_team.halo_offense, 1),
                              "defense": round(self.home_team.halo_defense, 1)},
                "away_halo": {"offense": round(self.away_team.halo_offense, 1),
                              "defense": round(self.away_team.halo_defense, 1)},
                "home_stars": self.state.home_stars,
                "away_stars": self.state.away_stars,
                "composure_final": {
                    "home": round(self.state.home_composure, 1),
                    "away": round(self.state.away_composure, 1),
                },
                "composure_timeline": {
                    "home": self.state.home_composure_timeline,
                    "away": self.state.away_composure_timeline,
                },
                "home_tilted_at_end": self.state.home_is_tilted,
                "away_tilted_at_end": self.state.away_is_tilted,
            },
        }

        return summary

    def calculate_team_stats(self, plays: List[Play]) -> Dict:
        total_yards = sum(p.yards_gained for p in plays if p.yards_gained > 0)
        total_plays = len(plays)

        laterals = [p for p in plays if p.laterals > 0]
        total_laterals = sum(p.laterals for p in laterals)
        successful_laterals = sum(1 for p in laterals if not p.fumble)

        drop_kicks = [p for p in plays if p.play_type == "drop_kick" and p.result == "successful_kick"]
        drop_kicks_attempted = [p for p in plays if p.play_type == "drop_kick"]
        place_kicks = [p for p in plays if p.play_type == "place_kick" and p.result == "successful_kick"]
        place_kicks_attempted = [p for p in plays if p.play_type == "place_kick"]
        touchdowns = [p for p in plays if p.result == "touchdown"]
        punt_return_tds = [p for p in plays if p.result == "punt_return_td"]
        fumbles_lost = [p for p in plays if p.fumble and p.result == "fumble"]
        turnovers_on_downs = [p for p in plays if p.result == "turnover_on_downs"]
        pindowns = [p for p in plays if p.result == "pindown"]
        punts = [p for p in plays if p.play_type == "punt"]
        chaos_recoveries = [p for p in plays if p.result == "chaos_recovery"]
        kick_passes = [p for p in plays if p.play_type == "kick_pass"]
        kick_pass_completions = [p for p in kick_passes if p.result in ("gain", "first_down", "touchdown")]
        kick_pass_tds = [p for p in kick_passes if p.result == "touchdown"]
        kick_pass_ints = [p for p in kick_passes if p.result in ("kick_pass_intercepted", "int_return_td")]
        kick_pass_yards = sum(max(0, p.yards_gained) for p in kick_pass_completions)
        lateral_ints = [p for p in laterals if p.result == "lateral_intercepted"]

        kick_plays = [p for p in plays if p.play_type in ["punt", "drop_kick", "place_kick"]]
        kick_percentage = round(len(kick_plays) / max(1, total_plays) * 100, 1)

        play_family_counts = {}
        for p in plays:
            fam = p.play_family
            play_family_counts[fam] = play_family_counts.get(fam, 0) + 1

        viper_efficiency = (total_yards / max(1, total_plays)) * (1 + successful_laterals / max(1, total_laterals))
        lateral_efficiency = (successful_laterals / max(1, len(laterals))) * 100 if laterals else 0

        fatigue_values = [p.fatigue for p in plays if p.fatigue is not None]
        avg_fatigue = round(sum(fatigue_values) / max(1, len(fatigue_values)), 1) if fatigue_values else 100.0

        down_conversions = {}
        for d in [4, 5, 6]:
            down_plays = [p for p in plays if p.down == d and p.play_type not in ["punt", "drop_kick", "place_kick"]]
            converted = [p for p in down_plays if p.yards_gained >= p.yards_to_go or p.result in ("touchdown", "punt_return_td")]
            down_conversions[d] = {
                "attempts": len(down_plays),
                "converted": len(converted),
                "rate": round(len(converted) / max(1, len(down_plays)) * 100, 1) if down_plays else 0.0,
            }

        penalty_plays = [p for p in plays if p.penalty is not None]
        penalties_accepted = [p for p in penalty_plays if not p.penalty.declined]
        penalties_declined = [p for p in penalty_plays if p.penalty.declined]
        penalty_yards = sum(p.penalty.yards for p in penalties_accepted)

        run_plays = [p for p in plays if p.play_type in ("run", "trick_play")]
        rushing_yards = sum(max(0, p.yards_gained) for p in run_plays)
        rushing_tds = len([p for p in run_plays if p.result == "touchdown"])
        lateral_chain_plays = [p for p in plays if p.play_type == "lateral_chain" and not p.fumble]
        lateral_yards = sum(max(0, p.yards_gained) for p in lateral_chain_plays)

        return {
            "total_yards": total_yards,
            "rushing_yards": rushing_yards,
            "rushing_touchdowns": rushing_tds,
            "lateral_yards": lateral_yards,
            "total_plays": total_plays,
            "yards_per_play": round(total_yards / max(1, total_plays), 2),
            "touchdowns": len(touchdowns),
            "punt_return_tds": len(punt_return_tds),
            "lateral_chains": len(laterals),
            "successful_laterals": successful_laterals,
            "fumbles_lost": len(fumbles_lost),
            "turnovers_on_downs": len(turnovers_on_downs),
            "drop_kicks_made": len(drop_kicks),
            "drop_kicks_attempted": len(drop_kicks_attempted),
            "place_kicks_made": len(place_kicks),
            "place_kicks_attempted": len(place_kicks_attempted),
            "kick_passes_attempted": len(kick_passes),
            "kick_passes_completed": len(kick_pass_completions),
            "kick_pass_yards": kick_pass_yards,
            "kick_pass_tds": len(kick_pass_tds),
            "kick_pass_interceptions": len(kick_pass_ints),
            "lateral_interceptions": len(lateral_ints),
            "punts": len(punts),
            "pindowns": len(pindowns),
            "chaos_recoveries": len(chaos_recoveries),
            "kick_percentage": kick_percentage,
            "viper_efficiency": round(viper_efficiency, 2),
            "lateral_efficiency": round(lateral_efficiency, 1),
            "play_family_breakdown": play_family_counts,
            "avg_fatigue": avg_fatigue,
            "safeties_conceded": len([p for p in plays if p.result == "safety"]),
            "down_conversions": down_conversions,
            "penalties": len(penalties_accepted),
            "penalty_yards": penalty_yards,
            "penalties_declined": len(penalties_declined),
        }

    def play_to_dict(self, play: Play) -> Dict:
        d = {
            "play_number": play.play_number,
            "quarter": play.quarter,
            "time_remaining": play.time,
            "possession": play.possession,
            "field_position": play.field_position,
            "down": play.down,
            "yards_to_go": play.yards_to_go,
            "play_type": play.play_type,
            "play_family": play.play_family,
            "players": play.players_involved,
            "yards": play.yards_gained,
            "result": play.result,
            "description": play.description,
            "fatigue": play.fatigue,
            "laterals": play.laterals if play.laterals > 0 else None,
            "fumble": play.fumble if play.fumble else None,
            "play_signature": play.play_signature if play.play_signature else None,
        }
        if play.penalty:
            d["penalty"] = {
                "name": play.penalty.name,
                "yards": play.penalty.yards,
                "on_team": play.penalty.on_team,
                "player": play.penalty.player,
                "declined": play.penalty.declined,
                "phase": play.penalty.phase,
            }
        return d


def _derive_prestige_from_roster(players: List[Player]) -> int:
    """Derive prestige from the worst 3 players on the roster.

    The idea: a program's depth defines its prestige.  Blue bloods
    have 65+ rated backups; doormat programs have 45-rated ones.
    We take the average overall of the 3 lowest-rated players and
    map that to a 10-99 prestige scale.

    Bottom-3 avg 45 → prestige ~25
    Bottom-3 avg 55 → prestige ~45
    Bottom-3 avg 65 → prestige ~65
    Bottom-3 avg 75 → prestige ~85
    """
    if not players or len(players) < 3:
        return 50

    overalls = sorted(p.overall for p in players)
    worst_3_avg = sum(overalls[:3]) / 3.0

    # Map: overall 40 → prestige 15, overall 80 → prestige 95
    # Linear: prestige = (worst_3_avg - 40) * 2.0 + 15
    prestige = (worst_3_avg - 40) * 2.0 + 15

    # Add some noise so identical rosters don't all land on the same prestige
    prestige += random.gauss(0, 3)

    return max(10, min(99, int(round(prestige))))


def load_team_from_json(filepath: str, fresh: bool = False,
                        program_archetype: Optional[str] = None) -> Team:
    """Load a team from its JSON metadata file.

    Args:
        filepath: Path to the team JSON file.
        fresh: If True, always generate a brand-new roster from the team's
               recruiting_pipeline and philosophy (dynamic mode).  If False,
               load the stored static roster when one is present; fall back to
               dynamic generation when there is no roster section.
        program_archetype: Optional program archetype for fresh generation
                          (e.g. "doormat", "blue_blood"). Only used when fresh=True.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")
    abbreviation = data["team_info"]["abbreviation"]
    mascot = data["team_info"]["mascot"]
    style = data.get("style", {}).get("offense_style", "balanced")
    defense_style = data.get("style", {}).get("defense_style", "base_defense")
    st_scheme = data.get("style", {}).get("st_scheme", "aces")
    identity = data.get("identity", {})
    philosophy = identity.get("philosophy", "hybrid")
    state = data["team_info"].get("state", "")

    # Build geo-aware pipeline from school location; this is blended with the
    # international baseline inside generate_player_name's select_origin().
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _root = str(_Path(__file__).parent.parent)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from scripts.generate_names import build_geo_pipeline as _build_geo
        recruiting_pipeline = _build_geo(state) if state else data.get("recruiting_pipeline", None)
    except Exception:
        recruiting_pipeline = data.get("recruiting_pipeline", None)

    has_roster = "roster" in data and data["roster"].get("players")

    if fresh or not has_roster:
        # Generate a completely fresh roster — each call produces unique players
        return generate_team_on_the_fly(
            team_name=team_name,
            abbreviation=abbreviation,
            mascot=mascot,
            offense_style=style,
            defense_style=defense_style,
            st_scheme=st_scheme,
            philosophy=philosophy,
            recruiting_pipeline=recruiting_pipeline,
            program_archetype=program_archetype,
        )

    _POSITION_MIGRATION = {
        "Zeroback/Back": "Zeroback",
        "Halfback/Back": "Halfback",
        "Wingback/End": "Wingback",
        "Wing/End": "Wingback",
        "Shiftback/Back": "Slotback",
        "Viper/Back": "Viper",
        "Back/Safety": "Keeper",
        "Back/Corner": "Keeper",
        "Safety": "Keeper",
        "Wedge/Line": "Offensive Line",
        "Lineman": "Offensive Line",
    }

    POSITION_ORDER = {
        "Viper": 0, "Zeroback": 1, "Halfback": 2, "Wingback": 3,
        "Slotback": 4, "Keeper": 5, "Offensive Line": 6, "Defensive Line": 7,
    }

    # Load the stored roster (static path — used when loading a saved game)
    players = []
    for p_data in data["roster"]["players"]:
        stats = p_data.get("stats", {})
        hometown = p_data.get("hometown", {})
        raw_pos = p_data["position"]
        position = _POSITION_MIGRATION.get(raw_pos, raw_pos)
        players.append(
            Player(
                number=p_data["number"],
                name=p_data["name"],
                position=position,
                speed=stats.get("speed", 80),
                stamina=stats.get("stamina", 82),
                kicking=stats.get("kicking", 72),
                lateral_skill=stats.get("lateral_skill", 78),
                tackling=stats.get("tackling", 75),
                agility=stats.get("agility", 75),
                power=stats.get("power", 75),
                awareness=stats.get("awareness", 75),
                hands=stats.get("hands", 75),
                kick_power=stats.get("kick_power", 75),
                kick_accuracy=stats.get("kick_accuracy", 75),
                archetype=p_data.get("archetype", "none"),
                player_id=p_data.get("player_id", ""),
                nationality=p_data.get("nationality", "American"),
                hometown_city=hometown.get("city", ""),
                hometown_state=hometown.get("state", ""),
                hometown_country=hometown.get("country", "USA"),
                high_school=p_data.get("high_school", ""),
                height=p_data.get("height", "5-10"),
                weight=p_data.get("weight", 170),
                year=p_data.get("year", "Sophomore"),
                potential=p_data.get("potential", 3),
                development=p_data.get("development", "normal"),
            )
        )

    players.sort(key=lambda p: (POSITION_ORDER.get(p.position, 99), p.number))

    # V2: Load prestige from team data, or derive from roster floor.
    # Prestige is keyed off the WORST 3 players — the depth of the roster
    # defines the program's floor.  A blue blood has 65-rated backups;
    # a doormat has 45-rated ones.  This creates natural prestige spread.
    stored_prestige = data.get("prestige", data.get("team_stats", {}).get("prestige", None))
    if stored_prestige is not None:
        prestige = stored_prestige
    else:
        prestige = _derive_prestige_from_roster(players)

    team = Team(
        name=team_name,
        abbreviation=abbreviation,
        mascot=mascot,
        players=players,
        avg_speed=data["team_stats"]["avg_speed"],
        avg_stamina=data["team_stats"]["avg_stamina"],
        kicking_strength=data["team_stats"]["kicking_strength"],
        lateral_proficiency=data["team_stats"]["lateral_proficiency"],
        defensive_strength=data["team_stats"]["defensive_strength"],
        offense_style=style,
        defense_style=defense_style,
        st_scheme=st_scheme,
        prestige=prestige,
    )

    # V2: Derive halo from prestige
    h_off, h_def = derive_halo(prestige)
    team.halo_offense = h_off
    team.halo_defense = h_def

    return team


def generate_team_on_the_fly(
    team_name: str,
    abbreviation: str,
    mascot: str,
    offense_style: str = "balanced",
    defense_style: str = "base_defense",
    st_scheme: str = "aces",
    philosophy: str = "hybrid",
    recruiting_pipeline: Optional[Dict] = None,
    program_archetype: Optional[str] = None,
) -> Team:
    """
    Generate a fresh Team with unique women players using the name/attribute generators.
    Used when no pre-built roster JSON exists, or to create dynamic teams in season/dynasty mode.
    Players are women only; archetypes are assigned from stats.

    Args:
        program_archetype: Optional program archetype key (e.g. "doormat", "blue_blood").
                          Affects talent distribution, potential ratings, and hidden gems.
                          None defaults to "regional_power" (matches original behavior).
    """
    import sys
    from pathlib import Path as _Path
    _root = str(_Path(__file__).parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from scripts.generate_names import generate_player_name
    from scripts.generate_rosters import generate_player_attributes, assign_archetype, PROGRAM_ARCHETYPES, DEFAULT_ARCHETYPE

    ROSTER_TEMPLATE = [
        ("Viper", True),
        ("Viper", False),
        ("Viper", False),
        ("Zeroback", False),
        ("Zeroback", False),
        ("Zeroback", False),
        ("Halfback", False),
        ("Halfback", False),
        ("Halfback", False),
        ("Halfback", False),
        ("Wingback", False),
        ("Wingback", False),
        ("Wingback", False),
        ("Wingback", False),
        ("Slotback", False),
        ("Slotback", False),
        ("Slotback", False),
        ("Slotback", False),
        ("Keeper", False),
        ("Keeper", False),
        ("Keeper", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Offensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
        ("Defensive Line", False),
    ]

    class_distribution = (
        ["freshman"] * 9
        + ["sophomore"] * 9
        + ["junior"] * 9
        + ["senior"] * 9
    )
    random.shuffle(class_distribution)

    players = []
    used_numbers: set = set()

    for i, (position, is_viper) in enumerate(ROSTER_TEMPLATE):
        number = 1 if is_viper and i == 0 else None
        while number is None or number in used_numbers:
            number = random.randint(2, 99)
        used_numbers.add(number)

        year = class_distribution[i] if i < len(class_distribution) else random.choice(["freshman", "sophomore", "junior", "senior"])

        name_data = generate_player_name(
            school_recruiting_pipeline=recruiting_pipeline,
            year=year,
        )
        attrs = generate_player_attributes(position, philosophy, year, is_viper,
                                           program_archetype=program_archetype)
        archetype = assign_archetype(
            position,
            attrs["speed"], attrs["stamina"],
            attrs["kicking"], attrs["lateral_skill"], attrs["tackling"],
        )
        hometown = name_data.get("hometown", {})

        players.append(Player(
            number=number,
            name=name_data["full_name"],
            position=position,
            speed=attrs["speed"],
            stamina=attrs["stamina"],
            kicking=attrs["kicking"],
            lateral_skill=attrs["lateral_skill"],
            tackling=attrs["tackling"],
            agility=attrs.get("agility", 75),
            power=attrs.get("power", 75),
            awareness=attrs.get("awareness", 75),
            hands=attrs.get("hands", 75),
            kick_power=attrs.get("kick_power", 75),
            kick_accuracy=attrs.get("kick_accuracy", 75),
            archetype=archetype,
            player_id=name_data.get("player_id", ""),
            nationality=name_data.get("nationality", "American"),
            hometown_city=hometown.get("city", ""),
            hometown_state=hometown.get("state", ""),
            hometown_country=hometown.get("country", "USA"),
            high_school=name_data.get("high_school", ""),
            height=attrs.get("height", "5-10"),
            weight=attrs.get("weight", 170),
            year=year.capitalize(),
            potential=attrs.get("potential", 3),
            development=attrs.get("development", "normal"),
        ))

    # ── Hidden gem boosts ──
    # Every program has a few players whose hidden abilities outstrip their
    # ratings.  Instead of boosting ALL stats (which inflates OVR uniformly),
    # each gem gets 2-4 *targeted* stats boosted heavily.  This means their
    # overall rating stays modest, but they shine in specific areas — a true
    # "hidden gem" whose game-day impact exceeds their number.
    _GEM_STAT_NAMES = [
        "speed", "stamina", "kicking", "lateral_skill", "tackling",
        "agility", "power", "awareness", "hands", "kick_power", "kick_accuracy",
    ]
    arch_key = program_archetype or DEFAULT_ARCHETYPE
    arch_data = PROGRAM_ARCHETYPES.get(arch_key, PROGRAM_ARCHETYPES[DEFAULT_ARCHETYPE])
    gem_min, gem_max = arch_data["hidden_gem_count"]
    boost_min, boost_max = arch_data["hidden_gem_boost"]
    gem_stat_range = arch_data.get("hidden_gem_stats", (2, 3))
    num_gems = random.randint(gem_min, gem_max)
    gem_indices = random.sample(range(len(players)), min(num_gems, len(players)))
    for gi in gem_indices:
        p = players[gi]
        boost = random.randint(boost_min, boost_max)
        # Pick a handful of stats to be this player's hidden strengths
        num_elite = random.randint(gem_stat_range[0], gem_stat_range[1])
        elite_stats = random.sample(_GEM_STAT_NAMES, num_elite)
        for stat_name in elite_stats:
            current = getattr(p, stat_name)
            setattr(p, stat_name, min(100, current + boost))
        # Hidden gems also get better potential
        p.potential = min(5, p.potential + random.randint(1, 2))

    avg_speed = sum(p.speed for p in players) // len(players)
    avg_stamina = sum(p.stamina for p in players) // len(players)
    kicking_strength = sum(p.kicking for p in players) // len(players)
    lateral_proficiency = sum(p.lateral_skill for p in players) // len(players)
    defensive_strength = sum(p.tackling for p in players) // len(players)

    # V2: Derive prestige from roster floor
    prestige = _derive_prestige_from_roster(players)

    team = Team(
        name=team_name,
        abbreviation=abbreviation,
        mascot=mascot,
        players=players,
        avg_speed=avg_speed,
        avg_stamina=avg_stamina,
        kicking_strength=kicking_strength,
        lateral_proficiency=lateral_proficiency,
        defensive_strength=defensive_strength,
        offense_style=offense_style,
        defense_style=defense_style,
        st_scheme=st_scheme,
        prestige=prestige,
    )

    h_off, h_def = derive_halo(prestige)
    team.halo_offense = h_off
    team.halo_defense = h_def

    return team


def get_available_teams() -> List[Dict]:
    import os
    teams_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
    teams = []
    for f in sorted(os.listdir(teams_dir)):
        if f.endswith(".json"):
            filepath = os.path.join(teams_dir, f)
            with open(filepath) as fh:
                data = json.load(fh)
            style = data.get("style", {}).get("offense_style", "balanced")
            team_info = data["team_info"]
            team_name = team_info.get("school") or team_info.get("school_name", "Unknown")
            teams.append({
                "key": f.replace(".json", ""),
                "name": team_name,
                "abbreviation": team_info["abbreviation"],
                "mascot": team_info["mascot"],
                "default_style": style,
                "file": filepath,
                "conference": team_info.get("conference", "Independent"),
                "state": team_info.get("state", ""),
                "city": team_info.get("city", ""),
            })
    return teams


def get_available_styles() -> Dict:
    return {k: {"label": v["label"], "description": v["description"]} for k, v in OFFENSE_STYLES.items()}
