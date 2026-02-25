"""
VIPERBALL ANALYTICS ENGINE
Fan-friendly metrics modeled after real sports analytics concepts.

Metrics fans already know, adapted for Viperball:
  - WPA  (Win Probability Added) — from baseball/NFL. How much did each
    play shift the win probability? Calculated in epa.py.
  - WAR  (Wins Above Replacement) — from baseball. How valuable is this
    player compared to a replacement-level player at their position?
  - ZBR  (Zeroback Rating) — like QBR for quarterbacks. Composite rating
    for the Zeroback based on lateral accuracy, yards, TDs, turnovers.
  - VPR  (Viper Rating) — position-specific composite for the Viper.
  - PPD  (Points Per Drive) — scoring efficiency. How many points does
    this team score per offensive possession?
  - TO+/- (Turnover Margin) — turnovers forced minus turnovers lost.
  - Lateral % — lateral chain completion rate.
  - Conversion % — 3rd-or-later down conversion rate.
  - Team Rating — composite 0-100 rating, like ESPN's SP+ or Madden ratings.
"""

import math
import random
from typing import List, Dict


# ═══════════════════════════════════════════════════════════════
# TEAM-LEVEL METRICS
# ═══════════════════════════════════════════════════════════════

def calculate_ppd(drives: List[Dict], team: str) -> float:
    """Points Per Drive (PPD).

    How many points this team scores per offensive possession.
    A fan says: "They averaged 4.2 points per drive."

    Elite: 5.0+  |  Good: 3.5-5.0  |  Average: 2.5-3.5  |  Poor: <2.5
    """
    team_drives = [d for d in drives if d.get("team") == team]
    if not team_drives:
        return 3.0

    scoring_drives = sum(
        1 for d in team_drives
        if d.get("result") in ["touchdown", "successful_kick", "pindown", "safety"]
    )

    # Weighted average points per scoring outcome in Viperball
    # TD = 9, DK = 5, PK = 3, Pindown = 1, Safety = 2
    avg_points_per_scoring_drive = (0.40 * 9 + 0.30 * 4 + 0.20 * 1 + 0.10 * 2)

    scoring_rate = scoring_drives / len(team_drives)
    ppd = scoring_rate * avg_points_per_scoring_drive
    return round(ppd, 2)


def calculate_conversion_pct(plays: List[Dict], team: str) -> float:
    """Conversion % on 3rd-or-later downs.

    A fan says: "They converted 55% of their pressure downs."
    Like 3rd-down conversion % in football — everyone understands this.

    Elite: 55%+  |  Good: 45-55%  |  Average: 35-45%  |  Poor: <35%
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    pressure_plays = [p for p in team_plays if p.get("down", 1) >= 3]

    if not pressure_plays:
        return 50.0

    conversions = sum(
        1 for p in pressure_plays
        if p.get("result") in ["first_down", "touchdown", "successful_kick", "punt_return_td"]
    )

    return round((conversions / len(pressure_plays)) * 100, 1)


def calculate_lateral_pct(plays: List[Dict], team: str) -> float:
    """Lateral chain completion rate (Lateral %).

    A fan says: "They completed 78% of their lateral chains."
    Viperball-specific, but expressed the same way as completion % in football.

    Elite: 80%+  |  Good: 65-80%  |  Average: 50-65%  |  Poor: <50%
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    lateral_plays = [p for p in team_plays if (p.get("laterals") or 0) > 0]

    if not lateral_plays:
        return 0.0

    successful = sum(
        1 for p in lateral_plays
        if p.get("result") not in ["fumble", "turnover_on_downs"]
    )

    return round((successful / len(lateral_plays)) * 100, 1)


def calculate_explosive_plays(plays: List[Dict], team: str) -> int:
    """Count of plays gaining 15+ yards (Explosive Plays).

    A fan says: "They had 8 explosive plays."
    Universal concept — ESPN uses this exact stat.
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    return sum(1 for p in team_plays if (p.get("yards_gained") or 0) >= 15)


def calculate_to_margin(plays: List[Dict], team: str) -> int:
    """Turnover Margin (TO+/-).

    Turnovers forced minus turnovers lost. Every fan knows this.
    A fan says: "They were plus-3 in turnovers."
    """
    turnovers_lost = sum(
        1 for p in plays
        if p.get("possession") == team and p.get("result") in ["fumble", "turnover_on_downs"]
    )

    opponent_plays = [p for p in plays if p.get("possession") != team]
    turnovers_forced = sum(
        1 for p in opponent_plays
        if p.get("result") in ["fumble", "turnover_on_downs", "safety"]
    )

    return turnovers_forced - turnovers_lost


def calculate_avg_start(plays: List[Dict], team: str) -> float:
    """Average starting field position (yard line).

    A fan says: "They started drives at their own 32 on average."
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    if not team_plays:
        return 25.0

    # Use first play of each drive sequence
    drive_starts = []
    prev_poss = None
    for p in plays:
        if p.get("possession") == team and prev_poss != team:
            drive_starts.append(p.get("field_position", 25))
        prev_poss = p.get("possession")

    if not drive_starts:
        return 25.0

    return round(sum(drive_starts) / len(drive_starts), 1)


