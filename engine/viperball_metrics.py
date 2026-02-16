"""
VIPERBALL SABERMETRICS ENGINE
Positive, interpretable metrics designed specifically for Viperball

Unlike traditional EPA (which can be negative), these metrics are all 0-100 scales
that make intuitive sense for Viperball's unique rules.
"""

import random
from typing import List, Dict


# ========================================
# FIELD POSITION VALUE (FPV)
# ========================================
# Converts yard line to 0-100 value scale
# Higher FPV = better field position
def calculate_fpv(yardline: int) -> float:
    """
    Field Position Value: 0-100 scale
    - Own 1 yard line = FPV of ~5
    - Midfield (50) = FPV of 50
    - Opponent 1 yard line (99) = FPV of ~95

    Formula: Logarithmic curve emphasizing red zone
    """
    yardline = max(1, min(99, yardline))

    # Red zone bonus (past 80 yard line)
    if yardline >= 80:
        base_fpv = 70 + (yardline - 80) * 1.5  # Accelerates in red zone
    elif yardline >= 50:
        base_fpv = 50 + (yardline - 50) * 0.67  # Moderate gain in opponent territory
    else:
        base_fpv = yardline * 1.0  # Linear in own territory

    return round(min(100, max(0, base_fpv)), 2)


# ========================================
# TERRITORY RATING (TR)
# ========================================
# Measures team's field position dominance
def calculate_territory_rating(plays: List[Dict], team: str) -> float:
    """
    Territory Rating: 0-100 scale
    - Higher TR = team controls better field position
    - Weighted by possession time and field position
    - 50 = neutral, 70+ = dominating, <30 = struggling
    """
    team_plays = [p for p in plays if p.get("possession") == team]

    if not team_plays:
        return 50.0

    total_fpv = sum(calculate_fpv(p.get("field_position", 50)) for p in team_plays)
    avg_fpv = total_fpv / len(team_plays)

    # Normalize to 0-100 (avg_fpv ranges from ~5 to ~95)
    territory_rating = avg_fpv

    return round(territory_rating, 2)


