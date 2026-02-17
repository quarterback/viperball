"""
Collegiate Viperball Simulation Engine
Core game simulation logic for CVL games
"""

import random
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy



class PlayType(Enum):
    RUN = "run"
    LATERAL_CHAIN = "lateral_chain"
    PUNT = "punt"
    DROP_KICK = "drop_kick"
    PLACE_KICK = "place_kick"


class PlayFamily(Enum):
    DIVE_OPTION = "dive_option"
    SPEED_OPTION = "speed_option"
    SWEEP_OPTION = "sweep_option"
    LATERAL_SPREAD = "lateral_spread"
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


PLAY_FAMILY_TO_TYPE = {
    PlayFamily.DIVE_OPTION: PlayType.RUN,
    PlayFamily.SPEED_OPTION: PlayType.RUN,
    PlayFamily.SWEEP_OPTION: PlayType.RUN,
    PlayFamily.POWER: PlayType.RUN,
    PlayFamily.COUNTER: PlayType.RUN,
    PlayFamily.DRAW: PlayType.RUN,
    PlayFamily.VIPER_JET: PlayType.RUN,
    PlayFamily.LATERAL_SPREAD: PlayType.LATERAL_CHAIN,
    PlayFamily.TERRITORY_KICK: PlayType.PUNT,
}

RUN_PLAY_CONFIG = {
    PlayFamily.DIVE_OPTION: {
        'base_yards': (7.5, 9.5),
        'variance': 3.5,
        'fumble_rate': 0.020,
        'primary_positions': ['HB', 'ZB', 'SB'],
        'action': 'dive',
    },
    PlayFamily.POWER: {
        'base_yards': (8.0, 10.0),
        'variance': 4.0,
        'fumble_rate': 0.022,
        'primary_positions': ['HB', 'SB', 'ZB'],
        'action': 'power',
    },
    PlayFamily.SWEEP_OPTION: {
        'base_yards': (8.5, 11.5),
        'variance': 5.0,
        'fumble_rate': 0.026,
        'primary_positions': ['WB', 'HB', 'SB'],
        'action': 'sweep',
    },
    PlayFamily.SPEED_OPTION: {
        'base_yards': (9.0, 12.5),
        'variance': 6.0,
        'fumble_rate': 0.028,
        'primary_positions': ['ZB', 'WB'],
        'action': 'pitch',
    },
    PlayFamily.COUNTER: {
        'base_yards': (8.0, 12.0),
        'variance': 6.0,
        'fumble_rate': 0.024,
        'primary_positions': ['HB', 'WB', 'SB'],
        'action': 'counter',
    },
    PlayFamily.DRAW: {
        'base_yards': (8.5, 12.5),
        'variance': 6.5,
        'fumble_rate': 0.022,
        'primary_positions': ['HB', 'ZB'],
        'action': 'draw',
    },
    PlayFamily.VIPER_JET: {
        'base_yards': (10.0, 14.0),
        'variance': 7.0,
        'fumble_rate': 0.030,
        'primary_positions': ['VP'],
        'action': 'jet',
    },
}

