"""
DTW — Deserve to Win

Adapted from the MLB "Deserve to Win" simulator concept for Viperball.

In baseball, DTW uses batted-ball quality (exit velocity, launch angle,
spray angle) to determine which team *should* have won independent of
outcome luck.  In Viperball, the primary "luck surface" is the Delta
Yards (DYE) system: when you score, the opponent's next drive starts
with preferential field position.  A team that builds a lead gets
progressively *punished* for being ahead — the trailing team gets
shorter fields, potential spark-plug momentum, and can ride that boost
into a comeback.  Conversely, a team can look dominant on paper because
they were trailing and operating from advantaged positions all game.

The DTW model strips this away.  It asks: controlling for the delta
environment each team operated in, who actually played better?

DYE-centric signals (the heart of Viperball DTW):
  - Penalty Kill efficiency: How well did you perform when the delta
    system *punished* you for leading? (drives with delta_cost > 0)
  - Power Play efficiency: How well did you capitalize when you got
    boosted field position from trailing? (drives with delta_cost < 0)
  - Mess Rate: Spread between power-play and penalty-kill scoring rates.
    High mess rate = team only produces when spoon-fed good field position.
  - Delta-Adjusted Yards: Raw yards normalized for starting position.

Supporting signals (traditional efficiency):
  - Conversion rate on pressure downs (4th-6th down)
  - Turnover margin
  - EPA (Expected Points Added)
  - Team Rating composite

Works across all game modes:
  - CVL (college)
  - NVL / WVL / EL / AL / PL / LA (professional)
  - FIV (international)

Key concepts:
  DTW%     — Per-game probability that each team "deserved" to win based
             on delta-adjusted performance quality (always sums to 1.0).
  xWins    — Expected wins over a season (sum of DTW% across all games).
  Luck     — Actual wins minus expected wins.  Positive = lucky.
  Lucky W  — Won despite DTW% < 50% (won when you didn't deserve to).
  Unlucky L— Lost despite DTW% > 50% (lost when you deserved to win).
"""

import math
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# SIGNAL WEIGHTS
# ═══════════════════════════════════════════════════════════════
# DYE signals get the lion's share because they measure true
# performance quality independent of the delta system's distortion.
# Traditional metrics fill in the gaps.

_DTW_WEIGHTS = {
    # DYE-centric (55% total weight)
    "pk_efficiency":   0.20,   # Penalty kill: how you play when punished
    "pk_score_rate":   0.10,   # Can you still score from behind the 8-ball?
    "pp_conversion":   0.10,   # Do you capitalize on boosted field position?
    "mess_rate":       0.10,   # Gap between PP and PK scoring (lower = more consistent)
    "delta_resilience": 0.05,  # Net delta yards absorbed vs inflicted

    # Traditional efficiency (45% total weight)
    "conversion_pct":  0.12,   # Pressure-down conversion %
    "to_margin":       0.10,   # Turnover margin
    "epa":             0.10,   # Total Expected Points Added
    "team_rating":     0.08,   # Composite 0-100 (like SP+)
    "yards_per_play":  0.05,   # Raw offensive efficiency
}


# ═══════════════════════════════════════════════════════════════
# SIGNAL EXTRACTION
# ═══════════════════════════════════════════════════════════════