# ========================================
# PRESSURE INDEX (PI)
# ========================================
# Offensive efficiency under pressure (3rd/4th/5th down)
def calculate_pressure_index(plays: List[Dict], team: str) -> float:
    """
    Pressure Index: 0-100 scale
    - Measures offensive efficiency on critical downs (3rd, 4th, 5th)
    - 70+ = clutch offense
    - <40 = struggles under pressure
    - 50 = league average
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    pressure_plays = [p for p in team_plays if p.get("down", 1) >= 3]

    if not pressure_plays:
        return 50.0  # Default neutral

    # Count conversions (first downs or scores on pressure situations)
    conversions = sum(
        1 for p in pressure_plays
        if p.get("result") in ["first_down", "touchdown", "successful_kick", "punt_return_td"]
    )

    conversion_rate = conversions / len(pressure_plays)

    # Scale: 0% conversions = 0 PI, 50% = 70 PI, 100% = 100 PI
    # Non-linear to emphasize excellence
    if conversion_rate >= 0.50:
        pressure_index = 70 + (conversion_rate - 0.50) * 60
    else:
        pressure_index = conversion_rate * 140

    return round(min(100, max(0, pressure_index)), 2)


# ========================================
# CHAOS FACTOR (CF)
# ========================================
# Lateral success + explosive plays + chaos events
def calculate_chaos_factor(plays: List[Dict], team: str) -> float:
    """
    Chaos Factor: 0-100 scale
    - Measures team's chaos play success (laterals, explosive plays)
    - High CF = effective lateral chains and big plays
    - Low CF = conservative, low-variance offense
    - 50 = average, 70+ = chaos masters, <30 = risk-averse
    """
    team_plays = [p for p in plays if p.get("possession") == team]

    if not team_plays:
        return 50.0

    # Count chaos elements (handle None values safely)
    lateral_plays = sum(1 for p in team_plays if (p.get("laterals") or 0) > 0)
    successful_laterals = sum(
        1 for p in team_plays
        if (p.get("laterals") or 0) > 0 and p.get("result") not in ["fumble", "turnover_on_downs"]
    )
    explosive_plays = sum(1 for p in team_plays if (p.get("yards_gained") or 0) >= 15)
    chaos_events = sum(1 for p in team_plays if p.get("chaos_event", False))

    # Calculate chaos metrics
    lateral_success_rate = successful_laterals / max(1, lateral_plays)
    explosive_rate = explosive_plays / max(1, len(team_plays))
    chaos_rate = chaos_events / max(1, len(team_plays))

    # Weighted combination
    chaos_factor = (
        lateral_success_rate * 30 +  # Lateral success is worth 30 points
        explosive_rate * 100 * 0.5 +  # Explosive plays worth 50 points
        chaos_rate * 100 * 0.2         # Chaos events worth 20 points
    )

    return round(min(100, max(0, chaos_factor)), 2)


# ========================================
# KICKING EFFICIENCY (KE)
# ========================================
# Pindowns + kick success + field position from kicks
def calculate_kicking_efficiency(plays: List[Dict], team: str) -> float:
    """
    Kicking Efficiency: 0-100 scale
    - Measures special teams effectiveness
    - Pindowns, successful kicks, net punt distance
    - 70+ = elite kicking game
    - <40 = weak special teams
    - 50 = average
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    kick_plays = [
        p for p in team_plays
        if p.get("play_type") in ["punt", "drop_kick", "place_kick"]
    ]

    if not kick_plays:
        return 50.0  # Default neutral

    # Count positive outcomes
    pindowns = sum(1 for p in kick_plays if p.get("result") == "pindown")
    successful_kicks = sum(1 for p in kick_plays if p.get("result") == "successful_kick")
    punt_return_tds_against = sum(1 for p in kick_plays if p.get("result") == "punt_return_td")

    # Calculate net field position gain from punts
    punts = [p for p in kick_plays if p.get("play_type") == "punt"]
    avg_punt_yards = sum(abs(p.get("yards_gained", 0)) for p in punts) / max(1, len(punts))

    # Scoring:
    # - Each pindown = +15 points
    # - Each successful kick = +20 points
    # - Punt return TD against = -30 points
    # - Avg punt yards: 40+ yards = +20 points, <30 yards = 0 points
    score = (
        pindowns * 15 +
        successful_kicks * 20 +
        punt_return_tds_against * -30 +
        max(0, (avg_punt_yards - 30) * 2)
    )

    # Normalize to 0-100 scale
    # Typical range: -30 to +100
    kicking_efficiency = 50 + (score / 2)

    return round(min(100, max(0, kicking_efficiency)), 2)


# ========================================
# DRIVE QUALITY (DQ)
# ========================================
# Points per drive expectancy
def calculate_drive_quality(drives: List[Dict], team: str) -> float:
    """
    Drive Quality: 0-10 scale (points per drive)
    - Higher DQ = more efficient red zone offense
    - 5+ = elite scoring offense
    - <2 = struggles to score
    - 3 = average
    """
    team_drives = [d for d in drives if d.get("team") == team]

    if not team_drives:
        return 3.0  # Default average

    # Count scoring drives (any points)
    scoring_drives = sum(
        1 for d in team_drives
        if d.get("result") in ["touchdown", "successful_kick", "pindown", "safety"]
    )

    # Estimate points per scoring drive (very rough)
    # TD = 9, FG = 3-5, Pindown = 1, Safety = 2
    # Assume: 40% TDs (9pts), 30% FGs (4pts), 20% Pindowns (1pt), 10% Safeties (2pt)
    avg_points_per_scoring_drive = (0.40 * 9 + 0.30 * 4 + 0.20 * 1 + 0.10 * 2)

    scoring_rate = scoring_drives / len(team_drives)
    drive_quality = scoring_rate * avg_points_per_scoring_drive

    return round(drive_quality, 2)


