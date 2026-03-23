#!/usr/bin/env python3
"""
Analyze a Viperball game and produce self-describing analytical output.

Generates a report with enough embedded context that any reader (human or LLM)
can understand the sport, the metrics, and what the numbers mean — without
needing prior knowledge of Viperball.

Usage:
    # Analyze an existing play-by-play JSON:
    python analyze_game.py examples/play_by_play_CU_at_MU.json

    # Simulate and analyze a new game:
    python analyze_game.py --sim nyu gonzaga

    # Simulate a full season and analyze:
    python analyze_game.py --season

    # Compare two teams across multiple simulated games:
    python analyze_game.py --matchup nyu gonzaga --games 10
"""

import sys
import json
import os
import math
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import ViperballEngine, load_team_from_json, BoxScoreGenerator
from engine.viperball_metrics import (
    calculate_viperball_metrics,
    calculate_scoring_profile,
    calculate_comprehensive_rating,
    calculate_team_rating,
    calculate_war,
    calculate_zbr,
    calculate_vpr,
    calculate_conversion_by_field_zone,
    calculate_delta_profile,
)
from engine.epa import calculate_game_epa


# ── Context header that makes the output self-describing ──

CONTEXT_HEADER = """
================================================================================
VIPERBALL GAME ANALYSIS
================================================================================

SPORT CONTEXT (for readers unfamiliar with Viperball):
  Viperball is a fictional women's collegiate gridiron sport where the forward
  pass was never invented. Teams move the ball via rushing, lateral passing
  (backward/sideways only), and kick passing (punting to a teammate). Played
  on a 100-yard field with 6 downs to gain 20 yards.

  SCORING:
    TD = 9 pts | Snap Kick = 5 pts | Field Goal = 3 pts | Safety = 2 pts
    Pindown (rouge) = 1 pt — awarded when a kicked ball enters the end zone
      and the receiving team fails to return it out. Like the CFL single.
    Bell = ½ pt — awarded on any loose-ball recovery (fumble, muffed punt,
      blocked kick). Play continues after the bell; it's a live-ball score.
  Typical game scores: 45-70 pts per team (combined 90-140).

  KEY POSITIONS:
  - Zeroback (ZB): The most important player on the field. Receives the
    snap, serves as the primary ball carrier AND the team's kicker (snap
    kicks, kick passes). Everything flows through the Zeroback.
  - Viper (VP): A versatile skill player who lines up anywhere and moves
    pre-snap — Viperball's mismatch creator. Think slot receiver meets
    rugby utility back.

  KEY DIFFERENCES FROM FOOTBALL:
  - No forward passes. Ball moves via rushing, kick passing (punting to a
    teammate), and laterals.
  - Snap kicks (drop kicks) can be attempted on any down for 5 points.
  - Two-way play is mandatory — same players on offense and defense.
  - NO KICKOFFS — THE DELTA YARDS SYSTEM: After each score, the receiving
    team starts at the 20-yard line +/- the current score differential.
    Trailing teams get better field position (down 14 → start at the 34);
    leading teams get worse (up 21 → start at the 1). This is Viperball's
    built-in comeback mechanic and the sport's most distinctive feature.
    Drives with a field position bonus are "power plays"; defending those
    drives while leading from a pushed-back position is a "penalty kill."
  - BONUS POSSESSIONS: When a team intercepts a kick pass, the intercepting
    team runs their drive, then the original team gets the ball back as a
    bonus possession — unless the intercepting team throws an INT back
    (which cancels the bonus). This is one of the most important stats for
    understanding dominant teams: a strong secondary generates extra drives
    that the opponent never gets to match. Inspired by pesäpallo.

METRIC BENCHMARKS:
  PPD (Points/Drive):    Elite 5.0+ | Good 3.5-5.0 | Avg 2.5-3.5 | Poor <2.5
  Conversion %:          Elite 55%+ | Good 45-55%   | Avg 35-45%  | Poor <35%
  Explosive Plays/Game:  Dominant 10+ | Good 6-9 | Average 3-5
  TO Margin:             +3 is significant (4-8 total TOs per game is normal)
  ZBR (Zeroback Rating): 0-158.3 scale (like NFL passer rating)
  VPR (Viper Rating):    0-158.3 scale (same scale as ZBR, emphasizes explosiveness)
================================================================================
""".strip()