def _extract_dye(game_result: Dict, side: str) -> Dict[str, float]:
    """Extract DYE (Delta Yards Efficiency) signals for one side.

    Reads the penalty_kill / power_play / neutral bucket stats that
    the game engine already computes post-game.
    """
    stats = game_result.get("stats", {}).get(side, {})
    dye = stats.get("dye", {})

    pk = dye.get("penalty_kill", {})
    pp = dye.get("power_play", {})
    neutral = dye.get("neutral", {})

    # Penalty Kill yards per drive (how you produce when leading / punished)
    pk_ypd = pk.get("yards_per_drive", 0.0)
    pk_score_rate = pk.get("score_rate", 0.0)
    pk_count = pk.get("count", 0)

    # Power Play yards per drive (how you capitalize when trailing / boosted)
    pp_ypd = pp.get("yards_per_drive", 0.0)
    pp_score_rate = pp.get("score_rate", 0.0)
    pp_count = pp.get("count", 0)

    # Neutral baseline
    neut_ypd = neutral.get("yards_per_drive", 0.0)

    # PK Efficiency: ratio of penalty-kill YPD to neutral YPD
    # >1.0 = you produce just as well when punished (elite)
    # <0.5 = you collapse when the delta system pushes you back
    if neut_ypd > 0 and pk_count > 0:
        pk_efficiency = pk_ypd / neut_ypd
    elif pk_count > 0:
        pk_efficiency = pk_ypd / max(pp_ypd, 1.0)
    else:
        pk_efficiency = 1.0  # No penalty-kill drives = neutral assumption

    # PP Conversion: power-play score rate (capitalize on the gift?)
    pp_conversion = pp_score_rate if pp_count > 0 else 50.0

    # Mess Rate: gap between PP and PK scoring rates
    # Low = consistent regardless of delta context = deserving
    # High = only scores when spoon-fed = lucky
    if pk_count > 0 and pp_count > 0:
        mess_rate = pp_score_rate - pk_score_rate
    else:
        mess_rate = 0.0

    # Net delta yards: total delta_yards absorbed (positive = net penalty)
    delta_yards = stats.get("delta_yards", 0)

    return {
        "pk_efficiency": pk_efficiency,
        "pk_score_rate": pk_score_rate,
        "pp_conversion": pp_conversion,
        "mess_rate": mess_rate,
        "delta_yards": delta_yards,
        "pk_count": pk_count,
        "pp_count": pp_count,
    }


def _extract_traditional(game_result: Dict, side: str,
                         metrics: Optional[Dict]) -> Dict[str, float]:
    """Extract traditional efficiency signals for one side."""
    stats = game_result.get("stats", {}).get(side, {})
    fs_metrics = game_result.get("_fast_sim_metrics", {}).get(side, {})
    m = metrics or {}

    team_rating = m.get("team_rating", m.get("opi",
                  fs_metrics.get("territory_rating", 50.0)))
    raw_epa = stats.get("epa", fs_metrics.get("epa", 0.0))
    # EPA may be a dict with sub-fields; extract total_epa if so
    if isinstance(raw_epa, dict):
        epa = raw_epa.get("total_epa", raw_epa.get("epa", 0.0))
    else:
        epa = raw_epa

    total_yards = stats.get("total_yards", fs_metrics.get("total_yards", 0))
    total_plays = stats.get("total_plays", fs_metrics.get("total_plays", 1))
    yards_per_play = total_yards / max(total_plays, 1)

    conversion_pct = m.get("conversion_pct",
                    fs_metrics.get("conversion_pct", 40.0))
    to_margin = m.get("to_margin", fs_metrics.get("to_margin", 0.0))

    return {
        "team_rating": team_rating,
        "epa": epa,
        "yards_per_play": yards_per_play,
        "conversion_pct": conversion_pct,
        "to_margin": to_margin,
    }


# ═══════════════════════════════════════════════════════════════
# EDGE COMPUTATION
# ═══════════════════════════════════════════════════════════════

def _normalize_edge(home_val: float, away_val: float,
                    scale: float = 1.0) -> float:
    """Convert a home-vs-away metric pair into a [-1, +1] edge for home.

    Uses tanh compression so extreme gaps saturate rather than blow up.
    """
    diff = home_val - away_val
    if scale <= 0:
        return 0.0
    return math.tanh(diff / scale)