# ========================================
# TURNOVER IMPACT (TI)
# ========================================
# Value of turnovers created vs turnovers lost
def calculate_turnover_impact(plays: List[Dict], team: str) -> float:
    """
    Turnover Impact: 0-100 scale
    - Positive turnovers (created) vs negative turnovers (lost)
    - 70+ = turnover dominance
    - <30 = turnover-prone
    - 50 = neutral
    """
    # Turnovers LOST by this team (when they have possession)
    turnovers_lost = sum(
        1 for p in plays
        if p.get("possession") == team and p.get("result") in ["fumble", "turnover_on_downs"]
    )

    # Turnovers CREATED by this team (when opponent has possession)
    opponent_plays = [p for p in plays if p.get("possession") != team]
    turnovers_created = sum(
        1 for p in opponent_plays
        if p.get("result") in ["fumble", "turnover_on_downs", "safety"]
    )

    # Net turnovers: created - lost
    net_turnovers = turnovers_created - turnovers_lost

    # Scale to 0-100
    # +3 turnovers = 100
    # 0 net = 50
    # -3 turnovers = 0
    turnover_impact = 50 + (net_turnovers * 16.67)

    return round(min(100, max(0, turnover_impact)), 2)


# ========================================
# COMPREHENSIVE TEAM RATING (CTR)
# ========================================
# Overall team performance index
def calculate_comprehensive_rating(plays: List[Dict], drives: List[Dict], team: str) -> Dict:
    """
    Comprehensive Team Rating: Combines all metrics
    Returns a full stat sheet for the team
    """
    return {
        "territory_rating": calculate_territory_rating(plays, team),
        "pressure_index": calculate_pressure_index(plays, team),
        "chaos_factor": calculate_chaos_factor(plays, team),
        "kicking_efficiency": calculate_kicking_efficiency(plays, team),
        "drive_quality": calculate_drive_quality(drives, team),
        "turnover_impact": calculate_turnover_impact(plays, team),
    }


# ========================================
# OVERALL PERFORMANCE INDEX (OPI)
# ========================================
# Single 0-100 number representing overall team performance
def calculate_viperball_metrics(game_result: Dict, team: str) -> Dict:
    """
    Calculate all Viperball metrics for a team from a game result

    Args:
        game_result: Complete game result dictionary from ViperballEngine.simulate_game()
        team: 'home' or 'away'

    Returns:
        Dictionary with all metrics including OPI
    """
    plays = game_result.get('play_by_play', [])
    drives = game_result.get('drives', [])

    # Calculate comprehensive rating
    metrics = calculate_comprehensive_rating(plays, drives, team)

    # Add OPI
    metrics['opi'] = calculate_overall_performance_index(metrics)

    return metrics


def calculate_overall_performance_index(metrics: Dict) -> float:
    """
    Overall Performance Index: 0-100 scale
    - Weighted combination of all metrics
    - 70+ = elite performance
    - 50 = average
    - <40 = poor performance
    """
    weights = {
        "territory_rating": 0.20,
        "pressure_index": 0.15,
        "chaos_factor": 0.10,
        "kicking_efficiency": 0.15,
        "drive_quality": 0.25,  # Highest weight - scoring is what matters
        "turnover_impact": 0.15,
    }

    # Drive quality is 0-10, normalize to 0-100
    normalized_drive_quality = min(100, metrics.get("drive_quality", 3) * 10)

    opi = (
        metrics.get("territory_rating", 50) * weights["territory_rating"] +
        metrics.get("pressure_index", 50) * weights["pressure_index"] +
        metrics.get("chaos_factor", 50) * weights["chaos_factor"] +
        metrics.get("kicking_efficiency", 50) * weights["kicking_efficiency"] +
        normalized_drive_quality * weights["drive_quality"] +
        metrics.get("turnover_impact", 50) * weights["turnover_impact"]
    )

    return round(opi, 2)