def calculate_kick_stats(plays: List[Dict], team: str) -> Dict:
    """Kicking game breakdown.

    Returns DK% (drop kick success rate), PK% (place kick success rate),
    and punt average. All concepts fans understand from football.
    """
    team_plays = [p for p in plays if p.get("possession") == team]
    kick_plays = [
        p for p in team_plays
        if p.get("play_type") in ["punt", "drop_kick", "place_kick"]
    ]

    dk_plays = [p for p in kick_plays if p.get("play_type") == "drop_kick"]
    pk_plays = [p for p in kick_plays if p.get("play_type") == "place_kick"]
    punts = [p for p in kick_plays if p.get("play_type") == "punt"]

    dk_made = sum(1 for p in dk_plays if p.get("result") == "successful_kick")
    pk_made = sum(1 for p in pk_plays if p.get("result") == "successful_kick")
    punt_avg = sum(abs(p.get("yards_gained", 0)) for p in punts) / max(1, len(punts))

    return {
        "dk_att": len(dk_plays),
        "dk_made": dk_made,
        "dk_pct": round((dk_made / len(dk_plays) * 100) if dk_plays else 0.0, 1),
        "pk_att": len(pk_plays),
        "pk_made": pk_made,
        "pk_pct": round((pk_made / len(pk_plays) * 100) if pk_plays else 0.0, 1),
        "punt_avg": round(punt_avg, 1),
        "punts": len(punts),
    }


# ═══════════════════════════════════════════════════════════════
# TEAM RATING — Composite 0-100 (like SP+, FPI, or Madden rating)
# ═══════════════════════════════════════════════════════════════

def calculate_team_rating(metrics: Dict) -> float:
    """Team Rating: 0-100 composite score.

    Like ESPN's SP+, College Football Playoff rankings, or a Madden
    team overall. Single number capturing total team quality.

    Built from the fan-friendly sub-metrics, weighted by importance:
      - PPD (scoring) is king: 25%
      - Conversion % matters: 15%
      - TO margin is huge: 20%
      - Lateral game (Viperball's signature): 10%
      - Explosive plays: 10%
      - Kicking game: 10%
      - Field position: 10%
    """
    # Normalize each metric to a 0-100 contribution

    # PPD: 0-10 scale -> 0-100
    ppd_score = min(100, metrics.get("ppd", 3.0) * 10)

    # Conversion %: already 0-100
    conv_score = min(100, max(0, metrics.get("conversion_pct", 40.0)))

    # TO margin: typically -5 to +5 -> map to 0-100 (0 net = 50)
    to_margin = metrics.get("to_margin", 0)
    to_score = min(100, max(0, 50 + to_margin * 10))

    # Lateral %: already 0-100
    lat_score = min(100, max(0, metrics.get("lateral_pct", 50.0)))

    # Explosive plays: typically 0-15 per game -> normalize
    # 8 explosive plays = ~70 score, 12+ = ~100
    explosive = metrics.get("explosive_plays", 4)
    explosive_score = min(100, max(0, explosive * 8.5))

    # Kick game: composite of DK%, PK%, punt avg
    kick = metrics.get("kick_stats", {})
    dk_pct = kick.get("dk_pct", 50.0)
    pk_pct = kick.get("pk_pct", 50.0)
    punt_avg = kick.get("punt_avg", 35.0)
    # Punt avg 40+ is good, 30 is bad -> normalize
    punt_score = min(100, max(0, (punt_avg - 20) * 3.3))
    kick_score = (dk_pct * 0.4 + pk_pct * 0.3 + punt_score * 0.3)

    # Avg starting field position: own 20 = bad, own 40 = great
    avg_start = metrics.get("avg_start", 25.0)
    fp_score = min(100, max(0, (avg_start - 10) * 2.5))

    # Weighted composite
    team_rating = (
        ppd_score * 0.25 +
        conv_score * 0.15 +
        to_score * 0.20 +
        lat_score * 0.10 +
        explosive_score * 0.10 +
        kick_score * 0.10 +
        fp_score * 0.10
    )

    return round(team_rating, 1)


