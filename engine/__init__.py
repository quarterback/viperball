"""
Collegiate Viperball Simulation Engine
"""

from .game_engine import (
    ViperballEngine,
    load_team_from_json,
    generate_team_on_the_fly,
    get_available_teams,
    get_available_styles,
    Team,
    Player,
    OFFENSE_STYLES,
    DEFENSE_STYLES,
)
from .box_score import BoxScoreGenerator
from .poll_system import PollSystem, TeamRecord, calculate_strength_of_schedule
from .epa import calculate_ep, calculate_epa, calculate_drive_epa, calculate_game_epa
from .season import Season, Game, BowlGame, TeamRecord as SeasonTeamRecord, WeeklyPoll, PollRanking, load_teams_from_directory, load_teams_with_states, create_season, generate_bowl_names, get_recommended_bowl_count
from .dynasty import Dynasty, Coach, create_dynasty
from .viperball_metrics import calculate_viperball_metrics
from .ai_coach import assign_ai_scheme, auto_assign_all_teams, get_scheme_label, load_team_identity
from .weather import generate_game_weather, generate_bowl_weather, get_weather_description, describe_conditions, get_climate_zone, WEATHER_DETAILS
from .player_card import PlayerCard, SeasonStats, GameLog, player_to_card, game_result_to_log

__all__ = [
    "ViperballEngine",
    "load_team_from_json",
    "generate_team_on_the_fly",
    "get_available_teams",
    "get_available_styles",
    "Team",
    "Player",
    "OFFENSE_STYLES",
    "DEFENSE_STYLES",
    "BoxScoreGenerator",
    "PollSystem",
    "TeamRecord",
    "calculate_strength_of_schedule",
    "calculate_ep",
    "calculate_epa",
    "calculate_drive_epa",
    "calculate_game_epa",
    "Season",
    "Game",
    "SeasonTeamRecord",
    "load_teams_from_directory",
    "load_teams_with_states",
    "create_season",
    "Dynasty",
    "Coach",
    "create_dynasty",
    "calculate_viperball_metrics",
    "assign_ai_scheme",
    "auto_assign_all_teams",
    "get_scheme_label",
    "load_team_identity",
    "generate_game_weather",
    "generate_bowl_weather",
    "get_weather_description",
    "describe_conditions",
    "get_climate_zone",
    "WEATHER_DETAILS",
    "PlayerCard",
    "SeasonStats",
    "GameLog",
    "player_to_card",
    "game_result_to_log",
]