def _fmt(v, decimals=1):
    """Format a number, handling half-points."""
    if isinstance(v, float) and abs(v - round(v)) > 0.01:
        whole = int(v)
        if abs(v - whole - 0.5) < 0.01:
            return f"{whole}½" if whole > 0 else "½"
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def _grade(value, thresholds):
    """Grade a value against (threshold, label) pairs, highest first."""
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return thresholds[-1][1]


PPD_GRADES = [(5.0, "ELITE"), (3.5, "Good"), (2.5, "Average"), (0, "Poor")]
CONV_GRADES = [(55, "ELITE"), (45, "Good"), (35, "Average"), (0, "Poor")]
ZBR_GRADES = [(130, "ELITE"), (100, "Great"), (80, "Solid"), (60, "Average"), (0, "Struggling")]


def analyze_game_data(game_data: dict) -> str:
    """Produce a full analytical report from game JSON data."""
    lines = [CONTEXT_HEADER, ""]

    home = game_data['final_score']['home']
    away = game_data['final_score']['away']
    home_stats = game_data['stats']['home']
    away_stats = game_data['stats']['away']
    plays = game_data.get('play_by_play', [])
    drives = game_data.get('drives', game_data.get('drive_summary', []))

    # ── Final Score ──
    lines.append(f"MATCHUP: {away['team']} @ {home['team']}")
    lines.append(f"FINAL:   {away['team']} {_fmt(away['score'])}  —  {home['team']} {_fmt(home['score'])}")
    margin = abs(home['score'] - away['score'])
    winner = home['team'] if home['score'] > away['score'] else away['team']
    if home['score'] == away['score']:
        lines.append("RESULT:  Tie game")
    elif margin <= 5:
        lines.append(f"RESULT:  {winner} wins in a tight contest (margin: {_fmt(margin)})")
    elif margin <= 14:
        lines.append(f"RESULT:  {winner} wins comfortably (margin: {_fmt(margin)})")
    else:
        lines.append(f"RESULT:  {winner} dominates (margin: {_fmt(margin)})")
    lines.append("")

    # ── Scoring Breakdown ──
    lines.append("─── SCORING BREAKDOWN ───")
    lines.append("(How each team scored — the 'scoring profile' is Viperball's")
    lines.append(" most important analytical lens)")
    lines.append("")

    for side, label in [('home', home['team']), ('away', away['team'])]:
        stats = game_data['stats'][side]
        profile = calculate_scoring_profile(plays, drives, side, stats)

        td_pts = profile['rush_td_pts'] + profile['lateral_td_pts'] + profile['kp_td_pts']
        total_tds = profile['rush_tds'] + profile['lateral_tds'] + profile['kp_tds']
        dk_pts = profile['dk_pts']
        pk_pts = profile['pk_pts']
        ret_pts = profile['return_td_pts']
        total = profile['total_pts']

        lines.append(f"  {label}:")
        lines.append(f"    Touchdowns:   {total_tds} × 9 = {td_pts} pts")
        if profile['rush_tds']:
            lines.append(f"      Rush TDs:     {profile['rush_tds']}")
        if profile['lateral_tds']:
            lines.append(f"      Lateral TDs:  {profile['lateral_tds']}")
        if profile['kp_tds']:
            lines.append(f"      Kick-Pass TDs: {profile['kp_tds']}")
        if profile['dk_made']:
            lines.append(f"    Snap Kicks:   {profile['dk_made']} × 5 = {dk_pts} pts")
        if stats.get('place_kicks_made', 0):
            lines.append(f"    Field Goals:  {stats['place_kicks_made']} × 3 = {pk_pts} pts")
        if profile['return_tds']:
            lines.append(f"    Return TDs:   {profile['return_tds']} × 9 = {ret_pts} pts")
        lines.append(f"    Accounted:    {total} pts")
        lines.append("")

    # ── Team Metrics (with grades) ──
    lines.append("─── TEAM ANALYTICS ───")
    lines.append("")

    for side, label in [('home', home['team']), ('away', away['team'])]:
        stats = game_data['stats'][side]
        metrics = calculate_viperball_metrics(game_data, side)
        wpa = calculate_game_epa(plays, side)

        ppd = metrics['ppd']
        conv = metrics['conversion_pct']
        explosive = metrics['explosive_plays']
        to_margin = metrics['to_margin']
        rating = metrics['team_rating']

        lines.append(f"  {label} (Team Rating: {_fmt(rating)}/100)")
        lines.append(f"    PPD:              {_fmt(ppd, 2)}  [{_grade(ppd, PPD_GRADES)}]")
        lines.append(f"    Conversion %:     {_fmt(conv)}%  [{_grade(conv, CONV_GRADES)}]")
        lines.append(f"    Explosive Plays:  {explosive}")
        lines.append(f"    TO Margin:        {to_margin:+d}")
        lines.append(f"    Total Yards:      {round(stats.get('total_yards', 0))}")
        lines.append(f"    Yards/Play:       {_fmt(stats.get('yards_per_play', 0), 2)}")
        lines.append(f"    WPA (total):      {_fmt(wpa.get('wpa', 0), 2)}")
        lines.append(f"    Success Rate:     {_fmt(wpa.get('success_rate', 0))}%")

        # Kicking aggression
        dk_att = stats.get('drop_kicks_attempted', 0)
        pk_att = stats.get('place_kicks_attempted', 0)
        total_kicks = dk_att + pk_att
        if total_kicks > 0:
            kai = round(dk_att / total_kicks * 100, 1)
            lines.append(f"    Kick Aggression:  {kai}% snap kicks ({dk_att}/{total_kicks} attempts)")

        lines.append("")

    # ── Delta Profile + Conversion by Zone ──
    lines.append("─── DELTA YARDS & FIELD POSITION ───")
    lines.append("(Viperball has NO kickoffs. After each score, the receiving team starts at")
    lines.append(" the 20-yard line adjusted by score differential. Trailing = better field")
    lines.append(" position (a 'power play'); leading = worse (a 'penalty kill').")
    lines.append(" 'Δ Yards' = net yards gained or lost from this system. A team leading big")
    lines.append(" all game will have large negative Δ Yards — that's the cost of winning,")
    lines.append(" not a flaw.)")
    lines.append("")

    for side, label in [('home', home['team']), ('away', away['team'])]:
        stats = game_data['stats'][side]
        metrics = calculate_viperball_metrics(game_data, side)
        delta = metrics.get('delta_profile', {})
        lines.append(f"  {label}:")
        dy = delta.get('delta_yds', 0)
        raw_delta = stats.get('delta_yards', 0)
        lines.append(f"    Δ Yards (raw):  {'+' if raw_delta >= 0 else ''}{round(raw_delta)}")
        lines.append(f"      (Negative = leading team penalty; positive = trailing team bonus)")
        adj_yds = stats.get('adjusted_yards', stats.get('total_yards', 0))
        tot_yds = round(stats.get('total_yards', 0))
        lines.append(f"    Total Yards:    {tot_yds}  |  Adjusted (with Δ): {round(adj_yds)}")
        lines.append(f"    Δ Drives: {delta.get('delta_drives', 0):+d}")
        lines.append(f"    Δ Scores: {delta.get('delta_scores', 0):+d}")
        team_kill = delta.get('team_kill_pct', 0)
        opp_kill = delta.get('opp_kill_pct', 0)
        lines.append(f"    PK% (Penalty Kill):  {team_kill}%  — scoring rate when leading & pinned back")
        lines.append(f"    Opp PP% (Power Play): {opp_kill}%  — opponent's scoring rate on boosted drives")
        lines.append("")

    # ── Bonus Possessions ──
    lines.append("─── BONUS POSSESSIONS ───")
    lines.append("(When a team intercepts a kick pass, the intercepting team gets their drive,")
    lines.append(" then the original team gets the ball back as a bonus drive — unless the")
    lines.append(" intercepting team throws an INT back, which cancels the bonus.")
    lines.append(" Bonus drives are a massive advantage: a dominant secondary generates extra")
    lines.append(" possessions that don't exist for the opponent. A team earning 4-5 bonus")
    lines.append(" drives per game at a 60%+ conversion rate is adding 10-15 points that the")
    lines.append(" other team simply never gets a chance to match.)")
    lines.append("")

    for side, label in [('home', home['team']), ('away', away['team'])]:
        stats = game_data['stats'][side]
        bp = stats.get('bonus_possessions', 0)
        bp_yds = stats.get('bonus_possession_yards', 0)
        bp_scores = stats.get('bonus_possession_scores', 0)
        lines.append(f"  {label}:")
        lines.append(f"    Bonus Drives:  {bp}")
        if bp > 0:
            lines.append(f"    Bonus Yards:   {round(bp_yds)}")
            lines.append(f"    Bonus Scores:  {bp_scores}/{bp} ({round(bp_scores / bp * 100)}% conversion)")
        else:
            lines.append(f"    (No bonus possessions earned)")
        lines.append("")

    lines.append("─── CONVERSION BY FIELD POSITION ───")
    lines.append("(Viperball uses 6 downs to gain 20 yards. 4D/5D/6D = conversion rate on")
    lines.append(" 4th, 5th, and 6th down — the pressure downs. Downs 1-3 are omitted because")
    lines.append(" converting that early is routine. Where a team converts matters as much as")
    lines.append(" how often — converting 5th down from your own 15 is harder than from midfield.)")
    lines.append("")

    zone_labels = {
        "own_deep": "Own 1-25 (backed up)",
        "own_half": "Own 26-50",
        "opp_half": "Opp 49-25",
        "opp_deep": "Opp 24-1 (red zone)",
    }

    for side, label in [('home', home['team']), ('away', away['team'])]:
        metrics = calculate_viperball_metrics(game_data, side)
        conv_zones = metrics.get('conversion_by_zone', {})
        lines.append(f"  {label}:")
        lines.append(f"    {'Zone':<25s} {'4D%':>8s} {'5D%':>8s} {'6D%':>8s}")
        lines.append(f"    {'─'*25} {'─'*8} {'─'*8} {'─'*8}")
        for zone_key, zone_label in zone_labels.items():
            zd = conv_zones.get(zone_key, {})
            d4 = f"{zd.get('d4_pct', 0):.0f}%" if zd.get('d4_att', 0) else "—"
            d5 = f"{zd.get('d5_pct', 0):.0f}%" if zd.get('d5_att', 0) else "—"
            d6 = f"{zd.get('d6_pct', 0):.0f}%" if zd.get('d6_att', 0) else "—"
            d4_n = f"({zd.get('d4_att', 0)})" if zd.get('d4_att', 0) else ""
            d5_n = f"({zd.get('d5_att', 0)})" if zd.get('d5_att', 0) else ""
            d6_n = f"({zd.get('d6_att', 0)})" if zd.get('d6_att', 0) else ""
            lines.append(f"    {zone_label:<25s} {d4:>4s}{d4_n:>4s} {d5:>4s}{d5_n:>4s} {d6:>4s}{d6_n:>4s}")
        lines.append("")

    # ── Key Player Performances ──
    lines.append("─── KEY PLAYERS ───")
    lines.append("(ZBR = Zeroback Rating, 0-158.3 scale like NFL passer rating)")
    lines.append("")

    for side, label in [('home', home['team']), ('away', away['team'])]:
        player_list = game_data.get('player_stats', {}).get(side, [])
        if not player_list:
            continue

        lines.append(f"  {label}:")

        # player_list is a list of dicts sorted by activity
        for ps in player_list[:5]:
            name = ps.get('name', ps.get('tag', '??'))
            pos = ps.get('position', '??')
            total_yards = ps.get('yards', 0)
            if total_yards <= 0 and ps.get('tackles', 0) <= 0:
                continue

            rush_yds = ps.get('rushing_yards', 0)
            lat_yds = ps.get('lateral_yards', 0)
            tds = ps.get('tds', 0)
            fumbles = ps.get('fumbles', 0)
            tackles = ps.get('tackles', 0)

            stat_parts = []
            if rush_yds:
                stat_parts.append(f"{round(rush_yds)} rush yds")
            if lat_yds:
                stat_parts.append(f"{round(lat_yds)} lat yds")
            if tds:
                stat_parts.append(f"{tds} TD")
            if fumbles:
                stat_parts.append(f"{fumbles} fumble")
            if tackles:
                stat_parts.append(f"{tackles} tackles")

            # ZBR for zerobacks
            rating_str = ""
            if pos in ("ZB", "Zeroback"):
                zbr = calculate_zbr(ps)
                rating_str = f" [ZBR: {_fmt(zbr)}]"
            elif pos in ("VP", "Viper"):
                vpr = calculate_vpr(ps)
                rating_str = f" [VPR: {_fmt(vpr)}]"

            stat_line = ", ".join(stat_parts) if stat_parts else "no offensive stats"
            lines.append(f"    {name} ({pos}): {stat_line}{rating_str}")

        lines.append("")

    # ── Narrative Summary ──
    lines.append("─── GAME NARRATIVE ───")
    lines.append("(Analytical summary for writers)")
    lines.append("")

    # Determine the story of the game
    home_metrics = calculate_viperball_metrics(game_data, 'home')
    away_metrics = calculate_viperball_metrics(game_data, 'away')

    narratives = []

    # Turnover story
    home_to = home_metrics['to_margin']
    if abs(home_to) >= 2:
        to_winner = home['team'] if home_to > 0 else away['team']
        to_loser = away['team'] if home_to > 0 else home['team']
        narratives.append(
            f"Turnover battle: {to_winner} was +{abs(home_to)} in turnovers, "
            f"giving them extra possessions that {to_loser} couldn't overcome."
        )

    # Kicking story
    home_dk = home_stats.get('drop_kicks_made', 0)
    away_dk = away_stats.get('drop_kicks_made', 0)
    total_dk = home_dk + away_dk
    if total_dk >= 4:
        narratives.append(
            f"Kicking dominated: {total_dk} snap kicks made in this game "
            f"({total_dk * 5} pts from the boot alone). This was a kicker's duel."
        )

    # Explosive play story
    home_exp = home_metrics['explosive_plays']
    away_exp = away_metrics['explosive_plays']
    if max(home_exp, away_exp) >= 8:
        big_play_team = home['team'] if home_exp > away_exp else away['team']
        narratives.append(
            f"Big-play dominance: {big_play_team} generated {max(home_exp, away_exp)} "
            f"explosive plays (15+ yards), creating chunk yardage that kept drives alive."
        )

    # PPD gap
    home_ppd = home_metrics['ppd']
    away_ppd = away_metrics['ppd']
    if abs(home_ppd - away_ppd) >= 2.0:
        better_ppd_team = home['team'] if home_ppd > away_ppd else away['team']
        narratives.append(
            f"Offensive efficiency gap: {better_ppd_team} scored "
            f"{max(home_ppd, away_ppd):.1f} PPD vs {min(home_ppd, away_ppd):.1f}. "
            f"That kind of per-drive separation accumulates fast over a full game."
        )

    if not narratives:
        narratives.append("A balanced, evenly-contested game without a single dominant storyline.")

    for n in narratives:
        lines.append(f"  • {n}")
    lines.append("")

    # ── Cross-sport comparison ──
    lines.append("─── CROSS-SPORT CONTEXT ───")
    lines.append("")
    combined = home['score'] + away['score']
    nfl_equiv = round(combined * 0.78)
    lines.append(f"  Combined score ({_fmt(combined)}) ≈ {nfl_equiv} in NFL-equivalent scoring")
    lines.append(f"  (Multiply Viperball scores by ~0.78 for NFL feel)")

    winner_metrics = home_metrics if home['score'] >= away['score'] else away_metrics
    winner_ppd = winner_metrics['ppd']
    if winner_ppd >= 5.0:
        lines.append(f"  Winner's PPD of {_fmt(winner_ppd, 2)} is elite — comparable to a")
        lines.append(f"  top-5 NFL offense or an NBA team with 115+ offensive rating")
    elif winner_ppd >= 3.5:
        lines.append(f"  Winner's PPD of {_fmt(winner_ppd, 2)} is solid — mid-tier NFL offense territory")
    lines.append("")

    lines.append("================================================================================")
    return "\n".join(lines)