# ═══════════════════════════════════════════════════════════════
# COMPREHENSIVE GAME METRICS — replaces calculate_comprehensive_rating
# ═══════════════════════════════════════════════════════════════

def calculate_comprehensive_rating(plays: List[Dict], drives: List[Dict], team: str) -> Dict:
    """Calculate all fan-friendly metrics for one team in a game.

    Returns a dict with the new metric names. Also includes legacy
    key aliases so existing code doesn't break during migration.
    """
    ppd = calculate_ppd(drives, team)
    conv_pct = calculate_conversion_pct(plays, team)
    lat_pct = calculate_lateral_pct(plays, team)
    explosive = calculate_explosive_plays(plays, team)
    to_margin = calculate_to_margin(plays, team)
    avg_start = calculate_avg_start(plays, team)
    kick = calculate_kick_stats(plays, team)

    metrics = {
        # New fan-friendly metrics
        "ppd": ppd,
        "conversion_pct": conv_pct,
        "lateral_pct": lat_pct,
        "explosive_plays": explosive,
        "to_margin": to_margin,
        "avg_start": avg_start,
        "kick_stats": kick,
        # Legacy aliases for backward compat during migration
        "territory_rating": avg_start * 2.0,  # rough 0-100 proxy
        "pressure_index": conv_pct,            # same concept
        "chaos_factor": lat_pct * 0.7 + min(100, explosive * 8.5) * 0.3,
        "kicking_efficiency": (kick["dk_pct"] * 0.4 + kick["pk_pct"] * 0.3 +
                               min(100, max(0, (kick["punt_avg"] - 20) * 3.3)) * 0.3),
        "drive_quality": ppd,                  # same concept, same scale
        "turnover_impact": min(100, max(0, 50 + to_margin * 10)),
    }

    return metrics


def calculate_overall_performance_index(metrics: Dict) -> float:
    """Calculate Team Rating from metrics dict.

    This function name is kept for backward compat — internally it
    now computes the new Team Rating.
    """
    return calculate_team_rating(metrics)


def calculate_viperball_metrics(game_result: Dict, team: str) -> Dict:
    """Calculate all Viperball analytics for a team from a game result.

    Main entry point used by season.py and UI code.
    Returns dict with all metrics plus the composite Team Rating
    stored under both 'team_rating' and legacy 'opi' keys.
    """
    plays = game_result.get('play_by_play', [])
    drives = game_result.get('drives', [])

    if not drives:
        drives = game_result.get('drive_summary', [])

    metrics = calculate_comprehensive_rating(plays, drives, team)
    team_rating = calculate_team_rating(metrics)
    metrics['team_rating'] = team_rating
    metrics['opi'] = team_rating  # legacy alias

    return metrics


# ═══════════════════════════════════════════════════════════════
# PLAYER-LEVEL METRICS
# ═══════════════════════════════════════════════════════════════

# ── WAR (Wins Above Replacement) ──
# Like baseball WAR — how valuable is this player vs. a replacement?
# Built from YAR (yards above replacement) scaled to wins.

_REPLACEMENT_LEVEL = {
    "Zeroback": 3.8,
    "Viper": 4.2,
    "Halfback": 3.5,
    "Wingback": 3.6,
    "Slotback": 3.4,
    "Keeper": 2.0,
    "Offensive Line": 0.0,
    "Defensive Line": 0.0,
}

# Points per yard (league average) — used to convert YAR to wins
_POINTS_PER_YARD = 0.08  # ~8 points per 100 yards
_POINTS_PER_WIN = 6.0    # ~6 marginal points = 1 marginal win


def calculate_war(player_stats: Dict, position: str = "") -> float:
    """Wins Above Replacement (WAR).

    A fan says: "Their Viper is worth 1.8 WAR this season."
    Same concept as baseball WAR — total player value in wins.

    WAR = (yards_above_replacement * points_per_yard) / points_per_win
    Scaled by volume (touches) with diminishing returns.

    Positive = above replacement, negative = below replacement.
    """
    touches = player_stats.get("touches", 0)
    yards = player_stats.get("yards", 0)
    if touches == 0:
        return 0.0

    yards_per_touch = yards / touches
    replacement = _REPLACEMENT_LEVEL.get(position, 3.5)
    yar_per_touch = yards_per_touch - replacement

    # Volume factor: log scale so high-volume players don't dominate
    volume_factor = math.log(touches + 1) / math.log(20)

    # Convert yard advantage to wins
    total_yar = yar_per_touch * volume_factor * touches
    war = (total_yar * _POINTS_PER_YARD) / _POINTS_PER_WIN

    return round(war, 2)