# Scale factors: how big a gap in each metric is considered decisive.
_EDGE_SCALES = {
    # DYE signals
    "pk_efficiency":   0.50,   # 0.5 ratio gap ≈ decisive (e.g. 1.2 vs 0.7)
    "pk_score_rate":   25.0,   # 25% gap in PK scoring ≈ decisive
    "pp_conversion":   25.0,   # 25% gap in PP scoring ≈ decisive
    "mess_rate":       20.0,   # 20% mess rate gap ≈ decisive (inverted: lower is better)
    "delta_resilience": 15.0,  # 15-yard delta gap ≈ decisive

    # Traditional signals
    "conversion_pct":  20.0,   # 20% conversion gap ≈ decisive
    "to_margin":        3.0,   # 3-turnover gap ≈ decisive
    "epa":             15.0,   # 15 EPA gap ≈ decisive
    "team_rating":     25.0,   # 25-point rating gap ≈ decisive
    "yards_per_play":   3.0,   # 3 YPP gap ≈ decisive
}


def calculate_game_dtw(game_result: Dict,
                       home_metrics: Optional[Dict] = None,
                       away_metrics: Optional[Dict] = None) -> Dict:
    """Calculate Deserve-to-Win probabilities for a completed game.

    The model weights DYE signals heavily: a team that produces on
    penalty-kill drives (when the delta system punishes them for leading)
    is genuinely good.  A team that only scores on power-play drives
    (when trailing and getting boosted field position) is riding the
    system — their wins are luckier than they look.

    Returns:
      home_dtw:          float 0.0-1.0
      away_dtw:          float 0.0-1.0 (= 1 - home_dtw)
      edges:             dict of per-metric edges [-1, +1]
      dye_breakdown:     dict with DYE-specific details per side
      deserved_winner:   "home" | "away" | "toss-up"
      upset:             bool — actual winner had DTW < 0.50
    """
    # Extract all signals
    home_dye = _extract_dye(game_result, "home")
    away_dye = _extract_dye(game_result, "away")
    home_trad = _extract_traditional(game_result, "home", home_metrics)
    away_trad = _extract_traditional(game_result, "away", away_metrics)

    # Build signal pairs for edge computation
    # For DYE metrics, assemble the home/away values
    home_signals = {
        "pk_efficiency": home_dye["pk_efficiency"],
        "pk_score_rate": home_dye["pk_score_rate"],
        "pp_conversion": home_dye["pp_conversion"],
        # Mess rate is INVERTED: lower is better, so negate for edge calc
        "mess_rate": -home_dye["mess_rate"],
        # Delta resilience: negative delta_yards = you were boosted (trailing).
        # Positive = you were penalized (leading). Being penalized and still
        # performing well is the signal. We use PK efficiency for that already,
        # so here we just measure net delta burden absorbed.
        "delta_resilience": -home_dye["delta_yards"],
        # Traditional
        "conversion_pct": home_trad["conversion_pct"],
        "to_margin": home_trad["to_margin"],
        "epa": home_trad["epa"],
        "team_rating": home_trad["team_rating"],
        "yards_per_play": home_trad["yards_per_play"],
    }
    away_signals = {
        "pk_efficiency": away_dye["pk_efficiency"],
        "pk_score_rate": away_dye["pk_score_rate"],
        "pp_conversion": away_dye["pp_conversion"],
        "mess_rate": -away_dye["mess_rate"],
        "delta_resilience": -away_dye["delta_yards"],
        "conversion_pct": away_trad["conversion_pct"],
        "to_margin": away_trad["to_margin"],
        "epa": away_trad["epa"],
        "team_rating": away_trad["team_rating"],
        "yards_per_play": away_trad["yards_per_play"],
    }

    # Compute weighted composite edge
    composite = 0.0
    edges = {}
    for metric, weight in _DTW_WEIGHTS.items():
        edge = _normalize_edge(
            home_signals[metric],
            away_signals[metric],
            _EDGE_SCALES[metric],
        )
        edges[metric] = round(edge, 3)
        composite += edge * weight

    # Convert composite edge to probability via sigmoid
    temperature = 0.35
    home_dtw = 1.0 / (1.0 + math.exp(-composite / temperature))
    home_dtw = max(0.02, min(0.98, home_dtw))
    away_dtw = 1.0 - home_dtw

    # Determine deserved winner
    if abs(home_dtw - 0.50) < 0.03:
        deserved_winner = "toss-up"
    elif home_dtw > 0.50:
        deserved_winner = "home"
    else:
        deserved_winner = "away"

    # Check if actual result was a DTW upset
    fs = game_result.get("final_score", {})
    home_score = fs.get("home", {}).get("score", 0)
    away_score = fs.get("away", {}).get("score", 0)
    if home_score == away_score:
        upset = False
    elif home_score > away_score:
        upset = away_dtw > 0.50
    else:
        upset = home_dtw > 0.50

    home_name = fs.get("home", {}).get("team", "Home")
    away_name = fs.get("away", {}).get("team", "Away")

    return {
        "home_dtw": round(home_dtw, 4),
        "away_dtw": round(away_dtw, 4),
        "home_team": home_name,
        "away_team": away_name,
        "edges": edges,
        "dye_breakdown": {
            "home": {
                "pk_efficiency": round(home_dye["pk_efficiency"], 2),
                "pk_score_rate": round(home_dye["pk_score_rate"], 1),
                "pp_score_rate": round(home_dye["pp_conversion"], 1),
                "mess_rate": round(home_dye["mess_rate"], 1),
                "delta_yards": home_dye["delta_yards"],
                "pk_drives": home_dye["pk_count"],
                "pp_drives": home_dye["pp_count"],
            },
            "away": {
                "pk_efficiency": round(away_dye["pk_efficiency"], 2),
                "pk_score_rate": round(away_dye["pk_score_rate"], 1),
                "pp_score_rate": round(away_dye["pp_conversion"], 1),
                "mess_rate": round(away_dye["mess_rate"], 1),
                "delta_yards": away_dye["delta_yards"],
                "pk_drives": away_dye["pk_count"],
                "pp_drives": away_dye["pp_count"],
            },
        },
        "deserved_winner": deserved_winner,
        "upset": upset,
        "home_score": home_score,
        "away_score": away_score,
    }


