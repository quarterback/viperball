"""
Fast Simulation Model for Viperball
====================================

Lightweight game simulation that generates realistic scores, team stats,
and individual stat leaders WITHOUT running play-by-play. Used for CPU-vs-CPU
games in season/dynasty mode to dramatically improve performance.

Full engine: ~1-3 seconds per game (hundreds of plays)
Fast sim:    ~1-5 milliseconds per game (statistical model)

The model uses team ratings to determine expected scoring, applies broad
variance factors (0.50-1.50) for realistic upset/blowout distributions,
and produces a result dict fully compatible with the existing pipeline.
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════
# SCORING SYSTEM
# ═══════════════════════════════════════════════════════════════
SCORING = {
    "td": 9,        # Touchdown
    "dk": 5,        # Drop kick (snap kick)
    "pk": 3,        # Place kick (field goal)
    "safety": 2,    # Safety
    "rouge": 0.5,   # Rouge (CFL-style single)
    "pindown": 0.5, # Pindown
    "bell": 0.5,    # Bell (chaos recovery)
}

# ═══════════════════════════════════════════════════════════════
# STYLE MODIFIERS
# ═══════════════════════════════════════════════════════════════
# Offense styles affect stat distributions
OFFENSE_STYLE_MODS = {
    "balanced":       {"rush": 1.00, "kick_pass": 1.00, "lateral": 1.00, "dk": 1.00, "td_rate": 1.00},
    "ground_pound":   {"rush": 1.35, "kick_pass": 0.65, "lateral": 0.80, "dk": 0.80, "td_rate": 1.10},
    "air_raid":       {"rush": 0.70, "kick_pass": 1.50, "lateral": 0.90, "dk": 1.15, "td_rate": 0.95},
    "lateral_chaos":  {"rush": 0.85, "kick_pass": 0.85, "lateral": 1.60, "dk": 0.90, "td_rate": 1.00},
    "smashmouth":     {"rush": 1.40, "kick_pass": 0.55, "lateral": 0.70, "dk": 0.70, "td_rate": 1.15},
    "tempo":          {"rush": 1.10, "kick_pass": 1.10, "lateral": 1.10, "dk": 1.05, "td_rate": 1.05},
    "west_coast":     {"rush": 0.90, "kick_pass": 1.25, "lateral": 1.10, "dk": 1.10, "td_rate": 0.95},
    "triple_option":  {"rush": 1.25, "kick_pass": 0.70, "lateral": 1.20, "dk": 0.85, "td_rate": 1.05},
    "power_spread":   {"rush": 1.10, "kick_pass": 1.10, "lateral": 0.90, "dk": 1.10, "td_rate": 1.00},
}

DEFENSE_STYLE_MODS = {
    "swarm":        {"yards_mult": 1.00, "turnover_mult": 1.00, "dk_suppress": 1.00},
    "bend_no_break":{"yards_mult": 1.10, "turnover_mult": 0.80, "dk_suppress": 0.90},
    "blitz_heavy":  {"yards_mult": 0.85, "turnover_mult": 1.25, "dk_suppress": 1.10},
    "zone":         {"yards_mult": 1.05, "turnover_mult": 0.90, "dk_suppress": 0.85},
    "man_press":    {"yards_mult": 0.90, "turnover_mult": 1.15, "dk_suppress": 1.05},
}

# ═══════════════════════════════════════════════════════════════
# V2.7 COACHING FLAVOR (No Named Coaches)
# ═══════════════════════════════════════════════════════════════
# Maps offense_style → (points_mult, variance_mult)
# points_mult: base scoring tendency (explosive styles score more, grinders less)
# variance_mult: how wild the game-to-game swings are (1.0 = baseline)
COACHING_FLAVOR = {
    # Explosive / aggressive styles → higher ceiling, wilder swings
    "air_raid":       (1.08, 1.30),
    "lateral_chaos":  (1.06, 1.35),
    "tempo":          (1.07, 1.20),
    "power_spread":   (1.04, 1.10),
    # Grinding / conservative styles → lower scoring, tighter outcomes
    "ground_pound":   (0.93, 0.75),
    "smashmouth":     (0.91, 0.70),
    "triple_option":  (0.95, 0.80),
    # Balanced / methodical → close to neutral, slightly tighter
    "balanced":       (1.00, 0.90),
    "west_coast":     (1.03, 0.95),
}

# Defense style also shifts expected points allowed
DEFENSE_COACHING_FLAVOR = {
    "swarm":         0.00,   # neutral
    "bend_no_break": 0.03,   # gives up yards, saves points → opponent scores a bit more
    "blitz_heavy":  -0.05,   # aggressive → suppress opponent scoring
    "zone":          0.02,   # conservative → slightly more porous
    "man_press":    -0.03,   # tight coverage → suppress opponent scoring
}


def _coaching_flavor(team, rng: random.Random) -> float:
    """
    Derive a coaching-personality multiplier from team identity.

    Pro teams don't have named coaches — this extracts coaching-like
    scoring effects from offense_style, defense_style, and prestige.
    Returns a multiplier for expected points (0.80-1.20 range).
    """
    style = getattr(team, 'offense_style', 'balanced')
    pts_mult, var_mult = COACHING_FLAVOR.get(style, (1.00, 1.00))

    # Defense style shifts the opponent's expected points, but here
    # we use it to color this team's scoring envelope
    def_style = getattr(team, 'defense_style', 'swarm')
    def_shift = DEFENSE_COACHING_FLAVOR.get(def_style, 0.0)
    # A blitz-heavy defense correlates with an aggressive coaching
    # philosophy that also pushes offense harder
    pts_mult -= def_shift  # blitz_heavy: -(-0.05) = +0.05 boost

    # Prestige widens the gap: elite teams get more from good coaching,
    # weak teams suffer more from bad coaching
    prestige = getattr(team, 'prestige', 50)
    prestige_factor = (prestige - 50) / 200.0  # -0.25 to +0.25
    pts_mult += prestige_factor * abs(pts_mult - 1.0) * 1.5

    # High-prestige → tighter variance (consistent); low → wilder
    if prestige >= 80:
        var_mult *= 0.85
    elif prestige >= 65:
        var_mult *= 0.92
    elif prestige <= 30:
        var_mult *= 1.20
    elif prestige <= 45:
        var_mult *= 1.10

    # Game-to-game random swing within the variance envelope
    swing = rng.gauss(0, 0.04) * var_mult

    return max(0.80, min(1.20, pts_mult + swing))


def _team_strength(team) -> float:
    """Calculate composite team strength (0-100 scale) from ratings."""
    players = team.players
    if not players:
        return 50.0

    avg_ovr = sum(p.overall for p in players) / len(players)

    off_components = (
        team.avg_speed * 0.25 +
        team.lateral_proficiency * 0.20 +
        team.kicking_strength * 0.15 +
        team.prestige * 0.15 +
        avg_ovr * 0.25
    )
    return min(99, max(20, off_components))


def _defensive_strength(team) -> float:
    """Calculate defensive strength from team attributes."""
    avg_ovr = sum(p.overall for p in team.players) / max(1, len(team.players))
    return (
        team.defensive_strength * 0.40 +
        team.prestige * 0.20 +
        avg_ovr * 0.25 +
        team.avg_speed * 0.15
    )


def _win_probability(home_str: float, away_str: float,
                     home_def: float, away_def: float,
                     is_rivalry: bool = False,
                     neutral_site: bool = False) -> float:
    """Calculate home team win probability using power differential."""
    home_power = home_str * 0.55 + home_def * 0.45
    away_power = away_str * 0.55 + away_def * 0.45

    diff = home_power - away_power

    if not neutral_site:
        diff += 3.0

    if is_rivalry:
        diff *= 0.75

    win_prob = 1.0 / (1.0 + math.exp(-diff / 12.0))
    return max(0.05, min(0.95, win_prob))


def _expected_points(team_str: float, opp_def: float, rng: random.Random) -> float:
    """Calculate expected points for a team based on matchup quality."""
    power_ratio = team_str / max(30, opp_def)

    base_points = 28.0 + (power_ratio - 1.0) * 40.0

    variance = rng.uniform(0.50, 1.50)
    return max(3.0, base_points * variance)


def _generate_scoring_events(total_points: float, team, opp_def_str: float,
                             rng: random.Random) -> Dict:
    """Break total points into specific scoring events."""
    off_mods = OFFENSE_STYLE_MODS.get(team.offense_style, OFFENSE_STYLE_MODS["balanced"])

    is_kicking_specialist = team.kicking_strength >= 80
    kick_players = [p for p in team.players if p.kicking >= 80]
    has_kicker = len(kick_players) > 0 or is_kicking_specialist

    target_dks = rng.gauss(3.8, 1.2) * off_mods["dk"]
    if has_kicker:
        target_dks *= rng.uniform(1.2, 1.8)
    target_dks = max(0, target_dks)

    target_pks = max(0, rng.gauss(3.5, 1.5))

    dk_points = round(target_dks) * SCORING["dk"]
    pk_attempts = max(0, round(target_pks))
    pk_make_rate = 0.55 + (team.kicking_strength - 50) / 200.0
    pk_make_rate = max(0.30, min(0.85, pk_make_rate))
    pk_made = sum(1 for _ in range(pk_attempts) if rng.random() < pk_make_rate)
    pk_points = pk_made * SCORING["pk"]

    misc_points = 0
    rouges = max(0, round(rng.gauss(1.5, 1.0)))
    safeties = 1 if rng.random() < 0.12 else 0
    pindowns = max(0, round(rng.gauss(1.0, 0.8)))
    bells = max(0, round(rng.gauss(0.5, 0.5)))
    misc_points = (rouges * SCORING["rouge"] + safeties * SCORING["safety"] +
                   pindowns * SCORING["pindown"] + bells * SCORING["bell"])

    remaining = max(0, total_points - dk_points - pk_points - misc_points)

    tds = max(0, round(remaining / SCORING["td"]))
    td_points = tds * SCORING["td"]

    actual_total = td_points + dk_points + pk_points + misc_points

    dk_made = max(0, round(target_dks))
    dk_att = dk_made + max(0, round(rng.gauss(1.0, 0.8)))

    return {
        "score": actual_total,
        "touchdowns": tds,
        "dk_made": dk_made,
        "dk_attempted": dk_att,
        "pk_made": pk_made,
        "pk_attempted": pk_attempts,
        "rouges": rouges,
        "safeties": safeties,
        "pindowns": pindowns,
        "bells": bells,
    }


def _generate_dye_data(total_yards: int, total_plays: int,
                       scoring: Dict, rng: random.Random) -> Dict:
    """Generate plausible DYE (Delta Yards Efficiency) data for fast sim."""
    total_drives = max(6, round(rng.gauss(12, 2)))
    pen_count = max(0, round(total_drives * rng.uniform(0.15, 0.35)))
    bst_count = max(0, round(total_drives * rng.uniform(0.15, 0.35)))
    neu_count = max(0, total_drives - pen_count - bst_count)

    ypd_base = total_yards / max(1, total_drives)

    pen_yards = max(0, round(pen_count * ypd_base * rng.uniform(0.6, 0.95)))
    bst_yards = max(0, round(bst_count * ypd_base * rng.uniform(1.05, 1.45)))
    neu_yards = max(0, round(neu_count * ypd_base * rng.uniform(0.85, 1.15)))

    pen_scores = sum(1 for _ in range(pen_count) if rng.random() < 0.20)
    bst_scores = sum(1 for _ in range(bst_count) if rng.random() < 0.35)
    neu_scores = sum(1 for _ in range(neu_count) if rng.random() < 0.28)

    return {
        "penalized": {
            "count": pen_count,
            "total_yards": pen_yards,
            "scores": pen_scores,
            "yards_per_drive": round(pen_yards / max(1, pen_count), 1),
            "score_rate": round(pen_scores / max(1, pen_count) * 100, 1),
            "avg_delta": round(rng.uniform(3, 10), 1) if pen_count > 0 else 0.0,
        },
        "boosted": {
            "count": bst_count,
            "total_yards": bst_yards,
            "scores": bst_scores,
            "yards_per_drive": round(bst_yards / max(1, bst_count), 1),
            "score_rate": round(bst_scores / max(1, bst_count) * 100, 1),
            "avg_delta": round(rng.uniform(3, 10), 1) if bst_count > 0 else 0.0,
        },
        "neutral": {
            "count": neu_count,
            "total_yards": neu_yards,
            "scores": neu_scores,
            "yards_per_drive": round(neu_yards / max(1, neu_count), 1),
            "score_rate": round(neu_scores / max(1, neu_count) * 100, 1),
            "avg_delta": 0.0,
        },
    }


def _generate_down_conversions(total_plays: int, rng: random.Random) -> Dict:
    """Generate plausible 4th/5th/6th down conversion data for fast sim."""
    result = {}
    for d in [4, 5, 6]:
        if d == 4:
            att = max(0, round(total_plays * rng.uniform(0.08, 0.18)))
            conv_rate = rng.uniform(0.55, 0.80)
        elif d == 5:
            att = max(0, round(total_plays * rng.uniform(0.03, 0.10)))
            conv_rate = rng.uniform(0.40, 0.65)
        else:
            att = max(0, round(total_plays * rng.uniform(0.01, 0.05)))
            conv_rate = rng.uniform(0.30, 0.55)
        conv = max(0, round(att * conv_rate))
        result[d] = {
            "attempts": att,
            "converted": conv,
            "rate": round(conv / max(1, att) * 100, 1) if att > 0 else 0.0,
        }
    return result


def _generate_team_stats(scoring: Dict, team, opp_def_str: float,
                         rng: random.Random) -> Dict:
    """Generate realistic team stat lines from scoring events."""
    off_mods = OFFENSE_STYLE_MODS.get(team.offense_style, OFFENSE_STYLE_MODS["balanced"])
    def_mods = DEFENSE_STYLE_MODS.get(getattr(team, 'defense_style', 'swarm'),
                                       DEFENSE_STYLE_MODS["swarm"])

    variance = rng.uniform(0.65, 1.40)

    base_total_yards = 280 + (scoring["touchdowns"] * 35) + (scoring["dk_made"] * 15)
    total_yards = max(100, int(base_total_yards * variance))

    rush_pct = 0.55 * off_mods["rush"]
    kp_pct = 0.25 * off_mods["kick_pass"]
    lat_pct = 0.20 * off_mods["lateral"]
    total_pct = rush_pct + kp_pct + lat_pct
    rush_pct /= total_pct
    kp_pct /= total_pct
    lat_pct /= total_pct

    rushing_yards = max(30, int(total_yards * rush_pct * rng.uniform(0.85, 1.15)))
    kick_pass_yards = max(0, int(total_yards * kp_pct * rng.uniform(0.80, 1.20)))
    lateral_yards = max(0, int(total_yards * lat_pct * rng.uniform(0.75, 1.25)))

    rushing_yards += lateral_yards
    total_yards = rushing_yards + kick_pass_yards

    rushing_carries = max(15, int(rushing_yards / max(1, rng.gauss(4.5, 0.8))))

    kp_completion_rate = 0.58 + (team.kicking_strength - 50) / 250.0
    kp_completion_rate *= rng.uniform(0.80, 1.20)
    kp_completion_rate = max(0.30, min(0.80, kp_completion_rate))
    kp_attempted = max(3, int(rng.gauss(16, 5) * off_mods["kick_pass"]))
    kp_completed = max(0, int(kp_attempted * kp_completion_rate))
    if kick_pass_yards > 0 and kp_completed == 0:
        kp_completed = 1

    kp_tds = min(kp_completed, max(0, round(rng.gauss(1.0, 0.8))))

    kp_ints = 0
    failed = kp_attempted - kp_completed
    if failed > 0:
        int_rate = 0.10 * rng.uniform(0.6, 1.5)
        kp_ints = sum(1 for _ in range(failed) if rng.random() < int_rate)

    lateral_chains = max(0, round(rng.gauss(8, 3) * off_mods["lateral"]))
    lateral_fumble_rate = 0.25 * rng.uniform(0.6, 1.4)
    fumbles_from_laterals = sum(1 for _ in range(lateral_chains) if rng.random() < lateral_fumble_rate)
    successful_laterals = lateral_chains - fumbles_from_laterals
    lateral_ints = max(0, round(rng.gauss(0.5, 0.5)))

    rush_fumbles = max(0, round(rng.gauss(0.8, 0.6)))
    total_fumbles = fumbles_from_laterals + rush_fumbles

    turnovers_on_downs = max(0, round(rng.gauss(1.5, 1.0)))

    rushing_tds = max(0, scoring["touchdowns"] - kp_tds)

    punts = max(1, round(rng.gauss(4.0, 1.5)))
    penalties = max(0, round(rng.gauss(5.0, 2.0)))
    penalty_yards = penalties * round(rng.gauss(8.5, 2.5))

    total_plays = rushing_carries + kp_attempted + lateral_chains + punts + scoring["dk_attempted"] + scoring["pk_attempted"]

    chaos_recoveries = max(0, round(rng.gauss(1.0, 0.8)))

    # Special teams returns
    kick_returns = max(1, round(rng.gauss(4, 1.5)))
    kick_return_yards = max(0, round(kick_returns * rng.gauss(22, 6)))
    kick_return_tds = 1 if rng.random() < 0.04 else 0
    punt_returns = max(0, round(rng.gauss(2.5, 1.2)))
    punt_return_yards = max(0, round(punt_returns * rng.gauss(10, 4)))
    punt_return_tds = 1 if rng.random() < 0.06 else 0

    return {
        "total_yards": total_yards,
        "rushing_carries": rushing_carries,
        "rushing_yards": rushing_yards,
        "rushing_touchdowns": rushing_tds,
        "lateral_yards": lateral_yards,
        "total_plays": total_plays,
        "yards_per_play": round(total_yards / max(1, total_plays), 2),
        "touchdowns": scoring["touchdowns"],
        "kick_returns": kick_returns,
        "kick_return_yards": kick_return_yards,
        "kick_return_tds": kick_return_tds,
        "punt_returns": punt_returns,
        "punt_return_yards": punt_return_yards,
        "punt_return_tds": punt_return_tds,
        "lateral_chains": lateral_chains,
        "successful_laterals": successful_laterals,
        "fumbles_lost": total_fumbles,
        "turnovers_on_downs": turnovers_on_downs,
        "drop_kicks_made": scoring["dk_made"],
        "drop_kicks_attempted": scoring["dk_attempted"],
        "place_kicks_made": scoring["pk_made"],
        "place_kicks_attempted": scoring["pk_attempted"],
        "kick_passes_attempted": kp_attempted,
        "kick_passes_completed": kp_completed,
        "kick_pass_yards": kick_pass_yards,
        "kick_pass_tds": kp_tds,
        "kick_pass_interceptions": kp_ints,
        "lateral_interceptions": lateral_ints,
        "punts": punts,
        "pindowns": scoring["pindowns"],
        "chaos_recoveries": chaos_recoveries,
        "kick_percentage": round(kp_completion_rate * 100, 1),
        "viper_efficiency": round(kick_pass_yards / max(1, kp_attempted), 2),
        "lateral_efficiency": round(successful_laterals / max(1, lateral_chains) * 100, 1),
        "play_family_breakdown": {},
        "avg_fatigue": round(rng.gauss(55, 8), 1),
        "safeties_conceded": scoring["safeties"],
        "down_conversions": _generate_down_conversions(total_plays, rng),
        "penalties": penalties,
        "penalty_yards": penalty_yards,
        "penalties_declined": max(0, round(rng.gauss(1.0, 0.8))),
        # DYE: delta kickoff system data
        "dye": _generate_dye_data(total_yards, total_plays, scoring, rng),
        "bonus_possessions": max(0, round(rng.gauss(1.2, 0.8))),
        "bonus_possession_scores": 1 if rng.random() < 0.15 else 0,
        "bonus_possession_yards": max(0, round(rng.gauss(20, 12))),
        "delta_yards": round(rng.gauss(0, 8), 1),
        "adjusted_yards": total_yards + round(rng.gauss(0, 8), 1),
        "delta_drives": max(0, round(rng.gauss(3, 1.5))),
        "delta_scores": max(0, round(rng.gauss(0.8, 0.6))),
        "compelled_efficiency": round(rng.uniform(15, 45), 1),
        "epa": {
            "total_epa": round(rng.gauss(0, 5), 2),
            "epa_per_play": round(rng.gauss(0, 0.1), 3),
            "wpa": round(rng.gauss(0, 5), 2),
            "wpa_per_play": round(rng.gauss(0, 0.1), 3),
            "offense_epa": round(rng.gauss(0, 4), 2),
            "special_teams_epa": round(rng.gauss(0, 1.5), 2),
            "success_rate": round(rng.uniform(35, 60), 1),
            "explosiveness": round(rng.uniform(0.5, 2.5), 3),
            "total_plays": total_plays,
        },
    }


def _generate_synthetic_metrics(stats: Dict, scoring: Dict,
                                team_str: float, rng: random.Random) -> Dict:
    """Generate plausible viperball metrics without needing play-by-play."""
    strength_factor = (team_str - 50) / 50.0

    territory = 50.0 + strength_factor * 15 + rng.gauss(0, 8)
    territory = max(20, min(85, territory))

    pressure = 50.0 + strength_factor * 12 + rng.gauss(0, 10)
    pressure = max(15, min(90, pressure))

    chaos = 50.0 + rng.gauss(0, 15)
    chaos = max(10, min(95, chaos))

    kick_eff = 50.0 + (scoring["dk_made"] + scoring["pk_made"]) * 5 + rng.gauss(0, 8)
    kick_eff = max(10, min(95, kick_eff))

    tds = scoring["touchdowns"]
    dks = scoring["dk_made"]
    pks = scoring["pk_made"]
    drive_quality = (tds * 1.5 + dks * 1.0 + pks * 0.6) + rng.gauss(0, 1.0)
    drive_quality = max(0.5, min(10.0, drive_quality))

    fumbles = stats.get("fumbles_lost", 0)
    ints_given = stats.get("kick_pass_interceptions", 0) + stats.get("lateral_interceptions", 0)
    tod = stats.get("turnovers_on_downs", 0)
    total_turnovers = fumbles + ints_given + tod
    turnover_impact = 65.0 - total_turnovers * 8 + rng.gauss(0, 5)
    turnover_impact = max(10, min(95, turnover_impact))

    metrics = {
        "territory_rating": round(territory, 2),
        "pressure_index": round(pressure, 2),
        "chaos_factor": round(chaos, 2),
        "kicking_efficiency": round(kick_eff, 2),
        "drive_quality": round(drive_quality, 2),
        "turnover_impact": round(turnover_impact, 2),
    }

    weights = {
        "territory_rating": 0.20,
        "pressure_index": 0.15,
        "chaos_factor": 0.10,
        "kicking_efficiency": 0.15,
        "drive_quality": 0.25,
        "turnover_impact": 0.15,
    }
    normalized_dq = min(100, metrics["drive_quality"] * 10)
    opi = (
        metrics["territory_rating"] * weights["territory_rating"] +
        metrics["pressure_index"] * weights["pressure_index"] +
        metrics["chaos_factor"] * weights["chaos_factor"] +
        metrics["kicking_efficiency"] * weights["kicking_efficiency"] +
        normalized_dq * weights["drive_quality"] +
        metrics["turnover_impact"] * weights["turnover_impact"]
    )
    metrics["opi"] = round(opi, 2)
    metrics["team_rating"] = round(opi, 2)  # fan-friendly alias

    # Defensive impact data for standings accumulation
    opp_drives = max(6, round(rng.gauss(12, 2)))
    def_stops = max(0, round(opp_drives * rng.uniform(0.3, 0.55)))
    metrics["defensive_impact"] = {
        "bonus_possessions": max(0, round(rng.gauss(1.0, 0.8))),
        "bonus_scores": 1 if rng.random() < 0.15 else 0,
        "turnovers_forced": total_turnovers,
        "defensive_stops": def_stops,
        "opponent_drives": opp_drives,
    }

    # Additional fields used by standings
    metrics["explosive_plays"] = max(0, round(rng.gauss(4, 2)))
    to_margin = total_turnovers - max(0, round(rng.gauss(2.5, 1.5)))
    metrics["to_margin"] = round(to_margin, 1)
    metrics["avg_start"] = round(25 + strength_factor * 5 + rng.gauss(0, 3), 1)

    # Fan-friendly metrics: lateral_pct, ppd, conversion_pct
    lat_eff = stats.get("lateral_efficiency", 50.0)
    metrics["lateral_pct"] = round(lat_eff, 1)
    metrics["ppd"] = round(drive_quality, 2)
    metrics["conversion_pct"] = round(pressure, 2)

    return metrics


_FAST_SIM_POS_TAGS = {
    "Zeroback": "ZB",
    "Viper": "VP",
    "Halfback": "HB",
    "Wingback": "WB",
    "Slotback": "SB",
    "Keeper": "KP",
    "Offensive Line": "OL",
    "Defensive Line": "DL",
    "Linebacker": "LB",
    "Cornerback": "CB",
    "Lineman": "LA",
    "Edge Defender": "ED",
}


def _fast_player_tag(player) -> str:
    tag = _FAST_SIM_POS_TAGS.get(player.position, player.position[:2].upper())
    return f"{tag}{player.number}"


def _make_player_entry(player, **overrides) -> Dict:
    """Build a player stat dict matching the full engine's field names."""
    tag = _fast_player_tag(player)
    entry = {
        "tag": tag,
        "name": player.name,
        "position": player.position,
        "overall": player.overall,
        "archetype": getattr(player, 'archetype', ''),
        # Rushing
        "rush_carries": 0,
        "rushing_yards": 0,
        "rushing_tds": 0,
        # Totals
        "yards": 0,
        "tds": 0,
        "touches": 0,
        "fumbles": 0,
        # Kick passing (thrown)
        "kick_passes_thrown": 0,
        "kick_passes_completed": 0,
        "kick_pass_yards": 0,
        "kick_pass_tds": 0,
        "kick_pass_interceptions_thrown": 0,
        # Kick passing (received)
        "kick_pass_receptions": 0,
        # Laterals
        "laterals_thrown": 0,
        "lateral_receptions": 0,
        "lateral_assists": 0,
        "lateral_yards": 0,
        "lateral_tds": 0,
        # Kicking
        "kick_att": 0,
        "kick_made": 0,
        "dk_att": 0,
        "dk_made": 0,
        "pk_att": 0,
        "pk_made": 0,
        "kick_deflections": 0,
        # Defense
        "tackles": 0,
        "tfl": 0,
        "sacks": 0,
        "hurries": 0,
        "kick_pass_ints": 0,
        # Returns & special teams
        "kick_returns": 0,
        "kick_return_yards": 0,
        "kick_return_tds": 0,
        "punt_returns": 0,
        "punt_return_yards": 0,
        "punt_return_tds": 0,
        "muffs": 0,
        "st_tackles": 0,
        "keeper_bells": 0,
        "coverage_snaps": 0,
        "keeper_tackles": 0,
        # Roles
        "off_role": "ROTATION",
        "def_role": "ROTATION",
        "st_role": "ROTATION",
    }
    entry.update(overrides)
    return entry