def calculate_yar(player_stats: Dict, position: str = "") -> float:
    """Yards Above Replacement (YAR) — kept for backward compat.

    Internal building block for WAR. Measures raw yard advantage
    over a replacement-level player.
    """
    touches = player_stats.get("touches", 0)
    yards = player_stats.get("yards", 0)
    if touches == 0:
        return 0.0

    yards_per_touch = yards / touches
    replacement = _REPLACEMENT_LEVEL.get(position, 3.5)
    yar_per_touch = yards_per_touch - replacement

    volume_factor = math.log(touches + 1) / math.log(20)
    return round(yar_per_touch * volume_factor, 2)


def calculate_team_yar(player_stats_list: list) -> float:
    """Sum of individual YAR values for all players on a team."""
    return round(sum(
        calculate_yar(ps, ps.get("position", ""))
        for ps in player_stats_list
    ), 2)


# ── ZBR (Zeroback Rating) ──
# Like QBR for quarterbacks. Composite rating for the Zeroback.

def calculate_zbr(player_stats: Dict) -> float:
    """Zeroback Rating (ZBR) — like QBR for the Zeroback.

    A fan says: "Their Zeroback had a 78.2 ZBR today."
    Composite 0-100 rating based on:
      - Yards per touch (efficiency)
      - Touchdown rate (scoring)
      - Fumble rate (ball security, inverted — fewer = better)
      - Lateral accuracy (successful laterals / attempts)

    Scale: 90+ elite | 70-90 good | 50-70 average | <50 poor
    """
    touches = player_stats.get("touches", 0)
    if touches < 2:
        return 0.0

    yards = player_stats.get("yards", 0)
    tds = player_stats.get("tds", 0)
    fumbles = player_stats.get("fumbles", 0)
    laterals_thrown = player_stats.get("laterals_thrown", 0)
    lateral_assists = player_stats.get("lateral_assists", 0)

    # Yards per touch: 5.0 ypt = ~60 rating, 8.0+ = ~90
    ypt = yards / touches
    ypt_score = min(100, max(0, (ypt - 1.0) * 12.5))

    # TD rate: 1 TD per 10 touches = ~70, per 5 touches = ~90
    td_rate = tds / touches
    td_score = min(100, max(0, td_rate * 500))

    # Fumble rate: 0 fumbles = 100, 1 per 10 touches = ~50
    fumble_rate = fumbles / touches
    fumble_score = max(0, 100 - fumble_rate * 500)

    # Lateral accuracy: successful laterals / total thrown
    if laterals_thrown > 0:
        lat_success = lateral_assists / laterals_thrown
        lat_score = lat_success * 100
    else:
        lat_score = 50.0  # neutral if no laterals

    # Weighted composite
    zbr = (
        ypt_score * 0.35 +
        td_score * 0.25 +
        fumble_score * 0.20 +
        lat_score * 0.20
    )

    return round(zbr, 1)


# ── VPR (Viper Rating) ──
# Position-specific composite for the Viper wild-card role.

def calculate_vpr(player_stats: Dict) -> float:
    """Viper Rating (VPR) — position-specific rating for the Viper.

    A fan says: "Their Viper had a 82.5 VPR — absolute game-wrecker."
    The Viper is the wild card, so VPR emphasizes explosiveness
    and big-play ability over volume.

    Based on:
      - Yards per touch (higher weight — Vipers should be explosive)
      - Big play rate (plays of 15+ yards)
      - Touchdown rate
      - All-purpose yards (rushing + returns + lateral yards)

    Scale: 90+ elite | 70-90 good | 50-70 average | <50 poor
    """
    touches = player_stats.get("touches", 0)
    if touches < 2:
        return 0.0

    yards = player_stats.get("yards", 0)
    tds = player_stats.get("tds", 0)
    all_purpose = player_stats.get("all_purpose_yards", yards)

    # Yards per touch: Vipers should average 5+ yds/touch
    ypt = yards / touches
    ypt_score = min(100, max(0, (ypt - 1.0) * 14))

    # All-purpose yards: 100+ = elite game
    apy_score = min(100, max(0, all_purpose * 0.8))

    # TD rate
    td_rate = tds / touches
    td_score = min(100, max(0, td_rate * 500))

    # Volume bonus: reward getting the ball
    volume_score = min(100, max(0, touches * 6))

    # Weighted composite — explosiveness matters most for Vipers
    vpr = (
        ypt_score * 0.40 +
        td_score * 0.25 +
        apy_score * 0.20 +
        volume_score * 0.15
    )

    return round(vpr, 1)