# ═══════════════════════════════════════════════════════════════
# SEASON-LEVEL LUCK METRICS
# ═══════════════════════════════════════════════════════════════

def calculate_season_luck(game_dtw_results: List[Dict]) -> Dict[str, Dict]:
    """Calculate season-level luck metrics from a list of per-game DTW results.

    Args:
        game_dtw_results: List of dicts from calculate_game_dtw(), one per game.

    Returns:
        Dict keyed by team name, each containing:
          games_played, actual_wins, expected_wins, luck_differential,
          lucky_wins, unlucky_losses, win_pct, expected_win_pct,
          dtw_record (str like "8.3-4.7"),
          avg_pk_efficiency, avg_mess_rate
    """
    teams: Dict[str, Dict] = {}

    for g in game_dtw_results:
        home = g["home_team"]
        away = g["away_team"]
        home_dtw = g["home_dtw"]
        away_dtw = g["away_dtw"]
        home_score = g["home_score"]
        away_score = g["away_score"]
        dye = g.get("dye_breakdown", {})

        for team_name, dtw_pct, opp_name, team_score, opp_score, side in [
            (home, home_dtw, away, home_score, away_score, "home"),
            (away, away_dtw, home, away_score, home_score, "away"),
        ]:
            if team_name not in teams:
                teams[team_name] = {
                    "team": team_name,
                    "games_played": 0,
                    "actual_wins": 0,
                    "expected_wins": 0.0,
                    "lucky_wins": 0,
                    "unlucky_losses": 0,
                    "total_pk_efficiency": 0.0,
                    "total_mess_rate": 0.0,
                    "total_delta_yards": 0,
                    "game_log": [],
                }

            t = teams[team_name]
            t["games_played"] += 1
            t["expected_wins"] += dtw_pct

            # Accumulate DYE season totals
            side_dye = dye.get(side, {})
            t["total_pk_efficiency"] += side_dye.get("pk_efficiency", 1.0)
            t["total_mess_rate"] += side_dye.get("mess_rate", 0.0)
            t["total_delta_yards"] += side_dye.get("delta_yards", 0)

            won = team_score > opp_score
            if won:
                t["actual_wins"] += 1
            if won and dtw_pct < 0.50:
                t["lucky_wins"] += 1
            if not won and team_score < opp_score and dtw_pct > 0.50:
                t["unlucky_losses"] += 1

            t["game_log"].append({
                "opponent": opp_name,
                "dtw_pct": round(dtw_pct, 4),
                "won": won,
                "score": f"{team_score}-{opp_score}",
                "lucky_win": won and dtw_pct < 0.50,
                "unlucky_loss": (not won and team_score < opp_score
                                 and dtw_pct > 0.50),
            })

    # Compute derived fields
    for t in teams.values():
        gp = t["games_played"]
        aw = t["actual_wins"]
        xw = t["expected_wins"]
        t["expected_wins"] = round(xw, 1)
        t["luck_differential"] = round(aw - xw, 1)
        t["win_pct"] = round(aw / gp, 3) if gp > 0 else 0.0
        t["expected_win_pct"] = round(xw / gp, 3) if gp > 0 else 0.0
        t["dtw_record"] = f"{xw:.1f}-{gp - xw:.1f}"
        t["avg_pk_efficiency"] = round(t["total_pk_efficiency"] / gp, 2) if gp > 0 else 1.0
        t["avg_mess_rate"] = round(t["total_mess_rate"] / gp, 1) if gp > 0 else 0.0

    return teams