POSITION_TAGS = {
    "Lineman": "LM",
    "Zeroback/Back": "ZB",
    "Halfback/Back": "HB",
    "Wingback/End": "WB",
    "Wing/End": "WB",
    "Shiftback/Back": "SB",
    "Viper/Back": "VP",
    "Back/Safety": "LB",
    "Back/Corner": "CB",
    "Wedge/Line": "LA",
    "Viper": "VP",
    "Back": "BK",
    "Wing": "WB",
    "Wedge": "LA",
    "Safety": "KP",
    "End": "ED",
    "Line": "LA",
    "Corner": "CB",
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
    elif any(p in pos for p in ["Halfback", "Wingback", "Shiftback", "Wing"]):
        if spd >= 93:
            return "speed_flanker"
        elif tck >= 80 and stam >= 88:
            return "power_flanker"
        elif lat >= 88 and spd >= 85:
            return "elusive_flanker"
        else:
            return "reliable_flanker"
    elif any(p in pos for p in ["Safety", "Keeper"]):
        if spd >= 90 and spd > tck:
            return "return_keeper"
        elif lat >= 85 and stam >= 85:
            return "sure_hands_keeper"
        else:
            return "tackle_keeper"
    return "none"


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
    hometown_country: str = "USA"
    high_school: str = ""
    height: str = "5-10"
    weight: int = 170
    year: str = "Sophomore"

    # --- Dynasty attributes ---
    potential: int = 3        # 1–5 stars
    development: str = "normal"  # normal / quick / slow / late_bloomer

    # --- Fatigue / game state ---
    current_stamina: float = 100.0
    archetype: str = "none"

    # --- Per-game stat counters (reset each game) ---
    game_touches: int = 0
    game_yards: int = 0
    game_rushing_yards: int = 0
    game_lateral_yards: int = 0
    game_tds: int = 0
    game_fumbles: int = 0
    game_laterals_thrown: int = 0
    game_kick_attempts: int = 0
    game_kick_makes: int = 0
    game_kick_deflections: int = 0
    game_keeper_bells: int = 0
    game_coverage_snaps: int = 0
    game_fake_td_allowed: int = 0
    game_keeper_tackles: int = 0
    game_keeper_return_yards: int = 0

    @property
    def overall(self) -> int:
        """Weighted overall rating based on all core and extended attributes."""
        return int((
            self.speed * 1.2 + self.stamina * 1.0 + self.kicking * 0.8 +
            self.lateral_skill * 1.1 + self.tackling * 0.9 +
            self.agility * 1.0 + self.power * 0.8 + self.awareness * 1.1 +
            self.hands * 0.9 + self.kick_power * 0.6 + self.kick_accuracy * 0.6
        ) / 10.0)

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
    defense_style: str = "base_defense"  # New: defensive archetype


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


OFFENSE_STYLES = {
    "power_option": {
        "label": "Power Option",
        "description": "Heavy run game with option reads",
        "weights": {
            "dive_option": 0.18,
            "speed_option": 0.10,
            "sweep_option": 0.12,
            "power": 0.18,
            "counter": 0.08,
            "draw": 0.05,
            "viper_jet": 0.04,
            "lateral_spread": 0.12,
            "territory_kick": 0.13,
        },
        "tempo": 0.5,
        "lateral_risk": 0.8,
        "kick_rate": 0.15,
        "option_rate": 0.55,
        "run_bonus": 0.10,
        "fatigue_resistance": 0.05,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.0,
    },
    "lateral_spread": {
        "label": "Lateral Spread",
        "description": "High lateral chain usage, spread the field",
        "weights": {
            "dive_option": 0.05,
            "speed_option": 0.08,
            "sweep_option": 0.07,
            "power": 0.03,
            "counter": 0.04,
            "draw": 0.04,
            "viper_jet": 0.03,
            "lateral_spread": 0.50,
            "territory_kick": 0.16,
        },
        "tempo": 0.7,
        "lateral_risk": 1.4,
        "kick_rate": 0.18,
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
    },
    "territorial": {
        "label": "Territorial",
        "description": "Field position game, frequent kicks and punts — kick-heavy archetype",
        "weights": {
            "dive_option": 0.08,
            "speed_option": 0.05,
            "sweep_option": 0.06,
            "power": 0.05,
            "counter": 0.03,
            "draw": 0.03,
            "viper_jet": 0.02,
            "lateral_spread": 0.10,
            "territory_kick": 0.58,
        },
        "tempo": 0.3,
        "lateral_risk": 0.8,
        "kick_rate": 0.56,
        "option_rate": 0.25,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.10,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.15,
    },
    "option_spread": {
        "label": "Option Spread",
        "description": "Speed-based option reads with lateral chains",
        "weights": {
            "dive_option": 0.08,
            "speed_option": 0.20,
            "sweep_option": 0.10,
            "power": 0.05,
            "counter": 0.07,
            "draw": 0.06,
            "viper_jet": 0.06,
            "lateral_spread": 0.25,
            "territory_kick": 0.13,
        },
        "tempo": 0.8,
        "lateral_risk": 1.25,
        "kick_rate": 0.14,
        "option_rate": 0.50,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.15,
        "broken_play_bonus": 0.10,
        "pindown_bonus": 0.0,
        "tired_def_broken_play_bonus": 0.10,
    },
    "balanced": {
        "label": "Balanced",
        "description": "No strong tendency, adapts to situation",
        "weights": {
            "dive_option": 0.12,
            "speed_option": 0.10,
            "sweep_option": 0.10,
            "power": 0.10,
            "counter": 0.07,
            "draw": 0.06,
            "viper_jet": 0.05,
            "lateral_spread": 0.20,
            "territory_kick": 0.20,
        },
        "tempo": 0.5,
        "lateral_risk": 1.0,
        "kick_rate": 0.22,
        "option_rate": 0.40,
        "run_bonus": 0.05,
        "fatigue_resistance": 0.025,
        "kick_accuracy_bonus": 0.05,
        "explosive_lateral_bonus": 0.05,
        "option_read_bonus": 0.05,
        "broken_play_bonus": 0.05,
        "pindown_bonus": 0.05,
    },
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
    "base_defense": {
        "label": "Base Defense",
        "description": "Balanced defensive approach, solid fundamentals",
        "play_family_modifiers": {
            "dive_option": 0.95,
            "speed_option": 0.95,
            "sweep_option": 0.95,
            "power": 0.95,
            "counter": 0.95,
            "draw": 0.95,
            "viper_jet": 0.95,
            "lateral_spread": 0.95,
            "territory_kick": 0.95,
        },
        "read_success_rate": 0.35,
        "pressure_factor": 0.50,
        "turnover_bonus": 0.10,
        "explosive_suppression": 0.90,
        "kick_suppression": 0.97,
        "pindown_defense": 1.00,
        "fatigue_resistance": 0.025,
        "gameplan_bias": {
            "dive_option": 0.05,
            "speed_option": 0.05,
            "sweep_option": 0.05,
            "power": 0.05,
            "counter": 0.05,
            "draw": 0.05,
            "viper_jet": 0.05,
            "lateral_spread": 0.05,
            "territory_kick": 0.05,
        }
    },
    "pressure_defense": {
        "label": "Pressure Defense",
        "description": "Aggressive blitzing, high risk/high reward",
        "play_family_modifiers": {
            "dive_option": 0.95,
            "speed_option": 0.80,
            "sweep_option": 0.90,
            "power": 0.90,
            "counter": 1.10,
            "draw": 1.15,
            "viper_jet": 0.85,
            "lateral_spread": 1.20,
            "territory_kick": 0.95,
        },
        "read_success_rate": 0.40,
        "pressure_factor": 1.00,
        "turnover_bonus": 0.20,
        "explosive_suppression": 1.10,
        "kick_suppression": 1.05,
        "pindown_defense": 0.95,
        "fatigue_resistance": -0.05,
        "gameplan_bias": {
            "dive_option": 0.05,
            "speed_option": 0.10,
            "sweep_option": 0.05,
            "power": 0.05,
            "counter": 0.03,
            "draw": 0.02,
            "viper_jet": 0.08,
            "lateral_spread": 0.10,
            "territory_kick": 0.00,
        }
    },
    "contain_defense": {
        "label": "Contain Defense",
        "description": "Anti-chaos, prevents lateral chains and explosive plays",
        "play_family_modifiers": {
            "dive_option": 1.00,
            "speed_option": 0.90,
            "sweep_option": 0.95,
            "power": 1.05,
            "counter": 0.90,
            "draw": 1.00,
            "viper_jet": 0.85,
            "lateral_spread": 0.80,
            "territory_kick": 1.00,
        },
        "read_success_rate": 0.35,
        "pressure_factor": 0.20,
        "turnover_bonus": 0.05,
        "explosive_suppression": 0.75,
        "kick_suppression": 1.00,
        "pindown_defense": 1.00,
        "fatigue_resistance": 0.05,
        "gameplan_bias": {
            "dive_option": 0.00,
            "speed_option": 0.05,
            "sweep_option": 0.05,
            "power": 0.00,
            "counter": 0.05,
            "draw": 0.00,
            "viper_jet": 0.08,
            "lateral_spread": 0.10,
            "territory_kick": 0.00,
        }
    },
    "run_stop_defense": {
        "label": "Run-Stop Defense",
        "description": "Stacks the box, elite vs run game",
        "play_family_modifiers": {
            "dive_option": 0.75,
            "speed_option": 0.85,
            "sweep_option": 0.80,
            "power": 0.80,
            "counter": 0.85,
            "draw": 0.90,
            "viper_jet": 0.90,
            "lateral_spread": 1.10,
            "territory_kick": 1.00,
        },
        "read_success_rate": 0.40,
        "pressure_factor": 0.30,
        "turnover_bonus": 0.05,
        "explosive_suppression": 0.85,
        "kick_suppression": 1.00,
        "pindown_defense": 1.00,
        "fatigue_resistance": 0.00,
        "gameplan_bias": {
            "dive_option": 0.10,
            "speed_option": 0.10,
            "sweep_option": 0.10,
            "power": 0.08,
            "counter": 0.06,
            "draw": 0.05,
            "viper_jet": 0.05,
            "lateral_spread": 0.00,
            "territory_kick": 0.00,
        }
    },
    "coverage_defense": {
        "label": "Coverage Defense",
        "description": "Anti-kick, prevents pindowns and punt returns",
        "play_family_modifiers": {
            "dive_option": 1.05,
            "speed_option": 1.00,
            "sweep_option": 1.00,
            "power": 1.10,
            "counter": 1.05,
            "draw": 1.05,
            "viper_jet": 1.00,
            "lateral_spread": 1.00,
            "territory_kick": 0.85,
        },
        "read_success_rate": 0.30,
        "pressure_factor": 0.40,
        "turnover_bonus": 0.15,
        "explosive_suppression": 0.95,
        "kick_suppression": 0.85,
        "pindown_defense": 0.80,
        "fatigue_resistance": 0.025,
        "gameplan_bias": {
            "dive_option": 0.00,
            "speed_option": 0.00,
            "sweep_option": 0.00,
            "power": 0.00,
            "counter": 0.02,
            "draw": 0.02,
            "viper_jet": 0.03,
            "lateral_spread": 0.00,
            "territory_kick": 0.10,
        }
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
    "territorial": 0.8,       # Built to kick, good protection
    "balanced": 1.0,          # Average
    "power_option": 1.1,      # Slightly weak special teams
    "option_spread": 1.2,     # Less focus on kicking
    "lateral_spread": 1.2,    # Less focus on kicking
}

# Defensive style modifiers for blocks/muffs (higher = better special teams pressure)
DEFENSE_BLOCK_MODIFIERS = {
    "pressure_defense": 1.5,   # Elite at blocking kicks
    "coverage_defense": 1.0,   # Average at blocking
    "contain_defense": 1.0,    # Average at blocking
    "run_stop_defense": 1.0,   # Average at blocking
    "base_defense": 1.0,       # Average at blocking
}

DEFENSE_MUFF_MODIFIERS = {
    "coverage_defense": 1.3,   # Better gunners/coverage = more muffs
    "pressure_defense": 1.1,   # Aggressive coverage
    "contain_defense": 1.0,    # Average
    "run_stop_defense": 1.0,   # Average
    "base_defense": 1.0,       # Average
}


class ViperballEngine:

    def __init__(self, home_team: Team, away_team: Team, seed: Optional[int] = None,
                 style_overrides: Optional[Dict[str, str]] = None,
                 weather: str = "clear"):
        self.home_team = deepcopy(home_team)
        self.away_team = deepcopy(away_team)
        self.state = GameState()
        self.play_log: List[Play] = []
        self.drive_log: List[Dict] = []
        self.viper_position = "free"
        self.seed = seed
        self.drive_play_count = 0
        self.weather = weather if weather in WEATHER_CONDITIONS else "clear"
        self.weather_info = WEATHER_CONDITIONS[self.weather]

        for p in self.home_team.players:
            p.archetype = assign_archetype(p)
        for p in self.away_team.players:
            p.archetype = assign_archetype(p)

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

        self.home_style = OFFENSE_STYLES.get(self.home_team.offense_style, OFFENSE_STYLES["balanced"])
        self.away_style = OFFENSE_STYLES.get(self.away_team.offense_style, OFFENSE_STYLES["balanced"])
        self.home_defense = DEFENSE_STYLES.get(self.home_team.defense_style, DEFENSE_STYLES["base_defense"])
        self.away_defense = DEFENSE_STYLES.get(self.away_team.defense_style, DEFENSE_STYLES["base_defense"])

    def simulate_game(self) -> Dict:
        self.kickoff("away")

        for quarter in range(1, 5):
            self.state.quarter = quarter
            self.state.time_remaining = 900

            while self.state.time_remaining > 0:
                self.simulate_drive()
                if self.state.time_remaining <= 0:
                    break

        return self.generate_game_summary()

    def _check_rouge_pindown(self, receiving_team_obj, kicking_possession: str) -> bool:
        return_speed = receiving_team_obj.avg_speed
        pindown_bonus = self._current_style().get("pindown_bonus", 0.0)
        receiving_defense = self.away_defense if kicking_possession == "home" else self.home_defense
        pindown_defense_factor = receiving_defense.get("pindown_defense", 1.0)
        return_chance = (return_speed / 200) * (1.0 - pindown_bonus) / pindown_defense_factor
        return_chance = max(0.10, min(0.45, return_chance))
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
        self.state.possession = receiving_team
        kick_distance = int(random.gauss(62, 10))
        kick_distance = max(40, min(85, kick_distance))

        if kick_distance >= 60:
            receiving_team_obj = self.home_team if receiving_team == "home" else self.away_team
            kicking_team = "away" if receiving_team == "home" else "home"
            if self._check_rouge_pindown(receiving_team_obj, kicking_team):
                self._apply_rouge_pindown(kicking_team, receiving_team)
                return
            else:
                self.state.field_position = random.randint(15, 30)
                self.state.down = 1
                self.state.yards_to_go = 20
                return

        return_yards = random.randint(10, 30)
        start_position = max(10, min(40, return_yards))
        self.state.field_position = start_position
        self.state.down = 1
        self.state.yards_to_go = 20

    def simulate_drive(self):
        style = self._current_style()
        tempo = style["tempo"]
        max_plays = int(20 + tempo * 15)
        self.drive_play_count = 0

        drive_team = self.state.possession
        drive_start = self.state.field_position
        drive_quarter = self.state.quarter
        drive_plays = 0
        drive_yards = 0
        drive_result = "stall"

        while self.drive_play_count < max_plays and self.state.time_remaining > 0:
            self.drive_play_count += 1
            play = self.simulate_play()
            self.play_log.append(play)
            drive_plays += 1
            if play.yards_gained > 0 and play.play_type not in ["punt"]:
                drive_yards += play.yards_gained

            base_time = random.randint(15, 45)
            time_elapsed = int(base_time * (1.2 - tempo * 0.4))
            self.state.time_remaining = max(0, self.state.time_remaining - time_elapsed)

            if play.result == "snap_kick_recovery":
                drive_result = "snap_kick_recovery"
                continue

            if play.result in ["touchdown", "turnover_on_downs", "fumble", "successful_kick", "missed_kick", "punt", "pindown", "punt_return_td", "chaos_recovery", "safety"]:
                drive_result = play.result
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
                elif play.result == "safety":
                    scored_team = "away" if drive_team == "home" else "home"
                    self.state.possession = drive_team
                    self.state.field_position = 20
                    self.state.down = 1
                    self.state.yards_to_go = 20
                break

        self.drive_log.append({
            "team": drive_team,
            "quarter": drive_quarter,
            "start_yard_line": drive_start,
            "plays": drive_plays,
            "yards": drive_yards,
            "result": drive_result,
        })

    FIELD_POSITION_VALUE = [
        (10, 0.3), (20, 0.6), (35, 1.0), (50, 1.5),
        (65, 2.2), (80, 3.0), (90, 4.5), (100, 6.5),
    ]

    CONVERSION_RATES = {
        4: {3: 0.78, 6: 0.62, 10: 0.48, 15: 0.32, 20: 0.24},
        5: {3: 0.74, 6: 0.58, 10: 0.44, 15: 0.28, 20: 0.20},
        6: {3: 0.68, 6: 0.53, 10: 0.38, 15: 0.25, 20: 0.16},
    }

    def _fp_value(self, fp: int) -> float:
        for threshold, val in self.FIELD_POSITION_VALUE:
            if fp <= threshold:
                return val
        return 6.5

    def _conversion_rate(self, down: int, ytg: int) -> float:
        rates = self.CONVERSION_RATES.get(down, self.CONVERSION_RATES[6])
        if ytg <= 3:
            return rates[3]
        elif ytg <= 6:
            return rates[6]
        elif ytg <= 10:
            return rates[10]
        elif ytg <= 15:
            return rates[15]
        return rates[20]

    def _place_kick_success(self, distance: int) -> float:
        if distance <= 25:
            return 0.97
        elif distance <= 34:
            return 0.93
        elif distance <= 44:
            return 0.84
        elif distance <= 54:
            return 0.72
        else:
            return max(0.20, 0.52 - (distance - 55) * 0.02)

    def _drop_kick_success(self, distance: int, kicker_skill: int) -> float:
        if kicker_skill >= 85:
            tier = 0
        elif kicker_skill >= 70:
            tier = 1
        elif kicker_skill >= 50:
            tier = 2
        else:
            tier = 3

        table = [
            [0.94, 0.82, 0.72, 0.57, 0.42],
            [0.84, 0.72, 0.61, 0.45, 0.31],
            [0.74, 0.62, 0.51, 0.35, 0.22],
            [0.64, 0.52, 0.41, 0.27, 0.14],
        ]

        if distance <= 25:
            col = 0
        elif distance <= 34:
            col = 1
        elif distance <= 44:
            col = 2
        elif distance <= 54:
            col = 3
        else:
            col = 4

        return table[tier][col]

    POSSESSION_VALUE = 3.0

    GO_FOR_IT_MATRIX = {
        15:  {4: 5, 5: 4, 6: 3},
        30:  {4: 8, 5: 6, 6: 4},
        45:  {4: 10, 5: 8, 6: 6},
        50:  {4: 12, 5: 10, 6: 8},
        60:  {4: 10, 5: 8, 6: 7},
        75:  {4: 8, 5: 6, 6: 5},
        100: {4: 6, 5: 4, 6: 3},
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
        fp = self.state.field_position
        down = self.state.down
        ytg = self.state.yards_to_go

        fg_distance = (100 - fp) + 17

        tod_opponent_fp = 100 - fp
        tod_value = self._fp_value(tod_opponent_fp)

        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        kicker_skill = kicker.kicking

        pk_success = self._place_kick_success(fg_distance)
        pk_miss_cost = (1 - pk_success) * tod_value * 0.3
        ev_place_kick = pk_success * 3 - pk_miss_cost
        ev_place_kick *= 2.10

        dk_success = self._drop_kick_success(fg_distance, kicker_skill)
        dk_recovery = 0.35
        dk_miss_value = dk_recovery * (self._fp_value(fp) * 0.5) + (1 - dk_recovery) * (-tod_value * 0.3)
        ev_drop_kick = dk_success * 5 + (1 - dk_success) * dk_miss_value
        ev_drop_kick *= 1.0

        arch_info = get_archetype_info(kicker.archetype)
        if kicker.archetype == "kicking_zb":
            ev_drop_kick *= 1.20
            snapkick_boost = arch_info.get("snapkick_trigger_boost", 0.0)
            ev_drop_kick *= (1.0 + snapkick_boost * 0.4)

        if fp <= 25:
            punt_distance = random.gauss(55, 8)
        elif fp <= 40:
            punt_distance = random.gauss(50, 7)
        else:
            punt_distance = random.gauss(45, 6)
        new_fp_after_punt = max(1, fp + int(punt_distance))
        opp_fp = max(1, 100 - new_fp_after_punt)
        opp_value_after_punt = self._fp_value(opp_fp)
        pindown_prob = 0.40 if new_fp_after_punt >= 100 else (0.25 if opp_fp <= 10 else (0.15 if opp_fp <= 20 else 0.05))
        ev_punt = max(0.2, tod_value - opp_value_after_punt + pindown_prob * 1.0 - self.POSSESSION_VALUE * 1.5)

        conversion_rate = self._conversion_rate(down, ytg)
        new_fp_if_convert = min(99, fp + ytg)
        continuation_value = self._fp_value(new_fp_if_convert)
        drive_ep = self._expected_points_from_position(new_fp_if_convert)
        td_prob_boost = 0.0
        if new_fp_if_convert >= 95:
            td_prob_boost = 0.55 * 9
        elif new_fp_if_convert >= 90:
            td_prob_boost = 0.35 * 9
        elif new_fp_if_convert >= 85:
            td_prob_boost = 0.18 * 9
        elif new_fp_if_convert >= 80:
            td_prob_boost = 0.10 * 9
        failure_cost = (1 - conversion_rate) * tod_value * 0.5
        ev_go_for_it = conversion_rate * (continuation_value + drive_ep * 0.6 + td_prob_boost) - failure_cost

        aggression = {4: 1.25, 5: 1.05, 6: 0.92}.get(down, 1.0)
        ev_go_for_it *= aggression

        score_diff = self._get_score_diff()
        quarter = self.state.quarter
        time_left = self.state.time_remaining

        if score_diff <= -10:
            ev_go_for_it *= 1.20
            ev_drop_kick *= 1.10
        elif score_diff >= 10:
            ev_place_kick *= 1.15
            ev_punt *= 1.10

        if quarter == 4 and time_left <= 300:
            if score_diff < 0:
                ev_go_for_it *= 1.25
                ev_punt *= 0.25
            if time_left <= 120 and -8 <= score_diff <= -3:
                ev_drop_kick *= 1.20
            if time_left <= 120 and 1 <= score_diff <= 3:
                ev_place_kick *= 1.25

        if fg_distance <= 30:
            ev_place_kick *= 1.60
        elif fg_distance <= 40:
            ev_place_kick *= 1.40
        elif fg_distance <= 50:
            ev_place_kick *= 1.25
        elif fg_distance <= 58:
            ev_place_kick *= 1.10

        style = self._current_style()
        kick_rate = style.get("kick_rate", 0.2)
        if kick_rate >= 0.40:
            ev_drop_kick *= 1.25
            ev_place_kick *= 1.15
        elif kick_rate >= 0.20:
            ev_drop_kick *= 1.08

        options = {}
        if fg_distance <= 62:
            options['place_kick'] = ev_place_kick
        if fg_distance <= 55:
            options['drop_kick'] = ev_drop_kick
        if fp < 60:
            options['punt'] = ev_punt
        options['go_for_it'] = ev_go_for_it

        best = max(options, key=options.get)

        if best == 'punt' and 'place_kick' in options and fg_distance <= 55:
            best = 'place_kick'

        if best == 'go_for_it' and 'place_kick' in options and fg_distance <= 45 and down >= 4:
            conservative_prob = 0.0
            if down == 4 and ytg >= 8:
                conservative_prob = 0.35
            elif down == 4 and ytg >= 5:
                conservative_prob = 0.25
            elif down == 4 and ytg >= 3:
                conservative_prob = 0.15
            if fg_distance <= 30:
                conservative_prob += 0.10
            if random.random() < conservative_prob:
                best = 'place_kick'

        if 'place_kick' in options and fg_distance <= 50 and down >= 5 and ytg >= 3:
            coach_kick_prob = 0.0
            if down == 6 and ytg >= 5:
                coach_kick_prob = 0.92
            elif down == 6 and ytg >= 3:
                coach_kick_prob = 0.80
            elif down == 5 and ytg >= 8:
                coach_kick_prob = 0.65
            elif down == 5 and ytg >= 5:
                coach_kick_prob = 0.50
            elif down == 5 and ytg >= 3:
                coach_kick_prob = 0.30
            if fg_distance <= 35:
                coach_kick_prob += 0.12
            if random.random() < coach_kick_prob:
                best = 'place_kick'

        if down == 6 and fg_distance <= 50 and 'place_kick' in options:
            if score_diff < 0 and abs(score_diff) <= 4 and 'drop_kick' in options:
                best = 'drop_kick'
            else:
                best = 'place_kick'

        if fp >= 90:
            if ytg <= 1 and down <= 4:
                best = 'go_for_it'
            elif down >= 5 and 'place_kick' in options and fg_distance <= 25:
                best = 'place_kick'
        elif fp >= 80:
            if ytg <= 1 and down <= 3:
                best = 'go_for_it'
            elif down >= 5 and 'place_kick' in options:
                best = 'place_kick'
        else:
            if ytg <= 2 and fp >= 30 and down <= 3:
                best = 'go_for_it'

            if fp >= 60 and best == 'punt':
                if fg_distance <= 58 and 'place_kick' in options:
                    best = 'place_kick'
                elif 'go_for_it' in options:
                    best = 'go_for_it'

            if down == 6 and 'place_kick' in options and fg_distance <= 62:
                best = 'place_kick'

            if down == 5 and 'place_kick' in options and fg_distance <= 58:
                best = 'place_kick'
            elif down == 4 and 'place_kick' in options and fg_distance <= 45 and ytg >= 3:
                if random.random() < 0.55:
                    best = 'place_kick'
            elif down == 4 and 'place_kick' in options and fg_distance <= 40 and ytg >= 8:
                best = 'place_kick'

            if 'place_kick' in options and fg_distance <= 58:
                take_points_prob = 0.0
                if down == 6 and ytg >= 4:
                    take_points_prob = 0.95
                elif down == 6 and ytg >= 2:
                    take_points_prob = 0.80
                elif down >= 5 and ytg >= 6:
                    take_points_prob = 0.78
                elif down >= 5 and ytg >= 4:
                    take_points_prob = 0.62
                elif down >= 5 and ytg >= 2:
                    take_points_prob = 0.48
                elif down >= 4 and ytg >= 8:
                    take_points_prob = 0.65
                elif down >= 4 and ytg >= 5:
                    take_points_prob = 0.50
                elif down >= 4 and ytg >= 3:
                    take_points_prob = 0.35
                elif down >= 3 and ytg >= 14:
                    take_points_prob = 0.55
                elif down >= 3 and ytg >= 12:
                    take_points_prob = 0.40
                if pk_success >= 0.85:
                    take_points_prob += 0.12
                elif pk_success >= 0.70:
                    take_points_prob += 0.08
                if fg_distance <= 40:
                    take_points_prob += 0.10
                if random.random() < take_points_prob:
                    best = 'place_kick'

            if 'drop_kick' in options and fp < 80 and best != 'place_kick':
                if score_diff < -6 and fg_distance <= 45 and kicker_skill >= 65:
                    best = 'drop_kick'
                elif score_diff < -3 and fg_distance <= 38 and down >= 5:
                    best = 'drop_kick'
                if kicker.archetype == "kicking_zb" and fg_distance <= 42 and down >= 4:
                    best = 'drop_kick'
                if down >= 4 and fg_distance <= 35 and random.random() < 0.20:
                    best = 'drop_kick'

        if down <= 3 and best != 'place_kick':
            return None

        type_map = {
            'place_kick': PlayType.PLACE_KICK,
            'drop_kick': PlayType.DROP_KICK,
            'punt': PlayType.PUNT,
            'go_for_it': None,
        }
        return type_map.get(best)

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
                player = random.choice(team_obj.players[:8])
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
        if self.state.down > 5:
            return None
        fp = self.state.field_position
        fg_distance = (100 - fp) + 10
        if fg_distance > 55:
            return None

        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)

        shot_chance = 0.12
        if kicker.archetype == "kicking_zb":
            shot_chance = 0.18

        if self.state.down >= 4:
            shot_chance *= 0.55

        score_diff = self._get_score_diff()
        if score_diff < -6:
            shot_chance *= 1.4
        elif score_diff < -3:
            shot_chance *= 1.2

        if fg_distance <= 35:
            shot_chance *= 1.3
        elif fg_distance <= 30:
            shot_chance *= 1.3

        if random.random() < shot_chance:
            return PlayType.DROP_KICK
        return None

    def simulate_play(self) -> Play:
        self.state.play_number += 1

        pre_snap_pen = self._check_penalties("pre_snap")
        if pre_snap_pen:
            return self._apply_pre_snap_penalty(pre_snap_pen)

        fp = self.state.field_position
        fg_dist_quick = (100 - fp) + 17
        if fp >= 62 and fp <= 80 and self.state.down <= 3:
            early_pk_prob = 0.10
            if fg_dist_quick <= 35:
                early_pk_prob = 0.16
            elif fg_dist_quick <= 45:
                early_pk_prob = 0.13
            if self.state.down == 3 and self.state.yards_to_go >= 5:
                early_pk_prob *= 2.0
            if random.random() < early_pk_prob:
                family = PlayFamily.TERRITORY_KICK
                play = self.simulate_place_kick(family)
                post_pen = self._check_penalties("post_play", play_type=play.play_type)
                if post_pen:
                    play = self._apply_post_play_penalty(post_pen, play)
                return play

        if self.state.down >= 3:
            fg_distance = (100 - self.state.field_position) + 17
            should_evaluate_kick = False
            if self.state.down >= 5:
                should_evaluate_kick = True
            elif self.state.down == 4 and (fg_distance <= 62 or self.state.yards_to_go >= 4):
                should_evaluate_kick = True
            elif self.state.down == 3 and fg_distance <= 45 and self.state.yards_to_go >= 12:
                should_evaluate_kick = True

            if should_evaluate_kick:
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

        weights["territory_kick"] = max(0.02, weights.get("territory_kick", 0.2) * 0.15)

        if ytg <= 3:
            weights["dive_option"] = weights.get("dive_option", 0.1) * 2.0
            weights["power"] = weights.get("power", 0.1) * 2.0
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.4
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.2
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.4
            weights["counter"] = weights.get("counter", 0.05) * 0.8
            weights["draw"] = weights.get("draw", 0.05) * 0.6
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 0.8
        elif ytg <= 10:
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.2
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.2
            weights["counter"] = weights.get("counter", 0.05) * 1.2
            weights["draw"] = weights.get("draw", 0.05) * 1.1
        else:
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.8
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.4
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.2
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.3
            weights["dive_option"] = weights.get("dive_option", 0.1) * 0.5
            weights["power"] = weights.get("power", 0.1) * 0.5

        if fp >= 90:
            weights["dive_option"] = weights.get("dive_option", 0.1) * 2.0
            weights["power"] = weights.get("power", 0.1) * 2.0
            weights["sweep_option"] = weights.get("sweep_option", 0.1) * 1.3
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.3
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.1
        elif fp >= 80:
            weights["dive_option"] = weights.get("dive_option", 0.1) * 1.5
            weights["power"] = weights.get("power", 0.1) * 1.5
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 0.6

        if down >= 5 and ytg >= 10:
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.5
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
        elif quarter == 4 and time_left <= 300 and score_diff < -7:
            weights["speed_option"] = weights.get("speed_option", 0.1) * 1.5
            weights["lateral_spread"] = weights.get("lateral_spread", 0.2) * 1.6
            weights["viper_jet"] = weights.get("viper_jet", 0.05) * 1.4
            weights["dive_option"] = weights.get("dive_option", 0.1) * 0.5
            weights["power"] = weights.get("power", 0.1) * 0.5

        families = list(PlayFamily)
        w = [max(0.01, weights.get(f.value, 0.05)) for f in families]
        return random.choices(families, weights=w)[0]

    def _current_style(self) -> Dict:
        if self.state.possession == "home":
            return self.home_style
        return self.away_style

    def _current_defense(self) -> Dict:
        """Returns the defensive style of the team currently on defense"""
        if self.state.possession == "home":
            return self.away_defense  # Away is on defense when home has ball
        return self.home_defense      # Home is on defense when away has ball

    def calculate_block_probability(self, kick_type: str = "punt") -> float:
        """
        Calculate probability of blocked kick based on offensive/defensive styles.

        Args:
            kick_type: "punt" or "kick" (FG/snapkick)

        Returns:
            Probability of block (0.0 to 1.0)
        """
        base_prob = BASE_BLOCK_PUNT if kick_type == "punt" else BASE_BLOCK_KICK

        # Get offensive style modifier (kicking team)
        offense_style_name = self.home_team.offense_style if self.state.possession == "home" else self.away_team.offense_style
        offense_modifier = OFFENSE_BLOCK_MODIFIERS.get(offense_style_name, 1.0)

        # Get defensive style modifier (rush team)
        defense_style_name = self.away_team.defense_style if self.state.possession == "home" else self.home_team.defense_style
        defense_modifier = DEFENSE_BLOCK_MODIFIERS.get(defense_style_name, 1.0)

        # Apply modifiers
        block_prob = base_prob * offense_modifier * defense_modifier

        return min(0.20, max(0.01, block_prob))  # Cap at 20%, floor at 1%

    def calculate_muff_probability(self) -> float:
        """
        Calculate probability of muffed punt return based on defensive style.

        Returns:
            Probability of muff (0.0 to 1.0)
        """
        # Get receiving team's defensive style (their special teams quality)
        receiving_defense_name = self.away_team.defense_style if self.state.possession == "home" else self.home_team.defense_style

        # Kicking team's defensive style (their coverage quality)
        kicking_defense_name = self.home_team.defense_style if self.state.possession == "home" else self.away_team.defense_style
        coverage_modifier = DEFENSE_MUFF_MODIFIERS.get(kicking_defense_name, 1.0)

        # Base probability modified by kicking team's coverage
        muff_prob = BASE_MUFF_PUNT * coverage_modifier
        muff_prob += self.weather_info.get("muff_modifier", 0.0)

        return min(0.15, max(0.02, muff_prob))

    def get_defensive_read(self, play_family: PlayFamily) -> bool:
        """
        Determines if the defense successfully 'reads' the play.
        A successful read reduces play effectiveness.
        Returns True if defense reads the play correctly.
        """
        defense = self._current_defense()
        base_read_rate = defense.get("read_success_rate", 0.35)

        # Add gameplan bias for specific play families
        gameplan_bias = defense.get("gameplan_bias", {}).get(play_family.value, 0.0)
        total_read_rate = base_read_rate + gameplan_bias

        return random.random() < total_read_rate

    def apply_defensive_modifiers(self, yards_gained: int, play_family: PlayFamily,
                                   is_explosive: bool = False) -> int:
        """
        Applies all defensive modifiers to yards gained.
        This is the core of the defensive system.
        """
        defense = self._current_defense()

        # 1. Check if defense read the play
        defense_read = self.get_defensive_read(play_family)

        # 2. Apply play family modifier
        family_modifier = defense.get("play_family_modifiers", {}).get(play_family.value, 1.0)
        yards_gained = int(yards_gained * family_modifier)

        # 3. If defense read the play, reduce yards by 20-40%
        if defense_read:
            read_reduction = random.uniform(0.70, 0.88)
            yards_gained = int(yards_gained * read_reduction)

        # 4. Apply explosive play suppression (if play is explosive)
        if is_explosive:
            explosive_suppression = defense.get("explosive_suppression", 1.0)
            # If suppression is 0.75, reduce explosive plays by 25%
            if random.random() > explosive_suppression:
                # Explosive play was suppressed, reduce yards
                yards_gained = int(yards_gained * 0.70)

        return yards_gained

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

        # Fatigue resistance reduces the fatigue penalty
        # fatigue_resistance of 0.05 reduces fatigue bonus by 5%
        # fatigue_resistance of -0.05 INCREASES fatigue penalty by 5%
        adjusted_fatigue = 1.0 + (base_fatigue - 1.0) * (1.0 - fatigue_resistance)

        return max(1.0, adjusted_fatigue)

    def _red_zone_td_check(self, new_position: int, yards_gained: int, team: Team) -> bool:
        if yards_gained < 2:
            return False
        if new_position >= 97:
            td_chance = 0.92
            return random.random() < td_chance
        elif new_position >= 95:
            td_chance = 0.82 + (team.avg_speed - 85) * 0.01
            if self.drive_play_count >= 5:
                td_chance += 0.08
            return random.random() < td_chance
        elif new_position >= 90:
            td_chance = 0.65 + (team.avg_speed - 85) * 0.008
            if self.drive_play_count >= 5:
                td_chance += 0.10
            return random.random() < td_chance
        elif new_position >= 85:
            td_chance = 0.45 + (team.avg_speed - 85) * 0.005
            if self.drive_play_count >= 5:
                td_chance += 0.10
            return random.random() < td_chance
        elif new_position >= 80:
            td_chance = 0.28 + (team.avg_speed - 85) * 0.004
            if self.drive_play_count >= 5:
                td_chance += 0.08
            return random.random() < td_chance
        elif new_position >= 75:
            td_chance = 0.12 + (team.avg_speed - 85) * 0.003
            if yards_gained >= 8:
                td_chance += 0.10
            return random.random() < td_chance
        elif new_position >= 70:
            td_chance = 0.05 + (team.avg_speed - 85) * 0.002
            if yards_gained >= 12:
                td_chance += 0.08
            return random.random() < td_chance
        return False

    def _breakaway_check(self, yards_gained: int, team: Team) -> int:
        if yards_gained >= 7:
            speed_gap = (team.avg_speed - 85) / 100
            def_fatigue_bonus = (self._defensive_fatigue_factor() - 1.0)
            breakaway_chance = 0.25 + speed_gap + def_fatigue_bonus
            if self.state.field_position >= 50:
                breakaway_chance += 0.15
            if random.random() < breakaway_chance:
                extra = random.randint(15, 50)
                return yards_gained + extra
        return yards_gained

    def _run_fumble_check(self, family: PlayFamily, yards_gained: int, carrier=None) -> bool:
        config = RUN_PLAY_CONFIG.get(family, RUN_PLAY_CONFIG[PlayFamily.DIVE_OPTION])
        base_fumble = config['fumble_rate']

        if yards_gained <= 0:
            base_fumble += 0.035
        elif yards_gained <= 2:
            base_fumble += 0.015

        if carrier:
            best_power = getattr(carrier, 'stamina', 75)
            if best_power >= 80:
                base_fumble *= 0.75
            elif best_power < 50:
                base_fumble *= 1.20
        else:
            team = self.get_offensive_team()
            best_power = max(p.stamina for p in team.players[:5])
            if best_power >= 80:
                base_fumble *= 0.85
            elif best_power < 50:
                base_fumble *= 1.15

        fatigue_factor = self.get_fatigue_factor()
        if fatigue_factor < 0.85:
            base_fumble += 0.008

        defense = self._current_defense()
        pressure = defense.get("pressure_factor", 0.50)
        if pressure >= 0.80:
            base_fumble += 0.010
        turnover_bonus = defense.get("turnover_bonus", 0.0)
        base_fumble *= (1 + turnover_bonus)

        base_fumble += self.weather_info.get("fumble_modifier", 0.0)

        if carrier and carrier.archetype != "none":
            arch_info = get_archetype_info(carrier.archetype)
            fumble_mod = arch_info.get("fumble_modifier", 1.0)
            if isinstance(fumble_mod, float) and fumble_mod != 1.0:
                base_fumble *= fumble_mod

        return random.random() < base_fumble

    def simulate_run(self, family: PlayFamily = PlayFamily.DIVE_OPTION) -> Play:
        team = self.get_offensive_team()
        config = RUN_PLAY_CONFIG.get(family, RUN_PLAY_CONFIG[PlayFamily.DIVE_OPTION])

        primary_positions = config['primary_positions']
        eligible = [p for p in team.players[:8] if any(
            pos in player_tag(p) for pos in primary_positions
        )]
        if not eligible:
            eligible = team.players[:5]

        weights = []
        for p in eligible:
            w = 1.0
            arch_info = get_archetype_info(p.archetype)
            run_mod = arch_info.get("run_yards_modifier", 1.0)
            if run_mod > 1.0:
                w *= 1.3
            stamina_pct = getattr(p, 'stamina', 75) / 100
            if stamina_pct < 0.6:
                w *= 0.6
            weights.append(max(0.1, w))

        player = random.choices(eligible, weights=weights, k=1)[0]
        plabel = player_label(player)
        ptag = player_tag(player)
        player.game_touches += 1
        action = config['action']

        base_min, base_max = config['base_yards']
        base_center = random.uniform(base_min, base_max)
        variance = config['variance']
        base_yards = random.gauss(base_center, variance)

        arch_info = get_archetype_info(player.archetype)
        run_arch_mod = arch_info.get("run_yards_modifier", 1.0)
        base_yards *= run_arch_mod

        speed_weather_mod = 1.0 + self.weather_info.get("speed_modifier", 0.0)
        base_yards *= speed_weather_mod

        style = self._current_style()
        strength_factor = team.avg_speed / 90
        fatigue_factor = self.get_fatigue_factor()
        fatigue_resistance = style.get("fatigue_resistance", 0.0)
        fatigue_factor = min(1.0, fatigue_factor + fatigue_resistance)
        viper_factor = self.calculate_viper_impact()
        def_fatigue = self._defensive_fatigue_factor()

        run_bonus = style.get("run_bonus", 0.0)
        if family in (PlayFamily.DIVE_OPTION, PlayFamily.SWEEP_OPTION, PlayFamily.POWER):
            run_bonus_factor = 1.0 + run_bonus
        else:
            run_bonus_factor = 1.0

        option_read_bonus = style.get("option_read_bonus", 0.0)
        if family in (PlayFamily.SPEED_OPTION, PlayFamily.DIVE_OPTION) and option_read_bonus > 0:
            run_bonus_factor *= (1.0 + option_read_bonus)

        fp = self.state.field_position
        if fp <= 25:
            territory_mod = 0.80
        elif fp <= 40:
            territory_mod = 0.88
        elif fp <= 55:
            territory_mod = 0.95
        elif fp <= 70:
            territory_mod = 1.10
        elif fp <= 85:
            territory_mod = 1.20
        else:
            territory_mod = 1.30

        defense = self._current_defense()
        def_family_mod = defense.get("play_family_modifiers", {}).get(family.value, 1.0)
        gap_breakdown_chance = 0.08

        defensive_stiffening = 1.0
        if self.state.field_position >= 85:
            defensive_stiffening = 0.96
        elif self.state.field_position >= 70:
            defensive_stiffening = 0.86
        elif self.state.field_position >= 55:
            defensive_stiffening = 0.84
        elif self.state.field_position >= 45:
            defensive_stiffening = 0.93

        safety_chance = 0.0
        if self.state.field_position <= 2:
            safety_chance = 0.14
        elif self.state.field_position <= 5:
            safety_chance = 0.09
        elif self.state.field_position <= 10:
            safety_chance = 0.05
        elif self.state.field_position <= 15:
            safety_chance = 0.025
        elif self.state.field_position <= 20:
            safety_chance = 0.0120

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
                description=f"{ptag} {action} → swarmed in own end zone — SAFETY! (+2 defensive)",
                fatigue=round(stamina, 1),
            )

        if random.random() < gap_breakdown_chance:
            yards_gained = random.randint(-3, 1)
        elif random.random() < 0.18:
            yards_gained = random.randint(1, 4)
        elif random.random() < 0.25:
            pre_contact = base_yards * strength_factor * fatigue_factor * run_bonus_factor * territory_mod * defensive_stiffening
            yards_gained = int(pre_contact * random.uniform(0.6, 0.85))
        else:
            yards_gained = int(base_yards * strength_factor * fatigue_factor * viper_factor * def_fatigue * run_bonus_factor * territory_mod * def_family_mod * defensive_stiffening)

        yards_gained = max(-5, min(yards_gained, 45))

        broken_play_bonus = style.get("broken_play_bonus", 0.0)
        tired_def_broken = style.get("tired_def_broken_play_bonus", 0.0)
        if def_fatigue > 1.0 and tired_def_broken > 0:
            broken_play_bonus += tired_def_broken

        if broken_play_bonus > 0 and yards_gained >= 8:
            if random.random() < broken_play_bonus:
                yards_gained += random.randint(5, 15)

        missed_tackle_chance = 0.08
        if player.archetype in ['elusive_flanker', 'speed_flanker']:
            missed_tackle_chance += 0.05
        if family == PlayFamily.VIPER_JET:
            missed_tackle_chance += 0.04
        if family in (PlayFamily.COUNTER, PlayFamily.DRAW):
            missed_tackle_chance += 0.03
        if yards_gained >= 6 and random.random() < missed_tackle_chance:
            yards_gained = int(yards_gained * random.uniform(1.3, 2.0))

        yards_gained = self._breakaway_check(yards_gained, team)
        yards_gained = self.apply_defensive_modifiers(yards_gained, family, yards_gained >= 15)

        if self._run_fumble_check(family, yards_gained, carrier=player):
            fumble_yards = random.randint(-3, max(1, yards_gained))
            old_pos = self.state.field_position
            fumble_spot = max(1, old_pos + fumble_yards)
            player.game_fumbles += 1

            recovery_chance = 0.65
            defensive_pressure = defense.get("pressure_factor", 0.50)
            recovery_chance += defensive_pressure * 0.05
            turnover_bonus = defense.get("turnover_bonus", 0.0)
            recovery_chance += turnover_bonus * 0.10
            recovery_chance = min(0.82, recovery_chance)

            if random.random() < recovery_chance:
                self.change_possession()
                self.state.field_position = max(1, 100 - fumble_spot)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.add_score(0.5)
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
                    play_type="run", play_family=family.value,
                    players_involved=[plabel],
                    yards_gained=fumble_yards,
                    result=PlayResult.FUMBLE.value,
                    description=f"{ptag} {action} → {fumble_yards} — FUMBLE! Defense recovers — BELL (+½){weather_tag}",
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
                        description=f"{ptag} {action} → FUMBLE recovered by offense but TURNOVER ON DOWNS",
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
                    description=f"{ptag} {action} → FUMBLE recovered by offense at {self.state.field_position}",
                    fatigue=round(stamina, 1),
                    fumble=True,
                )

        new_position = min(100, self.state.field_position + yards_gained)

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
                description=f"{ptag} {action} → tackled in end zone — SAFETY! (+2 defensive)",
                fatigue=round(stamina, 1),
            )

        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            player.game_tds += 1
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained} — TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained} — FIRST DOWN"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            player.game_yards += yards_gained
            player.game_rushing_yards += yards_gained
            description = f"{ptag} {action} → {yards_gained}"

            if self.state.down > 6:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

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
            description=description,
            fatigue=round(stamina, 1),
        )

    def simulate_lateral_chain(self, family: PlayFamily = PlayFamily.LATERAL_SPREAD) -> Play:
        team = self.get_offensive_team()
        style = self._current_style()

        chain_length = random.randint(2, 5)
        players_involved = random.sample(team.players[:8], min(chain_length, len(team.players[:8])))
        chain_tags = " → ".join(player_tag(p) for p in players_involved)
        chain_labels = [player_label(p) for p in players_involved]

        per_exchange_fumble = 0.014
        fumble_prob = 1.0 - (1.0 - per_exchange_fumble) ** chain_length
        fumble_prob += self.weather_info.get("lateral_fumble_modifier", 0.0)
        if self.drive_play_count >= 6:
            fumble_prob += random.uniform(0.008, 0.015)
        if chain_length >= 3:
            fumble_prob += 0.008
        if chain_length >= 4:
            fumble_prob += 0.010
        fatigue_factor_lat = self.get_fatigue_factor()
        if fatigue_factor_lat < 0.9:
            fumble_prob += 0.012

        tempo = style.get("tempo", 0.5)
        fumble_prob *= (1 + (tempo - 0.5) * 0.10)

        lateral_success_bonus = style.get("lateral_success_bonus", 0.0)
        fumble_prob *= (1 - lateral_success_bonus)

        fumble_prob *= style.get("lateral_risk", 1.0)
        prof_reduction = max(0.85, team.lateral_proficiency / 100)
        fumble_prob /= prof_reduction

        # DEFENSIVE SYSTEM: Apply defensive pressure to lateral chains
        defense = self._current_defense()
        defensive_pressure = defense.get("pressure_factor", 0.50)
        fumble_prob *= (1 + defensive_pressure * 0.15)  # Pressure increases fumble chance

        # DEFENSIVE SYSTEM: Apply turnover bonus
        turnover_bonus = defense.get("turnover_bonus", 0.0)
        fumble_prob *= (1 + turnover_bonus)

        if random.random() < fumble_prob:
            yards_gained = random.randint(-5, 8)
            old_pos = self.state.field_position

            fumbler = random.choice(players_involved)
            fumbler.game_fumbles += 1

            recovery_chance = 0.65
            defensive_pressure = defense.get("pressure_factor", 0.50)
            recovery_chance += defensive_pressure * 0.05
            recovery_chance = min(0.80, recovery_chance)

            if random.random() < recovery_chance:
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

        base_yards = random.gauss(5, 5)
        lateral_bonus = chain_length * 1.5
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()
        def_fatigue = self._defensive_fatigue_factor()

        tired_def_yardage = style.get("tired_def_yardage_bonus", 0.0)
        if def_fatigue > 1.0 and tired_def_yardage > 0:
            def_fatigue += tired_def_yardage

        fp = self.state.field_position
        if fp <= 25:
            lat_territory_mod = 0.75
        elif fp <= 40:
            lat_territory_mod = 0.85
        elif fp <= 55:
            lat_territory_mod = 0.95
        elif fp <= 70:
            lat_territory_mod = 1.15
        elif fp <= 85:
            lat_territory_mod = 1.30
        else:
            lat_territory_mod = 1.45

        yards_gained = int((base_yards + lateral_bonus) * fatigue_factor * viper_factor * def_fatigue * lat_territory_mod)
        yards_gained = max(-5, min(yards_gained, 55))

        # Check for explosive lateral play
        is_explosive = False
        explosive_lateral_bonus = style.get("explosive_lateral_bonus", 0.0)
        explosive_chance = chain_length * 0.05 + explosive_lateral_bonus
        if yards_gained >= 10 and random.random() < explosive_chance:
            extra = random.randint(8, 30)
            yards_gained += extra
            is_explosive = True

        # DEFENSIVE SYSTEM: Apply all defensive modifiers
        yards_gained = self.apply_defensive_modifiers(yards_gained, family, is_explosive or yards_gained >= 15)

        new_position = min(100, self.state.field_position + yards_gained)

        for p in players_involved:
            p.game_touches += 1
        for p in players_involved[:-1]:
            p.game_laterals_thrown += 1
        ball_carrier = players_involved[-1]

        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            ball_carrier.game_tds += 1
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
            description=description,
            fatigue=round(stamina, 1),
            laterals=chain_length,
        )

    def simulate_punt(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        punter = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(punter)

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
                blocker = max(def_team.players[:5], key=lambda p: p.speed)
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
                    blocker = max(def_team.players[:5], key=lambda p: p.speed)
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
        distance = max(20, min(distance, 85))

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
            returner = max(def_team.players[:5], key=lambda p: p.speed)
            rtag = player_tag(returner)

            # Calculate where the punt landed
            landing_spot = min(99, self.state.field_position + distance)

            # 55% return team recovers (bad field position)
            # 45% kicking team recovers (bell + short field)
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
                kicker_recoverer = max(team.players[:8], key=lambda p: p.speed)
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

        if random.random() < 0.03:
            def_team = self.get_defensive_team()
            returner = max(def_team.players[:5], key=lambda p: p.speed)
            rtag = player_tag(returner)
            self.change_possession()
            self.add_score(9)
            new_pos = 100 - min(99, self.state.field_position + distance)
            self.apply_stamina_drain(2)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number, quarter=self.state.quarter,
                time=self.state.time_remaining, possession=self.state.possession,
                field_position=self.state.field_position, down=1, yards_to_go=20,
                play_type="punt", play_family=family.value,
                players_involved=[player_label(punter), player_label(returner)],
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

        new_position = 100 - min(99, self.state.field_position + distance)

        self.change_possession()
        self.state.field_position = max(1, new_position)
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
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="punt",
            play_family=family.value,
            players_involved=[player_label(punter)],
            yards_gained=-distance,
            result="punt",
            description=f"{ptag} punt → {distance} yards",
            fatigue=round(stamina, 1),
        )

    def get_defensive_team(self) -> Team:
        return self.away_team if self.state.possession == "home" else self.home_team

    def simulate_drop_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        # SPECIAL TEAMS CHAOS: Check for blocked kick FIRST
        block_prob = self.calculate_block_probability(kick_type="kick")
        if random.random() < block_prob:
            # BLOCKED KICK!
            def_team = self.get_defensive_team()
            blocker = max(def_team.players[:5], key=lambda p: p.speed)
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
            if any(k in p.position for k in ["Safety", "Keeper"]):
                keeper = p
                break
        if keeper is None:
            keeper = max(def_team.players[-3:], key=lambda p: p.speed)

        keeper.game_coverage_snaps += 1

        keeper_arch = get_archetype_info(keeper.archetype)
        deflection_base = 0.08
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

        skill_factor = kicker.kicking / 85
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)

        arch_info = get_archetype_info(kicker.archetype)
        kick_arch_bonus = arch_info.get("kick_accuracy_bonus", 0.0)

        if distance <= 25:
            base_prob = 0.72
        elif distance <= 35:
            base_prob = 0.60
        elif distance <= 45:
            base_prob = 0.45
        elif distance <= 55:
            base_prob = 0.30
        else:
            base_prob = max(0.08, 0.30 - (distance - 55) * 0.015)

        weather_kick_mod = self.weather_info.get("kick_accuracy_modifier", 0.0)
        success_prob = base_prob * skill_factor * (1.0 + kick_acc + kick_arch_bonus + weather_kick_mod)
        kicker.game_kick_attempts += 1

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(5)
            kicker.game_kick_makes += 1
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
            recovery_chance = 0.35
            if kicker.archetype == "kicking_zb":
                recovery_chance = 0.40

            landing_offset = random.randint(5, 15)
            ball_landing = self.state.field_position + landing_offset
            kicking_team = self.state.possession
            receiving = "away" if kicking_team == "home" else "home"

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
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        # SPECIAL TEAMS CHAOS: Check for blocked kick FIRST
        block_prob = self.calculate_block_probability(kick_type="kick")
        if random.random() < block_prob:
            # BLOCKED KICK!
            def_team = self.get_defensive_team()
            blocker = max(def_team.players[:5], key=lambda p: p.speed)
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

        if distance <= 25:
            success_prob = 0.93
        elif distance <= 35:
            success_prob = 0.86
        elif distance <= 45:
            success_prob = 0.76
        elif distance <= 55:
            success_prob = 0.62
        else:
            success_prob = max(0.20, 0.62 - (distance - 55) * 0.025)

        skill_factor = kicker.kicking / 85
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)
        arch_info = get_archetype_info(kicker.archetype)
        kick_arch_bonus = arch_info.get("kick_accuracy_bonus", 0.0)
        weather_kick_mod = self.weather_info.get("kick_accuracy_modifier", 0.0)
        success_prob *= skill_factor * (1.0 + kick_acc + kick_arch_bonus + weather_kick_mod)
        kicker.game_kick_attempts += 1

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(3)
            kicker.game_kick_makes += 1
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
                if p.game_touches > 0 or p.game_kick_attempts > 0 or p.game_kick_deflections > 0 or p.game_coverage_snaps > 0:
                    stat_entry = {
                        "tag": player_tag(p),
                        "name": p.name,
                        "archetype": get_archetype_info(p.archetype).get("label", p.archetype) if p.archetype != "none" else "—",
                        "touches": p.game_touches,
                        "yards": p.game_yards,
                        "rushing_yards": p.game_rushing_yards,
                        "lateral_yards": p.game_lateral_yards,
                        "tds": p.game_tds,
                        "fumbles": p.game_fumbles,
                        "laterals_thrown": p.game_laterals_thrown,
                        "kick_att": p.game_kick_attempts,
                        "kick_made": p.game_kick_makes,
                        "kick_deflections": p.game_kick_deflections,
                        "keeper_bells": p.game_keeper_bells,
                        "coverage_snaps": p.game_coverage_snaps,
                        "keeper_tackles": p.game_keeper_tackles,
                        "keeper_return_yards": p.game_keeper_return_yards,
                    }
                    stats.append(stat_entry)
            return sorted(stats, key=lambda x: x["touches"] + x["kick_att"], reverse=True)

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

        run_plays = [p for p in plays if p.play_type == "run"]
        rushing_yards = sum(max(0, p.yards_gained) for p in run_plays)
        lateral_chain_plays = [p for p in plays if p.play_type == "lateral_chain" and not p.fumble]
        lateral_yards = sum(max(0, p.yards_gained) for p in lateral_chain_plays)

        return {
            "total_yards": total_yards,
            "rushing_yards": rushing_yards,
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


def load_team_from_json(filepath: str, fresh: bool = False) -> Team:
    """Load a team from its JSON metadata file.

    Args:
        filepath: Path to the team JSON file.
        fresh: If True, always generate a brand-new roster from the team's
               recruiting_pipeline and philosophy (dynamic mode).  If False,
               load the stored static roster when one is present; fall back to
               dynamic generation when there is no roster section.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")
    abbreviation = data["team_info"]["abbreviation"]
    mascot = data["team_info"]["mascot"]
    style = data.get("style", {}).get("offense_style", "balanced")
    defense_style = data.get("style", {}).get("defense_style", "base_defense")
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
            philosophy=philosophy,
            recruiting_pipeline=recruiting_pipeline,
        )

    # Load the stored roster (static path — used when loading a saved game)
    players = []
    for p_data in data["roster"]["players"][:10]:
        stats = p_data.get("stats", {})
        hometown = p_data.get("hometown", {})
        players.append(
            Player(
                number=p_data["number"],
                name=p_data["name"],
                position=p_data["position"],
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
                hometown_country=hometown.get("country", "USA"),
                high_school=p_data.get("high_school", ""),
                height=p_data.get("height", "5-10"),
                weight=p_data.get("weight", 170),
                year=p_data.get("year", "Sophomore"),
                potential=p_data.get("potential", 3),
                development=p_data.get("development", "normal"),
            )
        )

    return Team(
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
    )


def generate_team_on_the_fly(
    team_name: str,
    abbreviation: str,
    mascot: str,
    offense_style: str = "balanced",
    defense_style: str = "base_defense",
    philosophy: str = "hybrid",
    recruiting_pipeline: Optional[Dict] = None,
) -> Team:
    """
    Generate a fresh Team with unique women players using the name/attribute generators.
    Used when no pre-built roster JSON exists, or to create dynamic teams in season/dynasty mode.
    Players are women only; archetypes are assigned from stats.
    """
    import sys
    from pathlib import Path as _Path
    _root = str(_Path(__file__).parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from scripts.generate_names import generate_player_name
    from scripts.generate_rosters import generate_player_attributes, assign_archetype

    GAME_POSITIONS = [
        "Viper/Back",
        "Zeroback/Back",
        "Halfback/Back",
        "Wingback/End",
        "Shiftback/Back",
        "Back/Safety",
        "Back/Corner",
        "Lineman",
        "Wing/End",
        "Wedge/Line",
    ]

    players = []
    used_numbers: set = set()
    # Viper always #1
    for i, position in enumerate(GAME_POSITIONS):
        number = 1 if i == 0 else None
        while number is None or number in used_numbers:
            number = random.randint(2, 99)
        used_numbers.add(number)

        year = random.choice(["freshman", "sophomore", "junior", "senior"])
        is_viper = (i == 0)

        name_data = generate_player_name(
            school_recruiting_pipeline=recruiting_pipeline,
            year=year,
        )
        attrs = generate_player_attributes(position, philosophy, year, is_viper)
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
            hometown_country=hometown.get("country", "USA"),
            high_school=name_data.get("high_school", ""),
            height=attrs.get("height", "5-10"),
            weight=attrs.get("weight", 170),
            year=year.capitalize(),
            potential=attrs.get("potential", 3),
            development=attrs.get("development", "normal"),
        ))

    avg_speed = sum(p.speed for p in players) // len(players)
    avg_stamina = sum(p.stamina for p in players) // len(players)
    kicking_strength = sum(p.kicking for p in players) // len(players)
    lateral_proficiency = sum(p.lateral_skill for p in players) // len(players)
    defensive_strength = sum(p.tackling for p in players) // len(players)

    return Team(
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
    )


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
            team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")
            teams.append({
                "key": f.replace(".json", ""),
                "name": team_name,
                "abbreviation": data["team_info"]["abbreviation"],
                "mascot": data["team_info"]["mascot"],
                "default_style": style,
                "file": filepath,
            })
    return teams


def get_available_styles() -> Dict:
    return {k: {"label": v["label"], "description": v["description"]} for k, v in OFFENSE_STYLES.items()}