# ═══════════════════════════════════════════════════════════════
# FPV — Field Position Value (internal use)
# ═══════════════════════════════════════════════════════════════

def calculate_fpv(yardline: int) -> float:
    """Field Position Value: 0-100 scale.

    Internal utility used by other systems. Converts a yard line
    to a 0-100 value emphasizing the red zone.
    """
    yardline = max(1, min(99, yardline))

    if yardline >= 80:
        base_fpv = 70 + (yardline - 80) * 1.5
    elif yardline >= 50:
        base_fpv = 50 + (yardline - 50) * 0.67
    else:
        base_fpv = yardline * 1.0

    return round(min(100, max(0, base_fpv)), 2)


# ═══════════════════════════════════════════════════════════════
# HEADLINE GENERATOR
# Composure-driven narrative templates.
# ═══════════════════════════════════════════════════════════════

_HEADLINE_TEMPLATES = {
    "blowout_win": [
        "{winner} DEMOLISHES {loser} {score}",
        "{winner} cruises past {loser} in blowout",
        "Dominant {winner} rolls over {loser} {score}",
    ],
    "close_win": [
        "{winner} holds on to edge {loser} {score}",
        "Thriller: {winner} survives {loser} scare {score}",
        "{winner} escapes with narrow win over {loser}",
    ],
    "upset": [
        "UPSET! {winner} stuns {loser} {score}",
        "Cinderella: {winner} topples {loser} {score}",
        "{winner} pulls off massive upset over {loser}",
    ],
    "tilt_collapse": [
        "{loser} COLLAPSES after tilt — {winner} wins {score}",
        "Composure meltdown: {loser} falls apart, {winner} capitalizes {score}",
        "{winner} pounces on tilted {loser} {score}",
    ],
    "comeback": [
        "COMEBACK! {winner} rallies from behind to beat {loser} {score}",
        "{winner} mounts furious comeback to stun {loser}",
        "Down but not out: {winner} storms back for {score} win",
    ],
    "defensive_battle": [
        "Defensive war: {winner} grinds out {score} win over {loser}",
        "Low-scoring affair as {winner} edges {loser} {score}",
    ],
}


def generate_headline(game_summary: Dict) -> str:
    """Generate a narrative headline from a game summary."""
    import random as _rng

    fs = game_summary.get("final_score", {})
    home_score = fs.get("home", {}).get("score", 0)
    away_score = fs.get("away", {}).get("score", 0)
    home_name = fs.get("home", {}).get("team", "Home")
    away_name = fs.get("away", {}).get("team", "Away")

    if home_score > away_score:
        winner, loser = home_name, away_name
        w_score, l_score = home_score, away_score
    else:
        winner, loser = away_name, home_name
        w_score, l_score = away_score, home_score

    margin = abs(w_score - l_score)
    score_str = f"{w_score}-{l_score}"

    v2 = game_summary.get("v2_engine", {})
    home_tilted = v2.get("home_tilted_at_end", False)
    away_tilted = v2.get("away_tilted_at_end", False)
    loser_tilted = (home_tilted and home_score < away_score) or \
                   (away_tilted and away_score < home_score)

    home_prestige = v2.get("home_prestige", 50)
    away_prestige = v2.get("away_prestige", 50)
    if home_score > away_score:
        winner_prestige, loser_prestige = home_prestige, away_prestige
    else:
        winner_prestige, loser_prestige = away_prestige, home_prestige

    is_upset = loser_prestige - winner_prestige > 15

    if loser_tilted and margin > 10:
        category = "tilt_collapse"
    elif is_upset:
        category = "upset"
    elif margin >= 20:
        category = "blowout_win"
    elif margin <= 5:
        category = "close_win"
    elif w_score + l_score < 40:
        category = "defensive_battle"
    else:
        category = "close_win"

    templates = _HEADLINE_TEMPLATES.get(category, _HEADLINE_TEMPLATES["close_win"])
    template = _rng.choice(templates)
    return template.format(winner=winner, loser=loser, score=score_str)