def get_luck_rankings(game_dtw_results: List[Dict],
                      sort_by: str = "luck_differential") -> List[Dict]:
    """Return teams sorted by luck metric (default: luck_differential desc).

    Valid sort_by: luck_differential, expected_wins, lucky_wins,
    unlucky_losses, expected_win_pct, avg_pk_efficiency, avg_mess_rate.
    """
    teams = calculate_season_luck(game_dtw_results)
    team_list = list(teams.values())
    team_list.sort(key=lambda t: t.get(sort_by, 0), reverse=True)
    return team_list


def calculate_model_accuracy(game_dtw_results: List[Dict]) -> Dict:
    """How often the DTW favorite actually won.

    Returns dict with: correct, total, accuracy (0.0-1.0).
    """
    correct = 0
    total = 0

    for g in game_dtw_results:
        home_score = g["home_score"]
        away_score = g["away_score"]
        if home_score == away_score:
            continue

        total += 1
        home_won = home_score > away_score
        home_favored = g["home_dtw"] > 0.50

        if home_won == home_favored:
            correct += 1

    return {
        "correct": correct,
        "total": total,
        "accuracy": round(correct / total, 4) if total > 0 else 0.0,
    }


def get_extreme_teams(game_dtw_results: List[Dict]) -> Dict:
    """Identify luckiest and unluckiest teams."""
    teams = calculate_season_luck(game_dtw_results)
    if not teams:
        return {
            "luckiest": {"team": "N/A", "differential": 0.0},
            "unluckiest": {"team": "N/A", "differential": 0.0},
        }

    sorted_teams = sorted(teams.values(),
                          key=lambda t: t["luck_differential"],
                          reverse=True)

    return {
        "luckiest": {
            "team": sorted_teams[0]["team"],
            "differential": sorted_teams[0]["luck_differential"],
        },
        "unluckiest": {
            "team": sorted_teams[-1]["team"],
            "differential": sorted_teams[-1]["luck_differential"],
        },
    }


# ═══════════════════════════════════════════════════════════════
# SINGLE-TEAM GAME LOG
# ═══════════════════════════════════════════════════════════════

def get_team_dtw_log(game_dtw_results: List[Dict],
                     team_name: str) -> List[Dict]:
    """Get the DTW game log for a specific team."""
    teams = calculate_season_luck(game_dtw_results)
    team_data = teams.get(team_name)
    if not team_data:
        return []
    return team_data.get("game_log", [])