def _generate_player_stats(team, stats: Dict, scoring: Dict,
                           rng: random.Random) -> List[Dict]:
    """Generate individual player stat leaders from team totals.

    Output field names match the full game engine so the API aggregator
    can combine fast-sim and full-engine results seamlessly.
    """
    players = list(team.players)
    if not players:
        return []

    skill_players = sorted(
        [p for p in players if p.position in ("Viper", "Zeroback", "Halfback", "Wingback", "Slotback")],
        key=lambda p: p.overall,
        reverse=True,
    )[:8]

    defenders = sorted(
        [p for p in players if p.position in ("Defensive Line", "Linebacker", "Cornerback", "Lineman", "Keeper")
         and p not in skill_players],
        key=lambda p: p.tackling,
        reverse=True,
    )[:6]

    kickers = sorted(
        [p for p in players if p.kicking >= 70],
        key=lambda p: p.kicking,
        reverse=True,
    )[:2]

    all_stat_players = []

    total_carries = stats["rushing_carries"]
    total_rush_yards = stats["rushing_yards"]
    total_rush_tds = stats["rushing_touchdowns"]
    total_kp_att = stats["kick_passes_attempted"]
    total_kp_comp = stats["kick_passes_completed"]
    total_kp_yards = stats["kick_pass_yards"]
    total_kp_tds = stats["kick_pass_tds"]
    total_kp_ints = stats.get("kick_pass_interceptions", 0)

    carry_weights = [p.overall + p.speed * 0.3 + rng.gauss(0, 10) for p in skill_players]
    total_w = sum(max(1, w) for w in carry_weights)

    remaining_carries = total_carries
    remaining_rush_yards = total_rush_yards
    remaining_rush_tds = total_rush_tds
    remaining_kp_att = total_kp_att
    remaining_kp_comp = total_kp_comp
    remaining_kp_yards = total_kp_yards
    remaining_kp_tds = total_kp_tds
    remaining_kp_ints = total_kp_ints

    for i, player in enumerate(skill_players):
        is_last = (i == len(skill_players) - 1)
        share = max(1, carry_weights[i]) / total_w

        if is_last:
            carries = remaining_carries
            rush_yards = remaining_rush_yards
            rush_tds = remaining_rush_tds
            kp_att = remaining_kp_att
            kp_comp = remaining_kp_comp
            kp_yards = remaining_kp_yards
            kp_tds = remaining_kp_tds
            kp_ints_thrown = remaining_kp_ints
        else:
            carries = max(0, round(total_carries * share * rng.uniform(0.7, 1.3)))
            carries = min(carries, remaining_carries)
            rush_yards = max(0, round(total_rush_yards * share * rng.uniform(0.7, 1.3)))
            rush_yards = min(rush_yards, remaining_rush_yards)
            rush_tds = min(remaining_rush_tds, 1 if rng.random() < share * 1.5 else 0)

            kp_share = share * (1.3 if player.position == "Zeroback" else 0.7)
            kp_att = max(0, round(total_kp_att * kp_share * rng.uniform(0.6, 1.4)))
            kp_att = min(kp_att, remaining_kp_att)
            kp_comp = max(0, round(total_kp_comp * kp_share * rng.uniform(0.6, 1.4)))
            kp_comp = min(kp_comp, min(kp_att, remaining_kp_comp))
            kp_yards = max(0, round(total_kp_yards * kp_share * rng.uniform(0.6, 1.4)))
            kp_yards = min(kp_yards, remaining_kp_yards)
            kp_tds = min(remaining_kp_tds, 1 if rng.random() < kp_share else 0)
            kp_ints_thrown = min(remaining_kp_ints, 1 if kp_att > 0 and rng.random() < 0.15 else 0)

        remaining_carries -= carries
        remaining_rush_yards -= rush_yards
        remaining_rush_tds -= rush_tds
        remaining_kp_att -= kp_att
        remaining_kp_comp -= kp_comp
        remaining_kp_yards -= kp_yards
        remaining_kp_tds -= kp_tds
        remaining_kp_ints -= kp_ints_thrown

        lateral_chains = max(0, round(rng.gauss(2, 1.5)))
        lat_yards = max(0, round(rng.gauss(8, 5))) if lateral_chains > 0 else 0
        lat_thrown = max(0, round(lateral_chains * rng.uniform(0.3, 0.7)))
        lat_recv = max(0, lateral_chains - lat_thrown)
        lat_assists = max(0, round(lat_thrown * rng.uniform(0.3, 0.8)))

        tackles = max(0, round(rng.gauss(1, 1))) if player.position in ("Halfback", "Wingback") else 0
        fumbles = 1 if rng.random() < 0.08 else 0

        # Receiving: distribute completed passes as receptions
        kp_rec = max(0, round(kp_comp * rng.uniform(0.3, 0.7))) if kp_comp > 0 else 0

        total_yds = rush_yards + lat_yards + kp_yards
        total_tds = rush_tds + kp_tds

        entry = _make_player_entry(
            player,
            rush_carries=carries,
            rushing_yards=rush_yards,
            rushing_tds=rush_tds,
            yards=total_yds,
            tds=total_tds,
            touches=carries + kp_comp + lateral_chains,
            fumbles=fumbles,
            kick_passes_thrown=kp_att,
            kick_passes_completed=kp_comp,
            kick_pass_yards=kp_yards,
            kick_pass_tds=kp_tds,
            kick_pass_interceptions_thrown=kp_ints_thrown,
            kick_pass_receptions=kp_rec,
            laterals_thrown=lat_thrown,
            lateral_receptions=lat_recv,
            lateral_assists=lat_assists,
            lateral_yards=lat_yards,
            lateral_tds=1 if lat_yards > 15 and rng.random() < 0.15 else 0,
            tackles=tackles,
            off_role="STARTER" if i < 4 else "ROTATION",
        )
        all_stat_players.append(entry)

    for player in defenders:
        tackles = max(1, round(rng.gauss(5, 2.5)))
        tfl = max(0, round(rng.gauss(0.8, 0.6)))
        sacks = max(0, round(rng.gauss(0.3, 0.4)))
        hurries = max(0, round(rng.gauss(0.5, 0.5)))
        def_kp_ints = 1 if rng.random() < 0.08 else 0

        entry = _make_player_entry(
            player,
            tackles=tackles,
            tfl=tfl,
            sacks=sacks,
            hurries=hurries,
            kick_pass_ints=def_kp_ints,
            st_tackles=max(0, round(rng.gauss(0.5, 0.5))),
            def_role="STARTER" if tackles >= 4 else "ROTATION",
        )
        all_stat_players.append(entry)

    if kickers and scoring["dk_made"] + scoring["pk_made"] > 0:
        kicker = kickers[0]
        dk_m = scoring["dk_made"]
        dk_a = scoring["dk_attempted"]
        pk_m = scoring["pk_made"]
        pk_a = scoring["pk_attempted"]
        total_kick_att = dk_a + pk_a
        total_kick_made = dk_m + pk_m
        for entry in all_stat_players:
            if entry["name"] == kicker.name:
                entry["dk_made"] = dk_m
                entry["dk_att"] = dk_a
                entry["pk_made"] = pk_m
                entry["pk_att"] = pk_a
                entry["kick_att"] = total_kick_att
                entry["kick_made"] = total_kick_made
                entry["touches"] += total_kick_att
                break
        else:
            entry = _make_player_entry(
                kicker,
                touches=total_kick_att,
                dk_made=dk_m,
                dk_att=dk_a,
                pk_made=pk_m,
                pk_att=pk_a,
                kick_att=total_kick_att,
                kick_made=total_kick_made,
                off_role="STARTER",
                st_role="STARTER",
            )
            all_stat_players.append(entry)

    # ── Special teams returns: distribute to fastest skill players ──
    kr_total = stats.get("kick_returns", 0)
    kr_yards_total = stats.get("kick_return_yards", 0)
    kr_tds_total = stats.get("kick_return_tds", 0)
    pr_total = stats.get("punt_returns", 0)
    pr_yards_total = stats.get("punt_return_yards", 0)
    pr_tds_total = stats.get("punt_return_tds", 0)

    if (kr_total > 0 or pr_total > 0) and skill_players:
        # Pick 1-2 returners (fastest)
        returners = sorted(skill_players[:4], key=lambda p: p.speed, reverse=True)[:2]
        for i, ret_player in enumerate(returners):
            # Find or create the entry
            entry = None
            for e in all_stat_players:
                if e["name"] == ret_player.name:
                    entry = e
                    break
            if not entry:
                entry = _make_player_entry(ret_player, st_role="STARTER")
                all_stat_players.append(entry)

            if i == 0:
                # Primary returner gets majority
                kr = min(kr_total, max(0, round(kr_total * rng.uniform(0.55, 0.85))))
                kr_yds = min(kr_yards_total, max(0, round(kr_yards_total * rng.uniform(0.55, 0.85))))
                pr = min(pr_total, max(0, round(pr_total * rng.uniform(0.55, 0.85))))
                pr_yds = min(pr_yards_total, max(0, round(pr_yards_total * rng.uniform(0.55, 0.85))))
                entry["kick_returns"] = kr
                entry["kick_return_yards"] = kr_yds
                entry["kick_return_tds"] = kr_tds_total
                entry["punt_returns"] = pr
                entry["punt_return_yards"] = pr_yds
                entry["punt_return_tds"] = pr_tds_total
                entry["st_role"] = "STARTER"
                kr_total -= kr
                kr_yards_total -= kr_yds
                pr_total -= pr
                pr_yards_total -= pr_yds
            else:
                # Secondary returner gets the rest
                entry["kick_returns"] = kr_total
                entry["kick_return_yards"] = kr_yards_total
                entry["punt_returns"] = pr_total
                entry["punt_return_yards"] = pr_yards_total
                if kr_total > 0 or pr_total > 0:
                    entry["st_role"] = "STARTER"

    # Distribute ST tackles to defenders
    st_tkl_total = max(0, round(rng.gauss(4, 2)))
    if defenders and st_tkl_total > 0:
        for d_player in defenders:
            for e in all_stat_players:
                if e["name"] == d_player.name:
                    share = max(0, round(st_tkl_total * rng.uniform(0.1, 0.4)))
                    e["st_tackles"] += share
                    break

    all_stat_players.sort(
        key=lambda x: x["touches"] + x["kick_att"] + x["tackles"],
        reverse=True,
    )

    return all_stat_players