def simulate_and_analyze(home_name: str, away_name: str) -> tuple:
    """Simulate a game and return the analysis."""
    home_file = f"data/teams/{home_name}.json"
    away_file = f"data/teams/{away_name}.json"

    if not os.path.exists(home_file):
        return f"Error: team file not found: {home_file}", None
    if not os.path.exists(away_file):
        return f"Error: team file not found: {away_file}", None

    home_team = load_team_from_json(home_file)
    away_team = load_team_from_json(away_file)

    engine = ViperballEngine(home_team, away_team)
    game_data = engine.simulate_game()

    return analyze_game_data(game_data), game_data


def matchup_analysis(home_name: str, away_name: str, num_games: int = 10) -> str:
    """Simulate multiple games and produce aggregate analysis."""
    home_file = f"data/teams/{home_name}.json"
    away_file = f"data/teams/{away_name}.json"

    if not os.path.exists(home_file):
        return f"Error: team file not found: {home_file}"
    if not os.path.exists(away_file):
        return f"Error: team file not found: {away_file}"

    home_team = load_team_from_json(home_file)
    away_team = load_team_from_json(away_file)

    results = []
    home_wins = 0
    away_wins = 0
    ties = 0
    home_scores = []
    away_scores = []

    for _i in range(num_games):
        engine = ViperballEngine(home_team, away_team)
        gd = engine.simulate_game()
        hs = gd['final_score']['home']['score']
        as_ = gd['final_score']['away']['score']
        home_scores.append(hs)
        away_scores.append(as_)
        if hs > as_:
            home_wins += 1
        elif as_ > hs:
            away_wins += 1
        else:
            ties += 1
        results.append(gd)

    lines = [CONTEXT_HEADER, ""]
    lines.append(f"MATCHUP ANALYSIS: {away_team.name} @ {home_team.name}")
    lines.append(f"SAMPLE SIZE: {num_games} simulated games")
    lines.append("")
    lines.append(f"  {home_team.name}: {home_wins}-{away_wins}" +
                 (f"-{ties}" if ties else "") + f" ({home_wins/num_games*100:.0f}% win rate)")
    lines.append(f"  {away_team.name}: {away_wins}-{home_wins}" +
                 (f"-{ties}" if ties else "") + f" ({away_wins/num_games*100:.0f}% win rate)")
    lines.append("")
    lines.append(f"  Avg score: {home_team.name} {sum(home_scores)/num_games:.1f} — "
                 f"{away_team.name} {sum(away_scores)/num_games:.1f}")
    lines.append(f"  Score range: {min(home_scores)}-{max(home_scores)} vs "
                 f"{min(away_scores)}-{max(away_scores)}")
    lines.append(f"  Avg combined: {(sum(home_scores)+sum(away_scores))/num_games:.1f}")
    lines.append("")

    # Closest and most lopsided
    margins = [abs(home_scores[i] - away_scores[i]) for i in range(num_games)]
    closest_i = margins.index(min(margins))
    blowout_i = margins.index(max(margins))
    lines.append(f"  Closest game:  {_fmt(away_scores[closest_i])}-{_fmt(home_scores[closest_i])} "
                 f"(margin: {_fmt(margins[closest_i])})")
    lines.append(f"  Biggest blowout: {_fmt(away_scores[blowout_i])}-{_fmt(home_scores[blowout_i])} "
                 f"(margin: {_fmt(margins[blowout_i])})")
    lines.append("")

    lines.append("  INTERPRETATION:")
    if max(home_wins, away_wins) >= num_games * 0.7:
        dominant = home_team.name if home_wins > away_wins else away_team.name
        lines.append(f"    {dominant} is clearly the stronger team in this matchup.")
    elif max(home_wins, away_wins) >= num_games * 0.55:
        lines.append(f"    Slight edge but competitive — expect close games.")
    else:
        lines.append(f"    True toss-up matchup. Either team can win on any given day.")

    avg_margin = sum(margins) / num_games
    if avg_margin > 15:
        lines.append(f"    High average margin ({avg_margin:.1f}) suggests talent gap.")
    elif avg_margin < 8:
        lines.append(f"    Low average margin ({avg_margin:.1f}) — these teams are evenly matched.")

    lines.append("")
    lines.append("================================================================================")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Viperball Game Analysis")
    parser.add_argument("input", nargs="?", help="Play-by-play JSON file to analyze")
    parser.add_argument("--sim", nargs=2, metavar=("HOME", "AWAY"),
                        help="Simulate a game between two teams")
    parser.add_argument("--matchup", nargs=2, metavar=("HOME", "AWAY"),
                        help="Multi-game matchup analysis")
    parser.add_argument("--games", type=int, default=10,
                        help="Number of games for matchup analysis (default: 10)")
    parser.add_argument("--save", help="Save analysis to file")

    args = parser.parse_args()

    if args.matchup:
        output = matchup_analysis(args.matchup[0], args.matchup[1], args.games)
    elif args.sim:
        output, game_data = simulate_and_analyze(args.sim[0], args.sim[1])
        # Also save the raw game data
        os.makedirs("examples", exist_ok=True)
        raw_path = f"examples/analysis_{args.sim[1]}_at_{args.sim[0]}.json"
        with open(raw_path, 'w') as f:
            json.dump(game_data, f, indent=2)
        print(f"(Raw game data saved to {raw_path})", file=sys.stderr)
    elif args.input:
        with open(args.input) as f:
            game_data = json.load(f)
        output = analyze_game_data(game_data)
    else:
        parser.print_help()
        sys.exit(1)

    if args.save:
        with open(args.save, 'w') as f:
            f.write(output)
        print(f"Analysis saved to {args.save}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