# ═══════════════════════════════════════════════════════════════
# HEADLINE GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_dtw_headline(dtw_result: Dict) -> str:
    """Generate a fan-friendly headline for a single game's DTW result.

    Incorporates DYE context when available — e.g. noting when a team
    won purely off power-play drives or survived despite heavy delta
    penalties.
    """
    home = dtw_result["home_team"]
    away = dtw_result["away_team"]
    home_dtw = dtw_result["home_dtw"]
    away_dtw = dtw_result["away_dtw"]
    home_score = dtw_result["home_score"]
    away_score = dtw_result["away_score"]
    upset = dtw_result["upset"]
    dye = dtw_result.get("dye_breakdown", {})

    if home_score > away_score:
        winner, loser = home, away
        winner_dtw = home_dtw
        winner_side = "home"
    elif away_score > home_score:
        winner, loser = away, home
        winner_dtw = away_dtw
        winner_side = "away"
    else:
        return (f"Dead heat: {home} and {away} tie "
                f"— DTW split {home_dtw:.0%} / {away_dtw:.0%}")

    pct = f"{winner_dtw:.0%}"
    winner_dye = dye.get(winner_side, {})
    winner_mess = winner_dye.get("mess_rate", 0)

    # Check if winner rode the power-play boost
    if upset and winner_dtw < 0.35:
        if winner_mess > 30:
            return (f"{winner} steals one on power-play drives alone "
                    f"— just {pct} DTW")
        return f"{winner} steals one — won with just {pct} DTW"
    elif upset:
        loser_pct = f"{1.0 - winner_dtw:.0%}"
        loser_side = "away" if winner_side == "home" else "home"
        loser_dye = dye.get(loser_side, {})
        loser_pk = loser_dye.get("pk_efficiency", 1.0)
        if loser_pk > 1.1:
            return (f"{loser} dominated even on penalty-kill drives but lost "
                    f"— {loser_pct} DTW, unlucky defeat")
        return (f"{loser} outplayed {winner} but lost "
                f"— {loser_pct} DTW, unlucky defeat")
    elif abs(home_dtw - 0.50) < 0.05:
        return (f"Even matchup: {winner} edges {loser} "
                f"— DTW {home_dtw:.0%}/{away_dtw:.0%}")
    elif winner_dtw > 0.75:
        return f"{winner} earned it convincingly — {pct} DTW"
    else:
        return f"{winner} deserved the win — {pct} DTW"


def generate_season_luck_summary(game_dtw_results: List[Dict]) -> str:
    """Generate a text summary of season luck standings.

    Includes DYE context: average penalty-kill efficiency and mess rate
    alongside traditional luck metrics.
    """
    rankings = get_luck_rankings(game_dtw_results)
    accuracy = calculate_model_accuracy(game_dtw_results)
    extremes = get_extreme_teams(game_dtw_results)

    lines = [
        "═══ DESERVE TO WIN — SEASON LUCK REPORT ═══",
        "",
        f"Model accuracy: {accuracy['accuracy']:.1%} "
        f"({accuracy['correct']}/{accuracy['total']} games)",
        f"Luckiest team:   {extremes['luckiest']['team']} "
        f"(+{extremes['luckiest']['differential']:.1f} wins)",
        f"Unluckiest team: {extremes['unluckiest']['team']} "
        f"({extremes['unluckiest']['differential']:.1f} wins)",
        "",
        f"{'Team':<25} {'W-L':<8} {'xW-xL':<10} {'Luck':<7} "
        f"{'Lucky W':<8} {'Unlk L':<7} {'PK Eff':<8} {'Mess':<6}",
        "─" * 90,
    ]

    for t in rankings:
        gp = t["games_played"]
        losses = gp - t["actual_wins"]
        record = f"{t['actual_wins']}-{losses}"
        lines.append(
            f"{t['team']:<25} {record:<8} {t['dtw_record']:<10} "
            f"{t['luck_differential']:>+5.1f}   "
            f"{t['lucky_wins']:<8} {t['unlucky_losses']:<7} "
            f"{t['avg_pk_efficiency']:<8.2f} {t['avg_mess_rate']:<6.1f}"
        )

    lines.append("")
    lines.append("PK Eff = Avg Penalty-Kill Efficiency (>1.0 = elite under pressure)")
    lines.append("Mess   = Avg Mess Rate (lower = more consistent across delta contexts)")

    return "\n".join(lines)