def fast_sim_game(home_team, away_team,
                  seed: int = 0,
                  weather: Optional[str] = None,
                  weather_label: str = "Clear",
                  weather_description: str = "Clear skies",
                  is_rivalry: bool = False,
                  neutral_site: bool = False) -> Dict:
    """
    Fast-simulate a Viperball game using a statistical model.

    Returns a result dict compatible with the full engine's output,
    suitable for standings updates, metrics calculation, and UI display.
    Play-by-play and drive logs are empty (fast-sim marker).

    Args:
        home_team: Team object for home side
        away_team: Team object for away side
        seed: Random seed (0 = random)
        weather: Weather condition string
        weather_label: Display label for weather
        weather_description: Weather description text
        is_rivalry: Whether this is a rivalry game
        neutral_site: Whether this is a neutral-site game

    Returns:
        Game result dict compatible with ViperballEngine.simulate_game()
    """
    if seed == 0:
        seed = random.randint(1, 999999)
    rng = random.Random(seed)

    home_str = _team_strength(home_team)
    away_str = _team_strength(away_team)
    home_def = _defensive_strength(home_team)
    away_def = _defensive_strength(away_team)

    home_expected = _expected_points(home_str, away_def, rng)
    away_expected = _expected_points(away_str, home_def, rng)

    # V2.7: Coaching flavor — style/prestige → scoring personality
    home_expected *= _coaching_flavor(home_team, rng)
    away_expected *= _coaching_flavor(away_team, rng)

    if not neutral_site:
        home_expected *= rng.uniform(1.02, 1.12)

    if is_rivalry:
        rivalry_factor = rng.uniform(0.85, 1.15)
        home_expected *= rivalry_factor
        away_expected *= (2.0 - rivalry_factor)

    weather_mult = 1.0
    if weather in ("snow", "blizzard"):
        weather_mult = rng.uniform(0.70, 0.90)
    elif weather in ("rain", "heavy_rain"):
        weather_mult = rng.uniform(0.80, 0.95)
    elif weather in ("wind", "strong_wind"):
        weather_mult = rng.uniform(0.85, 0.95)
    home_expected *= weather_mult
    away_expected *= weather_mult

    home_scoring = _generate_scoring_events(home_expected, home_team, away_def, rng)
    away_scoring = _generate_scoring_events(away_expected, away_team, home_def, rng)

    if home_scoring["score"] == away_scoring["score"]:
        if rng.random() < 0.5:
            home_scoring["score"] += SCORING["rouge"]
            home_scoring["rouges"] += 1
        else:
            away_scoring["score"] += SCORING["rouge"]
            away_scoring["rouges"] += 1

    home_stats = _generate_team_stats(home_scoring, home_team, away_def, rng)
    away_stats = _generate_team_stats(away_scoring, away_team, home_def, rng)

    home_player_stats = _generate_player_stats(home_team, home_stats, home_scoring, rng)
    away_player_stats = _generate_player_stats(away_team, away_stats, away_scoring, rng)

    home_metrics = _generate_synthetic_metrics(home_stats, home_scoring, home_str, rng)
    away_metrics = _generate_synthetic_metrics(away_stats, away_scoring, away_str, rng)

    result = {
        "final_score": {
            "home": {
                "team": home_team.name,
                "score": home_scoring["score"],
                "stats": home_stats,
            },
            "away": {
                "team": away_team.name,
                "score": away_scoring["score"],
                "stats": away_stats,
            },
        },
        "home_style": home_team.offense_style,
        "away_style": away_team.offense_style,
        "home_defense_style": getattr(home_team, 'defense_style', 'swarm'),
        "away_defense_style": getattr(away_team, 'defense_style', 'swarm'),
        "home_st_scheme": getattr(home_team, 'st_scheme', 'aces'),
        "away_st_scheme": getattr(away_team, 'st_scheme', 'aces'),
        "delta_yards": {"home": 0, "away": 0},
        "weather": weather or "clear",
        "weather_label": weather_label,
        "weather_description": weather_description,
        "seed": seed,
        "stats": {
            "home": home_stats,
            "away": away_stats,
        },
        "player_stats": {
            "home": home_player_stats,
            "away": away_player_stats,
        },
        "drive_summary": [],
        "play_by_play": [],
        "in_game_injuries": [],
        "v2_engine": {
            "contest_model": "fast_sim",
            "halo_enabled": False,
            "composure_enabled": False,
            "home_prestige": home_team.prestige,
            "away_prestige": away_team.prestige,
            "home_halo": {"offense": 0, "defense": 0},
            "away_halo": {"offense": 0, "defense": 0},
            "home_stars": [],
            "away_stars": [],
            "composure_final": {"home": 50, "away": 50},
            "composure_timeline": {"home": [], "away": []},
            "home_tilted_at_end": False,
            "away_tilted_at_end": False,
        },
        "modifier_stack": {},
        "adaptation_log": [],
        "_fast_sim": True,
        "_fast_sim_metrics": {
            "home": home_metrics,
            "away": away_metrics,
        },
    }

    return result
