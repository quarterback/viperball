"""
Collegiate Viperball Simulation Engine
"""

from .game_engine import (
    ViperballEngine,
    load_team_from_json,
    get_available_teams,
    get_available_styles,
    Team,
    Player,
    OFFENSE_STYLES,
)
from .box_score import BoxScoreGenerator
from .poll_system import PollSystem, TeamRecord, calculate_strength_of_schedule
from .epa import calculate_ep, calculate_epa, calculate_drive_epa, calculate_game_epa

__all__ = [
    "ViperballEngine",
    "load_team_from_json",
    "get_available_teams",
    "get_available_styles",
    "Team",
    "Player",
    "OFFENSE_STYLES",
    "BoxScoreGenerator",
    "PollSystem",
    "TeamRecord",
    "calculate_strength_of_schedule",
    "calculate_ep",
    "calculate_epa",
    "calculate_drive_epa",
    "calculate_game_epa",
]
